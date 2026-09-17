#!/usr/bin/env python3
"""test_schema.py — the ADR-001 §5 content schema, pinned by fixtures (CR-T-06).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_schema.py

Stdlib only, no third-party deps.

Three things are asserted, in this order:

  1. The REAL content/ in this repo is schema-clean. This is the control: a
     schema that has never been seen to pass on the shipping content proves
     nothing about the fixtures that follow.
  2. Every bundle under tests/fixtures/schema/valid/ produces zero errors.
  3. Every bundle under tests/fixtures/schema/invalid/ produces at least one
     error, AND that error is the one the fixture's own `_expect` names — a
     fixture that fails for the wrong reason is a false green.

The schema rules themselves are in extract/schema.py, which build.py imports
too, so this file and the build enforce one statement of the schema rather than
two that drift.
"""

import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "extract"))
sys.path.insert(0, REPO)

import schema  # noqa: E402
import build   # noqa: E402

FIXTURES = os.path.join(REPO, "tests", "fixtures", "schema")


def load_bundle(path):
    """Read a fixture and split its documentation keys off the bundle."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    case = data.pop("_case", None)
    expect = data.pop("_expect", None)
    return data, case, expect


def fixture_files(kind):
    d = os.path.join(FIXTURES, kind)
    return sorted(os.path.join(d, n) for n in os.listdir(d) if n.endswith(".json"))


class RealContentIsSchemaClean(unittest.TestCase):
    """Control. The content this repo actually ships must satisfy the schema."""

    def test_content_dir_validates(self):
        data = build.load_content()
        have = os.path.exists(build.CONTENT_SRC_SOURCES)
        source_ids = set()
        if have:
            with open(build.CONTENT_SRC_SOURCES, encoding="utf-8") as f:
                source_ids = set(json.load(f).get("sources", {}).keys())
        errs = schema.content_errors(data, source_ids=source_ids, have_sources_json=have)
        self.assertEqual([], errs, "content/ is not schema-clean:\n  " + "\n  ".join(errs))

    def test_every_entry_carries_all_four_rhel_keys(self):
        """Stated separately from the bundle check because it is the P0 promise."""
        data = build.load_content()
        for e in data["commands"]["entries"]:
            self.assertEqual(set(schema.VERSIONS), set(e["rhel_versions"].keys()),
                             "entry %s does not cover all four releases" % e["id"])

    def test_flag_explain_nulls_are_still_honest(self):
        """explain:null is legal only while no RHEL host has been read (ADR-001 §6.1).

        When CR-T-09..12 populate content/flags_rhel*.json, this assertion flips
        from documenting the gap to documenting that it closed, and the schema
        starts rejecting the nulls. Nothing here needs editing for that to happen.
        """
        data = build.load_content()
        ctx = schema.make_ctx(data)
        nulls = [(e["id"], fl.get("flag"))
                 for e in data["commands"]["entries"]
                 for fl in (e.get("flags") or []) if fl.get("explain") is None]
        if ctx["flags_datasets_empty"]:
            self.assertEqual([], schema.content_errors(data),
                             "flag explains are null and the dictionaries are empty — that is legal; "
                             "some other rule is failing")
        else:
            self.assertEqual([], nulls,
                             "the FLAGS dictionaries are populated, so these flags must now carry a "
                             "curated explain: %s" % nulls)


class ValidFixtures(unittest.TestCase):

    def test_valid_bundles_produce_no_errors(self):
        paths = fixture_files("valid")
        self.assertTrue(paths, "no valid fixtures found")
        for path in paths:
            with self.subTest(fixture=os.path.basename(path)):
                data, case, expect = load_bundle(path)
                self.assertIsNone(expect, "a valid fixture must not declare an _expect")
                self.assertTrue(case, "every fixture must say what it is in _case")
                errs = schema.content_errors(data)
                self.assertEqual([], errs,
                                 "%s is meant to be valid but produced:\n  %s"
                                 % (os.path.basename(path), "\n  ".join(errs)))


class InvalidFixtures(unittest.TestCase):

    def test_invalid_bundles_fail_for_the_stated_reason(self):
        paths = fixture_files("invalid")
        self.assertTrue(paths, "no invalid fixtures found")
        for path in paths:
            with self.subTest(fixture=os.path.basename(path)):
                data, case, expect = load_bundle(path)
                self.assertTrue(expect, "every invalid fixture must name the error it expects")
                errs = schema.content_errors(data)
                self.assertTrue(errs, "%s (%s) was accepted; it must not be" % (os.path.basename(path), case))
                self.assertTrue(any(expect in e for e in errs),
                                "%s failed for the wrong reason.\n  expected: %s\n  got:\n  %s"
                                % (os.path.basename(path), expect, "\n  ".join(errs)))

    def test_every_schema_rule_family_has_a_fixture(self):
        """A rule with no fixture has never been seen to fire."""
        covered = " ".join(os.path.basename(p) for p in fixture_files("invalid"))
        for family in ("rhel_key", "same_as", "unavailable", "provenance", "blast", "stig",
                       "verified", "flag", "duplicate", "rule_count", "cci", "tool", "promise"):
            self.assertIn(family, covered, "no invalid fixture covers the '%s' rule family" % family)


class SchemaModuleShape(unittest.TestCase):
    """The constants the rest of the toolchain reads off this module."""

    def test_enums(self):
        self.assertEqual(("7", "8", "9", "10"), schema.VERSIONS)
        self.assertEqual(("green", "yellow", "red"), schema.BLASTS)
        self.assertEqual(("verbatim-ok", "paraphrase-only"), schema.LICENSE_CLASSES)
        self.assertEqual(("title", "url_or_man", "version", "retrieved_on", "license_class"),
                         schema.PROVENANCE_FIELDS)

    def test_build_uses_this_module_and_not_a_copy(self):
        self.assertIs(build.VERSIONS, schema.VERSIONS)
        self.assertIs(build.BLASTS, schema.BLASTS)
        self.assertIs(build.LICENSE_CLASSES, schema.LICENSE_CLASSES)

    def test_a_malformed_bundle_returns_errors_rather_than_raising(self):
        for junk in ({}, {"commands": {}}, {"commands": {"entries": [{}]}}):
            self.assertIsInstance(schema.content_errors(junk), list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
