from datetime import date

from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'int_603_test')
class TestInvoiceToBillLines(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test partner
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'is_company': True,
        })

        # Create test product
        cls.test_product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
            'list_price': 100.0,
        })

        # Create vendor partner for bill
        cls.vendor_partner = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'is_company': True,
            'supplier_rank': 1,
        })

    def test_generate_bill_lines_from_invoices(self):
        """Test generating bill lines from customer invoices"""
        # Create customer invoice for current month
        current_date = date.today()
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.test_partner.id,
            'invoice_date': current_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 150.0,
            })]
        })
        customer_invoice.action_post()

        # Create vendor bill
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': current_date,
        })

        # Test the action
        result = vendor_bill.action_generate_bill_lines_from_invoices()

        # Verify result
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['params']['type'], 'success')

        # Check bill lines were created
        self.assertTrue(vendor_bill.invoice_line_ids)
        bill_line = vendor_bill.invoice_line_ids[0]
        self.assertIn(customer_invoice.name, bill_line.name)
        self.assertIn(self.test_partner.name, bill_line.name)
        self.assertEqual(bill_line.price_unit, customer_invoice.amount_total)

    def test_generate_bill_lines_invalid_move_type(self):
        """Test error when trying to generate lines on non-bill"""
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.test_partner.id,
        })

        with self.assertRaises(UserError):
            customer_invoice.action_generate_bill_lines_from_invoices()

    def test_generate_bill_lines_no_date(self):
        """Test error when no date is selected"""
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': False,
        })

        with self.assertRaises(UserError):
            vendor_bill.action_generate_bill_lines_from_invoices()

    def test_generate_bill_lines_no_invoices(self):
        """Test error when no invoices found for selected month"""
        # Use a date far in the past
        past_date = date(2020, 1, 1)
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': past_date,
        })

        with self.assertRaises(UserError):
            vendor_bill.action_generate_bill_lines_from_invoices()

    def test_partner_fee_product_creation(self):
        """Test creation of Partner fee product when not exists"""
        # Remove any existing Partner fee products
        existing_products = self.env['product.product'].search([
            ('name', 'ilike', 'Partner fee')
        ])
        existing_products.unlink()

        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
        })

        product = vendor_bill._get_or_create_partner_fee_product()
        self.assertEqual(product.name, 'Partner fee')
        self.assertEqual(product.type, 'service')
        self.assertTrue(product.purchase_ok)
        self.assertFalse(product.sale_ok)
