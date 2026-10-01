#!/usr/bin/env python3
"""Regression coverage for the dedicated Git rail and its guided scenarios."""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(REPO, name), encoding="utf-8") as fh:
        return json.load(fh)


class GitRailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = load("content/commands.json")["entries"]
        cls.tools = load("content/tools.json")["tools"]
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as fh:
            cls.template = fh.read()

    def test_git_tool_and_entries_are_reachable(self):
        git_tools = {t["id"] for t in self.tools if t.get("category") == "git"}
        self.assertEqual(git_tools, {"git"})
        git_entries = [e for e in self.entries if e.get("tool") == "git"]
        self.assertGreater(len(git_entries), 0)
        self.assertEqual(
            sorted({e["tool"] for e in git_entries} - git_tools), [],
            "Git content points at a tool the Git rail cannot render",
        )

    def test_git_guided_workflows_include_the_roadmap_and_repaired_tasks(self):
        expected = {
            "gen-git-clone", "gen-git-branch", "gen-git-merge",
            "gen-git-rebase", "gen-git-tag", "gen-git-log",
            "gen-git-bisect", "gen-git-recovery",
            "git-checkout-discard-changes", "git-recovery-wrong-branch",
            "git-recovery-lost-commit",
        }
        actual = {
            e["id"] for e in self.entries
            if e.get("tool") == "git" and "fields" in e and "template" in e
        }
        self.assertEqual(actual, expected)

    def test_template_has_live_git_slice_and_routes_git_entries_back_to_it(self):
        self.assertIn('data-rail="git"', self.template)
        self.assertIn('STATE.rail==="git"', self.template)
        self.assertIn('entry.tool==="git"', self.template)
        self.assertNotIn("Git generator not implemented", self.template)

    def test_builder_slice_explicitly_excludes_git(self):
        self.assertIn('all[ti].category!=="git"', self.template)


if __name__ == "__main__":
    unittest.main()
