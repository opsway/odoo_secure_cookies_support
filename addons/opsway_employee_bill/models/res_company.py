from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_terms = fields.Text(string="Default Terms and Conditions", translate=True)
