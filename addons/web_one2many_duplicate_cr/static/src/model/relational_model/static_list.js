/** @odoo-module **/

import { StaticList } from '@web/model/relational_model/static_list';
import {ONE2MANY_DUPLICATE_CONTEXT_KEY} from "../../main";


const originalAddNewRecord = StaticList.prototype.addNewRecord;

StaticList.prototype.addNewRecord = async function (params) {
    const newRecord = await originalAddNewRecord.call(this, params);
    if (!!params?.context?.[ONE2MANY_DUPLICATE_CONTEXT_KEY]) {
        await newRecord.update({});

        delete params.context[ONE2MANY_DUPLICATE_CONTEXT_KEY];
    }
    return newRecord;
}
