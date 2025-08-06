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

        # Create parent company for testing company name logic
        cls.parent_company = cls.env['res.partner'].create({
            'name': 'X Inc',
            'is_company': True,
        })

        # Create child partner under parent company
        cls.child_partner = cls.env['res.partner'].create({
            'name': 'John Doe',
            'parent_id': cls.parent_company.id,
            'is_company': False,
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
        self.assertEqual(bill_line.price_unit,
                         customer_invoice.amount_total_signed)

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

    def test_credit_notes_excluded(self):
        """Test that credit notes (out_refund) are excluded from bill line generation"""
        # Use specific date to avoid conflicts
        test_date = date(2049, 12, 15)

        # Create regular customer invoice
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.test_partner.id,
            'invoice_date': test_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 150.0,
            })]
        })
        customer_invoice.action_post()

        # Create credit note for same month
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.test_partner.id,
            'invoice_date': test_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 50.0,
            })]
        })
        credit_note.action_post()

        # Create vendor bill
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': test_date,
        })

        # Generate bill lines
        vendor_bill.action_generate_bill_lines_from_invoices()

        # Verify only one line was created (from invoice, not credit note)
        self.assertEqual(len(vendor_bill.invoice_line_ids), 1)
        bill_line = vendor_bill.invoice_line_ids[0]

        # Verify it's from the invoice, not the credit note
        self.assertIn(customer_invoice.name, bill_line.name)
        self.assertEqual(bill_line.price_unit,
                         customer_invoice.amount_total_signed)

        # Verify credit note is not included
        self.assertNotIn(credit_note.name, bill_line.name)

    def test_custom_bill_line_quantity(self):
        """Test using custom quantity for bill lines"""
        # Use a specific date far in the future to avoid conflicts with existing invoices
        test_date = date(2050, 1, 15)

        # Create customer invoice
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.test_partner.id,
            'invoice_date': test_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })]
        })
        customer_invoice.action_post()

        # Create vendor bill with custom quantity
        custom_quantity = 2.5
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': test_date,
            'bill_line_quantity': custom_quantity,
        })

        # Generate bill lines
        vendor_bill.action_generate_bill_lines_from_invoices()

        # Verify quantity is used correctly
        self.assertEqual(len(vendor_bill.invoice_line_ids), 1)
        bill_line = vendor_bill.invoice_line_ids[0]
        self.assertEqual(bill_line.quantity, custom_quantity)

    def test_amount_total_signed_usage(self):
        """Test that amount_total_signed is used for bill line value"""
        test_date = date(2051, 3, 20)

        # Create customer invoice
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.test_partner.id,
            'invoice_date': test_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })]
        })
        customer_invoice.action_post()

        # Create vendor bill
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': test_date,
        })

        # Generate bill lines
        vendor_bill.action_generate_bill_lines_from_invoices()

        # Verify amount_total_signed is used
        bill_line = vendor_bill.invoice_line_ids[0]
        self.assertEqual(bill_line.price_unit,
                         customer_invoice.amount_total_signed)

    def test_parent_company_name_usage(self):
        """Test that parent company name is used when available"""
        test_date = date(2052, 6, 10)

        # Create customer invoice with child partner (has parent company)
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.child_partner.id,
            'invoice_date': test_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })]
        })
        customer_invoice.action_post()

        # Create vendor bill
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': test_date,
        })

        # Generate bill lines
        vendor_bill.action_generate_bill_lines_from_invoices()

        # Verify parent company name is used
        bill_line = vendor_bill.invoice_line_ids[0]
        # Should contain "X Inc"
        self.assertIn(self.parent_company.name, bill_line.name)
        # Should not contain "John Doe"
        self.assertNotIn(self.child_partner.name, bill_line.name)

    def test_no_parent_company_fallback(self):
        """Test fallback to partner name when no parent company exists"""
        test_date = date(2053, 9, 25)

        # Create customer invoice with regular partner (no parent)
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.test_partner.id,
            'invoice_date': test_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.test_product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })]
        })
        customer_invoice.action_post()

        # Create vendor bill
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor_partner.id,
            'invoice_date_filter': test_date,
        })

        # Generate bill lines
        vendor_bill.action_generate_bill_lines_from_invoices()

        # Verify partner name is used (fallback)
        bill_line = vendor_bill.invoice_line_ids[0]
        # Should contain "Test Customer"
        self.assertIn(self.test_partner.name, bill_line.name)
