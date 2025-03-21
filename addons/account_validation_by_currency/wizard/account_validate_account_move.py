from odoo import models


class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        self.env['account.move'].browse(result['move_ids'][0][2])._validate_partner_bank_id()
        return result
