#!/usr/bin/env python3
"""test_doc_spec_schema.py -- the build-time half of the generated-file sink.

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_doc_spec_schema.py

extract/schema.py's doc_errors() and template.html's composeDoc() are TWO
statements of the same rules -- the build refuses to ship what the runtime would
refuse to compose. Two statements of a rule is one more than one, and the copy
nobody exercises is the copy that drifts, which is the whole reason
extract/schema.py exists (its own docstring, CR-T-06). So:

  * the control comes FIRST. If a correct doc spec does not validate clean, a
    malformed one failing proves nothing -- the validator would just be broken.
  * every refusal is a planted defect, one per rule, each one a shape a content
    author could plausibly write.
  * the two tables that exist on both sides (the INI field-type allow-list and
    the key/lit/filename patterns) are compared against template.html directly,
    the same way test_schema.py compares FIELD_TYPES and RICHRULE_SLOT_TYPES.
    A rule the build enforces more loosely than the runtime is a build that
    ships a file the runtime then refuses to produce; a rule it enforces more
    tightly is a generator nobody can write. Either way they must be the same
    rule, and nothing but a comparison proves that.

MCR-SEC-010 is the reason this file exists at all: the YAML sink, its quoter and
its oracle ship together, and the validator that keeps the sink's INPUT honest is
part of the same promise.
"""
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from extract import schema  # noqa: E402

FIELDS = [
    {"name": "play_name", "type": "comment", "required": True},
    {"name": "hosts", "type": "hostname", "required": True},
    {"name": "user", "type": "username", "required": False},
    {"name": "forks", "type": "integer", "required": True},
]
BY_NAME = {f["name"]: f for f in FIELDS}


def yaml_doc(lines):
    return {"kind": "yaml", "filename": "site.yml", "lines": lines}


def ini_doc(lines):
    return {"kind": "ini", "filename": "ansible.cfg", "lines": lines}


def lines_doc(lines):
    return {"kind": "lines", "filename": "service.conf", "lines": lines}


GOOD_YAML = yaml_doc([
    {"indent": 0, "seq": True, "key": "name", "field": "play_name"},
    {"indent": 1, "key": "hosts", "field": "hosts"},
    {"indent": 1, "key": "become", "bool": True},
    {"indent": 1, "key": "vars", "requires": "user", "optional": True},
    {"indent": 2, "key": "remote_user", "field": "user", "optional": True},
    {"indent": 1, "key": "tasks"},
    {"indent": 2, "seq": True, "key": "name", "lit": "placeholder"},
])
GOOD_INI = ini_doc([
    {"section": "defaults"},
    {"key": "forks", "field": "forks"},
    {"key": "remote_user", "field": "user", "optional": True},
    {"section": "ssh_connection"},
    {"key": "pipelining", "bool": True},
])


class TheControlComesFirst(unittest.TestCase):
    def test_a_correct_yaml_doc_validates_clean(self):
        self.assertEqual(schema.doc_errors("spec", GOOD_YAML, BY_NAME), [])

    def test_a_correct_ini_doc_validates_clean(self):
        self.assertEqual(schema.doc_errors("spec", GOOD_INI, BY_NAME), [])

    def test_a_correct_token_lines_doc_validates_clean(self):
        doc = lines_doc([{"parts": [{"lit": "server"}, {"field": "hosts"},
                                             {"lit": "iburst"}]}])
        self.assertEqual(schema.doc_errors("spec", doc, BY_NAME), [])

    def test_all_shipped_generators_validate_clean(self):
        """The real content, not an analogue. A rule that only the fixtures obey
        is a rule the shipped generators are exempt from."""
        with open(os.path.join(REPO, "content", "commands.json"), encoding="utf-8") as fh:
            entries = json.load(fh)["entries"]
        with_docs = [e for e in entries if e.get("doc")]
        self.assertGreater(len(with_docs), 0,
                           "no shipped generator declares a doc, so the YAML sink is absent and "
                           "yamlQuote() is dead code again (MCR-SEC-010)")
        for e in with_docs:
            names = {f["name"]: f for f in e.get("fields") or []}
            self.assertEqual(schema.doc_errors(e["id"], e["doc"], names), [],
                             "shipped generator %s does not validate" % e["id"])


