from odoo import models, api, _


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.depends('acc_number', 'bank_id', 'currency_id', 'allow_out_payment')
    @api.depends_context('display_account_trust')
    def _compute_display_name(self):
        for acc in self:
            if acc.currency_id and acc.bank_id:
                result_name = f'{
                    acc.acc_number} - {acc.bank_id.name} - {acc.currency_id.name}'
            elif not acc.currency_id and acc.bank_id:
                result_name = f'{acc.acc_number} - {acc.bank_id.name}'
            else:
                result_name = f'{acc.acc_number}'

            trusted_label = _(
                'trusted') if acc.allow_out_payment else _('untrusted')
            if self.env.context.get('display_account_trust'):
                acc.display_name = f'{result_name} ({trusted_label})'
            else:
                acc.display_name = result_name
