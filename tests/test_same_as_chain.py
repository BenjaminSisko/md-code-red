#!/usr/bin/env python3
"""test_same_as_chain.py — task item 3: resolve same_as chains transitively,
with a cycle guard, in both schema.py and the capture-integrity check.

Riley Park's RILEY-F5 (capture-review-run1-2026-09-18.md): a two-hop same_as
chain (RHEL 10 -> 9 -> 8) silently skipped the "edit resets verified"
integrity check for the far end of the chain, because
extract/import_captures.py's own resolved_command() only ever followed one
same_as hop before giving up. This file pins two things:

  1. extract/schema.py's resolve_chain()/resolved_command() walk a chain of
     ANY length (with a cycle guard), and extract/import_captures.py's own
     resolved_command() now delegates to it instead of keeping a second,
     independently-drifting one-hop copy.
  2. The fail-first case Riley's finding describes: a two-hop chain whose
     TARGET drifted must be CAUGHT by capture_errors(), not silently passed.

Run with either:
    python3 -m pytest tests/
    python3 tests/test_same_as_chain.py
"""

import hashlib
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "extract"))

import schema            # noqa: E402
import import_captures    # noqa: E402


def two_hop_entry():
    """RHEL 7 unavailable, 8 concrete, 9 same_as 8, 10 same_as 9 — a genuine
    two-hop chain, the exact shape Riley Park's RILEY-F5 found in
    firewalld-service-active's RHEL 10 row before this tranche promoted it to
    a concrete command. RHEL 10 resolves through 9 to 8's command."""
    return {
        "id": "fixture-two-hop",
        "rhel_versions": {
            "7": {"unavailable": {"reason": "not packaged", "alternative": None}},
            "8": {"command": "systemctl is-active fixtured", "notes": "n", "changed_in_note": None},
            "9": {"same_as": "8", "changed_in_note": None},
            "10": {"same_as": "9", "changed_in_note": None},
        },
    }


def make_capture(command_as_run):
    cap = {
        "entry_id": "fixture-two-hop",
        "rhel_version": "10",
        "host": "fixture-vm",
        "redhat_release": "fixture release",
        "kernel": "fixture kernel",
        "pkg_versions": {},
        "command_as_run": command_as_run,
        "exit_code": 0,
        "stdout": "active",
        "stderr": "",
        "captured_on": "2026-09-17",
        "captured_by": "Caleb Stone",
        "blast_confirmed": "green",
        "undo_executed": {"run": False, "reason": "read-only"},
        "verify_result": "PASS",
    }
    cap["command_hash_at_capture"] = hashlib.sha256(command_as_run.encode("utf-8")).hexdigest()
    return cap


class SchemaChainResolution(unittest.TestCase):
    """schema.resolve_chain()/resolved_command() — the one resolver
    extract/import_captures.py delegates to and build.py's assemble() mirrors,
    so a chain of any length is handled the same way everywhere."""

    def test_two_hop_chain_resolves_to_the_concrete_command(self):
        self.assertEqual(schema.resolved_command(two_hop_entry(), "10"),
                         "systemctl is-active fixtured")
        self.assertEqual(schema.resolved_command(two_hop_entry(), "9"),
                         "systemctl is-active fixtured")

    def test_unavailable_version_resolves_to_none(self):
        self.assertIsNone(schema.resolved_command(two_hop_entry(), "7"))

    def test_generator_entry_resolves_to_none(self):
        self.assertIsNone(schema.resolved_command({"id": "gen-x", "template": []}, "8"))

    def test_cycle_is_refused_not_looped_forever(self):
        entry = {
            "id": "fixture-cycle",
            "rhel_versions": {
                "7": {"unavailable": {"reason": "n/a", "alternative": None}},
                "8": {"same_as": "9", "changed_in_note": None},
                "9": {"same_as": "8", "changed_in_note": None},
                "10": {"unavailable": {"reason": "n/a", "alternative": None}},
            },
        }
        self.assertIsNone(schema.resolved_command(entry, "8"))


class ImportCapturesDelegatesToSchema(unittest.TestCase):
    """extract/import_captures.py must not keep a second copy of the resolver."""

    def test_resolved_command_is_schema_resolved_command(self):
        entry = two_hop_entry()
        self.assertEqual(import_captures.resolved_command(entry, "10"),
                         schema.resolved_command(entry, "10"))


class TwoHopChainDriftFailFirst(unittest.TestCase):
    """Fail-first fixture (task item 3): a two-hop same_as chain whose target
    drifted must be CAUGHT (the capture refused), not silently skipped.

    Before this tranche, extract/import_captures.py's resolved_command()
    stopped after one same_as hop (RILEY-F5): for a version two hops deep it
    returned None, and capture_errors() — reading "current is None" as
    "nothing to diff against" — let a stale capture through with no warning.
    """

    def test_two_hop_chain_target_drift_is_caught(self):
        entry = two_hop_entry()
        entries_by_id = {entry["id"]: entry}
        # command_as_run matches what was true when this was captured, but
        # entry["8"]["command"] (the chain's target) has since changed —
        # exactly the "edited the command text, forgot to re-capture" case
        # this integrity rule exists to catch, two hops away from where the
        # edit actually happened.
        cap = make_capture("systemctl is-active fixtured-OLD-NAME")
        errs = import_captures.capture_errors("tests/captures/10/fixture-two-hop.json",
                                              cap, entries_by_id)
        self.assertTrue(errs, "a two-hop chain's drifted target must be caught, not silently passed")
        self.assertTrue(any("has changed since this capture" in e for e in errs),
                        "wrong reason:\n  " + "\n  ".join(errs))

    def test_two_hop_chain_no_drift_is_clean(self):
        """Control: the same chain, same command text, produces no integrity error."""
        entry = two_hop_entry()
        entries_by_id = {entry["id"]: entry}
        cap = make_capture("systemctl is-active fixtured")
        errs = import_captures.capture_errors("tests/captures/10/fixture-two-hop.json",
                                              cap, entries_by_id)
        self.assertEqual([], errs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
