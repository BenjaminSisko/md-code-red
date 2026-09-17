#!/usr/bin/env python3
"""test_q16_receipts.py — task item 2: a per-version verified receipt must be
backed by its OWN capture file for that exact (entry, rhel_version) pair.

qa.py's gate_q16() is exercised directly against a hand-built, ASSEMBLED-shape
ctx["data"] (same shape build.py leaves in the shipped data island — same_as
already resolved to a concrete command) rather than through a full build, so
these cases run in milliseconds. gate_q16() reads a receipt's capture file
off disk by REPO-relative path exactly the way a real build does, so each
case points qa.REPO at a scratch directory holding just the one capture file
it needs (unittest.mock.patch.object, restored after every case).

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


class Q16ReceiptBacking(unittest.TestCase):
    """Fail-first fixtures (task item 2): a receipt with no matching capture,
    or with a capture some OTHER content edited since, or captured by the
    same person the receipt names as the QA reviewer, must all fail."""

    def run_q16(self, data, cap):
        tmp = tempfile.mkdtemp(prefix="mcr-q16-")
        try:
            capdir = os.path.join(tmp, "tests", "captures", "8")
            os.makedirs(capdir)
            with open(os.path.join(capdir, "fixture-q16.json"), "w", encoding="utf-8") as f:
                json.dump(cap, f)
            with mock.patch.object(qa, "REPO", tmp):
                return qa.gate_q16({"data": data})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_receipt_by_same_as_captured_by_fails(self):
        """Fail-first #1: SME captures, QA verifies — the same name cannot
        do both for one receipt."""
        data, cap = make_ctx_data(receipt_by="Caleb Stone")  # same as captured_by
        f, _d = self.run_q16(data, cap)
        self.assertTrue(f, "a receipt whose 'by' equals the capture's 'captured_by' must fail")
        self.assertTrue(any("same person as the capture's captured_by" in x for x in f),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
