#!/usr/bin/env python3
"""test_pipeline_ui_wiring.py - CR-T-31, the UI half of the composer.

tests/hostile_harness.js proves the ASSEMBLER: an operator is a key into a
closed table, a value is a single-quoted token, and the pipeline oracle checks
the emitted line word by word. None of that says anything about the PANEL that
drives it, and the panel is where the design constraint is easiest to lose:

    A PIPELINE IS STRUCTURE THE TOOL OWNS, NEVER A VALUE THE USER SUPPLIES.

One text input rendered with an operator in its value, one control wired to a
verb the router does not handle, and the constraint is gone or the feature is
silently dead. This file is the gate on that seam.

It reads template.html, which is where the app script LIVES: build.py inlines
the content island into this same file, so the shell these checks read is
byte-for-byte the shell that ships. dist/ deliberately holds a FROZEN release
artifact (v1.0.0-alpha.1) that predates this feature, and a gate that read it
would report on a build nobody is changing -- the same reasoning
test_airgap_and_markers.py applies to the marker inventory.

WHAT IT ASSERTS

  1. OPERATOR TEXT NEVER REACHES A VALUE. Inside renderPipelinePanel(), every
     read of PIPE_OPERATORS[...].emit goes through esc() into element TEXT. No
     `value="` attribute in the panel is fed from the operator table, and
     neither pipelineSetOp() nor pipelineRowFor() touches emit text at all --
     STATE carries a KEY, because a key cannot be typed into a form and text
     can.
  2. THE OPTION VALUES ARE KEYS. The operator <select> carries option values
     from PIPE_OPERATOR_KEYS through escapeAttr(), so what the DOM hands back
     to pipelineSetOp() is a key, which hasOwnProperty then resolves against
     the closed table.
  3. NO CONTROL IS DEAD AND NO VERB IS UNREACHABLE. Every data-pipe-action verb
     the renderer emits is handled by the click router and every verb the
     router handles is emitted by the renderer; same, both ways, for every
     data-pipe-field. A gate proves a feature works; a dead button proves
     nothing and is found by a user.
  4. THE PICKER OFFERS EXACTLY THE CLOSED SET. PIPE_OPERATOR_KEYS and the own
     keys of PIPE_OPERATORS are the same set of ten, and every emit in the
     table is in the emission allow-list pipeOperator() fails closed against.
  5. ONE SINK, ONE WRITER. #pipeline-panel is written by renderPipelinePanel()
     and nothing else, and renderAll() calls it -- Q17's rule applied to the
     panel CR-T-31 added.
  6. THE ONLY FREE TEXT IS A PATH AND AN INTEGER, both of which validateField()
     owns. A third free-text field added here without a validator behind it is
     how an operator becomes typeable.

EVERY CHECK IS SHOWN TO FAIL. Each audit below is a function of the source
text, so the negative controls at the bottom hand each one a MUTATED copy of
the real file -- an operator emitted into a value, a button whose verb the
router does not handle, a key removed from the picker, a second writer into the
sink -- and fail if the audit still reports the file clean. A checker nobody
has watched fail is not a gate; it is a comment (PL5, and the discipline that
caught MCR-SEC-008).
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

SRC_PATH = os.path.join(REPO, "template.html")
with open(SRC_PATH, encoding="utf-8") as _f:
    SRC = _f.read()


def body(src, name):
    text, err = qa.extract_js_function(src, name)
    if err:
        raise AssertionError("%s: %s" % (name, err))
    return text


# ---------------------------------------------------------------------------
# The audits. Each takes the whole source and returns a list of failure
# strings, so each can be driven with a mutated copy by the controls below.
# ---------------------------------------------------------------------------

def audit_operator_text_stays_text(src):
    """Claim 1: emit text is esc()'d into element text and reaches no value."""
    f = []
    panel = body(src, "renderPipelinePanel")
    reads = [m.start() for m in re.finditer(r"PIPE_OPERATORS\[[^\]]+\]\.emit", panel)]
    if not reads:
        f.append("the panel never renders an operator's text at all -- the picker would show "
                 "ten unlabelled options, which is not a readable closed set")
    for pos in reads:
        before = panel[:pos]
        esc_at = before.rfind("esc(")
        attr_at = before.rfind("escapeAttr(")
        if esc_at < 0:
            f.append("an operator's emit text is rendered without esc() at offset %d" % pos)
        elif esc_at < attr_at:
            f.append("an operator's emit text at offset %d is rendered through escapeAttr(), the "
                     "ATTRIBUTE escaper: operator text belongs in element text, never a value" % pos)
    for m in re.finditer(r'value=\\"', panel):
        # Only the expression INSIDE the attribute: cut at the escaped quote
        # that closes it, so the option's TEXT -- which follows and IS allowed
        # to carry operator text -- is not read as part of the value.
        window = panel[m.end():m.end() + 400]
        cut = window.find('\\"')
        if cut >= 0:
            window = window[:cut]
        if "PIPE_OPERATORS" in window:
            f.append("a value= attribute in the pipeline panel is fed from the operator table. An "
                     "operator that can round-trip through a form value is a value the user "
                     "supplies, which is the one thing this design forbids")
    for fn in ("pipelineSetOp", "pipelineRowFor"):
        if ".emit" in body(src, fn):
            f.append("%s() reads the table's emit TEXT. The UI must carry a key: a key cannot be "
                     "typed into a form, and text can" % fn)
    return f


