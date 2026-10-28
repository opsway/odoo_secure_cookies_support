#!/usr/bin/env python3
"""Tests for scripts/check_licenses.py: every case here is one the gate must reject.

The gate decides whether copyleft can reach the proprietary addon, and it is the
only check whose failure is a delivery problem rather than a test problem. What it
had before was mutations run by hand, and that missed an own-licence value which
cleared every branch instead of none of them -- so each arrangement below is one
the gate has to keep refusing without anyone remembering to try it.
"""
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout

GATE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_licenses.py"

# By path, because scripts/ is not a package and the gate is a CLI, not a library.
_spec = importlib.util.spec_from_file_location("check_licenses", GATE)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

# The gate's two maps hold the consuming repository's own dependencies, so a case
# that reads them asserts on what that repository happens to require rather than on
# the gate: adding a dependency would change the outcome of tests about something
# else. GateCase substitutes these for the duration, which is also what lets one
# copy of this file serve the template and every repository generated from it.
# Wheel keys are canonical distribution names (PEP 503), which is what the gate
# reads a requirement expression down to; an entry under any other spelling is
# one it cannot find.
MAPPED_ADDONS = {"web": "LGPL-3", "mapped_addon": "LGPL-3"}
MAPPED_WHEELS = {"cleared-wheel": "MIT", "decided-wheel": "BSD",
                 "copyleft-wheel": "GPL-3.0"}

# Given to every synthetic addon so the licence-text axis stays quiet and the case
# under test is the only thing that can fail it.
ALL_TEXTS = ("AGPL-3.txt", "GPL-2.txt", "GPL-3.txt", "LGPL-3.txt", "OPL-1.txt",
             "OEEL-1.txt")


def write_addon(
    root: pathlib.Path,
    name: str,
    licence: str | None,
    *,
    depends: tuple[str, ...] = (),
    python: tuple[str, ...] = (),
    texts: tuple[str, ...] = ALL_TEXTS,
    license_md: str | None = "# terms\n",
) -> pathlib.Path:
    directory = root / name
    (directory / "LICENSES").mkdir(parents=True)
    manifest = {"name": name, "license": licence, "depends": list(depends)}
    if python:
        manifest["external_dependencies"] = {"python": list(python)}
    (directory / "__manifest__.py").write_text(repr(manifest), encoding="utf-8")
    if license_md is not None:
        (directory / "LICENSE.md").write_text(license_md, encoding="utf-8")
    for text in texts:
        (directory / "LICENSES" / text).write_text("licence text\n", encoding="utf-8")
    return directory


class GateCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmp = pathlib.Path(tmp.name)
        self._trees = 0
        for name, fixture in (("KNOWN_LICENSES", MAPPED_ADDONS),
                              ("KNOWN_PYTHON_LICENSES", MAPPED_WHEELS)):
            patched = unittest.mock.patch.dict(
                getattr(gate, name), fixture, clear=True)
            patched.start()
            self.addCleanup(patched.stop)

    def tree(self) -> pathlib.Path:
        """A fresh, empty addons root."""
        self._trees += 1
        root = self._tmp / f"tree{self._trees}"
        root.mkdir()
        return root

    def run_gate(self, root: pathlib.Path, *argv: str) -> tuple[int, str]:
        """(exit code, printed output) for the gate run over `root`.

        ROOT is a module constant read at call time, so pointing it at a synthetic
        tree needs no seam in the gate itself.
        """
        out = io.StringIO()
        original_root, original_argv = gate.ROOT, sys.argv
        gate.ROOT, sys.argv = root, ["check_licenses.py", *argv]
        try:
            with redirect_stdout(out):
                code = gate.main()
        finally:
            gate.ROOT, sys.argv = original_root, original_argv
        return code, out.getvalue()

    def run_gate_aborting(self, root: pathlib.Path, *argv: str) -> str:
        """The SystemExit message for a scan that cannot honour its own arguments."""
        with self.assertRaises(SystemExit) as raised:
            self.run_gate(root, *argv)
        return str(raised.exception)

    def assertRefused(self, output: str, *fragments: str):
        errors = [line for line in output.splitlines() if line.startswith("ERROR")]
        self.assertTrue(errors, f"nothing was refused:\n{output}")
        for fragment in fragments:
            self.assertTrue(
                any(fragment in line for line in errors),
                f"no ERROR mentions {fragment!r}:\n{output}",
            )


