/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { ListRenderer } from '@web/views/list/list_renderer';
import { serializeDate, serializeDateTime } from '@web/core/l10n/dates';

export const ONE2MANY_DUPLICATE_CONTEXT_KEY = 'duplicate_one2many_record';


patch(ListRenderer.prototype, {
    get showCopyButton() {
        return this.isX2Many &&
            this.activeActions.create &&
            (this.props.disableLinesDuplicate === undefined || !this.props.disableLinesDuplicate);
    },

    set showCopyButton(value) {},

    x2manyIds(record, fieldName) {
        let valueIds = [];

        const x2ManyValue = record.data[fieldName];
        if (x2ManyValue) {
            let x2ManyValueRecords;
            if ('records' in x2ManyValue) {
                x2ManyValueRecords = x2ManyValue.records;
            } else if ('data' in x2ManyValue) {
                x2ManyValueRecords = x2ManyValue.data;
            }
            if (Array.isArray(x2ManyValueRecords)) {
                valueIds = x2ManyValueRecords.filter(rec => rec.data?.id).map(rec => rec.data.id);
                if (valueIds.length == 0 && x2ManyValueRecords) {
                    valueIds = x2ManyValueRecords.filter(rec => rec._parentRecord?.data[fieldName].currentIds)
                        .map(rec => rec._parentRecord?.data[fieldName].currentIds)
                    if (valueIds.length > 1) {
                        valueIds = valueIds[0]
                    }
                }
            }
        }
        return valueIds;
    },

    async onCopyRecord(record) {
        const context = record.context;
        const newCopyData = {
            [ONE2MANY_DUPLICATE_CONTEXT_KEY]: 1,
        };

        if (record.resId) {
            if (record.isDirty) {
                await this.props.list.model.root.save({ stayInEdition: true });
            }
            let copyData = await this.env.model.orm.call(record.resModel, 'copy_data', [record.resId], { context: context });
            if (copyData) {
                copyData = copyData[0]
            }

            Object.entries(copyData).forEach(([fieldName, fieldValue]) => {
                newCopyData[`default_${fieldName}`] = fieldValue;
            })
        } else {
            Object.entries(record.fields).forEach(([fieldName, fieldProps]) => {
                if (!fieldProps.copy) {
                    return;
                }
                let value;
                switch (fieldProps.type) {
                    case 'many2one':
                        value = false;
                        const many2OneValue = record.data[fieldName];
                        if (many2OneValue) {
                            if ('data' in many2OneValue) {
                                value = many2OneValue.data?.id || false;
                            } else if (Array.isArray(many2OneValue) && many2OneValue.length) {
                                value = many2OneValue[0];
                            }
                        }
                        break;
                    case 'many2many':
                    case 'one2many':
                        const valueIds = this.x2manyIds(record, fieldName);
                        value = [[6, 0, valueIds]];
                        break;
                    case 'datetime':
                        value = record.data[fieldName] ? serializeDateTime(record.data[fieldName]) : false;
                        break;
                    case 'date':
                        value = record.data[fieldName] ? serializeDate(record.data[fieldName]) : false;
                        break;
                    default:
                        value = record.data[fieldName];
                        break;
                }
                if (value !== undefined) {
                    newCopyData[`default_${fieldName}`] = value;
                }
            });
        }

        const contextToPass = Object.assign({}, context, newCopyData);
        await this.props.onAdd({ context: contextToPass });
    },
});

ListRenderer.props = [
    ...ListRenderer.props,
    'disableLinesDuplicate?',
];
