#!/usr/bin/env python3
"""Refuse a dependency whose licence this addon's own licence cannot absorb.

The defect this exists to catch is invisible by default: an addon declared
'Other proprietary' while depending on an AGPL-3 module draws no complaint,
because Odoo does not check licences and neither does pylint_odoo. The
combination shows up only if something reads both manifests and knows which way
copyleft flows. It has shipped in a real repository at least once.

Two modes, one policy:

  * offline (no --addons-path) — the mode pre-commit uses. Dependencies outside
    this repository are resolved from KNOWN_LICENSES below, and an unrecognised
    one is an ERROR rather than a pass. Failing closed is the point: adding a
    dependency should force a decision about its licence, and "I did not know" is
    exactly the state that produced the original defect.
  * resolved (--addons-path a,b,c) — the mode CI uses, where Odoo core and the OCA
    sources are checked out anyway. Real manifests are read, the walk is
    transitive, and KNOWN_LICENSES is audited against them rather than consulted,
    so a wrong entry in the map is reported instead of being trusted forever. A
    dependency no path entry holds is an ERROR: reading it from the map instead
    would stop the walk there while the run still reports a transitive scan.

Two axes beyond the addon graph, added because the original defect's cause -- a
licence nobody had looked at -- is not specific to Odoo modules:

  * external_dependencies['python'], declared anywhere in an addon's install
    closure rather than only in its own manifest -- installing an addon installs
    its dependencies, so their wheels arrive under its licence too. Each entry is
    a PEP 508 requirement, as Odoo 18 reads it: extras, a version specifier and
    an environment marker are all valid, so the maps here are keyed by the
    canonical distribution name and pip is handed the whole expression. Same two
    modes: KNOWN_PYTHON_LICENSES offline, and --resolve-python in CI, which asks
    pip to resolve the wheels transitively and report their metadata without
    installing anything. Published licence metadata is free-form and often
    self-contradictory, so the map stays the authority; a wheel that disagrees
    with itself and has no entry there is refused rather than read at its
    friendliest.
  * licence texts, checked PER ADDON. Addons here are distributed individually --
    extracted with `git subtree` into a customer's addons path -- so a licence
    text kept at the repository root does not travel with the thing it licenses,
    and goes missing at delivery. Each addon therefore carries its own LICENSE.md
    and its own LICENSES/ copies, including the texts of licences it only links:
    every Odoo addon links LGPL-3 Community Edition, and LGPL-3 s4(b) wants the
    GPL text shipped alongside the LGPL.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys
import urllib.parse
from typing import NamedTuple

# Optional here because it is optional for Odoo. 18.0 dropped packaging from
# requirements.txt and reads a bare name with a stub of its own, raising for
# anything it cannot parse unaided -- and the odoo:18.0 image ships without it.
# Demanding it would make this gate refuse to run where Odoo runs fine; guessing
# without it would make the gate accept an entry Odoo would refuse to install. So
# the two states below are Odoo's own two states.
try:
    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.utils import canonicalize_name
except ImportError:
    Requirement = None

    class InvalidRequirement(Exception):
        pass

    def canonicalize_name(name: str) -> str:
        """PEP 503 in full: the whole rule is a case fold and one substitution."""
        return re.sub(r"[-_.]+", "-", name).lower()

# Odoo's fallback rule, kept identical to odoo/modules/module.py so that what
# this refuses without packaging is what an install would refuse.
BARE_REQUIREMENT = re.compile(r"[\w\-]+")

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Kept in step with check_manifests.py and update_readme.py, which each carry
# their own copy by the template's convention.
IGNORED = {".git", ".github", ".claude", "docs", "scripts", ".venv", "venv"}

# Odoo's manifest licence vocabulary, grouped by how copyleft flows.
STRONG_COPYLEFT = {
    "AGPL-3",
    "GPL-2", "GPL-2 or any later version",
    "GPL-3", "GPL-3 or any later version",
}
WEAK_COPYLEFT = {"LGPL-3"}
# Two strong-copyleft licences do not automatically absorb each other. GPL-2 has
# no "or later" clause to bridge with and GPL-3 is not backwards compatible, so
# the two cannot be combined in either direction; and AGPL-3 s13 conditions
# conveyance on offering source to whoever interacts with the work over a
# network, which nothing else in Odoo's vocabulary carries.
GPL_2_ONLY = {"GPL-2"}
GPL_3_LINEAGE = {"GPL-3", "GPL-3 or any later version", "AGPL-3"}
NETWORK_COPYLEFT = {"AGPL-3"}
PROPRIETARY = {"Other proprietary", "OPL-1", "OEEL-1"}
# Odoo's catch-all. It spans MIT through to something GPL-incompatible, so it can
# never be cleared automatically.
NEEDS_REVIEW = {"Other OSI approved licence"}
# Everything the rules below can reason about. Odoo's vocabulary holds no permissive
# value, so a spelling in none of these sets is not a lenient licence but one nobody
# has classified -- and since every rule asks whether a licence is in a set it
# recognises, an unclassified value clears them all rather than none. That is why it
# is refused on the dependency's side as well as on the addon's own.
CLASSIFIED = STRONG_COPYLEFT | WEAK_COPYLEFT | PROPRIETARY

# Licences of dependencies that live outside this repository. Only what this pack
# actually depends on: an entry nothing reaches is dead config, and the resolved
# mode below will not validate it either.
KNOWN_LICENSES = {
    # Odoo community core. Extend with what this repository actually depends on;
    # an entry nothing reaches is dead config, and the resolved mode below will
    # not validate it either.
    "base": "LGPL-3",
    "web": "LGPL-3",
    "mail": "LGPL-3",
}


# Python wheel licences. Spellings are as PyPI actually emits them, not as SPDX
# would prefer. Permissive is its own set because no rule refuses it; everything
# else is translated into Odoo's vocabulary and judged by copyleft_clash(), so the
# wheel path cannot grow a second, laxer copy of the copyleft rules. It had one:
# it collapsed the whole GPL family into "strong" and so cleared a GPL-2-only
# wheel under an AGPL-3 addon, which no version of either licence permits.
PY_PERMISSIVE = {
    "MIT", "MIT License",
    "BSD", "BSD License", "BSD-3-Clause", "BSD-2-Clause",
    "Apache-2.0", "Apache Software License",
    "ISC", "PSF-2.0", "Python Software Foundation License",
    "Unlicense", "Zlib",
}
# A wheel is only ever on the dependency side, where every weak-copyleft licence
# behaves alike -- it permits the combination -- so they collapse onto LGPL-3.
# The GPL spellings do not collapse: which version, and whether "or later", is
# exactly what decides whether two copyleft licences can meet at all.
PY_AS_ODOO = {
    "LGPL-3.0": "LGPL-3", "LGPL-2.1": "LGPL-3", "LGPLv3": "LGPL-3",
    "MPL-2.0": "LGPL-3", "Mozilla Public License 2.0": "LGPL-3",
    "GPL-2.0": "GPL-2", "GPL-2.0-only": "GPL-2", "GPLv2": "GPL-2",
    "GPL-2.0+": "GPL-2 or any later version",
    "GPL-2.0-or-later": "GPL-2 or any later version",
    "GPLv2+": "GPL-2 or any later version",
    "GPL-3.0": "GPL-3", "GPL-3.0-only": "GPL-3", "GPLv3": "GPL-3",
    "GPL-3.0+": "GPL-3 or any later version",
    "GPL-3.0-or-later": "GPL-3 or any later version",
    "GPLv3+": "GPL-3 or any later version",
    "AGPL-3.0": "AGPL-3", "AGPL-3.0-only": "AGPL-3",
    "AGPL-3.0-or-later": "AGPL-3", "AGPLv3": "AGPL-3", "AGPLv3+": "AGPL-3",
}
# The families normalise_py_license() collapses to. Only the transitive path uses
# these: a declared wheel is classified by KNOWN_PYTHON_LICENSES, whose exact
# spellings PY_AS_ODOO above holds. A wheel nothing declares has no agreed
# spelling to check against, so it is judged by family or not at all -- and a
# family names no version, which is why a strong-copyleft one is refused until
# somebody records the exact licence.
PY_STRONG_FAMILIES = {"agpl", "gpl"}
PY_CLEARED_FAMILIES = {"lgpl", "mit", "bsd", "apache", "mpl", "isc"}

# Licences of the wheels named in external_dependencies['python'], keyed by the
# canonical distribution name (PEP 503: lowercase, runs of -_. collapsed to -),
# which is what a requirement expression is read down to. Failing closed on an
# absent entry is the same policy as KNOWN_LICENSES, for the same reason.
KNOWN_PYTHON_LICENSES: dict[str, str] = {
    # Populate from external_dependencies['python']. Failing closed on an absent
    # entry is deliberate: "I did not know" is the state that produces the defect
    # this script exists to catch. Where a wheel publishes signals that disagree
    # with each other, the entry here is what decides between them.
}

# Which file under <addon>/LICENSES/ carries each licence's text. None means the
# text lives in the addon's own LICENSE.md, which is where a bespoke proprietary
# grant belongs -- there is no canonical file to copy for one.
#
# Every value in CLASSIFIED needs an entry, and check_license_texts() refuses a
# classified licence that has none rather than skipping it: a licence this script
# is willing to accept but has no text rule for ships with no terms at all, which
# is the one outcome the whole per-addon text axis exists to prevent. "or any
# later version" is a grant, not a second set of terms, so it wants the text of
# the version the addon is actually under.
LICENSE_TEXTS = {
    "AGPL-3": "AGPL-3.txt",
    "GPL-2": "GPL-2.txt",
    "GPL-2 or any later version": "GPL-2.txt",
    "GPL-3": "GPL-3.txt",
    "GPL-3 or any later version": "GPL-3.txt",
    "LGPL-3": "LGPL-3.txt",
    "OPL-1": "OPL-1.txt",
    "OEEL-1": "OEEL-1.txt",
    "Other proprietary": None,
}
# LGPL-3 s4(b) asks that a combined work ship the GPL as well as the LGPL, since
# the LGPL is written as a set of added permissions on top of it.
LICENSE_COMPANIONS = {"LGPL-3": ("GPL-3",)}

# Copyleft over a proprietary dependency, by (addon, dependency). Strong copyleft
# obliges the whole combined work, and a proprietary licence forbids releasing its
# half under it, so the arrangement is lawful only where one party owns both and
# can license its own work as it chooses. A manifest records licences, never
# ownership, so this script cannot tell a proprietary addon this repository owns
# from a third party's -- and clearing the direction rather than the pair would
# clear an OPL-1 or OEEL-1 module of somebody else's just as readily. Named pairs
# only, each one a decision somebody made; everything else is refused.
#
# Empty on purpose. An entry records a decision about two named addons in this
# repository, so a template carrying one would approve that pair for every
# repository generated from it. Adding one is not a formality either: it asserts
# an ownership fact this script cannot check, and where the proprietary half is
# licensed rather than owned outright the assertion is a legal question, not an
# engineering one. Record the reasoning next to the entry, and expect the NOTE it
# prints on every run to be the only reminder anyone gets.
REVIEWED_PROPRIETARY_EDGES: set[tuple[str, str]] = set()


class Problem:
    __slots__ = ("addon", "message", "fatal")

    def __init__(self, addon: str, message: str, *, fatal: bool = True):
        self.addon = addon
        self.message = message
        self.fatal = fatal


def read_manifest(path: pathlib.Path) -> dict:
    return ast.literal_eval(path.read_text(encoding="utf-8"))


def local_addons(root: pathlib.Path) -> dict[str, dict]:
    found = {}
    for path in sorted(root.iterdir()):
        manifest = path / "__manifest__.py"
        if path.is_dir() and path.name not in IGNORED and manifest.exists():
            try:
                found[path.name] = read_manifest(manifest)
            except Exception as exc:
                raise SystemExit(f"ERROR {path.name}/__manifest__.py: {exc}") from exc
    return found


def index_addons_path(addons_path: str) -> dict[str, pathlib.Path]:
    """Every module reachable on an --addons-path, by name.

    A path that is not there is fatal rather than skipped. Skipping it degrades
    this mode to the offline map -- no transitive walk, no audit of KNOWN_LICENSES
    against real manifests -- while main() goes on printing that dependencies were
    resolved transitively. A typo in ADDONS_PATH, or an image that moved its addons
    directory, would buy a passing release scan that checked nothing.
    """
    index: dict[str, pathlib.Path] = {}
    missing = []
    for entry in addons_path.split(","):
        entry = entry.strip()
        if not entry:
            continue
        base = pathlib.Path(entry).expanduser()
        if not base.is_dir():
            missing.append(entry)
            continue
        for candidate in sorted(base.iterdir()):
            try:
                is_addon = (candidate / "__manifest__.py").exists()
            except OSError:
                # An entry this process cannot stat cannot be audited either, and
                # skipping it is safe rather than silent: anything that depends on
                # it falls through to KNOWN_LICENSES, and an absent entry there is
                # already fatal.
                continue
            if is_addon:
                index.setdefault(candidate.name, candidate)
    if missing:
        raise SystemExit(
            f"ERROR --addons-path entries that are not directories: "
            f"{', '.join(repr(entry) for entry in missing)}. Resolved mode cannot "
            f"read manifests that are not there, and falling back to the offline "
            f"map would report success for a scan that never happened."
        )
    if not index:
        raise SystemExit(
            f"ERROR --addons-path={addons_path!r} holds no addon: nothing under it "
            f"contains a __manifest__.py. Point it at Odoo's addons directory and "
            f"each dependency source, as the CI job does."
        )
    return index


def own_license_problem(addon: str, own: str) -> Problem | None:
    """Whether `own` is a licence the branches below can reason about at all.

    Unclassified, an addon's own licence clears every branch rather than none of
    them: each one asks whether `own` is in a set it recognises, so a value in no
    set is a silent pass for any dependency whatsoever. That is the inverse of the
    policy the dependency side already runs on, and it is the same not-knowing
    that produced the original defect.
    """
    if own in NEEDS_REVIEW:
        return Problem(
            addon,
            f"declares {own!r} -- Odoo's catch-all, which spans permissive to "
            f"GPL-incompatible. Nothing can say which dependencies it may absorb, so "
            f"it clears all of them, including strong copyleft. Record the concrete "
            f"licence in the manifest.",
        )
    if own not in CLASSIFIED:
        return Problem(
            addon,
            f"declares {own!r}, which is not one of Odoo's manifest licence values "
            f"and which this script cannot classify -- leaving it a silent pass for "
            f"any dependency. Use the Odoo spelling, or add this one to "
            f"STRONG_COPYLEFT / WEAK_COPYLEFT / PROPRIETARY in "
            f"scripts/check_licenses.py.",
        )
    return None


class Clash(NamedTuple):
    """Why one licence cannot simply absorb another, and what would fix it."""

    why: str
    # A licence this addon could be relicensed to that would make the combination
    # lawful. None where relicensing is not an answer -- a proprietary addon is
    # not going to become AGPL-3, and nothing bridges GPL-2 to GPL-3.
    relicense_to: str | None = None


def copyleft_clash(own: str | None, other: str) -> Clash | None:
    """Whether a work licensed `own` may absorb one licensed `other`.

    The only place these rules live. A Python wheel's licence is translated into
    Odoo's vocabulary (PY_AS_ODOO) and judged here rather than by a second copy of
    them; the second copy is what let a GPL-2-only wheel clear an AGPL-3 addon.
    Only the directions that actually bite are encoded: a weak-copyleft dependency
    is fine everywhere, which is the whole purpose of the "Lesser" in LGPL and why
    most dependencies are unremarkable. Strong copyleft over a
    proprietary dependency is decided by ownership rather than by licence text and
    is handled by its caller, not here.
    """
    if own in PROPRIETARY and other in STRONG_COPYLEFT:
        return Clash("Strong copyleft cannot sit in a proprietary module's install closure.")
    if own in WEAK_COPYLEFT and other in STRONG_COPYLEFT:
        if other in GPL_2_ONLY:
            return Clash(
                "LGPL-3 is GPL-3 with added permissions, and GPL-2 carries no 'or "
                "later' clause to reach GPL-3 with, so there is no licence the "
                "combined work could be conveyed under."
            )
        # LGPL-3 s2 permits conveying under GPL-3, so that is what the combination
        # converts to -- including against a 'GPL-2 or later' dependency, which
        # upgrades rather than holding the result back at GPL-2. AGPL-3 is the
        # exception: its s13 survives the combination and names the result.
        combined = other if other in NETWORK_COPYLEFT else "GPL-3"
        return Clash(
            f"A combined work of LGPL-3 and {other!r} must be distributed under "
            f"{combined}.",
            combined,
        )
    if own in STRONG_COPYLEFT and other in STRONG_COPYLEFT:
        if (own in GPL_2_ONLY and other in GPL_3_LINEAGE) or (
            own in GPL_3_LINEAGE and other in GPL_2_ONLY
        ):
            # Adding 'or later' reaches GPL-3 and settles the ordinary case, but
            # against AGPL-3 it only advances the caller to the s13 branch below,
            # which demands an AGPL-3 declaration anyway. Naming AGPL-3 here is
            # the same answer one refusal earlier; advice whose result is another
            # refusal teaches the reader to stop reading them.
            if own not in GPL_2_ONLY:
                relicense = None
            elif other in NETWORK_COPYLEFT:
                relicense = other
            else:
                relicense = "GPL-2 or any later version"
            return Clash(
                "GPL-2 carries no 'or later' clause, so there is no version of "
                "either licence the combined work could be conveyed under.",
                relicense,
            )
        if other in NETWORK_COPYLEFT and own not in NETWORK_COPYLEFT:
            return Clash(
                f"The combination is permitted, but AGPL-3 s13 conditions it on "
                f"offering source to everyone who interacts with the work over a "
                f"network, and an Odoo instance is network-accessed by definition. "
                f"Declaring {own!r} does not announce that obligation to whoever "
                f"receives the result.",
                other,
            )
    return None


def proprietary_dependency_problem(
    addon: str, own: str, dep: str, dep_license: str
) -> Problem:
    """A copyleft addon over a proprietary dependency: sound only by ownership.

    Refused unless the pair is one somebody decided on. It used to be a blanket
    NOTE, which read the shipped bridge's reasoning onto every such edge --
    including an AGPL-3 addon reaching third-party OPL-1 or OEEL-1 code, where
    nobody owns both halves and the combination cannot be distributed at all.
    """
    if (addon, dep) in REVIEWED_PROPRIETARY_EDGES:
        return Problem(
            addon,
            f"is {own!r} and depends on {dep!r}, which is {dep_license!r}. This is "
            f"sound only where one party holds the copyright on both and can license "
            f"its own work as it chooses; it would not be if the proprietary addon "
            f"were a third party's. Somebody recorded that as decided in "
            f"REVIEWED_PROPRIETARY_EDGES. Recorded, not blocking.",
            fatal=False,
        )
    return Problem(
        addon,
        f"is {own!r} and depends on {dep!r}, which is {dep_license!r}. Strong "
        f"copyleft obliges the whole combined work and {dep_license!r} forbids "
        f"releasing {dep!r} under it, so this is lawful only where one party owns "
        f"both. Nothing in a manifest records who owns {dep!r}. Where this "
        f"repository's licensor owns it and the combination has been reviewed, add "
        f"({addon!r}, {dep!r}) to REVIEWED_PROPRIETARY_EDGES in "
        f"scripts/check_licenses.py, with the reasoning beside it; otherwise drop "
        f"the dependency.",
    )


def compatibility_problem(addon: str, own: str, dep: str, dep_license: str) -> Problem | None:
    """Whether `addon`, licensed `own`, may depend on `dep`, licensed `dep_license`."""
    if dep_license in NEEDS_REVIEW:
        return Problem(
            addon,
            f"depends on {dep!r}, whose licence is {dep_license!r} — Odoo's catch-all, "
            f"which spans permissive to GPL-incompatible. Determine the real licence "
            f"and record it in scripts/check_licenses.py.",
        )
    if dep_license not in CLASSIFIED:
        return Problem(
            addon,
            f"depends on {dep!r}, whose licence is {dep_license!r} -- not one of "
            f"Odoo's manifest licence values, and not one this script can classify, "
            f"so every rule below is false and the dependency clears any addon "
            f"whatsoever. Correct the spelling where it is declared, or add this one "
            f"to STRONG_COPYLEFT / WEAK_COPYLEFT / PROPRIETARY in "
            f"scripts/check_licenses.py.",
        )
    if own in STRONG_COPYLEFT and dep_license in PROPRIETARY:
        return proprietary_dependency_problem(addon, own, dep, dep_license)
    clash = copyleft_clash(own, dep_license)
    if clash is None:
        return None
    remedy = (
        f"Relicense this addon {clash.relicense_to!r}, or move the dependency into a "
        f"companion that is." if clash.relicense_to else
        f"Move the dependency into a companion addon licensed {dep_license!r} and "
        f"reach it by parameter or hook rather than by import."
    )
    return Problem(
        addon,
        f"is {own!r} but depends on {dep!r}, which is {dep_license!r}. {clash.why} "
        f"{remedy}",
    )


def python_compatibility_problem(
    addon: str, own: str | None, dist: str, lic: str
) -> Problem | None:
    """Whether `addon`, licensed `own`, may depend on the wheel `dist`."""
    equivalent = PY_AS_ODOO.get(lic)
    if equivalent is None:
        if lic in PY_PERMISSIVE:
            return None
        return Problem(
            addon,
            f"requires the Python package {dist!r}, recorded as {lic!r}, which this "
            f"script does not classify. Add the spelling to PY_PERMISSIVE, or to "
            f"PY_AS_ODOO against the Odoo licence value carrying the same "
            f"obligations, in scripts/check_licenses.py.",
        )
    clash = copyleft_clash(own, equivalent)
    if clash is None:
        return None
    remedy = (
        f"Relicense this addon {clash.relicense_to!r}, or find a differently licensed "
        f"package." if clash.relicense_to else
        f"Find a differently licensed package, or move the feature into an addon "
        f"licensed to carry {lic!r}."
    )
    return Problem(
        addon,
        f"is {own!r} but requires the Python package {dist!r}, which is {lic!r}. "
        f"{clash.why} {remedy}",
    )


def declared_elsewhere(problem: Problem, addon: str, source: str) -> Problem:
    """Name the manifest a wheel came from, where it is not this addon's own.

    A wheel is judged against the licence of the addon whose install closure
    carries it, but it is fixed in the manifest that asks for it, and a refusal
    that sends the reader to the wrong file is one they cannot act on.
    """
    if source == addon:
        return problem
    return Problem(
        problem.addon,
        f"{problem.message} The requirement is declared by {source!r}, which "
        f"{addon} depends on -- installing {addon} installs it too.",
        fatal=problem.fatal,
    )


def transitive_python_problem(
    addon: str, own: str | None, dist: str, reported: str | None
) -> Problem | None:
    """Whether `addon` may carry `dist`, which no manifest declares but pip resolves.

    A licence that arrives two hops away binds exactly as one that arrives in the
    manifest, so the same policy applies. The map stays the authority where it has
    an entry; otherwise the only signal is what the distribution published.
    """
    mapped = KNOWN_PYTHON_LICENSES.get(dist)
    if mapped is not None:
        return python_compatibility_problem(addon, own, dist, mapped)
    if reported is None:
        return Problem(
            addon,
            f"pulls in the Python package {dist!r} transitively, and pip reports no "
            f"licence for it. Check pip's own version first: before 25.0 it drops the "
            f"PEP 639 License-Expression field, so wheels that do declare a licence "
            f"read as though they declare none. If it really publishes nothing, read "
            f"its source and record the licence in KNOWN_PYTHON_LICENSES in "
            f"scripts/check_licenses.py.",
        )
    family = normalise_py_license(reported)
    if family in PY_STRONG_FAMILIES and own in PROPRIETARY | WEAK_COPYLEFT:
        return Problem(
            addon,
            f"is {own!r} and pulls in the Python package {dist!r} transitively, which "
            f"publishes its licence as {reported!r}. Strong copyleft cannot sit under "
            f"{own!r} whether or not a manifest names it. Pin a version or an "
            f"alternative that does not reach it, or move the feature into an addon "
            f"licensed to carry it.",
        )
    if family in PY_STRONG_FAMILIES and own in STRONG_COPYLEFT:
        # A family names no version, and between two strong copyleft licences the
        # version is the whole question: GPL-2 and the GPL-3 lineage cannot be
        # combined in either direction, and AGPL-3 s13 binds a GPL work that meets
        # it. Neither is decidable from "gpl", so this is refused until somebody
        # reads the wheel -- one map entry, after which the rules above apply in
        # full.
        return Problem(
            addon,
            f"is {own!r} and pulls in the Python package {dist!r} transitively, which "
            f"publishes its licence as {reported!r} -- strong copyleft, but naming no "
            f"version, and which version decides whether {own!r} may carry it at all. "
            f"Record the exact licence in KNOWN_PYTHON_LICENSES in "
            f"scripts/check_licenses.py.",
        )
    if family not in PY_STRONG_FAMILIES | PY_CLEARED_FAMILIES:
        return Problem(
            addon,
            f"pulls in the Python package {dist!r} transitively, which publishes its "
            f"licence as {reported!r} -- a spelling this script does not classify. "
            f"Decide what it means and record it in KNOWN_PYTHON_LICENSES in "
            f"scripts/check_licenses.py.",
        )
    return None


class PyRequirement(NamedTuple):
    """One external_dependencies['python'] entry, parsed as Odoo 18 parses it.

    Odoo reads each entry with packaging.Requirement where packaging is
    installed, honouring extras, version specifiers and environment markers, so
    'requests==2.31.0', 'requests[socks]' and 'pywin32; sys_platform == "win32"'
    are all valid manifest values -- and refuses anything beyond a bare name where
    it is not. parse_py_requirement() below follows both halves of that. A
    licence attaches to the distribution and not to the constraint on it, so the
    maps here are keyed by the canonical name while pip is given the whole
    expression -- reading the expression as a name refuses a wheel that is
    already classified, which is a false failure in the one place false failures
    teach people to bypass the gate.

    A marker is left to pip, which evaluates it against the environment the scan
    ran in and reports that environment. Classification does not consult it: what
    a wheel is licensed under does not depend on the platform that installs it,
    and skipping an entry gated to another platform would clear a wheel that
    still ships under this addon's licence wherever the marker does match.
    """

    name: str
    expression: str
    # The manifest that asks for it, which is not always the addon under
    # judgment: installing an addon installs its whole closure.
    source: str


class RequirementProblem(Exception):
    """Why one external_dependencies['python'] entry cannot be judged."""


def parse_py_requirement(expression: str, source: str) -> PyRequirement:
    """Raises RequirementProblem, phrased for whichever of the two causes it is."""
    if Requirement is None:
        if not BARE_REQUIREMENT.fullmatch(expression):
            raise RequirementProblem(
                "which needs 'packaging' to read, and this environment has none. "
                "Odoo 18.0 and later ship without packaging as well and parse only "
                "a bare name unaided, so an expression needing it is a liability "
                "there whatever this repository targets. Install packaging where "
                "this runs, or drop the version specifier, extra or marker."
            )
        name = expression
    else:
        try:
            name = Requirement(expression).name
        except InvalidRequirement as exc:
            raise RequirementProblem(
                f"which is not a valid PEP 508 requirement: {exc}. Odoo 18 parses "
                f"every external_dependencies['python'] entry with "
                f"packaging.Requirement and raises on this one, so the addon would "
                f"not install."
            ) from exc
    return PyRequirement(str(canonicalize_name(name)), expression, source)


class ResolvedDist(NamedTuple):
    # The version matters as much as the licence: a requirement that pins nothing
    # resolves to whatever the index offers, so a record naming only the licence
    # cannot say which release was audited once the wheel moves on.
    version: str | None
    license: str | None
    # The signals as published, when they disagree with each other. Carried so a
    # wheel nobody has read cannot be cleared by picking the friendliest of them.
    conflict: str | None = None
    # Which artefact was actually read, and its hash. pip is given no index, so
    # without this the record cannot say whether a wheel came from PyPI or from
    # the mirror or private index pip's configuration selected.
    url: str | None = None
    digest: str | None = None


class Resolution(NamedTuple):
    """What one pip resolution answered, and the ground it answered on."""

    dists: dict[str, ResolvedDist]
    # Both are properties of the run rather than of the manifests, and the answer
    # cannot be read without them: which pip answered decides whether a PEP 639
    # licence expression was relayed at all, and the marker environment decides
    # which requirements were in scope.
    pip_version: str | None
    environment: dict[str, str]


def artefact_url(download_info: dict) -> str | None:
    """Where the artefact came from, with anything credential-bearing dropped.

    An index URL can carry a token in userinfo or in the query string, and this
    goes into a record that is attached to releases and read by people who should
    not thereby be handed the credential that produced it.
    """
    url = (download_info or {}).get("url")
    if not url:
        return None
    split = urllib.parse.urlsplit(url)
    host = split.hostname or ""
    if split.port:
        host = f"{host}:{split.port}"
    return urllib.parse.urlunsplit((split.scheme, host, split.path, "", ""))


def dist_from_entry(entry: dict) -> ResolvedDist:
    """One wheel's version, licence, self-disagreement and provenance, from pip's
    report entry.

    Kept apart from the pip call because these rules decide whether a wheel is
    cleared, and nothing that decides that should need a network to exercise.
    """
    meta = entry.get("metadata") or {}
    download = entry.get("download_info") or {}
    signals = []
    for key in ("license_expression", "license"):
        value = (meta.get(key) or "").strip()
        # Some projects paste their whole licence text into the field.
        if value and "\n" not in value and len(value) < 60:
            signals.append(value)
    signals.extend(
        c.rsplit("::", 1)[-1].strip()
        for c in meta.get("classifier", []) or []
        if c.startswith("License ::")
    )
    # The most restrictive signal wins, not the first one listed: a wheel that
    # publishes 'MIT' beside a GPL classifier has to be read as the GPL one until
    # somebody decides otherwise in KNOWN_PYTHON_LICENSES. That settles only the
    # copyleft families, so any other disagreement is carried out as a conflict
    # instead of being resolved to whichever signal happened to come first.
    strongest = next(
        (s for s in signals if normalise_py_license(s) in PY_STRONG_FAMILIES), None
    )
    return ResolvedDist(
        version=meta.get("version"),
        license=strongest or (signals[0] if signals else None),
        conflict=(
            " / ".join(signals)
            if len({normalise_py_license(s) for s in signals}) > 1
            else None
        ),
        url=artefact_url(download),
        digest=(download.get("archive_info") or {}).get("hash") or None,
    )


def conflict_problem(dist: str, found: ResolvedDist) -> Problem | None:
    """Whether `dist`, whose published signals disagree, can be cleared anyway.

    Only KNOWN_PYTHON_LICENSES and the strongest-signal rule decide a conflict,
    and the latter reaches GPL and AGPL only. A permissive field beside a
    proprietary classifier is settled by neither, and clearing it on the
    permissive reading is the fail-open this gate exists to refuse.
    """
    if not found.conflict:
        return None
    decided = KNOWN_PYTHON_LICENSES.get(dist)
    if decided is not None:
        return Problem(
            "scripts/check_licenses.py",
            f"{dist} publishes licence signals that disagree: {found.conflict}. "
            f"KNOWN_PYTHON_LICENSES records {decided!r} as the reading. Recorded, "
            f"not blocking.",
            fatal=False,
        )
    if normalise_py_license(found.license or "") in PY_STRONG_FAMILIES:
        return None
    return Problem(
        "scripts/check_licenses.py",
        f"{dist} publishes licence signals that disagree: {found.conflict}, and "
        f"nothing decides between them -- taking the strongest settles GPL and AGPL "
        f"only. Read the project's own licence file and record the answer in "
        f"KNOWN_PYTHON_LICENSES in scripts/check_licenses.py.",
    )


def resolve_python_licenses(requirements: list[str]) -> Resolution:
    """Ask pip to resolve `requirements` transitively and report their licences.

    `requirements` are whole PEP 508 expressions, so pip applies each specifier
    and evaluates each marker itself; the environment it evaluated against comes
    back in the answer.

    Uses --dry-run --report, so nothing is installed and nothing is imported. No
    index is named, which means pip's own configuration decides where this
    resolves from -- PIP_INDEX_URL, pip.conf and a private mirror all apply, and
    each wheel's artefact URL is recorded rather than assumed. The licence signal
    is whatever the distribution published: a license/license_expression field,
    or the License:: classifiers, and None where pip reports neither. Returns the
    whole closure -- the requirements and everything they drag in.
    """
    import json
    import subprocess

    if not requirements:
        return Resolution({}, None, {})

    # --dry-run --report landed in pip 22.2. Without this check the failure is
    # pip's full usage dump under "no such option", which says nothing useful.
    version = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True, text=True,
    ).stdout.split()
    if len(version) > 1:
        try:
            major, minor = (int(part) for part in version[1].split(".")[:2])
        except ValueError:
            major = minor = 0
        if (major, minor) < (22, 2):
            raise SystemExit(
                f"ERROR --resolve-python needs pip >= 22.2 for --dry-run --report; "
                f"{sys.executable} has pip {version[1]}. Upgrade it, or run this in a "
                f"virtualenv. The offline mode (no --resolve-python) needs no pip."
            )

    proc = subprocess.run(
        # --ignore-installed because the report omits whatever the environment
        # already holds, and the odoo images ship several common wheels: without
        # it, which wheels get audited depends on the image rather than on the
        # manifests, and a wheel the image happens to carry is never audited at
        # all. The versions this resolves are therefore a scan-time answer rather
        # than any deployment's, which is what python_resolution records.
        [sys.executable, "-m", "pip", "install", "--dry-run", "--quiet",
         "--ignore-installed", "--report", "-", *sorted(requirements)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "ERROR --resolve-python: pip could not resolve "
            f"{sorted(requirements)}:\n{proc.stderr.strip()[-2000:]}"
        )

    # Recorded even where a wheel published nothing at all -- it is in the closure
    # either way, and dropping it would hide the wheel nobody classified.
    report = json.loads(proc.stdout)
    resolved: dict[str, ResolvedDist] = {}
    for entry in report.get("install", []):
        name = (entry.get("metadata") or {}).get("name") or ""
        resolved[str(canonicalize_name(name))] = dist_from_entry(entry)
    return Resolution(
        resolved, report.get("pip_version"), report.get("environment") or {}
    )


def normalise_py_license(value: str) -> str:
    """Collapse PyPI's spellings far enough to compare two signals for agreement."""
    text = value.strip().rstrip(".").lower()
    text = text.removeprefix("osi approved").strip(" :")
    squashed = text.replace("-", "").replace(" ", "")
    # PyPI's trove list spells Affero out in full and only sometimes appends the
    # abbreviation, so "GNU Affero General Public License v3" carries neither
    # "agpl" nor "gpl" as a substring -- the one family that must never be missed.
    if "affero" in squashed:
        return "agpl"
    for family in ("agpl", "lgpl", "gpl", "mit", "bsd", "apache", "mpl", "isc"):
        if family in squashed:
            return family
    # The same trap one spelling further out. PyPI's classifiers do append the
    # abbreviation for the GPL and the LGPL -- which is why only Affero needed the
    # case above -- but a free-form `license` field is under no such discipline,
    # and "GNU General Public License v3" carries no "gpl" either. Checked after
    # the loop so an abbreviation, where there is one, still decides; and "lesser"
    # first, so the LGPL is not read as the GPL it is written on top of.
    if "generalpubliclicense" in squashed:
        return "lgpl" if "lesser" in squashed else "gpl"
    return text


