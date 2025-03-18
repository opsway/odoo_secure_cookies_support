from odoo import models
from odoo.tools import str2bool


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info['secure_cookies'] = str2bool(
            self.env['ir.config_parameter'].sudo().get_param('secure_cookies'), default=False)
        return session_info

    def session_info(self):
        session_info = super().session_info()
        session_info['secure_cookies'] = str2bool(
            self.env['ir.config_parameter'].sudo().get_param('secure_cookies'), default=False)
        return session_info
