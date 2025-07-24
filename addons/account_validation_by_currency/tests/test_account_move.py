from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.tests import tagged, common


@tagged('post_install', '-at_install')
class TestAccountMoveCurrency(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.ref('base.EUR').active = True
        cls.bank_eur = cls.env['res.partner.bank'].create({
            'acc_number': 'Test_Bank_EUR',
            'partner_id': cls.env.ref('base.main_partner').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'company_id': cls.env.company.id,
        })
        cls.bank_usd = cls.env['res.partner.bank'].create({
            'acc_number': 'Test_Bank_USD',
            'partner_id': cls.env.ref('base.main_partner').id,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.env.company.id,
        })

        Invoice = cls.env['account.move']
        cls.invoice = Invoice.create({
            'move_type': 'out_invoice',
            'state': 'draft',
            'partner_id': cls.env.ref('base.main_partner').id,
            'currency_id': cls.env.ref('base.USD').id,
            'invoice_date': datetime.today().date(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Demo product line',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })

    def test_invoice_smoke(self):
        self.invoice.partner_bank_id = self.bank_usd.id
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')

    def test_invoice_empty_partner_bank_id(self):
        self.invoice.partner_bank_id = False
        with self.assertRaises(ValidationError):
            self.invoice.action_post()

    def test_invoice_currency_mismatch(self):
        self.invoice.partner_bank_id = self.bank_eur.id
        with self.assertRaises(ValidationError):
            self.invoice.action_post()

    def test_invoice_multi_currency(self):
        self.env.ref('base.EUR').active = False
        self.invoice.partner_bank_id = self.bank_eur.id
        with self.assertRaises(ValidationError):
            self.invoice.action_post()

    def test_default_currency(self):
        self.bank_eur.currency_id = False
        self.invoice.partner_bank_id = self.bank_eur.id
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')
