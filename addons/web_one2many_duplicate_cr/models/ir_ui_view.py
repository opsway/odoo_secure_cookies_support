from odoo import models, api


class Model(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_view_field_attributes(self):
        attributes = super()._get_view_field_attributes()
        if 'copy' not in attributes:
            attributes.append('copy')
        return attributes
