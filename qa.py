#!/usr/bin/env python3
"""qa.py — the MD CODE RED QA gate. Exits non-zero on any FAIL.

Stdlib only.

    python3 qa.py              # every gate, Q1..Q21, one PASS/FAIL line each
    python3 qa.py --accuracy   # Q10 + Q11 only (the STIG/CCI accuracy re-check)
    python3 qa.py --size       # the size report only — informational, never fails

Gate numbering follows ADR-001 §7.3 (Q1..Q17). Q1..Q7 come from grey-beard-ansible
qa.py, Q8..Q11 from the Etsy RHEL STIG pipeline's qa-rhel-stig.py (this file keeps
its own independent XCCDF parse on purpose: the accuracy gate is worth nothing if
it re-uses the extractor's code path), Q12..Q17 are new for MD CODE RED.

Q18 through Q21 are beyond ADR-001's list. Q18 is Marcus's CI merge-gate #4 and #9
(threat-model-v1 §11), the hostile-input harness over the command assembler and
the quoting-domain separation check. Q19 closes AL-GATE3-001 from Al Kowalski's
BQP Gate 3 review: Q17 proves esc()/escapeAttr() are CALLED at every render
sink and cannot prove they ESCAPE anything, so Q19 lifts them out of the shipped
artifact and RUNS them against a hostile corpus. Both REQUIRE Node — see
gate_q18 and gate_q19 for why a skip is not acceptable in either.

Q20 is MCR-SEC-020 and MCR-SEC-019 (condition E5 of Marcus Reed's D4 review):
the flag dictionary measured against the raw captures it was extracted from, and
every generator citation checked to show an option that generator actually
emits. Q15 cannot see either, because it re-runs the extractor and diffs the
output against itself — a systematically skipped option class produces a
byte-identical re-parse and a PASS.

Q21 scans TRACKED SOURCE FILES for raw control, bidi and zero-width characters,
using the same TROJAN_RANGES table Q17 applies to the shipped artifact. Q17
proves what crosses the air gap is clean; Q21 proves the repository is. The
failure it exists for is not an attacker but an editor — see the block comment
above gate_q21.

SIZE IS REPORTED, NEVER ENFORCED. The Founder ruled the ceiling unlimited on
2026-09-17; ADR-001 §7.2's 8 MB ceiling is superseded. The size line prints MB
and cannot fail this gate or CI.

PENDING vs FAIL. A marker for a module that this build does not yet contain is
reported as PENDING with the task that owns it, and does not fail the gate. A
marker that should exist and does not is a FAIL. Nothing is quietly skipped.
"""

import hashlib
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(REPO, "dist")
CONTENT = os.path.join(REPO, "content")
STIG_SRC = os.path.join(REPO, "stig-src")
NS = {"x": "http://checklists.nist.gov/xccdf/1.1"}
CCI_NS = {"c": "http://iase.disa.mil/cci"}
VERSIONS = ("7", "8", "9", "10")

XCCDF = {
    "7": "U_RHEL_7_STIG_V3R15_Manual-xccdf.xml",
    "8": "U_RHEL_8_STIG_V2R8_Manual-xccdf.xml",
    "9": "U_RHEL_9_STIG_V2R9_Manual-xccdf.xml",
    "10": "U_RHEL_10_STIG_V1R2_Manual-xccdf.xml",
}
CCI_LIST = "U_CCI_List.xml"

# Deterministic sample: fixed stride, no RNG, reproducible in CI (ADR-001 §7.3 Q10).
SAMPLE_PER_RELEASE = 20
SAMPLE_STRIDE = 7

# Every extractor that writes into content/. Q15 re-runs each with --check and
# diffs the result against the committed files (ADR-001 §6.3).
GENERATORS = (
    "extract/parse_xccdf.py",            # rules_rhel{7,8,9,10}.json, cci_nist.json
    "extract/make_pending_skeletons.py",  # flags_rhel{7,8,9,10}.json (empty placeholders)
    "extract/import_captures.py",         # expected_output.json (CR-T-34, from tests/captures/)
)

# extract/extract_flags.py is re-run by Q15 too (below), but through its own
# --check --rhel <v> loop, not the generic GENERATORS loop above -- --rhel is
# required, so it cannot run under a bare --check the way the scripts above
# do. A FLAGS dataset is allowed to declare it as its generator (AL-GATE3-009):
# a dataset naming anything outside this combined set is naming a script Q15
# never re-runs, which is exactly the hand-edit-or-orphan state Q15 exists to
# catch.
FLAGS_GENERATOR = "extract/extract_flags.py"
RERUN_GENERATORS = GENERATORS + (FLAGS_GENERATOR,)

CDN_LITERALS = ("cdnjs", "jsdelivr", "unpkg", "googleapis", "gstatic", "cdn.")

# ---------------------------------------------------------------------------
# Feature markers (BQP Gate 2 check #7). "phase" names the task that adds a
# marker this build does not have yet; those report PENDING, never PASS.
# ---------------------------------------------------------------------------
MARKERS = [
    ("APP_NAME constant", 'var APP_NAME="', None),
    ("APP_VERSION constant", 'var APP_VERSION="', None),
    ("APP_BUILD_DATE constant", 'var APP_BUILD_DATE="', None),
    ("esc() definition", "function esc(", None),
    ("escapeAttr() definition", "function escapeAttr(", None),
    ("escapeRegex() definition", "function escapeRegex(", None),
    ("guarded storage module", "var STORE=(function(){", None),
    ("storage schema version", 'var SCHEMA=1;', None),
    ("theme module", "var THEME=(function(){", None),
    ("data-island loader", 'document.getElementById("mcr-data")', None),
    ("status bar renderer", "function renderStatusBar(", None),
    ("version state", "var STATE={version:", None),
    ("no-guess humility copy", "UNVERIFIED_FLAG_COPY", None),
    ("delegated click router", 'document.addEventListener("click"', None),
    ("RAIL region", 'id="rail"', None),
    ("SIDEBAR region", 'id="sidebar"', None),
    ("EDITOR region", 'id="editor"', None),
    ("INSPECTOR region", 'id="inspector"', None),
    ("STATUSBAR region", 'id="statusbar"', None),
    ("PALETTE overlay", 'id="palette"', None),
    ("print stylesheet", "@media print", None),
    # CR-T-13/14/15 — the runtime shell, the keyboard controller, the assembler
    ("rail renderer", "function renderRail(", None),
    ("tool list renderer (version-gated)", "function renderToolList(", None),
    ("editor renderer with gutter", "function renderEditor(", None),
    ("inspector renderer", "function renderInspector(", None),
    ("version-gated reason copy", "Not available in RHEL ", None),
    ("command assembler", "function assembleCommand(", None),
    ("assembler extraction markers", "MCR-ASSEMBLER-BEGIN", None),
    ("field type allow-list table", "var FIELD_TYPES=", None),
    ("field validator", "function validateField(", None),
    ("spec validator (which field is wrong)", "function validateSpec(", None),
    ("POSIX shell quoting", "function shQuote(", None),
    # MCR-SEC-010: the YAML quoter was dead code with no call site, so Q18's
    # quoting-domain gate passed on a domain that did not exist. It is removed
    # and reported PENDING until the Ansible generator gives it a real sink.
    ("YAML quoting (separate escaping domain)", "function yamlQuote(", "CR-T-17..25"),
    ("rich-rule composition from validated sub-fields", "function composeRichRule(", None),
    ("blast evaluation against the destructive table", "function blastFor(", None),
    ("red-blast confirmation banner", "function renderBlastBanner(", None),
    ("keyboard binding table", "var KEYMAP=", None),
    ("keyboard controller", 'document.addEventListener("keydown"', None),
    ("palette controller", "function openPalette(", None),
    ("palette search", "function paletteMatches(", None),
    ("clipboard (no network, no download)", "function copyText(", None),
    # MCR-SEC-012 / threat-model-v1 §9: the screen, the clipboard and the future
    # exporter read ONE rendered-state object, never four recomputations.
    ("single rendered-state object", "function computeResult(", None),
    ("clipboard payload composed once per interaction", "function withCopyPayloads(", None),
    ("clipboard header: every line '# '-prefixed", "function commentPayload(", None),
    ("de-quoted projection for the destructive table", "function unquoteCommand(", None),
    ("rich-rule slot allow-list", "var RICHRULE_SLOT_TYPES=", None),
    ("template flag/lit token allow-lists", "var FLAG_TOKEN_RE=", None),
    # later tranches — reported PENDING, never PASS, until their task lands
    ("generator registry", "var GENERATORS=", "CR-T-17..25"),
    ("flag decoder", "function decodeCmd(", "CR-T-17"),
    ("STIG panel", "function renderStigPanel(", None),
    ("evidence exporter", "function exportEvidence(", None),
    ("lazy typed search index", "function buildIndex(", None),
    # CR-T-26/28/29 support code, landed on the same branch
    ("content fingerprint constant", "var CONTENT_FINGERPRINT=", None),
    ("CCI to NIST crosswalk lookup", "function nistForCci(", None),
    ("typed search-index query", "function queryIndex(", None),
    ("evidence-export formatter (pure)", "function formatEvidenceText(", None),
    # CR-T-30
    ("favorites/recent id sanitizer (pure)", "function sanitizeIdList(", None),
    ("favorites toggle", "function toggleFavorite(", None),
    ("recent-list push", "function pushRecent(", None),
    ("favorites/recent sidebar", "function renderFavoritesSidebar(", None),
    ("print-only STIG mirror", 'id="print-stig-panel"', None),
    ("About panel", "function renderAbout(", None),
    ("attribution block (licensing ruling v1)", "var ATTRIBUTION_BLOCK=", None),
]

# ---------------------------------------------------------------------------
# innerHTML audit allow-list (ADR-001 §7.3 Q17, threat-model-v1 §11 item 3).
# An accumulator may appear bare on the right of an innerHTML assignment ONLY if
# it is named here AND every contribution to it is itself audited by this gate.
# ---------------------------------------------------------------------------
INNERHTML_ALLOWLIST = {
    'parts.join("")': "renderStatusBar(): every parts.push() argument is audited by this same gate",
}
AUDITED_PUSH_TARGETS = ["parts"]         # <name>.push(<expr>)

# ---------------------------------------------------------------------------
# Render-sink inventory (Q17, MCR-SEC-004).
#
# The audit used to look for one sink spelling — `.innerHTML =` — and one
# hard-coded accumulator name. Five mechanical bypasses followed from that:
# `+=` on the sink, `html = html + x` (assignment, not `+=`), an intermediate
# accumulator under any other name, insertAdjacentHTML(), and outerHTML. None of
# them existed in the code; all five passed the gate. The gate now (a) forbids
# the sinks this product has no use for outright, (b) derives the accumulator
# set from the source instead of hard-coding it, and (c) audits `=` and `+=`
# alike, on the sink and on every derived accumulator.
#
# These are FORBIDDEN, not audited: there is no correct use of them here, and a
# rule with no exception cannot be bypassed by writing the exception.
# ---------------------------------------------------------------------------
FORBIDDEN_SINKS = [
    (re.compile(r"\binsertAdjacentHTML\s*\("), "insertAdjacentHTML()"),
    (re.compile(r"\.\s*outerHTML\b"), ".outerHTML"),
    (re.compile(r"\bdocument\s*\.\s*write(?:ln)?\s*\("), "document.write()/document.writeln()"),
    (re.compile(r"\bcreateContextualFragment\s*\("), "Range.createContextualFragment()"),
    (re.compile(r"\bsrcdoc\s*="), "srcdoc="),
]
# `.innerHTML` may only ever appear as an assignment sink, never read into
# something else or passed anywhere.
INNERHTML_ANY_RE = re.compile(r"\.\s*innerHTML\b")
INNERHTML_SINK_RE = re.compile(r"\.\s*innerHTML\s*\+?=(?!=)\s*")
# setAttribute must name its attribute with a literal the gate can read, and that
# literal may not be one that turns a value into a URL, a style or a handler.
SETATTR_RE = re.compile(r"\.setAttribute\s*\(")
SETATTR_FORBIDDEN_RE = re.compile(r"^(href|src|srcdoc|style|action|formaction|xlink:href|on[a-z]+)$",
                                  re.I)
IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
JOIN_RE = re.compile(r"^([A-Za-z_$][A-Za-z0-9_$]*)\s*\.\s*join\s*\(")

# ---------------------------------------------------------------------------
# Computed member access (Q17, MCR-SEC-014).
#
# Every rule above is written against the DOT spelling of a property, so
# `el("x")["innerHTML"] = raw` was not a sink at all as far as this gate was
# concerned, and `el("x")["inner"+"HTML"] = raw` never spells the name in the
# source for any regex to find. Marcus Reed recorded the second one as an
# obfuscation residual — nobody splices a property name by accident — and said
# either closing it or writing the residual down was acceptable, but describing
# the gate as unbypassable was not.
#
# It is closed, because the check turns out to be mechanical and has no false
# positive on the code it guards. The gate does not try to search harder for a
# name that was deliberately taken apart; it refuses a computed property
# assignment whose property expression it cannot READ:
#
#   allowed   obj[i]  obj[key]  obj[0]  out[fields[i].name]  seen[seen.length]
#             — an identifier, a number, or a dotted/indexed chain. None of
#               these spells a sink name in the source, and all of them are
#               shapes template.html actually writes (fieldTypeMap(),
#               validateSpec()), so the rule costs the product nothing.
#   refused   obj["innerHTML"]        the sink, by its other spelling
#             obj["inner"+"HTML"]     a property expression built from pieces
#             obj[k] where k = "inner"+"HTML"   — the splice is caught where it
#               is written, by the fusion rule below, and again by following the
#               assignments to `k` the way accumulators are followed, which also
#               catches the name built across two statements.
#
# What this does NOT catch, said plainly rather than left for the next reviewer
# to find: a property name produced at run time from something that is not a
# string literal — characters from a code-point array, a value read out of the
# content island. No scan of the source can see those, and this gate does not
# claim to. Q17 exists so the next render path somebody writes by hand during
# CR-T-25/26/27/30 cannot become an XSS path by accident, over code CODEOWNERS
# reviews; it is not a sandbox and a determined author with commit rights was
# never inside its threat model (MCR-SEC-014, condition D2).
# ---------------------------------------------------------------------------
PROPERTY_SINK_NAME_RE = re.compile(
    r"^(innerHTML|outerHTML|srcdoc|href|src|style|action|formaction|xlink:href|on[a-z]+)$", re.I)
# A property expression the gate can read: identifier, number, or a dotted /
# bracketed chain of them. No string literal, no template literal, no operator.
READABLE_PROPERTY_RE = re.compile(r"^[A-Za-z_$0-9][A-Za-z0-9_$.\[\]]*$")
STRING_LIT_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"' + r"|'(?:[^'\\\n]|\\.)*'")
_TERM = r"""(?:"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|[A-Za-z_$][A-Za-z0-9_$.]*)"""
CONCAT_CHAIN_RE = re.compile(r"%s(?:\s*\+\s*%s)+" % (_TERM, _TERM))
# What a spliced name is not allowed to spell, once the non-literal terms are
# dropped and the literal pieces are fused together.
SPLICED_SINK_RE = re.compile(r"(innerHTML|outerHTML|srcdoc|insertAdjacentHTML|createContextualFragment)",
                             re.I)

# ---------------------------------------------------------------------------
# Trojan-source scan (Q17). Raw C0/C1 controls and invisible or bidirectional
# formatting characters do not belong in hand-written source: they are how a
# reviewer is shown one thing while the engine compiles another, and they are
# also how a JS \u escape silently turns into the character it was meant to
# describe. The ranges are assembled from code points rather than typed, because
# typing them is the mistake this gate exists to catch.
# ---------------------------------------------------------------------------
TROJAN_RANGES = [
    (0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F), (0x7F, 0x9F),   # C0 and C1, keeping \t \n \r
    (0xAD, 0xAD), (0x34F, 0x34F), (0x61C, 0x61C),             # soft hyphen, CGJ, Arabic letter mark
    (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180E),
    (0x200B, 0x200F), (0x2028, 0x2029), (0x202A, 0x202E),     # zero-width, line/paragraph
                                                              #   separators, bidi overrides
    (0x2060, 0x206F),                                         # word joiner, invisible format
                                                              #   and bidi isolates, 2065
                                                              #   included (MCR-SEC-009)
    (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0),
]
TROJAN_RE = re.compile("[" + "".join("%s-%s" % (chr(a), chr(b)) for a, b in TROJAN_RANGES) + "]")

results = []   # (gate_id, name, status, details)  status in PASS/FAIL/PENDING


def record(gid, name, failures, details=None, pendings=None):
    status = "FAIL" if failures else "PASS"
    results.append((gid, name, status, list(details or []), list(failures), list(pendings or [])))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def clean(s):
    if s is None:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s.replace("\r\n", "\n")).strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_artifact():
    """The ONE artifact qa.py gates: the exact filename build.py's own
    APP_VERSION names -- never whatever a directory listing happens to sort
    last.

    AL-GATE3-001-class fail-open (DECISION_LOG 2026-09-17/18, three dist/
    incidents this cycle). The old implementation globbed dist/ for anything
    matching `md-code-red_*.html` and took `sorted(...)[-1]`. That is
    fail-open in the dangerous direction: a stale artifact left behind by an
    old branch, a hand copy, or a sidecar export, if it merely sorted last
    AND carried the CURRENT version string, would be gated and PASS instead
    of the fresh build -- every downstream check only reads the file it was
    handed and has no way to ask whether it is the file build.py just wrote.
    Deriving the name from APP_VERSION instead of the directory listing closes
    that off structurally: there is exactly one filename this function will
    ever return for a given build.py, and a stale file cannot become it no
    matter how it is named, dated, or sorted.

    Returns the path if that exact file exists, else None -- callers that
    treat this as "is there a build to gate" (most of tests/) keep working
    unchanged. dist_integrity_failures() is the separate check for whether
    dist/ is clean enough to gate it at all.
    """
    version = load_build_constants().get("APP_VERSION")
    if not version:
        return None
    path = os.path.join(DIST, "md-code-red_%s.html" % version)
    return path if os.path.exists(path) else None


def newest_source_mtime():
    """The newest mtime among build.py's declared inputs: build.py itself,
    template.html, and every file in content/ (ADR-001 section 4's CONTENT
    map -- the same directory load_content() reads to assemble the island).

    This is the mtime half of AL-GATE3-001's fail-open: a correctly-NAMED
    artifact that simply was not rebuilt after content/ or template.html
    changed would pass find_artifact() and every content check that only
    reads the file it was handed, because none of them compare the artifact
    against the tree it should have come from. Returns (mtime, path) of the
    newest input found, or (None, None) if none of the expected inputs exist
    (a scratch dist/ with no repo around it, in a test).
    """
    candidates = [os.path.join(REPO, "build.py"), os.path.join(REPO, "template.html")]
    if os.path.isdir(CONTENT):
        candidates.extend(os.path.join(CONTENT, f) for f in sorted(os.listdir(CONTENT)))
    stats = [(os.path.getmtime(p), p) for p in candidates if os.path.exists(p)]
    if not stats:
        return None, None
    return max(stats)


def dist_integrity_failures():
    """Refuse a dirty dist/ by name, and a stale-but-correctly-named
    artifact by mtime -- the two halves of AL-GATE3-001 that find_artifact()
    alone cannot close (it only ever returns ONE path; it says nothing about
    what else is sitting next to it, or whether that one path is fresh).

    DECISION_LOG 2026-09-17/18: three incidents from one root cause, two
    false FAILs and one push-before-read. A dirty dist/ is now a hard
    refusal, named, with the cleanup command spelled out -- not a silent
    pass and not a guess at which file to gate.

    Returns a list of failure strings; empty means dist/ is clean enough to
    proceed. Callers exit non-zero on any entry (build_ctx() does; a build
    step should too before it hands dist/ to anything downstream).
    """
    out = []
    if not os.path.isdir(DIST):
        return out
    consts = load_build_constants()
    version = consts.get("APP_VERSION")
    if not version:
        return out  # find_artifact() already reports this failure mode
    expected_name = "md-code-red_%s.html" % version
    # The artifact's OWN sidecars belong next to it -- build.py writes
    # <expected_name>.sha256 itself, and extract/make_provenance.py writes
    # <version>.provenance.json -- so only a stray whose name is NOT one of
    # these three is a hazard, never the build's own paperwork.
    allowed = {expected_name, expected_name + ".sha256", "md-code-red_%s.provenance.json" % version}
    entries = sorted(os.listdir(DIST))
    strays = [f for f in entries
              if f not in allowed and f.startswith("md-code-red_")
              and (f.endswith(".html") or f.endswith(".sha256") or f.endswith(".provenance.json"))]
    if strays:
        out.append(
            "dist/ contains %d file(s) besides the current build's %s: %s. A stale "
            "artifact or sidecar sitting next to the real one is exactly what let a "
            "QA gate validate a file build.py did not just produce (AL-GATE3-001; "
            "DECISION_LOG 2026-09-17/18, three incidents this cycle). Clean dist/ "
            "before gating it: `git clean -fdx dist` or `rm -rf dist && python3 build.py`."
            % (len(strays), expected_name, ", ".join(strays)))
    expected_path = os.path.join(DIST, expected_name)
    if os.path.exists(expected_path):
        newest_mtime, newest_path = newest_source_mtime()
        if newest_mtime is not None and os.path.getmtime(expected_path) < newest_mtime:
            out.append(
                "dist/%s is older than %s -- the artifact predates its own build input, "
                "so it cannot be what building the current tree would produce. Rebuild: "
                "`rm -rf dist && python3 build.py`."
                % (expected_name, os.path.relpath(newest_path, REPO)))
    return out


