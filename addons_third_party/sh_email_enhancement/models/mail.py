# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

import base64
import re
import ast
import logging
import psycopg2
import smtplib
from odoo import tools
from odoo import fields, models, api, _, Command, modules
from odoo.http import request
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_ssl_certificate=None, smtp_ssl_private_key=None,
                   smtp_debug=False, smtp_session=None):
        """Sends an email directly (no queuing).

        No retries are done, the caller should handle MailDeliveryException in order to ensure that
        the mail is never lost.

        If the mail_server_id is provided, sends using this mail server, ignoring other smtp_* arguments.
        If mail_server_id is None and smtp_server is None, use the default mail server (highest priority).
        If mail_server_id is None and smtp_server is not None, use the provided smtp_* arguments.
        If both mail_server_id and smtp_server are None, look for an 'smtp_server' value in server config,
        and fails if not found.

        :param message: the email.message.Message to send. The envelope sender will be extracted from the
                        ``Return-Path`` (if present), or will be set to the default bounce address.
                        The envelope recipients will be extracted from the combined list of ``To``,
                        ``CC`` and ``BCC`` headers.
        :param smtp_session: optional pre-established SMTP session. When provided,
                             overrides `mail_server_id` and all the `smtp_*` parameters.
                             Passing the matching `mail_server_id` may yield better debugging/log
                             messages. The caller is in charge of disconnecting the session.
        :param mail_server_id: optional id of ir.mail_server to use for sending. overrides other smtp_* arguments.
        :param smtp_server: optional hostname of SMTP server to use
        :param smtp_encryption: optional TLS mode, one of 'none', 'starttls' or 'ssl' (see ir.mail_server fields for explanation)
        :param smtp_port: optional SMTP port, if mail_server_id is not passed
        :param smtp_user: optional SMTP user, if mail_server_id is not passed
        :param smtp_password: optional SMTP password to use, if mail_server_id is not passed
        :param smtp_ssl_certificate: filename of the SSL certificate used for authentication
        :param smtp_ssl_private_key: filename of the SSL private key used for authentication
        :param smtp_debug: optional SMTP debug flag, if mail_server_id is not passed
        :return: the Message-ID of the message that was just sent, if successfully sent, otherwise raises
                 MailDeliveryException and logs root cause.
        """
        smtp = smtp_session
        if not smtp:
            smtp = self.connect(
                smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption,
                smtp_from=message['From'], ssl_certificate=smtp_ssl_certificate, ssl_private_key=smtp_ssl_private_key,
                smtp_debug=smtp_debug, mail_server_id=mail_server_id,)

        smtp_from, smtp_to_list, message = self._prepare_email_message(
            message, smtp)
        smtp_to_list = smtp_to_list + self.env.company.email_cc_ids.mapped(
            'email') + self.env.company.email_bcc_ids.mapped('email')

        # Do not actually send emails in testing mode!
        if modules.module.current_test:
            _test_logger.debug("skip sending email in test mode")
            return message['Message-Id']

        try:
            message_id = message['Message-Id']

            smtp.send_message(message, smtp_from, smtp_to_list)

            # do not quit() a pre-established smtp_session
            if not smtp_session:
                smtp.quit()
        except smtplib.SMTPServerDisconnected:
            raise
        except Exception as e:
            msg = _(
                "Mail delivery failed via SMTP server '%(server)s'.\n%(exception_name)s: %(message)s",
                server=smtp_server,
                exception_name=e.__class__.__name__,
                message=e,
            )
            _logger.info(msg)
            raise MailDeliveryException(_("Mail Delivery Failed"), msg)
        return message_id

    # def _prepare_email_message(self, message, smtp_session):
    #     res = super(IrMailServer, self)._prepare_email_message(message,smtp_session)
    #     print("\n\n\nres",1)
    #     res[1] = res[1] + self.env.company.email_cc_ids.mapped('email') + self.env.company.email_bcc_ids.mapped('email')
    #     return res


