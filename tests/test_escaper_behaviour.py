#!/usr/bin/env python3
"""test_escaper_behaviour.py — the escapers must ESCAPE, not merely be called (AL-GATE3-001).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_escaper_behaviour.py

Al Kowalski's BQP Gate 3 review of qa.py returned PASS WITH ISSUES with one HIGH
finding, and this is it. Q17 proves that `esc()` / `escapeAttr()` are CALLED at
every render sink. It never proves, and structurally cannot prove, that either
one escapes anything. A one-line change to either body —

    function esc(s){ return s; }

— defeats the entire render-safety property with ZERO change to any call site,
and every call site keeps looking exactly as safe as it does today. Al's
reproduction, from the review:

    qa.render_sink_failures(shell_with_identity_escapers)
    # -> ([], 4)   — zero failures, 4 expressions "audited"

`TheRenderAuditCannotSeeThis` below re-runs that reproduction and asserts the
result Al got, so what Q17 does NOT prove is written down as an executable fact
rather than as a sentence somebody has to remember. It is expected to keep
passing forever: Q17 is a static audit of call sites and making it a behavioural
one is not possible from the source text.

Everything under `TheEscaperGateCatchesIt` drives the new gate — the one that
lifts the three functions out of the SHIPPED artifact and RUNS them against a
hostile corpus under node. Those tests fail until that gate exists, which is the
point of committing this file first (the CR-T-08 convention: a gate shown to
fail before it is shown to pass).

Node is REQUIRED here for the same reason it is required by
tests/test_hostile_inputs.py: the escapers are JavaScript, and the only honest
way to find out what they do to a string is to run them on one. A Python
re-implementation would be a second escaper to keep in sync, and the one that
shipped would be the one nobody tested.
"""

import json
import os
import shutil
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

PROBE = os.path.join(REPO, "tests", "escaper_probe.js")
CORPUS = os.path.join(REPO, "tests", "fixtures", "escaper-corpus.json")

# Al's reproduction, verbatim from the Gate 3 review §2 AL-GATE3-001.
IDENTITY_SHELL = '''
function esc(s){ return s; }               /* identity, not escaping */
function escapeAttr(s){ return s; }
function escapeRegex(s){ return s; }
function render(entry){
  var html="";
  html+="<h2>"+esc(entry.intent)+"</h2>";
  html+="<p class=\\""+escapeAttr(entry.tool)+"\\">"+esc(entry.notes||"")+"</p>";
  el("x").innerHTML=html;
}
'''

# Broken the way a real regression breaks an escaper: a well-meaning
# "optimization" that strips the dangerous characters instead of encoding them.
# It is XSS-safe and DATA-destructive — DISA fix text would silently lose every
# angle bracket it contains — so a gate that only asked "is the output safe"
# would rate it clean.
DROPPING_SHELL = '''
function esc(s){ return String(s==null?"":s).replace(/[&<>"']/g,""); }
function escapeAttr(s){ return esc(s); }
function escapeRegex(s){ return String(s==null?"":s).replace(/[.*+?^${}()|[\\]\\\\]/g,"\\\\$&"); }
'''

# Half-escaped: the shape a hand-written escaper actually arrives in. Angle
# brackets handled, quotes forgotten, so a value rendered into an attribute
# closes it.
HALF_SHELL = '''
function esc(s){ return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function escapeAttr(s){ return esc(s); }
function escapeRegex(s){ return String(s==null?"":s).replace(/[.*+?^${}()|[\\]\\\\]/g,"\\\\$&"); }
'''

# escapeRegex() alone reverted, which the two HTML escapers would not notice:
# the search path builds a RegExp from operator text.
REGEX_ONLY_SHELL = '''
function esc(s){ return String(s==null?"":s).replace(/[&<>"']/g,function(c){
  return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[c]; }); }
function escapeAttr(s){ return esc(s).replace(/`/g,"&#96;").replace(/=/g,"&#61;"); }
function escapeRegex(s){ return String(s==null?"":s); }
'''


def require_node():
    node = shutil.which("node")
    if not node:
        raise AssertionError(
            "node is not on PATH. The escapers are JavaScript and this test runs them; install "
            "Node (CI uses actions/setup-node@v4) rather than skipping the one test that proves "
            "the functions the whole render path funnels through actually escape.")
    return node


class TheRenderAuditCannotSeeThis(unittest.TestCase):
    """The control: Al's reproduction, kept executable.

    This is not a bug to fix in Q17. It is the boundary of what a static audit of
    call sites can prove, recorded so nobody reads a Q17 PASS as "rendering is
    safe" when it means "no new UNESCAPED render path was added".
    """

    def test_identity_escapers_pass_the_render_sink_audit(self):
        failures, audited = qa.render_sink_failures(IDENTITY_SHELL)
        self.assertEqual([], failures,
                         "Q17 started catching identity escapers — if that is deliberate, this "
                         "control should be rewritten, not deleted")
        self.assertEqual(4, audited,
                         "the audit read a different number of expressions than Al's transcript "
                         "recorded (%d, not 4)" % audited)


