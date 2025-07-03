/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(Message.prototype, {
    setup() {
        super.setup();

        this.orm = useService("orm");

        // Use useState for reactive state
        this.emailState = useState({
            cc_email: '',
            bcc_email: '',
        });

        this._fetchCCandBCC();
    },

    async _fetchCCandBCC() {
        try {
            const result = await this.orm.read("mail.message", [this.message.id], ["cc_email", "bcc_email"]);
            if (result && result.length) {
                const mailRecord = result[0];

                this.emailState.cc_email = mailRecord.cc_email || '';
                this.emailState.bcc_email = mailRecord.bcc_email || '';
            } else {
                console.warn("No mail.message record found for given ID.");
            }
        } catch (error) {
            console.error("Failed to fetch mail.message record:", error);
        }
    },
});