class OwnLicence(GateCase):
    """Every branch asks whether the addon's licence is in a set it knows, so a
    licence in no set is a pass for any dependency rather than a refusal."""

    def test_odoo_vocabulary_is_classified_and_anything_else_is_refused(self):
        # An LGPL-3 dependency that every one of these may absorb, so the addon's
        # own licence is the only thing that can decide the outcome.
        cases = [
            # (licence, the fragment that must name why, or "" to pass)
            ("Other proprietary", ""),
            ("OPL-1", ""),
            ("OEEL-1", ""),
            ("LGPL-3", ""),
            ("AGPL-3", ""),
            ("GPL-2", ""),
            ("GPL-2 or any later version", ""),
            ("GPL-3", ""),
            ("GPL-3 or any later version", ""),
            # Odoo's catch-all. A valid manifest value spanning MIT to
            # GPL-incompatible, so nothing can say what it may absorb. The
            # fragment is asserted because the wider branch below would refuse
            # this too, and refusing it as a typo would send its author to fix a
            # spelling that is already correct.
            ("Other OSI approved licence", "Odoo's catch-all"),
            # Outside Odoo's vocabulary: a typo in a real value read as
            # unclassified, which cleared the copyleft checks rather than failing.
            ("Other Proprietary", "not one of Odoo's manifest licence values"),
            ("MIT", "not one of Odoo's manifest licence values"),
            (None, "declares no 'license'"),
        ]
        for licence, fragment in cases:
            with self.subTest(licence=licence):
                root = self.tree()
                write_addon(root, "suite", licence, depends=("web",))
                code, output = self.run_gate(root)
                self.assertEqual(code, 1 if fragment else 0, output)
                if fragment:
                    self.assertRefused(output, fragment)

    def test_an_unclassifiable_own_licence_still_records_what_it_reaches(self):
        """Refusing the licence must not stop the dependency walk.

        Skipping the addon would blank its closure and its licence-text
        requirements in the release record, for the one addon under suspicion.
        """
        root = self.tree()
        write_addon(root, "suite", "Other OSI approved licence", depends=("web",))
        inventory = root / "inventory.json"
        code, output = self.run_gate(root, f"--inventory={inventory}")

        self.assertEqual(code, 1, output)
        recorded = json.loads(inventory.read_text(encoding="utf-8"))["addons"]["suite"]
        self.assertEqual(recorded["odoo_closure"], {"web": "LGPL-3"})
        self.assertIn("LGPL-3.txt", recorded["license_texts"])


class DependencyLicence(GateCase):
    def test_copyleft_flows_one_way(self):
        cases = [
            # (addon's licence, dependency's licence, refused, message fragment)
            ("Other proprietary", "AGPL-3", True, "Strong copyleft cannot sit"),
            ("Other proprietary", "GPL-3", True, "Strong copyleft cannot sit"),
            ("Other proprietary", "LGPL-3", False, ""),
            ("Other proprietary", "OPL-1", False, ""),
            # The target licence is asserted, not just the refusal: LGPL-3 s2
            # converts the combination to GPL-3, so echoing the dependency's own
            # spelling back would send its author to a licence that cannot carry
            # the result -- or, for GPL-2, to one that cannot exist.
            ("LGPL-3", "AGPL-3", True, "must be distributed under AGPL-3"),
            ("LGPL-3", "GPL-3", True, "must be distributed under GPL-3"),
            ("LGPL-3", "GPL-3 or any later version", True, "must be distributed under GPL-3"),
            ("LGPL-3", "GPL-2 or any later version", True, "must be distributed under GPL-3"),
            ("LGPL-3", "GPL-2", True, "no licence the combined work could be conveyed under"),
            ("AGPL-3", "LGPL-3", False, ""),
            # Two strong-copyleft licences do not absorb each other on contact.
            # AGPL-3 s13 attaches to the combined work, and a GPL declaration
            # does not announce it -- the obligation this whole boundary is
            # about, arriving where nobody is looking for it.
            ("GPL-3", "AGPL-3", True, "AGPL-3 s13"),
            ("GPL-3 or any later version", "AGPL-3", True, "AGPL-3 s13"),
            ("GPL-2 or any later version", "AGPL-3", True, "AGPL-3 s13"),
            # The AGPL addon is already the stronger of the two.
            ("AGPL-3", "GPL-3", False, ""),
            ("AGPL-3", "AGPL-3", False, ""),
            # GPL-2-only against the GPL-3 lineage, both directions: there is no
            # version of either licence the combination can go out under.
            ("GPL-2", "GPL-3", True, "no 'or later' clause"),
            ("GPL-3", "GPL-2", True, "no 'or later' clause"),
            ("AGPL-3", "GPL-2", True, "no 'or later' clause"),
            ("GPL-2", "GPL-2", False, ""),
            # Deliberately allowed: the 'or later' clause is what makes this
            # legal, and the combination goes out under GPL-3.
            ("GPL-2 or any later version", "GPL-3", False, ""),
            ("GPL-2", "GPL-2 or any later version", False, ""),
        ]
        for own, dep_licence, refused, fragment in cases:
            with self.subTest(own=own, dependency=dep_licence):
                root = self.tree()
                write_addon(root, "companion", dep_licence)
                write_addon(root, "suite", own, depends=("companion",))
                code, output = self.run_gate(root)
                self.assertEqual(code, 1 if refused else 0, output)
                if refused:
                    self.assertRefused(output, fragment)

    def test_copyleft_over_a_proprietary_dependency_needs_a_named_pair(self):
        """This direction is decided by who owns the two works, not by their licences.

        Strong copyleft obliges the whole combined work and a proprietary licence
        forbids releasing its half under it, so the pair is lawful only where one
        party owns both -- an ownership fact no manifest records. A blanket note
        used to clear the direction, which read one repository's reasoning onto a
        third party's proprietary code as readily as onto its own. The allowlist
        therefore ships empty: refusal is what a generated repository gets, and an
        entry is a decision that stays visible as a NOTE.
        """
        root = self.tree()
        write_addon(root, "vendor_module", "Other proprietary")
        write_addon(root, "reporting", "AGPL-3", depends=("vendor_module",))

        code, output = self.run_gate(root)
        self.assertEqual(code, 1, output)
        self.assertRefused(output, "REVIEWED_PROPRIETARY_EDGES")

        with unittest.mock.patch.object(
            gate, "REVIEWED_PROPRIETARY_EDGES", {("reporting", "vendor_module")}
        ):
            code, output = self.run_gate(root)
        self.assertEqual(code, 0, output)
        self.assertIn("NOTE ", output)

    def test_an_unclassified_dependency_is_refused_rather_than_assumed(self):
        cases = [
            # (manifest key, message fragment)
            ({"depends": ("nobody_classified_this",)}, "Add it to KNOWN_LICENSES"),
            ({"python": ("nobody_classified_this",)}, "KNOWN_PYTHON_LICENSES"),
        ]
        for kwargs, fragment in cases:
            with self.subTest(**kwargs):
                root = self.tree()
                write_addon(root, "suite", "Other proprietary", **kwargs)
                code, output = self.run_gate(root)
                self.assertEqual(code, 1, output)
                self.assertRefused(output, fragment)

    def test_every_relicensing_the_gate_advises_clears_the_gate(self):
        """A refusal that names a licence to relicense to must name one that works.

        'GPL-2' over an AGPL-3 dependency advised 'GPL-2 or any later version',
        which only advanced the caller to the next rule -- the AGPL-3 s13 branch,
        which demands AGPL-3. Advice whose result is another refusal teaches
        people to stop reading them, and every rule added here can reintroduce
        it, so this walks the whole vocabulary rather than the pair that broke.
        """
        vocabulary = sorted(gate.CLASSIFIED)
        advised = 0
        for own in vocabulary:
            for other in vocabulary:
                clash = gate.copyleft_clash(own, other)
                if clash is None or clash.relicense_to is None:
                    continue
                advised += 1
                target = clash.relicense_to
                with self.subTest(own=own, dependency=other, advised=target):
                    self.assertIn(target, gate.CLASSIFIED)
                    # Else following it trips the licence-text axis instead.
                    self.assertIn(target, gate.LICENSE_TEXTS)
                    self.assertIsNone(gate.copyleft_clash(target, other))
        self.assertTrue(advised, "no refusal offered a relicensing at all")


