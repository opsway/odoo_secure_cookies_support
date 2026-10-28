# Odoo translation management

Use when adding or updating translations.

1. Keep original source/user-facing strings in English.
2. Ensure strings are actually translatable using standard Odoo mechanisms (`_()`, translatable field/view terms, QWeb where supported).
3. Update/create the appropriate `i18n/<locale>.po` files; do not replace source strings with translated text.
4. Preserve placeholders, markup and formatting exactly unless the target language grammar requires safe reordering.
5. Avoid translating technical identifiers, XML IDs, field names, code comments or configuration keys.
6. Review fuzzy/obsolete entries before committing them as authoritative translations.
7. If a repository has a different translation process, follow its local rule/documentation instead.
