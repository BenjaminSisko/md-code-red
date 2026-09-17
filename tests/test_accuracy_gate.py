#!/usr/bin/env python3
"""test_accuracy_gate.py — CR-T-08. Proves the Q10 accuracy gate can actually fail.

A gate nobody has ever seen fail is a gate nobody knows works. These tests run
the real qa.accuracy_failures() — the same function gate_q10 calls on every CI
build — against two committed fixtures cut from the shipping RHEL 9 dataset:

  clean_rules_rhel9.json     the deterministic Q10 sample, unmodified  -> PASS
  mutated_rules_rhel9.json   the same sample with six planted edits    -> FAIL

The control case comes first on purpose. If the clean fixture ever fails, the
mutated fixture failing proves nothing: the comparison would be broken rather
than discriminating.

Stdlib only. Discovered by `python3 -m unittest discover -s tests`, which is what
the CI workflow already runs.
"""
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

FIXTURES = os.path.join(REPO, "tests", "fixtures", "accuracy")


def load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


class AccuracyGateTests(unittest.TestCase):
    """The pinned XCCDF is parsed once for the whole class: it is a 5 MB file."""

    @classmethod
    def setUpClass(cls):
        pin_failures, _ = qa.verify_pins()
        if pin_failures:
            raise unittest.SkipTest("pinned sources unavailable: %s" % "; ".join(pin_failures))
        cls.src, _ = qa.parse_source("9")
        cls.clean = load("clean_rules_rhel9.json")
        cls.mutated = load("mutated_rules_rhel9.json")

    # ---- control ---------------------------------------------------------
    def test_clean_fixture_passes(self):
        bad, sample = qa.accuracy_failures("9", self.clean["rules"], self.src, full_set=False)
        self.assertEqual(bad, [], "the unmodified sample must diff clean against the pinned XCCDF")
        self.assertEqual(len(sample), len(self.clean["rules"]),
                         "a dataset at the sample size is checked in full, not sampled again")

    def test_shipping_dataset_passes_in_full(self):
        """The whole shipping dataset, including the ID-set parity layer."""
        with open(os.path.join(REPO, "content", "rules_rhel9.json"), encoding="utf-8") as f:
            shipping = json.load(f)
        bad, sample = qa.accuracy_failures("9", shipping["rules"], self.src)
        self.assertEqual(bad, [])
        self.assertEqual(len(sample), qa.SAMPLE_PER_RELEASE,
                         "ADR-001 §7.3 Q10 requires 20 samples per release")

    # ---- the mutation ----------------------------------------------------
    def test_mutated_fixture_fails(self):
        bad, _ = qa.accuracy_failures("9", self.mutated["rules"], self.src, full_set=False)
        self.assertTrue(bad, "the gate reported a mutated dataset clean — Q10 is not a gate")

    def test_every_planted_mutation_is_caught(self):
        """Not 'something failed' — each planted edit is named in the output."""
        bad, _ = qa.accuracy_failures("9", self.mutated["rules"], self.src, full_set=False)
        blob = "\n".join(bad)
        expect = {
            "t": "title differs from source",
            "rid": "rule id",
            "cci": "CCI",
            "c": "CAT",
            "fix": "fix text",
            "chk": "check text",
        }
        for mutation in self.mutated["_meta"]["mutations"]:
            sid, field = mutation["stig_id"], mutation["field"]
            hits = [line for line in bad if line.startswith(sid + ":")]
            self.assertTrue(hits, "mutation of %s on %s produced no failure" % (field, sid))
            self.assertTrue(any(expect[field] in h for h in hits),
                            "mutation of %s on %s was not reported as a %s mismatch: %s"
                            % (field, sid, expect[field], hits))
        self.assertIn("RHEL-09", blob)

    def test_fix_text_mutation_is_past_the_prefix_window(self):
        """The planted fix-text edit must be invisible to a prefix-only check.

        Q10 used to compare the first 100 characters. The fixture deliberately
        appends past that, so this test fails if anyone reinstates a prefix-only
        comparison and calls it equivalent.
        """
        target = None
        for mutation in self.mutated["_meta"]["mutations"]:
            if mutation["field"] == "fix":
                target = mutation["stig_id"]
        self.assertIsNotNone(target)
        clean = {r["i"]: r for r in self.clean["rules"]}[target]
        dirty = {r["i"]: r for r in self.mutated["rules"]}[target]
        self.assertNotEqual(clean["fix"], dirty["fix"])
        self.assertEqual(clean["fix"][:100], dirty["fix"][:100])

    # ---- the second layer: parity outside the sample ---------------------
    def test_dropped_rule_outside_the_sample_is_caught(self):
        """A stride of 20-in-445 would walk past a deleted rule. Parity does not."""
        with open(os.path.join(REPO, "content", "rules_rhel9.json"), encoding="utf-8") as f:
            shipping = json.load(f)
        rules = shipping["rules"]
        sampled = set(qa.accuracy_sample([r["i"] for r in rules]))
        victim = None
        for r in rules:
            if r["i"] not in sampled:
                victim = r["i"]
                break
        self.assertIsNotNone(victim, "every rule is in the sample — this test has nothing to prove")
        reduced = [r for r in rules if r["i"] != victim]
        bad, _ = qa.accuracy_failures("9", reduced, self.src)
        self.assertTrue(any("not embedded" in b for b in bad),
                        "dropping %s outside the sample was not caught" % victim)

    def test_renamed_rule_outside_the_sample_is_caught(self):
        with open(os.path.join(REPO, "content", "rules_rhel9.json"), encoding="utf-8") as f:
            shipping = json.load(f)
        rules = [dict(r) for r in shipping["rules"]]
        sampled = set(qa.accuracy_sample([r["i"] for r in rules]))
        for r in rules:
            if r["i"] not in sampled:
                r["i"] = "RHEL-09-999999"
                break
        bad, _ = qa.accuracy_failures("9", rules, self.src)
        self.assertTrue(any("absent from the pinned XCCDF" in b for b in bad))

    def test_duplicate_stig_id_is_caught(self):
        rules = list(self.clean["rules"]) + [dict(self.clean["rules"][0])]
        bad, _ = qa.accuracy_failures("9", rules, self.src, full_set=False)
        self.assertTrue(any("embedded twice" in b for b in bad))

    # ---- the sample itself ----------------------------------------------
    def test_sample_is_deterministic(self):
        ids = [r["i"] for r in self.mutated["rules"]] * 1
        self.assertEqual(qa.accuracy_sample(ids), qa.accuracy_sample(list(reversed(ids))),
                         "the sample must not depend on input order — no RNG, no dict ordering")


if __name__ == "__main__":
    unittest.main()
