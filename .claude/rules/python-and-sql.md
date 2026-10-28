# Python, ORM and SQL

- Use ORM unless SQL is materially clearer/faster and the transaction/security consequences are understood.
- Parameterize SQL. Never interpolate user-controlled values into SQL text.
- Avoid `eval`; use Odoo `safe_eval` only where framework semantics require it and tightly control the expression/context.
- External calls require explicit timeouts, failure handling and careful logging that does not leak secrets or personal data.
- Do not use subprocess/filesystem access when an Odoo/Python API is sufficient.
- Do not commit credentials, API keys or customer data.
