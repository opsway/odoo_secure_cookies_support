# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Email Enhancement",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "16.0.3",
    "license": "OPL-1",
    "category": "Extra Tools",
    
    "summary": "Set CC & BCC In Email Module Default CC & BCC On Mail Select CC & BCC For All Mail Email Management With CC & BCC Put Default Mail CC & BCC Email With Permanent CC & BCC Odoo Email BCC Mail BCC Email CC and BCC Default Set Email CC and BCC Default CC Default BCC Default cc on Email Default BCC on Email Compose Email Email Enhancement Odoo Customer Email CC BCC in Odoo Customer in CC Customer in BCC ",
    
    "description": """This module enhances the email sending options by adding CC & BCC by default in odoo. You can select the person in CC & BCC whom you want to send the emails as by default. You can also change CC & BCC when you compose your email.""",

    "depends": ['mail', 'base_setup'],
    "data": [
        "views/res_config_settings.xml",
        "views/mail_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'sh_email_enhancement/static/src/xml/**/*',
            'sh_email_enhancement/static/src/models/*/*.js',
        ],
    },
    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/4Biinb-XjyA",
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": "33.5",
    "currency": "EUR"
}
