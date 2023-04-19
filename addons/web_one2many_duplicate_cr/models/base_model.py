from odoo.models import BaseModel


BaseModel._old_onchange_eval = BaseModel._onchange_eval


class MyBaseModel(BaseModel):
    _auto = False
    _name = 'fake'
    _description = "Patch Base Model onchange method"

    def _onchange_eval(self, field_name, onchange, result):
        if not self.env.context.get('duplicate_one2many_record'):
            self._old_onchange_eval(field_name, onchange, result)
        else:
            return


BaseModel._onchange_eval = MyBaseModel._onchange_eval
