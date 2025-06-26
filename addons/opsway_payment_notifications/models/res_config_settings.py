from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_notification_enabled = fields.Boolean(
        string='Enable Payment Notifications',
        config_parameter='opsway_payment_notifications.enabled',
        help='Enable email notifications for received payments'
    )