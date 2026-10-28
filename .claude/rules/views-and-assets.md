# XML, views, QWeb and assets

- Prefer stable XML inheritance targets; avoid brittle absolute XPath chains.
- Keep access restrictions in backend security as well as UI visibility.
- Escape untrusted values in QWeb/HTML; raw rendering needs explicit justification.
- Keep JS/assets inside the owning addon and declare them through the supported manifest asset bundles for the target Odoo version.
- IDs must be stable and namespaced by addon conventions; avoid duplicate XML IDs across the pack.
