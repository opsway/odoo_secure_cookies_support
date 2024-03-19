# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _,Command
import logging
import psycopg2
import smtplib
import base64
from odoo.http import request
import re
from odoo import tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval
import ast

_logger = logging.getLogger(__name__)


class Mail(models.Model):
    _inherit = "mail.mail"

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        IrMailServer = self.env['ir.mail_server']
        IrAttachment = self.env['ir.attachment']
        for mail_id in self.ids:
            success_pids = []
            failure_type = None
            processing_pid = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    continue

                # remove attachments if user send the link with the access_token
                body = mail.body_html or ''
                attachments = mail.attachment_ids
                for link in re.findall(r'/web/(?:content|image)/([0-9]+)', body):
                    attachments = attachments - IrAttachment.browse(int(link))

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['name'], base64.b64decode(a['datas']), a['mimetype'])
                               for a in attachments.sudo().read(['name', 'datas', 'mimetype']) if a['datas'] is not False]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail._send_prepare_values())
                for partner in mail.recipient_ids:
                    values = mail._send_prepare_values(partner=partner)
                    values['partner_id'] = partner
                    email_list.append(values)

                # headers
                headers = {}
                ICP = self.env['ir.config_parameter'].sudo()
                bounce_alias = ICP.get_param("mail.bounce.alias")
                catchall_domain = ICP.get_param("mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    headers['Return-Path'] = '%s@%s' % (
                        bounce_alias, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(ast.literal_eval(mail.headers))
                    except Exception:
                        pass

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

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                # TDE note: could be great to pre-detect missing to/cc and skip sending it
                # to go directly to failed state update
                for email in email_list:
                    msg = IrMailServer.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        # email_cc=tools.email_split(mail.email_cc),
                        reply_to=mail.reply_to,
                        email_cc=tools.email_split(
                            mail.mail_message_id.cc_email),
                        email_bcc=tools.email_split(
                            mail.mail_message_id.bcc_email),
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and (
                            '%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    processing_pid = email.pop("partner_id", None)
                    try:
                        res = IrMailServer.send_email(
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
                    _logger.info(
                        'Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
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
                failure_reason = tools.ustr(e)
                _logger.exception(
                    'failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write(
                    {'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message(
                    success_pids=success_pids, failure_reason=failure_reason, failure_type='unknown')
                if raise_exception:
                    if isinstance(e, (AssertionError, UnicodeEncodeError)):
                        if isinstance(e, UnicodeEncodeError):
                            value = "Invalid text: %s" % e.object
                        else:
                            value = '. '.join(e.args)
                        raise MailDeliveryException(value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True


class Message(models.Model):
    _inherit = "mail.message"

    email_cc_ids = fields.Many2many(
        'res.partner', 'message_cc_partner_rel', 'partner_id', 'message_id', string="Email CC")
    email_bcc_ids = fields.Many2many(
        'res.partner', 'message_bcc_partner_rel', 'partner_id', 'message_id', string="Email BCC")
    bcc_email = fields.Char("Email BCC")
    cc_email = fields.Char("Email CC")

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
        'res.partner', 'message_compose_cc_partner_rel', 'partner_id', 'message_id', string="Email CC")
    email_bcc_ids = fields.Many2many(
        'res.partner', 'message_compose_bcc_partner_rel', 'partner_id', 'message_id', string="Email BCC")
    bcc_email = fields.Char("Email BCC")
    cc_email = fields.Char("Email CC")

    @api.model
    def default_get(self, fields):
        result = super(MailComposeMessage, self).default_get(fields)
        default_email_cc_ids = self.env.user.company_id.email_cc_ids
        default_email_bcc_ids = self.env.user.company_id.email_bcc_ids
        if default_email_cc_ids:
            result['email_cc_ids'] = [(6, 0, default_email_cc_ids.ids)]
        if default_email_bcc_ids:
            result['email_bcc_ids'] = [(6, 0, default_email_bcc_ids.ids)]
        return result

    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.reply_to_force_new:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = records._notify_get_reply_to(default=False)
            # when having no specific reply-to, fetch rendered email_from value
            for res_id, reply_to in reply_to_value.items():
                if not reply_to:
                    reply_to_value[res_id] = rendered_values.get(
                        res_id, {}).get('email_from', False)

        for res_id in res_ids:
            email_bcc_list = []
            email_cc_list = []
            if self.email_bcc_ids:
                for bcc_email in self.email_bcc_ids:
                    email_bcc_list.append(bcc_email.email)
            if self.email_cc_ids:
                for cc_email in self.email_cc_ids:
                    email_cc_list.append(cc_email.email)
            email_bcc = ','.join(email_bcc_list)
            email_cc = ','.join(email_cc_list)
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'reply_to_force_new': self.reply_to_force_new,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
                'message_type': 'email' if mass_mail_mode else self.message_type,
                'bcc_email': email_bcc,
                'cc_email': email_cc,
                'email_cc_ids': [(6, 0, self.email_cc_ids.ids)],
                'email_bcc_ids': [(6, 0, self.email_bcc_ids.ids)],
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                record = self.env[self.model].browse(res_id)
                mail_values['headers'] = repr(
                    record._notify_by_email_get_headers())
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(is_notification=not self.auto_delete_message,
                                   model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.reply_to_force_new:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.reply_to_force_new and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [Command.link(
                    id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(
                    enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(
                        attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                attachment_ids.reverse()
                mail_values['attachment_ids'] = self.env['mail.thread'].with_context(attached_to=record)._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']

            results[res_id] = mail_values

        results = self._process_state(results)
        return results
