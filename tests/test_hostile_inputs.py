#!/usr/bin/env python3
"""test_hostile_inputs.py — CR-T-16. Runs the hostile-input harness over template.html.

This is the same gate qa.py Q18 runs against the BUILT artifact; this copy runs
it against the source template, so a broken assembler is caught by
`python3 -m unittest discover -s tests` before a build is even attempted.

Node is REQUIRED for this test, and its absence is a FAILURE, not a skip. The
assembler is JavaScript; the only honest way to test it is to run it. A Python
re-implementation of the quoting would be a second assembler to keep in sync,
and the one that shipped would be the one nobody tested. CI installs Node for
exactly this reason (.forgejo/workflows/ci.yml, actions/setup-node).
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(REPO, "tests", "hostile_harness.js")
FIXTURE = os.path.join(REPO, "tests", "fixtures", "hostile-inputs.json")


def run_harness(target):
    node = shutil.which("node")
    if not node:
        raise AssertionError(
            "node is not on PATH. The command assembler is JavaScript and this gate runs it; "
            "install Node (CI uses actions/setup-node@v4) rather than skipping the one test "
            "that stands between a form field and a root shell.")
    proc = subprocess.run([node, HARNESS, target, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        report = json.loads(out)
    except ValueError:
        raise AssertionError("harness produced no JSON report.\nstdout:\n%s\nstderr:\n%s" % (out, err))
    return proc.returncode, report


class HostileInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.report = run_harness(os.path.join(REPO, "template.html"))
        with open(FIXTURE, encoding="utf-8") as f:
            cls.fixture = json.load(f)

    def test_no_vector_escapes_its_quoting(self):
        self.assertEqual(self.report["failures"], [],
                         "hostile vectors were neither rejected nor safely quoted")
        self.assertEqual(self.rc, 0)

    def test_every_field_type_and_vector_ran(self):
        self.assertEqual(self.report["field_types"], len(self.fixture["field_types"]))
        self.assertEqual(self.report["vectors"], len(self.fixture["vectors"]))
        self.assertEqual(self.report["versions"], 4)
        types, vectors = self.report["field_types"], self.report["vectors"]
        # Two rich-rule shapes: the port/protocol rule (5 sub-fields) and the
        # MCR-SEC-001 reproduction's service rule (4). Every sub-field of both
        # takes every field type in turn (MCR-SEC-005a), with a benign value and
        # with every hostile vector.
        rich_fields = 5 + 4
        expected = (types * vectors * 4 * 3              # every type x vector x release x shape
                    + rich_fields * vectors * 4          # native sub-field types, hostile values
                    + rich_fields * types * 4            # every type substituted into every slot
                    + rich_fields * types * vectors * 4  # substituted type AND hostile value
                    + 2 * 4                               # benign control per rich-rule shape
                    # CR-T-17..25: every field of every REAL generator spec in
                    # content/commands.json, fuzzed in its own template rather
                    # than a synthetic analog (self.report["content_spec_checks"]
                    # is itself computed from the entries and their declared
                    # fields/versions, not a constant, so a new generator or
                    # field changes this total on its own).
                    + self.report["content_spec_checks"]
                    # CR-T-31: the PIPELINE sweeps fold into the same headline
                    # count, so "N checks" on the console is the whole of what
                    # the harness proved and not the command half of it. Read
                    # out of the report for the same reason content_spec_checks
                    # is: it is derived from the fixture and the operator table,
                    # not a constant somebody has to remember to bump.
                    + self.report["pipeline_checks"])
        self.assertEqual(self.report["checks"], expected,
                         "the harness did not run every field type x vector x release x shape")
        # the pipeline half, stated in its own terms: every vector into every
        # field of every stage of three multi-stage shapes, plus the redirect
        # target, plus the operator seam and the ten operator controls.
        expected_pipeline = (types * vectors * 4 * 3          # 3 shapes x every type/vector/release
                             + vectors * 4                    # every vector into a redirect target
                             + self.report["pipeline_operator_seam_checks"]
                             + self.report["pipeline_operator_controls"])
        self.assertEqual(self.report["pipeline_checks"], expected_pipeline,
                         "the pipeline sweep did not drive every vector into every field of every "
                         "stage")
        self.assertGreater(self.report["pipeline_negative_controls"], 0,
                           "the pipeline oracle has no negative control — an oracle nobody has "
                           "watched fail proves nothing")
        self.assertGreater(self.report["one_stage_invariants"], 0,
                           "the one-stage invariant (a pipeline of one stage IS assembleCommand(), "
                           "byte for byte) was never asserted")
        self.assertGreater(self.report["content_spec_checks"], 0,
                           "no real generator spec was fuzzed — CR-T-17's content-spec sweep is dead")
        self.assertGreater(self.report["content_spec_entries"], 0,
                           "content/commands.json has no generator (template) entries to fuzz")

    def test_rich_rule_slots_refuse_every_type_that_is_not_allow_listed(self):
        """MCR-SEC-001/005: the sweep richRuleSpec's signature was written for."""
        self.assertGreater(self.report["rich_rule_slot_types_refused"], 0,
                           "no (rich-rule slot, field type) pair was refused — the hostile-type "
                           "substitution is dead again")
        self.assertGreater(self.report["rich_rule_slot_types_allowed"], 0,
                           "no field type composed a rich rule at all — the slot allow-list is so "
                           "narrow the feature cannot work, which is not a pass")

    def test_absent_optional_fields_are_covered_on_every_template_shape(self):
        """MCR-SEC-002: never-half-formed is a property of the template, not a field."""
        self.assertGreaterEqual(
            self.report["half_formed_checks"], 13 * 4,
            "the absent-optional sweep does not cover every template shape on every release")

    def test_the_rich_rule_oracle_ran(self):
        """Shell-token containment is not rich-rule containment (MCR-SEC-005b)."""
        self.assertGreater(self.report["rich_rule_oracles"], 0,
                           "no composed rich rule was parsed and compared to the operator's intent")

    def test_outcomes_are_accounted_for(self):
        self.assertEqual(self.report["rejected"] + self.report["quoted_safe"],
                         self.report["checks"],
                         "a check ended in neither state — the harness lost track of an outcome")

    def test_the_gate_is_not_passing_by_rejecting_everything(self):
        """Positive controls: the benign value of every field type still works."""
        self.assertGreater(self.report["positive_controls"], 0)
        self.assertGreater(self.report["quoted_safe"], 0,
                           "no vector was ever accepted-and-quoted — the free-text path is untested")

    def test_fixture_covers_the_threat_model_vector_classes(self):
        """threat-model-v1 §12 item 1 names the minimum vector set by class."""
        classes = set(v["class"] for v in self.fixture["vectors"])
        for required in ("command substitution", "statement separator", "newline injection",
                         "option injection", "unicode look-alike", "path traversal",
                         "length", "quote breaking", "NUL", "invisible character"):
            self.assertIn(required, classes, "fixture is missing the %s vector class" % required)

    def test_the_invisible_character_class_covers_the_line_separators(self):
        """MCR-SEC-009: U+2028/U+2029/U+2065 were the gap in INVISIBLE_RE."""
        values = "".join(v["value"] for v in self.fixture["vectors"]
                         if v["class"] == "invisible character")
        for cp in (0x2028, 0x2029, 0x2065):
            self.assertIn(chr(cp), values,
                          "no fixture vector carries U+%04X" % cp)

    def test_fixture_declares_its_provenance(self):
        src = self.fixture["_meta"]["source"]
        for key in ("title", "url_or_man", "version", "retrieved_on", "license_class"):
            self.assertTrue(src.get(key), "hostile-inputs fixture source.%s missing" % key)


if __name__ == "__main__":
    sys.exit(unittest.main())
