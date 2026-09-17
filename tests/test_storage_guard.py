#!/usr/bin/env python3
"""test_storage_guard.py — Q7's try/catch span finder, shown to fail (AL-GATE3-003).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_storage_guard.py

Q7 exists because storage is blocked outright on `file://` in some browsers, and
an unguarded `localStorage.getItem()` there is an uncaught exception on load —
on a jump box, mid-task, a blank page. The gate proves every storage identifier
in the shipped script sits inside a `try{...}catch` block.

It proved it by counting raw `{` and `}` characters. Al Kowalski's Gate 3 review
(AL-GATE3-003, MEDIUM) reproduced what that costs: ONE unbalanced brace inside a
string literal inside a `try` body shifts the running depth, so the span does not
close at its own `catch` — it runs on and swallows the sibling code after it. A
genuinely unguarded storage call in that sibling code is then reported as one of
the "audited try/catch references", silently.

    try {
      var s = "{";                       // <- the brace that desyncs the count
      localStorage.setItem("a","1");
    } catch(e){}
    localStorage.setItem("c","3");       // <- NOT guarded; rated guarded

The construct is not exotic. A CSS selector, an embedded JSON example, a regex
written as a string, a `${` in prose — any of them does it by accident, and the
result is a silent PASS.

The control runs first, here as everywhere: the same finder must still be right
about code that is genuinely guarded and code that is genuinely not.
"""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402


def guarded_hits(script):
    """(line, guarded?) for every storage identifier, the way Q7 judges them.

    try_block_spans() is handed the script as written. Deciding what is a brace
    and what is a character inside a literal is the finder's own job — a caller
    that has to remember to launder its input first is a caller that will one day
    forget, and AL-GATE3-003 is what that costs.
    """
    import re
    spans = qa.try_block_spans(script)
    masked = qa.mask_js_literals(script)
    out = []
    for m in re.finditer(r"\b(?:localStorage|sessionStorage)\b", masked):
        out.append((masked[:m.start()].count("\n") + 1,
                    any(s <= m.start() < e for s, e in spans)))
    return out


# Al's reproduction, verbatim from the review.
BRACE_IN_STRING = '''function guarded(){
  try {
    var s = "{";
    localStorage.setItem("a","1");
  } catch(e){}
  localStorage.setItem("c","3");
}
'''

# The same desync reached four other ways. A checker fixed for one spelling of a
# bug and not the rest has been fixed for the fixture, not for the bug.
BRACE_IN_TEMPLATE = '''function guarded(){
  try {
    var s = `${"x"}{`;
    localStorage.setItem("a","1");
  } catch(e){}
  localStorage.setItem("c","3");
}
'''
BRACE_IN_REGEX = '''function guarded(){
  try {
    var re = /[{]/;
    localStorage.setItem("a","1");
  } catch(e){}
  localStorage.setItem("c","3");
}
'''
BRACE_IN_LINE_COMMENT = '''function guarded(){
  try {
    // the record shape is {schema,data}
    localStorage.setItem("a","1");
  } catch(e){}
  localStorage.setItem("c","3");
}
'''
BRACE_IN_BLOCK_COMMENT = '''function guarded(){
  try {
    /* the record shape is {schema,data} */
    localStorage.setItem("a","1");
  } catch(e){}
  localStorage.setItem("c","3");
}
'''
# The closing half of the pair, which shortens the span instead of lengthening
# it: a genuinely guarded call reported as unguarded is a false FAIL, and a gate
# that cries wolf gets switched off.
CLOSE_BRACE_IN_STRING = '''function guarded(){
  try {
    var s = "}";
    localStorage.setItem("a","1");
  } catch(e){}
}
'''

HEALTHY_GUARDED = '''function guarded(){
  try { localStorage.setItem("a","1"); } catch(e){}
  try { return sessionStorage.getItem("b"); } catch(e){ return null; }
}
'''
HEALTHY_UNGUARDED = '''function loose(){
  localStorage.setItem("a","1");
}
'''

