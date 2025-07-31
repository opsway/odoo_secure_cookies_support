import calendar
from datetime import datetime

from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_date_filter = fields.Date(
        string='Invoice Date Filter',
        help='Select date to filter invoices for the same month',
        default=fields.Date.context_today
    )

    bill_line_quantity = fields.Float(
        string='Bill Line Quantity',
        help='Quantity to be used for all generated bill lines',
        default=1.0
    )

    def action_generate_bill_lines_from_invoices(self):
        """Generate bill lines from customer invoices for the selected month"""
        if self.move_type not in ['in_invoice', 'in_refund']:
            raise UserError(
                _('This action is only available on vendor bills.'))

        if not self.invoice_date_filter:
            raise UserError(_('Please select a date to filter invoices.'))

        # Get month and year from selected date
        selected_date = self.invoice_date_filter
        year = selected_date.year
        month = selected_date.month

        # Get first and last day of the month
        first_day = datetime(year, month, 1).date()
        last_day = datetime(
            year, month, calendar.monthrange(year, month)[1]).date()

        # Find all customer invoices in the selected month (excluding credit notes)
        customer_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', first_day),
            ('invoice_date', '<=', last_day),
        ])

        if not customer_invoices:
            raise UserError(
                _('No customer invoices found for %s/%s.') % (month, year))

        # Get or create Partner fee product
        partner_fee_product = self._get_or_create_partner_fee_product()

        # Clear existing invoice lines except the first one (if any)
        existing_lines = self.invoice_line_ids.filtered(
            lambda line: not line.display_type)
        if len(existing_lines) > 1:
            existing_lines[1:].unlink()

        # Create bill lines for each invoice
        bill_lines_data = []
        for invoice in customer_invoices:
            # Use parent company name if available, otherwise use partner name
            customer_name = (invoice.partner_id.parent_id.name
                             if invoice.partner_id.parent_id
                             else invoice.partner_id.name)

            line_data = {
                'product_id': partner_fee_product.id,
                'name': _('Invoice %s - %s') % (invoice.name, customer_name),
                'quantity': self.bill_line_quantity,
                'price_unit': invoice.amount_total_signed,
                'account_id': partner_fee_product.property_account_expense_id.id or
                partner_fee_product.categ_id.property_account_expense_categ_id.id,
            }
            bill_lines_data.append((0, 0, line_data))

        # Update the bill with new lines
        if existing_lines:
            # If there's already a line, replace it
            existing_lines[0].unlink()

        self.write({'invoice_line_ids': bill_lines_data})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Generated %d bill lines from customer invoices for %s/%s.') % (
                    len(customer_invoices), month, year
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_or_create_partner_fee_product(self):
        """Get Partner fee product or create a default one"""
        # Try to find existing "Partner fee" product
        partner_fee_product = self.env['product.product'].search([
            ('name', 'ilike', 'Partner fee')
        ], limit=1)

        if partner_fee_product:
            return partner_fee_product

        # Create default product if not found
        product_category = self.env['product.category'].search([
            ('name', '=', 'All')
        ], limit=1)

        if not product_category:
            product_category = self.env['product.category'].search([], limit=1)

        partner_fee_product = self.env['product.product'].create({
            'name': 'Partner fee',
            'type': 'service',
            'categ_id': product_category.id if product_category else False,
            'list_price': 0.0,
            'purchase_ok': True,
            'sale_ok': False,
        })

        return partner_fee_product
