#!/usr/bin/env python3
"""test_q16_receipts.py — task item 2 (original), plus J1 (Marcus Reed's
Verified-per-version review, VER-001): a GENERATOR's per-version verified
receipt has no rhel_versions[v].command to diff against, so Q16's drift
check must bind it to the hand-authored validity oracle in
tests/fixtures/golden-commands.json instead — a template edit that changes
what the generator emits must invalidate the receipts that describe the old
behaviour, exactly the way a fixed-command edit already did.

qa.py's gate_q16() is exercised directly against a hand-built, ASSEMBLED-shape
ctx["data"] (same shape build.py leaves in the shipped data island — same_as
already resolved to a concrete command) rather than through a full build, so
these cases run in milliseconds. gate_q16() reads a receipt's capture file
and (for a generator) tests/fixtures/golden-commands.json off disk by
REPO-relative path exactly the way a real build does, so each case points
qa.REPO at a scratch directory holding just the fixture files it needs
(unittest.mock.patch.object, restored after every case).

Run with either:
    python3 -m pytest tests/
    python3 tests/test_q16_receipts.py
"""

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

CAPTURE_TEMPLATE = {
    "entry_id": "fixture-q16",
    "rhel_version": "8",
    "host": "fixture-host",
    "redhat_release": "fixture release",
    "kernel": "fixture kernel",
    "pkg_versions": {},
    "command_as_run": "systemctl is-active fixtured",
    "exit_code": 0,
    "stdout": "active",
    "stderr": "",
    "captured_on": "2026-09-17",
    "captured_by": "Caleb Stone",
    "blast_confirmed": "green",
    "undo_executed": {"run": False, "reason": "read-only"},
    "verify_result": "PASS",
}

# The real roster (content-src/roster.json) shape, reused as a fixture so
# these tests exercise the same names/roles production data uses.
ROSTER_FIXTURE = {
    "people": [
        {"name": "Caleb Stone", "roles": ["SME"]},
        {"name": "Renata Osei", "roles": ["SME"]},
        {"name": "Riley Park", "roles": ["QA"]},
    ]
}

GOLDEN_FIXTURE = {
    "generators": {
        "fixture-gen-q16": {
            "commands": {
                "7": "toolgen '10G'",
                "8": "toolgen '10G'",
                "9": "toolgen '10G'",
                "10": "toolgen '10G'",
            }
        }
    }
}


def make_ctx_data(receipt_by, capture_overrides=None):
    cap = copy.deepcopy(CAPTURE_TEMPLATE)
    cap.update(capture_overrides or {})
    cap["command_hash_at_capture"] = hashlib.sha256(cap["command_as_run"].encode("utf-8")).hexdigest()
    entry = {
        "id": "fixture-q16",
        "tool": "systemctl",
        "stig": [],
        "rhel_versions": {
            "7": {"unavailable": {"reason": "n/a", "alternative": None}},
            "8": {"command": "systemctl is-active fixtured", "notes": "n"},
            "9": {"unavailable": {"reason": "n/a", "alternative": None}},
            "10": {"unavailable": {"reason": "n/a", "alternative": None}},
        },
        "verified": {
            "7": False,
            "8": {"by": receipt_by, "on": "2026-09-18", "host": "fixture-host",
                 "capture": "tests/captures/8/fixture-q16.json"},
            "9": False,
            "10": False,
        },
    }
    data = {"commands": {"entries": [entry]}, "expected_output": {"captures": {}}}
    return data, cap


def make_gen_ctx_data(receipt_by="Riley Park", capture_overrides=None, receipt_overrides=None):
    """Same shape as make_ctx_data(), but for a GENERATOR entry (carries
    `template`), which J1 (VER-001) binds to the golden table instead of
    rhel_versions.command."""
    cap = copy.deepcopy(CAPTURE_TEMPLATE)
    cap["entry_id"] = "fixture-gen-q16"
    cap["command_as_run"] = "toolgen '10G'"
    cap.update(capture_overrides or {})
    cap["command_hash_at_capture"] = hashlib.sha256(cap["command_as_run"].encode("utf-8")).hexdigest()
    receipt = {"by": receipt_by, "on": "2026-09-18", "host": "fixture-host",
              "capture": "tests/captures/8/fixture-gen-q16.json"}
    receipt.update(receipt_overrides or {})
    entry = {
        "id": "fixture-gen-q16",
        "tool": "toolgen",
        "stig": [],
        "template": [{"lit": "toolgen"}, {"field": "size"}],
        "fields": [{"name": "size", "type": "comment", "required": True}],
        "versions": ["7", "8", "9", "10"],
        "verified": {
            "7": False,
            "8": receipt,
            "9": False,
            "10": False,
        },
    }
    data = {"commands": {"entries": [entry]}, "expected_output": {"captures": {}}}
    return data, cap


