#!/usr/bin/env python3
"""test_airgap_and_markers.py — Q2 and Q5 read text, not structure (AL-GATE3 §1).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_airgap_and_markers.py

Two rows of Al Kowalski's Gate 3 per-gate table, both marked "fail-open risk
found: Y" with no negative control and, for Q2, no test file of any kind.

Q2 — air-gap law. The scan is `re.findall` over the shipped text for
`fetch(`, `XMLHttpRequest`, `WebSocket`, `navigator.sendBeacon`, `import(`.

    "A computed call (window["fe"+"tch"](), var f=fetch;f()) or a non-literal
     CDN host built by string concatenation is invisible to it — same structural
     class as the already-known Q17 computed-member gap (MCR-SEC-014), but here
     it is undocumented and untested, not an accepted, recorded residual."

Q17 closed that class for render sinks under MCR-SEC-014 condition D2. The same
three shapes — a bracketed name, a name fused inline from literals, a name built
through a variable across statements — reach the network API and nothing looks
at them. The air gap is not a nice-to-have in this product: the whole reason a
single HTML file exists is that it runs on a machine with no route off it.

Q5 — feature markers. A substring match over the WHOLE shipped file, so a marker
string sitting in a comment, a doc string, or dead code registers as "present".

    "Same limitation as Q6, but Q5's markers stand in for structural product
     claims ('rail renderer exists'), which is a stronger claim to be making
     from a substring hit."

A marker is not all one kind of thing, and the fix reflects that rather than
flattening it: `function renderRail(` is a claim about CODE, `id="rail"` is a
claim about the static HTML, and `Not available in RHEL ` is deliberately a
claim about user-visible COPY, which lives inside a string literal and must
stay allowed there. The marker list itself is untouched — the kind is derived
from the marker text, so a tranche that adds markers does not also have to
classify them, and two branches adding markers do not collide over a schema
change.

Controls first in both halves: every shape this product actually writes must
stay clean, or the gates get turned off and the real ones go with them.
"""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402


# --------------------------------------------------------------------- Q2 ---

REACHES_THE_NETWORK = [
    ("a bracketed API name",
     'window["fetch"]("/x");'),
    ("a name fused inline from literals",
     'window["fe"+"tch"]("/x");'),
    ("a name fused with a decoy term between the pieces",
     'var part="tch"; window["fe"+part]("/x");'),
    ("a name built through a variable across statements",
     'var k="fe"; k+="tch"; window[k]("/x");'),
    ("an alias taken without calling it at the definition",
     'var f=fetch; later(function(){ f("/x"); });'),
    ("an alias through a bracketed global",
     'var f=window["XMLHttp"+"Request"]; var r=new f();'),
    ("a constructor rather than a call",
     'var s=new WebSocket("wss://x");'),
    ("the beacon, aliased",
     'var b=navigator.sendBeacon; b("/x","y");'),
    ("a dynamic import",
     'import("./mod.js");'),
]

# Everything here is a shape template.html writes today, or one it plausibly
# will. A gate that flags any of these is a gate somebody will delete.
STAYS_CLEAN = [
    ("an object index by identifier", 'out[fields[i].name] = v;'),
    ("an array index", 'var x = list[i]; var y = list[i + 1];'),
    ("a map read with a literal key", 'var t = FIELD_TYPES["path"];'),
    ("a dispatch table call", 'var fn = handlers[name]; fn(ev);'),
    ("a nested index", 'out.resolved[f.name] = spec[f.name][0];'),
    ("dotted DOM access", 'document.getElementById("rail").hidden = false;'),
    ("the word in a comment", '/* there is no fetch in this product */ var a=1;'),
    ("the word in a string", 'var msg = "no fetch, no XMLHttpRequest, no WebSocket";'),
    ("an unrelated concatenation", 'var cls = "mean" + " " + "unverified";'),
    ("an identifier that merely contains one", 'var prefetching = 0; refetchLater();'),
]


class TheAirGapOnCodeTheProductWrites(unittest.TestCase):
    """Control first."""

    def test_nothing_the_product_writes_is_flagged(self):
        for label, src in STAYS_CLEAN:
            with self.subTest(shape=label):
                self.assertEqual([], qa.network_call_failures(src),
                                 "%s was flagged as a network call" % label)

    def test_the_shipped_script_is_clean(self):
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as f:
            script = qa.app_script_of(f.read())
        self.assertEqual([], qa.network_call_failures(script),
                         "template.html's own app script was flagged")

    def test_a_plain_call_is_still_caught(self):
        """The check that already worked must keep working."""
        self.assertTrue(qa.network_call_failures('fetch("/x");'))


class TheAirGapCannotBeSpelledAround(unittest.TestCase):

    def test_every_computed_route_to_the_network_fails(self):
        for label, src in REACHES_THE_NETWORK:
            with self.subTest(shape=label):
                self.assertTrue(qa.network_call_failures(src),
                                "%s reached a network API and Q2 saw nothing — the same "
                                "structural class MCR-SEC-014 closed for render sinks" % label)

    def test_the_failure_names_the_api(self):
        failures = qa.network_call_failures('window["fe"+"tch"]("/x");')
        self.assertIn("fetch", " ".join(failures).lower())

    def test_the_whole_gate_fails_on_a_planted_call(self):
        if not qa.find_artifact():
            self.skipTest("no dist/ artifact — run python3 build.py first")
        ctx = qa.build_ctx()
        self.assertEqual([], qa.gate_q2(ctx)[0], "Q2 fails on the real artifact")
        planted = '\nvar leak=window["fe"+"tch"];\n'
        # planted into everything Q2 reads, so the gate gets every chance it has
        ctx["app_script"] = ctx["app_script"] + planted
        ctx["shell"] = ctx["shell"] + planted
        ctx["html"] = ctx["html"] + planted
        self.assertTrue(qa.gate_q2(ctx)[0],
                        "Q2 passed an app script carrying a spliced fetch reference")


