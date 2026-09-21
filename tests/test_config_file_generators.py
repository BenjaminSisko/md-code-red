#!/usr/bin/env python3
"""Completion contract for roadmap item 260917-004."""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ConfigFileGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "content", "commands.json"), encoding="utf-8") as fh:
            cls.entries = json.load(fh)["entries"]
        with open(os.path.join(REPO, "docs", "IDEAS.md"), encoding="utf-8") as fh:
            cls.ideas = fh.read()

    def test_all_six_roadmap_generators_ship(self):
        expected = {
            "gen-sshd-config": ("sshd", "lines"),
            "gen-chrony-config": ("chronyd", "lines"),
            "gen-rsyslog-config": ("rsyslogd", "lines"),
            "gen-sudoers-config": ("visudo", "lines"),
            "gen-systemd-unit": ("systemd-analyze", "ini"),
            "gen-cron-config": ("crontab", "lines"),
        }
        by_id = {e["id"]: e for e in self.entries}
        self.assertTrue(set(expected).issubset(by_id))
        for entry_id, (tool, kind) in expected.items():
            entry = by_id[entry_id]
            self.assertEqual(entry["tool"], tool, entry_id)
            self.assertEqual(entry.get("doc", {}).get("kind"), kind, entry_id)
            self.assertTrue(entry.get("doc", {}).get("filename"), entry_id)
            self.assertTrue(entry.get("verify"), entry_id)
            self.assertTrue(entry.get("undo"), entry_id)

    def test_roadmap_item_is_marked_shipped(self):
        block = self.ideas.split("## [ID: 260917-004]", 1)[1].split("\n---", 1)[0]
        self.assertIn("**Status:** Shipped", block)


if __name__ == "__main__":
    unittest.main()