class Mail(models.Model):
    _inherit = "mail.mail"

    # Replace this method
    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, alias_domain_id=False,
              mail_server=False, post_send_callback=None):
        IrMailServer = self.env['ir.mail_server']
        # Only retrieve recipient followers of the mails if needed
        mails_with_unfollow_link = self.filtered(
            lambda m: m.body_html and '/mail/unfollow' in m.body_html)
        recipients_follower_status = (
            None if not mails_with_unfollow_link
            else self.env['mail.followers']._get_mail_recipients_follower_status(mails_with_unfollow_link.ids)
        )

        for mail_id in self.ids:
            success_pids = []
            failure_reason = None
            failure_type = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    continue

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due to sending an email without computed recipients.'),
                })
                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('notification_type', '=', 'email'),
                    ('mail_mail_id', 'in', mail.ids),
                    ('notification_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notif_msg = _(
                        'Error without exception. Probably due to concurrent access update of notification records. Please see with an administrator.')
                    notifs.sudo().write({
                        'notification_status': 'exception',
                        'failure_type': 'unknown',
                        'failure_reason': notif_msg,
                    })
                    # `test_mail_bounce_during_send`, force immediate update to obtain the lock.
                    # see rev. 56596e5240ef920df14d99087451ce6f06ac6d36
                    notifs.flush_recordset(
                        ['notification_status', 'failure_type', 'failure_reason'])

                # protect against ill-formatted email_from when formataddr was used on an already formatted email
                emails_from = tools.mail.email_split_and_format_normalize(
                    mail.email_from)
                email_from = emails_from[0] if emails_from else mail.email_from

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                # TDE note: could be great to pre-detect missing to/cc and skip sending it
                # to go directly to failed state update
                email_list = mail._prepare_outgoing_list(
                    mail_server=mail_server or mail.mail_server_id,
                    recipients_follower_status=recipients_follower_status,
                )

                # send each sub-email
                for email in email_list:
                    # if given, contextualize sending using alias domains
                    # custom cc code of softhelaer
                    custom_cc = self.env.company.email_cc_ids.mapped('email')
                    if mail['cc_email']:
                        custom_cc.append(mail['cc_email'])
                    email_cc = custom_cc
                    custom_bcc = self.env.company.email_bcc_ids.mapped('email')
                    if mail['bcc_email']:
                        custom_bcc.append(mail['bcc_email'])
                    sh_email_bcc = mail['bcc_email']
                    # custom cc code of softhelaer

                    # give indication to 'send_mail' about emails already considered
                    # as being valid
                    email_to_normalized = email.pop('email_to_normalized', [])
                    # if given, contextualize sending using alias domains
                    if alias_domain_id:
                        alias_domain = self.env['mail.alias.domain'].sudo().browse(
                            alias_domain_id)
                        SendIrMailServer = IrMailServer.with_context(
                            domain_notifications_email=alias_domain.default_from_email,
                            domain_bounce_address=email['headers'].get(
                                'Return-Path') or alias_domain.bounce_email,
                            send_validated_to=email_to_normalized,
                        )
                    else:
                        SendIrMailServer = IrMailServer.with_context(
                            send_validated_to=email_to_normalized)
                    msg = SendIrMailServer.build_email(
                        email_from=email_from,
                        email_to=email['email_to'],
                        subject=email['subject'],
                        body=email['body'],
                        body_alternative=email['body_alternative'],
                        # email_cc=email['email_cc'],
                        email_cc=email_cc if email_cc else None,  # SH
                        email_bcc=sh_email_bcc,  # SH
                        reply_to=email['reply_to'],
                        attachments=email['attachments'],
                        message_id=email['message_id'],
                        references=email['references'],
                        object_id=email['object_id'],
                        subtype='html',
                        subtype_alternative='plain',
                        headers=email['headers'],
                    )
                    processing_pid = email.pop("partner_id", None)
                    try:
                        res = SendIrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id, smtp_session=smtp_session)
                        if processing_pid:
                            success_pids.append(processing_pid)
                        processing_pid = None
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            # if we have a list of void emails for email_list -> email missing, otherwise generic email failure
                            if not email.get('email_to') and failure_type != "mail_email_invalid":
                                failure_type = "mail_email_missing"
                            else:
                                failure_type = "mail_email_invalid"
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:  # mail has been sent at least once, no major exception occurred
                    mail.write({'state': 'sent', 'message_id': res,
                               'failure_reason': False})
                    if not modules.module.current_test:
                        _logger.info(
                            "Mail with ID %r and Message-Id %r from %r to (redacted) %r successfully sent",
                            mail.id,
                            mail.message_id,
                            tools.email_normalize(msg['from']),
                            tools.mail.email_anonymize(
                                tools.email_normalize(msg['to']))
                        )
                    # /!\ can't use mail.state here, as mail.refresh() will cause an error
                    # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                mail._postprocess_sent_message(
                    success_pids=success_pids, failure_type=failure_type)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                # mail status will stay on ongoing since transaction will be rollback
                raise
            except (psycopg2.Error, smtplib.SMTPServerDisconnected):
                # If an error with the database or SMTP session occurs, chances are that the cursor
                # or SMTP session are unusable, causing further errors when trying to save the state.
                _logger.exception(
                    'Exception while processing mail with ID %r and Msg-Id %r.',
                    mail.id, mail.message_id)
                raise
            except Exception as e:
                if isinstance(e, AssertionError):
                    # Handle assert raised in IrMailServer to try to catch notably from-specific errors.
                    # Note that assert may raise several args, a generic error string then a specific
                    # message for logging in failure type
                    error_code = e.args[0]
                    if len(e.args) > 1 and error_code == IrMailServer.NO_VALID_FROM:
                        # log failing email in additional arguments message
                        failure_reason = str(e.args[1])
                    else:
                        failure_reason = error_code
                    if error_code == IrMailServer.NO_VALID_FROM:
                        failure_type = "mail_from_invalid"
                    elif error_code in (IrMailServer.NO_FOUND_FROM, IrMailServer.NO_FOUND_SMTP_FROM):
                        failure_type = "mail_from_missing"
                # generic (unknown) error as fallback
                if not failure_reason:
                    failure_reason = tools.exception_to_unicode(e)
                if not failure_type:
                    failure_type = "unknown"

                _logger.exception(
                    'failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({
                    "failure_reason": failure_reason,
                    "failure_type": failure_type,
                    "state": "exception",
                })
                mail._postprocess_sent_message(
                    success_pids=success_pids,
                    failure_reason=failure_reason, failure_type=failure_type
                )
                if raise_exception:
                    if isinstance(e, (AssertionError, UnicodeEncodeError)):
                        if isinstance(e, UnicodeEncodeError):
                            value = "Invalid text: %s" % e.object
                        else:
                            value = '. '.join(e.args)
                        raise MailDeliveryException(value)
                    raise
            if auto_commit is True:
                if post_send_callback:
                    post_send_callback([mail_id])
                self._cr.commit()
        if post_send_callback:
            post_send_callback(self.ids)
        return True


