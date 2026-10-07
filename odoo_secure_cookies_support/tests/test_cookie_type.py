from unittest.mock import Mock, patch

from odoo.http import FutureResponse, Response, _request_stack
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCookieType(TransactionCase):
    """The wrapper adds Secure and SameSite, and must leave Odoo's consent check to Odoo."""

    def _set_cookie(self, response_class, cookie_type):
        _request_stack.push(Mock(db=self.env.cr.dbname, env=self.env, httprequest=Mock(scheme='https')))
        try:
            response = response_class()
            response.set_cookie('trace', 'x', max_age=3600, cookie_type=cookie_type)
        finally:
            _request_stack.pop()
        return response.headers['Set-Cookie']

    def test_an_optional_cookie_waits_for_consent(self):
        # As a website with a cookie bar answers a visitor who has not accepted optional cookies.
        def is_allowed(cls, cookie_type):
            return cookie_type == 'required'

        with patch.object(type(self.env['ir.http']), '_is_allowed_cookie', classmethod(is_allowed)):
            for response_class in (Response, FutureResponse):
                with self.subTest(response=response_class.__name__):
                    self.assertIn('Max-Age=0', self._set_cookie(response_class, 'optional'),
                                  "Without consent the browser drops the cookie at once")
                    required = self._set_cookie(response_class, 'required')
                    self.assertIn('Max-Age=3600', required)
                    self.assertIn('SameSite=Lax', required)