class PythonScan(NamedTuple):
    problems: list[Problem]
    # Per addon, every wheel pip put in its install closure with what that wheel
    # published. Empty offline, where there is nothing to resolve against.
    closures: dict[str, dict[str, ResolvedDist]]
    # The pip that answered and the marker environment it evaluated against, for
    # the release record. None offline: nothing was resolved.
    pip_version: str | None = None
    environment: dict[str, str] | None = None


def check_python_dependencies(
    addons: dict[str, dict],
    requirements: dict[str, dict[str, PyRequirement]],
    *,
    resolve: bool,
) -> PythonScan:
    """`requirements` maps each addon to the wheels its install closure needs, by
    canonical distribution name, each carrying the expression a manifest wrote and
    the manifest that wrote it."""
    closures: dict[str, dict[str, ResolvedDist]] = {}
    merged: dict[str, ResolvedDist] = {}
    pip_version: str | None = None
    environment: dict[str, str] | None = None
    if resolve:
        # Resolved per addon rather than once for the union: a wheel one addon
        # drags in is not evidence about another, and a shared resolution would
        # have to blame it on both or on neither.
        by_requirements: dict[frozenset[str], Resolution] = {}
        for addon in sorted(addons):
            # Whole expressions, so pip applies the specifiers and the markers.
            required = frozenset(
                requirement.expression
                for requirement in requirements.get(addon, {}).values()
            )
            if not required:
                continue
            if required not in by_requirements:
                by_requirements[required] = resolve_python_licenses(sorted(required))
            resolution = by_requirements[required]
            closures[addon] = resolution.dists
            merged.update(resolution.dists)
            # The same pip and the same environment for every resolution in a
            # run, so whichever answered describes them all.
            pip_version = resolution.pip_version
            environment = resolution.environment

    problems: list[Problem] = []
    # A wrong map entry silently clears a real incompatibility, so audit the map
    # against what pip actually reported wherever both exist.
    for dist, expected in sorted(KNOWN_PYTHON_LICENSES.items()):
        found = merged.get(str(canonicalize_name(dist)))
        actual = found.license if found else None
        if actual and normalise_py_license(actual) != normalise_py_license(expected):
            problems.append(Problem(
                "scripts/check_licenses.py",
                f"KNOWN_PYTHON_LICENSES says {dist} is {expected!r} but its published "
                f"metadata says {actual!r}. Correct the map.",
            ))

    # Once per wheel, not once per addon: a wheel's own metadata does not depend
    # on which addon dragged it in.
    for dist, found in sorted(merged.items()):
        problem = conflict_problem(dist, found)
        if problem:
            problems.append(problem)

    for addon, manifest in sorted(addons.items()):
        own = manifest.get("license")
        declared = requirements.get(addon, {})
        for dist, requirement in sorted(declared.items()):
            # Named where the manifest wrote something other than the bare
            # distribution -- the map is keyed by the name, so a reader sent to
            # add 'requests' has to be able to find 'requests[socks]'.
            as_written = (
                "" if requirement.expression == dist
                else f", declared as {requirement.expression!r}"
            )
            lic = KNOWN_PYTHON_LICENSES.get(dist)
            if lic is None:
                problems.append(declared_elsewhere(Problem(
                    addon,
                    f"requires the Python package {dist!r}{as_written}, whose licence "
                    f"is unknown. Determine it and record it in "
                    f"KNOWN_PYTHON_LICENSES in scripts/check_licenses.py.",
                ), addon, requirement.source))
                continue
            problem = python_compatibility_problem(addon, own, dist, lic)
            if problem:
                problems.append(declared_elsewhere(problem, addon, requirement.source))

        for dist, found in sorted(closures.get(addon, {}).items()):
            if dist in declared:
                continue
            problem = transitive_python_problem(addon, own, dist, found.license)
            if problem:
                problems.append(problem)
    return PythonScan(problems, closures, pip_version, environment)


