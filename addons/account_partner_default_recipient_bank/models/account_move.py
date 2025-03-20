from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('bank_partner_id', 'partner_id')
    def _compute_partner_bank_id(self):
        moves_with_defaults = self.filtered(lambda x: x.partner_id and x.partner_id.partner_bank_id)
        for move in moves_with_defaults:
            move.partner_bank_id = move.partner_id.partner_bank_id
        super(AccountMove, self - moves_with_defaults)._compute_partner_bank_id()
