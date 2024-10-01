from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    bill_name = fields.Char(translate=True)
    bill_street = fields.Char(translate=True)
    bill_street2 = fields.Char(translate=True)
    bill_zip = fields.Char(translate=True)
    bill_city = fields.Char(translate=True)
    bill_state = fields.Char(translate=True)

    def _get_address_data(self):
        self.ensure_one()
        data = [self.country_id.name, self.bill_zip, self.bill_state, self.bill_city, self.bill_street,
                self.bill_street2]
        data = filter(lambda x: x, data)
        return ', '.join(data)
