import inspect
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.addons.opsway_payment_notifications.models.account_move import AccountMove


@tagged('post_install', '-at_install', 'payment_notifications_test_ai_564', 'all_run')
class TestPaymentNotifications(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Enable payment notifications
        cls.env['ir.config_parameter'].sudo().set_param(
            'opsway_payment_notifications.enabled', True
        )

        # Create test users
        cls.test_user_1 = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Test User 1',
            'login': 'testuser1',
            'email': 'testuser1@example.com',
        })
        cls.test_user_2 = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Test User 2',
            'login': 'testuser2',
            'email': 'testuser2@example.com',
        })

        # Create test partner
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'testpartner@example.com',
        })

        # Create bank journal and account
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Test Bank',
            'type': 'bank',
            'code': 'TBNK',
        })

        # Create cash journal
        cls.cash_journal = cls.env['account.journal'].create({
            'name': 'Test Cash',
            'type': 'cash',
            'code': 'TCSH',
        })

        # Create sale journal for invoice test
        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Test Sale',
            'type': 'sale',
            'code': 'TSALE',
        })

        # Create accounts for testing
        cls.bank_account = cls.env['account.account'].create({
            'name': 'Test Bank Account',
            'code': 'TBANK001',
            'account_type': 'asset_cash',
        })
        cls.income_account = cls.env['account.account'].create({
            'name': 'Test Income Account',
            'code': 'TINC001',
            'account_type': 'income',
        })

        # Set default account for bank journal
        cls.bank_journal.default_account_id = cls.bank_account
        cls.cash_journal.default_account_id = cls.bank_account

        # Create notification settings
        cls.all_payments_setting = cls.env['payment.notification.settings'].create({
            'name': 'All Payments Notification',
            'notification_type': 'all_payments',
            'all_payment_user_ids': [(6, 0, [cls.test_user_1.id])],
        })

        cls.partner_specific_setting = cls.env['payment.notification.settings'].create({
            'name': 'Partner Specific Notification',
            'notification_type': 'partner_specific',
            'partner_specific_user_ids': [(6, 0, [cls.test_user_2.id])],
            'partner_ids': [(6, 0, [cls.test_partner.id])],
        })

    def test_should_send_notification_bank_journal(self):
        """Test that bank journal entries with debit should trigger notifications."""
        move = self.env['account.move'].create({
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.bank_account.id,
                    'debit': 1000.0,
                    'partner_id': self.test_partner.id,
                }),
                (0, 0, {
                    'account_id': self.income_account.id,
                    'credit': 1000.0,
                }),
            ],
        })

        self.assertTrue(move._should_send_payment_notification())

    def test_should_send_notification_cash_journal(self):
        """Test that cash journal entries with debit should trigger notifications."""
        move = self.env['account.move'].create({
            'journal_id': self.cash_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.bank_account.id,
                    'debit': 500.0,
                }),
                (0, 0, {
                    'account_id': self.income_account.id,
                    'credit': 500.0,
                }),
            ],
        })

        self.assertTrue(move._should_send_payment_notification())

    def test_should_not_send_notification_invoice(self):
        """Test that invoices should not trigger notifications."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.sale_journal.id,
            'partner_id': self.test_partner.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Test Product',
                    'price_unit': 100.0,
                    'account_id': self.income_account.id,
                }),
            ],
        })

        self.assertFalse(move._should_send_payment_notification())

    def test_should_not_send_notification_no_debit(self):
        """Test that entries without debit on bank account should not trigger notifications."""
        move = self.env['account.move'].create({
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.bank_account.id,
                    'credit': 1000.0,
                }),
                (0, 0, {
                    'account_id': self.income_account.id,
                    'debit': 1000.0,
                }),
            ],
        })

        self.assertFalse(move._should_send_payment_notification())

    def test_get_notification_users_all_payments(self):
        """Test getting users for all payments notifications."""
        users = self.env['payment.notification.settings'].get_notification_users()
        self.assertIn(self.test_user_1, users)

    def test_get_notification_users_partner_specific(self):
        """Test getting users for partner-specific notifications."""
        users = self.env['payment.notification.settings'].get_notification_users(
            partner_id=self.test_partner.id
        )
        self.assertIn(self.test_user_1, users)  # From all payments
        self.assertIn(self.test_user_2, users)  # From partner specific

    @patch('odoo.addons.opsway_payment_notifications.models.account_move.AccountMove._send_payment_notification')
    def test_action_post_triggers_notification(self, mock_send):
        """Test that posting a qualifying move triggers notification."""
        move = self.env['account.move'].create({
            'journal_id': self.bank_journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.bank_account.id,
                    'debit': 1000.0,
                    'partner_id': self.test_partner.id,
                }),
                (0, 0, {
                    'account_id': self.income_account.id,
                    'credit': 1000.0,
                }),
            ],
        })

        move.action_post()
        mock_send.assert_called_once()

    def test_notification_disabled_no_trigger(self):
        """Test that notifications are not sent when no active settings exist."""
        # Disable all notification settings
        self.env['payment.notification.settings'].search(
            []).write({'active': False})

        with patch(
            'odoo.addons.opsway_payment_notifications.models.'
            'account_move.AccountMove._send_payment_notification'
        ) as mock_send:
            move = self.env['account.move'].create({
                'journal_id': self.bank_journal.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': self.bank_account.id,
                        'debit': 1000.0,
                    }),
                    (0, 0, {
                        'account_id': self.income_account.id,
                        'credit': 1000.0,
                    }),
                ],
            })

            move.action_post()
            mock_send.assert_not_called()

        # Re-enable for other tests
        self.env['payment.notification.settings'].search(
            []).write({'active': True})

    def test_email_layout_parameter_correct(self):
        """Test that the fixed code doesn't contain the old notif_layout parameter."""
        # Check the source code doesn't contain the problematic parameter
        source = inspect.getsource(AccountMove._send_payment_notification)

        # Verify the fix: email_layout_xmlid should be present, notif_layout should not
        self.assertIn('email_layout_xmlid', source)
        self.assertNotIn('notif_layout', source)
