#!/usr/bin/env python3
"""test_anchor_resolution.py -- Q25 (threat model v2, M2) watched firing.

Q25 re-resolves every stored citation against the committed source and asserts
the source actually contains the text the record claims. This file is the proof
that it does something: it drives the same resolver over DELIBERATELY BROKEN
records, on committed fixtures, and fails if any of them is accepted.

Why fixtures rather than only in-line mutations: `tests/fixtures/anchors/`
carries the four shapes as JSON, so a reviewer can read what a broken anchor
looks like without running anything, and the file is what the gate was watched
failing on before it was believed.

The pairing that makes each case a test rather than a ritual: every broken
record is accompanied by the CORRECT one it was derived from, and the correct
one must resolve. A resolver that refused everything would pass the first half
of each case and fail the second.
"""

import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

FIXTURES = os.path.join(REPO, "tests", "fixtures", "anchors", "broken_anchors.json")
CORPUS = os.path.join(REPO, "content", "reference_commands.json")


class AnchorResolverFiresOnBrokenAnchors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES, encoding="utf-8") as fh:
            cls.cases = json.load(fh)["cases"]

    def test_the_intact_record_in_every_case_resolves(self):
        """Positive control. Without it, a resolver that returns False for
        everything passes every other test in this file."""
        for case in self.cases:
            rec = case["intact"]
            ok, why = qa.resolve_anchor(rec, rec["o"][0])
            self.assertTrue(ok, "%s: the INTACT record did not resolve: %s" % (case["name"], why))

    def test_every_broken_anchor_is_refused(self):
        for case in self.cases:
            rec = case["broken"]
            ok, _why = qa.resolve_anchor(rec, rec["o"][0])
            self.assertFalse(ok, "%s: Q25 accepted a broken anchor" % case["name"])

    def test_the_refusal_says_what_was_wrong(self):
        """A gate that fails without naming the record and the mismatch costs
        whoever is on shift an hour of bisecting."""
        for case in self.cases:
            rec = case["broken"]
            _ok, why = qa.resolve_anchor(rec, rec["o"][0])
            self.assertTrue(why and len(why) > 20, "%s: unhelpful refusal %r" % (case["name"], why))
            for token in case.get("expect_in_reason", []):
                self.assertIn(token, why, case["name"])


class TheDigestIsPartOfTheAnchor(unittest.TestCase):
    """`file@sha256#anchor`. Without the digest half, "it re-resolves" is a claim
    about whatever is at that path today, not about the bytes mined."""

    def test_the_shipped_corpus_pins_every_file_its_anchors_point_into(self):
        with open(CORPUS, encoding="utf-8") as fh:
            corpus = json.load(fh)
        meta = corpus.get("_meta") or {}
        pinned = set((meta.get("source_files") or {}).keys())
        self.assertTrue(pinned, "no source_files manifest")
        wanted = set()
        for rec in corpus["commands"]:
            for occ in rec.get("o") or []:
                path = qa._anchor_file_for(occ)
                if path:
                    wanted.add(path)
        self.assertEqual(set(), wanted - pinned,
                         "anchors point into files the manifest does not pin")

    def test_a_changed_source_file_fails_the_digest_check(self):
        meta = {"source_files": {"build.py": {"sha256": "0" * 64, "bytes": 1}}}
        failures, checked = qa.anchor_digest_failures(meta)
        self.assertEqual(0, checked)
        self.assertEqual(1, len(failures), failures)
        self.assertIn("different bytes", failures[0])

    def test_a_missing_manifest_fails_rather_than_passing_quietly(self):
        failures, checked = qa.anchor_digest_failures({})
        self.assertEqual(0, checked)
        self.assertEqual(1, len(failures))
        self.assertIn("source_files", failures[0])


class TheOneTrojanTable(unittest.TestCase):
    """M8. Three statements existed; one remains, and the JavaScript one is
    proved equal to it rather than trusted."""

    def test_qa_reads_the_table_out_of_schema_and_does_not_restate_it(self):
        with open(os.path.join(REPO, "extract", "schema.py"), encoding="utf-8") as fh:
            parsed = qa.parse_schema_ranges(fh.read(), "TROJAN_RANGES")
        self.assertEqual(parsed, qa.TROJAN_RANGES)
        self.assertGreater(len(parsed), 10)

    def test_an_empty_or_absent_table_raises_rather_than_defaulting(self):
        with self.assertRaises(ValueError):
            qa.parse_schema_ranges("NOTHING_HERE = 1\n", "TROJAN_RANGES")
        with self.assertRaises(ValueError):
            qa.parse_schema_ranges("TROJAN_RANGES = [\n]\n", "TROJAN_RANGES")

    def test_a_drifted_javascript_table_is_caught(self):
        """The exact drift condition H2 already caught once by hand."""
        drifted = ('var INVISIBLE_RE=/[\\u200B-\\u200F]/;\n'
                   'var HEADER_UNSAFE_G=/[\\u0000-\\u001F]/g;')
        failures = qa.trojan_table_agreement_failures(drifted)
        self.assertTrue(failures)
        self.assertIn("MISSING", failures[0])

    def test_an_unliftable_table_fails_rather_than_passing(self):
        failures = qa.trojan_table_agreement_failures("var x=1;")
        self.assertEqual(1, len(failures))
        self.assertIn("not being checked", failures[0])


if __name__ == "__main__":
    unittest.main()
