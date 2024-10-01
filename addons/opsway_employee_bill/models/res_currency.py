from odoo import models, fields

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    currency_unit_label = fields.Char(string="Currency Unit", translate=True)
    currency_subunit_label = fields.Char(string="Currency Subunit", translate=True)