class Q16TestCase(unittest.TestCase):
    """Shared scratch-REPO machinery: a tempdir carrying the one capture file
    a case needs, plus (when asked) the golden-commands table, so gate_q16()'s
    file reads (qa.REPO-relative, exactly like a real build) resolve against
    a fixture, never the real repo."""

    def run_q16(self, data, cap, entry_id="fixture-q16", version="8", golden=None,
               roster=ROSTER_FIXTURE):
        tmp = tempfile.mkdtemp(prefix="mcr-q16-")
        try:
            capdir = os.path.join(tmp, "tests", "captures", version)
            os.makedirs(capdir)
            with open(os.path.join(capdir, "%s.json" % entry_id), "w", encoding="utf-8") as f:
                json.dump(cap, f)
            if golden is not None:
                fixdir = os.path.join(tmp, "tests", "fixtures")
                os.makedirs(fixdir, exist_ok=True)
                with open(os.path.join(fixdir, "golden-commands.json"), "w", encoding="utf-8") as f:
                    json.dump(golden, f)
            if roster is not None:
                rosterdir = os.path.join(tmp, "content-src")
                os.makedirs(rosterdir, exist_ok=True)
                with open(os.path.join(rosterdir, "roster.json"), "w", encoding="utf-8") as f:
                    json.dump(roster, f)
            with mock.patch.object(qa, "REPO", tmp):
                return qa.gate_q16({"data": data})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Q16ReceiptBacking(Q16TestCase):
    """Fail-first fixtures (task item 2): a receipt with no matching capture,
    or with a capture some OTHER content edited since, or captured by the
    same person the receipt names as the QA reviewer, must all fail."""

    def test_receipt_by_same_as_captured_by_fails(self):
        """Fail-first #1: SME captures, QA verifies — the same name cannot
        do both for one receipt."""
        data, cap = make_ctx_data(receipt_by="Caleb Stone")  # same as captured_by
        f, _d = self.run_q16(data, cap)
        self.assertTrue(f, "a receipt whose 'by' equals the capture's 'captured_by' must fail")
        self.assertTrue(any("normalise to the same person" in x for x in f),
                        "wrong reason:\n  " + "\n  ".join(f))

    def test_receipt_command_drift_fails(self):
        """Fail-first #2: the capture's command_as_run no longer matches the
        command this build actually assembles today."""
        data, cap = make_ctx_data(receipt_by="Riley Park",
                                  capture_overrides={"command_as_run": "systemctl is-active fixtured-STALE"})
        f, _d = self.run_q16(data, cap)
        self.assertTrue(f, "a receipt backed by a capture whose command has drifted must fail")
        self.assertTrue(any("no longer matches the RHEL" in x for x in f),
                        "wrong reason:\n  " + "\n  ".join(f))

    def test_valid_receipt_passes(self):
        """Control: a real capture, real different-person receipt, matching
        command — must NOT fail. A gate that fails everything proves nothing."""
        data, cap = make_ctx_data(receipt_by="Riley Park")
        f, _d = self.run_q16(data, cap)
        self.assertEqual([], f, "\n  ".join(f))

    def test_receipt_missing_capture_file_fails(self):
        data, cap = make_ctx_data(receipt_by="Riley Park")
        data["commands"]["entries"][0]["verified"]["8"]["capture"] = "tests/captures/8/does-not-exist.json"
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("does not exist" in x for x in f), "\n  ".join(f))


