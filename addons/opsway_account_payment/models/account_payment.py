from odoo import models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('journal_id')
    def _compute_partner_id(self):
        """
        Copy of the _compute_partner_id from the account module.
        Customization for Opsway to allow internal payments
        """
        for pay in self:
            # START OF CUSTOMIZATION
            # if pay.partner_id == pay.journal_id.company_id.partner_id:
            #     pay.partner_id = False
            # else:
            pay.partner_id = pay.partner_id
            #END OF CUSTOMIZATION
