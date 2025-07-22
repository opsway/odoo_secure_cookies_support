import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override to send payment notifications after posting."""
        result = super().action_post()

        # Check if there are active notification settings
        notification_settings = self.env['payment.notification.settings'].search([
            ('active', '=', True),
            ('company_id', '=', self.env.company.id)
        ])

        if not notification_settings:
            return result

        for move in self:
            if move._should_send_payment_notification():
                move._send_payment_notification()

        return result

    def _should_send_payment_notification(self):
        """Check if this move should trigger a payment notification."""
        # Must be a journal entry (not invoice, bill, etc.)
        if self.move_type != 'entry':
            return False

        # Journal must be Bank or Cash type
        if self.journal_id.type not in ('bank', 'cash'):
            return False

        # Must have journal items with debit > 0 on the bank/cash account
        bank_account = self.journal_id.default_account_id
        if not bank_account:
            return False

        # Check for debit entries on the bank account
        debit_lines = self.line_ids.filtered(
            lambda line: line.account_id == bank_account and line.debit > 0
        )

        return bool(debit_lines)

    def _send_payment_notification(self):
        """Send payment notification emails."""
        try:
            # Get bank account and debit lines
            bank_account = self.journal_id.default_account_id
            debit_lines = self.line_ids.filtered(
                lambda line: line.account_id == bank_account and line.debit > 0
            )

            if not debit_lines:
                return

            # Calculate total amount and get partner info
            total_amount = sum(debit_lines.mapped('debit'))
            currency = self.currency_id or self.company_id.currency_id

            # Get partner from first debit line (assuming same partner for all)
            partner = debit_lines[0].partner_id if debit_lines else None

            # Get users to notify
            notification_settings = self.env['payment.notification.settings']
            users_to_notify = notification_settings.get_notification_users(
                partner_id=partner.id if partner else None
            )

            # Remove the user who created this entry to avoid redundant notifications
            if self.create_uid in users_to_notify:
                users_to_notify -= self.create_uid

            if not users_to_notify:
                return

            # Prepare email template data
            template_values = {
                'partner_name': partner.display_name if partner else None,
                'amount': currency.symbol + ' ' + str(total_amount),
                'journal_name': self.journal_id.display_name,
                'move_id': self.id,
                'move_name': self.name,
            }

            # Send emails
            mail_template = self.env.ref(
                'opsway_payment_notifications.payment_received_email_template'
            )

            for user in users_to_notify:
                if user.partner_id.email:
                    # Generate template with render_fields to get subject and body
                    template_data = mail_template.with_context(
                        **template_values,
                        recipient_name=user.name
                    )._generate_template([self.id], ['subject', 'body_html'])

                    # Clean subject to remove newlines and carriage returns
                    subject = template_data.get(self.id, {}).get('subject', '')
                    if subject:
                        subject = subject.replace(
                            '\n', ' ').replace('\r', ' ').strip()
                        # Remove excessive whitespace
                        subject = ' '.join(subject.split())

                    # Send email with cleaned subject
                    mail_template.send_mail(
                        self.id,
                        force_send=True,
                        email_values={
                            'email_to': user.partner_id.email,
                            'subject': subject
                        }
                    )

            _logger.info(
                f"Payment notification sent for move {
                    self.name} to {len(users_to_notify)} users"
            )

        except Exception as e:
            _logger.error(f"Error sending payment notification for move {
                          self.name}: {str(e)}")
            # Don't raise the exception to avoid blocking the posting process
