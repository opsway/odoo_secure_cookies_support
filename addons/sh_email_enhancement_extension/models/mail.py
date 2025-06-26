from odoo import models, api


class Message(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, values_list):
        res = super().create(values_list)
        for rec in res:
            rec.update({
                'cc_email': ','.join(rec['email_cc_ids'].mapped('email')),
                'bcc_email': ','.join(rec['email_bcc_ids'].mapped('email'))
            })
        return res


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_message_create_valid_field_names(self):
        """
            This method is overridden to add email_cc_ids and email_bcc_ids to the valid fields
        """
        result = super(
            MailThread, self)._get_message_create_valid_field_names()
        result.update(['email_cc_ids', 'email_bcc_ids'])
        return result