class ResolvedMode(GateCase):
    """--addons-path, as CI runs it. Pre-commit reaches none of this."""

    def test_a_stale_map_entry_is_reported_rather_than_trusted(self):
        root, external = self.tree(), self.tree()
        write_addon(root, "suite", "Other proprietary")
        # The map says mapped_addon is LGPL-3. Upstream relicensing is what
        # this mode exists to notice, and a wrong entry clears a real conflict.
        write_addon(external, "mapped_addon", "AGPL-3")
        code, output = self.run_gate(root, f"--addons-path={external}")

        self.assertEqual(code, 1, output)
        self.assertRefused(output, "KNOWN_LICENSES says mapped_addon")

    def test_copyleft_two_hops_away_is_reached(self):
        root, external = self.tree(), self.tree()
        write_addon(root, "suite", "Other proprietary", depends=("bridge",))
        write_addon(external, "bridge", "LGPL-3", depends=("enforcer",))
        write_addon(external, "enforcer", "AGPL-3")
        code, output = self.run_gate(root, f"--addons-path={external}")

        self.assertEqual(code, 1, output)
        self.assertRefused(output, "'enforcer'")

    def test_an_addons_path_that_cannot_resolve_aborts_rather_than_degrades(self):
        """Skipping a bad entry buys a passing scan that checked nothing.

        The fallback is the offline map, with no transitive walk and no audit of
        KNOWN_LICENSES -- while main() goes on printing that dependencies were
        resolved transitively. A typo in ADDONS_PATH, or an image that moved its
        addons directory, must not read as success.
        """
        root, external = self.tree(), self.tree()
        write_addon(root, "suite", "Other proprietary")
        write_addon(external, "vendor", "LGPL-3")
        empty = self.tree()

        cases = [
            # (addons path, fragment of the abort)
            (f"{self._tmp / 'not-there'}", "are not directories"),
            (f"{external},{self._tmp / 'not-there'}", "are not directories"),
            (f"{empty}", "holds no addon"),
        ]
        for addons_path, fragment in cases:
            with self.subTest(addons_path=addons_path):
                message = self.run_gate_aborting(root, f"--addons-path={addons_path}")
                self.assertIn(fragment, message)

        # A trailing comma is formatting, not a missing directory.
        code, output = self.run_gate(root, f"--addons-path={external},")
        self.assertEqual(code, 0, output)

    def test_a_dependency_licence_the_rules_cannot_place_is_refused(self):
        """The dependency side has to fail closed exactly as the addon's own does.

        Every compatibility rule asks whether a licence is in a set it recognises,
        so a spelling in none of them clears any addon rather than refusing it --
        the same silent pass OwnLicence above covers for the addon's own value, and
        the same not-knowing that shipped the original defect.
        """
        cases = [
            # (the dependency's manifest licence, the fragment that must name why)
            ("Other OSI approved licence", "Odoo's catch-all"),
            # Proprietary spelled the way English does, not the way Odoo does.
            ("Proprietary", "not one this script can classify"),
            # Friendly-looking, and still a licence nobody here has classified.
            ("MIT", "not one this script can classify"),
            # The licence this whole gate exists for, in SPDX's spelling rather
            # than Odoo's -- so no rule matches it and every one of them passes.
            ("AGPL-3.0", "not one this script can classify"),
        ]
        for licence, fragment in cases:
            with self.subTest(licence=licence):
                root, external = self.tree(), self.tree()
                write_addon(root, "suite", "Other proprietary", depends=("vendor",))
                write_addon(external, "vendor", licence)
                code, output = self.run_gate(root, f"--addons-path={external}")

                self.assertEqual(code, 1, output)
                self.assertRefused(output, "'vendor'", fragment)

    def test_a_dependency_off_the_addons_path_is_refused_rather_than_mapped(self):
        """An incomplete ADDONS_PATH must not buy the tick a complete one gets.

        The case above catches an entry that is not a directory. This is the one it
        cannot see: every entry real, one source simply absent -- Odoo core checked
        out and server-auth not. The dependency then takes its licence from
        KNOWN_LICENSES and nothing below it is walked at all, while the run reports
        that it read real manifests transitively.
        """
        for dep in ("mapped_addon", "nobody_ships_this"):
            with self.subTest(dep=dep):
                root, external = self.tree(), self.tree()
                write_addon(root, "suite", "Other proprietary", depends=(dep,))
                write_addon(external, "web", "LGPL-3")
                code, output = self.run_gate(root, f"--addons-path={external}")

                self.assertEqual(code, 1, output)
                self.assertRefused(output, f"{dep!r}", "no --addons-path entry")

        # Offline the map is the authority rather than a fallback, so the same
        # dependency has to stay fine there: dropping the mode check would fail
        # every commit instead.
        root = self.tree()
        write_addon(root, "suite", "Other proprietary", depends=("mapped_addon",))
        code, output = self.run_gate(root)
        self.assertEqual(code, 0, output)


