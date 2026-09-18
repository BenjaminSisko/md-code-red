#!/usr/bin/env python3
"""test_reference_index.py -- runs tests/test_reference_index.js over the built
artifact, the same idiom test_search_index.py and test_evidence_export_real.py
use: `python3 -m unittest discover -s tests` picks this file up, and the real
work happens in Node against the SHIPPED file, because the code under test is
JavaScript and re-implementing it in Python would test the re-implementation.
"""
import json
import os
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_reference_index.js")
DIST = os.path.join(REPO, "dist")


def find_artifact():
    if not os.path.isdir(DIST):
        return None
    cands = sorted(f for f in os.listdir(DIST)
                   if f.startswith("md-code-red_") and f.endswith(".html"))
    return os.path.join(DIST, cands[-1]) if cands else None


class ReferenceIndexTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        artifact = find_artifact()
        if not artifact:
            raise unittest.SkipTest("no dist/md-code-red_*.html -- run python3 build.py first")
        node = shutil.which("node")
        if not node:
            raise AssertionError("node is not on PATH -- the reference index is JavaScript and "
                                 "this test runs it rather than re-implementing it in Python")
        proc = subprocess.run([node, SCRIPT, artifact, "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            cls.report = json.loads(proc.stdout.decode("utf-8", "replace"))
        except ValueError:
            raise AssertionError("test_reference_index.js produced no JSON report.\nstdout:\n%s\n"
                                 "stderr:\n%s" % (proc.stdout.decode("utf-8", "replace"),
                                                  proc.stderr.decode("utf-8", "replace")))
        cls.rc = proc.returncode

    def test_the_index_resolves_and_hydrates_lazily(self):
        self.assertEqual([], self.report["failures"], self.report["failures"])
        self.assertEqual(0, self.rc)

    def test_the_negative_controls_actually_ran(self):
        """A green report means nothing unless the checks were shown firing."""
        joined = " ".join(self.report.get("notes") or [])
        self.assertIn("negative controls ran first", joined)
        self.assertIn("+1 ordinal shift", joined)


if __name__ == "__main__":
    unittest.main()