def load_build_constants():
    """Read APP_NAME/APP_VERSION out of build.py without importing it."""
    with open(os.path.join(REPO, "build.py"), encoding="utf-8") as fh:
        src = fh.read()
    out = {}
    for key in ("APP_NAME", "APP_VERSION", "CLASSIFICATION"):
        m = re.search(r'^%s\s*=\s*"([^"]+)"' % key, src, re.M)
        out[key] = m.group(1) if m else None
    return out


SCHEMA_PATH = os.path.join(REPO, "extract", "schema.py")


def parse_schema_tuple(src, name):
    """A module-level tuple of string literals out of extract/schema.py's TEXT.

    AL-GATE3-005. Q3 re-checks provenance at the artifact level, independently of
    the extractor — that independence is the same rule Q10's docstring states for
    the XCCDF parse, and it is worth keeping. What is not worth keeping is Q3
    ALSO carrying its own idea of which fields are required, because that copy
    silently drifted: qa.py wanted four fields, extract/schema.py wanted five,
    and the missing one was `version`, the field schema.py's own docstring calls
    mandatory because "a source that cannot say which version of the document it
    came from cannot be re-checked".

    So: the CONSTANT is shared, the CHECK is not. It is read out of the file the
    same way load_build_constants() reads APP_VERSION out of build.py, with no
    import and no code path in common.

    Raises rather than returning a default. A gate that falls back to an idea of
    its own when it cannot read the source of truth is the weaker-copy problem
    again, with extra steps.
    """
    m = re.search(r"^%s\s*=\s*\(([^)]*)\)" % re.escape(name), src, re.M)
    if not m:
        raise ValueError("extract/schema.py declares no module-level %s tuple that qa.py can "
                         "read — Q3's independent re-check has no source of truth for which "
                         "fields are required (AL-GATE3-005)" % name)
    fields = tuple(re.findall(r"""["']([^"']+)["']""", m.group(1)))
    if not fields:
        raise ValueError("extract/schema.py's %s is empty — an empty requirement list is a gate "
                         "that requires nothing (AL-GATE3-005)" % name)
    return fields


def provenance_fields():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return parse_schema_tuple(f.read(), "PROVENANCE_FIELDS")


def license_classes():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return parse_schema_tuple(f.read(), "LICENSE_CLASSES")


def parse_provenance_fields(src):
    """parse_schema_tuple(src, "PROVENANCE_FIELDS"), kept as its own name for tests."""
    return parse_schema_tuple(src, "PROVENANCE_FIELDS")


def split_top_level(expr, sep="+"):
    """Split a JS expression on a top-level operator, respecting strings/parens."""
    parts, buf, depth, quote, i = [], "", 0, None, 0
    while i < len(expr):
        c = expr[i]
        if quote:
            buf += c
            if c == "\\":
                if i + 1 < len(expr):
                    buf += expr[i + 1]
                    i += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            buf += c
        elif c in "([{":
            depth += 1
            buf += c
        elif c in ")]}":
            depth -= 1
            buf += c
        elif c == sep and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += c
        i += 1
    parts.append(buf.strip())
    return [p for p in parts if p != ""]


