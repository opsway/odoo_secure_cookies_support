# Licensing

Addons in this repository are licensed **individually**. Each declares its own `license` in its
`__manifest__.py`, and that declaration governs. This file is the map.

<!-- ADDON_LICENSE_TABLE_START -->
<!-- Add a row per addon: name, declared licence, and where its text lives. -->
<!-- ADDON_LICENSE_TABLE_END -->

Recommended licence for new first-party addons here: **`LGPL-3`**, from this repository's
designation — *free*. Imported addons keep the licence they actually had.

## Every addon carries its own licence files

**Each addon needs its own `LICENSE.md` and its own `LICENSES/` copies of every licence text it must
ship.** Addons are delivered individually — extracted with `git subtree` or copied into a customer's
Odoo addons path — so a licence text kept only here, at the repository root, does not travel with the
thing it licenses. It goes missing at delivery, which is the one moment it matters.

`scripts/check_licenses.py` enforces this per addon and will fail until each addon has them. When you
add an addon:

```bash
mkdir -p <addon>/LICENSES
cp LICENSES/LGPL-3.txt LICENSES/GPL-3.txt <addon>/LICENSES/   # Odoo CE is LGPL-3
cp LICENSES/LGPL-3.txt <addon>/LICENSES/
# then write <addon>/LICENSE.md from the terms below
```

Add the text of every licence the addon **links**, not only the one it declares — LGPL-3 §4(b)
requires the GPL text alongside the LGPL, and every Odoo addon links LGPL-3 Community Edition.

Relative links inside an addon must stay inside it: a `](../…)` is dead once the addon is extracted,
and the check rejects one in an addon's `LICENSE.md`.

The [`LICENSES/`](LICENSES/) directory at this root is a **stock to copy from**, not the licence of
anything. Once every addon carries its own copies you may keep it for convenience or delete it; the
check only ever looks inside addons.

## Copyright

Copyright © <YEAR> **Digital Delivery Center Spolka z ograniczona odpowiedzialnoscia**, ul. Kawalerzystow 17/12, 53-004 Wroclaw, Poland, KRS 0000964819, NIP 8992922295 ("DDC").

DDC trades as **OpsWay**. That is a trading name and not a legal
person: it cannot hold copyright, grant a licence, or be a party to an agreement. Name the entity.

Replace `<YEAR>` above with the year of first publication.


## LGPL-3

These addons are free software, published under the **LGPL-3**. Full text in
[`LICENSES/LGPL-3.txt`](LICENSES/LGPL-3.txt).


LGPL-3 permits a proprietary work to depend on and extend these addons — that is what the "Lesser"
is for. If that is not what you want, the designation should have been AGPL-3.

Per LGPL-3 §4, a combined work must ship both the LGPL and the GPL texts; both are in
[`LICENSES/`](LICENSES/).


Every source file should carry a notice, as LGPL-3 §5(a) expects:

```python
# Copyright <YEAR> Digital Delivery Center Spolka z ograniczona odpowiedzialnoscia
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3-3.0).
```


## Third-party components

Every Odoo addon depends on Odoo Community Edition, which is **LGPL-3**; its text and the GPL-3 text
it requires are stocked in [`LICENSES/`](LICENSES/) for copying into each addon. List anything further
here — OCA modules, Python packages — with its licence and where its text lives.

Nothing third-party should be vendored into this repository. Where it is unavoidable, record its
provenance, licence and upgrade ownership explicitly.

## The licence boundary is enforced, not remembered

`scripts/check_licenses.py` checks, on every commit and again in CI as the **Dependency licence
scan** job:

- that no addon depends on an Odoo module whose licence its own cannot absorb;
- the same for `external_dependencies['python']`;
- that **every addon** carries a readable text for each licence it is under or links, beside it
  rather than at the repository root.

A dependency whose licence is unknown fails the check by design. Classifying a licence is a decision
someone has to make, and a repository that never forces that decision is how a copyleft dependency
ends up inside a proprietary addon unnoticed.

**A dependency whose licence the primary addon cannot absorb goes in a companion addon licensed to
match it**, reached through configuration parameters or a hook rather than by import — not into the
primary addon.
