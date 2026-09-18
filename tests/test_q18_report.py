#!/usr/bin/env python3
"""test_q18_report.py — Q18 must FAIL on a malformed harness report, not crash (AL-GATE3-006).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_q18_report.py

Al Kowalski's Gate 3 review, AL-GATE3-006 (LOW). gate_q18 reads the harness's
failure list defensively — `rep.get("failures", [])` — and then reads its
success detail with `rep["checks"]`, `rep["field_types"]` and six more, with no
guard at all. A harness that exits 0 with syntactically valid JSON missing those
keys therefore raises an uncaught KeyError in the middle of qa.py, with no
try/except anywhere in main().

    # subprocess.run monkeypatched to return rc=0, stdout=b"{}"
    qa.gate_q18(ctx)   # raises KeyError('checks')

This is NOT a silent pass. Python exits non-zero on an uncaught exception, so CI
still fails and the merge is still blocked. The problem is triage. A stack trace
looks identical whether the harness is broken or whether it found real hostile
input failures, and the only signal an operator gets is whichever gates happened
to print before the crash. Q18 is the gate whose own docstring calls it "the
only thing between a form field and a command a human runs as root"; its failure
mode should be as legible as every other gate's.

Four ways a report arrives malformed, all of them boring and all of them real: a
partial write, a harness that dies after opening its JSON, a field renamed in
hostile_harness.js and not mirrored here, and a future --json shape change. None
of them is an attack. All of them should read as one FAIL line naming the
reason.
"""

import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

GOOD = {
    "checks": 63536, "field_types": 12, "vectors": 34, "versions": 4,
    "rejected": 60000, "quoted_safe": 3536, "positive_controls": 144,
    "invariants": 9, "assembler_bytes": 18000, "failures": [],
    "half_formed_checks": 76, "rich_rule_oracles": 12,
    # CR-T-31: a COMPLETE report now includes the pipeline counts, because Q18's
    # statement covers pipeline assembly. A stub missing them is a drifted
    # report, which is exactly what the tests below are about.
    "pipeline_checks": 17092, "pipeline_oracles": 577, "pipeline_negative_controls": 11,
    "pipeline_operator_seam_checks": 332, "pipeline_interpreter_class_checks": 100,
    "pipeline_stage_naming_checks": 36, "one_stage_invariants": 96,
    # PL4 on the screen: the panel shows the rating the assembler made, and an
    # unclassified redirect target is `unrated` rather than green. Part of the
    # report contract for the same reason as the counts above -- Q18's PASS text
    # states the claim, so the gate has to fail closed when nothing checked it.
    "pipeline_target_rating_checks": 44,
    # MCR-SEC-010 (CR-T-25). The generated-file oracles are part of the report
    # contract now: Q18 reads both counts and fails on a zero, because a YAML
    # quoter whose oracle silently stopped running is the dead-escaper finding
    # with the call site filled in and the proof still missing.
    "yaml_oracle_checks": 316, "ini_oracle_checks": 60,
}


class _StubProc(object):
    """What subprocess.run returns, as far as gate_q18 is concerned."""

    def __init__(self, stdout, returncode=0, stderr=b""):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class TheReportConsumerOnAGoodReport(unittest.TestCase):
    """Control first."""

    def test_a_complete_report_passes_and_says_what_it_proved(self):
        failures, details = qa.harness_report_failures(dict(GOOD), 0)
        self.assertEqual([], failures)
        self.assertTrue(details, "a clean harness run reported nothing about what it proved")
        self.assertIn("63536", " ".join(details))

    def test_a_named_hostile_failure_is_reported_as_one(self):
        rep = dict(GOOD, failures=["path/../../etc/passwd escaped its quoting"])
        failures, _ = qa.harness_report_failures(rep, 1)
        self.assertEqual(1, len(failures))
        self.assertIn("etc/passwd", failures[0])


