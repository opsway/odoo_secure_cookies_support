# Repository conventions

This repository contains standalone Odoo addons/addon packs.

- Recommended repository naming prefix: `odoo-addons-` (not enforced).
- Odoo version this branch targets: `19.0`. It is what the CI image, `valid-odoo-versions` and every manifest version prefix here follow.
- Odoo branches this repository maintains: `18.0`, `17.0`, `19.0`. `scripts/configure_repository.sh` provisions a branch ruleset for each, and makes the first the default branch.
- Technical owner / CODEOWNER: `@opsway/tech-leads`.
- GitHub access: `@opsway/lumirang` has write, `@opsway/tech-leads` has admin.
- Addon designation: *free*, so new first-party addons here declare `LGPL-3`. Imported addons retain their actual license. Terms live in [`LICENSE.md`](../LICENSE.md); licence texts in [`LICENSES/`](../LICENSES/).
- Addons live directly at repository root.
- Pack-level documentation lives here under `docs/`; addon-specific docs stay inside the addon.
- This repository is source, not a customer deployment project.
- Pull request merges: merge commit, squash and rebase are all allowed. Use a merge commit when the branch history is worth keeping, squash when it is not. Merge commits take the pull request title as their subject and its description as the body.

Template-managed files should normally be treated as read-only. Put local agent rules in `.claude/rules/local.md`; use `copier update` to receive future template changes and resolve any intentional local conflicts normally.

Update this branch from the template's matching branch:

```
copier update --vcs-ref 19.0
```

The answers file records the template commit, not the branch it came from, so omitting the ref
resolves to the template's default branch and would re-render this branch off another Odoo line.

## Licensing boundary

Addons here are licensed individually; [`LICENSE.md`](../LICENSE.md) is the map. One rule matters
when adding a dependency:

**A dependency whose licence the primary addon cannot absorb goes in a companion addon licensed to
match it**, not in the primary addon. A proprietary or LGPL-3 addon cannot carry an AGPL-3 or GPL
dependency in its install closure; the companion is licensed to match the dependency, and the
primary addon reaches the feature through configuration parameters or a hook rather than by
importing it. The same applies to `external_dependencies['python']`.

`scripts/check_licenses.py` enforces it, on three axes — the addon graph, the Python wheels, and,
**per addon**, a readable text for every licence that addon is under or links. It runs offline in
pre-commit against curated maps, and in CI as the **Dependency licence scan** job, which resolves
real Odoo manifests transitively and asks pip to resolve the wheels, then reports a stale map entry
rather than trusting it. A dependency whose licence is unknown fails the check on purpose:
classifying a licence is a decision someone has to make, and a repository that never forces that
decision is how a copyleft dependency ends up inside a proprietary addon unnoticed.

That job is not gated on which files changed — a gate a pull request can skip by touching only
ignored paths is not a gate, and `scripts/**` is on the ignore list.

## Before a release

1. `make lint` — the whole hook set.
2. `make licence-inventory ADDONS_PATH=…` — the resolved licence scan, the same one CI runs. Needs
   network access and installs nothing. It wants pip >= 25.0: 22.2 is enough for `--dry-run
   --report`, but earlier pips drop the PEP 639 `License-Expression` field, so wheels that declare
   their licence that way — `idna` and `urllib3` among them — come back looking unlicensed. The
   addons path is required, and must reach Odoo core and every pinned external source: without it
   the Odoo side reads the offline map instead of real manifests, and a release record that cannot
   see an upstream licence change is not a record. It writes `licence-inventory.json`: every addon
   with its version and licence, its whole Odoo install closure with each licence, every Python
   wheel pip resolves under it with that wheel's resolved version, licence, artefact URL and hash,
   the pip and marker environment that resolved them, and the licence texts present.
3. Attach that inventory to the release. Its two halves are evidence of different things, and
   conflating them is how a compliance record starts claiming more than it knows:
   - **The addon and Odoo side records what shipped.** It is read from the real manifests at the
     commit named in the file, so the licences it lists are the licences that applied to the code in
     that release. This is the half nobody can reconstruct afterwards, once upstream has moved on.
   - **The Python side is a dependency-resolution snapshot, not a bill of materials.** pip is asked
     what *would* resolve, at scan time, from whichever index that machine's pip configuration
     selects — so it is not necessarily PyPI, which is why each wheel records the artefact URL and
     hash it was actually read from. An `external_dependencies['python']` entry is a PEP 508
     requirement and Odoo 18 honours a version specifier in it, so a pinned requirement names the
     release the deployment will get; one that pins nothing names only what the index offered that
     day. To know what a given deployment holds, read that deployment. The file states all of this
     in `python_resolution.basis`; do not restate it as "what shipped" in release notes.
4. Confirm every addon carries its own `LICENSE.md` and `LICENSES/`. The scan fails if not, so this
   is a read of the output rather than a separate check.
5. Resolve every `TODO` left in [`LICENSE.md`](../LICENSE.md). For a proprietary designation those
   are the commercial terms, and they must come from the signed agreement rather than from general
   licensing practice.
6. A green scan is not legal clearance. It reports what the manifests declare and what pip resolved;
   it knows nothing about who owns the code or which instrument it goes out under. Whether this
   repository may be licensed to anyone is answered by whoever holds those questions, not by this
   job.

## Licence files live inside each addon

Each addon carries its own `LICENSE.md` and its own `LICENSES/` copies of every licence text it must
ship. **These addons are delivered individually** — extracted with `git subtree` or copied into a
customer's Odoo addons path — so a licence text kept only at the repository root would not travel
with the thing it licenses, and would go missing at delivery.

`LICENSES/` at the repository root is a stock to copy from; the check never reads it. Relative links
inside an addon must stay inside it, because a `](../…)` is dead once the addon is extracted.
Duplicating the FSF texts across addons is the intended cost — one copy per distributable unit.

[`../LICENSE.md`](../LICENSE.md) carries the copy-in commands for this repository's designation.
