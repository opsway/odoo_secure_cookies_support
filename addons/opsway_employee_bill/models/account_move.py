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
    employee_product_tag_id = fields.Many2one(
        'product.tag',
        compute='_compute_employee_product_tag_id',
        store=True,
    )

    @api.depends('line_ids.product_id')
    def _compute_employee_product_tag_id(self):
        for rec in self:
            rec.employee_product_tag_id = bool(rec.line_ids and rec.line_ids[0].product_id.product_tag_ids) and \
                                          rec.line_ids[0].product_id.product_tag_ids[0]

    @api.depends('partner_id.lang')
    def _compute_need_multi_lang_report(self):
        for rec in self:
            rec.need_multi_lang_report = rec.partner_id.lang != self.env.user.lang

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self.employee_bill_sign_ids.unlink()
        return res

    def _get_months(self, month_number):
        months = [
            (1, _('January')),
            (2, _('February')),
            (3, _('March')),
            (4, _('April')),
            (5, _('May')),
            (6, _('June')),
            (7, _('July')),
            (8, _('August')),
            (9, _('September')),
            (10, _('October')),
            (11, _('November')),
            (12, _('December')),
        ]
        return dict(months)[month_number]

    def _get_vendor_invoice_date(self):
        self.ensure_one()
        return f'{self._get_months(self.invoice_date.month)} {self.invoice_date.day}, {self.invoice_date.year}'

    def _get_vendor_invoice_period(self):
        self.ensure_one()
        return f'{self._get_months(self.invoice_date.month)} {self.invoice_date.year}'

    def _get_total_amount_in_word_pe(self):
        self.ensure_one()
        return self.currency_id.amount_to_text(self.amount_total).replace(',', '').capitalize()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.move_type == 'in_invoice':
            for rec in self:
                lang = rec.partner_id.lang
                rec = self.with_context(lang=lang)
                first_line = rec.line_ids and rec.line_ids[0]
                self.env['employee.bill.sign.line'].create({
                    'move_id': rec.id,
                    'period': rec._get_vendor_invoice_period(),
                    'amount': rec.amount_total,
                    'description': rec.employee_product_tag_id.name or first_line.product_id.name,
                    'price': first_line.price_unit,
                })
