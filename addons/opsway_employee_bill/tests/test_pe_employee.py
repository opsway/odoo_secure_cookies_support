from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPEEmployee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
        Create a partner, product and invoice for testing. Add translation to the partner in ukrainian.
        """
        super().setUpClass()
        lang = cls.env.ref('base.lang_uk_UA')
        lang._activate_lang(lang.code)
        cls.lang = lang

        cls.partner_ua = cls.env['res.partner'].create(
            {'name': 'Test Partner UA', 'lang': lang.code, 'street': 'Test Street',
             'city': 'Test City', 'zip': '12345',
             'country_id': cls.env.ref('base.ua').id})
        cls.partner_ua.update_field_translations('name', {lang.code: 'Тестовий Партнер'})
        cls.partner_ua.update_field_translations('street', {lang.code: 'Тестова Вулиця'})
        cls.partner_ua.update_field_translations('city', {lang.code: 'Тестове Місто'})
        cls.partner_ua.update_field_translations('zip', {lang.code: '12345'})
        cls.bank_account = cls.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'partner_id': cls.partner_ua.id,
            'bank_name': 'Test Bank',
            'bank_bic': '123456789',
            'bank_id': cls.env.ref('base.res_bank_1').id
        })
        cls.env.company.partner_id.write({
            'name': 'Test Company',
            'street': 'Test Street',
            'city': 'Test City',
            'street2': 'Name of Company',
        })
        cls.env.company.partner_id.update_field_translations('name', {lang.code: 'Тестова Компанія'})
        cls.env.company.partner_id.update_field_translations('street', {lang.code: 'Тестова Вулиця'})
        cls.env.company.partner_id.update_field_translations('city', {lang.code: 'Тестове Місто'})
        cls.env.company.partner_id.update_field_translations('street2', {lang.code: 'Назва Компанії'})
        cls.env.company.default_terms = 'Default Terms and Conditions in English'
        cls.env.company.update_field_translations('default_terms', {lang.code: 'Типові умови українською'})
        cls.partner_en = cls.env['res.partner'].create({'name': 'Test Partner EN', 'lang': 'en_US'})
        cls.product_tag_pe = cls.env['product.tag'].create({'name': 'Personal Employee'})
        cls.product_tag_pe.update_field_translations('name', {lang.code: 'ФОП'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
            'product_tag_ids': [(6, 0, [cls.product_tag_pe.id])]
        })
        cls.product.update_field_translations('name', {lang.code: 'Тестовий Продукт'})
        cls.product_secondary = cls.env['product.product'].create({
            'name': 'Test Product Secondary',
            'type': 'service',
        })

        cls.invoice_date = date(2024, 5, 15)
        cls.invoice_ua = cls.env['account.move'].create({
            'partner_id': cls.partner_ua.id,
            'move_type': 'in_invoice',
            'invoice_date': cls.invoice_date,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 20,
                'price_unit': 100
            }), (0, 0, {
                'product_id': cls.product_secondary.id,
                'quantity': 1,
                'price_unit': 200.5,
            })],
        })

    def test_employee_bill_sign_creation(self):
        """Test if Bill Sign lines are created correctly."""
        self.invoice_ua.action_post()
        self.assertTrue(self.invoice_ua.employee_bill_sign_ids)
        bill_line = self.invoice_ua.employee_bill_sign_ids[0]
        self.assertEqual(bill_line.description, self.product.with_context(lang=self.lang.code).product_tag_ids[0].name)
        self.assertEqual(bill_line.period,
                         self.invoice_ua.with_context(lang=self.lang.code)._get_vendor_invoice_period())
        self.assertEqual(bill_line.price, 100)
        self.assertEqual(bill_line.quantity, 25.31)
        self.assertEqual(bill_line.amount, 2530.58)

    def test_biilang_employee_bill_report(self):
        """Report create: English + Ukrainian; English."""
        self.invoice_ua.action_post()

        report_en = self.env['ir.actions.report']._render_qweb_pdf(
            'opsway_employee_bill.report_opsway_employee_bill_template', [self.invoice_ua.id], data=None)
        # check partner data in report
        self.assertIn(b'Test Partner', report_en[0], "English content not found in English report")
        self.assertIn('Тестовий Партнер'.encode('utf-8'), report_en[0],
                      "Ukrainian content not found in Ukrainian report")
        self.assertIn(b'Test Street', report_en[0], "English address not found in English report")
        self.assertIn('Тестова Вулиця'.encode('utf-8'), report_en[0], "Ukrainian address not found in Ukrainian report")
        self.assertIn(b'Test City', report_en[0], "English city not found in English report")
        self.assertIn('Тестове Місто'.encode('utf-8'), report_en[0], "Ukrainian city not found in Ukrainian report")
        self.assertIn(b'12345', report_en[0], "English zip not found in English report")
        self.assertIn('12345'.encode('utf-8'), report_en[0], "Ukrainian zip not found in Ukrainian report")
        # check company data in report
        self.assertIn(b'Test Company', report_en[0], "English company name not found in English report")
        self.assertIn('Тестова Компанія'.encode('utf-8'), report_en[0],
                      "Ukrainian company name not found in Ukrainian report")
        self.assertIn(b'Test Street', report_en[0], "English company street not found in English report")
        self.assertIn('Тестова Вулиця'.encode('utf-8'), report_en[0],
                      "Ukrainian company street not found in Ukrainian report")
        self.assertIn(b'Name of Company', report_en[0], "English company street2 not found in English report")
        self.assertIn('Назва Компанії'.encode('utf-8'), report_en[0],
                      "Ukrainian company street2 not found in Ukrainian report")
        self.assertIn(b'Personal Employee', report_en[0], "English product name not found in English report")
        self.assertIn('ФОП'.encode('utf-8'), report_en[0],
                      "Ukrainian product name not found in Ukrainian report")
        # check invoice data in report
        self.assertIn(b'May 15, 2024', report_en[0], "Invoice date not found in report")
        self.assertIn(b'2530.58', report_en[0], "Total amount not found in report")
        self.assertIn(b'Total: Two thousand five hundred and thirty dollars and fifty-eight cents', report_en[0],
                      "Total amount in words not found in report")
        self.assertIn('Total: Двi тисячi п&#39;ятсот тридцять dollars і п&#39;ятдесят вiсiм cents'.encode('utf-8'),
                      report_en[0],
                      "Total amount in words not found in report")
        # check bank account in report
        self.assertIn(b'123456789', report_en[0], "Bank account not found in report")
        self.assertIn(b'Test Bank', report_en[0], "Bank name not found in report")
        self.assertIn(b'123456789', report_en[0], "Bank BIC not found in report")
        # check bill sign description in report
        self.assertIn(self.invoice_ua.name.replace('BILL/', '').encode('utf-8'), report_en[0],
                      "Invoice name not found in report")
        self.assertIn(self.invoice_ua.with_context(lang=self.lang.code).name.replace('BILL/', '').encode('utf-8'),
                      report_en[0],
                      "Invoice name not found in report")

    def test_get_vendor_invoice_date(self):
        """Test _get_vendor_invoice_date method."""
        expected_date = "May 15, 2024"
        self.assertEqual(self.invoice_ua._get_vendor_invoice_date(), expected_date)

    def test_get_vendor_invoice_period(self):
        """Test _get_vendor_invoice_period method."""
        expected_period = "May 2024"
        self.assertEqual(self.invoice_ua._get_vendor_invoice_period(), expected_period)

    def test_get_total_amount_in_word_pe(self):
        """Test _get_total_amount_in_word_pe method."""
        expected_text = "Two thousand five hundred and thirty dollars and fifty-eight cents"
        self.assertEqual(self.invoice_ua._get_total_amount_in_word_pe(), expected_text)

    def test_get_pe_report_filename(self):
        """Test _get_pe_report_filename method."""
        expected_filename = "Invoice_Test Partner UA_05/24"  # Format: Invoice_<Vendor>_MM/YY
        self.assertEqual(self.invoice_ua._get_pe_report_filename(), expected_filename)

    def test_get_report_description(self):
        """Test _get_report_description method."""
        self.invoice_ua.action_post()
        self.assertTrue(len(self.invoice_ua.employee_bill_sign_ids) == 1, "Bill Sign lines not created.")
        self.assertEqual(self.invoice_ua.employee_bill_sign_ids[0].description, "ФОП",
                         "Report description is incorrect.")
        self.assertEqual(
            self.invoice_ua.with_context(lang=self.lang.code).employee_bill_sign_ids[0]._get_report_description(),
            "ФОП", "Report description is incorrect.")

    def test_company_get_address_data(self):
        """Test _get_address_data method to ensure proper address formatting."""
        expected_address = "United States, 94134, California, Test City, Test Street"
        actual_address = self.invoice_ua.company_id._get_address_data()
        self.assertEqual(actual_address, expected_address, "Address data format is incorrect.")

    def test_default_terms_translation(self):
        """Test that default_terms field supports translation."""

        self.assertEqual(self.invoice_ua.company_id.with_context(lang='en_US').default_terms,
                         "Default Terms and Conditions in English",
                         "Default terms in English do not match expected value.")

        self.assertEqual(self.invoice_ua.company_id.with_context(lang='uk_UA').default_terms,
                         "Типові умови українською",
                         "Default terms in Ukrainian do not match expected value.")

    def test_partner_get_address_data(self):
        """Test _get_address_data method to ensure proper address formatting."""
        expected_address = "Ukraine, 12345, Test City, Test Street"
        actual_address = self.partner_ua._get_address_data()
        self.assertEqual(actual_address, expected_address, "Address data format is incorrect.")