class LicenceTexts(GateCase):
    """Addons leave here one at a time, so a text at the repository root does not
    travel with the thing it licenses."""

    def test_each_addon_carries_the_texts_it_is_under_or_links(self):
        cases = [
            # (arrangement, addon kwargs, message fragment)
            (
                "no LICENSE.md at all",
                dict(licence="Other proprietary", license_md=None),
                "has no LICENSE.md",
            ),
            (
                "LGPL-3 without the GPL text s4(b) asks for alongside it",
                dict(licence="LGPL-3", texts=("LGPL-3.txt",)),
                "LGPL-3 s4(b)",
            ),
            (
                "links LGPL-3 through a dependency without carrying its text",
                dict(licence="AGPL-3", depends=("web",), texts=("AGPL-3.txt",)),
                "it links 'LGPL-3'",
            ),
            (
                "LICENSE.md linking to a file outside the addon",
                dict(
                    licence="Other proprietary",
                    license_md="see [the terms](../LICENSE.md)\n",
                ),
                "dead as soon as the addon is extracted",
            ),
        ]
        for arrangement, kwargs, fragment in cases:
            with self.subTest(arrangement=arrangement):
                root = self.tree()
                write_addon(root, "suite", **kwargs)
                code, output = self.run_gate(root)
                self.assertEqual(code, 1, output)
                self.assertRefused(output, fragment)

    def test_a_licence_the_gate_accepts_always_has_terms_to_ship(self):
        """A classified licence with no LICENSE_TEXTS entry required no text at all.

        Classifying a licence is what makes the gate accept it everywhere; the text
        check then skipped whatever it did not recognise, so the addon went out
        under terms it did not carry and nothing said so. GPL-2 and both "or any
        later version" spellings were in exactly that state.
        """
        self.assertEqual(gate.CLASSIFIED - set(gate.LICENSE_TEXTS), set())

        root = self.tree()
        write_addon(root, "suite", "GPL-2")
        with unittest.mock.patch.dict(gate.LICENSE_TEXTS):
            del gate.LICENSE_TEXTS["GPL-2"]
            code, output = self.run_gate(root)
        self.assertEqual(code, 1, output)
        self.assertRefused(output, "LICENSE_TEXTS")


