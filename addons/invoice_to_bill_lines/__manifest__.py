{
    'name': 'Invoice to Bill Lines',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Transform invoices into bill lines based on monthly selection',
    'description': """
        This module adds functionality to transform customer invoices into vendor bill lines.
        It adds:
        - Date field for month selection
        - Button to generate bill lines from invoices
        - Automatic creation of bill lines with customer name and invoice number
        - Uses 'Partner fee' product for bill lines if available
    """,
    'author': 'AI Agent (OpsWay)',
    'website': 'https://opsway.com',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
