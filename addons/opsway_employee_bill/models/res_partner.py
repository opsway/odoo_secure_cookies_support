from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    bill_name = fields.Char(translate=True)

    name = fields.Char(translate=True, tracking=True, index=True, default_export_compatible=True)
    city = fields.Char(translate=True)
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)

    def _get_address_data(self):
        self.ensure_one()
        data = [self.country_id.name, self.zip, self.state_id.name, self.city, self.street,
                self.street2]
        data = filter(lambda x: x, data)
        return ', '.join(data)


class CountryState(models.Model):
    _inherit = 'res.country.state'

    name = fields.Char(
        string='State Name', required=True,
        translate=True,
        help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton',
    )