class AMalformedReportIsACleanFail(unittest.TestCase):

    def test_an_empty_object(self):
        """Al's exact reproduction: rc=0, body `{}`."""
        failures, _ = qa.harness_report_failures({}, 0)
        self.assertTrue(failures, "an empty harness report was rated a PASS")
        self.assertIn("checks", " ".join(failures), "the FAIL line does not name what is missing")

    def test_a_truncated_object(self):
        """A partial write: the first few keys arrived, the rest did not."""
        rep = {"checks": 63536, "field_types": 12}
        failures, _ = qa.harness_report_failures(rep, 0)
        self.assertTrue(failures)
        for expected in ("vectors", "rejected", "assembler_bytes"):
            self.assertIn(expected, " ".join(failures))

    def test_a_renamed_field(self):
        """hostile_harness.js changes its report shape and qa.py is not updated."""
        rep = dict(GOOD)
        rep["check_count"] = rep.pop("checks")
        failures, _ = qa.harness_report_failures(rep, 0)
        self.assertTrue(failures)
        self.assertIn("checks", " ".join(failures))

    def test_a_field_of_the_wrong_type(self):
        for value in ("63536", None, [], {}, True):
            with self.subTest(value=repr(value)):
                failures, _ = qa.harness_report_failures(dict(GOOD, checks=value), 0)
                self.assertTrue(failures, "checks=%r was accepted as a count" % value)

    def test_a_report_that_is_not_an_object(self):
        for body in ([], "ok", 3, None):
            with self.subTest(body=repr(body)):
                failures, _ = qa.harness_report_failures(body, 0)
                self.assertTrue(failures, "a %s report body was accepted" % type(body).__name__)

    def test_zero_checks(self):
        """The AL-GATE3-004 shape again: a harness that ran nothing proves nothing."""
        failures, _ = qa.harness_report_failures(dict(GOOD, checks=0), 0)
        self.assertTrue(failures, "a harness that reported zero checks was rated a PASS")

    def test_zero_file_oracle_checks(self):
        """MCR-SEC-010's own empty-set shape, and the reason this gate reads the
        counts at all.

        The original finding was a YAML quoter with no call site: the function
        was right, nothing called it, and Q18 passed on a domain that did not
        exist. CR-T-25 gave it a call site, so the same failure now looks
        different -- the quoter and the sink are both in the build and the ORACLE
        is what stopped running. A report saying zero files were parsed must fail
        here, or MCR-SEC-010 comes back one step further along and green.

        Both counts, separately: the INI kind has no quoter at all by design, so
        its parser is the entire defence and a zero there is worth more alarm,
        not less.
        """
        for key in ("yaml_oracle_checks", "ini_oracle_checks"):
            with self.subTest(key=key):
                failures, _ = qa.harness_report_failures(dict(GOOD, **{key: 0}), 0)
                self.assertTrue(failures,
                                "a harness that parsed ZERO generated files still passed Q18 "
                                "(%s=0)" % key)

    def test_a_nonzero_exit_with_no_named_failure(self):
        failures, _ = qa.harness_report_failures(dict(GOOD), 3, "Segmentation fault")
        self.assertTrue(failures)
        self.assertIn("3", " ".join(failures))

    def test_no_failure_line_is_a_traceback(self):
        """Whatever goes wrong, the operator gets a sentence, not a stack."""
        for rep in ({}, {"checks": 1}, [], "x", None, dict(GOOD, checks="x")):
            with self.subTest(rep=repr(rep)[:24]):
                failures, _ = qa.harness_report_failures(rep, 0)
                self.assertTrue(all("Traceback" not in line for line in failures))
                self.assertTrue(all(len(line) > 20 for line in failures),
                                "a one-word FAIL line is not triage")


class TheGateItselfDoesNotCrash(unittest.TestCase):
    """End to end, the way Al reproduced it: a harness that exits 0 printing `{}`."""

    def setUp(self):
        if not qa.find_artifact():
            self.skipTest("no dist/ artifact — run python3 build.py first")
        self.ctx = qa.build_ctx()
        self.orig = qa.subprocess.run

    def tearDown(self):
        qa.subprocess.run = self.orig

    def _with_harness_output(self, stdout, returncode=0):
        qa.subprocess.run = lambda *a, **k: _StubProc(stdout, returncode)
        return qa.gate_q18(self.ctx)

    def test_an_empty_json_body_is_a_named_fail(self):
        failures, _ = self._with_harness_output(b"{}")
        self.assertTrue(failures, "Q18 rated an empty harness report a PASS")

    def test_a_truncated_json_body_is_a_named_fail(self):
        failures, _ = self._with_harness_output(b'{"checks": 100, "field_ty')
        self.assertTrue(failures)
        self.assertIn("no JSON report", " ".join(failures))

    def test_a_json_array_body_is_a_named_fail(self):
        failures, _ = self._with_harness_output(b"[]")
        self.assertTrue(failures)

    def test_a_good_stub_report_passes_the_gate(self):
        """Control: the consumer must still accept the shape the harness emits."""
        failures, _ = self._with_harness_output(json.dumps(GOOD).encode("utf-8"))
        self.assertEqual([], failures, "Q18 rejected a well-formed harness report: %s" % failures)

    def test_the_real_harness_still_passes(self):
        failures, details = qa.gate_q18(self.ctx)
        self.assertEqual([], failures, "Q18 fails against the real harness:\n  "
                                       + "\n  ".join(failures))
        self.assertTrue(details)


if __name__ == "__main__":
    unittest.main(verbosity=2)
