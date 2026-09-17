#!/usr/bin/env python3
"""qa.py — the MD CODE RED QA gate. Exits non-zero on any FAIL.

Stdlib only.

    python3 qa.py              # every gate, Q1..Q18, one PASS/FAIL line each
    python3 qa.py --accuracy   # Q10 + Q11 only (the STIG/CCI accuracy re-check)
    python3 qa.py --size       # the size report only — informational, never fails

Gate numbering follows ADR-001 §7.3 (Q1..Q17). Q1..Q7 come from grey-beard-ansible
qa.py, Q8..Q11 from the Etsy RHEL STIG pipeline's qa-rhel-stig.py (this file keeps
its own independent XCCDF parse on purpose: the accuracy gate is worth nothing if
it re-uses the extractor's code path), Q12..Q17 are new for MD CODE RED.

Q18 is beyond ADR-001's list: it is Marcus's CI merge-gate #4 and #9
(threat-model-v1 §11), the hostile-input harness over the command assembler and
the quoting-domain separation check. It is the only gate in this file that
REQUIRES Node — see gate_q18 for why a skip is not acceptable there.

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
    "extract/make_pending_skeletons.py",  # flags_rhel{7,8,9,10}.json, expected_output.json
)

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
    ("STIG panel", "function renderStigPanel(", "CR-T-26"),
    ("evidence exporter", "function exportEvidence(", "CR-T-28"),
    ("lazy typed search index", "function buildIndex(", "CR-T-29"),
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
    if not os.path.isdir(DIST):
        return None
    cands = sorted(f for f in os.listdir(DIST) if f.startswith("md-code-red_") and f.endswith(".html"))
    return os.path.join(DIST, cands[-1]) if cands else None


def load_build_constants():
    """Read APP_NAME/APP_VERSION out of build.py without importing it."""
    src = open(os.path.join(REPO, "build.py"), encoding="utf-8").read()
    out = {}
    for key in ("APP_NAME", "APP_VERSION", "CLASSIFICATION"):
        m = re.search(r'^%s\s*=\s*"([^"]+)"' % key, src, re.M)
        out[key] = m.group(1) if m else None
    return out


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
# independent source parses (never re-uses extract/)
# ---------------------------------------------------------------------------

def verify_pins():
    """Q10/Q11 precondition: the pinned XML must hash to stig-src/SHA256SUMS."""
    failures, details = [], []
    sums = {}
    path = os.path.join(STIG_SRC, "SHA256SUMS")
    if not os.path.exists(path):
        return ["stig-src/SHA256SUMS is missing — refusing to parse unpinned sources"], details
    for line in open(path, encoding="utf-8"):
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
        want = open(side, encoding="utf-8").read().split()[0]
        got = sha256_file(ctx["artifact"])
        if want != got:
            f.append("sha256 sidecar %s does not match the artifact %s" % (want[:16], got[:16]))
        else:
            d.append("sha256 sidecar matches: %s" % got[:32])
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
    return f, d


def gate_q3(ctx):
    f, d = [], []
    data = ctx["data"]
    need = ("title", "url_or_man", "retrieved_on", "license_class")

    def check(where, src):
        if not isinstance(src, dict):
            f.append("%s: no source object" % where)
            return
        for field in need:
            if not src.get(field):
                f.append("%s: source.%s missing" % (where, field))
        if src.get("license_class") not in ("verbatim-ok", "paraphrase-only"):
            f.append("%s: license_class '%s' is not verbatim-ok or paraphrase-only"
                     % (where, src.get("license_class")))

    for e in data["commands"]["entries"]:
        check("command entry %s" % e.get("id"), e.get("source"))
    for t in data["tools"]["tools"]:
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
                 "destructive-pattern table carry title/url_or_man/retrieved_on/license_class")
    return f, d


def gate_q4(ctx):
    f, d = [], []
    entries = ctx["data"]["commands"]["entries"]
    for e in entries:
        if not e.get("verify") or not e.get("undo") or e.get("blast") not in ("green", "yellow", "red"):
            f.append("entry %s: verify/undo/blast promise broken" % e.get("id"))
    if not f:
        d.append("all %d command entries keep verify/undo/blast" % len(entries))
    return f, d


def gate_q5(ctx):
    f, d, p = [], [], []
    html = ctx["html"]
    for name, marker, phase in MARKERS:
        if marker in html:
            continue
        if phase:
            p.append("%s — not in this build yet (%s)" % (name, phase))
        else:
            f.append("feature marker missing: %s (%s)" % (name, marker))
    d.append("%d/%d markers present, %d pending"
             % (len(MARKERS) - len(f) - len(p), len(MARKERS), len(p)))
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


def strip_js_comments(src):
    """Blank out // and /* */ comments, preserving offsets and line numbers.

    Conservative by design: it tracks string state so a comment marker inside a
    string literal is left alone. Regex literals in this codebase never open with
    '//' or '/*', so they are not mistaken for comments.
    """
    out = list(src)
    i, n, quote = 0, len(src), None
    while i < n:
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'`":
            quote = c
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c == "/":
            # A regex literal, if a regex can legally start here. Skipping it whole
            # keeps a quote character inside a character class (/[&<>"']/g) from
            # throwing the string tracker out of phase for the rest of the file.
            prev = ""
            k = i - 1
            while k >= 0 and src[k] in " \t\r\n":
                k -= 1
            if k >= 0:
                prev = src[k]
            if prev == "" or prev in "(,=:[!&|?{};+-*%~^":
                j, in_class = i + 1, False
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
                        break
                    elif ch == "\n":
                        break
                    j += 1
                i = j + 1
                continue
        i += 1
    return "".join(out)


def try_block_spans(src):
    """Brace-matched [start, end) spans of every try{...} block in the script."""
    spans = []
    for m in re.finditer(r"\btry\s*\{", src):
        depth, i = 0, m.end() - 1
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), i + 1))
                    break
            i += 1
    return spans


def gate_q7(ctx):
    f, d = [], []
    script = strip_js_comments(ctx["app_script"])
    spans = try_block_spans(script)
    hits = list(re.finditer(r"\b(?:localStorage|sessionStorage)\b", script))
    if not hits:
        f.append("no storage access found at all — the storage guard should exist")
    for m in hits:
        if not any(s <= m.start() < e for s, e in spans):
            line = script[:m.start()].count("\n") + 1
            f.append("storage identifier '%s' at app-script line %d is not inside a try{...}catch block"
                     % (m.group(0), line))
    if not f:
        d.append("all %d localStorage/sessionStorage references sit inside one of %d try/catch blocks"
                 % (len(hits), len(spans)))
    if "var SCHEMA=1;" not in script:
        f.append("storage records are not schema-versioned")
    else:
        d.append("storage records are schema-versioned and namespaced (mdcr.v1.)")
    return f, d


def gate_q8(ctx):
    f, d = [], []
    data = ctx["data"]
    for v in VERSIONS:
        ds = data["rules"][v]
        meta = ds.get("_meta") or {}
        embedded = ds.get("rules", [])
        src, total = ctx["source_rules"][v]
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
    if len(entries) != (data["commands"].get("_meta") or {}).get("entry_count"):
        f.append("commands.json _meta.entry_count != %d embedded entries" % len(entries))
    else:
        d.append("commands: %d entries, count matches _meta" % len(entries))
    for v in VERSIONS:
        fl = data["flags"][v]
        d.append("flags_rhel%s: %d CLI dictionaries (%s)"
                 % (v, len(fl.get("clis", {})), (fl.get("_meta") or {}).get("status", "")[:48]))
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
        source_ids = set(json.load(open(sources_json, encoding="utf-8")).get("sources", {}).keys())
    n_stig = 0
    for e in data["commands"]["entries"]:
        if e.get("tool") not in tool_ids:
            f.append("entry %s: tool '%s' is not in tools.json" % (e.get("id"), e.get("tool")))
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


def gate_q14(ctx):
    f, d = [], []
    raw_dir = os.path.join(REPO, "content-src", "raw")
    staged = []
    for sub in ("man", "help", "redhat", "git"):
        p = os.path.join(REPO, "content-src", sub)
        if os.path.isdir(p):
            staged.append(sub)
    if not os.path.isdir(raw_dir) and not staged:
        d.append("no raw sources present under content-src/ — nothing to collide with; "
                 "the 8-gram collision check activates when CR-T-09/CR-T-10 stage man and guide text")
        return f, d
    # 8-gram collision check against every staged raw source (ADR-001 §7.3 Q14)
    corpus = []
    for sub in staged + (["raw"] if os.path.isdir(raw_dir) else []):
        base = os.path.join(REPO, "content-src", sub)
        for root, _dirs, files in os.walk(base):
            for name in files:
                if name.endswith((".txt", ".md")):
                    corpus.append(os.path.join(root, name))

    def shingles(text):
        toks = re.sub(r"[^a-z0-9\s-]", " ", text.lower()).split()
        return set(tuple(toks[i:i + 8]) for i in range(max(0, len(toks) - 7)))

    raw_grams = set()
    for path in corpus:
        raw_grams |= shingles(open(path, encoding="utf-8", errors="replace").read())
    hits = 0
    for e in ctx["data"]["commands"]["entries"]:
        if (e.get("source") or {}).get("license_class") != "paraphrase-only":
            continue
        texts = []
        for v in VERSIONS:
            val = (e.get("rhel_versions") or {}).get(v) or {}
            if val.get("notes"):
                texts.append(val["notes"])
            if (val.get("changed_in_note") or {}).get("what"):
                texts.append(val["changed_in_note"]["what"])
        for fl in (e.get("flags") or []):
            if fl.get("explain"):
                texts.append(fl["explain"])
        for t in texts:
            shared = shingles(t) & raw_grams
            if shared:
                hits += 1
                f.append("entry %s: 8-gram lifted from a paraphrase-only source: \"%s\""
                         % (e.get("id"), " ".join(list(shared)[0])))
    if not f:
        d.append("%d raw source file(s) shingled; no curated paraphrase shares an 8-gram with them" % len(corpus))
    return f, d


def gate_q15(ctx):
    """Re-run every extractor over the committed sources and diff (ADR-001 §6.3).

    One entry per generated content family. A family with no extractor listed here
    is a family nobody can prove was generated rather than typed, so the list is
    checked against the generators the datasets themselves declare, below.

    FLAGS special case (CR-T-09/10). extract/make_pending_skeletons.py still emits
    the placeholder EMPTY flags_rhel<N>.json for every version — that was fine
    while CR-T-09/10 hadn't run, but flags_rhel8.json and flags_rhel10.json are now
    real data from extract/extract_flags.py (Defiant/Saratoga), so a diff against
    the placeholder script's empty output would always "drift". Re-running the
    live extractor here would mean this gate re-opens an SSH session to both hosts
    on every CI run — slow, and a hard dependency on lab hosts being reachable from
    the runner. Instead: (a) the two flags_rhel8/10.json lines are filtered out of
    make_pending_skeletons.py's drift report below — that script is still the
    right authority for flags_rhel7/9, which remain genuinely empty pending
    CR-T-11/12 — and (b) extract_flags.py's own --check mode re-parses the raw
    man/--help dumps already committed under content-src/raw/ (no SSH, no live
    host) and diffs that against content/flags_rhel{8,10}.json instead.
    """
    f, d = [], []
    flags_reextracted = {"flags_rhel8.json", "flags_rhel10.json"}
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
        f.append("extract/extract_flags.py missing — flags_rhel8/10.json cannot be re-derived")
    else:
        for v in ("8", "10"):
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
    data = ctx["data"]
    declared = set()
    for v in VERSIONS:
        declared.add(((data["rules"][v].get("_meta") or {}).get("generator")))
    declared.add((data["cci_nist"].get("_meta") or {}).get("generator"))
    unrerun = sorted(g for g in declared if g and g not in GENERATORS)
    if unrerun:
        f.append("generated dataset(s) declare a generator this gate does not re-run: %s"
                 % ", ".join(unrerun))
    else:
        d.append("every RULES and CCI dataset declares a generator that this gate re-ran: %s"
                 % ", ".join(sorted(declared - {None})))
    return f, d


def gate_q16(ctx):
    f, d = [], []
    data = ctx["data"]
    captures = (data["expected_output"].get("captures") or {})
    n_exp = 0
    for e in data["commands"]["entries"]:
        for s in (e.get("stig") or []):
            if s.get("expected_output"):
                n_exp += 1
                key = "%s|%s|%s" % (e["id"], s.get("stig_id"), s.get("rhel_version"))
                cap = captures.get(key)
                if not cap:
                    f.append("entry %s stig %s: expected_output with no capture record %s"
                             % (e["id"], s.get("stig_id"), key))
                    continue
                for field in ("host", "os_release", "kernel", "patch_level", "command_run",
                              "exit_code", "stdout", "captured_on", "captured_by"):
                    if field not in cap:
                        f.append("capture %s: missing required field %s" % (key, field))
        ver = e.get("verified")
        if ver not in (False, None):
            for field in ("by", "on", "host"):
                if not (ver or {}).get(field):
                    f.append("entry %s: verified is set but has no '%s'" % (e["id"], field))
    if not f:
        d.append("%d expected_output blocks, %d capture records — expected output is captured, never typed "
                 "(content validation protocol runs are CR-T-34)" % (n_exp, len(captures)))
        d.append("no entry claims verified without a {by,on,host} receipt")
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
        for k, why in sorted(INNERHTML_ALLOWLIST.items()):
            d.append("allow-list: %s — %s" % (k, why))
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
    for line in rep.get("failures", []):
        f.append("hostile input: %s" % line)
    if proc.returncode != 0 and not rep.get("failures"):
        f.append("the harness exited %d without naming a failure: %s" % (proc.returncode, err[:300]))
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
    if not artifact:
        print("FAIL: no dist/md-code-red_*.html — run python3 build.py first")
        sys.exit(1)
    html = open(artifact, encoding="utf-8").read()
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
        if ctx["data"] is None and gid not in ("Q1", "Q2", "Q6", "Q17", "Q18", "JS"):
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
