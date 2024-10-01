from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    employee_bill_sign_ids = fields.One2many(
        'employee.bill.sign.line',
        'move_id',
        string='Bill Sign'
    )
    need_multi_lang_report = fields.Boolean(
        string='Need Multi Lang Report',
        compute='_compute_need_multi_lang_report',
    )
    service_agreement = fields.Char(
        translate=True,
    )
    invoice_number = fields.Char()

    @api.depends('partner_id.lang')
    def _compute_need_multi_lang_report(self):
        for rec in self:
            rec.need_multi_lang_report = rec.partner_id.lang != self.env.user.lang

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self.employee_bill_sign_ids.unlink()
        return res

    def _get_vendor_invoice_date(self):
        self.ensure_one()
        months = {
            1: _('January'),
            2: _('February'),
            3: _('March'),
            4: _('April'),
            5: _('May'),
            6: _('June'),
            7: _('July'),
            8: _('August'),
            9: _('September'),
            10: _('October'),
            11: _('November'),
            12: _('December'),
        }
        return f'{months[self.invoice_date.month]} {self.invoice_date.day}, {self.invoice_date.year}'

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.move_type == 'in_invoice':
            for rec in self:
                lang = rec.partner_id.lang
                rec = self.with_context(lang=lang)
                first_line = rec.line_ids and rec.line_ids[0]
                product_id = first_line.product_id
                product_tag_id = product_id.product_tag_ids and product_id.product_tag_ids[0]
                description = product_tag_id and product_tag_id.name or product_id.name
                self.env['employee.bill.sign.line'].create({
                    'move_id': rec.id,
                    'period': rec.invoice_date.strftime('%B %Y'),
                    'description': description,
                    'amount': rec.amount_total,
                    'price': first_line.price_unit,
                })