def literal_end(seg):
    """Index of the quote that closes the string literal starting at seg[0], or None."""
    if not seg or seg[0] not in "\"'":
        return None
    quote, i = seg[0], 1
    while i < len(seg):
        c = seg[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i
        if c in "\n\r":
            return None            # a JS string literal cannot span a raw newline
        i += 1
    return None


def is_literal(seg):
    """True only for ONE complete string literal that closes at its last character.

    MCR-SEC-004(c). The old implementation compared seg[0] and seg[-1] only, so
    is_literal('"a" + raw + "b"') was True. That was not exploitable while
    split_top_level() splits on top-level '+' first — but a checker whose
    correctness depends on the splitter running first is one refactor away from
    being wrong, and this one guards the XSS path into a tool trusted at root.
    Template literals are rejected outright: interpolation is the thing this gate
    exists to catch.
    """
    seg = seg.strip()
    if seg.startswith("`"):
        return False
    end = literal_end(seg)
    return end is not None and end == len(seg) - 1


def segment_ok(seg, accumulators=()):
    seg = seg.strip()
    if not seg:
        return True
    if is_literal(seg):
        return True
    if re.match(r"^(esc|escapeAttr|escapeRegex)\s*\(", seg):
        return True
    if seg in accumulators:
        return True            # derived accumulator: its own assignments are audited
    if seg in INNERHTML_ALLOWLIST:
        return True
    if seg.startswith("(") and seg.endswith(")"):
        inner = seg[1:-1]
        if "?" in inner:
            cond, _, rest = inner.partition("?")
            branches = split_top_level(rest, ":")
            return all(segment_ok(b, accumulators) for b in branches)
        return segment_ok(inner, accumulators)
    return False


def expression_ok(expr, accumulators=()):
    return all(segment_ok(s, accumulators) for s in split_top_level(expr))


def assignments_to(src, name):
    """Every `<name> = ...` and `<name> += ...` expression in src.

    The lookbehind keeps `foo.html = x` and `myhtml = x` out; `(?!=)` keeps
    `==` out.
    """
    out = []
    pat = re.compile(r"(?<![.\w$])%s\s*\+?=(?!=)\s*" % re.escape(name))
    for m in pat.finditer(src):
        expr, _end = read_assignment(src, m.end())
        out.append(expr)
    return out


def sink_expressions(src):
    """Every expression assigned into an audited render sink (`=` and `+=`)."""
    out = []
    for m in INNERHTML_SINK_RE.finditer(src):
        expr, _end = read_assignment(src, m.end())
        out.append(expr)
    return out


def derive_accumulators(src):
    """Every identifier that reaches a render sink, transitively (MCR-SEC-004b).

    An accumulator is not a name this file knows in advance — it is whatever the
    source assigns into a sink. Start from the bare identifiers on the right of
    every sink assignment, then follow their own assignments: `var html = "" + h`
    makes `h` an accumulator too, so `h += entry.intent` is audited rather than
    invisible. Fixed point, so a chain of any length is covered.
    """
    queue, seen = [], set()
    for expr in sink_expressions(src):
        for seg in split_top_level(expr):
            seg = seg.strip()
            if IDENT_RE.match(seg):
                queue.append(seg)
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        for expr in assignments_to(src, name):
            for seg in split_top_level(expr):
                seg = seg.strip()
                if IDENT_RE.match(seg) and seg not in seen:
                    queue.append(seg)
    return seen


def computed_property_expressions(src):
    """Every `<expr>[<prop>] = ...` / `+= ...` in src, as (prop, context).

    The property expression is recovered by walking back from the `]` that
    precedes the `=`, matching brackets, so a nested index (`a[b[i]] = x`) is
    read whole rather than by a regex that stops at the first `[`.
    """
    out = []
    for m in re.finditer(r"\]\s*\+?=(?!=)", src):
        depth, j = 0, m.start()
        while j >= 0:
            if src[j] == "]":
                depth += 1
            elif src[j] == "[":
                depth -= 1
                if depth == 0:
                    break
            j -= 1
        if j < 0:
            continue                       # unbalanced: not an assignment we can read
        out.append((src[j + 1:m.start()].strip(), src[max(0, j - 30):m.end()].strip()))
    return out


def fused_literal_concatenations(src):
    """Every `+` chain containing a string literal, fused with the non-literal
    terms dropped: `"inner" + x + "HTML"` -> `innerHTML`.

    This is what makes a spliced property name visible at the place it is
    written, rather than at the place it is used (MCR-SEC-014).
    """
    out = []
    for m in CONCAT_CHAIN_RE.finditer(src):
        chunk = m.group(0)
        lits = STRING_LIT_RE.findall(chunk)
        if len(lits) < 2:
            continue
        out.append(("".join(l[1:-1] for l in lits), chunk))
    return out


def computed_member_expressions(src):
    """Every `<expr>[<prop>]` in src, as (prop, context) — reads as well as writes.

    computed_property_expressions() above only looks at ASSIGNMENTS, which is all
    Q17 needs: a render sink is written, never read. Q2 needs the other half. A
    network API is REACHED, and it can be reached by a read that never becomes a
    call on the same line (`var f = window["fe"+"tch"];`). The property is
    recovered by walking back from the `]` and matching brackets, so a nested
    index is read whole.
    """
    out = []
    for m in re.finditer(r"\]", src):
        depth, j = 0, m.start()
        while j >= 0:
            if src[j] == "]":
                depth += 1
            elif src[j] == "[":
                depth -= 1
                if depth == 0:
                    break
            j -= 1
        if j <= 0:
            continue                       # unbalanced, or an array literal at offset 0
        if src[j - 1] in " \t\r\n=(,:[{;+":
            continue                       # `[1,2]` is an array literal, not a member access
        out.append((src[j + 1:m.start()].strip(), src[max(0, j - 30):m.end()].strip()))
    return out


# ---------------------------------------------------------------------------
# Air-gap law: reaching the network without spelling its name (Q2).
#
# Q2 was a text scan: `fetch(`, `XMLHttpRequest`, `WebSocket`,
# `navigator.sendBeacon`, `import(`. Al Kowalski's Gate 3 review put it in the
# same structural class as the Q17 computed-member gap MCR-SEC-014 closed, but
# undocumented and untested rather than accepted and recorded — a computed call
# (`window["fe"+"tch"]()`) or an alias (`var f=fetch; f()`) is invisible to it.
#
# So the D2 rule, mirrored: a name spelled in brackets, a name fused inline out
# of string literals, and a name assembled through a variable across statements
# are all the name. Plus the shape Q17 does not need — the bare REFERENCE. A
# render sink is always written; a network API only has to be reached, and
# `var f = fetch;` never spells a call at all.
#
# What this does NOT catch is the same residual Q17 states rather than claims
# away: a name produced at run time from something that is not a string literal.
# No scan of the source can see that, and this gate does not pretend to. It is an
# accident-prevention gate over hand-written code CODEOWNERS reviews.
# ---------------------------------------------------------------------------
NETWORK_APIS = ("fetch", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon",
                "importScripts", "Worker", "SharedWorker", "RTCPeerConnection", "navigator")
NETWORK_NAME_RE = re.compile(r"(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|"
                             r"importScripts|SharedWorker|Worker|RTCPeerConnection)")
NETWORK_BARE_RE = re.compile(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|importScripts|"
                             r"SharedWorker|Worker|RTCPeerConnection)\b|"
                             r"\bnavigator\s*\.\s*sendBeacon\b|\bimport\s*\(")


def network_call_failures(script):
    """Every route from this app script to a network API. Returns a list of failures.

    Pure: takes JavaScript, returns strings. gate_q2 and
    tests/test_airgap_and_markers.py both call it.
    """
    f = []
    masked = mask_js_literals(script)

    # 1. The name, written out, anywhere in real code — a CALL is not required.
    #    `var f = fetch;` is the whole of the bypass, and the call site that
    #    follows it need not be in this file's line of sight.
    seen = set()
    for m in NETWORK_BARE_RE.finditer(masked):
        name = m.group(0).strip()
        if name in seen:
            continue
        seen.add(name)
        f.append("network-capable API '%s' is named in the app script at line %d. This product "
                 "ships one HTML file because it runs where there is no route off the machine; "
                 "there is no correct reference to a network API in it, called or not"
                 % (name, masked[:m.start()].count("\n") + 1))

    # 2. The name in brackets, or built out of literals — MCR-SEC-014's D2 rule,
    #    applied to the air gap instead of to the render sinks.
    for prop, context in computed_member_expressions(script):
        if is_literal(prop):
            hit = NETWORK_NAME_RE.search(prop[1:-1])
            if hit:
                f.append("computed member access naming '%s' — `window[\"fetch\"]` is the same "
                         "API as `window.fetch`, written the other way round, and every text scan "
                         "here reads the dotted spelling: %s" % (hit.group(0), context[:70]))
            continue
        if IDENT_RE.match(prop):
            lits = []
            for expr in assignments_to(script, prop):
                lits.extend(l[1:-1] for l in STRING_LIT_RE.findall(expr))
            hit = NETWORK_NAME_RE.search("".join(lits))
            if hit:
                f.append("computed member access `[%s]` where the source builds '%s' into '%s' "
                         "from string literals — an API name assembled across statements is still "
                         "that API's name: %s" % (prop, hit.group(0), prop, context[:70]))
            continue
        # A property expression that is neither one literal nor one identifier:
        # fuse every literal it contributes, plus every literal assigned to each
        # identifier term, and read the result. `window["fe"+part]` with
        # `part="tch"` elsewhere spells the API name across two places at once.
        pieces = []
        for seg in split_top_level(prop):
            seg = seg.strip()
            if is_literal(seg):
                pieces.append(seg[1:-1])
            elif IDENT_RE.match(seg):
                for expr in assignments_to(script, seg):
                    pieces.extend(l[1:-1] for l in STRING_LIT_RE.findall(expr))
        hit = NETWORK_NAME_RE.search("".join(pieces))
        if hit:
            f.append("computed member access whose property expression (%s) fuses to '%s' out of "
                     "string literals in this file — splitting an API name over a literal and a "
                     "variable is still spelling it: %s" % (prop[:40], hit.group(0), context[:70]))

    # 3. Any concatenation of string literals that spells one, wherever it sits.
    for fused, chunk in fused_literal_concatenations(script):
        hit = NETWORK_NAME_RE.search(fused)
        if hit:
            f.append("a concatenation of string literals spells '%s' (%s) — network API names are "
                     "not assembled from pieces in an air-gapped product"
                     % (hit.group(0), chunk[:70]))

    # 4. A CDN host built the same way, which the CDN_LITERALS scan cannot see.
    for fused, chunk in fused_literal_concatenations(script):
        low = fused.lower()
        for lit in CDN_LITERALS:
            if lit in low:
                f.append("a concatenation of string literals spells the CDN literal '%s' (%s)"
                         % (lit, chunk[:70]))
                break
    return f


def computed_sink_failures(src):
    """Q17's computed-member rule (MCR-SEC-014). Returns (failures, inspected)."""
    f, inspected = [], 0
    for prop, context in computed_property_expressions(src):
        inspected += 1
        if is_literal(prop):
            name = prop[1:-1]
            if PROPERTY_SINK_NAME_RE.match(name):
                f.append("computed member assignment to %r — `obj[\"innerHTML\"] = x` is the same "
                         "sink as `obj.innerHTML = x`, written the other way round, and every other "
                         "rule here reads the dotted spelling (MCR-SEC-014): %s"
                         % (name, context[:70]))
            continue
        if IDENT_RE.match(prop):
            # The property is a plain identifier — the shape ordinary map and
            # array code uses, so the form is not the problem. Follow what the
            # source assigns to it, the way derive_accumulators() follows an
            # accumulator, and fuse the literal pieces: a name built across two
            # statements (`k = "inner"; k += "HTML"`) is the last place this
            # splice had left to hide.
            lits = []
            for expr in assignments_to(src, prop):
                lits.extend(l[1:-1] for l in STRING_LIT_RE.findall(expr))
            hit = SPLICED_SINK_RE.search("".join(lits))
            if hit:
                f.append("computed member assignment `[%s]` where the source builds %s into '%s' "
                         "from string literals — a render-sink name assembled across statements is "
                         "still a render-sink name (MCR-SEC-014): %s"
                         % (prop, hit.group(0), prop, context[:70]))
            continue
        if not READABLE_PROPERTY_RE.match(prop):
            f.append("computed member assignment whose property expression this gate cannot read "
                     "(%s) — a property name built from pieces is how a render sink is reached "
                     "without ever spelling its name. Write the property out, or use an identifier "
                     "or index (MCR-SEC-014): %s" % (prop[:40], context[:70]))
    for fused, chunk in fused_literal_concatenations(src):
        inspected += 1
        hit = SPLICED_SINK_RE.search(fused)
        if hit:
            f.append("a concatenation of string literals spells %r (%s) — the render-sink names are "
                     "not assembled from pieces in this product (MCR-SEC-014)"
                     % (hit.group(0), chunk[:70]))
    return f, inspected


def render_sink_failures(src):
    """The whole Q17 render-safety audit over a piece of JS. Returns (failures, audited).

    Factored out of gate_q17 so tests/test_render_audit.py can drive it with the
    bypass constructs from MCR-SEC-004 and prove each one now fails. A gate that
    has never been seen to fail is not a gate.
    """
    f, audited = [], 0

    for rx, label in FORBIDDEN_SINKS:
        hits = len(rx.findall(src))
        if hits:
            f.append("%s appears %d time(s): this product renders through exactly one audited sink "
                     "(innerHTML, esc()-wrapped), and there is no correct use of this one here "
                     "(MCR-SEC-004)" % (label, hits))

    # `.innerHTML` may only be an assignment target
    for m in INNERHTML_ANY_RE.finditer(src):
        tail = src[m.end():m.end() + 8]
        if not re.match(r"\s*\+?=(?!=)", tail):
            f.append("`.innerHTML` used as something other than an assignment sink (followed by %r) "
                     "— every render path has to go through the audited assignment form" % tail)

    # setAttribute: the attribute name must be a readable literal, and not one
    # that turns its value into a URL, a style or an event handler.
    for m in SETATTR_RE.finditer(src):
        args, _end = read_assignment(src, m.end())
        first = split_top_level(args, ",")[0].strip() if args else ""
        if not is_literal(first):
            f.append("setAttribute() called with a non-literal attribute name (%s) — the gate cannot "
                     "prove it is not href/src/style/on*, so write the name out" % first[:40])
            continue
        name = first[1:-1]
        if SETATTR_FORBIDDEN_RE.match(name):
            f.append("setAttribute(%r, ...) — href/src/srcdoc/style/action/on* turn a string into a "
                     "URL, a stylesheet or a handler; this product sets data-* and ARIA only" % name)

    # computed member access: the other spelling of a property, and the spliced
    # name that spelling makes possible (MCR-SEC-014)
    computed_f, computed_n = computed_sink_failures(src)
    f.extend(computed_f)
    audited += computed_n

    accumulators = derive_accumulators(src)

    for expr in sink_expressions(src):
        audited += 1
        if not expression_ok(expr, accumulators):
            bad = [s for s in split_top_level(expr) if not segment_ok(s, accumulators)]
            f.append("innerHTML assignment is not esc()/escapeAttr()-wrapped or literal: %s"
                     % "; ".join(b[:70] for b in bad))

    for name in sorted(accumulators):
        exprs = assignments_to(src, name)
        if not exprs:
            f.append("'%s' is assigned into an innerHTML sink but nothing in this file assigns to it "
                     "in a form this gate can audit" % name)
        for expr in exprs:
            audited += 1
            if not expression_ok(expr, accumulators):
                bad = [s for s in split_top_level(expr) if not segment_ok(s, accumulators)]
                f.append("accumulator '%s' takes an unescaped segment: %s"
                         % (name, "; ".join(b[:70] for b in bad)))

    # allow-listed join() accumulators: the push target must itself be audited
    for expr in sink_expressions(src):
        for seg in split_top_level(expr):
            jm = JOIN_RE.match(seg.strip())
            if jm and jm.group(1) not in AUDITED_PUSH_TARGETS:
                f.append("'%s.join(...)' reaches a sink but '%s' is not an audited push target"
                         % (jm.group(1), jm.group(1)))

    for name in AUDITED_PUSH_TARGETS:
        for m in re.finditer(r"\b%s\.push\(" % re.escape(name), src):
            expr, _end = read_assignment(src, m.end())
            audited += 1
            if not expression_ok(expr, accumulators):
                bad = [s for s in split_top_level(expr) if not segment_ok(s, accumulators)]
                f.append("'%s.push()' takes an unescaped segment: %s"
                         % (name, "; ".join(b[:70] for b in bad)))

    return f, audited


def trojan_scan(text, where):
    """Raw C0/C1, zero-width and bidirectional-override characters, by code point.

    C10: this runs over the data island as well as the hand-written shell. DISA
    fix text is rendered AND copied into evidence blocks, so a bidi override in
    vendor XML is the textbook trojan-source case; excluding the island was a
    deliberate blind spot.
    """
    found = {}
    for m in TROJAN_RE.finditer(text):
        cp = ord(m.group(0))
        if cp in found:
            continue
        found[cp] = text[:m.start()].count("\n") + 1
    if not found:
        return []
    return ["raw control or invisible character(s) in %s: %s — source and embedded content are "
            "written with escapes, never with the character itself; a bidi override or a stray NUL "
            "is both a review-integrity hazard and how a \\u escape turns into the thing it meant "
            "to describe"
            % (where, ", ".join("U+%04X at line %d" % (cp, ln) for cp, ln in sorted(found.items())[:8]))]


def read_assignment(src, start):
    """Read a JS expression from `start` up to the terminating top-level ';'."""
    buf, depth, quote, i = "", 0, None, start
    while i < len(src):
        c = src[i]
        if quote:
            buf += c
            if c == "\\":
                if i + 1 < len(src):
                    buf += src[i + 1]
                    i += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            buf += c
        elif c in "([{":
            depth += 1
            buf += c
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
            buf += c
        elif c == ";" and depth == 0:
            break
        else:
            buf += c
        i += 1
    return buf.strip(), i


# ---------------------------------------------------------------------------
# JS lexical masking (AL-GATE3-001, AL-GATE3-003)
#
# Several gates need to know where the CODE is: Q7 brace-matches try{} blocks,
# Q19 brace-matches a function body out of the shipped file, Q5 asks whether a
# structural marker is real code rather than a word in a comment, and Q2 asks
# whether a network API is named in the script rather than in prose. All four
# were counting raw characters, and Al Kowalski's Gate 3 review reproduced what
# that costs: one unbalanced brace inside a string literal inside a try{} block
# desynced Q7's depth counter and absorbed a genuinely unguarded
# localStorage call into the span it rated "guarded" (AL-GATE3-003).
#
# mask_js_literals() answers the question once. It returns a copy of the source
# with the same length and the same line breaks, in which:
#
#   * a comment is blanked entirely, delimiters included;
#   * the CONTENTS of a string, template literal or regex literal are blanked,
#     and the delimiters are left in place.
#
# Keeping the delimiters is what lets Q5 still find a marker like `var APP_NAME="`
# (that trailing quote is the delimiter, not content) while a marker sitting
# INSIDE a string is gone. Blanking a template literal whole — interpolation
# included — is deliberate: `${...}` is code, but it carries braces, and dropping
# both halves keeps the brace count balanced, which is the property every caller
# here depends on.
#
# Same offsets in, same offsets out: a line number computed on the masked copy is
# the line number in the original.
# ---------------------------------------------------------------------------

# A '/' can only open a regex literal where a value cannot already have ended;
# anywhere else it is division. Same heuristic the comment stripper used.
REGEX_MAY_START_AFTER = "(,=:[!&|?{};+-*%~^"


def mask_js_literals(src):
    """Blank comment text and string/template/regex CONTENTS, preserving offsets."""
    out = list(src)
    n = len(src)

    def blank(a, b):
        for k in range(max(0, a), min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    i = 0
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c or src[j] in "\n\r":
                    break        # a JS string literal cannot span a raw newline
                j += 1
            blank(i + 1, j)
            i = min(j, n) + 1
            continue
        if c == "`":
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "`":
                    break
                j += 1
            blank(i + 1, j)
            i = min(j, n) + 1
            continue
        if c == "/":
            k = i - 1
            while k >= 0 and src[k] in " \t\r\n":
                k -= 1
            prev = src[k] if k >= 0 else ""
            if prev == "" or prev in REGEX_MAY_START_AFTER:
                j, in_class, closed = i + 1, False, False
                while j < n:
                    ch = src[j]
                    if ch == "\\":
                        j += 2
                        continue
                    if ch == "[":
                        in_class = True
                    elif ch == "]":
                        in_class = False
                    elif ch == "/" and not in_class:
                        closed = True
                        break
                    elif ch == "\n":
                        break
                    j += 1
                if closed:
                    blank(i + 1, j)
                    i = j + 1
                    continue
        i += 1
    return "".join(out)


def app_script_of(src):
    """The JavaScript to read: the last inline <script> of an HTML file, else src.

    Lets the escaper gate take a built artifact, template.html, or a bare
    fragment of JS, and read the same thing in each case. Masking an HTML file
    with a JS lexer would be wrong — an apostrophe in prose would open a string
    that never closes — so the JS is separated out first.
    """
    blocks = re.findall(r"<script>(.*?)</script>", src, re.S)
    return blocks[-1] if blocks else src


def extract_js_function(src, name):
    """The verbatim text of `function <name>(...){...}`. Returns (text, error).

    Brace-matched over the masked copy, so a brace inside a string, a regex or a
    comment cannot end the body early. Exactly one of the two return values is
    None.
    """
    masked = mask_js_literals(src)
    hits = list(re.finditer(r"\bfunction\s+%s\s*\(" % re.escape(name), masked))
    if not hits:
        return None, "no `function %s(` definition in the shipped file" % name
    if len(hits) > 1:
        return None, ("%d definitions of `function %s(` — the gate cannot tell which one the "
                      "render paths call, and neither can a reviewer" % (len(hits), name))
    m = hits[0]
    brace = masked.find("{", m.end())
    if brace < 0:
        return None, "`function %s(` has no body" % name
    depth = 0
    for i in range(brace, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():i + 1], None
    return None, ("`function %s(`'s body is never closed — the brace match ran off the end of "
                  "the file" % name)


# The three functions every rendered value in this product passes through. Q17
# proves they are CALLED; Q19 proves they ESCAPE.
ESCAPERS = ("esc", "escapeAttr", "escapeRegex")
ESCAPER_PROBE = os.path.join(REPO, "tests", "escaper_probe.js")
ESCAPER_CORPUS = os.path.join(REPO, "tests", "fixtures", "escaper-corpus.json")


def extract_escaper_block(src):
    """The three escaper definitions, lifted verbatim. Returns (text, error)."""
    script = app_script_of(src)
    parts, errs = [], []
    for name in ESCAPERS:
        text, err = extract_js_function(script, name)
        if err:
            errs.append("%s(): %s" % (name, err))
        else:
            parts.append(text)
    if errs:
        return None, "; ".join(errs)
    return "\n".join(parts) + "\n", None


def escaper_failures(src):
    """Q19 (AL-GATE3-001). Run the shipped escapers; do not read them.

    Returns (failures, details). Factored out of gate_q19 so
    tests/test_escaper_behaviour.py can drive it with a mutated escaper body and
    prove the gate sees what Q17 cannot.
    """
    f, d = [], []
    if not os.path.exists(ESCAPER_PROBE) or not os.path.exists(ESCAPER_CORPUS):
        f.append("tests/escaper_probe.js or tests/fixtures/escaper-corpus.json is missing — the "
                 "escaper property gate cannot run. An escaping check that quietly skips is the "
                 "fail-open this gate exists to close (AL-GATE3-001)")
        return f, d

    block, err = extract_escaper_block(src)
    if err:
        f.append("could not lift the escapers out of the shipped file: %s" % err)
        return f, d

    node = shutil.which("node")
    if not node:
        f.append("node is not installed on this runner. The escapers are JavaScript and this gate "
                 "RUNS them — reading them is what Q17 already does, and reading them is what "
                 "AL-GATE3-001 showed is not enough. CI installs Node (actions/setup-node@v4) so "
                 "this check cannot be skipped on the build that needed it.")
        return f, d

    tmp = tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8")
    try:
        tmp.write(block)
        tmp.close()
        proc = subprocess.run([node, ESCAPER_PROBE, tmp.name, "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        os.unlink(tmp.name)
    out = proc.stdout.decode("utf-8", "replace")
    err_text = proc.stderr.decode("utf-8", "replace").strip()
    try:
        rep = json.loads(out)
    except ValueError:
        f.append("the escaper probe produced no JSON report: %s" % (err_text or out)[:400])
        return f, d
    if not isinstance(rep, dict):
        f.append("the escaper probe's report is not an object: %s" % out[:200])
        return f, d
    for line in rep.get("failures", []):
        f.append("escaper property: %s" % line)
    if proc.returncode != 0 and not rep.get("failures"):
        f.append("the escaper probe exited %d without naming a failure: %s"
                 % (proc.returncode, err_text[:300]))
    checks = rep.get("checks", 0)
    if not f and not checks:
        f.append("the escaper probe reported zero checks — a battery with nothing in it passes "
                 "everything, which is the empty-set fail-open in a different costume")
    if not f:
        d.append("%d properties checked over %s declared and %s generated hostile vectors: esc() "
                 "leaves no raw < > \" ' and no bare &, escapeAttr() adds ` and =, and both "
                 "round-trip exactly through a strict entity decoder — so an escaper that DELETES "
                 "the dangerous character fails here too, rather than silently corrupting DISA "
                 "fix text"
                 % (checks, rep.get("vectors", "?"), rep.get("generated_vectors", "?")))
        d.append("escapeRegex(): every regex metacharacter present is backslash-escaped and none "
                 "is left bare; the pattern compiles, matches its own input, and does not match "
                 "what only the UNescaped pattern would match")
        d.append("%s negative control(s) ran first: the probe drives its own battery against "
                 "known-broken escapers (identity, drop-the-character, half-escaped) and refuses "
                 "to report a PASS unless it just failed all of them (AL-GATE3-001)"
                 % rep.get("negative_controls", "?"))
        d.append("escapers lifted verbatim out of the shipped file (%d bytes, %s), not read from "
                 "template.html and not re-implemented in Python"
                 % (rep.get("escaper_bytes", len(block)), ", ".join("%s()" % n for n in ESCAPERS)))
    return f, d


# ---------------------------------------------------------------------------
# independent source parses (never re-uses extract/)
# ---------------------------------------------------------------------------

def verify_pins():
    """Q10/Q11 precondition: the pinned XML must hash to stig-src/SHA256SUMS."""
    failures, details = [], []
    sums = {}
    path = os.path.join(STIG_SRC, "SHA256SUMS")
    if not os.path.exists(path):
        return ["stig-src/SHA256SUMS is missing — refusing to parse unpinned sources"], details
    with open(path, encoding="utf-8") as fh:
        sum_lines = fh.readlines()
    for line in sum_lines:
        line = line.strip()
        if line:
            digest, name = line.split(None, 1)
            sums[name.strip()] = digest
    for name in list(XCCDF.values()) + [CCI_LIST]:
        p = os.path.join(STIG_SRC, name)
        if not os.path.exists(p):
            failures.append("stig-src/%s missing" % name)
            continue
        got = sha256_file(p)
        if sums.get(name) != got:
            failures.append("stig-src/%s sha256 %s does not match the pin %s"
                            % (name, got[:16], (sums.get(name) or "?")[:16]))
        else:
            details.append("pin verified: %s (%s...)" % (name, got[:16]))
    return failures, details


def parse_source(version):
    """Re-parse a pinned XCCDF from scratch. Keyed by STIG ID."""
    root = ET.parse(os.path.join(STIG_SRC, XCCDF[version])).getroot()
    out, total = {}, 0
    for g in root.findall("x:Group", NS):
        rule = g.find("x:Rule", NS)
        if rule is None:
            continue
        total += 1
        ver = rule.find("x:version", NS)
        sid = clean(ver.text) if ver is not None else ""
        ccis = []
        for ident in rule.findall("x:ident", NS):
            if "cci" in (ident.get("system") or "").lower():
                val = (ident.text or "").strip()
                if val and val not in ccis:
                    ccis.append(val)
        chk_el = rule.find("x:check/x:check-content", NS)
        fix_el = rule.find("x:fixtext", NS)
        out[sid] = {
            "v": g.get("id"),
            "rid": rule.get("id"),
            "c": {"high": "I", "medium": "II", "low": "III"}.get(rule.get("severity"), "?"),
            "t": clean(rule.find("x:title", NS).text),
            "cci": ccis,
            "chk": clean(chk_el.text) if chk_el is not None else "",
            "fix": clean(fix_el.text) if fix_el is not None else "",
        }
    return out, total


def parse_cci_list():
    root = ET.parse(os.path.join(STIG_SRC, CCI_LIST)).getroot()
    out = {}
    for item in root.findall(".//c:cci_item", CCI_NS):
        best = None
        for ref in item.findall("c:references/c:reference", CCI_NS):
            title = ref.get("title") or ""
            if "800-53" not in title or "800-53A" in title:
                continue
            idx = (ref.get("index") or "").strip()
            if not idx:
                continue
            try:
                vnum = int(re.sub(r"\D", "", ref.get("version") or "0") or 0)
            except ValueError:
                vnum = 0
            if best is None or vnum > best[0]:
                best = (vnum, idx)
        out[item.get("id")] = best[1] if best else None
    return out


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------

def island_escape_failures(island):
    """MCR-SEC-007 — no HTML-significant character survives into the data island.

    Escaping only `</` closes `</script>` and leaves `<!--` and `<script` alone,
    which is enough to push the HTML tokeniser into script-data-double-escaped
    state and swallow the island's own closing tag along with the whole app
    script. build.py escapes every `<` and `>` as \\u003c / \\u003e; this asserts
    it on the built file, so reverting the escaping fails the build rather than
    waiting for a DISA fix text that happens to contain `<!--<script`.

    Returns a list of failure strings; empty means the island is clean.
    """
    out = []
    for ch, name in (("<", "less-than"), (">", "greater-than")):
        n = island.count(ch)
        if n:
            at = island.index(ch)
            out.append("the data island contains %d raw %s character(s) — first at offset %d, "
                       "context %r. build.py must escape every '<' and '>' as \\u003c / \\u003e so "
                       "'</script', '<!--', '-->' and '<script' are all closed by one rule "
                       "(MCR-SEC-007)" % (n, name, at, island[max(0, at - 30):at + 30]))
    return out


def empty_set_failure(what, why):
    """The one sentence AL-GATE3-004 asks every per-item gate to be able to say.

    Q9 has said it since CR-T-07 — "a release with no CAT I rules at all means
    the severity parse dropped them silently, which would make this gate pass by
    having nothing to check" — and Q11 has guarded `not embedded`. The reasoning
    was never specific to CAT I rules or to the CCI map: a loop that only records
    a failure when it finds something wrong WITH an item reports PASS on no items
    at all, which is the loudest possible silence.
    """
    return ("zero %s — %s. This gate finds a failure only by finding something wrong with an "
            "item, so an empty set passes it by having nothing to check; the emptiness is "
            "therefore the finding (AL-GATE3-004)" % (what, why))


def gate_q1(ctx):
    f, d = [], []
    html = ctx["html"]
    d.append("artifact: %s" % os.path.relpath(ctx["artifact"], REPO))
    for token, label in [("<!DOCTYPE html>", "DOCTYPE"), ("<html", "<html>"),
                         ("<head", "<head>"), ("<body", "<body>")]:
        if token.lower() not in html.lower():
            f.append("missing %s" % label)
    if not f:
        d.append("DOCTYPE/html/head/body present")
    scripts = re.findall(r"<script\b[^>]*>", html)
    if len(scripts) != 2:
        f.append("expected exactly 2 <script> elements, found %d" % len(scripts))
    else:
        if 'type="application/json"' not in scripts[0] or 'id="mcr-data"' not in scripts[0]:
            f.append("first <script> is not the id=mcr-data application/json data island")
        if "src=" in scripts[1] or "type=" in scripts[1]:
            f.append("second <script> is not a plain inline application script")
        d.append("exactly two <script> elements: one JSON data island, one app script "
                 "(BQP Gate 2 #2, declared deviation per ADR-001 §7.4)")
    if html.count("<script") != html.count("</script>"):
        f.append("unbalanced <script> open/close counts")
    if "/*__DATA__*/" in html:
        f.append("template placeholder /*__DATA__*/ was not replaced")
    for token in ("__VERSION__", "__BUILT_DATE__", "__APP_NAME__", "__CLASSIFICATION__"):
        if token in html:
            f.append("template token %s was not substituted" % token)
    data = ctx["data"]
    if data is None:
        f.append("data island does not parse as JSON")
    else:
        d.append("data island parses (%.2f MB of JSON)" % (ctx["island_len"] / 1024.0 / 1024.0))
    esc_f = island_escape_failures(ctx["island"])
    f.extend(esc_f)
    if not esc_f:
        d.append("no raw '<' or '>' anywhere in the data island — '</script', '<!--', '-->' and "
                 "'<script' are all closed by build.py's \\u003c/\\u003e escaping (MCR-SEC-007)")
    consts = ctx["build_consts"]
    version = consts.get("APP_VERSION")
    checks = [
        ("build.py APP_VERSION", version),
        ("island meta.version", (data or {}).get("meta", {}).get("version")),
        ("app script APP_VERSION constant",
         (re.search(r'var APP_VERSION="([^"]+)"', html) or [None, None])[1]),
        ("version comment block",
         (re.search(r"Version:\s*(\S+)", html) or [None, None])[1]),
        ("dist filename", os.path.basename(ctx["artifact"])[len("md-code-red_"):-len(".html")]),
    ]
    mismatched = [n for n, v in checks if v != version]
    if mismatched:
        f.append("version string mismatch (%s should all read %s): %s"
                 % (", ".join(n for n, _ in checks), version,
                    ", ".join("%s=%s" % (n, v) for n, v in checks if v != version)))
    else:
        d.append("version %s matches in all five places (comment block, APP_VERSION, "
                 "island meta, dist filename, build.py)" % version)
    built = (data or {}).get("meta", {}).get("built")
    if not built or ("Last modified:      %s" % built) not in html:
        f.append("build date missing or inconsistent between the comment block and the island")
    else:
        d.append("build date %s consistent" % built)
    side = ctx["artifact"] + ".sha256"
    if not os.path.exists(side):
        f.append("sha256 sidecar missing")
    else:
        with open(side, encoding="utf-8") as fh:
            want = fh.read().split()[0]
        got = sha256_file(ctx["artifact"])
        if want != got:
            f.append("sha256 sidecar %s does not match the artifact %s" % (want[:16], got[:16]))
        else:
            d.append("sha256 sidecar matches: %s" % got[:32])

    # CR-T-28/CR-T-30. The content fingerprint is defined as the sha256 of
    # exactly the bytes inside <script id="mcr-data">...</script> — the same
    # bytes this file already extracted as ctx["island"] — computed by
    # build.py BEFORE that payload was substituted into the template and
    # embedded as the CONTENT_FINGERPRINT constant, never inside the JSON
    # island itself (a hash inside the thing it hashes is circular). This is
    # the independent re-check: re-hash the shipped island and compare it to
    # the constant the shell actually carries, so the evidence exporter and
    # the About panel cannot print a fingerprint that does not match what
    # shipped.
    fp_m = re.search(r'var CONTENT_FINGERPRINT="([^"]*)"', html)
    if not fp_m or not fp_m.group(1) or fp_m.group(1) == "__CONTENT_FINGERPRINT__":
        f.append("CONTENT_FINGERPRINT constant is missing or unsubstituted in the shipped shell")
    elif not ctx["island"]:
        f.append("content fingerprint cannot be checked — the data island did not extract")
    else:
        want_fp = fp_m.group(1)
        got_fp = hashlib.sha256(ctx["island"].encode("utf-8")).hexdigest()
        if want_fp != got_fp:
            f.append("content fingerprint %s does not match a fresh sha256 of the shipped data "
                     "island %s — the embedded constant and the island have drifted"
                     % (want_fp[:16], got_fp[:16]))
        else:
            d.append("content fingerprint matches a fresh sha256 of the shipped data island: %s"
                     % got_fp[:32])
    return f, d


def gate_q2(ctx):
    f, d = [], []
    html, shell = ctx["html"], ctx["shell"]
    ext_script = re.findall(r"<script[^>]+src=", html)
    ext_css = re.findall(r'<link[^>]+rel=["\']?stylesheet', html)
    ext_link = re.findall(r"<link[^>]+href=[\"']?https?://", html)
    ext_img = re.findall(r"<img[^>]+src=[\"']?https?://", html)
    ext_media = re.findall(r"<(?:iframe|video|audio|source|embed|object)[^>]+(?:src|data)=", html)
    css_import = re.findall(r"@import|@font-face", html)
    css_url = [u for u in re.findall(r"url\(([^)]*)\)", html) if not u.strip().strip("\"'").startswith("data:")]
    http_srcs = re.findall(r"(?:src|href)=[\"']https?://[^\"']+", html)
    # Network-capable JS is scanned in the SHELL only: the data island is vendor
    # STIG prose and matching a word like "fetch" inside it is not a network call.
    net_js = re.findall(r"\b(fetch\s*\(|XMLHttpRequest|WebSocket|navigator\.sendBeacon|import\s*\()", shell)
    cdn = [lit for lit in CDN_LITERALS if lit in shell]
    # The text scans above read the DOTTED, written-out spelling and nothing
    # else. network_call_failures() reads the app script structurally: a
    # bracketed name, a name fused out of literals inline or through a variable,
    # a bare reference that is never called on the same line, and a CDN host
    # assembled the same way (Gate 3, Q2 row; MCR-SEC-014's D2 rule applied to
    # the air gap rather than to the render sinks).
    structural = network_call_failures(ctx["app_script"])
    f.extend(structural)
    for bad, msg in [(ext_script, "external <script src>"), (ext_css, "external stylesheet"),
                     (ext_link, "external <link href>"), (ext_img, "remote <img>"),
                     (ext_media, "embedded media element with a src/data attribute"),
                     (css_import, "CSS @import/@font-face"), (css_url, "non-data: url() in CSS"),
                     (http_srcs, "http(s) src/href"), (net_js, "network-capable JS call"),
                     (cdn, "CDN literal")]:
        if bad:
            f.append("%s found: %s" % (msg, list(bad)[:5]))
    if not f:
        d.append("no external script/stylesheet/link/img/media, no @import or @font-face, "
                 "no non-data url(), zero http(s) src/href")
        d.append("no fetch/XMLHttpRequest/WebSocket/sendBeacon/dynamic import in the app script")
        d.append("no CDN literals (%s)" % ", ".join(CDN_LITERALS))
        d.append("and none of them reached the other way round either: %d computed member "
                 "accesses in the app script read, no bracketed API name, no API name and no CDN "
                 "host fused out of string literals — inline, through a variable, or across "
                 "statements — and no bare reference to one, called or not. Residual, stated "
                 "rather than claimed away: a name produced at RUN TIME from something that is "
                 "not a string literal is invisible to any scan of the source, here exactly as in "
                 "Q17 (MCR-SEC-014)" % len(computed_member_expressions(ctx["app_script"])))
    return f, d


def gate_q3(ctx):
    f, d = [], []
    data = ctx["data"]
    # AL-GATE3-005: which fields are required is read out of extract/schema.py,
    # never restated here. The CHECK stays independent (that is the point of Q3);
    # only the constant is shared, and the read failing is a FAIL, not a default.
    try:
        need = provenance_fields()
        classes = license_classes()
    except (OSError, ValueError) as exc:
        f.append("could not read the provenance rule out of extract/schema.py: %s" % exc)
        return f, d

    def check(where, src):
        if not isinstance(src, dict):
            f.append("%s: no source object" % where)
            return
        for field in need:
            if not src.get(field):
                f.append("%s: source.%s missing" % (where, field))
        if src.get("license_class") not in classes:
            f.append("%s: license_class '%s' is not one of %s"
                     % (where, src.get("license_class"), ", ".join(classes)))

    entries = data["commands"]["entries"]
    tools = data["tools"]["tools"]
    if not entries:
        f.append(empty_set_failure(
            "command entries to re-check the provenance of",
            "the provenance law is the reason a reader can trust a rendered command at root, and "
            "a build that embeds no commands cannot have honoured it"))
    if not tools:
        f.append(empty_set_failure(
            "tools to re-check the provenance of",
            "every command entry names a tool, so no tools means no entries either — or an "
            "extraction that dropped them"))
    for e in entries:
        check("command entry %s" % e.get("id"), e.get("source"))
    for t in tools:
        check("tools entry %s" % t.get("id"), t.get("source"))
    for v in VERSIONS:
        check("rules_rhel%s" % v, (data["rules"][v].get("_meta") or {}).get("source"))
        fmeta = data["flags"][v].get("_meta") or {}
        if data["flags"][v].get("clis"):
            check("flags_rhel%s" % v, fmeta.get("source"))
        elif not (fmeta.get("status") or "").strip():
            f.append("flags_rhel%s: empty dictionary with no _meta.status saying why" % v)
    check("cci_nist", (data["cci_nist"].get("_meta") or {}).get("source"))
    check("dangerous", data["dangerous"].get("source"))
    if not f:
        d.append("every command entry, tool, flag dictionary, rules dataset, the CCI map and the "
                 "destructive-pattern table carry %s" % "/".join(need))
        d.append("the required field list was read out of extract/schema.py's PROVENANCE_FIELDS, "
                 "not restated here: Q3 stays an INDEPENDENT re-check of the artifact, but it can "
                 "no longer be a WEAKER one than the build-time check it doubles against — which "
                 "is what it had silently become, missing 'version' (AL-GATE3-005)")
    return f, d


def gate_q4(ctx):
    f, d = [], []
    entries = ctx["data"]["commands"]["entries"]
    if not entries:
        f.append(empty_set_failure(
            "command entries",
            "verify/undo/blast IS the product's promise, and a build with no entries keeps it "
            "the way an empty book keeps a promise to be accurate"))
    for e in entries:
        if not e.get("verify") or not e.get("undo") or e.get("blast") not in ("green", "yellow", "red"):
            f.append("entry %s: verify/undo/blast promise broken" % e.get("id"))
    if not f:
        d.append("all %d command entries keep verify/undo/blast" % len(entries))
    return f, d


HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S)


def marker_kind(marker):
    """What sort of claim a feature marker makes, derived from its own text.

    Gate 3, Q5 row: the markers "stand in for structural product claims ('rail
    renderer exists'), which is a stronger claim to be making from a substring
    hit". True of most of them and NOT of all of them, which is why this is a
    classifier and not a blanket rule:

      code   `function renderRail(`, `var KEYMAP=`, `document.addEventListener(`
             — a claim about code, which must be in the app script and not in a
             comment or a string.
      html   `id="rail"` — a claim about the static document, which must be in
             the markup and not inside a JS string or an HTML comment.
      text   `Not available in RHEL `, `UNVERIFIED_FLAG_COPY`, `@media print`,
             `MCR-ASSEMBLER-BEGIN` — user-visible copy, a CSS at-rule, a comment
             marker. Copy LIVES in a string literal and the assembler marker
             lives in a comment BY DESIGN, so for these a substring hit over the
             whole file is the right and only check.

    Derived rather than declared on purpose: MARKERS stays a list of 3-tuples,
    so a tranche that adds markers does not also have to classify them, and two
    branches adding markers do not collide over a schema change.
    """
    if marker.startswith('id="'):
        return "html"
    if re.match(r"^(function|var)\s+[A-Za-z_$]", marker) or marker.startswith("document."):
        return "code"
    return "text"


def marker_present(html, marker):
    """Is this marker really there, in the place its kind requires?"""
    kind = marker_kind(marker)
    if kind == "text":
        return marker in html
    if kind == "html":
        markup = SCRIPT_BLOCK_RE.sub(" ", html)
        markup = HTML_COMMENT_RE.sub(" ", markup)
        return marker in markup
    script = app_script_of(html)
    masked = mask_js_literals(script)
    # The marker must START at a position that survived masking — i.e. at real
    # code. Several markers deliberately END inside a string literal
    # (`var APP_NAME="`, `document.addEventListener("click"`), so the marker is
    # matched against the RAW script and only its starting position is asked to
    # be code. A marker sitting wholly inside a comment or a string has its first
    # character blanked, and is not counted.
    at = script.find(marker)
    while at >= 0:
        if masked[at] == script[at]:
            return True
        at = script.find(marker, at + 1)
    return False


def gate_q5(ctx):
    f, d, p = [], [], []
    html = ctx["html"]
    kinds = {"code": 0, "html": 0, "text": 0}
    for name, marker, phase in MARKERS:
        if marker_present(html, marker):
            kinds[marker_kind(marker)] += 1
            continue
        if phase:
            p.append("%s — not in this build yet (%s)" % (name, phase))
        else:
            f.append("feature marker missing: %s (%s, expected as %s)"
                     % (name, marker, {"code": "live code in the app script, not a comment or a "
                                               "string",
                                       "html": "an element in the static markup, not a JS string "
                                               "or an HTML comment",
                                       "text": "text anywhere in the shipped file"}[marker_kind(marker)]))
    d.append("%d/%d markers present, %d pending"
             % (len(MARKERS) - len(f) - len(p), len(MARKERS), len(p)))
    d.append("%d structural markers found in LIVE CODE (masked: a definition named only in a "
             "comment, a doc string or dead string data does not count), %d region markers found "
             "in the static markup outside every <script> and HTML comment, and %d text markers "
             "— copy, a CSS at-rule and the assembler's own comment marker, which belong in a "
             "string or a comment and are matched as text on purpose"
             % (kinds["code"], kinds["html"], kinds["text"]))
    if "unverified" not in html:
        f.append("no-guess copy for an uncurated flag explanation is absent")
    else:
        d.append("no-guess copy present: a flag with no curated explain renders as unverified")
    return f, d, p


def gate_q6(ctx):
    f, d = [], []
    shell = ctx["shell"]
    for pat, why in [(r"\bTODO\b", "TODO"), (r"lorem ipsum", "lorem ipsum"),
                     (r"example\.com", "example.com"), (r"CHANGEME", "CHANGEME"),
                     (r"\bFIXME\b", "FIXME"), (r"\bXXX\b", "XXX")]:
        if re.search(pat, shell, re.I):
            f.append("leak: %s present in the shell" % why)
    if not f:
        d.append("no TODO/FIXME/XXX/lorem/example.com/CHANGEME in the shell "
                 "(the data island is vendor text and is scanned separately by Q10)")
    return f, d


STORAGE_RE = re.compile(r"\b(?:localStorage|sessionStorage)\b")


def try_block_spans(src):
    """Brace-matched [start, end) spans of every try{...} block in the script.

    AL-GATE3-003. This used to count raw `{` and `}` characters. One unbalanced
    brace inside a string literal inside a `try` body shifted the depth, the span
    ran past its own `catch`, and it absorbed the sibling code after it — so a
    genuinely unguarded storage call was reported as guarded. Silently, which is
    the worst way for a gate to be wrong.

    The masking is done HERE, not by the caller. Deciding what is a brace and
    what is a character inside a literal is this function's own job; a caller
    that has to remember to launder its input first is a caller that will one day
    forget. Masking is idempotent, so a caller that masks anyway costs nothing.
    Spans index into the string that was passed in: the mask preserves offsets.
    """
    masked = mask_js_literals(src)
    spans = []
    for m in re.finditer(r"\btry\s*\{", masked):
        depth, i = 0, m.end() - 1
        while i < len(masked):
            if masked[i] == "{":
                depth += 1
            elif masked[i] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), i + 1))
                    break
            i += 1
    return spans


