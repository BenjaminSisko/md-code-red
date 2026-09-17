#!/usr/bin/env python3
"""test_evidence_invisible_coverage.py — H2. Runs
tests/test_evidence_invisible_coverage.js over template.html.

Same idiom as test_evidence_export.py: this Python file is what
`python3 -m unittest discover -s tests` actually picks up, and it shells out
to the real Node test so the codepoint list it checks is read fresh from the
shipped INVISIBLE_RE every run (Marcus Reed's H2: the evidence safener's own
hand-rolled range table had already drifted from INVISIBLE_RE once; a test
that hand-copies the codepoint list again risks the exact same drift).
"""
import json
import os
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_evidence_invisible_coverage.js")


def run(target):
    node = shutil.which("node")
    if not node:
        raise AssertionError("node is not on PATH — INVISIBLE_RE and the evidence safener are "
                             "both JavaScript and this test runs them, rather than "
                             "re-implementing either in Python")
    proc = subprocess.run([node, SCRIPT, target, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError("test_evidence_invisible_coverage.js produced no JSON report.\n"
                             "stdout:\n%s\nstderr:\n%s" % (out, err))
    return proc.returncode, report


class EvidenceInvisibleCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = run(os.path.join(REPO, "template.html"))

    def test_every_invisible_re_rejection_is_neutralised(self):
        self.assertEqual(self.report["failures"], [], self.report["failures"])
        self.assertEqual(self.rc, 0)

    def test_invisible_re_actually_rejects_something(self):
        self.assertGreater(self.report["rejected_count"], 0)


if __name__ == "__main__":
    unittest.main()
