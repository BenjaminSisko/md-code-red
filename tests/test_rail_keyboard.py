#!/usr/bin/env python3
"""MCR-A2-KEY-001: keep rendered rails, runtime keys, and docs in lockstep."""
import json
import os
import re
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "tests", "test_rail_keyboard.js")
TEMPLATE = os.path.join(REPO, "template.html")
USER_GUIDE = os.path.join(REPO, "docs", "USER_GUIDE.md")
README = os.path.join(REPO, "README.md")


def run_keyboard_contract(target):
    node = shutil.which("node")
    if not node:
        raise AssertionError(
            "node is not on PATH -- the keyboard test executes the shipped JavaScript "
            "instead of re-implementing KEYMAP in Python"
        )
    proc = subprocess.run(
        [node, SCRIPT, target, "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError(
            "test_rail_keyboard.js produced no JSON report.\nstdout:\n%s\nstderr:\n%s"
            % (out, err)
        )
    return proc.returncode, report


def documented_rail_rows(markdown):
    """Read the explicit Activity Rail table; prose is not a keyboard contract."""
    rows = []
    row_re = re.compile(
        r"^\|\s*(?P<label>[^|]+?)\s*\|\s*`Ctrl\+Alt\+(?P<key>[0-9]+)`\s*\|",
        re.MULTILINE,
    )
    for match in row_re.finditer(markdown):
        rows.append((match.group("label").strip(), match.group("key")))
    return rows


class RailKeyboardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = run_keyboard_contract(TEMPLATE)
        with open(USER_GUIDE, encoding="utf-8") as handle:
            cls.user_guide = handle.read()
        with open(README, encoding="utf-8") as handle:
            cls.readme = handle.read()

    def test_every_rendered_rail_has_one_working_unique_binding(self):
        self.assertEqual(self.report["failures"], [], self.report["failures"])
        self.assertEqual(self.rc, 0)

    def test_user_guide_mapping_matches_rendered_runtime_order(self):
        expected = [(mapping["label"], mapping["key"]) for mapping in self.report["mappings"]]
        self.assertEqual(
            documented_rail_rows(self.user_guide),
            expected,
            "docs/USER_GUIDE.md must carry one explicit Activity Rail row per rendered "
            "button, in runtime order",
        )

    def test_current_docs_do_not_assign_about_to_the_old_key(self):
        stale = re.compile(r"About[^\n]{0,80}`Ctrl\+Alt\+5`|`Ctrl\+Alt\+5`[^\n]{0,80}About")
        self.assertIsNone(stale.search(self.user_guide), "user guide still maps About to Ctrl+Alt+5")
        self.assertIsNone(stale.search(self.readme), "README still maps About to Ctrl+Alt+5")


if __name__ == "__main__":
    unittest.main()
