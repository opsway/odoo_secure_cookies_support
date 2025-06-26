from odoo import fields, models, api


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    email_cc_ids = fields.Many2many(
        'res.partner', 'message_invoice_cc_partner_rel', 'partner_id', 'message_id', string="Email CC")
    email_bcc_ids = fields.Many2many(
        'res.partner', 'message_invoice_bcc_partner_rel', 'partner_id', 'message_id', string="Email BCC")

    @api.model
    def default_get(self, fields_list):
        result = super(AccountMoveSendWizard, self).default_get(fields_list)
        default_email_cc_ids = self.env.user.company_id.email_cc_ids
        default_email_bcc_ids = self.env.user.company_id.email_bcc_ids
        if default_email_cc_ids:
            result['email_cc_ids'] = [(6, 0, default_email_cc_ids.ids)]
        if default_email_bcc_ids:
            result['email_bcc_ids'] = [(6, 0, default_email_bcc_ids.ids)]
        return result


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        """
            This method is overridden to add email_cc_ids and email_bcc_ids in kwargs
            original method in - odoo/addons/account/wizard/account_move_send.py
        """
        partner_ids = kwargs.get('partner_ids', [])
        author_id = kwargs.pop('author_id')

        new_message = move \
            .with_context(
                no_new_invoice=True,
                mail_notify_author=author_id in partner_ids,
            ).message_post(
                message_type='comment',
                **kwargs,
                **{
                    'email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                    'email_add_signature': not mail_template,
                    'mail_auto_delete': mail_template.auto_delete,
                    'mail_server_id': mail_template.mail_server_id.id,
                    'reply_to_force_new': False,
                    # customized part to add email_cc_ids and email_bcc_ids
                    'email_cc_ids': self.email_cc_ids,
                    'email_bcc_ids': self.email_bcc_ids,
                },
            )

        # Prevent duplicated attachments linked to the invoice.
        new_message.attachment_ids.invalidate_recordset(
            ['res_id', 'res_model'], flush=False)
        if new_message.attachment_ids.ids:
            self.env.cr.execute("UPDATE ir_attachment SET res_id = NULL WHERE id IN %s",
                                [tuple(new_message.attachment_ids.ids)])
        new_message.attachment_ids.write({
            'res_model': new_message._name,
            'res_id': new_message.id,
        })
