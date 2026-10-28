# Architectural review

Use this skill for non-trivial addon changes or initial adoption.

1. Identify the addon(s), business motivation and target Odoo versions.
2. Map dependencies, inherited models, overridden lifecycle/search methods, controllers, cron/jobs and external integrations.
3. Check whether the implementation uses ordinary Odoo extension points before accepting custom infrastructure or framework monkeypatching.
4. Look for cross-addon coupling, hidden assumptions about customer/project code, duplicated framework behavior and irreversible data transformations.
5. Separate mechanical normalization findings from behavioral/architectural changes.
6. Produce concise findings with severity (`blocking`, `important`, `cleanup`) and concrete remediation. Do not manufacture findings to fill categories.
7. For adoption, include unresolved architectural risks in `docs/adoption.md`; the tech lead owns the final `status: adopted` decision.