DESYNCING = [
    ("a brace inside a string literal", BRACE_IN_STRING),
    ("a brace inside a template literal", BRACE_IN_TEMPLATE),
    ("a brace inside a regex literal", BRACE_IN_REGEX),
    ("a brace inside a // comment", BRACE_IN_LINE_COMMENT),
    ("a brace inside a /* */ comment", BRACE_IN_BLOCK_COMMENT),
]


class TheFinderOnHealthyCode(unittest.TestCase):
    """Control first."""

    def test_a_guarded_call_is_rated_guarded(self):
        self.assertEqual([(2, True), (3, True)], guarded_hits(HEALTHY_GUARDED))

    def test_an_unguarded_call_is_rated_unguarded(self):
        self.assertEqual([(2, False)], guarded_hits(HEALTHY_UNGUARDED))

    def test_the_shipped_script_still_passes(self):
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as f:
            script = qa.app_script_of(f.read())
        failures, details = qa.storage_guard_failures(script)
        self.assertEqual([], failures, "template.html's own storage guard was flagged:\n  "
                                       + "\n  ".join(failures))
        self.assertTrue(details)


class TheSpanCannotBeDesynced(unittest.TestCase):

    def test_a_sibling_call_is_not_swallowed(self):
        for label, script in DESYNCING:
            with self.subTest(construct=label):
                hits = guarded_hits(script)
                self.assertEqual(2, len(hits), "%s: expected two storage hits, got %s"
                                               % (label, hits))
                self.assertTrue(hits[0][1], "%s: the call actually inside the try was rated "
                                            "unguarded" % label)
                self.assertFalse(hits[1][1],
                                 "%s desynced the brace count: the sibling call on line %d sits "
                                 "AFTER the catch and was rated guarded (AL-GATE3-003)"
                                 % (label, hits[1][0]))

    def test_the_gate_fails_on_each_one(self):
        """Through the gate's own logic, not only through the span finder."""
        for label, script in DESYNCING:
            with self.subTest(construct=label):
                failures, _ = qa.storage_guard_failures(script)
                self.assertTrue(failures, "%s: Q7 rated a script with an unguarded storage call "
                                          "clean" % label)

    def test_a_closing_brace_in_a_string_does_not_shorten_the_span(self):
        """The false-FAIL half: a gate that cries wolf gets switched off."""
        hits = guarded_hits(CLOSE_BRACE_IN_STRING)
        self.assertEqual([(4, True)], hits,
                         "a '}' inside a string literal closed the try span early and a genuinely "
                         "guarded call was reported unguarded")
        self.assertEqual([], qa.storage_guard_failures(CLOSE_BRACE_IN_STRING)[0])


class MaskingIsLossless(unittest.TestCase):
    """mask_js_literals() is load-bearing for Q2, Q5, Q7 and Q19; it must not lie."""

    def test_offsets_and_line_breaks_survive(self):
        for _label, script in DESYNCING:
            masked = qa.mask_js_literals(script)
            self.assertEqual(len(script), len(masked), "masking changed the length")
            self.assertEqual(script.count("\n"), masked.count("\n"), "masking lost a line break")

    def test_string_contents_go_and_delimiters_stay(self):
        masked = qa.mask_js_literals('var a="localStorage"; var b=3;')
        self.assertNotIn("localStorage", masked, "a string's contents survived the mask")
        self.assertIn('var a="', masked, "the opening delimiter was blanked with the contents")
        self.assertIn("var b=3;", masked, "real code was blanked")

    def test_comments_go_entirely(self):
        masked = qa.mask_js_literals("var a=1; // localStorage\n/* localStorage */ var b=2;")
        self.assertNotIn("localStorage", masked)
        self.assertIn("var a=1;", masked)
        self.assertIn("var b=2;", masked)

    def test_a_character_class_holding_a_quote_does_not_desync_the_rest(self):
        """The construct that is actually in template.html: /[&<>"']/g."""
        masked = qa.mask_js_literals('x.replace(/[&<>"\']/g,"y"); var keep=1;')
        self.assertIn("var keep=1;", masked,
                      "a quote inside a regex character class threw the masker out of phase and "
                      "swallowed the rest of the file")


if __name__ == "__main__":
    unittest.main(verbosity=2)
