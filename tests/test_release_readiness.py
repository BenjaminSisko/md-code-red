#!/usr/bin/env python3
"""Focused regression tests for release identity and provenance guidance."""

import importlib.util
import os
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "extract", "make_provenance.py")

spec = importlib.util.spec_from_file_location("make_provenance", SCRIPT)
make_provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_provenance)


class ReleaseReadinessTests(unittest.TestCase):
    def test_review_lineage_is_derived_from_the_requested_version(self):
        version = "v9.8.7-test.6"
        lineage = make_provenance.review_lineage(version)

        self.assertEqual(lineage["release_version"], version)
        self.assertIn(version, lineage["change_record"])
        self.assertEqual(
            lineage["required_release_evidence"],
            [
                "docs/BQP_SUMMARY_%s.md" % version,
                "docs/QA_REPORT_%s.md" % version,
                "docs/SECURITY_REVIEW_%s.md" % version,
                "docs/RELEASE_REPORT_%s.md" % version,
            ],
        )

    def test_review_lineage_does_not_claim_a_historical_release_review(self):
        lineage = make_provenance.review_lineage("v9.8.7-test.6")
        rendered = repr(lineage)

        self.assertNotIn("alpha3_", rendered)
        self.assertNotIn("MCR-A2-KEY-001", rendered)
        self.assertNotIn("46507926500ea92aa8904c6a9d69698e2d3ba705", rendered)
        self.assertIn("must be recorded", lineage["independent_review"])
        self.assertIn("does not itself assert", lineage["independent_review"])

    def test_missing_artifact_guidance_uses_safe_dist_cleanup(self):
        with self.assertRaises(SystemExit) as caught:
            make_provenance.find_artifact("version-that-does-not-exist")

        message = str(caught.exception)
        self.assertIn("git clean -fdx dist", message)
        self.assertNotIn("rm -rf", message)


if __name__ == "__main__":
    unittest.main()