class ScannedCommit(GateCase):
    """An inventory that names a commit its content does not hold looks
    answerable and is not, which is worse than naming no commit at all."""

    def test_an_explicit_commit_is_taken_on_trust(self):
        # The odoo container has no git, so the CI job passes the sha in and
        # nothing on hand could check it against a tree.
        self.assertEqual(gate.head_commit("deadbeef"), ("deadbeef", False))

    def test_no_git_records_no_commit(self):
        original = gate.ROOT
        gate.ROOT = self.tree()
        try:
            self.assertEqual(gate.head_commit(None), (None, False))
        finally:
            gate.ROOT = original

    @unittest.skipUnless(shutil.which("git"), "needs git to build a repository")
    def test_a_dirty_tree_is_recorded_as_dirty_and_reported(self):
        root = self.tree()
        write_addon(root, "suite", "Other proprietary")
        for args in (
            ("init", "-q"),
            ("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"),
            ("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "baseline"),
        ):
            subprocess.run(["git", "-C", str(root), *args], check=True,
                           capture_output=True)

        original = gate.ROOT
        gate.ROOT = root
        try:
            clean = gate.head_commit(None)
        finally:
            gate.ROOT = original
        self.assertFalse(clean.dirty)
        self.assertRegex(clean.commit, r"^[0-9a-f]{40}$")

        (root / "suite" / "LICENSE.md").write_text("edited\n", encoding="utf-8")
        inventory = root / "inventory.json"
        code, output = self.run_gate(root, f"--inventory={inventory}")

        self.assertEqual(code, 0, output)
        self.assertIn("NOTE ", output)
        self.assertIn("uncommitted changes", output)
        recorded = json.loads(inventory.read_text(encoding="utf-8"))["commit"]
        self.assertEqual(recorded, f"{clean.commit}-dirty")


class InventoryRecord(GateCase):
    """The artefact a release is answered from, so what it claims has to be true."""

    def test_the_python_closure_says_what_it_is_evidence_of(self):
        """A resolver's answer at scan time, not a deployment's bill of materials.

        The record showed a version per wheel and called itself what shipped. It
        is not: --ignore-installed asks what would resolve at scan time, while the
        deployment that later installs the addon holds whatever its image and its
        own pip left there. A version in a compliance artefact reads as a bill of
        materials unless the artefact says otherwise, so it says otherwise -- and
        it says where the artefact came from rather than naming an index pip was
        never given, since pip's own configuration decides that.
        """
        cases = [
            # (resolve, mode, the version recorded, what the basis has to say)
            (True, "resolved", "4.4.28", "not necessarily PyPI"),
            (False, "declared", None, "no version, artefact or hash is known"),
        ]
        for resolve, mode, version, basis in cases:
            with self.subTest(mode=mode):
                root = self.tree()
                write_addon(root, "suite", "Other proprietary", python=("cleared-wheel",))
                inventory = root / "inventory.json"
                argv = [f"--inventory={inventory}", "--commit=deadbeef"]
                original = gate.resolve_python_licenses
                if resolve:
                    argv.append("--resolve-python")
                    # Stubbed rather than run: pip resolving is the one part of
                    # this that needs a network, and the claim under test is about
                    # how the answer is recorded, not how it is got.
                    gate.resolve_python_licenses = lambda required: gate.Resolution(
                        {"cleared-wheel": gate.ResolvedDist(
                            version="4.4.28",
                            license="MIT",
                            url="https://mirror.internal/simple/cleared-wheel-4.4.28.whl",
                            digest="sha256=deadbeef",
                        )},
                        "25.2",
                        {"python_version": "3.12", "sys_platform": "linux"},
                    )
                try:
                    code, output = self.run_gate(root, *argv)
                finally:
                    gate.resolve_python_licenses = original

                self.assertEqual(code, 0, output)
                recorded = json.loads(inventory.read_text(encoding="utf-8"))
                resolution = recorded["python_resolution"]
                self.assertEqual(resolution["mode"], mode)
                self.assertEqual(bool(resolution["resolved_at"]), resolve)
                self.assertIn(basis, resolution["basis"])
                self.assertNotIn("against PyPI", resolution["basis"])
                wheel = recorded["addons"]["suite"]["python_closure"]["cleared-wheel"]
                self.assertEqual(wheel["version"], version)
                # Which pip answered and which markers it evaluated: without them
                # the closure cannot be read, because a pip before 25.0 drops the
                # PEP 639 licence field and a marker decides what was in scope.
                self.assertEqual(
                    resolution["pip_version"], "25.2" if resolve else None
                )
                self.assertEqual(
                    (resolution["environment"] or {}).get("python_version"),
                    "3.12" if resolve else None,
                )
                self.assertEqual(
                    wheel["url"],
                    "https://mirror.internal/simple/cleared-wheel-4.4.28.whl" if resolve
                    else None,
                )
                self.assertEqual(
                    wheel["hash"], "sha256=deadbeef" if resolve else None
                )

    def test_a_credential_in_an_index_url_does_not_reach_the_record(self):
        """The inventory is attached to releases and read widely.

        A private index is reached with a token, in userinfo or in the query
        string, and pip reports the URL it actually fetched. Recording that
        verbatim hands the credential to everyone the release record reaches.
        """
        cases = [
            ("https://user:tok@mirror.internal/simple/x-1.0.whl",
             "https://mirror.internal/simple/x-1.0.whl"),
            ("https://mirror.internal/simple/x-1.0.whl?token=abc123",
             "https://mirror.internal/simple/x-1.0.whl"),
            ("https://user:tok@mirror.internal:8443/s/x-1.0.whl#sha256=y",
             "https://mirror.internal:8443/s/x-1.0.whl"),
            ("https://files.pythonhosted.org/packages/x-1.0.whl",
             "https://files.pythonhosted.org/packages/x-1.0.whl"),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                recorded = gate.artefact_url({"url": url})
                self.assertEqual(recorded, expected)
                for secret in ("tok", "abc123"):
                    self.assertNotIn(secret, recorded)
        self.assertIsNone(gate.artefact_url({}))


class PythonWheels(GateCase):
    def test_wheel_copyleft_flows_the_same_way(self):
        """The same rules as the addon graph, reached through the same function.

        A wheel binds its addon exactly as an Odoo dependency does, but the wheel
        path used to hold its own copy of the rules, and that copy collapsed the
        GPL family into "strong" -- so the version, which is the whole question
        between two copyleft licences, stopped being asked. The last three cases
        are what that cleared.
        """
        cases = [
            # (addon's licence, wheel's licence, refused, message fragment)
            ("Other proprietary", "GPL-3.0", True, "Strong copyleft cannot sit"),
            ("Other proprietary", "AGPL-3.0", True, "Strong copyleft cannot sit"),
            ("LGPL-3", "GPL-3.0", True, "must be distributed under GPL-3"),
            ("LGPL-3", "GPL-2.0", True, "no licence the combined work could be conveyed under"),
            ("Other proprietary", "MIT", False, ""),
            ("Other proprietary", "LGPL-3.0", False, ""),
            ("AGPL-3", "GPL-3.0", False, ""),
            ("AGPL-3", "GPL-2.0", True, "no 'or later' clause"),
            ("GPL-2", "GPL-3.0", True, "no 'or later' clause"),
            ("GPL-3", "AGPL-3.0", True, "AGPL-3 s13"),
            # The 'or later' clause is what makes this one lawful, on either side.
            ("GPL-2 or any later version", "GPL-3.0", False, ""),
            ("GPL-2", "GPL-2.0+", False, ""),
            # A spelling in neither PY_PERMISSIVE nor PY_AS_ODOO is a decision
            # nobody made.
            ("Other proprietary", "WTFPL", True, "does not classify"),
        ]
        for own, licence, refused, fragment in cases:
            with self.subTest(own=own, licence=licence):
                problem = gate.python_compatibility_problem("suite", own, "wheel", licence)
                self.assertEqual(problem is not None, refused)
                if refused:
                    self.assertIn(fragment, problem.message)

    def test_the_affero_spelling_pypi_emits_is_not_missed(self):
        """PyPI's trove name for the AGPL contains neither 'agpl' nor 'gpl'.

        A substring test clears 'GNU Affero General Public License v3' silently,
        and it is the one family that must never be cleared silently.
        """
        cases = [
            ("GNU Affero General Public License v3", "agpl"),
            ("GNU Affero General Public License v3 or later (AGPLv3+)", "agpl"),
            ("AGPL-3.0", "agpl"),
            ("GNU Lesser General Public License v3 (LGPLv3)", "lgpl"),
            ("GNU General Public License v3 (GPLv3)", "gpl"),
            # PyPI's classifiers append the abbreviation for the GPL and the
            # LGPL, so only Affero needed a case of its own -- but a free-form
            # `license` field is under no such discipline, and neither of these
            # carries 'gpl' as a substring either.
            ("GNU General Public License v3", "gpl"),
            ("GNU General Public License (GPL)", "gpl"),
            ("GNU Lesser General Public License", "lgpl"),
            ("GNU Lesser General Public License v3 (LGPLv3)", "lgpl"),
            ("MIT License", "mit"),
            ("OSI Approved :: BSD License", "bsd"),
        ]
        for spelling, family in cases:
            with self.subTest(spelling=spelling):
                self.assertEqual(gate.normalise_py_license(spelling), family)

    def test_a_wheel_no_manifest_declares_binds_the_same_way(self):
        cases = [
            # (addon's licence, what pip published, refused, message fragment)
            ("Other proprietary", "GNU Affero General Public License v3", True,
             "Strong copyleft cannot sit under"),
            ("Other proprietary", "MIT License", False, ""),
            ("Other proprietary", None, True, "pip reports no "),
            ("Other proprietary", "WTFPL", True, "a spelling this script does not classify"),
            # A published spelling is read as a family, and a family names no
            # version -- so under a copyleft addon, where the version is what
            # decides, it is refused until somebody reads the wheel. 'GPL' here
            # could as easily be GPL-2-only, which AGPL-3 cannot combine with.
            ("AGPL-3", "GNU General Public License (GPL)", True, "naming no version"),
            ("AGPL-3", "MIT License", False, ""),
        ]
        for own, reported, refused, fragment in cases:
            with self.subTest(own=own, reported=reported):
                problem = gate.transitive_python_problem(
                    "suite", own, "undeclared_wheel", reported
                )
                self.assertEqual(problem is not None, refused, reported)
                if refused:
                    self.assertIn(fragment, problem.message)

    def test_a_wheel_that_disagrees_with_itself_is_not_read_at_its_friendliest(self):
        """Taking the strongest signal settles GPL and AGPL, and nothing else.

        A permissive field beside a proprietary or unclassified classifier used to
        resolve to whichever signal pip happened to list first -- always the
        permissive one -- and clear the wheel on a NOTE.
        """
        cases = [
            # (what the wheel published, distribution, refused, fatal, fragment)
            (
                "a permissive field beside a proprietary classifier",
                {"license": "BSD", "classifier": ["License :: Other/Proprietary License"]},
                "unmapped_wheel", True, "nothing decides between them",
            ),
            (
                "the same, where the map records the reading",
                {"license": "BSD", "classifier": ["License :: Other/Proprietary License"]},
                "decided-wheel", False, "records 'BSD' as the reading",
            ),
            (
                "a permissive field beside a GPL classifier: the strongest decides",
                {"license": "MIT",
                 "classifier": ["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"]},
                "unmapped_wheel", None, "",
            ),
            (
                "signals that agree",
                {"license": "Apache-2.0",
                 "classifier": ["License :: OSI Approved :: Apache Software License"]},
                "unmapped_wheel", None, "",
            ),
        ]
        for arrangement, meta, dist, fatal, fragment in cases:
            with self.subTest(arrangement=arrangement):
                problem = gate.conflict_problem(
                    dist, gate.dist_from_entry({"metadata": meta})
                )
                if fatal is None:
                    self.assertIsNone(problem)
                    continue
                self.assertIsNotNone(problem)
                self.assertEqual(problem.fatal, fatal)
                self.assertIn(fragment, problem.message)

    def test_the_strongest_signal_decides_not_the_first_one_listed(self):
        meta = {
            "version": "1.0",
            "license": "MIT",
            "classifier": ["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"],
        }
        found = gate.dist_from_entry({"metadata": meta})
        self.assertEqual(gate.normalise_py_license(found.license), "gpl")
        self.assertIsNotNone(
            gate.transitive_python_problem(
                "suite", "Other proprietary", "unmapped_wheel", found.license
            )
        )

    def test_a_licence_text_pasted_into_the_field_is_not_a_signal(self):
        """Some projects paste their whole licence into `license`."""
        for value in ["x" * 200, "Copyright (c) me\n\nPermission is hereby granted"]:
            with self.subTest(value=value[:20]):
                found = gate.dist_from_entry({"metadata": {"license": value}})
                self.assertIsNone(found.license)
                self.assertIsNone(found.conflict)

    def test_a_conflicting_wheel_reaches_the_report(self):
        """conflict_problem being right is no use if nothing calls it.

        Stubbed at the resolver, which is the pip boundary, so the wiring, the
        once-per-wheel reporting and the declared/transitive split all stay real.
        """
        addons = {
            "suite": {
                "name": "suite",
                "license": "Other proprietary",
                "external_dependencies": {"python": ["cleared-wheel"]},
            }
        }
        published = {
            "license": "BSD",
            "classifier": ["License :: Other/Proprietary License"],
        }
        closure = {
            "cleared-wheel": gate.ResolvedDist("4.4.28", "MIT"),
            # Undeclared, unmapped, and disagreeing with itself.
            "unmapped_wheel": gate.dist_from_entry({"metadata": published}),
            # Declared nowhere either, but the map records the reading.
            "decided-wheel": gate.dist_from_entry({"metadata": published}),
        }
        original = gate.resolve_python_licenses
        gate.resolve_python_licenses = lambda requirements: gate.Resolution(
            closure, "25.2", {}
        )
        try:
            scan = gate.check_python_dependencies(
                addons,
                {"suite": {"cleared-wheel": gate.PyRequirement("cleared-wheel", "cleared-wheel", "suite")}},
                resolve=True,
            )
        finally:
            gate.resolve_python_licenses = original

        messages = [p.message for p in scan.problems]
        fatal = [p.message for p in scan.problems if p.fatal]
        self.assertTrue(
            any("unmapped_wheel publishes licence signals" in m for m in fatal),
            messages,
        )
        self.assertTrue(
            any("decided-wheel publishes licence signals" in m for m in messages)
            and not any("decided-wheel" in m for m in fatal),
            messages,
        )

    def test_a_wheel_arrives_with_the_addon_that_needs_it(self):
        """Installing an addon installs its dependencies' wheels under its licence.

        Judging and recording only what an addon's own manifest names lets a wheel
        reach a proprietary install closure through a dependency that is itself
        allowed -- and leaves the release record naming none of it, which is the
        one artefact meant to answer what shipped.
        """
        root, external = self.tree(), self.tree()
        write_addon(root, "suite", "Other proprietary", depends=("vendor",),
                    python=("decided-wheel",))
        # Declares no wheels of its own, and installs both by depending on suite.
        write_addon(root, "extra", "AGPL-3", depends=("suite",))
        write_addon(external, "vendor", "LGPL-3", python=("nobody_classified_this",))
        inventory = self._tmp / "inventory.json"
        code, output = self.run_gate(
            root, f"--addons-path={external}", f"--inventory={inventory}"
        )

        self.assertEqual(code, 1, output)
        # Two hops from extra, and blamed on the manifest that asks for it rather
        # than on the addon that carries it.
        # Named by the canonical distribution, which is the key the map wants,
        # and by the spelling the manifest used, which is what the reader greps.
        self.assertRefused(
            output, "'nobody-classified-this'", "declared as 'nobody_classified_this'",
            "declared by 'vendor'",
        )
        record = json.loads(inventory.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(record["addons"]["extra"]["python_closure"]),
            ["decided-wheel", "nobody-classified-this"],
        )

    @unittest.skipUnless(
        gate.Requirement is not None,
        "needs packaging; without it the gate refuses these entries, which is\n         what Odoo does here too -- see the test below",
    )
    def test_a_requirement_specifier_is_read_as_the_distribution_it_names(self):
        """Odoo 18 parses every entry with packaging.Requirement, so a specifier,
        an extra and an environment marker are all valid manifest values.

        Read as a name instead, 'decided-wheel==8.2' is a distribution nobody
        classified: a refusal whose only remedy is to record a licence for a
        spelling, on a manifest Odoo installs happily. False failures in a
        compliance gate are how people learn to bypass it. The licence still has
        to be judged on the distribution, so the parse must not become a way
        past the rules -- the copyleft cases pin that.
        """
        cases = [
            # (the manifest entry, refused, the fragment that must name why)
            ("decided-wheel", False, ""),
            ("decided-wheel==8.2", False, ""),
            ("decided-wheel>=7,<9", False, ""),
            ("decided-wheel[pil]", False, ""),
            ('decided-wheel; python_version >= "3.10"', False, ""),
            # Canonicalised: the map is keyed 'copyleft-wheel', and an entry
            # found only under the spelling one manifest used is not found.
            ("copyleft_wheel", True, "Strong copyleft cannot sit"),
            # A pin is not a bypass: the licence is the distribution's either way.
            ("copyleft-wheel==1.0", True, "Strong copyleft cannot sit"),
            ('copyleft-wheel[extra]; sys_platform == "win32"', True,
             "Strong copyleft cannot sit"),
            # packaging raises on this, so Odoo refuses to install the addon.
            ("decided-wheel >= ", True, "not a valid PEP 508 requirement"),
        ]
        for entry, refused, fragment in cases:
            with self.subTest(entry=entry):
                root = self.tree()
                write_addon(root, "suite", "Other proprietary", python=(entry,))
                code, output = self.run_gate(root)
                self.assertEqual(code, 1 if refused else 0, output)
                if refused:
                    self.assertRefused(output, fragment)

    def test_without_packaging_a_bare_name_still_works_and_the_rest_is_refused(self):
        """Odoo 18 dropped packaging from requirements.txt, and its image ships
        without it: odoo/modules/module.py parses a bare `[\\w-]+` name with a stub
        of its own and raises for anything else.

        So the gate has two states to get right, and both are Odoo's. Demanding
        packaging made it refuse to run at all where Odoo runs fine -- CI caught
        that in the odoo:18.0 container. Extracting a name with a laxer regex
        instead would be worse than either: it would classify 'decided-wheel==1.0' under a
        licence while the addon declaring it could not be installed there at all,
        which is a second, laxer copy of a rule this file exists to keep single.
        """
        cases = [
            # (the manifest entry, refused, the fragment that must name why)
            ("decided-wheel", False, ""),
            # A hyphen is a bare name too -- Odoo widened its own stub to allow one.
            ("nobody-classified-this", True, "licence is unknown"),
            ("decided-wheel==1.0", True, "needs 'packaging' to read"),
            ("decided-wheel[extra]", True, "needs 'packaging' to read"),
            ('decided-wheel; sys_platform == "linux"', True, "needs 'packaging' to read"),
        ]
        with unittest.mock.patch.object(gate, "Requirement", None):
            for entry, refused, fragment in cases:
                with self.subTest(entry=entry):
                    root = self.tree()
                    write_addon(root, "suite", "Other proprietary", python=(entry,))
                    code, output = self.run_gate(root)
                    self.assertEqual(code, 1 if refused else 0, output)
                    if refused:
                        self.assertRefused(output, fragment)

    @unittest.skipUnless(
        gate.Requirement is not None,
        "needs packaging; without it the gate refuses these entries, which is\n         what Odoo does here too -- see the test below",
    )
    def test_a_marker_that_excludes_the_scan_host_still_classifies_the_wheel(self):
        """What a wheel is licensed under does not depend on who installs it.

        pip evaluates a marker against the environment the scan ran in, so a
        requirement gated to another platform resolves to nothing here. Letting
        that skip classification would clear a copyleft wheel on Linux CI that
        still ships under this addon's licence on the platform the marker names.
        """
        root = self.tree()
        write_addon(root, "suite", "Other proprietary",
                    python=('copyleft-wheel; sys_platform == "nosuchplatform"',))
        code, output = self.run_gate(root)
        self.assertEqual(code, 1, output)
        self.assertRefused(output, "Strong copyleft cannot sit")

    def test_the_map_outranks_what_a_wheel_published(self):
        """A wheel can publish a stray classifier beside the grant it means.

        The map records which reading was decided, so the resolved mode must not
        re-litigate it on every run against whatever the wheel published.
        """
        self.assertIsNone(
            gate.transitive_python_problem(
                "suite", "Other proprietary", "decided-wheel", "GPL-3.0")
        )


if __name__ == "__main__":
    unittest.main()
