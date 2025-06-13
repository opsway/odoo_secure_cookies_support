import werkzeug
from odoo.http import FutureResponse, Response, request
from odoo.tools import str2bool
import functools

DEFAULT_SAMESITE = 'Strict'


def _get_secure_cookies_param(default=False):
    return default or str2bool(request.env['ir.config_parameter'].sudo().get_param('secure_cookies', False))


def _set_cookie_wrapper(original_func, response_class):
    @functools.wraps(response_class.set_cookie)
    def wrapper(self, key, value='', max_age=None, expires=-1, path='/', domain=None,
                secure=False, httponly=False, samesite=None, cookie_type='required'):
        secure = _get_secure_cookies_param(secure)
        samesite = samesite or DEFAULT_SAMESITE
        return original_func(self, key, value=value, max_age=max_age, expires=expires,
                             path=path, domain=domain, secure=secure, httponly=httponly,
                             samesite=samesite)
    return wrapper


_old_future_response_set_cookie = FutureResponse.set_cookie
_old_response_set_cookie = Response.set_cookie

FutureResponse.set_cookie = _set_cookie_wrapper(_old_future_response_set_cookie, werkzeug.Response)
Response.set_cookie = _set_cookie_wrapper(_old_response_set_cookie, Response)