def audit_the_picker_hands_back_a_key(src):
    """Claim 2: option values are keys, and the setter resolves them as own keys."""
    f = []
    panel = body(src, "renderPipelinePanel").replace(" ", "")
    if "escapeAttr(key)" not in panel:
        f.append("the operator <option> does not carry the closed table's KEY escaped as an "
                 "attribute -- that key is what pipelineSetOp() resolves by hasOwnProperty")
    if "PIPE_OPERATOR_KEYS" not in panel:
        f.append("the picker does not iterate the declared key order, so it would inherit "
                 "whatever key enumeration order the engine happens to give it")
    setter = body(src, "pipelineSetOp").replace(" ", "")
    if "hasOwnProperty.call(PIPE_OPERATORS,key)" not in setter:
        f.append("pipelineSetOp() does not resolve its argument as an OWN key of the closed "
                 "table: 'constructor', 'toString' and '__proto__' are not operators")
    return f


def _emitted_actions(src):
    return set(re.findall(r'data-pipe-action=\\"([a-z]+)\\"', body(src, "renderPipelinePanel")))


def _routed_actions(src):
    return set(re.findall(r'pact==="([a-z]+)"', src))


def _emitted_fields(src):
    return set(re.findall(r'data-pipe-field=\\"([a-z]+)\\"', body(src, "renderPipelinePanel")))


def _routed_fields(src):
    routed = set(re.findall(r'pname==="([a-z]+)"', body(src, "onFieldChange")))
    routed |= set(re.findall(r'field==="([a-z]+)"', body(src, "pipelineSetField")))
    return routed


def audit_no_dead_controls(src):
    """Claim 3: emitted and routed are the same set, both directions, both kinds."""
    f = []
    ea, ra = _emitted_actions(src), _routed_actions(src)
    ef, rf = _emitted_fields(src), _routed_fields(src)
    if len(ea) < 5 or len(ef) < 4:
        f.append("the panel emits almost no controls (%d actions, %d fields) -- this audit has "
                 "stopped reading what it thinks it reads" % (len(ea), len(ef)))
    if sorted(ea - ra):
        f.append("these pipeline buttons are rendered but no click handler acts on them, so they "
                 "do nothing when pressed: %s" % sorted(ea - ra))
    if sorted(ra - ea):
        f.append("the click router handles pipeline verbs no control emits, so nothing in this "
                 "build can reach them: %s" % sorted(ra - ea))
    if sorted(ef - rf):
        f.append("these pipeline inputs are rendered but no handler reads them, so editing them "
                 "changes nothing: %s" % sorted(ef - rf))
    if sorted(rf - ef):
        f.append("the field router handles pipeline fields no control emits: %s" % sorted(rf - ef))
    return f


def audit_free_text_is_a_path_and_an_integer(src):
    """Claim 6: exactly two typed fields, each with a validateField() type behind it."""
    panel = body(src, "renderPipelinePanel")
    texts = set()
    for m in re.finditer(r'type=\\"text\\"(.{0,200}?)data-pipe-field=\\"([a-z]+)\\"', panel, re.S):
        texts.add(m.group(2))
    for m in re.finditer(r'data-pipe-field=\\"([a-z]+)\\"(.{0,200}?)maxlength=', panel, re.S):
        texts.add(m.group(1))
    if texts != {"target", "maxargs"}:
        return ["the pipeline panel's free-text inputs are %s. Only the redirect target "
                "(validateField 'path') and the xargs batch size (validateField 'integer') may be "
                "typed; everything else in a pipeline is structure the tool owns" % sorted(texts)]
    return []


