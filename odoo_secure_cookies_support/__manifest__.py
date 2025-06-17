{
    'name': "Secure Cookies Support",
    'version': "17.0.1.0.0",
    'summary': "Secure Cookies Support",
    'description': "Adds the Secure flag to every session and CSRF cookie served by Odoo",
    'author': "OpsWay",
    'website': "https://opsway.com",
    'category': "Quality",
    'license': "LGPL-3",
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
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
