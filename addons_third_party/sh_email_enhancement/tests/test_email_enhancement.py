# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'email_enhancement_int576')
class TestEmailEnhancement(TransactionCase):

    def setUp(self):
        super(TestEmailEnhancement, self).setUp()
        self.company = self.env.user.company_id
        self.partner_cc = self.env['res.partner'].create({
            'name': 'CC Test Partner',
            'email': 'cc_test@example.com'
        })
        self.partner_bcc = self.env['res.partner'].create({
            'name': 'BCC Test Partner',
            'email': 'bcc_test@example.com'
        })

    def test_company_cc_bcc_fields(self):
        """Test that company can have CC and BCC fields configured"""
        self.company.write({
            'email_cc_ids': [(6, 0, [self.partner_cc.id])],
            'email_bcc_ids': [(6, 0, [self.partner_bcc.id])]
        })

        self.assertEqual(len(self.company.email_cc_ids), 1)
        self.assertEqual(len(self.company.email_bcc_ids), 1)
        self.assertEqual(
            self.company.email_cc_ids[0].email, 'cc_test@example.com')
        self.assertEqual(
            self.company.email_bcc_ids[0].email, 'bcc_test@example.com')

    def test_mail_message_cc_bcc_fields_exist(self):
        """Test that mail.message has cc_email and bcc_email fields"""
        message = self.env['mail.message'].create({
            'subject': 'Test Message',
            'body': 'Test Body'
        })

        # Check that the fields exist and can be written to
        message.write({
            'cc_email': 'cc_test@example.com',
            'bcc_email': 'bcc_test@example.com'
        })

        self.assertEqual(message.cc_email, 'cc_test@example.com')
        self.assertEqual(message.bcc_email, 'bcc_test@example.com')

    def test_mail_compose_message_default_cc_bcc(self):
        """Test that mail compose message gets default CC/BCC from company"""
        self.company.write({
            'email_cc_ids': [(6, 0, [self.partner_cc.id])],
            'email_bcc_ids': [(6, 0, [self.partner_bcc.id])]
        })

        # Use with_context to ensure we get the defaults
        compose_message = self.env['mail.compose.message'].with_context(
            default_composition_mode='comment'
        ).create({
            'subject': 'Test Subject',
            'body': 'Test Body'
        })

        # Check that default CC/BCC are set
        self.assertIn(self.partner_cc.id, compose_message.email_cc_ids.ids)
        self.assertIn(self.partner_bcc.id, compose_message.email_bcc_ids.ids)