def check_license_texts(
    addons: dict[str, dict], reached: dict[str, set[str]]
) -> list[Problem]:
    """Every licence an addon is under or links must be readable inside that addon.

    `reached[addon]` holds the licences of everything that addon depends on, not
    just its own: a proprietary addon that links LGPL-3 libraries must carry
    LGPL-3's text beside it even though it declares something else.

    The check is per addon rather than per repository on purpose. An addon leaves
    here on its own, so a text that lives only at the repository root is a text
    the recipient never sees.
    """
    problems: list[Problem] = []
    for addon, manifest in sorted(addons.items()):
        directory = ROOT / addon
        own = manifest.get("license")
        # An addon's own terms must be beside it whatever the licence: a full text
        # for the standard ones, a written grant for a proprietary one.
        if not (directory / "LICENSE.md").exists():
            problems.append(Problem(
                addon,
                "has no LICENSE.md. Addons here are distributed individually, so "
                "each one carries its own terms; a licence file at the repository "
                "root does not survive `git subtree split`.",
            ))
        # Linking a licence is not the same as declaring it, and both oblige.
        wanted = {own} | reached.get(addon, set())
        for licence in sorted(filter(None, wanted)):
            if licence not in LICENSE_TEXTS:
                # A licence this script classifies is one it is willing to accept,
                # so an accepted licence with no text rule ships with no terms and
                # nothing says so. Unclassified values are left alone: they are
                # already fatal above, and a second refusal naming a different file
                # to edit only obscures the first.
                if licence in CLASSIFIED:
                    problems.append(Problem(
                        addon,
                        f"is under or links {licence!r}, which LICENSE_TEXTS in "
                        f"scripts/check_licenses.py has no entry for, so no text is "
                        f"required of this addon and none is checked. Add the entry, "
                        f"with None where the terms belong in the addon's own "
                        f"LICENSE.md.",
                    ))
                continue
            for name in (licence, *LICENSE_COMPANIONS.get(licence, ())):
                filename = LICENSE_TEXTS.get(name)
                if filename is None:
                    continue
                if not (directory / "LICENSES" / filename).exists():
                    because = (
                        f"it is under {name!r}" if name == own
                        else f"it links {licence!r}"
                    )
                    companion = (
                        ", and LGPL-3 s4(b) requires the GPL text alongside the LGPL"
                        if name != licence else ""
                    )
                    problems.append(Problem(
                        addon,
                        f"is missing LICENSES/{filename}, but {because}{companion}. "
                        f"Copy the text into {addon}/LICENSES/ so it travels with the "
                        f"addon.",
                    ))
        # A relative link that climbs out of the addon is dead once extracted.
        licence_file = directory / "LICENSE.md"
        if licence_file.exists() and "](../" in licence_file.read_text(encoding="utf-8"):
            problems.append(Problem(
                addon,
                "LICENSE.md links outside the addon directory with '](../'. That "
                "link is dead as soon as the addon is extracted on its own; inline "
                "what it points at, or name the file without linking to it.",
            ))
    return problems


