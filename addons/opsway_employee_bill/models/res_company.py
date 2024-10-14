from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_terms = fields.Text(string="Default Terms and Conditions", translate=True)
    name = fields.Char(related='partner_id.name', string='Company Name', required=True, store=True, readonly=False,
                       translate=True)
