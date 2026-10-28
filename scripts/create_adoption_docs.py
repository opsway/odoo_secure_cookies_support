#!/usr/bin/env python3
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADOPTION = ROOT / "docs" / "adoption.md"
SECURITY = ROOT / "docs" / "security-review.md"

ADOPTION_CONTENT = """# Addon-pack adoption record

## Status

`status: baselined`

Only the tech lead changes this to `status: adopted` after mechanical work/review is complete and signed off.

## Business motivation

Describe why these addons exist, who uses them, and what problem they solve. Preserve the BA's original description/motivation rather than replacing it with an engineering paraphrase.

## Origin and provenance

Source type: `git | zip | vendor | other`
Original repository/remote:
Original commit SHA:
Received from:
Received date:
Production status: `not-known | production-unmanaged | not-in-production`
License/provenance notes:

For ZIP intake, record an external artifact hash/location if available, but do not commit the ZIP. Unpack it and baseline the resulting source in Git.

## Baseline

Baseline commit:
Production equivalence / known differences:

The first meaningful repository commit/history should preserve the received code/docs before mechanical normalization. Git history is the primary record; this section makes provenance readable without archaeology.

## Mechanical normalization

- [ ] repository shape normalized
- [ ] manifests/dependencies inventoried
- [ ] code formatting/lint/static checks addressed or documented
- [ ] licenses/provenance understood
- [ ] addon docs capture purpose and limitations
- [ ] obvious credentials/customer data removed

## Review

Architecture review:
Security review: see `docs/security-review.md` when applicable.
Known technical debt:

## Runtime verification

Workbench/staging commit:
Environment/data notes:
UAT result:

Runtime verification is normally performed after mechanical work and reviews. Existing production remains untouched during reverse adoption.

## Tech-lead sign-off

Signed off by:
Date:
Reviewed commit:

`status: baselined`
"""

SECURITY_CONTENT = """# Security review

## Scope

Reviewed commit:
Target Odoo version(s):
Reviewer/tool:
Date:

## Risk summary

Overall risk: `not-reviewed`

Security-sensitive surfaces:

- TBD

## Findings

No review recorded yet.

## Accepted risks

None recorded.

## Unresolved actions

- Run the Odoo `security-review` skill.

## Tech-lead note

Security tooling provides evidence; adoption authority remains with the tech lead and is recorded in `docs/adoption.md`.
"""

for path in (ADOPTION, SECURITY):
    if path.exists():
        raise SystemExit(f"{path.relative_to(ROOT)} already exists; refusing to overwrite adoption history")
ADOPTION.write_text(ADOPTION_CONTENT, encoding="utf-8")
SECURITY.write_text(SECURITY_CONTENT, encoding="utf-8")
print("Created docs/adoption.md and docs/security-review.md")
