#!/usr/bin/env python3
"""test_evidence_export_real.py — G3. Runs tests/test_evidence_export_real.js
over the built artifact.

Same idiom as test_search_index.py: this Python file is what
`python3 -m unittest discover -s tests` actually picks up, and it shells out
to the real Node test so the snapshot it checks is a measurement of the
shipped formatEvidenceText() over REAL committed content — never a
re-implementation and never the hand-written fixture CR-T-28's report sample
turned out to trace back to (Marcus Reed's Panels review, "Ruling on the
reported citation oddity").
"""
import json
import os
import re
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_evidence_export_real.js")
DIST = os.path.join(REPO, "dist")


def find_artifact():
    """The built artifact — this test needs the REAL data island (the real
    content/commands.json entry for firewalld-service-active, not a synthetic
    fixture), and template.html before a build carries only the
    /*__DATA__*/ placeholder. Same lookup qa.py's find_artifact() uses.
    """
    with open(os.path.join(REPO,"build.py"),encoding="utf-8") as handle:
        build = handle.read()
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"',build,re.MULTILINE)
    if not match:
        raise AssertionError("build.py has no literal APP_VERSION")
    artifact=os.path.join(DIST,"md-code-red_%s.html" % match.group(1))
    return artifact if os.path.isfile(artifact) else None


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
        raise AssertionError("test_evidence_export_real.js produced no JSON report.\nstdout:\n%s\nstderr:\n%s"
                             % (out, err))
    return proc.returncode, report


class EvidenceExportRealSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = find_artifact()
        if not artifact:
            raise unittest.SkipTest("no dist/md-code-red_*.html — run python3 build.py first "
                                    "(this test needs the real embedded dataset, not the "
                                    "template's /*__DATA__*/ placeholder)")
        cls.rc, cls.report = run(artifact)

    def test_real_export_matches_committed_snapshot(self):
        self.assertEqual(self.report["failures"], [], self.report["failures"])
        self.assertEqual(self.rc, 0)


if __name__ == "__main__":
    unittest.main()
