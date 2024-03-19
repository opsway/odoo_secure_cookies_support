/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'Message',
    modelMethods: {
        /**
         * @override
         */
        convertData(data) {
        	 const res = this._super(data);
             if ('cc_email' in data) {
                 res.cc_email = data.cc_email;
             }
             if ('bcc_email' in data) {
                 res.bcc_email = data.bcc_email;
             }
             return res;
        },
    },
    fields: {
    	cc_email: attr(),
        bcc_email: attr(),
        
    },
});
