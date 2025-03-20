from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_terms = fields.Text(string="Default Terms and Conditions", translate=True)
    name = fields.Char(related='partner_id.name', string='Company Name', required=True, store=True, readonly=False,
                       translate=False)

    def _get_address_data(self):
        self.ensure_one()
        data = [self.partner_id.country_id.name, self.partner_id.zip, self.partner_id.state_id.name,
                self.partner_id.city, self.partner_id.street]
        data = filter(lambda x: x, data)
        return ', '.join(data)
