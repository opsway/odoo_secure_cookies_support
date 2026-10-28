# Odoo access and privilege rules

- Treat ACLs, record rules, groups, multi-company filtering and portal/public access as part of the feature, not cleanup.
- Prefer operating with the caller's normal environment. Every `sudo()`, `with_user(SUPERUSER_ID)` or equivalent privilege escalation needs an explicit reason and narrow scope.
- On Odoo 17.0 the access check is still the split pair, `check_access_rights()` and `check_access_rule()`; `check_access()` does not exist before 18.0. Use `env.user.has_group()` for group checks.
- Never assume UI visibility is authorization.
- Public model methods/controllers must validate both identity and object-level access.
- Security changes require security-review attention even when they look mechanically small.