def storage_guard_failures(script):
    """Q7's judgement over a piece of JS. Returns (failures, details).

    Factored out of gate_q7 so tests/test_storage_guard.py can drive the gate
    with the desync constructs from AL-GATE3-003 rather than only its span
    finder. A gate whose decision cannot be called from a test is a gate nobody
    can watch fail.
    """
    f, d = [], []
    masked = mask_js_literals(script)
    spans = try_block_spans(masked)
    hits = list(STORAGE_RE.finditer(masked))
    if not hits:
        f.append("no storage access found at all in the app script — Q7 proves the storage guard "
                 "holds, and a gate with nothing to check reports PASS by having found nothing. "
                 "STORE is not optional: if it were genuinely removed, this line is the one that "
                 "has to be edited on purpose")
    for m in hits:
        if not any(s <= m.start() < e for s, e in spans):
            line = masked[:m.start()].count("\n") + 1
            f.append("storage identifier '%s' at app-script line %d is not inside a try{...}catch "
                     "block" % (m.group(0), line))
    if not f:
        d.append("all %d localStorage/sessionStorage references sit inside one of %d try/catch "
                 "blocks — braces counted over a lexically masked copy, so a brace inside a "
                 "string, template or regex literal cannot stretch a span past its own catch "
                 "and swallow an unguarded sibling (AL-GATE3-003)" % (len(hits), len(spans)))
    return f, d


def gate_q7(ctx):
    f, d = [], []
    script = ctx["app_script"]
    sf, sd = storage_guard_failures(script)
    f.extend(sf)
    d.extend(sd)
    if "var SCHEMA=1;" not in mask_js_literals(script):
        f.append("storage records are not schema-versioned")
    else:
        d.append("storage records are schema-versioned and namespaced (mdcr.v1.)")
    return f, d


# AL-GATE3-011: content/glossary.json shipped in the island, bound to
# DATASETS.GLOSSARY at template.html's data-island loader, and read by
# nothing -- grep -n GLOSSARY template.html turned up exactly one line, its
# own assignment. Nothing caught that because nothing checked it: Q8 counts
# embedded records, Q3 checks provenance, and neither asks whether anything
# RENDERS a family. This is that check, for every family build.py's CONTENT
# map embeds -- the module variable DATASETS binds each one to must be
# referenced somewhere in the shipped app script besides its own assignment.
#
# expected_output is the one documented exception. build.py folds
# data["expected_output"]["captures"] onto each matching rule record's own
# .expected_output field before the island is serialized (the "captures
# joined onto rules" step) -- so its content is not unreachable, it is
# reachable through RULES, which this same check confirms is live. The raw
# top-level copy is a redundant duplicate of already-embedded data, not an
# orphan; collapsing that duplicate is a real size win but a separate,
# narrower finding than AL-GATE3-011 and is not this ticket.
#
# This table is maintained BY HAND in step with build.py's CONTENT map — the
# same discipline load_build_constants() and GENERATORS already rely on
# (qa.py reads build.py's text rather than importing it). glossary is not
# listed here: dropping a family from CONTENT means it is no longer this
# check's business, the same day it stops being build.py's.
CONTENT_FAMILY_TOKENS = {
    "COMMANDS": "commands", "TOOLS": "tools", "DANGEROUS": "dangerous",
    "RULES": "rules", "FLAGS": "flags",
    "CCI_NIST": "cci_nist", "EXPECTED": "expected_output",
}
CONTENT_FAMILY_JOINED_ELSEWHERE = {"EXPECTED"}
_TOKEN_RE_CACHE = {}


def content_family_liveness_failures(app_script):
    f = []
    for token, family in sorted(CONTENT_FAMILY_TOKENS.items()):
        if token in CONTENT_FAMILY_JOINED_ELSEWHERE:
            continue
        rx = _TOKEN_RE_CACHE.get(token)
        if rx is None:
            rx = _TOKEN_RE_CACHE[token] = re.compile(r"\b%s\b" % token)
        if len(rx.findall(app_script)) <= 1:
            f.append("%s (CONTENT family '%s') is bound to DATASETS.%s in the data-island "
                      "loader and referenced nowhere else in the shipped app script -- "
                      "embedded payload nothing reads (AL-GATE3-011)" % (token, family, token))
    return f


def gate_q8(ctx):
    f, d = [], []
    f.extend(content_family_liveness_failures(ctx.get("app_script") or ""))
    data = ctx["data"]
    for v in VERSIONS:
        ds = data["rules"][v]
        meta = ds.get("_meta") or {}
        embedded = ds.get("rules", [])
        src, total = ctx["source_rules"][v]
        if not embedded:
            f.append(empty_set_failure(
                "rules embedded for RHEL %s" % v,
                "this gate reconciles the embedded count against _meta, and 0 == 0 is the one "
                "pair of numbers that agrees no matter what the extractor did"))
        if meta.get("rule_count") != len(embedded):
            f.append("rules_rhel%s: _meta.rule_count %s != %d embedded"
                     % (v, meta.get("rule_count"), len(embedded)))
        if meta.get("source_rule_count") != total:
            f.append("rules_rhel%s: _meta.source_rule_count %s != %d rules in the pinned XCCDF"
                     % (v, meta.get("source_rule_count"), total))
        # CR-T-07 removed the partial datasets. extract/parse_xccdf.py emits every
        # rule in every pinned benchmark, so a shortfall is now a failure and not a
        # declaration: there is no longer an extractor that can honestly produce one.
        if meta.get("partial"):
            f.append("rules_rhel%s: _meta.partial is set — CR-T-07 emits full benchmarks; "
                     "a partial RULES dataset no longer has a generator that produces it" % v)
        if len(embedded) != total:
            f.append("rules_rhel%s: %d embedded != %d rules in the pinned XCCDF" % (v, len(embedded), total))
        else:
            cats = meta.get("cat_counts") or {}
            d.append("rules_rhel%s (%s): %d rules, full parity with the pinned XCCDF — "
                     "CAT I %s / II %s / III %s"
                     % (v, meta.get("version", "?"), total,
                        cats.get("I", "?"), cats.get("II", "?"), cats.get("III", "?")))
        if meta.get("generator") not in GENERATORS:
            f.append("rules_rhel%s: _meta.generator '%s' is not an extractor Q15 re-runs"
                     % (v, meta.get("generator")))
    entries = data["commands"]["entries"]
    if not entries:
        f.append(empty_set_failure(
            "command entries",
            "the entry count and _meta.entry_count agree trivially at zero"))
    if not data["cci_nist"].get("cci"):
        f.append(empty_set_failure(
            "CCI mappings",
            "the mapping count and _meta.entry_count agree trivially at zero"))
    if len(entries) != (data["commands"].get("_meta") or {}).get("entry_count"):
        f.append("commands.json _meta.entry_count != %d embedded entries" % len(entries))
    else:
        d.append("commands: %d entries, count matches _meta" % len(entries))
    for v in VERSIONS:
        fl = data["flags"][v]
        fl_meta = fl.get("_meta") or {}
        # AL-GATE3-009: a FLAGS dataset's declared generator was never checked
        # against anything — flags_rhel9.json shipped naming a script
        # (extract/extract_rhel_flags.py) that has never existed in this repo.
        if fl_meta.get("generator") not in RERUN_GENERATORS:
            f.append("flags_rhel%s: _meta.generator '%s' is not an extractor Q15 re-runs"
                     % (v, fl_meta.get("generator")))
        d.append("flags_rhel%s: %d CLI dictionaries (%s)"
                 % (v, len(fl.get("clis", {})), fl_meta.get("status", "")[:48]))
    cci_meta = data["cci_nist"].get("_meta") or {}
    n_cci = len(data["cci_nist"].get("cci", {}))
    if cci_meta.get("entry_count") != n_cci:
        f.append("cci_nist.json: _meta.entry_count %s != %d embedded mappings"
                 % (cci_meta.get("entry_count"), n_cci))
    else:
        d.append("cci_nist: %d mappings embedded, filtered from the %s item DISA CCI list"
                 % (n_cci, cci_meta.get("source_cci_count", "?")))
    return f, d


def gate_q9(ctx):
    f, d = [], []
    data = ctx["data"]
    cci_map = data["cci_nist"].get("cci", {})
    n_cat1 = 0
    for v in VERSIONS:
        src, _ = ctx["source_rules"][v]
        cat1 = 0
        for r in data["rules"][v].get("rules", []):
            sid = r.get("i")
            if not sid:
                f.append("rules_rhel%s: a rule has no STIG ID" % v)
                continue
            if r.get("c") not in ("I", "II", "III"):
                f.append("rules_rhel%s %s: CAT '%s' is not I/II/III" % (v, sid, r.get("c")))
            if r.get("c") == "I":
                cat1 += 1
                n_cat1 += 1
                missing = [label for label, key in (("check", "chk"), ("fix", "fix")) if not r.get(key)]
                if missing:
                    f.append("rules_rhel%s %s: CAT I rule with no %s text — a CAT I finding without "
                             "both is not usable as evidence" % (v, sid, " and no ".join(missing)))
            s = src.get(sid)
            if s and s["cci"] and not r.get("cci"):
                f.append("rules_rhel%s %s: source has CCI %s, embedded record has none" % (v, sid, s["cci"]))
            for c in (r.get("cci") or []):
                if cci_map.get(c) and cci_map[c].get("nist") and not r.get("n"):
                    f.append("rules_rhel%s %s: %s maps to %s but the record carries no NIST control"
                             % (v, sid, c, cci_map[c]["nist"]))
        # A release with no CAT I rules at all means the severity parse dropped them
        # silently, which would make this gate pass by having nothing to check.
        if cat1 == 0:
            f.append("rules_rhel%s: zero CAT I rules — every pinned RHEL benchmark has some, so the "
                     "severity parse dropped them" % v)
        else:
            d.append("rules_rhel%s: all %d CAT I rules carry both check and fix text" % (v, cat1))
    if not f:
        d.append("every one of the %d embedded rules has a STIG ID and a CAT of I/II/III; all %d CAT I "
                 "rules carry check and fix text; CCI present wherever the source has one; NIST present "
                 "wherever the CCI maps"
                 % (sum(len(data["rules"][v].get("rules", [])) for v in VERSIONS), n_cat1))
    return f, d


def accuracy_sample(ids):
    """The Q10 sample: fixed stride, no RNG, reproducible in CI (ADR-001 §7.3).

    A dataset at or below the sample size is checked in full rather than sampled,
    because sampling 20 out of 20 is just a slower way of checking all of them.
    """
    ids = sorted(ids)
    if len(ids) <= SAMPLE_PER_RELEASE:
        return ids
    return (ids[::SAMPLE_STRIDE] or ids)[:SAMPLE_PER_RELEASE]