def audit_the_closed_set(src):
    """Claim 4: the table, the picker order and the emission allow-list agree."""
    f = []
    table = re.search(r"var PIPE_OPERATORS=\{(.*?)\n\};", src, re.S)
    if table is None:
        return ["no PIPE_OPERATORS table in the source"]
    keys = set(re.findall(r"^\s*([a-z_]+)\s*:\s*\{", table.group(1), re.M))
    order = re.search(r"var PIPE_OPERATOR_KEYS=\[(.*?)\];", src, re.S)
    if order is None:
        return ["no PIPE_OPERATOR_KEYS list in the source"]
    offered = set(re.findall(r'"([a-z_]+)"', order.group(1)))
    if keys != offered:
        f.append("the operator table and the picker's key order disagree: %s are in the table and "
                 "not offered, %s are offered and not in the table"
                 % (sorted(keys - offered), sorted(offered - keys)))
    if len(keys) != 10:
        f.append("the closed operator set is %d operators, not the ten this product documents. "
                 "Widening the set is a decision, not a diff" % len(keys))
    emits = set(re.findall(r'emit:"([^"]*)"', table.group(1)))
    allowed = re.search(r"var PIPE_OPERATOR_EMITS=\[(.*?)\];", src, re.S)
    if allowed is None:
        return f + ["no PIPE_OPERATOR_EMITS allow-list in the source"]
    listed = set(re.findall(r'"([^"]*)"', allowed.group(1)))
    if emits != listed:
        f.append("the table emits %s and the allow-list permits %s. pipeOperator() fails closed on "
                 "a row whose emit is not listed, so a mismatch is an operator that silently "
                 "cannot be used" % (sorted(emits), sorted(listed)))
    return f


def audit_one_sink_one_writer(src):
    """Claim 5: exactly one function writes #pipeline-panel, and renderAll() draws it."""
    f = []
    if 'id="pipeline-panel"' not in src:
        f.append("the #pipeline-panel sink is missing from the document")
    writers = set()
    for m in re.finditer(r'el\("pipeline-panel"\)', src):
        fn = src.rfind("\nfunction ", 0, m.start())
        if fn < 0:
            writers.add("(top level)")
            continue
        writers.add(re.match(r"\nfunction\s+([A-Za-z0-9_]+)", src[fn:fn + 80]).group(1))
    if writers != {"renderPipelinePanel"}:
        f.append("#pipeline-panel is reached by %s. One sink, one writer: a second render path "
                 "into this panel is a second escaping story to keep in step (Q17)"
                 % sorted(writers))
    if "renderPipelinePanel();" not in body(src, "renderAll"):
        f.append("renderAll() does not draw the pipeline panel, so a version change or a rail "
                 "change would leave the stage list showing the previous state")
    return f


def audit_every_rendered_value_is_escaped(src):
    """Q19's narrow sibling: the panel uses the escapers it is supposed to use."""
    panel = body(src, "renderPipelinePanel")
    bare = re.findall(r"html\+=[^;]*?\+\s*(row\.[a-z]+|d\.[a-z]+)(?!\s*\))", panel)
    if bare:
        return ["these stage values are concatenated into the panel's HTML without an escaper: %s"
                % bare]
    return []


AUDITS = (
    ("operator text stays text", audit_operator_text_stays_text),
    ("the picker hands back a key", audit_the_picker_hands_back_a_key),
    ("no dead controls, no unreachable verbs", audit_no_dead_controls),
    ("free text is a path and an integer", audit_free_text_is_a_path_and_an_integer),
    ("the closed operator set", audit_the_closed_set),
    ("one sink, one writer", audit_one_sink_one_writer),
    ("every rendered value is escaped", audit_every_rendered_value_is_escaped),
)


class ThePanelAsShipped(unittest.TestCase):
    """The positive case: template.html passes every audit."""

    def test_every_audit_is_clean(self):
        for name, fn in AUDITS:
            with self.subTest(audit=name):
                self.assertEqual(fn(SRC), [], "%s: %s" % (name, fn(SRC)))


