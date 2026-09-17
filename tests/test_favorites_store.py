#!/usr/bin/env python3
"""test_favorites_store.py — CR-T-30. Runs tests/test_favorites_store.js over template.html.

Same idiom as test_hostile_inputs.py: lifts the pure MCR-FAVORITES block
(sanitizeIdList()) out of the source template and drives it, under Node,
with hostile localStorage shapes — raw text, objects, numbers, oversized
lists, duplicates — proving only known-good ID strings ever survive
(threat-model-v1 §7: "favorites store content IDs only, never raw text").
"""
import json
import os
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_favorites_store.js")


def run(target):
    node = shutil.which("node")
    if not node:
        raise AssertionError("node is not on PATH — sanitizeIdList() is JavaScript and this test "
                             "runs it, rather than re-implementing it in Python")
    proc = subprocess.run([node, SCRIPT, target, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError("test_favorites_store.js produced no JSON report.\nstdout:\n%s\nstderr:\n%s"
                             % (out, err))
    return proc.returncode, report


class FavoritesStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = run(os.path.join(REPO, "template.html"))

    def test_only_known_good_ids_survive(self):
        self.assertEqual(self.report["failures"], [], self.report["failures"])
        self.assertEqual(self.rc, 0)


if __name__ == "__main__":
    unittest.main()
