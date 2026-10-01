#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FeedbackSupportArtifactTests(unittest.TestCase):
    def test_generated_release_facts_are_current(self):
        result = subprocess.run(
            ["python3", os.path.join(REPO, "tools", "generate_release_facts.py"), "--check"],
            cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with open(os.path.join(REPO, "docs", "generated", "release-facts.json"),
                  encoding="utf-8") as handle:
            facts = json.load(handle)
        self.assertEqual(facts["curated_entries"], 200)
        self.assertEqual(facts["guided_generators"], 58)
        self.assertEqual(facts["static_entries"], 142)
        self.assertEqual(facts["default_rhel"], "8")
        self.assertEqual(facts["flag_rows_total"], 3178)

    def test_user_guide_distinguishes_reference_from_execution(self):
        with open(os.path.join(REPO, "docs", "USER_GUIDE.md"), encoding="utf-8") as handle:
            guide = handle.read()
        self.assertIn("command and\n   control reference", guide)
        self.assertIn("not proof of execution", guide)
        self.assertNotIn("additional config-file generators remain", guide)
        with open(os.path.join(REPO, "docs", "generated", "release-facts.json"),
                  encoding="utf-8") as handle:
            facts = json.load(handle)
        self.assertIn("%d curated" % facts["curated_entries"], guide)
        self.assertIn("%d **guided form generators**" % facts["guided_generators"], guide)
        self.assertIn("default is RHEL %s" % facts["default_rhel"], guide)

    def test_troubleshooting_has_all_requested_families_and_safe_stops(self):
        path = os.path.join(REPO, "content", "rhel_troubleshooting.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        expected = {"boot-emergency", "fstab", "dnf-rpm", "networkmanager",
                    "firewalld", "lvm-filesystem", "selinux-avc", "time-sync", "rsyslog"}
        self.assertEqual({tree["id"] for tree in data["trees"]}, expected)
        for tree in data["trees"]:
            self.assertTrue(tree["preconditions"], tree["id"])
            self.assertTrue(tree["branches"], tree["id"])
            self.assertIn("Stop", tree["escalate"], tree["id"])
            for branch in tree["branches"]:
                self.assertTrue(branch["observe"], (tree["id"], branch))
                self.assertTrue(branch["next"], (tree["id"], branch))

    def test_validation_matrix_preserves_unknowns(self):
        with open(os.path.join(REPO, "content-src", "real-host-validation-matrix.json"),
                  encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertTrue(data["policy"]["read_only_only"])
        self.assertTrue(data["policy"]["unknowns_remain_unknown"])
        self.assertEqual(data["releases"]["9"]["verified_receipts"], 0)
        self.assertIn("legacy/reference", data["releases"]["7"]["support_posture"])
        self.assertGreaterEqual(len(data["read_only_cases"]), 9)
        result = subprocess.run(
            ["python3", os.path.join(REPO, "tools", "validation_matrix.py"), "check"],
            cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_signing_manifest_is_deterministic_and_unsigned_is_not_valid(self):
        script = os.path.join(REPO, "tools", "release_signing.py")
        with tempfile.TemporaryDirectory() as directory:
            a = os.path.join(directory, "a.txt")
            b = os.path.join(directory, "b.txt")
            with open(a, "wb") as handle:
                handle.write(b"a")
            with open(b, "wb") as handle:
                handle.write(b"b")
            first = os.path.join(directory, "SHA256SUMS")
            second = os.path.join(directory, "SECOND")
            for output, inputs in ((first, [b, a]), (second, [a, b])):
                result = subprocess.run(["python3", script, "prepare", *inputs, "--output", output],
                                        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with open(first, "rb") as one, open(second, "rb") as two:
                self.assertEqual(one.read(), two.read())
            result = subprocess.run(["python3", script, "verify", first],
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("do not authenticate a publisher", result.stderr)
            result = subprocess.run(
                ["python3", script, "sign", first,
                 "--key-fingerprint", "publisher@example.invalid"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("40- or 64-hex-character", result.stderr)


if __name__ == "__main__":
    unittest.main()
