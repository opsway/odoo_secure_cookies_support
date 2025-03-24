from odoo import models


class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        move_ids = result.get('move_ids', [(None, None, [])])[0][2]
        if move_ids:
            self.env['account.move'].browse(move_ids)._validate_partner_bank_id()
        return result
