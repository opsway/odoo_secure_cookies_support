# Models and fields

- Prefer Odoo ORM and standard extension points over monkeypatching or broad framework overrides.
- Keep overrides narrow; call `super()` unless intentionally replacing behavior and document that exception.
- Avoid model-level `readonly=True` merely to control UI editing; prefer view-level readonly when import/API writes must remain possible.
- Use expressive indexes and stored computed fields only when justified by access/query patterns.
- Be careful with non-stored related/computed fields in domains and searches.
- Consider multi-company semantics for every company-dependent model/field/domain.
- Avoid hidden side effects in `create`, `write`, `unlink`, `search`, `_search`, `name_search` and compute methods.
