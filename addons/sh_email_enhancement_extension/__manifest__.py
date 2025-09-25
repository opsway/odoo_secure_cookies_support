{
    'name': 'Email Enhancement Invoice Extension',
    'version': '19.0.1.0',
    'author': 'OpsWay',
    "description": "Email Enhancement for Invoices wizard",
    'license': "Other proprietary",
    'depends': [
        'account',
        'mail',
        'sh_email_enhancement',
    ],
    'data': [
        'wizard/account_invoice_send_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
