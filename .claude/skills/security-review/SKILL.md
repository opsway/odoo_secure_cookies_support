# Odoo security review

Use for initial adoption, security-sensitive changes, or explicit security review requests.

## Routine review

Review the relevant addon code, dependencies and manifests. Pay special attention to:

- ACLs, record rules, groups, company isolation and portal/public users;
- `sudo()`, superuser/`with_user`, context tricks and privilege transitions;
- controllers/routes: `auth`, CSRF, CORS, object-level access, RPC/public methods;
- raw SQL, dynamic domains, `eval`/`safe_eval`, deserialization and template rendering;
- external HTTP: SSRF, redirects, TLS verification, timeouts, credentials and data exfiltration;
- filesystem, uploads, attachments, path traversal, subprocess/shell execution;
- secrets in code/config/logs and unsafe `ir.config_parameter` handling;
- cron/background jobs and operations that run with broader privileges than interactive users;
- accounting, payment, authentication, signing/crypto, personal/health/customer-sensitive data;
- install/uninstall/migration hooks and destructive writes;
- JS/QWeb XSS or unsafe raw HTML;
- dependency/provenance issues that materially change trust.

Report concrete attack/failure scenarios, affected code, severity and remediation. Do not equate style deviations with vulnerabilities.

## Heavy audit escalation

Consider Cloudflare `security-audit-skill` when the pack is unknown/untrusted, large/complex, security-sensitive, exposes public/auth surfaces, or the tech lead explicitly requests a deep audit. It is expensive and should not run on every ordinary PR.

If used, keep its raw output outside the maintained adoption record if it is noisy. Synthesize confirmed/relevant findings into the single living `docs/security-review.md` and identify the audited commit.

## Authority

Automated security review never sets `status: adopted`. It produces evidence. The tech lead reviews code/report and owns adoption sign-off.
