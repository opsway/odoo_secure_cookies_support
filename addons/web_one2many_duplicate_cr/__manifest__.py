{
    'name': "One2Many Duplicate Records",
    'summary': """One2Many Duplicate Records""",
    'description': """This module helps you to duplicate records in One2many line for Quotation,\
    Sale Order, Invoice etc.""",
    'author': 'OpsWay',
    'category': 'Extra Tools',
    'version': '18.0.1.0.0',
    'depends': ['web', 'sale'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'web_one2many_duplicate_cr/static/src/views/list/list_renderer.js',
            ('after', 'web/static/src/views/list/list_renderer.xml',
             'web_one2many_duplicate_cr/static/src/views/list/list_renderer.xml'),
            'web_one2many_duplicate_cr/static/src/views/fields/x2many/x2many_field.js',
            'web_one2many_duplicate_cr/static/src/views/list/',
            'web_one2many_duplicate_cr/static/src/model/relational_model/static_list.js',
            'web_one2many_duplicate_cr/static/src/main.js',
        ],
        'web.assets_qweb': [
            'web_one2many_duplicate_cr/static/src/views/list/list_renderer.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
