{
    'name': 'Opsway Employee Bill',
    'version': '17.0.0.9.0',
    'category': 'Accounting/Accounting',
    'summary': 'Bill Report for Opsway',
    'description': 'Bill report for employee',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'report/opsway_employee_bill_template.xml',
    ],
    'license': 'Other proprietary',
    'installable': True,
    'application': True,
}