class TheEscaperGateCatchesIt(unittest.TestCase):
    """The gate that runs the functions instead of reading them."""

    def test_the_shipped_escapers_pass(self):
        """Control first: the real thing must be clean, or the gate is unusable."""
        require_node()
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as f:
            shell = f.read()
        failures, details = qa.escaper_failures(shell)
        self.assertEqual([], failures, "template.html's own escapers fail the property gate:\n  "
                                       + "\n  ".join(failures))
        self.assertTrue(details, "the gate passed without reporting what it checked")

    def test_identity_escapers_fail(self):
        """AL-GATE3-001's own reproduction, through the gate that is meant to see it."""
        require_node()
        failures, _ = qa.escaper_failures(IDENTITY_SHELL)
        self.assertTrue(failures, "`return s;` in every escaper body was rated safe — this is the "
                                  "exact one-line change AL-GATE3-001 is about")

    def test_an_escaper_that_drops_characters_fails(self):
        """Safe output is not enough: escaping has to be reversible."""
        require_node()
        failures, _ = qa.escaper_failures(DROPPING_SHELL)
        self.assertTrue(failures, "an escaper that deletes the dangerous characters instead of "
                                  "encoding them was rated clean; it is XSS-safe and silently "
                                  "corrupts every DISA fix text that contains a '<'")

    def test_a_half_escaper_fails(self):
        require_node()
        failures, _ = qa.escaper_failures(HALF_SHELL)
        self.assertTrue(failures, "an escaper that handles < and > but not the quotes was rated "
                                  "clean — that value closes the attribute it is rendered into")

    def test_a_reverted_escape_regex_fails(self):
        """The two HTML escapers being right does not make the third one right."""
        require_node()
        failures, _ = qa.escaper_failures(REGEX_ONLY_SHELL)
        self.assertTrue(failures, "escapeRegex() reverted to the identity was rated clean")

    def test_a_missing_escaper_is_a_failure_not_a_skip(self):
        failures, _ = qa.escaper_failures("function esc(s){ return s; }\n")
        self.assertTrue(failures)
        self.assertIn("escapeAttr", " ".join(failures),
                      "a shell with no escapeAttr() definition must name the missing function")

    def test_extraction_refuses_an_impure_escaper(self):
        """The same purity rule hostile_harness.js puts on the assembler block."""
        impure = ('function esc(s){ return document.createTextNode(s).nodeValue; }\n'
                  'function escapeAttr(s){ return esc(s); }\n'
                  'function escapeRegex(s){ return s; }\n')
        require_node()
        failures, _ = qa.escaper_failures(impure)
        self.assertTrue(failures, "an escaper reaching into the DOM was accepted — the probe would "
                                  "be testing a stub, or crashing, rather than the shipped code")


class TheProbeItself(unittest.TestCase):
    """A checker that has never been seen to fail is not a checker."""

    def test_the_probe_reports_its_own_negative_controls(self):
        """The probe refuses to report a PASS unless it just failed three known-broken escapers."""
        node = require_node()
        self.assertTrue(os.path.exists(CORPUS), "the hostile corpus fixture is missing")
        # Drive the probe directly with the shipped escaper text.
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as f:
            shell = f.read()
        block, err = qa.extract_escaper_block(shell)
        self.assertIsNone(err, "could not lift the escapers out of template.html: %s" % err)
        path = os.path.join(REPO, "tests", ".escaper_probe_input.js")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(block)
            proc = subprocess.run([node, PROBE, path, "--json"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            report = json.loads(proc.stdout.decode("utf-8", "replace"))
        finally:
            if os.path.exists(path):
                os.unlink(path)
        self.assertEqual([], report["failures"])
        self.assertEqual(0, proc.returncode)
        self.assertGreaterEqual(report["negative_controls"], 3,
                                "the probe's own broken-escaper set has shrunk")
        self.assertGreater(report["checks"], 200,
                           "the battery ran too few checks to be the corpus it claims")

    def test_the_corpus_covers_the_classes_the_finding_named(self):
        with open(CORPUS, encoding="utf-8") as f:
            doc = json.load(f)
        classes = set(v["class"] for v in doc["vectors"])
        for required in ("html metacharacter", "xss cheat-sheet", "nested entity",
                         "control or invisible", "surrogate half", "regex metacharacter",
                         "look-alike or shell-shaped", "benign"):
            self.assertIn(required, classes, "the escaper corpus is missing the %s class" % required)
        values = "".join(v["value"] for v in doc["vectors"])
        for ch in ("&", "<", ">", '"', "'", "/", "`", chr(0), chr(0x2028), chr(0x2029),
                   chr(0x202E), chr(0xD800)):
            self.assertIn(ch, values, "no corpus vector carries U+%04X" % ord(ch))
        self.assertTrue(any(g["count"] >= 10000 for g in doc["generated"]),
                        "no very long generated vector — a length bug in an escaper is a real one")

    def test_the_corpus_declares_its_provenance(self):
        with open(CORPUS, encoding="utf-8") as f:
            src = json.load(f)["_meta"]["source"]
        for key in ("title", "url_or_man", "version", "retrieved_on", "license_class"):
            self.assertTrue(src.get(key), "escaper-corpus source.%s missing" % key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
