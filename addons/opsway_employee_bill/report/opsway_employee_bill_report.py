from odoo import models


class OpswayEmployeeBillReport(models.AbstractModel):
    _name = 'report.opsway_employee_bill'
    _description = 'Opsway Employee Bill Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
        }
