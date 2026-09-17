#!/usr/bin/env python3
"""test_hostile_inputs.py — CR-T-16. Runs the hostile-input harness over template.html.

This is the same gate qa.py Q18 runs against the BUILT artifact; this copy runs
it against the source template, so a broken assembler is caught by
`python3 -m unittest discover -s tests` before a build is even attempted.

Node is REQUIRED for this test, and its absence is a FAILURE, not a skip. The
assembler is JavaScript; the only honest way to test it is to run it. A Python
re-implementation of the quoting would be a second assembler to keep in sync,
and the one that shipped would be the one nobody tested. CI installs Node for
exactly this reason (.forgejo/workflows/ci.yml, actions/setup-node).
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(REPO, "tests", "hostile_harness.js")
FIXTURE = os.path.join(REPO, "tests", "fixtures", "hostile-inputs.json")


def run_harness(target):
    node = shutil.which("node")
    if not node:
        raise AssertionError(
            "node is not on PATH. The command assembler is JavaScript and this gate runs it; "
            "install Node (CI uses actions/setup-node@v4) rather than skipping the one test "
            "that stands between a form field and a root shell.")
    proc = subprocess.run([node, HARNESS, target, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError("harness produced no JSON report.\nstdout:\n%s\nstderr:\n%s" % (out, err))
    return proc.returncode, report


class HostileInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = run_harness(os.path.join(REPO, "template.html"))
        with open(FIXTURE, encoding="utf-8") as f:
            cls.fixture = json.load(f)

    def test_no_vector_escapes_its_quoting(self):
        self.assertEqual(self.report["failures"], [],
                         "hostile vectors were neither rejected nor safely quoted")
        self.assertEqual(self.rc, 0)

    def test_every_field_type_and_vector_ran(self):
        self.assertEqual(self.report["field_types"], len(self.fixture["field_types"]))
        self.assertEqual(self.report["vectors"], len(self.fixture["vectors"]))
        self.assertEqual(self.report["versions"], 4)
        expected = (self.report["field_types"] * self.report["vectors"] * 4 * 3
                    + 5 * self.report["vectors"] * 4)
        self.assertEqual(self.report["checks"], expected,
                         "the harness did not run every field type x vector x release x shape")

    def test_outcomes_are_accounted_for(self):
        self.assertEqual(self.report["rejected"] + self.report["quoted_safe"],
                         self.report["checks"],
                         "a check ended in neither state — the harness lost track of an outcome")

    def test_the_gate_is_not_passing_by_rejecting_everything(self):
        """Positive controls: the benign value of every field type still works."""
        self.assertGreater(self.report["positive_controls"], 0)
        self.assertGreater(self.report["quoted_safe"], 0,
                           "no vector was ever accepted-and-quoted — the free-text path is untested")

    def test_fixture_covers_the_threat_model_vector_classes(self):
        """threat-model-v1 §12 item 1 names the minimum vector set by class."""
        classes = set(v["class"] for v in self.fixture["vectors"])
        for required in ("command substitution", "statement separator", "newline injection",
                         "option injection", "unicode look-alike", "path traversal",
                         "length", "quote breaking", "NUL", "invisible character"):
            self.assertIn(required, classes, "fixture is missing the %s vector class" % required)

    def test_fixture_declares_its_provenance(self):
        src = self.fixture["_meta"]["source"]
        for key in ("title", "url_or_man", "version", "retrieved_on", "license_class"):
            self.assertTrue(src.get(key), "hostile-inputs fixture source.%s missing" % key)


if __name__ == "__main__":
    sys.exit(unittest.main())
