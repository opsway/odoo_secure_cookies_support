{
    'name': 'Account Analytic Percentage',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Calculate percentage of analytical plan on bills',
    'description': """
        This module adds functionality to calculate the percentage of a particular
        analytical plan on vendor bills. It adds two fields:
        - Analytical plan selection
        - Calculated percentage based on analytical entries
    """,
    'author': 'Ed Chu (OpsWay)',
    'website': 'https://opsway.com',
    'depends': [
        'account',
        'analytic',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}