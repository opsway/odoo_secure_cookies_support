from odoo import models, fields, api


class PaymentNotificationSettings(models.Model):
    _name = 'payment.notification.settings'
    _description = 'Payment Notification Settings'

    name = fields.Char(string='Setting Name', required=True)
    notification_type = fields.Selection([
        ('all_payments', 'All Payments'),
        ('partner_specific', 'Partner Specific')
    ], string='Notification Type', required=True, default='all_payments')
    
    # For all payments notifications
    all_payment_user_ids = fields.Many2many(
        'res.users',
        'payment_notification_all_users_rel',
        'setting_id',
        'user_id',
        string='Users for All Payments'
    )
    
    # For partner-specific notifications
    partner_specific_user_ids = fields.Many2many(
        'res.users',
        'payment_notification_partner_users_rel',
        'setting_id',
        'user_id',
        string='Users for Partner Payments'
    )
    partner_ids = fields.Many2many(
        'res.partner',
        'payment_notification_partners_rel',
        'setting_id',
        'partner_id',
        string='Partners'
    )
    
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)

    @api.model
    def get_notification_users(self, partner_id=None):
        """Get users who should receive notifications for a payment."""
        users = self.env['res.users']
        
        # Get users for all payments
        all_payment_settings = self.search([
            ('notification_type', '=', 'all_payments'),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id)
        ])
        for setting in all_payment_settings:
            users |= setting.all_payment_user_ids
        
        # Get users for partner-specific payments
        if partner_id:
            partner_settings = self.search([
                ('notification_type', '=', 'partner_specific'),
                ('active', '=', True),
                ('company_id', '=', self.env.company.id),
                ('partner_ids', 'in', [partner_id])
            ])
            for setting in partner_settings:
                users |= setting.partner_specific_user_ids
        
        return users