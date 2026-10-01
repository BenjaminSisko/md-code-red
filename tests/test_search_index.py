#!/usr/bin/env python3
"""test_search_index.py — CR-T-29. Runs tests/test_search_index.js over template.html.

Same idiom as test_hostile_inputs.py: this Python file is what
`python3 -m unittest discover -s tests` actually picks up, and it shells out
to the real Node test so the number that answers "<100ms on the full
dataset" is a measurement of the shipped JavaScript, not a re-implementation.
"""
import json
import os
import re
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_search_index.js")
DIST = os.path.join(REPO, "dist")


def find_artifact():
    """The built artifact — this test needs a REAL data island (buildIndex()
    runs against the full embedded dataset, not a synthetic fixture), and
    template.html before a build carries only the /*__DATA__*/ placeholder.
    Same lookup qa.py's find_artifact() uses; this test's place in the gate
    order (`python3 build.py && ... && python3 -m unittest discover`) means
    dist/ always exists by the time it runs.
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
        raise AssertionError("node is not on PATH — CR-T-29's timing claim can only be measured "
                             "by running the shipped JavaScript, not re-implementing it in Python")
    proc = subprocess.run([node, SCRIPT, target, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError("test_search_index.js produced no JSON report.\nstdout:\n%s\nstderr:\n%s"
                             % (out, err))
    return proc.returncode, report


class SearchIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = find_artifact()
        if not artifact:
            raise unittest.SkipTest("no dist/md-code-red_*.html — run python3 build.py first "
                                    "(this test needs the real embedded dataset, not the "
                                    "template's /*__DATA__*/ placeholder)")
        cls.rc, cls.report = run(artifact)

    def test_index_builds_and_queries_under_budget(self):
        self.assertEqual(self.report["failures"], [], self.report["failures"])
        self.assertEqual(self.rc, 0)

    def test_build_time_under_100ms(self):
        self.assertLess(self.report["build_ms"], 100.0)

    def test_every_query_under_100ms(self):
        self.assertLess(self.report["worst_query_ms"], 100.0)

    def test_no_match_state_is_explicit(self):
        self.assertTrue(self.report["no_match_explicit"])

    def test_index_is_non_trivial(self):
        # A template.html with no build yet still has an embedded seed island
        # in this repo's committed content/, so the index should never be empty.
        self.assertGreater(self.report["index_size"], 0)


if __name__ == "__main__":
    unittest.main()
