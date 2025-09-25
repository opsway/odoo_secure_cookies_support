{
    'name': 'Opsway Payment Notifications',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Email notifications for received payments',
    'description': """
        Sends email notifications when payments are received on Bank or Cash journals.
        Provides configurable notification settings for all payments or specific partner payments.
    """,
    'author': 'OpsWay',
    'depends': [
        'account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/payment_notification_settings_views.xml',
    ],
    'license': 'Other proprietary',
    'installable': True,
    'application': False,
    'auto_install': False,
}