class Q16GoldenTableBinding(Q16TestCase):
    """J1 (VER-001): a GENERATOR receipt (entry carries `template`) has no
    rhel_versions[v].command to diff against, so without a golden-table bind
    a template edit that changes the emitted command never invalidates the
    receipts describing the old behaviour. Reproduces Marcus's own repro
    (gen-journalctl-unit-logs template += {lit:"--extra"}) in miniature: a
    generator's captured command_as_run must equal the golden row for the
    same (entry, version), not merely "not be empty"."""

    def test_generator_receipt_with_no_golden_row_fails(self):
        """Fail-first #1 (the state BEFORE this fix, and BEFORE the golden
        table even carries the row at all): a generator receipt with no
        golden-commands.json in the tree cannot be bound to anything, so it
        must fail rather than pass silently the way it did before J1."""
        data, cap = make_gen_ctx_data()
        f, _d = self.run_q16(data, cap, entry_id="fixture-gen-q16", golden=None)
        self.assertTrue(any("golden-commands.json is missing" in x for x in f), "\n  ".join(f))

    def test_generator_receipt_with_no_matching_golden_row_fails(self):
        data, cap = make_gen_ctx_data()
        empty_golden = {"generators": {}}
        f, _d = self.run_q16(data, cap, entry_id="fixture-gen-q16", golden=empty_golden)
        self.assertTrue(any("no golden-table row for generator" in x for x in f), "\n  ".join(f))

    def test_generator_template_drift_fails(self):
        """This IS Marcus's repro: the golden table still states the OLD
        command (as if the template had not changed since it was written),
        but the capture's command_as_run reflects what the CHANGED template
        now emits — exactly the shape of gen-journalctl-unit-logs's template
        gaining {lit:"--extra"} while the golden row and the receipt still
        describe the pre-edit command. At HEAD (no golden bind) this passed
        silently; after J1 it must name the entry and version."""
        data, cap = make_gen_ctx_data(capture_overrides={"command_as_run": "toolgen '10G' --extra"})
        f, _d = self.run_q16(data, cap, entry_id="fixture-gen-q16", golden=GOLDEN_FIXTURE)
        self.assertTrue(f, "a generator receipt whose capture no longer matches the golden row must fail")
        self.assertTrue(any("golden-table command generator" in x and "fixture-gen-q16" in x for x in f),
                        "wrong reason:\n  " + "\n  ".join(f))

    def test_generator_receipt_matching_golden_row_passes(self):
        """Control: a generator receipt whose capture matches the golden
        row exactly (the real shape of all 6 shipped generator receipts,
        e.g. gen-journalctl-unit-logs) must NOT fail."""
        data, cap = make_gen_ctx_data()
        f, _d = self.run_q16(data, cap, entry_id="fixture-gen-q16", golden=GOLDEN_FIXTURE)
        self.assertEqual([], f, "\n  ".join(f))