# --------------------------------------------------------------------- Q5 ---

class MarkersAreClassifiedFromTheirOwnText(unittest.TestCase):
    """No schema change to MARKERS: two branches adding markers must not collide."""

    def test_the_kinds_are_derived(self):
        self.assertEqual("code", qa.marker_kind("function renderRail("))
        self.assertEqual("code", qa.marker_kind('var APP_NAME="'))
        self.assertEqual("code", qa.marker_kind('document.addEventListener("click"'))
        self.assertEqual("html", qa.marker_kind('id="rail"'))
        self.assertEqual("text", qa.marker_kind("MCR-ASSEMBLER-BEGIN"))
        self.assertEqual("text", qa.marker_kind("Not available in RHEL "))
        self.assertEqual("text", qa.marker_kind("@media print"))

    def test_every_shipped_marker_classifies(self):
        for name, marker, _phase in qa.MARKERS:
            with self.subTest(marker=name):
                self.assertIn(qa.marker_kind(marker), ("code", "html", "text"))


class AMarkerInACommentIsNotAFeature(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(REPO, "template.html"), encoding="utf-8") as f:
            self.html = f.read()

    def test_the_real_file_has_every_non_pending_marker(self):
        """Control: the gate must still see what is genuinely there."""
        missing = [name for name, marker, phase in qa.MARKERS
                   if not phase and not qa.marker_present(self.html, marker)]
        self.assertEqual([], missing, "markers that exist in template.html were not found: %s"
                                      % missing)

    def test_a_code_marker_in_a_block_comment_does_not_count(self):
        planted = "<script>\n/* one day: function renderStigPanel(entry){} */\nvar a=1;\n</script>"
        self.assertFalse(qa.marker_present(planted, "function renderStigPanel("),
                         "a function named only inside a /* */ comment was counted as a feature")

    def test_a_code_marker_in_a_line_comment_does_not_count(self):
        planted = "<script>\n// TODO function exportEvidence(){}\nvar a=1;\n</script>"
        self.assertFalse(qa.marker_present(planted, "function exportEvidence("))

    def test_a_code_marker_inside_a_string_does_not_count(self):
        planted = '<script>\nvar doc="function buildIndex( is coming in CR-T-29";\n</script>'
        self.assertFalse(qa.marker_present(planted, "function buildIndex("),
                         "a function named only inside a string literal was counted as a feature")

    def test_a_real_definition_does_count(self):
        real = "<script>\nfunction renderStigPanel(entry){ return 1; }\n</script>"
        self.assertTrue(qa.marker_present(real, "function renderStigPanel("))

    def test_a_marker_whose_own_text_contains_a_string_still_matches(self):
        """`document.addEventListener("click"` is code and ends inside a literal."""
        real = '<script>\ndocument.addEventListener("click", onClick, false);\n</script>'
        self.assertTrue(qa.marker_present(real, 'document.addEventListener("click"'))

    def test_an_html_region_marker_in_a_js_string_does_not_count(self):
        planted = '<body></body>\n<script>\nvar t = \'<nav id="rail"></nav>\';\n</script>'
        self.assertFalse(qa.marker_present(planted, 'id="rail"'),
                         "a region id that exists only inside a JS string was counted as a region")

    def test_an_html_region_marker_in_an_html_comment_does_not_count(self):
        planted = '<!-- <nav id="rail"></nav> is coming -->\n<body></body>'
        self.assertFalse(qa.marker_present(planted, 'id="rail"'))

    def test_a_real_region_does_count(self):
        self.assertTrue(qa.marker_present('<nav id="rail" role="navigation"></nav>', 'id="rail"'))

    def test_copy_markers_are_still_allowed_to_live_in_strings(self):
        """The distinction the fix exists to preserve: copy IS a string."""
        real = '<script>\nvar r = "Not available in RHEL " + v;\n</script>'
        self.assertTrue(qa.marker_present(real, "Not available in RHEL "),
                        "a user-visible copy marker was rejected for being in a string literal, "
                        "which is the only place copy can be")

    def test_the_whole_gate_fails_when_a_real_marker_is_demoted_to_a_comment(self):
        if not qa.find_artifact():
            self.skipTest("no dist/ artifact — run python3 build.py first")
        ctx = qa.build_ctx()
        self.assertEqual([], qa.gate_q5(ctx)[0], "Q5 fails on the real artifact")
        ctx["html"] = ctx["html"].replace("function renderRail(", "function renderRail_MOVED(")
        ctx["html"] = ctx["html"].replace("</body>", "<!-- function renderRail( -->\n</body>")
        self.assertTrue(qa.gate_q5(ctx)[0],
                        "Q5 accepted an HTML comment as proof that the rail renderer exists")


if __name__ == "__main__":
    unittest.main(verbosity=2)
