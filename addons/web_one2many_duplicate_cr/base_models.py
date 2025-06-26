from odoo.models import BaseModel


_apply_onchange_methods = BaseModel._apply_onchange_methods


def _new_apply_onchange_methods(self, field_name, result):
    if self.env.context.get('duplicate_one2many_record'):
        return None
    return _apply_onchange_methods(self, field_name, result)


BaseModel._apply_onchange_methods = _new_apply_onchange_methods