class Q16TwoPersonRoster(Q16TestCase):
    """J2 (VER-002): normalise both names, then require BOTH to resolve
    against the closed roster (content-src/roster.json) with the right role
    — 'by' as QA, 'captured_by' as SME. Marcus's nine variants, all of which
    used to pass Q16 against plain string equality."""

    ACCIDENTAL_VARIANTS = [
        ("exact match", "Caleb Stone"),
        ("lowercase", "caleb stone"),
        ("uppercase", "CALEB STONE"),
        ("leading space", " Caleb Stone"),
        ("trailing space", "Caleb Stone "),
        ("double space", "Caleb  Stone"),
        ("non-breaking space", "Caleb Stone"),
        ("parenthetical suffix", "Caleb Stone (SME)"),
    ]

    def test_all_eight_accidental_variants_fail(self):
        for label, by in self.ACCIDENTAL_VARIANTS:
            with self.subTest(label=label, by=by):
                data, cap = make_ctx_data(receipt_by=by)  # capture's captured_by is "Caleb Stone"
                f, _d = self.run_q16(data, cap)
                self.assertTrue(f, "variant %r (%s) must fail — it normalises to the capture's "
                                "captured_by, and/or is not QA-roled" % (by, label))

    def test_deliberate_alias_not_closed_by_equality_but_by_roster(self):
        """Fail-first #9: 'C. Stone' does not normalise to 'Caleb Stone' by
        any string rule — it must still fail, but for roster non-membership,
        not for equality. This is the residual Marcus named explicitly."""
        data, cap = make_ctx_data(receipt_by="C. Stone")
        f, _d = self.run_q16(data, cap)
        self.assertTrue(f, "'C. Stone' must fail even though it is not string-equal to 'Caleb Stone'")
        self.assertTrue(any("is not a QA-roled member of the roster" in x for x in f),
                        "wrong reason — must be a roster-membership failure, not an equality "
                        "failure:\n  " + "\n  ".join(f))

    def test_off_roster_name_fails_even_if_distinct_from_captured_by(self):
        """A name that is nobody's alias and simply is not on the roster
        (distinct from captured_by, so the equality check alone would have
        waved it through) must still fail."""
        data, cap = make_ctx_data(receipt_by="Nobody Onrecord")
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("is not a QA-roled member of the roster" in x for x in f), "\n  ".join(f))

    def test_captured_by_off_roster_fails(self):
        data, cap = make_ctx_data(receipt_by="Riley Park",
                                  capture_overrides={"captured_by": "Nobody Onrecord"})
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("is not an SME-roled member of the roster" in x for x in f), "\n  ".join(f))

    def test_sme_named_as_by_fails_role_check(self):
        """A real roster member in the wrong ROLE (Caleb is SME-only) must
        fail even though he IS on the roster — role, not mere membership."""
        data, cap = make_ctx_data(receipt_by="Caleb Stone",
                                  capture_overrides={"captured_by": "Renata Osei"})
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("is not a QA-roled member of the roster" in x for x in f), "\n  ".join(f))

    def test_missing_roster_file_fails_rather_than_silently_passing(self):
        data, cap = make_ctx_data(receipt_by="Riley Park")
        f, _d = self.run_q16(data, cap, roster=None)
        self.assertTrue(any("roster.json is missing" in x for x in f), "\n  ".join(f))

    def test_valid_receipt_still_passes_with_roster_enforced(self):
        """Control, repeated under the roster: real QA 'by', real SME
        'captured_by', both on the roster in the right role — must pass."""
        data, cap = make_ctx_data(receipt_by="Riley Park")
        f, _d = self.run_q16(data, cap)
        self.assertEqual([], f, "\n  ".join(f))

    def test_residual_stated_in_diagnostics(self):
        """The gate's own PASS output must say, in words, that the
        deliberate-alias case is closed by the roster and not by string
        comparison — the same discipline Q17/Q20 already hold themselves to."""
        data, cap = make_ctx_data(receipt_by="Riley Park")
        f, d = self.run_q16(data, cap)
        self.assertEqual([], f)
        self.assertTrue(any("C. Stone" in x and "NOT closable by any string comparison" in x for x in d),
                        "residual not stated in diagnostics:\n  " + "\n  ".join(d))


class Q16ClosedGrammars(Q16TestCase):
    """J3 (VER-003): `host` and `capture` are closed grammars, not free
    text. `by`'s grammar is the roster itself (J2) — covered above."""

    def test_hostile_host_fails(self):
        data, cap = make_ctx_data(receipt_by="Riley Park")
        data["commands"]["entries"][0]["verified"]["8"]["host"] = '<img src=x onerror=alert(1)>'
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("closed hostname grammar" in x for x in f), "\n  ".join(f))

    def test_hostile_capture_path_fails(self):
        data, cap = make_ctx_data(receipt_by="Riley Park")
        data["commands"]["entries"][0]["verified"]["8"]["capture"] = \
            'tests/captures/8/<img src=x onerror=alert(1)>.json'
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("does not match the closed grammar" in x for x in f), "\n  ".join(f))

    def test_capture_path_traversal_fails(self):
        data, cap = make_ctx_data(receipt_by="Riley Park")
        data["commands"]["entries"][0]["verified"]["8"]["capture"] = \
            'tests/captures/8/../../../etc/passwd.json'
        f, _d = self.run_q16(data, cap)
        self.assertTrue(any("does not match the closed grammar" in x for x in f), "\n  ".join(f))

    def test_receipt_host_disagreeing_with_capture_host_fails(self):
        """The receipt's own 'host' is a claim about where verification
        happened — it must equal the capture record's own 'host', not just
        be well-formed."""
        data, cap = make_ctx_data(receipt_by="Riley Park")
        data["commands"]["entries"][0]["verified"]["8"]["host"] = "other-host"
        f, _d = self.run_q16(data, cap)  # cap["host"] is still "fixture-host"
        self.assertTrue(any("does not match the capture's own host" in x for x in f), "\n  ".join(f))

    def test_wellformed_host_and_capture_path_pass(self):
        data, cap = make_ctx_data(receipt_by="Riley Park")
        f, _d = self.run_q16(data, cap)
        self.assertEqual([], f, "\n  ".join(f))


if __name__ == "__main__":
    unittest.main(verbosity=2)
