# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    email_cc_ids = fields.Many2many(
        'res.partner', 'config_cc_partner_rel', 'partner_id', 'company_id', string="Default CC")
    email_bcc_ids = fields.Many2many(
        'res.partner', 'config_bcc_partner_rel', 'partner_id', 'company_id', string="Default BCC")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_cc_ids = fields.Many2many(
        'res.partner', related="company_id.email_cc_ids", readonly=False, string="Default CC")
    email_bcc_ids = fields.Many2many(
        'res.partner', related="company_id.email_bcc_ids", readonly=False, string="Default BCC")
