#!/usr/bin/env python3
"""test_q20_rhel7_coverage.py — AL-GATE3-010. Q20's RHEL 7 baseline rows must
actually be evaluated, not just carried in content-src/flag_coverage_baseline.json.

Before this fix, qa.py's RAW_DIR_FOR was {"8": "rhel8", "10": "rhel10"} -- RHEL 7
was absent, so the six coverage["7"] rows (chage, journalctl, systemctl, useradd,
usermod, yum) were read by nothing. Extending RAW_DIR_FOR alone would still have
measured nothing: _long_options_in_raw() filtered committed raw captures to
".man.txt" only, and every RHEL 7 dump under content-src/raw/rhel7/ is ".help.txt"
(UBI7 has no man-db -- CR-T-12). So raw_long was None for every RHEL 7 tool and
the loop `continue`d silently.

This test proves both halves are fixed: RAW_DIR_FOR reaches "7", and
_long_options_in_raw() reads .help.txt where no .man.txt exists, so Q20's own
diagnostics actually contain "RHEL 7 / <tool>" rows for all six tools the
baseline carries -- using the REAL shipped ctx and REAL committed raw captures,
not a synthetic fixture, because the whole defect was about files that already
exist not being looked at.

No baseline widening: content-src/flag_coverage_baseline.json's coverage["7"]
accepted_missing counts were already pre-measured (per its own _rhel7_note) and
are asserted here to still hold -- if a real run produces MORE missing options
than the baseline accepts, gate_q20 itself fails and this test's own control
assertion (zero Q20 failures) catches it, which is the correct way for a
baseline change to surface: recorded under the existing owner/date (Caleb
Stone, retires 2026-09-25), not invented here.
"""
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

RHEL7_TOOLS = ("chage", "journalctl", "systemctl", "useradd", "usermod", "yum")


def _real_ctx():
    ctx = qa.build_ctx_if_current()
    if not ctx:
        return None
    qa.load_sources(ctx)
    return ctx


class Q20EvaluatesRhel7Rows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = _real_ctx()
        with open(os.path.join(REPO, "content-src", "flag_coverage_baseline.json"),
                  encoding="utf-8") as fh:
            cls.baseline = json.load(fh)

    def test_baseline_still_carries_all_six_rhel7_rows(self):
        """Sanity on the fixture this test relies on -- not the fix itself."""
        rows = (self.baseline.get("coverage") or {}).get("7") or {}
        self.assertEqual(sorted(RHEL7_TOOLS), sorted(rows.keys()))

    def test_raw_help_txt_is_readable_for_every_rhel7_tool(self):
        """The raw captures exist and are .help.txt, not .man.txt (CR-T-12)."""
        raw_dir = os.path.join(REPO, "content-src", "raw", "rhel7")
        for cli in RHEL7_TOOLS:
            with self.subTest(cli=cli):
                path = os.path.join(raw_dir, cli + ".help.txt")
                self.assertTrue(os.path.exists(path), "%s missing" % path)

    def test_rhel7_rows_are_in_q20s_evaluated_set(self):
        if not self.ctx:
            self.skipTest("no dist/ artifact — run python3 build.py first")
        f, d, _p = qa.gate_q20(self.ctx)
        evaluated = set()
        for line in d + f:
            if line.startswith("RHEL 7 / "):
                evaluated.add(line.split("RHEL 7 / ", 1)[1].split(":", 1)[0])
        missing = sorted(set(RHEL7_TOOLS) - evaluated)
        self.assertEqual(
            [], missing,
            "Q20 never evaluated these RHEL 7 tools -- the baseline rows are "
            "unreachable (AL-GATE3-010): %r\nfull diagnostics: %r\nfull failures: %r"
            % (missing, d, f))

    def test_q20_still_passes_the_real_bundle(self):
        """No baseline widening: the pre-recorded accepted_missing counts must
        still cover the real measurement, so Q20 reports zero failures."""
        if not self.ctx:
            self.skipTest("no dist/ artifact — run python3 build.py first")
        f, _d, _p = qa.gate_q20(self.ctx)
        self.assertEqual([], f, f)


if __name__ == "__main__":
    unittest.main()
