{
    'name': 'Set default Recipient Bank Account for Customer',
    'version': '19.0.1.0.0',
    'summary': '',
    'author': 'OpsWay',
    'description': "Populate Invoice default Recipient Bank from linked Customer",
    'depends': [
        'account',
    ],
    'category': 'Tools',
    'sequence': 10,
    'data': [
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}
