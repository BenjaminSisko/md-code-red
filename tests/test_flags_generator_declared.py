#!/usr/bin/env python3
"""test_flags_generator_declared.py — AL-GATE3-009 part 2. Q15/Q8's generator
declaration check must cover the FLAGS datasets, not just RULES/CCI.

Before this fix, content/flags_rhel9.json declared _meta.generator:
"extract/extract_rhel_flags.py" -- a script that has never existed in this
repository -- and every gate passed, because Q15's `declared` set (and Q8's
per-dataset check) built itself only from data["rules"][v] and
data["cci_nist"]. A FLAGS dataset's declared generator was compared against
nothing (AL-GATE3-009).

This test proves the gap is closed the way AL-GATE3-009 asked: plant a bogus
generator name on a FLAGS dataset (RHEL 9's, in memory only) and confirm
gate_q15 (the generated-file integrity gate) and gate_q8 (the embedded-count
reconciliation gate) both go red for it -- using the REAL shipped ctx (real
RULES/CCI/other FLAGS content, so nothing else in the bundle can be the reason
either gate fails).
"""
import copy
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

BOGUS_GENERATOR = "extract/extract_rhel_flags.py"  # AL-GATE3-009: never existed


def _real_ctx():
    ctx = qa.build_ctx_if_current()
    if not ctx:
        return None
    qa.load_sources(ctx)
    return ctx


class FlagsDatasetGeneratorIsChecked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = _real_ctx()

    def test_bogus_flags_generator_fails_q15(self):
        if not self.ctx:
            self.skipTest("no dist/ artifact — run python3 build.py first")
        ctx = copy.deepcopy(self.ctx)
        ctx["data"]["flags"]["9"].setdefault("_meta", {})["generator"] = BOGUS_GENERATOR
        f, _d = qa.gate_q15(ctx)
        self.assertTrue(
            any("flags_rhel9" in line and "extract_rhel_flags" in line for line in f),
            "gate_q15 did not flag a FLAGS dataset declaring a generator that does not "
            "exist and is never re-run (AL-GATE3-009):\n  %s" % "\n  ".join(f))

    def test_bogus_flags_generator_fails_q8(self):
        if not self.ctx:
            self.skipTest("no dist/ artifact — run python3 build.py first")
        ctx = copy.deepcopy(self.ctx)
        ctx["data"]["flags"]["9"].setdefault("_meta", {})["generator"] = BOGUS_GENERATOR
        f, _d = qa.gate_q8(ctx)
        self.assertTrue(
            any("flags_rhel9" in line and "extract_rhel_flags" in line for line in f),
            "gate_q8 did not flag a FLAGS dataset whose declared generator is not an "
            "extractor Q15 re-runs (AL-GATE3-009):\n  %s" % "\n  ".join(f))

    def test_the_real_shipped_flags_generators_all_pass(self):
        """Control: on the REAL bundle (flags_rhel9.json corrected to name the
        real extractor), neither gate may fire on any flags_rhel* dataset."""
        if not self.ctx:
            self.skipTest("no dist/ artifact — run python3 build.py first")
        f_q15, _ = qa.gate_q15(self.ctx)
        f_q8, _ = qa.gate_q8(self.ctx)
        flags_related_q15 = [x for x in f_q15 if x.startswith("flags_rhel")]
        flags_related_q8 = [x for x in f_q8 if x.startswith("flags_rhel")]
        self.assertEqual([], flags_related_q15, flags_related_q15)
        self.assertEqual([], flags_related_q8, flags_related_q8)


if __name__ == "__main__":
    unittest.main()
