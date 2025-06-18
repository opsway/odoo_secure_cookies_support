from odoo.exceptions import ValidationError
from odoo.tests import tagged, common
from datetime import datetime


@tagged('post_install', '-at_install')
class TestAccountMoveCurrency(common.TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.env.ref('base.EUR').active = True
        self.bank_eur = self.env['res.partner.bank'].create({
            'acc_number': 'Test_Bank_EUR',
            'partner_id': self.env.ref('base.main_partner').id,
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
        })
        self.bank_usd = self.env['res.partner.bank'].create({
            'acc_number': 'Test_Bank_USD',
            'partner_id': self.env.ref('base.main_partner').id,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.env.company.id,
        })

        Invoice = self.env['account.move']
        self.invoice = Invoice.create({
            'move_type': 'out_invoice',
            'state': 'draft',
            'partner_id': self.env.ref('base.res_partner_1').id,
            'currency_id': self.env.ref('base.USD').id,
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
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')

    def test_default_currency(self):
        self.bank_eur.currency_id = False
        self.invoice.partner_bank_id = self.bank_eur.id
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')
