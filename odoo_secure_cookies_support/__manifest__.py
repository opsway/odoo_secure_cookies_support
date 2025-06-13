{
    'name': "Secure Cookies Support",
    'version': "17.0.0.1.0",
    'summary': "Secure Cookies Support",
    'description': "Secure Cookies Support",
    'author': "Lumirang",
    'website': "https://lumirang.com",
    'category': "Quality",
    'license': "Other proprietary",
    'depends': ['web'],
    'data': [
        'data/ir_config_parameter.xml',
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_secure_cookies_support/static/src/js/core/browser/cookie.js',
        ],
        'web.assets_frontend': [
            'odoo_secure_cookies_support/static/src/js/core/browser/cookie.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 5,
}
