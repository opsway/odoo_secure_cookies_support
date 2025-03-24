from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _validate_partner_bank_id(self):
        invalid_moves = self.filtered(
            lambda move: not move.partner_bank_id
                         or not move.currency_id
                         or move.partner_bank_id.currency_id != move.currency_id)
        if invalid_moves:
            error_messages = "\n".join(
                f"Invoice {move.name}: Recipient bank currency {move.partner_bank_id.currency_id.name or 'is not set'},"
                f" Invoice currency {move.currency_id.name or 'is not set'}"
                for move in invalid_moves)
            raise UserError(f"Currency mismatches:\n{error_messages}")

    def action_post(self):
        self._validate_partner_bank_id()
        return super().action_post()