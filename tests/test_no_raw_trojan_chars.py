#!/usr/bin/env python3
"""test_no_raw_trojan_chars.py — no tracked source file spells an invisible character.

The gate behind Q21, and the reason it exists.

`tests/fixtures/hostile-inputs.json` states its invisible-character vectors as
JSON `\\u` escapes ON PURPOSE: the file that describes U+202E has to be a file a
reviewer can read and a diff can show. At `dd01ad7` I rewrote that fixture
through `json.dump(..., ensure_ascii=False)` while adding two field types, and
eight of those escapes came back out as the raw characters they name — U+200B,
U+200D, U+202E, U+FEFF, U+00AD, U+2028, U+2029 and U+2065. Nothing caught it.
Q17 could not: it scans the built artifact's shell and data island, and this
fixture reaches neither. The harness could not: it reads the file as JSON, where
an escape and the character it denotes are the same value, which is exactly why
the bug is invisible to every test that consumes the data rather than reading
the bytes.

So this reads the bytes. The character set is `qa.TROJAN_RANGES` — the table
Q17 already applies to the artifact, not a second copy written here; two
statements of one table is the thing `tests/test_schema.py` already exists to
prevent for the field-type and rich-rule tables.

`stig-src/` and `content-src/raw/` are excluded: pinned vendor captures, verified
by their own SHA256SUMS, not ours to normalise (`stig-src/U_CCI_List.xml`'s
leading BOM is legitimate and lives there).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_no_raw_trojan_chars.py
"""

import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402


class TheScannerCanFail(unittest.TestCase):
    """Negative controls first. A scanner only ever pointed at clean input is not a scanner.

    The planted files live in a temp directory, never in the repository: a
    committed fixture containing a raw U+202E would be the very thing this gate
    forbids, and excluding it by name would put a hole in the walk to hold the
    proof that the walk works.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _plant(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_a_planted_bidi_override_is_caught(self):
        """Al Kowalski's trojan-source shape: the character, not its escape."""
        # chr(), never the literal: a source file that spells U+202E is the very
        # thing this gate forbids, and an editor round-trip would plant it here.
        path = self._plant("planted.json",
                           '{"value": "safe' + chr(0x202E) + 'gnp"}\n')
        failures = qa.raw_trojan_failures([path])
        self.assertEqual(1, len(failures), failures)
        self.assertIn("U+202E", failures[0])
        self.assertIn("byte 15", failures[0])

    def test_each_character_class_is_caught(self):
        """Every class the set names, one planted file each."""
        for cp in (0x200B, 0x200D, 0x202E, 0xFEFF, 0x00AD, 0x2028, 0x2029, 0x2065,
                   0x0001, 0x000B, 0x001F, 0x0085, 0x2066, 0x206F):
            with self.subTest(codepoint=hex(cp)):
                path = self._plant("cp%04x.txt" % cp, "sa%sfe\n" % chr(cp))
                failures = qa.raw_trojan_failures([path])
                self.assertTrue(failures, "U+%04X was not caught" % cp)
                self.assertIn("U+%04X" % cp, failures[0])

    def test_the_escape_spelling_is_not_caught(self):
        """The whole point: `\\u202e` as six ASCII characters is what the fixture must hold."""
        path = self._plant("escaped.json", '{"value": "safe\\u202egnp"}\n')
        self.assertEqual([], qa.raw_trojan_failures([path]))

    def test_ordinary_text_is_not_caught(self):
        """Positive control. Tabs, newlines, em dashes and accents are not trojans."""
        path = self._plant("prose.md",
                           "# Title\tcol\n\nAn em dash " + chr(0x2014) + " and caf" +
                           chr(0xE9) + ".\n")
        self.assertEqual([], qa.raw_trojan_failures([path]))

    def test_a_binary_file_is_skipped_rather_than_guessed_at(self):
        path = os.path.join(self.tmp, "blob.bin")
        with open(path, "wb") as fh:
            fh.write(b"\x00\x01\x02\xff\xfe")
        self.assertEqual([], qa.raw_trojan_failures([path]))