class ScannedTree(NamedTuple):
    # What to record. A '-dirty' suffix follows `git describe --dirty`: a record
    # naming a commit whose content it does not hold is worse than one naming no
    # commit at all, because only the first looks answerable.
    commit: str | None
    dirty: bool


def head_commit(explicit: str | None) -> ScannedTree:
    """The commit whose tree was scanned, and whether that tree was clean.

    The odoo images carry no git, and actions/checkout falls back to a REST-API
    tarball where git is missing, leaving no .git to read either -- so that job
    has to pass the commit in rather than have it discovered, and an explicit
    value is taken on trust because nothing on hand could check it.
    """
    if explicit:
        return ScannedTree(explicit, False)
    import subprocess

    def git(*args: str) -> str | None:
        try:
            done = subprocess.run(
                ["git", "-C", str(ROOT), *args], capture_output=True, text=True
            )
        except OSError:
            return None
        return done.stdout if done.returncode == 0 else None

    head = git("rev-parse", "HEAD")
    if not head or not head.strip():
        return ScannedTree(None, False)
    sha = head.strip()
    # None means git could not answer, which is not evidence of a clean tree.
    status = git("status", "--porcelain")
    dirty = status is None or bool(status.strip())
    return ScannedTree(f"{sha}-dirty" if dirty else sha, dirty)