class TheAuditsAreShownToFail(unittest.TestCase):
    """PL5: a rule nobody has proved fires does not exist.

    Each control mutates the REAL source in exactly the way the audit exists to
    catch, and fails if the audit still calls the file clean.
    """

    def assertCatches(self, fn, mutated, what):
        self.assertNotEqual(fn(mutated), [],
                            "the audit passed a file in which %s -- it is not checking what its "
                            "name claims" % what)

    def test_an_operator_rendered_into_a_value_is_caught(self):
        bad = SRC.replace('html+="<option value=\\""+escapeAttr(key)+"\\""',
                          'html+="<option value=\\""+escapeAttr(PIPE_OPERATORS[key].emit)+"\\""')
        self.assertNotEqual(bad, SRC, "the control did not patch anything -- the panel's option "
                                      "markup changed and this control is now inert")
        self.assertCatches(audit_operator_text_stays_text, bad,
                           "the operator's emitted TEXT is the option's value")

    def test_a_setter_that_carries_operator_text_is_caught(self):
        setter = body(SRC, "pipelineSetOp")
        bad = SRC.replace(setter, setter.replace("var was=STATE.pipeline[i];",
                                                 "var was=STATE.pipeline[i];"
                                                 "var t=PIPE_OPERATORS[key].emit;"))
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_operator_text_stays_text, bad,
                           "pipelineSetOp() lifts operator text out of the table")

    def test_a_button_the_router_does_not_handle_is_caught(self):
        bad = SRC.replace('data-pipe-action=\\"clear\\"', 'data-pipe-action=\\"wipe\\"', 1)
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_no_dead_controls, bad, "a rendered button's verb is unrouted")

    def test_a_verb_no_control_emits_is_caught(self):
        bad = SRC.replace('if(pact==="clear"){ pipelineClear(); return; }',
                          'if(pact==="clear"){ pipelineClear(); return; }\n'
                          '    if(pact==="detonate"){ pipelineClear(); return; }')
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_no_dead_controls, bad, "the router handles an unreachable verb")

    def test_an_input_no_handler_reads_is_caught(self):
        bad = SRC.replace('data-pipe-field=\\"target\\"', 'data-pipe-field=\\"filename\\"')
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_no_dead_controls, bad, "a rendered input is read by no handler")

    def test_a_third_free_text_field_is_caught(self):
        panel = body(SRC, "renderPipelinePanel")
        bad = SRC.replace(panel, panel.replace(
            'html+="</div>";\n    }\n    if(!d.ok&&d.reason)',
            'html+="<input type=\\"text\\" data-pipe-field=\\"extra\\" maxlength=\\"99\\">";'
            'html+="</div>";\n    }\n    if(!d.ok&&d.reason)', 1))
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_free_text_is_a_path_and_an_integer, bad,
                           "a third free-text field with no validator behind it was added")

    def test_a_key_the_table_does_not_have_is_caught(self):
        bad = SRC.replace('"err_to_out","tee","tee_append"];',
                          '"err_to_out","tee","tee_append","exec"];', 1)
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_the_closed_set, bad,
                           "the picker offers a key the operator table does not define")

    def test_an_emit_outside_the_allow_list_is_caught(self):
        bad = SRC.replace('tee_append:  {emit:"| tee -a",', 'tee_append:  {emit:"| sh",', 1)
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_the_closed_set, bad,
                           "a table row emits something the allow-list does not permit")

    def test_a_second_writer_into_the_sink_is_caught(self):
        bad = SRC.replace("function renderEditor(){\n  var html=\"\";",
                          "function renderEditor(){\n  var html=\"\";\n"
                          "  if(false) el(\"pipeline-panel\").innerHTML=\"\";", 1)
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_one_sink_one_writer, bad,
                           "a second function writes the pipeline sink")

    def test_a_panel_renderAll_never_calls_is_caught(self):
        bad = SRC.replace("  renderPipelinePanel();       /* CR-T-31", "  /* CR-T-31", 1)
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_one_sink_one_writer, bad,
                           "renderAll() no longer draws the panel")

    def test_an_unescaped_stage_value_is_caught(self):
        panel = body(SRC, "renderPipelinePanel")
        bad = SRC.replace(panel, panel.replace(
            'html+="<div class=\\"stagelist\\">";',
            'html+="<div class=\\"stagelist\\">"+row.target;', 1))
        self.assertNotEqual(bad, SRC)
        self.assertCatches(audit_every_rendered_value_is_escaped, bad,
                           "a stage value reaches the sink with no escaper")


if __name__ == "__main__":
    unittest.main()