class TheRepositoryIsClean(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.paths = qa.tracked_text_files()

    def test_the_corpus_is_real(self):
        """A walk that returns nothing would pass the assertion below."""
        self.assertIsNotNone(self.paths,
                             "git ls-files is unavailable, so this test cannot enumerate the "
                             "tracked files it exists to scan")
        self.assertGreater(len(self.paths), 100,
                           "only %d tracked files to scan — the corpus collapsed"
                           % len(self.paths or []))

    def test_nothing_is_excluded_from_the_walk(self):
        """MCR-SEC-025/F1. The first cut of this gate skipped stig-src/ and
        content-src/raw/ wholesale as "pinned vendor captures". Marcus Reed asked
        for the narrower rule instead — every tracked file scanned, with ONE
        allowance, a U+FEFF byte-order mark at offset 0 — and he is right: both
        trees measure clean apart from that single BOM, so the exclusion bought
        nothing and cost the two largest directories in the repository. An
        exclusion list is a hole in a walk; this one is now empty."""
        self.assertEqual((), qa.TROJAN_SCAN_EXCLUDE,
                         "the walk excludes %r — every prefix here is a directory no gate reads"
                         % (qa.TROJAN_SCAN_EXCLUDE,))
        for tree in ("stig-src/", "content-src/raw/"):
            self.assertTrue(any(p.startswith(tree) for p in self.paths),
                            "%s is not in the scanned corpus" % tree)

    def test_a_byte_order_mark_at_offset_zero_is_allowed(self):
        """The single allowance, and the only reason stig-src/ was ever excluded."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "bom.xml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(chr(0xFEFF) + '<?xml version="1.0"?>\n<x/>\n')
        self.assertEqual([], qa.raw_trojan_failures([path]),
                         "a leading BOM is legitimate file framing, not a trojan character")

    def test_a_byte_order_mark_anywhere_else_is_caught(self):
        """...and the allowance is offset 0 ONLY, or it is a loophole."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "midbom.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("safe" + chr(0xFEFF) + "value\n")
        failures = qa.raw_trojan_failures([path])
        self.assertEqual(1, len(failures), failures)
        self.assertIn("U+FEFF", failures[0])

    def test_the_cci_xml_is_the_only_file_leaning_on_that_allowance(self):
        """Named, so a second BOM cannot appear without someone deciding to allow it."""
        leading = []
        for rel in self.paths:
            with open(os.path.join(REPO, rel), "rb") as fh:
                head = fh.read(3)
            if head == b"\xef\xbb\xbf":
                leading.append(rel)
        self.assertEqual(["stig-src/U_CCI_List.xml"], leading,
                         "the set of files carrying a leading BOM changed: %r" % leading)

    def test_no_tracked_file_carries_a_raw_trojan_character(self):
        failures = qa.raw_trojan_failures(self.paths)
        self.assertEqual([], failures,
                         "%d raw control/bidi/zero-width character(s) in tracked source:\n  %s"
                         % (len(failures), "\n  ".join(failures)))

    def test_the_hostile_fixture_still_states_its_vectors_as_escapes(self):
        """The specific regression: the fixture must hold escapes, and still parse to the
        characters, so what the harness fuzzes with is unchanged by fixing how it is written."""
        import json
        rel = os.path.join("tests", "fixtures", "hostile-inputs.json")
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            text = fh.read()
        for cp in (0x200B, 0x200D, 0x202E, 0xFEFF, 0x00AD, 0x2028, 0x2029, 0x2065):
            with self.subTest(codepoint=hex(cp)):
                self.assertTrue("\\u%04x" % cp in text.lower(),
                                "the fixture no longer spells U+%04X as an escape" % cp)
        values = [v.get("value") for v in json.loads(text).get("vectors", [])]
        for cp in (0x202E, 0x2028, 0x2029, 0x2065):
            self.assertTrue(any(chr(cp) in v for v in values if isinstance(v, str)),
                            "U+%04X is no longer a vector the harness fuzzes with — the escaping "
                            "fix must not change what is tested" % cp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
