from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def _get_default_analytic_plan(self):
        """Get the default analytical plan with complete_name 'Projects / Cider'"""
        plan = self.env['account.analytic.plan'].search([
            ('complete_name', '=', 'Projects / Cider')
        ], limit=1)
        return plan.id if plan else False

    analytic_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Analytical Plan',
        help='Select the analytical plan to calculate percentage for',
        default=lambda self: self._get_default_analytic_plan()
    )
    
    analytic_plan_percentage = fields.Float(
        string='Analytical Plan Percentage (%)',
        compute='_compute_analytic_plan_percentage',
        store=True,
        digits='Product Price',
        help='Percentage of the selected analytical plan in the total bill amount'
    )

    @api.depends('analytic_plan_id', 'line_ids.analytic_distribution', 'amount_total')
    def _compute_analytic_plan_percentage(self):
        for move in self:
            if not move.analytic_plan_id or not move.amount_total:
                move.analytic_plan_percentage = 0.0
                continue
            
            # Get all analytical entries related to this plan
            total_analytic_amount = 0.0
            
            for line in move.line_ids:
                if line.analytic_distribution:
                    # analytic_distribution is a JSON field with account_id: percentage
                    for account_id, percentage in line.analytic_distribution.items():
                        try:
                            # Convert account_id to integer, handling potential formatting issues
                            account_id_int = int(str(account_id).replace(',', '').replace('.', ''))
                            account = self.env['account.analytic.account'].browse(account_id_int)
                            if account.exists() and account.plan_id == move.analytic_plan_id:
                                # Calculate the amount for this analytical entry
                                line_amount = abs(line.balance)
                                # Convert percentage to float, handling potential formatting issues
                                percentage_float = float(str(percentage).replace(',', '.'))
                                analytic_amount = line_amount * (percentage_float / 100.0)
                                total_analytic_amount += analytic_amount
                        except (ValueError, TypeError):
                            # Skip invalid account_id or percentage values
                            continue
            
            # Calculate percentage of total bill amount
            if move.amount_total:
                move.analytic_plan_percentage = (total_analytic_amount / move.amount_total) * 100.0
            else:
                move.analytic_plan_percentage = 0.0