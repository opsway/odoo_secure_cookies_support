from odoo.fields import Field

get_description = Field.get_description


def new_get_description(self, env, attributes=None):
    desc = get_description(self, env, attributes)
    if attributes and 'copy' in attributes and 'copy' not in desc:
        desc['copy'] = self.copy
    return desc


Field.get_description = new_get_description
