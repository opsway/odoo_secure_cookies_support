{
    'name': 'Bank account validation on invoice',
    'version': '18.0.1.1.0',
    'summary': 'Bank account validation on invoice',
    'author': 'OpsWay',
    'description': "Validate on posting invoice that recipient bank currency is equal to invoice currency",
    'depends': [
        'base', 'account',
    ],
    'category': 'Tools',
    'sequence': 10,
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'demo': [
        'demo/account_demo.xml',
    ],
    'license': 'LGPL-3'
}
