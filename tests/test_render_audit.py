#!/usr/bin/env python3
"""test_render_audit.py — qa.py Q17's render-sink audit, shown to fail (MCR-SEC-004).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_render_audit.py

Q17 is the gate that keeps the next render path somebody writes from becoming the
XSS path into a tool whose output is trusted at root. Marcus Reed's review of
4184ea8 showed five mechanical ways past it — `+=` on the sink, an ordinary
assignment instead of `+=`, an intermediate accumulator under another name,
insertAdjacentHTML(), outerHTML() — all of which the gate rated PASS.

This file drives the audit itself (`qa.render_sink_failures`) rather than running
the whole gate, so each construct is named individually in the output. The
healthy control runs first: a checker that has never been seen to pass on good
code proves as little as one that has never been seen to fail.
"""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

FIXTURES = os.path.join(REPO, "tests", "fixtures", "render-bypass")


def read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def fixtures(prefix):
    return sorted(n for n in os.listdir(FIXTURES) if n.startswith(prefix) and n.endswith(".js"))


class TheGateOnHealthyCode(unittest.TestCase):
    """Control first."""

    def test_the_safe_fixtures_pass(self):
        """Every safe_control_*.js is a shape the product writes and must keep writing.

        The computed-index control (MCR-SEC-014) is the false-positive guard for
        the computed-member rule: `out[fields[i].name] = ...` is ordinary code in
        this very repo, and a gate that flagged it would be turned off.
        """
        names = fixtures("safe_control")
        self.assertGreaterEqual(len(names), 2, "the safe control set has shrunk")
        audited_any = 0
        for name in names:
            with self.subTest(fixture=name):
                failures, audited = qa.render_sink_failures(read(name))
                self.assertEqual([], failures, "%s: the audited render shape was flagged: %s"
                                 % (name, failures))
                audited_any += audited
        self.assertGreater(audited_any, 0, "nothing was audited — the checker read no expressions")

    def test_the_shipped_shell_passes(self):
        """The product's own render paths, as written today."""
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as f:
            shell = f.read()
        failures, audited = qa.render_sink_failures(shell)
        self.assertEqual([], failures, "template.html fails its own render audit:\n  "
                                       + "\n  ".join(failures))
        self.assertGreater(audited, 20)


class EveryBypassIsCaught(unittest.TestCase):

    def test_the_unsafe_control_fails(self):
        for name in fixtures("unsafe_control"):
            with self.subTest(fixture=name):
                failures, _ = qa.render_sink_failures(read(name))
                self.assertTrue(failures, "%s was rated safe" % name)

    def test_every_bypass_fixture_fails(self):
        names = fixtures("bypass_")
        self.assertGreaterEqual(len(names), 15, "the bypass fixture set has shrunk")
        for name in names:
            with self.subTest(fixture=name):
                failures, _ = qa.render_sink_failures(read(name))
                self.assertTrue(failures, "%s bypassed the render audit and was rated safe" % name)

    def test_accumulators_are_derived_from_the_source(self):
        """MCR-SEC-004(b): not a hard-coded name list."""
        acc = qa.derive_accumulators(read("bypass_3_intermediate_accumulator.js"))
        self.assertIn("html", acc)
        self.assertIn("h", acc, "an intermediate accumulator was not followed")


class IsLiteralActuallyParses(unittest.TestCase):
    """MCR-SEC-004(c): first-and-last-character matching is not parsing."""

    def test_a_concatenation_is_not_a_literal(self):
        self.assertFalse(qa.is_literal('"a" + raw + "b"'))
        self.assertFalse(qa.is_literal("'a' + raw + 'b'"))
        self.assertFalse(qa.is_literal('"unterminated'))
        self.assertFalse(qa.is_literal('`template ${x}`'))
        self.assertFalse(qa.is_literal('"a" + "b"'))

    def test_real_literals_still_pass(self):
        self.assertTrue(qa.is_literal('"a string"'))
        self.assertTrue(qa.is_literal("'a string'"))
        self.assertTrue(qa.is_literal(r'"an \"escaped\" quote"'))
        self.assertTrue(qa.is_literal('""'))


class TrojanScanCoversTheIsland(unittest.TestCase):
    """C10: DISA fix text is rendered AND copied into evidence."""

    def test_a_planted_bidi_override_is_caught(self):
        # built from a code point, never typed: the character this gate exists
        # to catch must not be sitting in this file's own source.
        planted = 'rule fix text: run this' + chr(0x202E) + ' then that'
        self.assertTrue(qa.trojan_scan(planted, "a test rule's fix text"),
                        "a U+202E right-to-left override in vendor prose was not flagged")

    def test_a_planted_nul_is_caught(self):
        self.assertTrue(qa.trojan_scan("fix text" + chr(0), "a test rule's fix text"))

    def test_clean_vendor_prose_is_not_flagged(self):
        self.assertEqual([], qa.trojan_scan("Run " + chr(0xA7) + " 5.2 " + chr(0x2014) + " set the flag to 'on'.", "prose"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
