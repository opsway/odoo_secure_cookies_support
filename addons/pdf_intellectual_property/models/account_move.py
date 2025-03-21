from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    intellectual_property = fields.Boolean()
