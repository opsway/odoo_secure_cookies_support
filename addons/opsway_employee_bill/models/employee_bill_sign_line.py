from odoo import models, fields, api


class EmployeeBillSignLine(models.Model):
    _name = 'employee.bill.sign.line'
    _description = 'Employee Bill Sign Line'

    move_id = fields.Many2one('account.move', string='Move')

    description = fields.Char()
    period = fields.Char(readonly=True)
    quantity = fields.Float(compute='_compute_quantity', store=True)
    currency_field = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    price = fields.Monetary(currency_field='currency_field')
    amount = fields.Monetary(string='Amount', currency_field='currency_field')

    def _get_report_description(self):
        self.ensure_one()
        report_description = ''
        if self.move_id.employee_product_tag_id:
            report_description = self.move_id.employee_product_tag_id.name
        elif self.move_id.employee_bill_first_line_id:
            report_description = self.move_id.employee_bill_first_line_id.product_id.name or ''
        return report_description

    @api.depends('price', 'amount')
    def _compute_quantity(self):
        for record in self:
            record.quantity = record.price and round(record.amount / record.price, 2) or 0.0