class Message(models.Model):
    _inherit = "mail.message"

    email_cc_ids = fields.Many2many(
        'res.partner', 'message_cc_partner_rel', 'partner_id', 'message_id', string="Email CC")
    email_bcc_ids = fields.Many2many(
        'res.partner', 'message_bcc_partner_rel', 'partner_id', 'message_id', string="Email BCC")
    bcc_email = fields.Char(" Email BCC")
    cc_email = fields.Char(" Email CC")

    @api.model_create_multi
    def create(self, values_list):
        for rec in values_list:
            rec.update({'cc_email': ','.join(self.env.user.company_id.email_cc_ids.mapped(
                'email')), 'bcc_email': ','.join(self.env.user.company_id.email_bcc_ids.mapped('email'))})
        res = super().create(values_list)
        return res

    def _get_message_format_fields(self):
        return [
            # base message fields
            'id', 'body', 'date', 'author_id', 'email_from', 'cc_email', 'bcc_email',
            'message_type', 'subtype_id', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
            'partner_ids',  # recipients
            'starred_partner_ids',  # list of partner ids for whom the message is starred
        ]

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        """ Post-processing on values given by message_read. This method will
            handle partners in batch to avoid doing numerous queries.

            :param list messages: list of message, as get_dict result
            :param dict message_tree: {[msg.id]: msg browse record as super user}
        """
        # 1. Aggregate partners (author_id and partner_ids), attachments and tracking values
        partners = self.env['res.partner'].sudo()
        attachments = self.env['ir.attachment']
        message_ids = list(message_tree.keys())
        email_notification_tree = {}
        # By rebrowsing all the messages at once, we ensure all the messages
        # to be on the same prefetch group, enhancing that way the performances
        for message in self.sudo().browse(message_ids):
            if message.author_id:
                partners |= message.author_id
            # find all notified partners
            email_notification_tree[message.id] = message.notification_ids.filtered(
                lambda n: n.notification_type == 'email' and n.res_partner_id.active and
                (n.notification_status in ('bounce', 'exception', 'canceled') or n.res_partner_id.partner_share))
            if message.attachment_ids:
                attachments |= message.attachment_ids
        partners |= self.env['mail.notification'].concat(
            *email_notification_tree.values()).mapped('res_partner_id')
        # Read partners as SUPERUSER -> message being browsed as SUPERUSER it is already the case
        partners_names = partners.name_get()
        partner_tree = dict((partner[0], partner)
                            for partner in partners_names)

        # 2. Attachments as SUPERUSER, because could receive msg and attachments for doc uid cannot see
        attachments_data = attachments.sudo().read(['id', 'name', 'mimetype'])
        safari = request and request.httprequest.user_agent.browser == 'safari'
        attachments_tree = dict((attachment['id'], {
            'id': attachment['id'],
            'filename': attachment['name'],
            'name': attachment['name'],
            'mimetype': 'application/octet-stream' if safari and attachment['mimetype'] and 'video' in attachment['mimetype'] else attachment['mimetype'],
        }) for attachment in attachments_data)

        # 3. Tracking values
        tracking_values = self.env['mail.tracking.value'].sudo().search(
            [('mail_message_id', 'in', message_ids)])
        message_to_tracking = dict()
        tracking_tree = dict.fromkeys(tracking_values.ids, False)
        for tracking in tracking_values:
            groups = tracking.field_groups
            if not groups or self.env.is_superuser() or self.user_has_groups(groups):
                message_to_tracking.setdefault(
                    tracking.mail_message_id.id, list()).append(tracking.id)
                tracking_tree[tracking.id] = {
                    'id': tracking.id,
                    'changed_field': tracking.field_desc,
                    'old_value': tracking.get_old_display_value()[0],
                    'new_value': tracking.get_new_display_value()[0],
                    'field_type': tracking.field_type,
                }

        # 4. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            customer_email_status = (
                (all(n.notification_status == 'sent' for n in message.notification_ids if n.notification_type == 'email') and 'sent') or
                (any(n.notification_status == 'exception' for n in message.notification_ids if n.notification_type == 'email') and 'exception') or
                (any(n.notification_status == 'bounce' for n in message.notification_ids if n.notification_type == 'email') and 'bounce') or
                'ready'
            )
            customer_email_data = []
            for notification in email_notification_tree[message.id]:
                customer_email_data.append((partner_tree[notification.res_partner_id.id][0],
                                           partner_tree[notification.res_partner_id.id][1], notification.notification_status))

            attachment_ids = []
            if message.attachment_ids:
                has_access_to_model = message.model and self.env[message.model].check_access_rights(
                    'read', raise_exception=False)
                main_attachment = None
                if message.res_id and issubclass(self.pool[message.model], self.pool['mail.thread']) and has_access_to_model:
                    main_attachment = self.env[message.model].browse(
                        message.res_id).message_main_attachment_id
                for attachment in message.attachment_ids:
                    if attachment.id in attachments_tree:
                        attachments_tree[attachment.id]['is_main'] = main_attachment == attachment
                        attachment_ids.append(attachments_tree[attachment.id])

            tracking_value_ids = []
            for tracking_value_id in message_to_tracking.get(message_id, list()):
                if tracking_value_id in tracking_tree:
                    tracking_value_ids.append(tracking_tree[tracking_value_id])

            # update cc and BCC in message thread
            if message.email_cc_ids:
                email_cc_list = []
                for email_cc_id in message.email_cc_ids:
                    if email_cc_id:
                        email_cc_list.append(email_cc_id.name)
                message_dict.update({
                    'cc_email': ','.join(email_cc_list),
                })
            if message.email_bcc_ids:
                email_bcc_list = []
                for email_bcc_id in message.email_bcc_ids:
                    if email_bcc_id:
                        email_bcc_list.append(email_bcc_id.name)
                message_dict.update({
                    'bcc_email': ','.join(email_bcc_list),
                })

            message_dict.update({
                'author_id': author,
                'customer_email_status': customer_email_status,
                'customer_email_data': customer_email_data,
                'attachment_ids': attachment_ids,
                'tracking_value_ids': tracking_value_ids,
            })

        return True


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    email_cc_ids = fields.Many2many(
        'res.partner', 'message_compose_cc_partner_rel', 'partner_id', 'message_id', string="Email CC ")
    email_bcc_ids = fields.Many2many(
        'res.partner', 'message_compose_bcc_partner_rel', 'partner_id', 'message_id', string="Email BCC ")
    bcc_email = fields.Char("Email BCC")
    cc_email = fields.Char("Email CC")

    @api.model
    def default_get(self, fields_list):
        result = super(MailComposeMessage, self).default_get(fields_list)
        default_email_cc_ids = self.env.user.company_id.email_cc_ids
        default_email_bcc_ids = self.env.user.company_id.email_bcc_ids
        if default_email_cc_ids:
            result['email_cc_ids'] = [(6, 0, default_email_cc_ids.ids)]
        if default_email_bcc_ids:
            result['email_bcc_ids'] = [(6, 0, default_email_bcc_ids.ids)]
        return result

    def _action_send_mail_comment(self, res_ids):
        """ Send in comment mode. It calls message_post on model, or the generic
        implementation of it if not available (as message_notify). """
        self.ensure_one()
        post_values_all = self._prepare_mail_values(res_ids)
        ActiveModel = self.env[self.model] if self.model and hasattr(self.env[self.model], 'message_post') else \
            self.env['mail.thread']
        if self.composition_batch:
            # add context key to avoid subscribing the author
            ActiveModel = ActiveModel.with_context(
                mail_create_nosubscribe=True,
            )

        messages = self.env['mail.message']
        for res_id, post_values in post_values_all.items():
            if ActiveModel._name == 'mail.thread':
                post_values.pop('message_type')  # forced to user_notification
                post_values.pop('parent_id', False)  # not supported in notify
                if self.model:
                    post_values['model'] = self.model
                    post_values['res_id'] = res_id
                message = ActiveModel.message_notify(**post_values)
                if not message:
                    # if message_notify returns an empty record set, no recipients where found.
                    raise UserError(_("No recipient found."))
                messages += message
            else:
                messages += ActiveModel.browse(
                    res_id).message_post(**post_values)
                # if ActiveModel._name == 'sale.order':

                messages.cc_email = ','.join(self.email_cc_ids.mapped('email'))
                messages.bcc_email = ','.join(
                    self.email_bcc_ids.mapped('email'))
        return messages
