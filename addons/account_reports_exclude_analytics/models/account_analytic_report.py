from odoo import models
from odoo.osv import expression as osv


class AccountAnalyticReport(models.AbstractModel):
    _inherit = 'account.report'

    # pylint: disable=no-else-return
    def action_audit_cell(self, options, params):
        column_group_options = self._get_column_group_options(
            options, params['column_group_key'])

        if not column_group_options.get('analytic_groupby_option'):
            return super(AccountAnalyticReport, self).action_audit_cell(options, params)
        else:
            report_line = self.env['account.report.line'].browse(
                params['report_line_id'])
            expression = report_line.expression_ids.filtered(
                lambda x: x.label == params['expression_label'])
            line_domain = self._get_audit_line_domain(
                column_group_options, expression, params)
            # The line domain is made for move lines, so we need some postprocessing
            # to have it work with analytic lines.
            domain = []
            AccountAnalyticLine = self.env['account.analytic.line']
            for expression_tuple in line_domain:  # Renamed to avoid conflict
                # For operators such as '&' or '|' we can juste add them again.
                if len(expression_tuple) == 1:
                    domain.append(expression_tuple)
                    continue

                field, operator, right_term = expression_tuple
                # On analytic lines, the account.account field is named general_account_id and not account_id.
                if field.split('.')[0] == 'account_id':
                    field = field.replace('account_id', 'general_account_id')
                    current_expression = [(field, operator, right_term)]
                # Replace the 'analytic_distribution' by the account_id domain as we expect for analytic lines.
                elif field == 'analytic_distribution':
                    # START OF CUSTOMIZATION
                    current_expression = [
                        ('auto_account_id', operator, right_term)]
                    # END OF CUSTOMIZATION
                # For other fields not present in on the analytic line model, map them
                # to get the info from the move_line.
                # Or ignore these conditions if there is no move lines.
                elif field.split('.')[0] not in AccountAnalyticLine._fields:
                    current_expression = [
                        (f'move_line_id.{field}', operator, right_term)]
                    if options.get('include_analytic_without_aml'):
                        current_expression = osv.OR([
                            [('move_line_id', '=', False)],
                            current_expression,
                        ])
                else:
                    # just for the extend
                    current_expression = [expression_tuple]
                domain.extend(current_expression)

            action = self.env.ref(
                'analytic.account_analytic_line_action_entries')._get_action_dict()
            action['domain'] = domain
            return action
