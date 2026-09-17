#!/usr/bin/env python3
"""test_coverage_baseline_expiry.py — the Q20 ratchet can expire, and is shown expiring.

MCR-SEC-020, condition F3. `content-src/flag_coverage_baseline.json` records a
flag-dictionary shortfall as accepted, and Q20 fails only when that shortfall
GROWS. That is the right shape for a defect owned by another ticket — and the
wrong shape forever, because a gate holding a residual steady with no end date
stops being a countdown and becomes the plan.

So the baseline names an owner and a date, and Q20 fails once the date passes.
This proves that: the deadline is checked against an injected `today`, so the
expiry is watched firing on this runner today rather than being taken on trust
and discovered by whoever is on shift on 2026-09-26.
"""

import datetime
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

BASELINE = os.path.join(REPO, "content-src", "flag_coverage_baseline.json")


class TheRatchetExpires(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(BASELINE, encoding="utf-8") as fh:
            cls.baseline = json.load(fh)

    def test_the_shipped_baseline_names_an_owner_and_a_date(self):
        self.assertEqual("Caleb Stone (extractor, CR-T-09 follow-up)",
                         self.baseline.get("_retire_owner"))
        self.assertEqual("2026-09-25", self.baseline.get("_retire_by"))

    def test_it_is_not_expired_today(self):
        """Positive control: the gate is green for the right reason, not because it never fires."""
        self.assertEqual([], qa.coverage_baseline_expiry_failures(self.baseline))

    def test_it_is_not_expired_on_the_deadline_itself(self):
        """The owner gets the whole day named in the file."""
        self.assertEqual([], qa.coverage_baseline_expiry_failures(
            self.baseline, today=datetime.date(2026, 9, 25)))

    def test_it_expires_the_day_after(self):
        """The negative control this file exists for."""
        failures = qa.coverage_baseline_expiry_failures(
            self.baseline, today=datetime.date(2026, 9, 26))
        self.assertEqual(1, len(failures), failures)
        self.assertIn("expired on 2026-09-25", failures[0])
        self.assertIn("Caleb Stone", failures[0])

    def test_a_baseline_with_no_retirement_plan_is_refused(self):
        for missing in ({"_retire_by": "2026-09-25"}, {"_retire_owner": "somebody"}, {}):
            with self.subTest(baseline=missing):
                failures = qa.coverage_baseline_expiry_failures(missing)
                self.assertTrue(failures)
                self.assertIn("no retirement plan", failures[0])

    def test_a_malformed_date_is_refused_rather_than_ignored(self):
        failures = qa.coverage_baseline_expiry_failures(
            {"_retire_owner": "somebody", "_retire_by": "next Tuesday"})
        self.assertTrue(failures)
        self.assertIn("not an ISO date", failures[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