def python_record(
    required: dict[str, PyRequirement], closure: dict[str, ResolvedDist]
) -> dict[str, dict]:
    """Every wheel in this addon's install closure, with the artefact that was read.

    `required` is the whole install closure's requirements, not just the ones this
    addon's own manifest names, for the reason `odoo_closure` is a closure too: a
    wheel that arrives with a dependency ships exactly as one declared here.

    The version names the release whose metadata produced the licence beside it,
    and nothing more: the release the manifest pins where it pins one, and
    otherwise whatever pip's index offered when the scan ran, which is not
    necessarily what the deployment that installs the addon later holds. The
    inventory says so in `python_resolution`, because a version in a compliance
    record reads as a bill of materials unless it is told otherwise, and `url`
    and `hash` name the artefact rather than leaving its origin to be assumed.
    Offline there is no closure to resolve, so this degrades to the required
    wheels with nothing resolved -- the same reach the offline mode has
    everywhere else, rather than a silent empty answer that would read as "none".
    """
    if not closure:
        return {
            dist: {
                "version": None,
                "license": KNOWN_PYTHON_LICENSES.get(dist),
                "url": None,
                "hash": None,
            }
            for dist in sorted(required)
        }
    return {
        dist: {
            "version": found.version,
            "license": KNOWN_PYTHON_LICENSES.get(dist) or found.license,
            "url": found.url,
            "hash": found.digest,
        }
        for dist, found in sorted(closure.items())
    }