def accuracy_failures(version, rules, src, full_set=True):
    """Diff an embedded rules list against a fresh parse of the pinned XCCDF.

    Pure: no ctx, no globals beyond the sampling constants, no I/O. gate_q10 and
    tests/test_accuracy_gate.py both call this, so the gate that runs in CI is
    the gate the mutated fixture proves. `full_set` is False only when the caller
    is deliberately passing a reduced dataset (the committed fixtures), never for
    a shipping build.

    Two layers, on purpose. The SAMPLE catches a rule whose text drifted; the
    ID-SET PARITY catches a rule that was added, dropped, or renamed outside the
    sample, which a stride of 20-in-445 would otherwise walk straight past.
    """
    bad = []
    embedded = {}
    for r in rules:
        sid = r.get("i")
        if not sid:
            bad.append("a rule carries no STIG ID")
            continue
        if sid in embedded:
            bad.append("%s: embedded twice" % sid)
        embedded[sid] = r
    ids = sorted(embedded)

    if full_set:
        extra = sorted(set(ids) - set(src))
        missing = sorted(set(src) - set(ids))
        if extra:
            bad.append("embedded but absent from the pinned XCCDF: %s" % ", ".join(extra[:6]))
        if missing:
            bad.append("in the pinned XCCDF but not embedded: %s" % ", ".join(missing[:6]))

    sample = accuracy_sample(ids)
    if full_set and len(ids) > SAMPLE_PER_RELEASE and len(sample) < SAMPLE_PER_RELEASE:
        bad.append("stride %d over %d rules yields only %d samples, not the %d ADR-001 §7.3 Q10 requires"
                   % (SAMPLE_STRIDE, len(ids), len(sample), SAMPLE_PER_RELEASE))

    for sid in sample:
        e, s = embedded[sid], src.get(sid)
        if s is None:
            bad.append("%s: absent from the pinned XCCDF" % sid)
            continue
        if e.get("t") != s["t"]:
            bad.append("%s: title differs from source" % sid)
        if e.get("rid") != s["rid"]:
            bad.append("%s: rule id %s != source %s" % (sid, e.get("rid"), s["rid"]))
        if list(e.get("cci") or []) != s["cci"]:
            bad.append("%s: CCI %s != source %s" % (sid, e.get("cci"), s["cci"]))
        if e.get("c") != s["c"]:
            bad.append("%s: CAT %s != source %s" % (sid, e.get("c"), s["c"]))
        # CR-T-07 embeds check and fix verbatim and uncapped, so the whole text
        # must match — not merely a prefix. The split on the Etsy pipeline's
        # trim marker stays so a capped dataset would still be compared fairly.
        for key, label in (("fix", "fix"), ("chk", "check")):
            et = (e.get(key) or "").split("[trimmed")[0].strip()
            if et and not s[key].startswith(et[:100]):
                bad.append("%s: %s text prefix differs from source" % (sid, label))
            elif et and et != s[key]:
                bad.append("%s: %s text differs from source beyond its first 100 characters"
                           % (sid, label))
    return bad, sample


def gate_q10(ctx):
    f, d = [], []
    f += ctx["pin_failures"]
    d += ctx["pin_details"]
    if ctx["pin_failures"]:
        return f, d
    data = ctx["data"]
    for v in VERSIONS:
        src, _ = ctx["source_rules"][v]
        rules = data["rules"][v].get("rules", [])
        bad, sample = accuracy_failures(v, rules, src)
        if bad:
            f.append("rules_rhel%s accuracy: %s" % (v, "; ".join(bad[:6])))
        else:
            d.append("rules_rhel%s: every one of the %d embedded STIG IDs is present in %s and vice "
                     "versa; %d of them sampled at stride %d and re-parsed, identical on title, rule "
                     "id, CCI, CAT, and full check and fix text"
                     % (v, len(rules), XCCDF[v], len(sample), SAMPLE_STRIDE))
    return f, d


def gate_q11(ctx):
    f, d = [], []
    if ctx["pin_failures"]:
        f.append("pin check failed; refusing to re-check CCI mappings against an unpinned list")
        return f, d
    data = ctx["data"]
    embedded = data["cci_nist"].get("cci", {})
    if not embedded:
        f.append("cci_nist.json carries no mappings")
        return f, d
    live = parse_cci_list()
    ids = sorted(embedded)
    sample = ids[::3][:SAMPLE_PER_RELEASE] or ids
    if len(ids) <= SAMPLE_PER_RELEASE:
        sample = ids
    bad = []
    for cci in sample:
        want = live.get(cci)
        got = (embedded[cci].get("nist") or [None])[0]
        if want != got:
            bad.append("%s: embedded %s != DISA list %s" % (cci, got, want))
    if bad:
        f.append("CCI->800-53 mismatch: %s" % "; ".join(bad[:6]))
    else:
        d.append("%d of %d CCI mappings re-checked against %s (Rev 5 index) — all match"
                 % (len(sample), len(ids), CCI_LIST))
    # The map is filtered on purpose (ADR-001 §5.4). It must be filtered to exactly
    # what the four benchmarks cite: anything more is dead weight in an air-gapped
    # file, anything less breaks a crosswalk at render time.
    meta = data["cci_nist"].get("_meta") or {}
    unmapped = meta.get("unmapped_cci")
    if unmapped:
        d.append("%d referenced CCI(s) carry no 800-53 index in the DISA list and are embedded with an "
                 "empty nist[] rather than a guess: %s" % (len(unmapped), ", ".join(unmapped[:6])))
    # every CCI referenced by an embedded rule must exist in the map
    referenced = set()
    for v in VERSIONS:
        for r in data["rules"][v].get("rules", []):
            referenced.update(r.get("cci") or [])
    missing = sorted(referenced - set(embedded))
    if missing:
        f.append("CCIs referenced by embedded rules but absent from cci_nist.json: %s" % ", ".join(missing))
    else:
        d.append("all %d CCIs referenced by embedded rules resolve in the map" % len(referenced))
    unreferenced = sorted(set(embedded) - referenced)
    if unreferenced:
        f.append("cci_nist.json carries %d mapping(s) no embedded rule cites — the map is filtered to "
                 "the referenced set (ADR-001 §5.4): %s" % (len(unreferenced), ", ".join(unreferenced[:6])))
    return f, d


def gate_q12(ctx):
    f, d = [], []
    entries = ctx["data"]["commands"]["entries"]
    if not entries:
        f.append(empty_set_failure(
            "command entries",
            "four-version completeness is the claim on the cover of this product; with no "
            "entries it is complete the way a blank page is"))
    for e in entries:
        if "template" in e:
            # A generator spec (CR-T-17+) composes its command at render time from
            # validated FORM INPUT, not from a fixed rhel_versions object — so the
            # four-version promise is kept by spec.versions (a whole-generator gate)
            # and each field's own .versions (a per-field gate) instead of a
            # rhel_versions block. extract/schema.py's spec_errors() is the
            # build-time authority for the field/template shape; this gate only
            # confirms that IF the entry restricts itself to certain releases, it
            # names real RHEL keys and not something that silently gates nothing.
            vs = e.get("versions")
            if vs is not None and (not isinstance(vs, list) or not vs or any(v not in VERSIONS for v in vs)):
                f.append("entry %s: versions %r is not a non-empty subset of %s" % (e.get("id"), vs, VERSIONS))
            continue
        versions = e.get("rhel_versions") or {}
        if set(versions.keys()) != set(VERSIONS):
            f.append("entry %s: rhel_versions keys %s != {7,8,9,10}" % (e.get("id"), sorted(versions.keys())))
            continue
        for v in VERSIONS:
            val = versions[v]
            if not isinstance(val, dict):
                f.append("entry %s: rhel_versions['%s'] is not an object" % (e.get("id"), v))
            elif "unavailable" in val:
                if not ((val.get("unavailable") or {}).get("reason") or "").strip():
                    f.append("entry %s: rhel_versions['%s'] unavailable with an empty reason" % (e.get("id"), v))
            elif "command" in val:
                if not (val.get("command") or "").strip():
                    f.append("entry %s: rhel_versions['%s'] has an empty command" % (e.get("id"), v))
            else:
                f.append("entry %s: rhel_versions['%s'] is not a command, an unavailable, or a "
                         "resolved same_as" % (e.get("id"), v))
    if not f:
        d.append("all %d entries carry all four RHEL keys with an explicit value in every one "
                 "(build.py resolved same_as pointers before embedding)" % len(entries))
    tools = ctx["data"]["tools"]["tools"]
    if not tools:
        f.append(empty_set_failure(
            "tools", "no tool declares availability for all four releases because no tool is here"))
    for t in tools:
        if set((t.get("availability") or {}).keys()) != set(VERSIONS):
            f.append("tools entry %s: availability keys != {7,8,9,10}" % t.get("id"))
    if not any("tools entry" in x for x in f):
        d.append("all %d tools declare availability for all four versions" % len(tools))
    return f, d


def gate_q13(ctx):
    f, d = [], []
    data = ctx["data"]
    tool_ids = set(t.get("id") for t in data["tools"]["tools"])
    categories = set(data["commands"].get("categories") or [])
    rule_index = {v: {r["i"]: r for r in data["rules"][v].get("rules", []) if r.get("i")} for v in VERSIONS}
    sources_json = os.path.join(REPO, "content-src", "SOURCES.json")
    have_sources = os.path.exists(sources_json)
    source_ids = set()
    if have_sources:
        with open(sources_json, encoding="utf-8") as fh:
            source_ids = set(json.load(fh).get("sources", {}).keys())
    n_stig = 0
    if not data["commands"]["entries"]:
        f.append(empty_set_failure(
            "command entries whose stig_id/rule_id/tool/category links resolve",
            "referential integrity over an empty set of references is not a property anybody "
            "wanted proved"))
    if not tool_ids:
        f.append(empty_set_failure(
            "tool ids to resolve entry.tool against",
            "an empty target set makes every future membership test a failure, not a pass, so "
            "this one is caught here rather than as a flood of confusing entry errors later"))
    if not categories:
        f.append(empty_set_failure(
            "categories to resolve entry.category against",
            "same shape as the tool index above"))
    for e in data["commands"]["entries"]:
        if e.get("tool") not in tool_ids:
            f.append("entry %s: tool '%s' is not in tools.json" % (e.get("id"), e.get("tool")))
        if "explain_tool" in e and e.get("explain_tool") not in tool_ids:
            f.append("entry %s: explain_tool '%s' is not in tools.json" % (e.get("id"), e.get("explain_tool")))
        if "privilege" in e and e.get("privilege") not in ("root",):
            f.append("entry %s: privilege '%s' is not a recognised privilege level"
                     % (e.get("id"), e.get("privilege")))
        if e.get("category") not in categories:
            f.append("entry %s: category '%s' is not in commands.json categories" % (e.get("id"), e.get("category")))
        for s in (e.get("stig") or []):
            n_stig += 1
            v, sid = s.get("rhel_version"), s.get("stig_id")
            if v not in VERSIONS:
                f.append("entry %s: stig %s has no valid rhel_version" % (e.get("id"), sid))
                continue
            if not sid or not sid.startswith("RHEL-%s-" % v.zfill(2)):
                f.append("entry %s: stig_id %s does not match its declared RHEL %s" % (e.get("id"), sid, v))
            rec = rule_index[v].get(sid)
            if rec is None:
                f.append("entry %s: stig_id %s does not resolve in rules_rhel%s" % (e.get("id"), sid, v))
                continue
            if s.get("rule_id") != rec.get("rid"):
                f.append("entry %s: stig %s rule_id != the rules record rid" % (e.get("id"), sid))
            if e["id"] not in (rec.get("cmds") or []):
                f.append("entry %s: reverse link missing in rules_rhel%s %s cmds[]" % (e.get("id"), v, sid))
        for fl in (e.get("flags") or []):
            ref = fl.get("source_ref")
            if ref and not have_sources:
                f.append("entry %s: flag %s cites source_ref %s but content-src/SOURCES.json does not exist"
                         % (e.get("id"), fl.get("flag"), ref))
            elif ref and ref not in source_ids:
                f.append("entry %s: flag %s source_ref %s does not resolve" % (e.get("id"), fl.get("flag"), ref))
    if not f:
        d.append("every tool, category, and all %d stig_id/rule_id pairs resolve, and every STIG row "
                 "has its reverse link in the rules dataset" % n_stig)
        d.append("source_ref: %s" % ("resolved against content-src/SOURCES.json" if have_sources
                                     else "no SOURCES.json yet (CR-T-06) and no entry cites one — consistent"))
    return f, d


SHINGLE_N = 8                       # ADR-001 §7.3 Q14. The promise is an 8-gram.
STAGED_SUBDIRS = ("man", "help", "redhat", "git")

# Mirrors extract/schema.py's HEADER_BOUND_FIELDS. Not imported from there on
# purpose — qa.py is stdlib-only and keeps its own independent path through
# this file's data on principle (see the module docstring: Q8..Q11 re-parse
# XCCDF themselves rather than reuse the extractor, "the accuracy gate is
# worth nothing if it re-uses the extractor's code path"). Same reasoning
# applies to Q14: it should not trust extract/schema.py's idea of which
# fields are free text, it should have its own.
HEADER_BOUND_FIELDS = ("intent", "verify", "undo")


def shingles(text):
    """Every SHINGLE_N-word run in text, normalised. Pure."""
    toks = re.sub(r"[^a-z0-9\s-]", " ", text.lower()).split()
    return set(tuple(toks[i:i + SHINGLE_N])
               for i in range(max(0, len(toks) - (SHINGLE_N - 1))))


def raw_source_paths(repo=REPO):
    """(staged subdirectory names, every .txt/.md path under them). Pure but for I/O."""
    staged = [sub for sub in STAGED_SUBDIRS if os.path.isdir(os.path.join(repo, "content-src", sub))]
    bases = list(staged)
    if os.path.isdir(os.path.join(repo, "content-src", "raw")):
        bases.append("raw")
    corpus = []
    for sub in bases:
        for root, _dirs, files in os.walk(os.path.join(repo, "content-src", sub)):
            for name in sorted(files):
                if name.endswith((".txt", ".md")):
                    corpus.append(os.path.join(root, name))
    return staged, corpus


def raw_shingles(repo=REPO):
    grams = set()
    for path in raw_source_paths(repo)[1]:
        with open(path, encoding="utf-8", errors="replace") as fh:
            grams |= shingles(fh.read())
    return grams


def curated_texts(entry):
    """Every curated free-text field on an entry that Q14 compares against raw sources.

    Returns (text, license_class) pairs, not bare strings. Most fields are
    governed by the entry's own `source.license_class` — but flags[] may carry
    a license_class of their own (a flag can be cited from a different source
    than the entry as a whole, once content-src/SOURCES.json exists to resolve
    a source_ref against), so a flag's own license_class wins over the entry's
    when present. This is the fix for the H1 gap: an entry whose top-level
    `source` is verbatim-ok (a DISA STIG citation) can still carry an
    individually paraphrase-only flag (systemctl's `status`/`is-active`
    behaviour, documented rather than STIG text) — under the old entry-level
    gate, that flag's `explain` was never checked at all, because the whole
    entry was skipped before curated_texts() ever ran.

    Every field Q14 was asked to cover (ADR-001 §7.3, widened per Milo Vance's
    self-flagged H1 gap): `intent`, `verify`, `undo` (entry-level, HEADER_BOUND_
    FIELDS — the same three fields copied into the clipboard comment header,
    extract/schema.py's single_line_errors rule), rhel_versions[].notes and
    .changed_in_note.what, flags[].explain, stig[].notes (schema does not
    define this key today, but a future free-text stig row note must not be a
    silent hole), and a generator spec's fields[].label / fields[].help — the
    form-facing strings on a `"template" in e` entry (extract/schema.py
    spec_fields_errors), which carry no `type` restriction and are exactly
    where a paraphrase-only man page sentence would land if pasted into a
    field's UI copy instead of into `intent`.
    """
    entry_lc = (entry.get("source") or {}).get("license_class")
    texts = []
    for field in HEADER_BOUND_FIELDS:  # ("intent", "verify", "undo")
        if isinstance(entry.get(field), str) and entry[field]:
            texts.append((entry[field], entry_lc))
    for v in VERSIONS:
        val = (entry.get("rhel_versions") or {}).get(v) or {}
        if val.get("notes"):
            texts.append((val["notes"], entry_lc))
        if (val.get("changed_in_note") or {}).get("what"):
            texts.append((val["changed_in_note"]["what"], entry_lc))
    for fl in (entry.get("flags") or []):
        if fl.get("explain"):
            texts.append((fl["explain"], fl.get("license_class") or entry_lc))
    for s in (entry.get("stig") or []):
        if isinstance(s, dict) and s.get("notes"):
            texts.append((s["notes"], entry_lc))
    if isinstance(entry.get("fields"), list):
        for fld in entry["fields"]:
            if not isinstance(fld, dict):
                continue
            for key in ("label", "help"):
                if isinstance(fld.get(key), str) and fld[key]:
                    texts.append((fld[key], entry_lc))
    return texts


def paraphrase_failures(entries, raw_grams):
    """Q14's collision check. Pure: no ctx, no globals, no I/O.

    gate_q14 and tests/test_paraphrase.py both call this, so the gate that runs
    in CI is the gate the planted fixture proves. ADR-001 §7.3 asked for that
    test file; until AL-GATE3's Gate 3 review, Q14 was the only gate in this file
    with no way to drive it at all.

    Filtering by license_class now happens PER FIELD (curated_texts' second
    tuple element), not once per entry — see curated_texts()'s docstring for
    why: a flags[] item's own license_class can differ from its entry's.
    """
    f = []
    for e in entries:
        for t, lc in curated_texts(e):
            if lc != "paraphrase-only":
                continue
            shared = shingles(t) & raw_grams
            if shared:
                f.append("entry %s: %d-gram lifted from a paraphrase-only source: \"%s\""
                         % (e.get("id"), SHINGLE_N, " ".join(sorted(shared)[0])))
    return f


def source_is_offline_checkable(source):
    """True if Q14's shingle check has bytes to compare this citation against.

    A `man N tool` reference or a direct `content-src/raw/...` path names a
    source this repo stages (or is staged FROM) under content-src/raw/, so
    raw_shingles() actually contains the text the citation claims. Anything
    else — a docs.redhat.com URL, a local PDF, a "... Guide" title — names a
    Red Hat guide (CC-BY-SA 3.0, paraphrase-only per content-licensing-ruling
    v1). This repo does not and should not stage guide prose the way it stages
    man/--help captures: copying a copyrighted guide passage into content-src/
    just so Q14 can shingle-check it would itself be the verbatim embedding
    the licensing ruling exists to prevent (and man pages are a redistributable
    reference dump by convention; a Red Hat doc page is not). So Q14 cannot
    see those bytes and cannot vouch for a paraphrase drawn from them the way
    it vouches for one drawn from a staged man page — see attestation_failures().
    """
    ref = (source or {}).get("url_or_man")
    if not isinstance(ref, str):
        return False
    return ref.startswith("man ") or ref.startswith("content-src/raw/")


def attestation_failures(entries, repo=REPO):
    """A paraphrase-only entry whose source Q14 cannot shingle-check offline.

    The offline mechanism decision (this tranche): Q14 stays a pure offline
    8-gram check against content-src/raw/ — it does NOT reach out to the
    corpus mirror on saratoga (not in this repo, not reachable in an air-gapped
    CI run, and the exact kind of live-host dependency gate_q15's own docstring
    already refuses for a similar reason). An entry whose paraphrase-only
    source is a Red Hat guide rather than a staged man page therefore gets no
    automated collision check — so it must carry a human one instead: a
    `source.paraphrase_attested_by: {by, on}` receipt naming who read the
    cited guide passage and confirms the curated text paraphrases it rather
    than copying it. `by` is checked against content-src/roster.json the same
    way gate_q16's per-version verified receipts are (normalize_person_name +
    the closed roster's QA role) — the same two-person-rule infrastructure,
    reused rather than re-invented, requiring a QA name because this is a
    review of someone else's curated text, not a self-attestation.

    None of the 27 shipped command entries hit this path today: every
    paraphrase-only entry cites a staged man page (content-src/raw/) and every
    guide mention in a `notes` field is contextual prose inside an entry whose
    own `source` is a man page. This function exists so the FIRST entry that
    cites a guide directly is not silently exempt from Q14 by having nothing
    to compare against.
    """
    f = []
    roster, roster_err = load_roster()
    for e in entries:
        src = e.get("source") or {}
        if src.get("license_class") != "paraphrase-only" or source_is_offline_checkable(src):
            continue
        eid = e.get("id")
        att = src.get("paraphrase_attested_by")
        if not isinstance(att, dict) or not att.get("by") or not att.get("on"):
            f.append("entry %s: source '%s' (%s) is paraphrase-only but is not a staged man page "
                     "or content-src/raw/ path — Q14 has no corpus bytes to shingle-check it "
                     "against, so it needs a source.paraphrase_attested_by {by, on} receipt "
                     "naming who confirmed the curated text paraphrases that source rather than "
                     "copying it"
                     % (eid, src.get("url_or_man"), src.get("title")))
            continue
        if roster is None:
            f.append("entry %s: source.paraphrase_attested_by cannot be checked — %s" % (eid, roster_err))
            continue
        who = normalize_person_name(att.get("by"))
        if "QA" not in roster.get(who, set()):
            f.append("entry %s: source.paraphrase_attested_by.by '%s' does not resolve to a QA "
                     "role in content-src/roster.json" % (eid, att.get("by")))
    return f


