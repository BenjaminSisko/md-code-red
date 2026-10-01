#!/usr/bin/env python3
"""The guided lsblk workflow stays useful and release-safe."""
import json
import os
import subprocess
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(relative):
    with open(os.path.join(REPO, relative), encoding="utf-8") as handle:
        return json.load(handle)


class GuidedLsblkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = next(
            entry
            for entry in load("content/commands.json")["entries"]
            if entry["id"] == "gen-lsblk-inspect-storage"
        )
        cls.golden = load("tests/fixtures/golden-commands.json")["generators"][
            cls.entry["id"]
        ]

    def assemble(self, versions, values):
        job = {
            "fields": self.entry["fields"],
            "shapes": [self.entry["template"]],
            "versions": versions,
            "combos": [values],
            "detail": True,
        }
        result = subprocess.run(
            ["node", os.path.join(REPO, "tests", "shift_crosscheck_driver.js")],
            input=json.dumps(job),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)["results"]

    def test_filesystem_and_lvm_tree_preset_is_available_on_every_release(self):
        expected = "lsblk -o 'NAME,TYPE,FSTYPE,SIZE,MOUNTPOINT'"
        self.assertEqual(
            [expected] * 4,
            self.assemble(("7", "8", "9", "10"), self.golden["values"]),
        )
        self.assertEqual(
            {version: expected for version in ("7", "8", "9", "10")},
            self.golden["commands"],
        )

    def test_rhel9_and_10_offer_the_benchmark_multi_mount_view(self):
        values = {"columns": "NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS"}
        expected = "lsblk -o 'NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS'"
        self.assertEqual([expected, expected], self.assemble(("9", "10"), values))
        self.assertEqual([None, None], self.assemble(("7", "8"), values))

    def test_presets_cover_capacity_filesystems_topology_and_lvm_relationships(self):
        options = self.entry["fields"][0]["options"]
        values = [option if isinstance(option, str) else option["value"] for option in options]
        self.assertIn("NAME,TYPE,SIZE,MOUNTPOINT", values)
        self.assertIn("NAME,TYPE,FSTYPE,SIZE,MOUNTPOINT", values)
        self.assertIn("NAME,KNAME,PKNAME,TYPE,TRAN,SIZE,MOUNTPOINT", values)
        modern = next(
            option
            for option in options
            if isinstance(option, dict) and option["value"].endswith("MOUNTPOINTS")
        )
        self.assertEqual(["9", "10"], modern["versions"])
        self.assertTrue(all(value.startswith("NAME,") for value in values))


if __name__ == "__main__":
    unittest.main()
