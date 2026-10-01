#!/usr/bin/env python3
"""test_provenance_fields.py — Q3 and schema.py must not drift (AL-GATE3-005).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_provenance_fields.py

Al Kowalski's Gate 3 review, AL-GATE3-005 (MEDIUM). Two copies of the same rule
live in this repo on purpose:

    qa.py      need = ("title", "url_or_man", "retrieved_on", "license_class")
    schema.py  PROVENANCE_FIELDS = ("title", "url_or_man", "version",
                                    "retrieved_on", "license_class")

The duplication is deliberate architecture, not an accident — Q10's docstring
says why in as many words: *"this file keeps its own independent XCCDF parse on
purpose: the accuracy gate is worth nothing if it re-uses the extractor's code
path"*. Q3 is meant to be that same independent, artifact-level re-check for
provenance.

What is not deliberate is that the independent copy is STRICTLY WEAKER than the
one it doubles against. `version` is missing from it, and schema.py's own
docstring says why that field is mandatory: *"a source that cannot say which
version of the document it came from cannot be re-checked."* Nothing ships
without it today, because build.py runs schema.content_errors() first — so this
is masked, not absent. Weaken build.py, re-validate an older dist/ with a newer
qa.py, or drift a `--check` path in a future refactor, and Q3 stops catching the
gap it exists to catch. It is the exact "two copies of a schema is one copy too
many... the drift is invisible until a bad entry ships" problem schema.py's
file-level docstring was written for (CR-T-06) — and it has already happened
once, between these two files.

The fix is not to delete a copy. It is to make the two mechanically incapable of
disagreeing about WHICH FIELDS ARE REQUIRED, while keeping the two independent
CHECKS. qa.py reads the tuple out of extract/schema.py as text, the same way it
already reads APP_VERSION out of build.py without importing it: a shared
constant, never a shared code path.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402
from extract import schema  # noqa: E402

FULL_SOURCE = {
    "title": "sshd_config(5)",
    "url_or_man": "man:sshd_config(5)",
    "version": "openssh-8.7p1-38.el9",
    "retrieved_on": "2026-09-17",
    "license_class": "paraphrase-only",
}


def bundle(entry_source):
    """One entry, one tool, everything else fully sourced and non-empty."""
    entry = {
        "id": "sshd-permitrootlogin",
        "tool": "sshd",
        "category": "service control",
        "source": entry_source,
        "verify": "sshd -T | grep permitrootlogin",
        "undo": "restore the previous value",
        "blast": "yellow",
        "rhel_versions": {v: {"command": "true"} for v in qa.VERSIONS},
    }
    return {
        "commands": {"_meta": {"entry_count": 1}, "entries": [entry],
                     "categories": ["service control"]},
        "tools": {"tools": [{"id": "sshd", "source": dict(FULL_SOURCE),
                             "availability": {v: True for v in qa.VERSIONS}}]},
        "rules": {v: {"_meta": {"source": dict(FULL_SOURCE)}, "rules": []} for v in qa.VERSIONS},
        "flags": {v: {"_meta": {"source": dict(FULL_SOURCE), "status": "pending"}, "clis": {}}
                  for v in qa.VERSIONS},
        "cci_nist": {"_meta": {"source": dict(FULL_SOURCE)}, "cci": {"CCI-000366": {}}},
        "dangerous": {"source": dict(FULL_SOURCE)},
        "expected_output": {"captures": {}},
    }


def q3(entry_source):
    return qa.gate_q3({"data": bundle(entry_source)})[0]


class TheTwoCopiesAgree(unittest.TestCase):

    def test_qa_requires_everything_schema_requires(self):
        """The superset assertion AL-GATE3-005 asks for."""
        need = set(qa.provenance_fields())
        self.assertTrue(need >= set(schema.PROVENANCE_FIELDS),
                        "qa.py's Q3 requires %s; extract/schema.py requires %s. The artifact-level "
                        "re-check is weaker than the build-time check it exists to double against, "
                        "so adding a field to one and not the other is invisible until a bad entry "
                        "ships (AL-GATE3-005)"
                        % (sorted(need), sorted(schema.PROVENANCE_FIELDS)))

    def test_qa_reads_the_tuple_rather_than_restating_it(self):
        """A shared CONSTANT, not a shared code path, and not a second copy.

        If qa.py went back to a local tuple that merely happens to match today,
        this test would still pass and the drift would be back. So: the fields
        have to come out of extract/schema.py's own text.
        """
        with open(os.path.join(REPO, "extract", "schema.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIsNotNone(re.search(r"^PROVENANCE_FIELDS\s*=", src, re.M),
                             "extract/schema.py no longer declares PROVENANCE_FIELDS at module "
                             "level in a form qa.py can read without importing it")
        self.assertEqual(tuple(schema.PROVENANCE_FIELDS), tuple(qa.provenance_fields()),
                         "qa.py's provenance fields are not the ones extract/schema.py declares")

    def test_an_unreadable_schema_is_a_failure_not_a_default(self):
        """No silent fallback: a gate that repairs its own input proves nothing."""
        self.assertRaises(Exception, qa.parse_provenance_fields, "# no tuple here\n")
        self.assertRaises(Exception, qa.parse_provenance_fields, "PROVENANCE_FIELDS = ()\n")


class TheGateCatchesAMissingVersion(unittest.TestCase):

    def test_a_source_with_no_version_fails_q3(self):
        missing = dict(FULL_SOURCE)
        del missing["version"]
        failures = q3(missing)
        self.assertTrue(failures, "a command entry whose source cannot say WHICH VERSION of the "
                                  "document it came from passed the artifact-level provenance "
                                  "gate; schema.py refuses it at build time (AL-GATE3-005)")
        self.assertIn("version", " ".join(failures))

    def test_schema_refuses_the_same_record(self):
        """The control: the two checks must disagree about nothing."""
        missing = dict(FULL_SOURCE)
        del missing["version"]
        self.assertTrue(schema.provenance_errors("command entry x", missing))

    def test_a_complete_source_passes_both(self):
        self.assertEqual([], q3(dict(FULL_SOURCE)))
        self.assertEqual([], schema.provenance_errors("command entry x", dict(FULL_SOURCE)))

    def test_every_required_field_is_actually_enforced(self):
        """One dropped field at a time, so no field is required only on paper."""
        for field in schema.PROVENANCE_FIELDS:
            with self.subTest(field=field):
                short = dict(FULL_SOURCE)
                del short[field]
                failures = q3(short)
                self.assertTrue(failures, "Q3 accepted a source with no %s" % field)
                self.assertIn(field, " ".join(failures))

    def test_the_shipped_bundle_still_passes(self):
        ctx = qa.build_ctx_if_current()
        if not ctx:
            self.skipTest("artifact is missing or stale — run python3 build.py first")
        self.assertEqual([], qa.gate_q3(ctx)[0],
                         "the real content bundle fails the strengthened provenance gate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
