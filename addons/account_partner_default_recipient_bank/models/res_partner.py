from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_bank_id = fields.Many2one('res.partner.bank',
            string='Recipient Bank',
            help="Bank Account Number to which the invoice for this Customer will be paid by default",
            company_dependent=True,
            tracking=True,
            domain=lambda record: [('id', 'in', record.env.company.bank_ids.ids)]
        )
