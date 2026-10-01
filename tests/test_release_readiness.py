#!/usr/bin/env python3
"""Focused regression tests for release identity and provenance guidance."""

import importlib.util
import hashlib
import json
import os
import re
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

    def test_bqp_summary_names_the_current_artifact_bytes(self):
        version="v1.0.0-alpha.6"
        artifact=os.path.join(REPO,"dist","md-code-red_%s.html" % version)
        sidecar=artifact+".sha256"
        provenance=os.path.join(REPO,"dist","md-code-red_%s.provenance.json" % version)
        summary_path=os.path.join(REPO,"docs","BQP_SUMMARY_%s.md" % version)
        with open(artifact,"rb") as fh:
            blob=fh.read()
        with open(sidecar,"rb") as fh:
            sidecar_blob=fh.read()
        with open(provenance,"rb") as fh:
            provenance_blob=fh.read()
        with open(summary_path,encoding="utf-8") as fh:
            summary=fh.read()
        fingerprint=re.search(
            rb"Content fingerprint \(SHA-256 of every data island\): ([0-9a-f]{64})",blob)
        self.assertIsNotNone(fingerprint)
        for expected in (
            format(len(blob),","),
            hashlib.sha256(blob).hexdigest(),
            fingerprint.group(1).decode("ascii"),
            hashlib.sha256(sidecar_blob).hexdigest(),
            hashlib.sha256(provenance_blob).hexdigest(),
        ):
            self.assertIn(expected,summary)

    def test_html_report_cites_only_recorded_browser_assertions(self):
        base=os.path.join(REPO,"docs","qa")
        with open(os.path.join(base,"QA_RESULTS_v1.0.0-alpha.6-rc.json"),encoding="utf-8") as fh:
            standalone=json.load(fh)
        with open(os.path.join(base,"QA_RESULTS_v1.0.0-alpha.6-rc-http.json"),encoding="utf-8") as fh:
            http=json.load(fh)
        with open(os.path.join(base,"QA_REPORT_v1.0.0-alpha.6-rc.html"),encoding="utf-8") as fh:
            report=fh.read()
        recorded={row["id"] for row in standalone["results"]}|{row["id"] for row in http["results"]}
        cited=set(re.findall(r"TC-[A-Za-z0-9_-]+",report))
        self.assertEqual(cited-recorded,set(),"HTML report cites nonexistent browser assertions")


if __name__ == "__main__":
    unittest.main()