# What `python_closure` is evidence of. Spelled out in the file rather than left
# to whoever opens it: a compliance record that shows a version without saying
# where it came from invites being read as a bill of materials for a deployment
# it never looked at.
PYTHON_RESOLUTION_BASIS = {
    True: "pip --dry-run --report with --ignore-installed, resolved against "
          "whichever index pip was configured to use on the machine that ran the "
          "scan. No --index-url is passed, so PIP_INDEX_URL, pip.conf and a "
          "private mirror all apply and this is not necessarily PyPI; each "
          "wheel's 'url' and 'hash' record the artefact that was actually read. "
          "A version is the release that resolved when the scan ran -- the one "
          "the requirement pins where it pins one, otherwise whatever the index "
          "then offered -- and not the release any particular deployment holds. "
          "'environment' is the marker environment pip evaluated, so a "
          "requirement gated to another platform is absent from the closure while "
          "still being classified.",
    False: "offline: the wheels the manifests name, with the licences "
           "KNOWN_PYTHON_LICENSES records. Nothing was resolved, so no version, "
           "artefact or hash is known and the closure reaches only what a "
           "manifest declares.",
}


def write_inventory(path: str, addons: dict[str, dict], license_of, *,
                    commit: str | None,
                    resolved_python: bool,
                    odoo_closures: dict[str, set[str]],
                    requirements: dict[str, dict[str, PyRequirement]],
                    python_closures: dict[str, dict[str, ResolvedDist]],
                    pip_version: str | None,
                    environment: dict[str, str] | None) -> None:
    import datetime
    import json

    inventory = {
        # The commit, not a path: a release record has to stay answerable from
        # somewhere other than the machine that produced it.
        "commit": commit,
        "python_resolution": {
            "mode": "resolved" if resolved_python else "declared",
            "basis": PYTHON_RESOLUTION_BASIS[resolved_python],
            # The moment the resolver answered, which is the only thing that makes
            # a resolved version reproducible or contestable later.
            "resolved_at": (
                datetime.datetime.now(datetime.timezone.utc)
                .replace(microsecond=0).isoformat()
                if resolved_python else None
            ),
            # The ground the answer stands on. Which pip ran decides whether a
            # PEP 639 licence expression was relayed at all -- before 25.0 it is
            # dropped, so a wheel can read as unlicensed here for a reason that
            # has nothing to do with the wheel -- and the marker environment
            # decides which requirements were in scope.
            "pip_version": pip_version,
            "environment": environment or None,
        },
        "addons": {
            name: {
                "version": manifest.get("version"),
                "license": manifest.get("license"),
                # The install closure, not the manifest line. A licence that
                # arrives two hops away binds exactly as one that is declared, and
                # naming only the declaration would under-report it for the
                # transitive licences that are hardest to reconstruct afterwards.
                "odoo_closure": {
                    dep: license_of(dep) for dep in sorted(odoo_closures.get(name, ()))
                },
                "python_closure": python_record(
                    requirements.get(name, {}), python_closures.get(name, {})
                ),
                # Per addon, since each is delivered on its own.
                "license_texts": sorted(
                    p.name for p in (ROOT / name / "LICENSES").glob("*.txt")
                ),
            }
            for name, manifest in sorted(addons.items())
        },
    }
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(f"  (licence inventory written to {path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--addons-path",
        help="Comma-separated addon directories, every one of which must exist. "
             "When given, dependency licences are read from real manifests, the "
             "walk is transitive, and KNOWN_LICENSES is checked against them.",
    )
    parser.add_argument(
        "--resolve-python",
        action="store_true",
        help="Ask pip to resolve external_dependencies['python'] transitively and "
             "audit KNOWN_PYTHON_LICENSES against the published metadata. Needs "
             "network access and pip >= 22.2; nothing is installed.",
    )
    parser.add_argument(
        "--commit",
        metavar="SHA",
        help="Commit to record in the inventory. Discovered from git when absent, "
             "which a container without git, or a tarball checkout, cannot do.",
    )
    parser.add_argument(
        "--inventory",
        metavar="PATH",
        help="Write every licence in play to PATH as JSON: the addons' own, their "
             "Odoo dependencies' and their Python packages'. This is the record to "
             "attach to a release, so which licences applied at a commit stays "
             "answerable later. Its Python versions and artefacts are the "
             "resolver's answer at scan time, against whichever index pip was "
             "configured to use, and not a deployment's inventory -- the file "
             "states which.",
    )
    args = parser.parse_args()

    addons = local_addons(ROOT)
    if not addons:
        print("No addons discovered; nothing to check.")
        return 0

    index = index_addons_path(args.addons_path) if args.addons_path else {}
    resolved_cache: dict[str, str | None] = {}

    def license_of(name: str) -> str | None:
        if name in addons:
            return addons[name].get("license")
        if name in resolved_cache:
            return resolved_cache[name]
        value = None
        if name in index:
            try:
                value = read_manifest(index[name] / "__manifest__.py").get("license")
            except Exception:
                value = None
        if value is None:
            value = KNOWN_LICENSES.get(name)
        resolved_cache[name] = value
        return value

    def depends_of(name: str) -> list[str]:
        if name in addons:
            return list(addons[name].get("depends", []))
        if name in index:
            try:
                return list(read_manifest(index[name] / "__manifest__.py").get("depends", []))
            except Exception:
                return []
        return []

    problems: list[Problem] = []
    # Per addon, because the licence texts an addon must ship are decided by that
    # addon's own dependencies -- it is distributed on its own.
    reached_licenses: dict[str, set[str]] = {name: set() for name in addons}
    # The walk below already computes each addon's transitive reach; the release
    # record needs the same set, so it is kept rather than discarded.
    odoo_closures: dict[str, set[str]] = {}

    # A wrong map entry is worse than a missing one: it silently clears a real
    # incompatibility. Only checkable where the real manifest is present.
    for name, expected in sorted(KNOWN_LICENSES.items()):
        if name in index:
            actual = read_manifest(index[name] / "__manifest__.py").get("license")
            if actual != expected:
                problems.append(Problem(
                    "scripts/check_licenses.py",
                    f"KNOWN_LICENSES says {name} is {expected!r} but its manifest says "
                    f"{actual!r}. Correct the map.",
                ))

    for addon, manifest in addons.items():
        own = manifest.get("license")
        if not own:
            problems.append(Problem(addon, "declares no 'license' in its manifest."))
            continue
        # Reported rather than skipped: the walk below still decides which licence
        # texts this addon has to ship and what the release record says it reaches,
        # and neither answer improves by being left blank.
        own_problem = own_license_problem(addon, own)
        if own_problem:
            problems.append(own_problem)

        # Transitive only where manifests are real; offline, the map holds direct
        # dependencies and pretending to walk further would invent reassurance.
        seen: set[str] = set()
        queue = list(manifest.get("depends", []))
        while queue:
            dep = queue.pop(0)
            if dep in seen:
                continue
            seen.add(dep)
            # Resolved mode promises real manifests. A dependency on no path entry
            # would take its licence from the offline map and stop the walk there,
            # while the run goes on reporting a transitive scan -- an incomplete
            # ADDONS_PATH buying the same green tick a complete one gets. Reported
            # rather than judged on the map, which this mode audits rather than
            # trusts.
            if args.addons_path and dep not in addons and dep not in index:
                problems.append(Problem(
                    addon,
                    f"depends on {dep!r}, which is on no --addons-path entry, so "
                    f"neither its licence nor anything it depends on can be read. "
                    f"Add the source that provides it to --addons-path.",
                ))
                continue
            dep_license = license_of(dep)
            if dep_license is not None:
                reached_licenses[addon].add(dep_license)
            if dep_license is None:
                problems.append(Problem(
                    addon,
                    f"depends on {dep!r}, whose licence is unknown. Add it to "
                    f"KNOWN_LICENSES in scripts/check_licenses.py, or run this with "
                    f"--addons-path so the real manifest can be read.",
                ))
                continue
            problem = compatibility_problem(addon, own, dep, dep_license)
            if problem:
                problems.append(problem)
            # Local addons are readable in either mode, so walk through them
            # always: otherwise a companion addon's transitive reach into Odoo
            # core would be visible in CI but not in pre-commit, and the two
            # would disagree about which texts it has to ship. External manifests
            # are only walkable when resolved.
            if args.addons_path or dep in addons:
                queue.extend(depends_of(dep))
        odoo_closures[addon] = seen

    def declared_python(name: str) -> list[str]:
        manifest = addons.get(name)
        if manifest is None and name in index:
            try:
                manifest = read_manifest(index[name] / "__manifest__.py")
            except Exception:
                manifest = None
        external = (manifest or {}).get("external_dependencies") or {}
        return list(external.get("python") or [])

    # A wheel that arrives with a dependency binds exactly as one this manifest
    # names: installing an addon installs its whole closure, so those addons'
    # requirements sit under this addon's licence too. Attributed to the addon's own
    # manifest first and then to its closure, so a refusal names the file to edit.
    requirements: dict[str, dict[str, PyRequirement]] = {}
    # Collected against the manifest that wrote it and reported once, rather
    # than once per addon whose closure reaches it.
    unreadable: dict[tuple[str, str], str] = {}
    for addon in addons:
        sources: dict[str, PyRequirement] = {}
        for name in (addon, *sorted(odoo_closures.get(addon, ()))):
            for expression in declared_python(name):
                try:
                    requirement = parse_py_requirement(expression, name)
                except RequirementProblem as exc:
                    unreadable[(name, expression)] = str(exc)
                    continue
                sources.setdefault(requirement.name, requirement)
        requirements[addon] = sources
    for (name, expression), why in sorted(unreadable.items()):
        problems.append(Problem(
            name, f"declares the Python requirement {expression!r}, {why}"))

    python_scan = check_python_dependencies(
        addons, requirements, resolve=args.resolve_python
    )
    problems.extend(python_scan.problems)
    problems.extend(check_license_texts(addons, reached_licenses))

    if args.inventory:
        scanned = head_commit(args.commit)
        if scanned.dirty:
            problems.append(Problem(
                "scripts/check_licenses.py",
                f"the working tree has uncommitted changes, so this inventory "
                f"describes a tree no commit holds. Recorded as {scanned.commit!r} "
                f"rather than as a bare commit. Commit before attaching it to a "
                f"release.",
                fatal=False,
            ))
        write_inventory(args.inventory, addons, license_of,
                        commit=scanned.commit,
                        resolved_python=args.resolve_python,
                        odoo_closures=odoo_closures,
                        requirements=requirements,
                        python_closures=python_scan.closures,
                        pip_version=python_scan.pip_version,
                        environment=python_scan.environment)

    for addon in sorted(addons):
        print(f"  {addon}: {addons[addon].get('license')!r}")
    if args.addons_path:
        print("  (dependency licences resolved from --addons-path, transitively)")
    if args.resolve_python:
        print("  (Python dependency licences audited against published metadata, "
              "at whichever versions resolved just now from pip's configured "
              "index: a requirement that pins nothing names no release)")

    fatal = [p for p in problems if p.fatal]
    for problem in problems:
        print(f"{'ERROR' if problem.fatal else 'NOTE '} {problem.addon}: {problem.message}")
    if not problems:
        print("All addon licences are compatible with their dependencies.")
    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
