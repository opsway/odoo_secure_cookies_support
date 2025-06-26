/** @odoo-module **/

import { SectionAndNoteFieldOne2Many } from '@account/components/section_and_note_fields_backend/section_and_note_fields_backend';
import { patch } from '@web/core/utils/patch';


patch(SectionAndNoteFieldOne2Many.prototype, {
    get rendererProps() {
        const props = super.rendererProps;
        if (this.props.arch.attrs.editable) {
            props.disableLinesDuplicate = this.props.activeField?.rawAttrs?.disable_lines_duplicate;
        }
        return props;
    },
});