def raw_coverage_failures(data, repo=REPO):
    """A populated flag dictionary whose raw sources are not staged (AL-GATE3-004 shape).

    flags_rhel<N>.json is EXTRACTED from the man and --help text under
    content-src/raw/rhel<N>/. If the dictionary ships populated and that
    directory is absent or empty, Q14 is comparing curated content against a
    corpus it did not come from — and reporting PASS, because an empty corpus
    collides with nothing. The gate's own "nothing staged yet" note is honest
    only while nothing was extracted; this is the line that keeps it honest
    afterwards.
    """
    f = []
    for v in VERSIONS:
        if not ((data.get("flags") or {}).get(v) or {}).get("clis"):
            continue
        base = os.path.join(repo, "content-src", "raw", "rhel%s" % v)
        present = []
        if os.path.isdir(base):
            for root, _dirs, files in os.walk(base):
                present += [n for n in files if n.endswith((".txt", ".md"))]
        if not present:
            f.append("flags_rhel%s ships a populated CLI dictionary and content-src/raw/rhel%s/ "
                     "holds no .txt/.md source — that dictionary was extracted FROM those files, "
                     "so Q14 is checking the curated text against a corpus it did not come from. "
                     "An empty corpus collides with nothing and this gate would report PASS by "
                     "having nothing to compare (AL-GATE3-004 applied to Q14)" % (v, v))
    return f


def gate_q14(ctx):
    f, d = [], []
    data = ctx["data"]
    staged, corpus = raw_source_paths()

    coverage = raw_coverage_failures(data)
    f.extend(coverage)
    f.extend(attestation_failures(data["commands"]["entries"]))

    if not corpus:
        if coverage:
            return f, d
        paraphrase = [e for e in data["commands"]["entries"]
                      if (e.get("source") or {}).get("license_class") == "paraphrase-only"]
        if paraphrase:
            f.append("%d command entry/entries are licensed paraphrase-only and NOT ONE raw source "
                     "is staged under content-src/ — the collision check has nothing to collide "
                     "with, so it passes by having nothing to check. Either stage the sources the "
                     "text was written from or stop claiming paraphrase-only (AL-GATE3-004)"
                     % len(paraphrase))
            return f, d
        d.append("no raw sources present under content-src/ and no entry is licensed "
                 "paraphrase-only — nothing to collide with, and nothing claiming to have been "
                 "paraphrased; the %d-gram collision check activates when CR-T-09/CR-T-10 stage "
                 "man and guide text" % SHINGLE_N)
        return f, d

    raw_grams = set()
    for path in corpus:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw_grams |= shingles(fh.read())
    f.extend(paraphrase_failures(data["commands"]["entries"], raw_grams))
    if not f:
        d.append("%d raw source file(s) shingled into %d distinct %d-grams; no curated paraphrase "
                 "shares one with them"
                 % (len(corpus), len(raw_grams), SHINGLE_N))
        d.append("every release whose flag dictionary ships populated has its raw man/--help text "
                 "staged under content-src/raw/, so the corpus this gate compares against is the "
                 "corpus the content was written from%s"
                 % (" (staged: %s)" % ", ".join(staged) if staged else ""))
    return f, d


