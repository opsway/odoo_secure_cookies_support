# Source language and translations

- Write source code, comments, technical documentation, commit/PR text and original user-facing strings in English.
- Do not "translate" source code by replacing English strings with another language.
- Use Odoo translation mechanisms for user-visible localization: translatable fields/strings and `i18n/*.po`.
- Keep `_()` calls meaningful; do not concatenate fragments that translators cannot reorder safely.
- Treat translations as normal maintained artifacts. Agents may create/update them using the `odoo-translation-management` skill unless repository-local documentation says otherwise.
