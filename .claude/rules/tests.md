# Testing

- Prefer business/integration scenarios over tests that merely assert fields/views exist.
- Exercise the same public method/button/controller/cron path the user or integration will use.
- Mock external side effects at the lowest practical boundary while keeping Odoo business logic real.
- Every defect fixed during adoption should gain a regression test when practical.
- High-risk authorization/business paths deserve tests even when legacy surrounding code remains untested.
- Do not demand heroic coverage as a prerequisite for adopting existing production code; improve risk-first.
