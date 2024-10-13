from odoo import models, fields, api


class EmployeeBillSignLine(models.Model):
    _name = 'employee.bill.sign.line'
    _description = 'Employee Bill Sign Line'

    move_id = fields.Many2one('account.move', string='Move')

    description = fields.Char(related='move_id.employee_product_tag_id.name')
    period = fields.Char(readonly=True)
    quantity = fields.Float(compute='_compute_quantity', store=True)
    currency_field = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    price = fields.Monetary(currency_field='currency_field')
    amount = fields.Monetary(string='Amount', currency_field='currency_field')


    @api.depends('price', 'amount')
    def _compute_quantity(self):
        for record in self:
            record.quantity = record.price and round(record.amount / record.price, 2) or 0.0
