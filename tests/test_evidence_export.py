#!/usr/bin/env python3
"""test_evidence_export.py — CR-T-28. Runs tests/test_evidence_export.js over template.html.

Same idiom as test_hostile_inputs.py: lifts the pure MCR-EVIDENCE block (the
formatter behind Export as Evidence) out of the source template and proves,
under Node (the formatter is JavaScript; a Python re-implementation would be
a second formatter to keep in sync), that two exports of the same entry are
byte-identical except the operator's own date line, and that the "not
captured" / "not available" paths never fabricate a value.
"""
import json
import os
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_evidence_export.js")


def run(target):
    node = shutil.which("node")
    if not node:
        raise AssertionError("node is not on PATH — the evidence formatter is JavaScript and this "
                             "test runs it, rather than re-implementing it in Python")
    proc = subprocess.run([node, SCRIPT, target, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError("test_evidence_export.js produced no JSON report.\nstdout:\n%s\nstderr:\n%s"
                             % (out, err))
    return proc.returncode, report


class EvidenceExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = run(os.path.join(REPO, "template.html"))

    def test_export_is_deterministic_except_operator_date(self):
        self.assertEqual(self.report["failures"], [], self.report["failures"])
        self.assertEqual(self.rc, 0)

    def test_byte_identical_flag_true(self):
        self.assertTrue(self.report["byte_identical_except_date"])


if __name__ == "__main__":
    unittest.main()
