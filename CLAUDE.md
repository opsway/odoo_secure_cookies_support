# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

One Odoo addon, `odoo_secure_cookies_support/`, at the repository root. It adds `Secure` and `SameSite` to the
cookies Odoo sets, server- and browser-side, when the `secure_cookies` system parameter is on.

Branches are Odoo major versions (`17.0`, `18.0`, `19.0`); `18.0` is the default and primary line. A PR targets
the branch of the Odoo version it fixes. The branches have diverged, so diff them before porting a fix
(`git diff origin/18.0 origin/19.0`). Commits follow `[INT-XXXX][FIX|ADD|IMP] subject`, with a body that says why.

## Hard rules

**These outrank established repository practice.** "The repo already does it this way" is not a reason to keep
doing it — where a rule and an existing convention disagree, the rule wins and the convention gets fixed. Only
user-facing text is exempt: `README.rst`, `static/description/index.html` and manifest strings.

- **Comments — default to none.** A new comment must justify itself; the reader is a competent developer and the
  code already states the logic, so never restate it. Same bar for docstrings. What earns one: a non-obvious *why*
  the code cannot carry — a workaround and its cause, an Odoo trap, an invariant or unit a caller cannot infer, a
  `path:line` pointer to the doc holding the rationale. Trim, don't expand, verbose comments in code you touch.
- **Signatures carry the contract, not prose.** Prefer type hints and precise but short argument names over a
  docstring. Annotate Odoo models with the PyCharm-Odoo stub form, single-quoted —
  `def _partners(self) -> 'odoo.model.res_partner':`. **Keep it quoted:** `odoo.model` is a stub namespace with
  no runtime module behind it, so unquoted it raises at import.
- **Tests** — before adding a test, identify the durable behaviour, a plausible regression, its consequence, and
  why this test is the cheapest effective way to detect it. If any part is missing, do not add the test. **Never
  test the view layer**: no arch xpath, no assertions on labels or widgets — prove the behaviour behind it instead.
- **Consolidate and parameterize.** One table driven through `self.subTest` (as in `tests/test_cookie_type.py`)
  beats near-duplicate `test_*` methods. Consolidation means fewer methods and the *same* asserted cases: every
  row survives, and the suite is green before and after. This bar governs *adding* a test — it is never licence
  to delete, skip or disable one to get a green run.
- **Docs — one fact, one home.** Cross-reference instead of restating. No implementation-history narrative: git
  history holds what changed and when. Docs describe current state and the durable *why*.

## Running tests

The repository carries no Makefile, CI or lint config. Run the tests in throwaway containers of the branch's Odoo
version:

```bash
docker network create sc-test
docker run -d --rm --name sc-test-db --network sc-test \
  -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres postgres:14.7
docker run --rm --network sc-test -e HOST=sc-test-db -e USER=odoo -e PASSWORD=odoo \
  -v "$PWD":/mnt/extra-addons:ro odoo:18.0 \
  odoo -d sc_test --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons \
  -i odoo_secure_cookies_support --test-tags /odoo_secure_cookies_support --stop-after-init --without-demo=all
docker stop sc-test-db && docker network rm sc-test
```

The image's entrypoint overrides `--db_host`/`--db_user`/`--db_password` from `HOST`/`USER`/`PASSWORD`, so pass
those as environment variables. Against a source checkout, the `odoo` arguments are the same for `odoo-bin`.

One test: `--test-tags /odoo_secure_cookies_support:TestCookieType.test_an_optional_cookie_waits_for_consent`.
The tests are `post_install`.

## Architecture

Everything keys off the `ir.config_parameter` `secure_cookies` (seeded `0`, `noupdate`). Four pieces enforce it:

- **`http.py`** monkey-patches `odoo.http.Response.set_cookie` and `FutureResponse.set_cookie` at import, so the
  patch is process-wide. It forces `Secure` when the parameter is on and defaults `SameSite=Lax`. With no database
  bound (`request.env is None`) it falls back to the request scheme being `https`. The wrapper's signature must
  mirror upstream `set_cookie` for the branch's Odoo version and pass every argument on: dropping `cookie_type`
  bypasses Odoo's consent check (`ir.http._is_allowed_cookie`) and sets optional cookies without consent.
- **`models/ir_http.py`** exposes the flag to the browser in `session_info` and `get_frontend_session_info`.
- **`static/src/js/core/browser/cookie.js`**, in both `web.assets_backend` and `web.assets_frontend`, patches the
  `document.cookie` setter and `fetch` to append `Secure; SameSite=Strict` — Strict, unlike the server's Lax.
- **`views/webclient_templates.xml`** replaces the inline `tz` cookie script of `web.frontend_layout`, which runs
  before the asset bundle can patch `document.cookie`. Its xpath matches the script's `t-nocache` text, so it
  stops applying if upstream rewords that text.
