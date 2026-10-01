#!/usr/bin/env python3
"""test_empty_set_gates.py — a gate with nothing to check must FAIL (AL-GATE3-004).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_empty_set_gates.py

Every per-item gate in qa.py loops `for e in entries` and records a failure only
when it finds something wrong WITH an item. Zero items is therefore a PASS, by
vacuity. Al Kowalski's Gate 3 review mutation-tested it and got:

    Q4   -> PASS (0 failures)
    Q8   -> PASS (0 failures)
    Q12  -> PASS (0 failures)
    Q13  -> PASS (0 failures)
    Q16  -> PASS (0 failures)

...on a bundle with no command entries, no tools and no rules at all.

qa.py already knows this is wrong; it just never carried the knowledge across.
Q9 guards its own empty case with the reasoning written out in a comment — *"A
release with no CAT I rules at all means the severity parse dropped them
silently, which would make this gate pass by having nothing to check"* — and Q11
guards `not embedded`. That argument is not about CAT I rules. It is about every
one of these loops.

The bundle below is deliberately well-formed in every OTHER respect: real
provenance on every dataset, `_meta` counts that agree with the empty lists,
a generator Q15 re-runs, a category list. Nothing but the emptiness is wrong, so
nothing but the emptiness can be the reason a gate fails. Al's own fixture
tripped Q3's rules/CCI provenance sub-checks for an unrelated reason; this one
does not, which isolates the command-entries loop he named.

The control runs first: the SAME gates, on a populated bundle, must still pass —
a guard that fires on real content is worse than the hole it closes.
"""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

SOURCE = {
    "title": "Red Hat Enterprise Linux 9 STIG",
    "url_or_man": "https://public.cyber.mil/stigs/",
    "version": "V2R9",
    "retrieved_on": "2026-09-17",
    "license_class": "verbatim-ok",
}


def empty_bundle():
    """Structurally perfect, and completely empty."""
    return {
        "commands": {"_meta": {"entry_count": 0}, "entries": [], "categories": ["service control"]},
        "tools": {"_meta": {"tool_count": 0}, "tools": []},
        "rules": {v: {"_meta": {"source": dict(SOURCE), "rule_count": 0, "source_rule_count": 0,
                                "generator": "extract/parse_xccdf.py", "version": "V1R1",
                                "cat_counts": {"I": 0, "II": 0, "III": 0}},
                      "rules": []} for v in qa.VERSIONS},
        "flags": {v: {"_meta": {"source": dict(SOURCE),
                                "status": "empty pending CR-T-11/12"},
                      "clis": {}} for v in qa.VERSIONS},
        "cci_nist": {"_meta": {"source": dict(SOURCE), "entry_count": 0,
                               "generator": "extract/parse_xccdf.py"},
                     "cci": {}},
        "dangerous": {"source": dict(SOURCE), "patterns": []},
        "expected_output": {"captures": {}},
    }


def empty_ctx():
    return {
        "data": empty_bundle(),
        "source_rules": {v: ({}, 0) for v in qa.VERSIONS},
        "pin_failures": [],
        "pin_details": [],
    }


# The gates that loop over a per-item set, with the set each one would find empty.
EMPTY_SET_GATES = [
    ("Q3", qa.gate_q3, "command entries and tools whose provenance it re-checks"),
    ("Q4", qa.gate_q4, "command entries whose verify/undo/blast promise it enforces"),
    ("Q8", qa.gate_q8, "embedded records whose counts it reconciles with _meta"),
    ("Q12", qa.gate_q12, "entries and tools whose four-version completeness it proves"),
    ("Q13", qa.gate_q13, "entries whose stig_id/rule_id/tool/category links it resolves"),
    ("Q16", qa.gate_q16, "entries whose expected_output it backs with a capture record"),
]


class TheGatesOnTheRealBundle(unittest.TestCase):
    """Control first: a guard that fires on real content is worse than the hole."""

    @classmethod
    def setUpClass(cls):
        cls.ctx = qa.build_ctx_if_current()
        cls.artifact = qa.find_artifact() if cls.ctx else None
        if cls.ctx:
            qa.load_sources(cls.ctx)

    def test_every_guarded_gate_still_passes_on_the_shipped_content(self):
        if not self.artifact:
            self.skipTest("artifact is missing or stale — run python3 build.py first")
        for gid, fn, _what in EMPTY_SET_GATES:
            with self.subTest(gate=gid):
                out = fn(self.ctx)
                failures = out[0]
                self.assertEqual([], failures,
                                 "%s fails on the real content bundle:\n  %s"
                                 % (gid, "\n  ".join(failures)))


class AnEmptyBundleFailsEveryGate(unittest.TestCase):

    def test_the_bundle_is_empty_and_otherwise_well_formed(self):
        """If the fixture were malformed, every assertion below would be worthless."""
        data = empty_bundle()
        self.assertEqual([], data["commands"]["entries"])
        self.assertEqual([], data["tools"]["tools"])
        for v in qa.VERSIONS:
            self.assertEqual([], data["rules"][v]["rules"])
            self.assertEqual(0, data["rules"][v]["_meta"]["rule_count"])
            for field in ("title", "url_or_man", "version", "retrieved_on", "license_class"):
                self.assertTrue(data["rules"][v]["_meta"]["source"].get(field))

    def test_each_gate_fails_on_it(self):
        for gid, fn, what in EMPTY_SET_GATES:
            with self.subTest(gate=gid):
                out = fn(empty_ctx())
                failures = out[0]
                self.assertTrue(failures,
                                "%s reported PASS on a bundle with no %s — a gate that records a "
                                "failure only when it finds something wrong WITH an item passes by "
                                "having nothing to check (AL-GATE3-004)" % (gid, what))

    def test_the_failure_says_what_was_empty(self):
        """A FAIL nobody can triage is only half a gate."""
        for gid, fn, _what in EMPTY_SET_GATES:
            with self.subTest(gate=gid):
                failures = fn(empty_ctx())[0]
                text = " ".join(failures).lower()
                self.assertTrue(any(word in text for word in ("zero", "empty", "no ")),
                                "%s failed without naming the empty set: %s" % (gid, failures))

    def test_q9_and_q11_already_guarded_their_own(self):
        """The pattern this finding asks the others to copy, kept under test."""
        self.assertTrue(qa.gate_q9(empty_ctx())[0], "Q9's zero-CAT-I guard stopped working")
        self.assertTrue(qa.gate_q11(empty_ctx())[0], "Q11's empty-map guard stopped working")

    def test_q7_fails_on_a_script_with_no_storage_at_all(self):
        """The same shape in the render/storage half of the file."""
        self.assertTrue(qa.storage_guard_failures("function f(){ return 1; }")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
