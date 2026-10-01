#!/usr/bin/env python3
"""test_content_family_liveness.py — AL-GATE3-011. Every CONTENT family that
build.py embeds in the data island must be referenced by at least one live
code path in the shipped app script, not merely counted or provenance-checked.

Before this fix, content/glossary.json (9.5 KB) was loaded by build.py,
embedded in the island, and bound to DATASETS.GLOSSARY at template.html's
data-island loader -- and read by nothing: no Glossary kind in the search
index, no rail, no panel, no renderer. `grep -n GLOSSARY template.html`
returned exactly one line, its own assignment. Q8 (embedded record counts)
and Q3 (provenance) both had a clean answer for glossary.json; neither one
asks whether anything RENDERS a family, so nothing caught it.

This test proves the new check (qa.content_family_liveness_failures(), wired
into gate_q8) actually catches that shape of defect on the REAL shipped
bundle, fails specifically FOR GLOSSARY while GLOSSARY is still embedded, and
goes clean once it is dropped from build.py's CONTENT map -- without the
check developing a new blind spot for EXPECTED, whose data is not dead the
same way (build.py joins captures onto RULES before the island is built).
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402


def _real_ctx():
    ctx = qa.build_ctx_if_current()
    if not ctx:
        return None
    qa.load_sources(ctx)
    return ctx


class ContentFamilyLivenessIsChecked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = _real_ctx()

    def test_a_bound_but_unread_family_is_caught_in_general(self):
        """Direct proof of the detection logic against a synthetic script that
        has exactly the AL-GATE3-011 shape -- a family bound in the DATASETS
        object and never touched again -- WITHOUT depending on glossary still
        being a tracked family (it no longer is: that is the fix). Every
        currently-tracked token is present in the fake DATASETS literal, so
        none of them is missing-and-therefore-flagged by coincidence; only
        DANGEROUS is left unused elsewhere, the way GLOSSARY used to be."""
        fake_script = (
            'var DATASETS={COMMANDS:DATA.commands,TOOLS:DATA.tools,'
            'DANGEROUS:DATA.dangerous,RULES:DATA.rules,FLAGS:DATA.flags,'
            'CCI_NIST:DATA.cci_nist,EXPECTED:DATA.expected_output};\n'
            'function f(){return DATASETS.COMMANDS.entries.concat('
            'DATASETS.TOOLS.tools,DATASETS.RULES,DATASETS.FLAGS,'
            'DATASETS.CCI_NIST);}\n'
        )
        failures = qa.content_family_liveness_failures(fake_script)
        self.assertTrue(
            any("DANGEROUS" in x for x in failures),
            "content_family_liveness_failures() did not flag a family bound "
            "and never touched again -- the exact AL-GATE3-011 shape: %r" % failures)
        for token in ("COMMANDS", "TOOLS", "RULES", "FLAGS", "CCI_NIST"):
            with self.subTest(token=token):
                self.assertFalse(any(x.startswith(token + " ") for x in failures), failures)
        # EXPECTED is exempt (joined into RULES elsewhere) even though it is
        # unused here too, same as on the real bundle.
        self.assertFalse(any(x.startswith("EXPECTED ") for x in failures), failures)

    def test_expected_output_is_not_a_false_positive(self):
        """EXPECTED is bound once and never referenced again either, but its
        content reaches the UI through RULES (build.py joins captures onto
        each rule record before the island is serialized) -- it must not be
        flagged the same way GLOSSARY is."""
        fake_script = (
            'var DATASETS={RULES:DATA.rules,EXPECTED:DATA.expected_output};\n'
            'function f(){return DATASETS.RULES;}\n'
        )
        failures = qa.content_family_liveness_failures(fake_script)
        self.assertFalse(any("EXPECTED" in x for x in failures), failures)

    def test_real_shipped_app_script_has_no_orphaned_family(self):
        """On the real bundle, after glossary is dropped from build.py's
        CONTENT map, this must be clean: gate_q8 has one CONTENT family per
        DATASETS key, and every one of them is either live or documented as
        joined elsewhere (EXPECTED)."""
        if not self.ctx:
            self.skipTest("artifact is missing or stale — run python3 build.py first")
        failures = qa.content_family_liveness_failures(self.ctx["app_script"])
        self.assertEqual([], failures, failures)
        # And GLOSSARY must actually be gone from the family list, not merely
        # passing by coincidence.
        self.assertNotIn("glossary", qa.CONTENT_FAMILY_TOKENS.values())


if __name__ == "__main__":
    unittest.main()
