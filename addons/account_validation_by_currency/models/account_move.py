from odoo import models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _validate_partner_bank_id(self, mass=False):
        invoice_ids = self.filtered(lambda x: x.move_type == 'out_invoice')
        inv_without_bank = invoice_ids.filtered(lambda x: not x.partner_bank_id)
        if inv_without_bank:
            error_msg = "Recipient Bank is not set. Please set the value to proceed with the action."
            error_msg += f"\nFailing record IDs: {inv_without_bank.ids}" if len(inv_without_bank.ids) > 1 or mass \
                else ""
            raise ValidationError(error_msg)

        default_currency = self.env.company.currency_id
        failed_inv = invoice_ids.filtered(
            lambda x: (x.partner_bank_id.currency_id.id or default_currency.id) != x.currency_id.id)
        if failed_inv:
            error_msg = "\n".join(
                f"Recipient Bank Currency {inv.partner_bank_id.currency_id.name or default_currency.name}, "
                f"Invoice Currency {inv.currency_id.name}" for inv in failed_inv)
            error_msg += f"\nFailing record IDs: {failed_inv.ids}" if len(failed_inv.ids) > 1 or mass else ""
            raise ValidationError(f"Currency mismatch:\n{error_msg}")

    def action_post(self):
        if not self.env.context.get('demo'):
            self._validate_partner_bank_id()
        return super().action_post()