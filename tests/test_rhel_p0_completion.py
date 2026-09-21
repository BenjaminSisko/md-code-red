#!/usr/bin/env python3
"""The Red Hat P0 command set includes both LVM initialization steps."""
import json
import os
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(relative):
    with open(os.path.join(REPO, relative), encoding="utf-8") as handle:
        return json.load(handle)


class RhelP0CompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = {e["id"]: e for e in load("content/commands.json")["entries"]}
        cls.tools = {t["id"]: t for t in load("content/tools.json")["tools"]}
        cls.golden = load("tests/fixtures/golden-commands.json")["generators"]
        cls.patterns = {p["id"]: p for p in load("content/dangerous.json")["patterns"]}

    def test_physical_volume_builder_is_shipped_and_red(self):
        entry = self.entries["gen-pvcreate-initialize"]
        self.assertEqual(entry["tool"], "pvcreate")
        self.assertEqual(entry["blast"], "red")
        self.assertEqual(entry["template"], [{"lit": "pvcreate"}, {"field": "device"}])
        self.assertIn("pvcreate", self.tools)
        self.assertEqual(self.patterns["dp-pvcreate"]["blast_floor"], "red")

    def test_volume_group_builder_is_shipped_and_red(self):
        entry = self.entries["gen-vgcreate-new-vg"]
        self.assertEqual(entry["tool"], "vgcreate")
        self.assertEqual(entry["blast"], "red")
        self.assertEqual(
            entry["template"],
            [{"lit": "vgcreate"}, {"field": "name"}, {"field": "device"}],
        )
        self.assertIn("vgcreate", self.tools)
        self.assertEqual(self.patterns["dp-vgcreate"]["blast_floor"], "red")

    def test_both_builders_have_all_release_golden_oracles(self):
        expected = {
            "gen-pvcreate-initialize": "pvcreate '/dev/sdb'",
            "gen-vgcreate-new-vg": "vgcreate 'vgdata' '/dev/sdb'",
        }
        for entry_id, command in expected.items():
            row = self.golden[entry_id]
            self.assertEqual(row["blast"], "red")
            self.assertEqual(row["commands"], {v: command for v in ("7", "8", "9", "10")})


if __name__ == "__main__":
    unittest.main()