def gate_q15(ctx):
    """Re-run every extractor over the committed sources and diff (ADR-001 §6.3).

    One entry per generated content family. A family with no extractor listed here
    is a family nobody can prove was generated rather than typed, so the list is
    checked against the generators the datasets themselves declare, below.

    FLAGS special case (CR-T-09/10, extended by CR-T-12). extract/make_pending_
    skeletons.py still emits the placeholder EMPTY flags_rhel<N>.json for every
    version — that was fine before any of CR-T-09/10/12 had run, but
    flags_rhel7.json, flags_rhel8.json and flags_rhel10.json are now real data
    from extract/extract_flags.py (a UBI7 container on saratoga standing in for
    the RHEL 7 host the lab doesn't have, and Defiant/Saratoga directly for RHEL
    8/10), so a diff against the placeholder script's empty output would always
    "drift". Re-running the live extractor here would mean this gate re-opens an
    SSH session to lab hosts (and a container) on every CI run — slow, and a
    hard dependency on lab hosts being reachable from the runner. Instead: (a)
    the three flags_rhel{7,8,10}.json lines are filtered out of make_pending_
    skeletons.py's drift report below — that script is still the right
    authority for flags_rhel9, which remains genuinely empty pending CR-T-11 —
    and (b) extract_flags.py's own --check mode re-parses the raw man/--help
    dumps already committed under content-src/raw/ (no SSH, no live host, no
    container) and diffs that against content/flags_rhel{7,8,10}.json instead.
    """
    f, d = [], []
    flags_reextracted = {"flags_rhel7.json", "flags_rhel8.json", "flags_rhel10.json"}
    for script in GENERATORS:
        path = os.path.join(REPO, script)
        if not os.path.exists(path):
            f.append("%s missing — the files it generates cannot be re-derived" % script)
            continue
        proc = subprocess.run([sys.executable, path, "--check"], cwd=REPO,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.stdout.decode("utf-8", "replace").strip()
        if script == "extract/make_pending_skeletons.py":
            lines = out.splitlines()
            real_drift = [ln for ln in lines
                          if ln.strip().split(":", 1)[0].strip() not in flags_reextracted]
            if any(ln.startswith("GENERATED-FILE DRIFT") for ln in lines) and len(real_drift) <= 1:
                d.append("%s: only flags_rhel8.json/flags_rhel10.json drifted from the empty "
                         "placeholder skeleton — expected now that CR-T-09/10 populated them; "
                         "checked separately below" % script)
            elif proc.returncode != 0:
                f.append("generated content does not match a fresh run of %s (hand-edited?):\n      %s"
                         % (script, "\n      ".join(real_drift)))
            else:
                d.append(out)
            continue
        if proc.returncode != 0:
            f.append("generated content does not match a fresh run of %s (hand-edited?):\n      %s"
                     % (script, out.replace("\n", "\n      ")))
        else:
            d.append(out)

    flags_script = os.path.join(REPO, "extract", "extract_flags.py")
    if not os.path.exists(flags_script):
        f.append("extract/extract_flags.py missing — flags_rhel7/8/10.json cannot be re-derived")
    else:
        for v in ("7", "8", "10"):
            proc = subprocess.run([sys.executable, flags_script, "--check", "--rhel", v], cwd=REPO,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out = proc.stdout.decode("utf-8", "replace").strip()
            if proc.returncode != 0:
                f.append("flags_rhel%s.json does not match a fresh offline re-parse of "
                         "content-src/raw/rhel%s/ (hand-edited, or extractor drifted from raw sources?):\n      %s"
                         % (v, v, out.replace("\n", "\n      ")))
            else:
                d.append(out)

    # Every generated dataset must name a generator this gate actually re-runs.
    # Otherwise a file could declare an extractor that is never executed and drift
    # unnoticed — which is precisely the hand-edit this gate exists to catch.
    # AL-GATE3-009: this used to build `declared` from RULES and CCI only, so a
    # FLAGS dataset's _meta.generator was never compared against anything --
    # flags_rhel9.json shipped naming extract/extract_rhel_flags.py, a script
    # that has never existed, and this gate reported PASS. FLAGS datasets are
    # included below, and RERUN_GENERATORS (not the bare GENERATORS tuple)
    # is the allowed set, since extract/extract_flags.py is re-run above
    # through its own --check --rhel <v> loop rather than the generic one.
    data = ctx["data"]
    declared = {}
    for v in VERSIONS:
        declared["rules_rhel%s" % v] = (data["rules"][v].get("_meta") or {}).get("generator")
        declared["flags_rhel%s" % v] = (data["flags"][v].get("_meta") or {}).get("generator")
    declared["cci_nist"] = (data["cci_nist"].get("_meta") or {}).get("generator")
    unrerun = sorted((name, gen) for name, gen in declared.items() if gen and gen not in RERUN_GENERATORS)
    if unrerun:
        f.append("dataset(s) declare a generator this gate does not re-run: %s"
                 % ", ".join("%s: '%s'" % (name, gen) for name, gen in unrerun))
    else:
        d.append("every RULES, FLAGS and CCI dataset declares a generator that this gate re-ran: %s"
                 % ", ".join(sorted({g for g in declared.values() if g})))
    return f, d


# capture record field names, content validation protocol §7
# (07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md Part B) plus
# command_hash_at_capture and verify_result, present on every real capture
# record — the authoritative set qa.py adapts to, not the reverse (Eli Cross
# ruling closing the CR-T-34 run's WADE_BLOCKED field-name mismatch). Kept
# textually identical to extract/import_captures.py's REQUIRED_FIELDS.
CAPTURE_REQUIRED_FIELDS = (
    "entry_id", "rhel_version", "host", "redhat_release", "kernel", "pkg_versions",
    "command_as_run", "exit_code", "stdout", "stderr", "captured_on", "captured_by",
    "blast_confirmed", "undo_executed", "command_hash_at_capture", "verify_result",
)


# {by, on, host, capture} — extract/schema.py's VERIFIED_RECEIPT_FIELDS, kept
# textually identical (CEO ruling, per-version verified; capture-review-run1-
# 2026-09-18.md RILEY-F1).
VERIFIED_RECEIPT_FIELDS = ("by", "on", "host", "capture")


# J3 (VER-003): closed grammars for the two receipt fields that had none.
# `host` gets an RFC-1123-ish hostname shape — the app already has this exact
# rule for the `hostname` field type, reused here rather than restated. The
# capture path is closed to the shape import_captures.py / build.py actually
# write: tests/captures/<release>/<slug>.json, no traversal, no case tricks.
RECEIPT_HOST_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,62}$")
RECEIPT_CAPTURE_PATH_RE = re.compile(r"^tests/captures/(7|8|9|10)/[a-z0-9-]+\.json$")


def load_golden_commands():
    """Load tests/fixtures/golden-commands.json, the hand-authored validity
    oracle (MCR-SEC-015/021). gate_q16() binds generator receipts to it (J1,
    VER-001): a generator entry has no rhel_versions[v].command to diff a
    capture against, so without this table a template edit can never
    invalidate the receipts that describe its old behaviour. Returns
    (dict_or_None, error_string_or_None); reads REPO fresh on every call
    (never cached at import time) so a test that patches qa.REPO — see
    tests/test_q16_receipts.py — sees its own fixture copy, not the real one.
    """
    path = os.path.join(REPO, "tests", "fixtures", "golden-commands.json")
    if not os.path.isfile(path):
        return None, "tests/fixtures/golden-commands.json is missing"
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (ValueError, OSError) as exc:
        return None, "tests/fixtures/golden-commands.json could not be read: %s" % exc


# trailing parenthetical, e.g. "Caleb Stone (SME)" -> "Caleb Stone" — stripped
# BEFORE whitespace collapse so a name can never smuggle whitespace through it.
_TRAILING_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")


def normalize_person_name(s):
    """J2 (VER-002): casefold, collapse ALL Unicode whitespace (incl. NBSP) to
    a single space, strip, after removing one trailing parenthetical. This
    closes the accidental bypass (case, padding, doubled/NBSP whitespace,
    "(SME)" suffix) — it does NOT and cannot close a deliberate alias like
    "C. Stone"; that half is closed by the roster lookup, not by this
    function, and the gate says so (see gate_q16's own diagnostic line)."""
    if not isinstance(s, str):
        return ""
    s = _TRAILING_PAREN_RE.sub("", s)
    s = "".join(" " if ch.isspace() else ch for ch in s)
    s = re.sub(r" +", " ", s).strip()
    return s.casefold()


def load_roster():
    """Load content-src/roster.json, the closed two-person-rule roster (J2,
    VER-002): {"people": [{"name": ..., "roles": [...]}, ...]}. Returns
    (dict_or_None, error_string_or_None) where the dict maps a NORMALISED
    name (normalize_person_name) to its set of roles. Same REPO-fresh-read
    rule as load_golden_commands(), for the same test-patching reason.
    """
    path = os.path.join(REPO, "content-src", "roster.json")
    if not os.path.isfile(path):
        return None, "content-src/roster.json is missing"
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (ValueError, OSError) as exc:
        return None, "content-src/roster.json could not be read: %s" % exc
    people = raw.get("people") if isinstance(raw, dict) else None
    if not isinstance(people, list) or not people:
        return None, "content-src/roster.json has no non-empty 'people' list"
    roster = {}
    for person in people:
        if not isinstance(person, dict):
            continue
        name = person.get("name")
        roles = person.get("roles")
        if not isinstance(name, str) or not name or not isinstance(roles, list):
            continue
        roster[normalize_person_name(name)] = set(roles)
    return roster, None


def load_capture_file(rel_path):
    """Read+parse a capture record by its REPO-relative path (a receipt's own
    `capture` field). Returns (cap_dict_or_None, error_string_or_None)."""
    if not isinstance(rel_path, str) or not rel_path:
        return None, "receipt's capture path is empty"
    abs_path = os.path.join(REPO, rel_path)
    if not os.path.isfile(abs_path):
        return None, "capture file '%s' does not exist" % rel_path
    try:
        with open(abs_path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (ValueError, OSError) as exc:
        return None, "capture file '%s' could not be read: %s" % (rel_path, exc)


def gate_q16(ctx):
    """Capture backing. Two independent claims are checked here:

    1. Every stig[] row that carries expected_output has a real capture record
       behind it, keyed entry_id|stig_id|rhel_version (unchanged from before
       the per-version verified ruling — expected_output is captured, never
       typed, regardless of whether anything is marked verified).

    2. Every per-version verified receipt is backed by ITS OWN capture file
       for that exact (entry, rhel_version) pair: the receipt names a capture
       path, that file exists and validates, its entry_id/rhel_version match
       the (entry, version) the receipt sits on, its command_hash_at_capture
       matches sha256(command_as_run) (not tampered/hand-edited), and — for a
       fixed rhel_versions command (never a generator's, MCR-SEC-006) — the
       captured command_as_run still matches the command this build actually
       assembles for that version today (ctx["data"] is the SHIPPED artifact,
       so same_as chains are already resolved here exactly the way build.py
       resolved them). Content edited since capture drifts this check red.
       Finally, the receipt's `by` must not equal the capture's `captured_by`
       — SME captures, QA verifies; the same name cannot do both.

    3. Closed grammars (J3, VER-003) for `host` (RFC-1123-ish hostname,
       cross-checked against the capture's own `host`) and `capture` (must
       be a literal tests/captures/<release>/<slug>.json path — no
       traversal, no other shape).
    """
    f, d = [], []
    data = ctx["data"]
    captures = (data["expected_output"].get("captures") or {})
    n_exp = 0
    n_receipts = 0
    if not data["commands"]["entries"]:
        f.append(empty_set_failure(
            "command entries whose expected_output and verified receipts to check",
            "'expected output is captured, never typed' is a claim about entries, and there are "
            "none to make it about"))
    for e in data["commands"]["entries"]:
        eid = e.get("id")
        for s in (e.get("stig") or []):
            if s.get("expected_output"):
                n_exp += 1
                key = "%s|%s|%s" % (eid, s.get("stig_id"), s.get("rhel_version"))
                cap = captures.get(key)
                if not cap:
                    f.append("entry %s stig %s: expected_output with no capture record %s"
                             % (eid, s.get("stig_id"), key))
                    continue
                for field in CAPTURE_REQUIRED_FIELDS:
                    if field not in cap:
                        f.append("capture %s: missing required field %s" % (key, field))

        ver = e.get("verified")
        if not isinstance(ver, dict):
            continue
        for v in VERSIONS:
            receipt = ver.get(v)
            if not isinstance(receipt, dict):
                continue
            n_receipts += 1
            for field in VERIFIED_RECEIPT_FIELDS:
                if not receipt.get(field):
                    f.append("entry %s verified['%s']: receipt has no '%s'" % (eid, v, field))

            # J3 (VER-003) — closed grammar on the receipt's own fields,
            # independent of whether the capture they name can even be
            # loaded. `by`'s grammar is the roster itself, enforced below.
            host = receipt.get("host")
            if host is not None and not RECEIPT_HOST_RE.match(host or ""):
                f.append("entry %s verified['%s']: receipt's host ('%s') does not match the "
                         "closed hostname grammar %s"
                         % (eid, v, host, RECEIPT_HOST_RE.pattern))
            cap_path = receipt.get("capture")
            if cap_path is not None and not RECEIPT_CAPTURE_PATH_RE.match(cap_path or ""):
                f.append("entry %s verified['%s']: receipt's capture path ('%s') does not match "
                         "the closed grammar %s"
                         % (eid, v, cap_path, RECEIPT_CAPTURE_PATH_RE.pattern))
            cap, err = load_capture_file(cap_path)
            if err:
                f.append("entry %s verified['%s']: %s" % (eid, v, err))
                continue
            if not isinstance(cap, dict):
                f.append("entry %s verified['%s']: capture '%s' is not a JSON object"
                         % (eid, v, cap_path))
                continue
            if cap.get("entry_id") != eid or str(cap.get("rhel_version")) != v:
                f.append("entry %s verified['%s']: capture '%s' is for %s/%s, not this entry/version "
                         "pair — a receipt's capture must back that exact (entry, rhel_version)"
                         % (eid, v, cap_path, cap.get("entry_id"), cap.get("rhel_version")))
                continue
            for field in CAPTURE_REQUIRED_FIELDS:
                if field not in cap:
                    f.append("entry %s verified['%s']: capture '%s' missing required field '%s'"
                             % (eid, v, cap_path, field))
            if "command_as_run" in cap and "command_hash_at_capture" in cap:
                computed = hashlib.sha256(cap["command_as_run"].encode("utf-8")).hexdigest()
                if computed != cap["command_hash_at_capture"]:
                    f.append("entry %s verified['%s']: capture '%s' command_hash_at_capture does "
                             "not match sha256(command_as_run) — tampered or hand-edited capture "
                             "record" % (eid, v, cap_path))
            if host and cap.get("host") and host != cap.get("host"):
                f.append("entry %s verified['%s']: receipt's host ('%s') does not match the "
                         "capture's own host ('%s') — a receipt's host claims where it was "
                         "verified, and that must be the machine the capture says it ran on"
                         % (eid, v, host, cap.get("host")))
            if "template" not in e:
                current = ((e.get("rhel_versions") or {}).get(v) or {}).get("command")
                run_as = cap.get("command_as_run")
                if current and run_as is not None and run_as != current:
                    f.append("entry %s verified['%s']: capture's command_as_run ('%s') no longer "
                             "matches the RHEL %s command this build assembles today ('%s') — "
                             "content changed since capture; re-capture before re-verifying"
                             % (eid, v, run_as, v, current))
            else:
                # J1 (VER-001): a generator has no rhel_versions[v].command to
                # diff against, so bind the receipt to the hand-authored
                # validity oracle instead — the golden table already states
                # the exact command this generator must emit per release.
                golden, golden_err = load_golden_commands()
                if golden_err:
                    f.append("entry %s verified['%s']: %s — a generator receipt cannot be bound "
                             "to a command with nothing to diff it against" % (eid, v, golden_err))
                else:
                    grow = (golden.get("generators") or {}).get(eid)
                    if grow is None:
                        f.append("entry %s verified['%s']: no golden-table row for generator "
                                 "'%s' in tests/fixtures/golden-commands.json — a template edit "
                                 "to this generator cannot be detected without one" % (eid, v, eid))
                    else:
                        golden_cmd = (grow.get("commands") or {}).get(v)
                        run_as = cap.get("command_as_run")
                        if golden_cmd and run_as is not None and run_as != golden_cmd:
                            f.append("entry %s verified['%s']: capture's command_as_run ('%s') no "
                                     "longer matches the golden-table command generator '%s' "
                                     "emits on RHEL %s ('%s') — the template changed since "
                                     "capture; re-capture before re-verifying"
                                     % (eid, v, run_as, eid, v, golden_cmd))
            # J2 (VER-002) — the two-person rule, normalised and roster-closed.
            by = receipt.get("by")
            captured_by = cap.get("captured_by")
            by_norm = normalize_person_name(by) if by else None
            captured_norm = normalize_person_name(captured_by) if captured_by else None
            roster, roster_err = load_roster()
            if roster_err:
                if by or captured_by:
                    f.append("entry %s verified['%s']: %s — the two-person rule cannot be "
                             "enforced with no roster to check names against" % (eid, v, roster_err))
            else:
                if by:
                    by_roles = roster.get(by_norm)
                    if by_roles is None or "QA" not in by_roles:
                        f.append("entry %s verified['%s']: receipt's by ('%s') is not a QA-roled "
                                 "member of the roster (content-src/roster.json) — QA verifies, "
                                 "and only a roster member holding the QA role may sign as 'by'"
                                 % (eid, v, by))
                if captured_by:
                    cap_roles = roster.get(captured_norm)
                    if cap_roles is None or "SME" not in cap_roles:
                        f.append("entry %s verified['%s']: capture's captured_by ('%s') is not "
                                 "an SME-roled member of the roster (content-src/roster.json) — "
                                 "SME captures, and only a roster member holding the SME role "
                                 "may sign as 'captured_by'" % (eid, v, captured_by))
            if by_norm and captured_norm and by_norm == captured_norm:
                f.append("entry %s verified['%s']: receipt's by ('%s') and capture's captured_by "
                         "('%s') normalise to the same person — SME captures, QA verifies; one "
                         "person cannot do both for the same receipt" % (eid, v, by, captured_by))
    if not f:
        d.append("%d expected_output blocks, %d capture records — expected output is captured, never typed "
                 "(content validation protocol runs are CR-T-34)" % (n_exp, len(captures)))
        d.append("%d per-version verified receipt(s), each backed by its own capture file for that "
                 "exact entry/version pair, hash-matched against the currently assembled command "
                 "(golden-table-bound for generators, J1), roster-checked by role (J2), and "
                 "grammar-closed on host/capture (J3)" % n_receipts)
        d.append("two-person rule residual (J2, VER-002): normalisation (casefold + collapsed "
                 "whitespace incl. NBSP + one stripped trailing parenthetical) closes only the "
                 "ACCIDENTAL bypass. A deliberate alias (e.g. 'C. Stone') is NOT closable by any "
                 "string comparison of names; it is refused here because it does not resolve "
                 "against the closed roster in content-src/roster.json, not because it is "
                 "detected as an alias of a real roster member.")
    return f, d


def gate_q17(ctx):
    f, d = [], []
    html, shell = ctx["html"], ctx["shell"]
    inline = re.findall(r"<[a-zA-Z][^>]*?\s(on[a-z]{2,})\s*=", shell)
    if inline:
        f.append("inline event-handler attribute(s) in the shipped file: %s" % sorted(set(inline)))
    else:
        d.append("zero inline on*= event-handler attributes")
    for bad in ("eval(", "new Function("):
        if bad in shell:
            f.append("%s present in the app script" % bad)
    for need in ("function esc(", "function escapeAttr("):
        if need not in shell:
            f.append("%s definition missing" % need.replace("function ", "").replace("(", "()"))
    # trojan-source scan — the hand-written shell AND the data island (C10).
    shell_trojan = trojan_scan(shell, "the shipped shell")
    island_trojan = trojan_scan(ctx["island"], "the embedded data island")
    f.extend(shell_trojan)
    f.extend(island_trojan)
    if not shell_trojan:
        d.append("no raw C0/C1 control, zero-width, or bidirectional-override character anywhere in "
                 "the hand-written shell")
    if not island_trojan:
        d.append("the same scan over the %.2f MB data island: clean. DISA fix text is rendered AND "
                 "copied into evidence, so vendor prose gets the trojan-source scan too — the earlier "
                 "exclusion was a blind spot (MCR-SEC-004 / condition C10)"
                 % (ctx["island_len"] / 1024.0 / 1024.0))

    # mechanical render-sink audit (MCR-SEC-004)
    sink_f, audited = render_sink_failures(shell)
    f.extend(sink_f)
    if not sink_f:
        d.append("%d innerHTML/accumulator/push expressions audited; every concatenated segment is a "
                 "string literal, an esc()/escapeAttr()/escapeRegex() call, or an accumulator this "
                 "gate derived from the source and audited in turn" % audited)
        d.append("derived accumulators: %s" % (", ".join(sorted(derive_accumulators(shell))) or "none"))
        d.append("forbidden sinks absent: %s"
                 % ", ".join(label for _rx, label in FORBIDDEN_SINKS))
        computed = computed_property_expressions(shell)
        d.append("computed member assignments read: %d (%s) — every property expression is an "
                 "identifier, a number or a dotted/indexed chain; no bracketed sink name, no "
                 "property name built from string literals here or anywhere else in the shell "
                 "(MCR-SEC-014)"
                 % (len(computed), ", ".join("[%s]" % p for p, _c in computed) or "none"))
        d.append("residual, stated rather than claimed away: this rule reads names built from "
                 "STRING LITERALS. A property name produced at run time from data — a character "
                 "array, an index into the content island — is not visible to any scan of the "
                 "source, and no regex gate can be. Q17 is an accident-prevention gate over "
                 "hand-written code that CODEOWNERS reviews, not a sandbox (MCR-SEC-014)")
        for k, why in sorted(INNERHTML_ALLOWLIST.items()):
            d.append("allow-list: %s — %s" % (k, why))
    return f, d


# Every count gate_q18 reports out of the harness's JSON. AL-GATE3-006: these
# used to be read with rep["checks"] and friends, so a report that PARSED but was
# key-incomplete — a partial write, a field renamed in hostile_harness.js and not
# mirrored here, a future --json shape change — raised an uncaught KeyError in
# the middle of qa.py instead of printing a named FAIL. It failed closed (Python
# exits non-zero), so it was never a silent pass; it was a stack trace that looks
# identical whether the harness broke or whether it caught something real.
HARNESS_REPORT_KEYS = ("checks", "field_types", "vectors", "versions", "rejected",
                       "quoted_safe", "positive_controls", "invariants", "assembler_bytes")


def harness_report_failures(rep, returncode, stderr=""):
    """Consume the hostile harness's JSON report. Returns (failures, details).

    Nothing in here trusts the shape of `rep`. Q18 is the gate that stands
    between a form field and a command a human runs as root, and its own failure
    mode should be as legible as every other gate's: one FAIL line, naming the
    reason, never a traceback.
    """
    f, d = [], []
    if not isinstance(rep, dict):
        f.append("the harness report is a JSON %s, not an object — qa.py and "
                 "tests/hostile_harness.js disagree about the shape of --json output, and this "
                 "gate is reading something it does not understand (AL-GATE3-006)"
                 % type(rep).__name__)
        return f, d

    failures = rep.get("failures")
    if failures is None:
        failures = []
    elif not isinstance(failures, list):
        f.append("the harness report's 'failures' is a %s, not a list — the one field this gate "
                 "reads to decide PASS or FAIL is not the field it expected (AL-GATE3-006)"
                 % type(failures).__name__)
        failures = []
    for line in failures:
        f.append("hostile input: %s" % line)

    missing = [k for k in HARNESS_REPORT_KEYS if k not in rep]
    if missing:
        f.append("the harness report is missing the field(s) %s. A report that PARSES but does "
                 "not carry what this gate reads means the harness and qa.py have drifted apart, "
                 "or the harness died partway through writing it — either way nothing here has "
                 "been proved (AL-GATE3-006)" % ", ".join(missing))
    wrong = [k for k in HARNESS_REPORT_KEYS
             if k in rep and (isinstance(rep[k], bool) or not isinstance(rep[k], int))]
    if wrong:
        f.append("the harness report carries a non-integer where this gate expects a count: %s "
                 "(AL-GATE3-006)"
                 % ", ".join("%s=%r" % (k, rep[k]) for k in wrong))

    if not missing and not wrong and not rep["checks"]:
        f.append("the harness reported ZERO checks. A sweep that ran nothing rejects nothing and "
                 "quotes nothing safely, so it passes by having done no work — the same empty-set "
                 "fail-open Q9 has guarded since CR-T-07 (AL-GATE3-004)")

    if returncode != 0 and not failures:
        f.append("the harness exited %d without naming a failure: %s" % (returncode, (stderr or "")[:300]))

    if not f:
        d.append("%d checks over %d field types x %d vectors x %d releases x 3 argument shapes, plus "
                 "5 rich-rule sub-fields: %d rejected outright, %d accepted and provably confined to a "
                 "single-quoted token"
                 % (rep["checks"], rep["field_types"], rep["vectors"], rep["versions"],
                    rep["rejected"], rep["quoted_safe"]))
        d.append("%d positive controls (every field type's benign value still assembles on every "
                 "release, in every argument shape) and %d invariants — a validator that rejected "
                 "everything would fail this gate, not pass it"
                 % (rep["positive_controls"], rep["invariants"]))
        d.append("assembler extracted from the shipped artifact (%d bytes), not from template.html"
                 % rep["assembler_bytes"])
        d.append("the report was checked for shape before it was believed: every count this line "
                 "prints was proved present and integral first, so a truncated or renamed report "
                 "is a FAIL line and never a traceback (AL-GATE3-006)")
    return f, d


def gate_q18(ctx):
    """Hostile-input harness — threat-model-v1 §11 merge-gate #4, plus gate #9.

    Runs tests/hostile_harness.js against the SHIPPED artifact, not against
    template.html: the harness lifts the assembler block out of dist/ and runs
    every fixture vector through it, so the code this gate clears is byte-for-byte
    the code that crosses the air gap.

    Node is REQUIRED here. Everywhere else in this file Node is optional and its
    absence downgrades to PENDING, because a missing syntax check is an
    inconvenience. A missing injection check is not: this gate is the only thing
    between a form field and a command a human runs as root, so a runner without
    Node fails it rather than quietly passing a build nobody tested.
    """
    f, d = [], []
    harness = os.path.join(REPO, "tests", "hostile_harness.js")
    fixture = os.path.join(REPO, "tests", "fixtures", "hostile-inputs.json")
    if not os.path.exists(harness) or not os.path.exists(fixture):
        f.append("the hostile-input harness or its fixture is missing — CI merge-gate #4 cannot run")
        return f, d

    # gate #9, quoting-domain confusion: the three escaping domains must never nest.
    shell = ctx["shell"]
    # MCR-SEC-010: SHELL-ONLY until the Ansible generator lands (CR-T-17+). The
    # YAML half of this gate used to pass on a quoter with no call site, which
    # read as "Ansible YAML output is proven safe" and was not true. If a YAML
    # quoter comes back, it must come back with a YAML-parsing oracle in the
    # harness in the same commit — the harness enforces that and fails here.
    for outer, inner in (("shQuote", "esc"), ("shQuote", "escapeAttr"),
                         ("esc", "shQuote"), ("escapeAttr", "shQuote")):
        if re.search(r"\b%s\s*\(\s*%s\s*\(" % (outer, inner), shell):
            f.append("quoting-domain confusion: %s(%s(...)) — a shell quoter and a DOM escaper are "
                     "two different jobs (threat-model-v1 §3.2)" % (outer, inner))
    if "yamlQuote" in shell:
        f.append("a YAML quoter is present in the shipped shell. MCR-SEC-010 removed the dead one; "
                 "the sink that brings it back ships a YAML-parsing oracle in "
                 "tests/hostile_harness.js in the SAME commit, and this gate's YAML half is "
                 "re-enabled then — not before")
    if not f:
        d.append("no shQuote/esc/escapeAttr call is nested inside another — the escaping domains "
                 "stay separate (threat-model-v1 §11 gate 9). SHELL-ONLY: there is no YAML sink in "
                 "this build and no dead YAML quoter pretending otherwise (MCR-SEC-010)")

    node = shutil.which("node")
    if not node:
        f.append("node is not installed on this runner. The command assembler is JavaScript and "
                 "this gate runs it; CI installs Node (actions/setup-node@v4) precisely so this "
                 "check cannot be skipped on the build that needed it.")
        return f, d
    proc = subprocess.run([node, harness, ctx["artifact"], "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace").strip()
    try:
        rep = json.loads(out)
    except ValueError:
        f.append("the harness produced no JSON report: %s" % (err or out)[:400])
        return f, d
    rf, rd = harness_report_failures(rep, proc.returncode, err)
    f.extend(rf)
    d.extend(rd)
    return f, d


def gate_q19(ctx):
    """Escaper behaviour — the functions ESCAPE, not merely exist (AL-GATE3-001).

    Q17 audits call sites: every value reaching a render sink is a literal, an
    accumulator this gate derived and audited in turn, or an
    esc()/escapeAttr()/escapeRegex() call. That is a real property and it stays.
    What it cannot be is a proof that those three functions do anything, because
    `function esc(s){return s;}` changes no call site at all — Al Kowalski's
    Gate 3 review reproduced exactly that against render_sink_failures() and got
    back zero failures over four audited expressions.

    So this gate stops reading and starts running. The three definitions are
    lifted verbatim out of the SHIPPED artifact — the same discipline Q18's
    harness applies to the assembler block, for the same reason: the code that
    clears the gate has to be the code that crosses the air gap. They go through
    tests/escaper_probe.js under node against a hostile corpus, and the probe
    proves it can fail, on this runner, on every run, before it reports anything.

    Node is REQUIRED, as it is for Q18. An escaping check that downgrades itself
    to PENDING when the runner is thin is a fail-open wearing a politer word.
    """
    return escaper_failures(ctx["shell"])

LONG_OPTION_RE = re.compile(r"--[a-z0-9][a-z0-9-]*")
COVERAGE_BASELINE = os.path.join(REPO, "content-src", "flag_coverage_baseline.json")
# AL-GATE3-010: "7" was absent, so content-src/flag_coverage_baseline.json's six
# coverage["7"] rows (chage, journalctl, systemctl, useradd, usermod, yum) were
# read by nothing.
RAW_DIR_FOR = {"7": "rhel7", "8": "rhel8", "10": "rhel10"}


def _long_options_in_raw(raw_dir, cli):
    """Distinct long options the committed raw capture for this tool mentions.

    RHEL 8/10 raw dumps are man pages (`.man.txt`). UBI7 has no man-db (CR-T-12),
    so every RHEL 7 dump under content-src/raw/rhel7/ is `--help` output
    (`.help.txt`) instead. AL-GATE3-010: filtering to `.man.txt` only made this
    return None for every RHEL 7 tool -- the raw files existed and were never
    looked at. Both suffixes are read; the long-option regex does not care which
    kind of text it is scanning.
    """
    if not os.path.isdir(raw_dir):
        return None
    files = sorted(f for f in os.listdir(raw_dir)
                   if f.startswith(cli + ".") and f.endswith((".man.txt", ".help.txt")))
    if not files:
        return None
    found = set()
    for name in files:
        with open(os.path.join(raw_dir, name), encoding="utf-8", errors="replace") as fh:
            found |= set(LONG_OPTION_RE.findall(fh.read()))
    return found


def coverage_baseline_expiry_failures(baseline, today=None):
    """MCR-SEC-020, condition F3 — the ratchet has to be able to expire.

    An accepted residual with a gate holding it steady is a good answer for a
    fortnight and a bad one forever: the gate stops being a countdown and starts
    being the plan. So the baseline names an owner and a date, and after that
    date this returns a failure until someone re-dates the file — which means
    either the extractor fix landed and the numbers came down, or a human
    decided, in writing, to extend it.
    """
    import datetime
    owner = baseline.get("_retire_owner")
    by = baseline.get("_retire_by")
    if not owner or not by:
        return ["the flag-coverage baseline names no _retire_owner/_retire_by. A ratchet with no "
                "retirement plan is not a countdown, it is the plan (MCR-SEC-020, condition F3)"]
    try:
        deadline = datetime.date(*[int(x) for x in by.split("-")])
    except (ValueError, TypeError):
        return ["the flag-coverage baseline's _retire_by %r is not an ISO date" % by]
    now = today or datetime.date.today()
    if now > deadline:
        return ["the flag-coverage baseline expired on %s and has not been re-dated. Owner: %s. "
                "Either CR-T-09's extractor fix landed (regenerate this file against the new "
                "dictionaries) or the residual needs extending in writing — but it stops being "
                "accepted by default (MCR-SEC-020, condition F3)" % (by, owner)]
    return []


def gate_q20(ctx):
    """MCR-SEC-020 (condition E5) — dictionary coverage, and citations that point at the flag.

    Marcus Reed's finding was not that the flag dictionary has a gap. It was that
    NOTHING COULD SEE ONE: Q15 re-runs the extractor and diffs the output against
    itself, so a systematically skipped option class produces a byte-identical
    re-parse and a PASS. `--add-rich-rule` is absent from flags_rhel8.json and
    flags_rhel10.json and present in the raw capture twice over, and every gate in
    this file was green.

    Two halves:

    (a) COVERAGE. Distinct long options in each committed raw capture, against the
        long option names the dictionary carries for that tool. Long options only,
        and the gate says so rather than implying more: they are the countable
        class in man-page text, and the option this finding was raised about is
        one. The raw count is an upper bound — it picks up prose and per-subcommand
        options the top-level parser never sees — so this is a REGRESSION gate
        against content-src/flag_coverage_baseline.json, which records the gap with
        the date it was accepted and the ticket that owns closing it (CR-T-09/10).
        A shortfall that GROWS fails. A shortfall that shrinks reports, and asks
        for the baseline to be tightened, because a stale baseline is a gate that
        has stopped measuring.

    (b) CITATIONS (MCR-SEC-019). A generator whose source cites a raw capture line
        must cite a line that actually shows an option the generator EMITS.
        gen-fw-allow-service cited firewall-cmd.man.txt#L310 — `--add-service`,
        an option it does not emit, since it composes a rich rule — which is
        threat-model §4's Explainer row in the provenance rather than in the panel.
    """
    f, d, p = [], [], []
    data = ctx.get("data")

    if not os.path.exists(COVERAGE_BASELINE):
        f.append("content-src/flag_coverage_baseline.json is missing — MCR-SEC-020's coverage "
                 "gate has no recorded baseline, so it cannot tell a gap from a regression")
        return f, d, p
    with open(COVERAGE_BASELINE, encoding="utf-8") as fh:
        baseline = json.load(fh)
    f.extend(coverage_baseline_expiry_failures(baseline))
    for key in ("_accepted_on", "_accepted_by", "_ticket", "_retire_owner", "_retire_by"):
        if not baseline.get(key):
            f.append("the flag-coverage baseline carries no %s — E5 asks for the gap closed OR "
                     "accepted WITH A DATE, and an undated acceptance is neither" % key)

    measured, stale = 0, []
    for rel, raw_name in sorted(RAW_DIR_FOR.items()):
        dict_path = os.path.join(REPO, "content", "flags_rhel%s.json" % rel)
        if not os.path.exists(dict_path):
            f.append("content/flags_rhel%s.json is missing" % rel)
            continue
        with open(dict_path, encoding="utf-8") as fh:
            dictionary = json.load(fh)
        raw_dir = os.path.join(REPO, "content-src", "raw", raw_name)
        rel_baseline = (baseline.get("coverage") or {}).get(rel) or {}
        for cli, rec in sorted((dictionary.get("clis") or {}).items()):
            raw_long = _long_options_in_raw(raw_dir, cli)
            if raw_long is None:
                continue                      # no committed capture for this tool on this release
            dict_long = set()
            for fl in rec.get("flags") or []:
                for n in fl.get("names") or []:
                    if n.startswith("--"):
                        dict_long.add(n)
            missing = sorted(raw_long - dict_long)
            measured += 1
            row = rel_baseline.get(cli)
            if row is None:
                f.append("RHEL %s / %s: the flag-coverage baseline has no row for this tool. A tool "
                         "with no recorded coverage has never been measured" % (rel, cli))
                continue
            accepted = row.get("accepted_missing")
            if not isinstance(accepted, int):
                f.append("RHEL %s / %s: the baseline row has no accepted_missing count" % (rel, cli))
                continue
            if len(missing) > accepted:
                f.append("RHEL %s / %s: the flag dictionary now misses %d long options documented in "
                         "the raw capture, up from the accepted %d. New: %s. A dictionary that loses "
                         "ground is an Explainer that quietly says 'unverified' about more of the "
                         "product (MCR-SEC-020)"
                         % (rel, cli, len(missing), accepted, ", ".join(missing[:8])))
            elif len(missing) < accepted:
                stale.append("RHEL %s / %s: %d missing, baseline accepts %d"
                             % (rel, cli, len(missing), accepted))
            if missing:
                d.append("RHEL %s / %s: %d of %d long options in the capture are in the dictionary "
                         "(%d missing, accepted %s)"
                         % (rel, cli, len(raw_long) - len(missing), len(raw_long), len(missing),
                            baseline.get("_accepted_on")))
    if measured == 0:
        f.append("no tool was measured for dictionary coverage — the gate ran and proved nothing")
    else:
        d.append("flag-dictionary coverage measured for %d tool/release pairs against the baseline "
                 "accepted on %s (%s); ratchet retires %s, owner %s"
                 % (measured, baseline.get("_accepted_on"), baseline.get("_ticket"),
                    baseline.get("_retire_by"), baseline.get("_retire_owner")))
    for line in stale:
        d.append("coverage IMPROVED beyond the baseline — tighten it: " + line)

    # (b) MCR-SEC-019: a cited raw line must show an option the generator emits.
    if data is None:
        p.append("no parsed island — the citation half of Q20 needs content/commands.json via the "
                 "built artifact")
        return f, d, p
    cited = 0
    for e in (((data.get("commands") or {}).get("entries")) or []):
        if not e.get("template"):
            continue
        ref = ((e.get("source") or {}).get("url_or_man")) or ""
        if "#L" not in ref:
            continue
        path_part, _, line_part = ref.partition("#L")
        target = os.path.join(REPO, path_part)
        if not os.path.exists(target):
            f.append("%s cites %s, which does not exist" % (e["id"], ref))
            continue
        try:
            line_no = int(line_part)
        except ValueError:
            f.append("%s cites %s, whose line anchor is not a number" % (e["id"], ref))
            continue
        with open(target, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        window = "\n".join(lines[max(0, line_no - 4):line_no + 4])
        # The option that DEFINES this generator is the one bound to a value or
        # to a composed rich rule, not a decoration like --permanent that half
        # the firewall-cmd man page mentions. gen-fw-allow-service cited a line
        # showing --add-service and --permanent; --permanent is emitted, so a
        # laxer rule here would have passed the very citation MCR-SEC-019 raised.
        primary = set()
        decoration = set()
        for tok in e["template"]:
            flag = tok.get("flag")
            if isinstance(flag, str) and flag.startswith("-"):
                primary.add(flag)
                continue
            lit = tok.get("lit")
            if isinstance(lit, str) and lit.startswith("-"):
                decoration.add(lit)
        emitted = primary or decoration
        if not emitted:
            d.append("%s cites %s and emits no option token of its own" % (e["id"], ref))
            continue
        cited += 1
        if not any(opt in window for opt in emitted):
            f.append("%s cites %s, and the eight lines around it show none of the options it "
                     "actually emits (%s). An explanation that does not match the flag present is "
                     "threat-model §4's Explainer row, landing in the provenance instead of the "
                     "panel (MCR-SEC-019)" % (e["id"], ref, ", ".join(sorted(emitted))))
        else:
            d.append("%s cites %s, which shows %s" % (e["id"], ref,
                                                      ", ".join(sorted(o for o in emitted if o in window))))
    d.append("%d generator citations point at a raw capture line and were checked against the "
             "options that generator emits" % cited)
    return f, d, p


# ---------------------------------------------------------------------------
# Q21 — raw trojan characters in tracked SOURCE files
#
# Q17 scans the built artifact's shell and data island: it proves what crosses
# the air gap is clean. This proves the REPO is, which is a different corpus and
# a different failure mode. Most tracked files never reach the artifact — tests,
# fixtures, docs — and the way this goes wrong is not an attacker, it is an
# editor: tests/fixtures/hostile-inputs.json states its invisible-character
# vectors as JSON \u escapes ON PURPOSE, so the file that describes U+202E is
# itself readable and diffable, and a round-trip through json.dump(...,
# ensure_ascii=False) turned eight of them into the raw characters they name.
# That is how it happened here, at dd01ad7, by my own hand.
#
# Deliberately NOT folded into Q17: a Q17 failure would then mean either "the
# shipped artifact is poisoned" or "someone's editor rewrote a fixture", and a
# gate whose failure is ambiguous costs more than it saves. Q17 also reads
# ctx["shell"]; this needs `git ls-files`.
#
# The character set is qa.py's own TROJAN_RANGES — the one Q17 already uses.
# Two statements of the same table is one too many (MCR-SEC-006's doctrine, and
# tests/test_schema.py already holds that line for the field-type and rich-rule
# tables). It is strictly broader than "bidi and line separators": it carries C0
# and C1 minus \t \n \r, soft hyphen, the zero-width run, the bidi isolates, and
# U+2065 (MCR-SEC-009).
#
# NOTHING is excluded. The first cut of this gate skipped stig-src/ and
# content-src/raw/ as pinned vendor captures; Marcus Reed asked for the narrower
# rule (MCR-SEC-025, condition F1) and the measurement backs him: across both
# trees, 62 files, the only hit of any kind is ONE leading byte-order mark, in
# stig-src/U_CCI_List.xml. So the exclusion bought nothing and cost the two
# largest directories in the repository. A U+FEFF at OFFSET 0 is file framing
# and is allowed; a U+FEFF anywhere else is exactly the trojan this gate is for.
# ---------------------------------------------------------------------------
TROJAN_SCAN_EXCLUDE = ()


def raw_trojan_failures(paths, root=None):
    """Raw control/bidi/zero-width characters in these files. One message each.

    Takes an explicit path list rather than walking anything itself, so the
    negative control can hand it a planted file and watch it fire — a scanner
    that has only ever been pointed at clean input is not a scanner.
    """
    failures = []
    root = root or REPO
    for rel in paths:
        full = rel if os.path.isabs(rel) else os.path.join(root, rel)
        try:
            with open(full, "rb") as fh:
                raw = fh.read()
        except (IOError, OSError):
            continue                                  # deleted or unreadable: not this gate's call
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue                                  # binary or non-UTF-8: nothing to say
        for m in TROJAN_RE.finditer(text):
            ch = m.group()
            if m.start() == 0 and ch == "\ufeff":
                continue                              # a leading BOM is framing, not content
            byte = len(text[:m.start()].encode("utf-8"))
            around = text[max(0, m.start() - 12):m.start() + 12].replace("\n", "\\n")
            failures.append("%s: raw U+%04X at byte %d, near %r. This character must be written as "
                            "an escape its format provides (JSON \\u%04x, a source-language escape), "
                            "never as the character itself — a file that spells out an invisible or "
                            "bidirectional character is a file no reviewer can read correctly"
                            % (rel, ord(ch), byte, around, ord(ch)))
    return failures


def tracked_text_files():
    """`git ls-files`, minus the pinned vendor captures. Empty if git is absent."""
    git = shutil.which("git")
    if not git:
        return None
    proc = subprocess.run([git, "ls-files", "-z"], cwd=REPO,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return None
    names = [n for n in proc.stdout.decode("utf-8", "replace").split("\0") if n]
    if not TROJAN_SCAN_EXCLUDE:
        return names
    return [n for n in names if not n.startswith(TROJAN_SCAN_EXCLUDE)]


def gate_q21(ctx):
    """No tracked source file carries a raw trojan character (see the block above)."""
    f, d, p = [], [], []
    paths = tracked_text_files()
    if paths is None:
        f.append("git ls-files is unavailable, so the tracked-file corpus cannot be enumerated. "
                 "This gate reports FAIL rather than skipping: a scan with nothing to scan is a "
                 "PASS that means nothing")
        return f, d, p
    if len(paths) < 50:
        f.append("git ls-files returned only %d files to scan — the corpus collapsed and this gate "
                 "would pass on an empty repository" % len(paths))
        return f, d, p
    f.extend(raw_trojan_failures(paths))
    d.append("%d tracked files scanned for raw control, bidi and zero-width characters — every "
             "file git tracks, nothing excluded. The one allowance is a U+FEFF byte-order mark at "
             "offset 0, which only stig-src/U_CCI_List.xml uses (MCR-SEC-025, condition F1)"
             % len(paths))
    return f, d, p


# ---------------------------------------------------------------------------
# Q22 — declared tool is the invoked binary, and every flag can be explained
#
# Marcus Reed's Panels review, PANEL-001 / condition G1. firewalld-service-active
# declared tool: "firewall-cmd" and journald-service-active declared
# tool: "journalctl", but every rhel_versions command on both is a systemctl
# invocation. The inspector's flag panel resolves an explanation with
# decodeCmd(explainTool, version, flags), which reads FLAGS[version].clis[explainTool]
# — so with the wrong binary declared, these flags could never resolve even
# once CR-T-09/10 populated the RHEL 8/10 dictionaries, and the failure would
# look identical to an ordinary coverage gap (Q20) rather than a mis-filed entry.
#
# Two checks, both fail-first (this gate was committed failing on the two
# entries above, then content/commands.json and template.html were fixed):
#
# (a) BINARY AGREEMENT. The first word of every rhel_versions[version].command
#     (after stripping one leading "sudo") must equal the binary that
#     tools.json records for the entry's explain_tool (falling back to tool
#     when no explain_tool is set — the common case). tool still names the
#     subject the sidebar rail groups the entry under; explain_tool exists
#     for exactly the case this gate polices, where that subject is not the
#     binary the command runs.
#
# (b) FLAG EXPLAINABILITY. Every flags[].flag either (1) resolves as a name in
#     that binary's flag dictionary on some version where the dictionary is
#     POPULATED (RHEL 7/9 ship empty flags_rhel*.json today — CR-T-09/10 §
#     "flags_rhel8/flags_rhel10 real" — so only 8 and 10 count as populated),
#     or (2) carries a curated flags[].explain, or (3) is honestly marked: it
#     is not option-shaped (does not start with "-", so no man-page OPTIONS
#     dictionary could ever contain it — "status"/"is-active" are systemctl
#     SUBCOMMANDS, not flags) and the flag record still carries a
#     license_class, which is this codebase's existing "not silently guessed,
#     needs a hand paraphrase" marker (ADR-001 §5.1 flag_explain_rule). A flag
#     that is option-shaped and unresolved with no explain and no reason on
#     record is the one shape this gate refuses outright — that is a silent
#     coverage gap Q20 was built to catch, wearing the wrong disguise.
# ---------------------------------------------------------------------------

def _q22_populated_dictionaries():
    """{version: parsed flags_rhelN.json} for every version whose dictionary
    is non-empty — RHEL 7/9 ship `{"clis": {}}` today (CR-T-09/10 landed real
    data for 8 and 10 only), and a dictionary with nothing in it can prove
    nothing about coverage, so it does not count as "populated"."""
    out = {}
    for v in VERSIONS:
        path = os.path.join(REPO, "content", "flags_rhel%s.json" % v)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            dic = json.load(fh)
        if dic.get("clis"):
            out[v] = dic
    return out


def _q22_flag_resolves(name, binary, dictionaries):
    for dic in dictionaries.values():
        cli = (dic.get("clis") or {}).get(binary)
        if not cli:
            continue
        for fl in cli.get("flags") or []:
            if name in (fl.get("names") or []):
                return True
    return False


def gate_q22(ctx):
    f, d = [], []
    data = ctx["data"]
    tools_by_id = {t.get("id"): t for t in data["tools"]["tools"]}
    dictionaries = _q22_populated_dictionaries()
    if not dictionaries:
        f.append("no populated flag dictionary (content/flags_rhel*.json with a non-empty clis) "
                 "exists — this gate cannot tell a real coverage gap from every dictionary being "
                 "empty, so it refuses to call anything resolved")
        return f, d
    entries_checked = 0
    flags_checked = 0
    for e in data["commands"]["entries"]:
        if "template" in e:
            continue                      # generator specs compose per release; no rhel_versions block
        entries_checked += 1
        eid = e.get("id")
        explain_tool = e.get("explain_tool") or e.get("tool")
        tool_rec = tools_by_id.get(explain_tool)
        if tool_rec is None:
            f.append("entry %s: explain_tool/tool '%s' is not in tools.json (Q13 also catches this)"
                     % (eid, explain_tool))
            continue
        binary = tool_rec.get("binary") or explain_tool
        for v in VERSIONS:
            slot = (e.get("rhel_versions") or {}).get(v) or {}
            cmd = slot.get("command")
            if not cmd:
                continue                  # unavailable on this release — nothing to check
            words = cmd.split()
            if words and words[0] == "sudo":
                words = words[1:]
            first = words[0] if words else ""
            if first != binary:
                f.append("entry %s RHEL %s: command '%s' invokes '%s', but its declared tool "
                         "resolves to binary '%s' (tool=%s%s) — the flag panel would look the "
                         "binary up in the wrong dictionary"
                         % (eid, v, cmd, first, binary, e.get("tool"),
                            "" if not e.get("explain_tool") else " explain_tool=%s" % e.get("explain_tool")))
        for fl in (e.get("flags") or []):
            flags_checked += 1
            name = fl.get("flag") or ""
            if _q22_flag_resolves(name, binary, dictionaries):
                continue
            if fl.get("explain"):
                continue
            if not name.startswith("-") and fl.get("license_class"):
                continue                  # honestly marked: not an option a dictionary could hold
            f.append("entry %s: flag '%s' resolves in no populated flag dictionary for binary "
                     "'%s', carries no curated explain, and has no honest reason on record "
                     "(license_class) — the no-guess law means this can never be told apart from "
                     "a silent coverage gap" % (eid, name, binary))
    if entries_checked == 0:
        f.append(empty_set_failure(
            "entries with a rhel_versions block to check tool/binary agreement over",
            "a gate with nothing to check proves nothing about the class it exists to catch"))
    elif not f:
        d.append("%d entries / %d flags checked against %d populated flag dictionar%s (RHEL %s): "
                 "every command's first word matches its declared binary, and every flag resolves, "
                 "is curated, or is honestly marked non-option"
                 % (entries_checked, flags_checked, len(dictionaries),
                    "y" if len(dictionaries) == 1 else "ies", ", ".join(sorted(dictionaries))))
    return f, d


def gate_node_check(ctx):
    """BQP Gate 2 #1/#9 — JS syntax of the extracted app script. Node is optional."""
    f, d, p = [], [], []
    node = shutil.which("node")
    if not node:
        p.append("node is not installed on this runner — JS syntax check skipped "
                 "(CI does not require Node; this is informational)")
        return f, d, p
    tmp = tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8")
    try:
        tmp.write(ctx["app_script"])
        tmp.close()
        proc = subprocess.run([node, "--check", tmp.name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            f.append("node --check failed on the extracted app script:\n      "
                     + proc.stdout.decode("utf-8", "replace").strip().replace("\n", "\n      "))
        else:
            d.append("node --check clean on the extracted app script (%d bytes)" % len(ctx["app_script"]))
    finally:
        os.unlink(tmp.name)
    return f, d, p


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def build_ctx():
    artifact = find_artifact()
    dirty = dist_integrity_failures()
    if not artifact:
        version = load_build_constants().get("APP_VERSION")
        if version:
            print("FAIL: dist/md-code-red_%s.html does not exist -- run python3 build.py first"
                  % version)
        else:
            print("FAIL: could not read APP_VERSION out of build.py -- cannot name the "
                  "artifact to gate")
        for msg in dirty:
            print("FAIL: %s" % msg)
        sys.exit(1)
    if dirty:
        for msg in dirty:
            print("FAIL: %s" % msg)
        sys.exit(1)
    with open(artifact, encoding="utf-8") as fh:
        html = fh.read()
    m = re.search(r'<script id="mcr-data" type="application/json">(.*?)</script>', html, re.S)
    island = m.group(1) if m else ""
    data = None
    if island:
        try:
            # < / > are ordinary JSON escapes; json.loads restores them.
            # No pre-substitution here on purpose — a gate that repairs its input
            # cannot tell a well-escaped island from a badly escaped one.
            data = json.loads(island)
        except json.JSONDecodeError:
            data = None
    app = re.findall(r"<script>(.*?)</script>", html, re.S)
    ctx = {
        "artifact": artifact,
        "html": html,
        "island": island,
        "island_len": len(island),
        "shell": html.replace(island, "") if island else html,
        "app_script": app[-1] if app else "",
        "data": data,
        "build_consts": load_build_constants(),
    }
    return ctx


def load_sources(ctx):
    pin_f, pin_d = verify_pins()
    ctx["pin_failures"], ctx["pin_details"] = pin_f, pin_d
    ctx["source_rules"] = {}
    if not pin_f:
        for v in VERSIONS:
            ctx["source_rules"][v] = parse_source(v)
    else:
        for v in VERSIONS:
            ctx["source_rules"][v] = ({}, 0)


GATES = [
    ("Q1", "Build integrity and structure (DOCTYPE, two <script>, island parses, versions match, sha256 sidecar)", gate_q1),
    ("Q2", "Air-gap law (no external assets, no network JS, no CDN literals)", gate_q2),
    ("Q3", "Provenance law (every entry and dataset cites a source)", gate_q3),
    ("Q4", "The promise (verify / undo / blast on every entry)", gate_q4),
    ("Q5", "Humility and feature markers", gate_q5),
    ("Q6", "Leak scan (TODO / lorem / example.com / CHANGEME)", gate_q6),
    ("Q7", "localStorage guard (try/catch, schema-versioned)", gate_q7),
    ("Q8", "Embedded record counts match content", gate_q8),
    ("Q9", "CAT completeness (CAT I check+fix, STIG ID, CCI, NIST)", gate_q9),
    ("Q10", "STIG accuracy re-check against the pinned XCCDF", gate_q10),
    ("Q11", "CCI to 800-53 sampled re-check against the DISA CCI list", gate_q11),
    ("Q12", "Four-version completeness", gate_q12),
    ("Q13", "Referential integrity (stig_id, rule_id, tool, category, source_ref)", gate_q13),
    ("Q14", "No verbatim text from a paraphrase-only source", gate_q14),
    ("Q15", "Generated-file integrity (re-run the extractor and diff)", gate_q15),
    ("Q16", "Capture backing (expected_output and verified receipts)", gate_q16),
    ("Q17", "Render safety (no inline handlers, innerHTML audit, esc/escapeAttr present)", gate_q17),
    ("Q18", "Command-assembly safety (hostile-input harness, quoting-domain separation)", gate_q18),
    ("Q19", "Escaper behaviour (esc/escapeAttr/escapeRegex actually escape, run under node)", gate_q19),
    ("Q20", "Flag-dictionary coverage against the raw captures, and citations that show the flag", gate_q20),
    ("Q21", "No raw control, bidi or zero-width character in any tracked source file", gate_q21),
    ("Q22", "Declared tool is the invoked binary, and every flag resolves, is curated, or is honestly marked (G1)", gate_q22),
    ("JS", "JS syntax of the extracted app script (BQP Gate 2 #1/#9, Node optional)", gate_node_check),
]


def size_report(ctx):
    size = os.path.getsize(ctx["artifact"])
    print("")
    print("SIZE REPORT (informational — the Founder ruled the ceiling UNLIMITED on 2026-09-17;")
    print("             this gate reports and can never fail a build)")
    print("  %s" % os.path.relpath(ctx["artifact"], REPO))
    print("  artifact:    %.3f MB (%d bytes)" % (size / 1024.0 / 1024.0, size))
    print("  data island: %.3f MB (%d bytes)" % (ctx["island_len"] / 1024.0 / 1024.0, ctx["island_len"]))
    print("  shell:       %.3f MB (%d bytes)" % ((size - ctx["island_len"]) / 1024.0 / 1024.0,
                                                 size - ctx["island_len"]))


def main():
    args = sys.argv[1:]
    ctx = build_ctx()

    if "--size" in args:
        size_report(ctx)
        sys.exit(0)

    only = None
    if "--accuracy" in args:
        only = ("Q10", "Q11")

    if ctx["data"] is None and only is None:
        pass  # Q1 reports it; later gates are skipped below
    load_sources(ctx)

    print("=" * 78)
    print(" QA GATE — MD CODE RED %s" % (ctx["build_consts"].get("APP_VERSION") or "?"))
    print("=" * 78)

    n_fail = 0
    for gid, name, fn in GATES:
        if only and gid not in only:
            continue
        if ctx["data"] is None and gid not in ("Q1", "Q2", "Q6", "Q17", "Q18", "Q19", "Q20", "Q21", "JS"):
            print("%-4s SKIP  %s" % (gid, name))
            print("       data island did not parse — see Q1")
            continue
        out = fn(ctx)
        if len(out) == 3:
            failures, details, pendings = out
        else:
            failures, details = out
            pendings = []
        status = "FAIL" if failures else "PASS"
        if failures:
            n_fail += 1
        print("%-4s %s  %s" % (gid, status, name))
        for line in details:
            print("       ok: %s" % line)
        for line in pendings:
            print("       PENDING: %s" % line)
        for line in failures:
            print("       FAIL: %s" % line)

    size_report(ctx)

    print("")
    print("-" * 78)
    if n_fail:
        print(" QA GATE: %d gate(s) FAILED" % n_fail)
        print("-" * 78)
        sys.exit(1)
    print(" QA GATE: PASS")
    print("-" * 78)
    sys.exit(0)


if __name__ == "__main__":
    main()