class EveryRuleRefusesItsOwnDefect(unittest.TestCase):
    def _one(self, doc, needle):
        errs = schema.doc_errors("spec", doc, BY_NAME)
        self.assertTrue(errs, "the planted defect validated clean")
        self.assertTrue(any(needle in e for e in errs),
                        "refused, but for the wrong reason: %s" % errs)

    def test_free_text_may_not_reach_an_ini_value(self):
        # The rule MCR-SEC-001 wrote for rich rules, applied to a grammar that
        # likewise has no escape sequence for its own delimiters.
        self._one(ini_doc([{"section": "defaults"}, {"key": "x", "field": "play_name"}]),
                  "no escape sequence")

    def test_an_ini_line_with_no_value_is_refused(self):
        self._one(ini_doc([{"section": "defaults"}, {"key": "x"}]), "bare INI key")

    def test_an_ini_doc_may_not_nest(self):
        self._one(ini_doc([{"section": "defaults"}, {"key": "x", "field": "forks", "indent": 1}]),
                  "no nesting")

    def test_a_droppable_line_must_declare_it(self):
        self._one(yaml_doc([{"indent": 0, "key": "remote_user", "field": "user"}]),
                  "optional:true")

    def test_a_droppable_block_header_may_not_orphan_its_block(self):
        # `vars:` vanishes with `user`; the line indented under it is gated on
        # nothing and stays, indented under whatever came before.
        self._one(yaml_doc([
            {"indent": 0, "key": "all"},
            {"indent": 1, "key": "vars", "requires": "user", "optional": True},
            {"indent": 2, "key": "hosts", "field": "hosts"},
        ]), "orphaned under the wrong parent")

    def test_a_key_that_is_not_a_plain_key_is_refused(self):
        self._one(yaml_doc([{"indent": 0, "key": "not: a key", "field": "hosts"}]), "usable key")

    def test_an_indent_outside_the_table_is_refused(self):
        self._one(yaml_doc([{"indent": 99, "key": "hosts", "field": "hosts"}]), "indent")

    def test_a_line_may_emit_only_one_value(self):
        self._one(yaml_doc([{"indent": 0, "key": "hosts", "field": "hosts", "bool": True}]),
                  "exactly one value")

    def test_a_field_the_spec_does_not_declare_is_refused(self):
        self._one(yaml_doc([{"indent": 0, "key": "hosts", "field": "nope"}]), "does not declare")

    def test_a_filename_that_is_not_a_plain_name_is_refused(self):
        self._one({"kind": "yaml", "filename": "../../etc/passwd",
                   "lines": [{"indent": 0, "key": "a", "field": "hosts"}]},
                  "plain file name")

    def test_an_unknown_kind_is_refused(self):
        self._one({"kind": "toml", "filename": "x.toml",
                   "lines": [{"indent": 0, "key": "a", "field": "hosts"}]}, "doc.kind")

    def test_an_ini_key_may_never_come_from_a_field(self):
        self._one(ini_doc([{"section": "defaults"}, {"keyField": "hosts", "field": "forks"}]),
                  "never operator text")

    def test_a_section_header_in_a_yaml_doc_is_refused(self):
        self._one(yaml_doc([{"section": "defaults"}]), "INI `section` in a yaml")

    def test_token_lines_refuse_free_text_fields(self):
        self._one(lines_doc([{"parts": [{"lit": "name"}, {"field": "play_name"}]}]),
                  "closed grammar")

    def test_token_lines_refuse_undeclared_fields(self):
        self._one(lines_doc([{"parts": [{"field": "nope"}]}]), "does not declare")

    def test_token_lines_refuse_shell_separator_literals(self):
        self._one(lines_doc([{"parts": [{"lit": ";"}]}]), "literal token")


class TheTwoStatementsAgree(unittest.TestCase):
    """Anything stated on both sides is compared, never assumed."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as fh:
            cls.tpl = fh.read()

    def test_ini_field_type_allow_list_matches_the_assembler(self):
        m = re.search(r"var INI_FIELD_TYPES=\[(.*?)\];", self.tpl, re.S)
        self.assertIsNotNone(m, "template.html has no INI_FIELD_TYPES")
        got = tuple(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
        self.assertEqual(sorted(got), sorted(schema.INI_FIELD_TYPES),
                         "extract/schema.py's INI_FIELD_TYPES and template.html's have drifted "
                         "apart -- the build and the runtime disagree about which grammars may "
                         "reach an ansible.cfg value")

    def test_the_ini_allow_list_admits_no_free_text(self):
        # Stated as its own assertion rather than left to the reader of the
        # table: `comment` is the one free-text type and `enum` is whatever a
        # content author lists. Neither can be made safe in a grammar with no
        # escape sequence, so neither is ever on this list.
        self.assertNotIn("comment", schema.INI_FIELD_TYPES)
        self.assertNotIn("enum", schema.INI_FIELD_TYPES)

    def test_doc_patterns_match_the_assembler(self):
        for name, compiled in (("DOC_KEY_RE", schema.DOC_KEY_RE),
                               ("DOC_LIT_RE", schema.DOC_LIT_RE),
                               ("INI_VALUE_RE", re.compile(r"^[A-Za-z0-9_./:@+(), -]+$"))):
            m = re.search(r"var %s=/(.+?)/;" % name, self.tpl)
            self.assertIsNotNone(m, "template.html has no %s" % name)
            self.assertEqual(compiled.pattern, m.group(1).replace("\\/", "/"),
                             "%s differs between extract/schema.py and template.html" % name)

    def test_max_indent_matches_the_assembler(self):
        m = re.search(r"var DOC_MAX_INDENT=(\d+);", self.tpl)
        self.assertIsNotNone(m, "template.html has no DOC_MAX_INDENT")
        self.assertEqual(int(m.group(1)), schema.DOC_MAX_INDENT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
