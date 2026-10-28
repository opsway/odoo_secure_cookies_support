# Odoo access and privilege rules

- Treat ACLs, record rules, groups, multi-company filtering and portal/public access as part of the feature, not cleanup.
- Prefer operating with the caller's normal environment. Every `sudo()`, `with_user(SUPERUSER_ID)` or equivalent privilege escalation needs an explicit reason and narrow scope.
- On Odoo 19.0, use `check_access()` rather than the older split access-right/rule checks where applicable, and `has_access()` where a boolean is wanted instead of a raise. Use `env.user.has_group()` for group checks.
- Never assume UI visibility is authorization.
- Public model methods/controllers must validate both identity and object-level access.
- Security changes require security-review attention even when they look mechanically small.
