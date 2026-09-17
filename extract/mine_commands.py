#!/usr/bin/env python3
"""mine_commands.py -- mine every command line the sources already carry.

Stdlib only. Deterministic: a pure function of files committed in this repo, so a
re-run is byte-identical and qa.py Q15 can diff it.

    python3 extract/mine_commands.py            # regenerate the generated files
    python3 extract/mine_commands.py --check    # regenerate into a temp dir and diff (Q15)
    python3 extract/mine_commands.py --report   # print the tally only, write nothing
    python3 extract/mine_commands.py --stage-guides <corpus-root>
                                                # re-stage content-src/raw/redhat/ from the
                                                # corpus. NEEDS THE CORPUS. Not part of --check.

WHAT IT PRODUCES

  content/reference_commands.json           the embedded family (tier: reference)
  content-src/residue/<family>_rhel<N>.jsonl every source line this parser DECLINED,
                                            with a closed reason code
  content-src/residue/_baseline.json        the ratchet the coverage gate reads

WHY THIS EXISTS

The Founder's requirement is "every possible command that can be generated
included in this tool". The artifact already carried 1,492 DISA STIG rules whose
check (`chk`) and fix (`fix`) text is full of literal, DISA-published command
lines, and showed them only as prose inside a rule panel. This turns that text,
plus the staged man/--help captures and the Red Hat product documentation, into a
first-class searchable family.

WHAT A MINED RECORD IS NOT

Not a curated entry. No verify text, no undo text, no reviewed blast rating, no
capture, no receipt. extract/schema.py's reference_commands_errors() REFUSES those
keys outright, so an extractor cannot invent one (ADR-002) and the curated
catalog's 18 human receipts keep their meaning. The assembler never sees these
records: there is nothing to assemble, the text is fixed.

THE THREE SOURCE FAMILIES

  C1 stig_rules    content/rules_rhel{7,8,9,10}.json chk/fix text.
                   DISA, public domain, license_class verbatim-ok,
                   authority GOVERNING for the release whose STIG it is.
  C2 raw_captures  content-src/raw/rhel{7,8,10}/*.txt SYNOPSIS/EXAMPLES.
                   Man pages and --help output, license_class paraphrase-only,
                   authority DOCUMENTARY. The COMMAND LINE ONLY is recorded --
                   never the sentence around it (qa.py Q14 holds that line).
  C3 redhat_guides content-src/raw/redhat/rhel{7,8,9,10}.candidates.jsonl,
                   staged from the 276 Red Hat guide text files on the corpus.
                   license_class cc-by-sa-3.0, authority DOCUMENTARY.
                   Licensing ruling v1 Ruling 2 (Alex Okafor, 2026-09-18): EMBED
                   WITH CONDITIONS. Those conditions are implemented here:
                     1. command only, never the surrounding sentence;
                     2. DISA wins on overlap -- a command that also appears in
                        the STIG text is attributed to DISA, not Red Hat (see
                        reattribute_overlap() and _meta.disa_overlap);
                     3. our taxonomy, not theirs -- records are ordered by tool
                        and command text, and Red Hat's per-guide chapter
                        ordering and selection are deliberately NOT preserved;
                     4. per-command attribution (guide title, URL, copyright)
                        through _meta.guides, plus a full CC BY-SA notice in the
                        About panel. The ruling is explicit that attribution may
                        not discharge share-alike if counsel later disagrees --
                        nothing here is written as though it settles that;
                     5. no "--help verification" language of any kind. Condition 4
                        of the ruling requires SME verification before any
                        external release; these records say only `reference` and
                        `documentary` and never that anything was checked.

THE PROMPT TEST, AND WHY IT IS NOT A REGEX SWEEP

A candidate must carry a SHELL PROMPT: "$ " (user) or "# " (root). That single
rule removes every expected-output line, every audit.rules content line
(`-a always,exit -F ...` is FILE CONTENT, not an invocation), every `ExecStart=`
unit directive and every `$ModLoad` rsyslog statement (no space after the sigil,
so not a prompt), and every shebang and `##` banner.

A `#` line then needs a second test, because a root prompt and a comment marker
are the same character -- and the right second test is NOT the same in both
families, which is a measurement, not a preference:

  C1: the head must resolve in the derived VOCABULARY (every head of every
      `$`-prompted line in all four benchmarks, plus this product's tool ids,
      plus the staged man pages, plus COMMON_BINARIES). The STIG's `#` lines are
      only 418 of ~15,600 and a large share of them are file-content excerpts
      (`includedir /etc/sudoers.d`, `FirewallBackend`), which a vocabulary
      catches and a shape test does not.
  C3: the head must be a LOWERCASE program name and the line must not read as
      prose. Measured on the guides, the vocabulary test rejects 13,218 real
      commands (pcs, stratis, nft, nvme, zipl, kpatch, vgs, testparm ...)
      because the guides use `#` as the ordinary root prompt and the vocabulary
      cannot keep up with 316 binaries. The lowercase-plus-prose test rejects
      3,711 lines instead, essentially all of them prose or table cells.

RESIDUE IS THE METRIC

Every declined line is recorded in content-src/residue/ with one of
RESIDUE_REASONS, and its text is written with every trojan character escaped
(threat model v2, M1: Q21 refuses raw control/bidi/zero-width characters in every
tracked file and TROJAN_SCAN_EXCLUDE stays empty, so residue escapes on the way
in rather than being excluded on the way out). qa.py's coverage gate fails when
total residue GROWS against _baseline.json or when `unparseable` exceeds its cap.

ADR-001 6.3: generated files are never hand-edited. Fix the extractor, re-run.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, OrderedDict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "extract"))
import schema  # noqa: E402

CONTENT = os.path.join(REPO, "content")
RAW = os.path.join(REPO, "content-src", "raw")
GUIDES_RAW = os.path.join(RAW, "redhat")
RESIDUE = os.path.join(REPO, "content-src", "residue")
OUT_NAME = "reference_commands.json"

VERSIONS = schema.VERSIONS
GENERATOR = "extract/mine_commands.py"
EXTRACTOR_VERSION = "2.0.0"
# Pinned like extract/parse_xccdf.py's: the date of the PINNED SOURCE SET, not the
# day the script ran. Mining is a pure function of the committed sources, so a
# re-run on any day is byte-identical (qa.py Q15 depends on that).
EXTRACTED_ON = "2026-09-17"
GUIDE_DOCSET = "docs-2026-09-17"

# --------------------------------------------------------------------------
# the command test
# --------------------------------------------------------------------------

# A program name, or an absolute path to one. Strict: no '=', no ':', no space --
# which is what throws out `ExecStart=-/usr/lib/...`, `SELINUX=` and `NOTE:`.
CMD_TOKEN_RE = re.compile(r"^(/[A-Za-z0-9_.+-]+)*/?[A-Za-z0-9_][A-Za-z0-9_.+-]*$")
# The BASENAME of a real RHEL binary is lowercase. An English sentence starts
# with a capital. Directory components may be any case (/usr/X11R6/bin/...).
LOWER_BASENAME_RE = re.compile(r"^[a-z0-9_][a-z0-9_.+-]*$")
# A shell prompt: the sigil, then REQUIRED whitespace, then something.
PROMPT_RE = re.compile(r"^([$#])[ \t]+(\S.*)$")
# The RHEL 7 STIG occasionally writes a root prompt with no space
# ("#find /dev -context ..."). Accepted only when what follows passes the same
# command test -- `#includedir /etc/sudoers.d` does not, and stays out.
TIGHT_PROMPT_RE = re.compile(r"^#([A-Za-z0-9_/][^\s]*)(\s.*)?$")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'-]*$")
# A configuration-file directive. The SPACE before the separator is the whole
# discriminator: `sanlock_lv_extend = 256` is lvm.conf, `DS_INSTANCE=$(...)` is a
# shell assignment and a real command. A trailing `key =` with no value is a
# directive too, which is why the value is optional here.
CONFIG_LINE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*[ \t]+[:=]([ \t]|$)"
                            r"|^[A-Za-z_][A-Za-z0-9_.-]*:[ \t]")
AUDIT_RULE_RE = re.compile(r"^-[aAwWFkSD]\b")

# Prose detection. Not a language model: a line with four or more tokens, none of
# which is an option, a path, an assignment, a pipe, a variable or a quoted
# string, and which uses two or more English function words, is a sentence.
PROSE_STOPWORDS = frozenset((
    "the a an to of is are was were and or in for that this with if not be been "
    "being will can could should must you your it its on from as by at has have "
    "had when which there their any all does do no yes than then these those we "
    "our us he she they them such use using used into over under about after "
    "before between each other more most some only also but so because while "
    "where what who how does".split()))
# An instruction to drive an interactive program, which is a procedure, not an
# invocation. Checked before prose so the tally separates the two.
TUI_OPENERS = frozenset((
    "select", "choose", "press", "click", "navigate", "highlight", "scroll",
    "type", "enter", "tab", "arrow", "confirm", "accept", "expand", "collapse"))
TUI_WORDS = frozenset((
    "menu", "screen", "dialog", "wizard", "field", "button", "tab", "prompt",
    "window", "installer", "anaconda", "nmtui", "cursor", "checkbox", "key",
    "keys", "arrow", "option", "list"))

# Hand-maintained. Binaries shipped in RHEL 7-10 that the STIG shows ONLY behind a
# root prompt, so the derived vocabulary (built from `$`-prompted lines) never
# sees them. Used only to let a line that ALREADY passed the prompt test through;
# never to add a line that failed it.
COMMON_BINARIES = (
    "apropos", "aureport", "authconfig", "basename", "bash", "cat", "chattr",
    "chcon", "chgrp", "chmod", "chown", "chpasswd", "cp", "crontab", "cut",
    "date", "dd", "df", "diff", "dirname", "dmesg", "dnf", "dracut", "du",
    "echo", "egrep", "env", "fgrep", "file", "find", "free", "getfacl",
    "getcap", "grep", "groupadd", "groupdel", "groupmod", "gzip", "head",
    "hostname", "id", "kill", "killall", "ln", "locate", "ls", "lsattr",
    "lscpu", "lsmod", "lsof", "man", "mkdir", "mktemp", "modprobe", "more",
    "mount", "mv", "netstat", "nice", "nohup", "passwd", "ping", "ps", "pwd",
    "readlink", "realpath", "rm", "rmdir", "rpm", "rsync", "scp", "sed",
    "setfacl", "sh", "sort", "ss", "ssh", "stat", "strings", "su", "sync",
    "tail", "tar", "tee", "test", "top", "touch", "tr", "tune2fs", "udevadm",
    "umask", "umount", "uname", "uniq", "unzip", "uptime", "vim", "w", "wc",
    "wget", "which", "who", "whoami", "xargs", "zcat",
)

# The closed set. ADR-002: every declined line carries exactly one of these.
RESIDUE_REASONS = (
    "prose",                 # an English sentence, a heading, or a table cell
    "interactive-tui",       # "Select X from the menu" -- a procedure, not an invocation
    "output-fragment",       # console output, a status line, a column of numbers
    "config-fragment",       # file content: a directive, an audit rule, key=value
    "unparseable",           # command-shaped but this parser refuses to read it
    "binary-not-on-release", # a real command whose binary this product records as absent
)
# M4: a line headed by a shell-wrapper whose command is a quoted string argument
# is REFUSED, not parsed. Counted separately so the signal is not lost inside
# "unparseable".
REFUSED_WRAPPER_REASON = "unparseable"


def escape(text):
    """schema.escape_trojan(), by its short name here. M1/M8: one table."""
    return schema.escape_trojan(text)


def first_token(text):
    toks = schema.split_tokens(text)
    return toks[0] if toks else ""


def stage_one_head(text):
    """The binary the FIRST top-level stage invokes (ADR-002 ruling 1)."""
    stages = schema.split_stages(text)
    if not stages:
        return None
    return schema.head_binary(stages[0])


def prose_like(text):
    toks = schema.split_tokens(text)
    if len(toks) < 4:
        return False
    for t in toks[1:]:
        if (t.startswith("-") or t.startswith("/") or t.startswith("~")
                or "=" in t or "|" in t or "$" in t or t.startswith("\"")
                or t.startswith("'") or t.startswith("<")):
            return False
    words = [t for t in toks if WORD_RE.match(t)]
    return sum(1 for w in words if w.lower() in PROSE_STOPWORDS) >= 2


def tui_like(text):
    toks = [t.lower().strip(".,:;") for t in schema.split_tokens(text)]
    if not toks or toks[0] not in TUI_OPENERS:
        return False
    return any(t in TUI_WORDS for t in toks[1:])


# An option token or an absolute path argument. A line carrying one is a line
# whose head is being INVOKED, not merely named -- see collect_strong_heads().
EVIDENCE_TOKEN_RE = re.compile(r"^(-{1,2}[A-Za-z0-9]|/[A-Za-z0-9_.]|~/)")


def collect_strong_heads(candidates):
    """The set of heads this corpus shows being INVOKED, derived in a first pass.

    TM2-F1 is the finding this answers: a false positive counts as `classified`
    AND `recorded`, so the residue ledger balances while `ticket constraints` or
    `delay to improve performance.` sits in the product under a citation. No
    language test catches those reliably -- two lowercase words with no stopword
    is not distinguishable from `virsh list` by grammar.

    What IS distinguishable is evidence. A head is accepted as a binary when the
    corpus shows it, somewhere, at a `$` prompt (which has no second meaning) or
    carrying an option token or an absolute path argument. `virsh`, `lstopo` and
    `targetcli` earn that; `ticket`, `keep`, `behavior` and `optional` never do.
    Derived from the same corpus being mined, in one pass, so it costs nothing
    and cannot go stale.
    """
    strong = set()
    for c in candidates:
        text = c["text"]
        if schema.TROJAN_RE.search(text):
            continue
        stages = schema.split_stages(text)
        if not stages:
            continue
        head_tok = schema.command_head(stages[0])
        if not head_tok or not CMD_TOKEN_RE.match(head_tok):
            continue
        head = head_tok.rsplit("/", 1)[-1]
        if head in schema.REFUSED_HEADS:
            continue
        # Evidence is only evidence if the LINE is command-shaped. Without this,
        # a wrapped prose line ("has failed. It is left to the user to run
        # lvconvert --repair") carries an option token and would make `has` a
        # binary -- which is how three sentences got into the first measurement.
        if not LOWER_BASENAME_RE.match(head) or head.endswith(".") or head.endswith("-"):
            continue
        if prose_like(text) or tui_like(text):
            continue
        toks = schema.split_tokens(text)
        if c["prompt"] == "$" or any(EVIDENCE_TOKEN_RE.match(t) for t in toks[1:]):
            strong.add(head)
    return strong


def looks_truncated(text):
    """True when the text is visibly an INCOMPLETE line.

    Vendor documentation is extracted from PDF, and a long command wraps. Some
    of those wraps are joined by a trailing backslash (the staging joins them);
    the rest are cut mid-token or mid-quote and there is no honest way to
    reconstruct them. Rather than drop those -- the fragment is still the real
    beginning of a real command, and it is what the source shows -- the record
    is FLAGGED, and the product says so where it renders it. The classifier
    accuracy review (tests/fixtures/mined-sample-review.json, threat model v2
    M5) is what holds this to being true: every record a human marked incomplete
    must carry this flag.
    """
    t = str(text).rstrip()
    if not t:
        return False
    if t.count("\"") % 2 or t.count("'") % 2:
        return True
    if t.endswith("-") or t.endswith("=") or t.endswith(","):
        return True
    last = schema.split_tokens(t)[-1] if schema.split_tokens(t) else ""
    if re.match(r"^--[A-Za-z0-9][A-Za-z0-9-]*$", last) and "=" not in last:
        # a long option left dangling with no value -- `... --template`
        return last not in NO_VALUE_LONG_OPTIONS
    return False


# Long options that legitimately end a line because they take no value. Small and
# hand-maintained; a miss here only costs a truncation flag on a complete line,
# which is the safe direction.
NO_VALUE_LONG_OPTIONS = frozenset((
    "--all", "--help", "--version", "--list", "--quiet", "--verbose", "--force",
    "--now", "--permanent", "--reload", "--live", "--system", "--user", "--json",
    "--yes", "--no-gpg-verify", "--dry-run", "--check", "--debug", "--full",
    "--recursive", "--long", "--raw", "--no-pager", "--global", "--local",
    "--enable", "--disable", "--status", "--start", "--stop", "--restart",
    "--syntax-check", "--verify", "--update", "--query", "--install", "--remove",
))


def no_evidence_reason(text):
    """The residue code for a line whose head this corpus never shows invoked.

    Not "unparseable": the line parsed fine, it just names something that is not
    a program. Almost all of these are wrapped sentences or table cells, so the
    reason follows the shape of the text rather than defaulting to the code
    reserved for lines this parser genuinely could not read.
    """
    toks = schema.split_tokens(text)
    words = [t for t in toks if WORD_RE.match(t.strip(".,:;"))]
    if toks and len(words) >= max(2, len(toks) - 1):
        return "prose"
    return residue_reason_for(text)


def residue_reason_for(text):
    """The closed reason code for a line this parser declined."""
    if tui_like(text):
        return "interactive-tui"
    stripped = text.strip()
    if AUDIT_RULE_RE.match(stripped) or CONFIG_LINE_RE.match(stripped):
        return "config-fragment"
    if prose_like(text):
        return "prose"
    head = first_token(stripped)
    if head and CMD_TOKEN_RE.match(head) and LOWER_BASENAME_RE.match(head.rsplit("/", 1)[-1]):
        # command-shaped, but something else refused it
        return "unparseable"
    if not stripped or not WORD_RE.match(head.strip(".,:;") or "x"):
        return "output-fragment"
    return "prose"


def classify(text, prompt, policy, vocab, unavailable, strong=()):
    """(tool, None) when this line is a command, (None, reason) when it is not.

    `policy` is "vocabulary" (C1) or "lowercase" (C2/C3) -- see the module
    docstring for why the two families need different second tests for a `#`
    prompt, and what each was measured to reject.
    """
    if schema.TROJAN_RE.search(text):
        return None, "unparseable"
    stages = schema.split_stages(text)
    if not stages:
        return None, "output-fragment"
    head_tok = schema.command_head(stages[0])
    if head_tok is None:
        if ENV_ASSIGN_RE.match(first_token(text)):
            return "shell", None            # `machine_id=$(cat /etc/machine-id)`
        return None, "output-fragment"
    head = head_tok.rsplit("/", 1)[-1]
    if head in schema.REFUSED_HEADS:
        # M4: su -c / sh -c / env VAR=value go to residue, not parsing.
        return None, REFUSED_WRAPPER_REASON
    if not CMD_TOKEN_RE.match(head_tok):
        return None, residue_reason_for(text)
    if CONFIG_LINE_RE.match(text.strip()):
        return None, "config-fragment"
    if head not in vocab and head not in strong and not _in_bin_dir(head_tok):
        # Nowhere in this corpus is this head shown being invoked. See
        # collect_strong_heads() -- this is the TM2-F1 rule, and it applies to
        # every family and both prompts.
        return None, no_evidence_reason(text)
    if prompt == "$":
        if prose_like(text):
            return None, "prose"
    else:
        if policy == "vocabulary":
            if head not in vocab and not _in_bin_dir(head_tok):
                return None, residue_reason_for(text)
        else:
            if not LOWER_BASENAME_RE.match(head):
                return None, residue_reason_for(text)
            if prose_like(text) or tui_like(text):
                return None, residue_reason_for(text)
    if head in unavailable:
        return None, "binary-not-on-release"
    return head, None


BIN_DIRS = ("/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/", "/usr/local/bin/",
            "/usr/local/sbin/", "/usr/libexec/", "/usr/X11R6/bin/", "/opt/")


def _in_bin_dir(tok):
    """An absolute path into a standard binary directory is a command by its own
    evidence, whatever a word list thinks of the basename."""
    return any(tok.startswith(d) for d in BIN_DIRS)


# --------------------------------------------------------------------------
# occurrence and residue records
# --------------------------------------------------------------------------

def occurrence(version, **anchor):
    o = {"v": version}
    o.update(anchor)
    return o


def anchor_of(occ):
    """The re-resolvable anchor string for one occurrence (threat model v2, M2).

    file@#anchor form, resolved by qa.py's Q25 against the committed source. The
    string is DERIVED, never stored, so it cannot disagree with the fields.
    """
    if occ.get("s"):
        return "content/rules_rhel%s.json#%s/%s@%s" % (occ["v"], occ["s"], occ.get("f"), occ.get("l"))
    if occ.get("g"):
        return "content-src/raw/redhat/rhel%s.candidates.jsonl#%s@%s" % (
            occ["v"], occ["g"], occ.get("l"))
    return "%s@%s" % (occ.get("p"), occ.get("l"))


# --------------------------------------------------------------------------
# C1 -- DISA STIG check/fix text
# --------------------------------------------------------------------------

def load_rules(version):
    with open(os.path.join(CONTENT, "rules_rhel%s.json" % version), encoding="utf-8") as fh:
        return json.load(fh)


def build_vocabulary(rulesets, tool_ids, page_names):
    vocab = set(COMMON_BINARIES) | set(tool_ids) | set(page_names)
    for ds in rulesets.values():
        for rule in ds.get("rules", []):
            for field in ("chk", "fix"):
                for line in (rule.get(field) or "").split("\n"):
                    m = PROMPT_RE.match(line.strip())
                    if not m or m.group(1) != "$":
                        continue
                    head = stage_one_head(m.group(2))
                    if head and CMD_TOKEN_RE.match(head):
                        vocab.add(head)
    return vocab


def mine_stig_rules(rulesets, vocab, unavailable, residue, strong, sink):
    out = []
    for version in VERSIONS:
        ds = rulesets.get(version) or {}
        for rule in ds.get("rules", []):
            for field in ("chk", "fix"):
                for n, line in enumerate((rule.get(field) or "").split("\n"), start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    anchor = {"s": rule.get("i"), "f": field, "l": n}
                    if stripped.startswith("#!") or stripped.startswith("##"):
                        residue.append(("stig", version, "config-fragment", stripped, anchor))
                        continue
                    m = PROMPT_RE.match(stripped)
                    tight = None if m else TIGHT_PROMPT_RE.match(stripped)
                    if not m and not tight:
                        residue.append(("stig", version, residue_reason_for(stripped),
                                        stripped, anchor))
                        continue
                    cmd = (m.group(2) if m else stripped[1:]).strip()
                    prompt = m.group(1) if m else "#"
                    if not cmd:
                        residue.append(("stig", version, "output-fragment", stripped, anchor))
                        continue
                    sink.append({"text": cmd, "prompt": prompt})
                    tool, why = classify(cmd, prompt, "vocabulary", vocab,
                                         unavailable.get(version, ()), strong)
                    if tool is None:
                        residue.append(("stig", version, why, stripped, anchor))
                        continue
                    out.append({
                        "command": cmd,
                        "tool": tool,
                        "kind": "invocation",
                        "authority": "governing",
                        "license_class": "verbatim-ok",
                        "family": "stig_rules",
                        # M3: byte-exact span of the source line. Prompt and
                        # surrounding whitespace removed is still a contiguous
                        # substring; nothing was joined or rewritten.
                        "verbatim_span": cmd in line,
                        "occ": occurrence(version, **anchor),
                    })
    return out


# --------------------------------------------------------------------------
# C2 -- staged man / --help captures
# --------------------------------------------------------------------------

MAN_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 ,/'\-]*$")
USAGE_RE = re.compile(r"^\s*(?:[Uu]sage|USAGE):\s*(\S.*)$")


def raw_files():
    out = []
    if not os.path.isdir(RAW):
        return out
    for d in sorted(os.listdir(RAW)):
        m = re.match(r"^rhel(\d+)$", d)
        if not m or m.group(1) not in VERSIONS:
            continue
        for name in sorted(os.listdir(os.path.join(RAW, d))):
            if name.endswith(".txt"):
                out.append((m.group(1), name, os.path.join(RAW, d, name)))
    return out


def man_sections(lines):
    sections, current = {}, None
    for n, line in enumerate(lines, start=1):
        if line.strip() and not line.startswith((" ", "\t")) and MAN_HEADING_RE.match(line.rstrip()):
            current = line.strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append((n, line))
    return sections


def mine_raw_captures(manifests, vocab, unavailable, residue, strong, sink):
    """SYNOPSIS and EXAMPLES lines. THE COMMAND LINE ONLY -- paraphrase-only
    sources contribute no prose at all, ever (qa.py Q14)."""
    out = []
    for version, fname, path in raw_files():
        key = fname[:-4]
        for suffix in (".man", ".help"):
            if key.endswith(suffix):
                key = key[: -len(suffix)]
                break
        entry = (manifests.get(version) or {}).get(key)
        if not entry:
            continue
        page = entry.get("page") or key
        if entry.get("source") == "man" and str(entry.get("section") or "") == "5":
            continue                      # a file-format page documents directives
        rel = os.path.relpath(path, REPO)
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")

        def take(n, text, kind, section):
            text = text.rstrip()
            anchor = {"p": rel, "l": n, "x": section}
            if not text:
                return
            sink.append({"text": text, "prompt": "$"})
            tool, why = classify(text, "$", "lowercase", vocab,
                                 unavailable.get(version, ()), strong)
            if tool is None:
                residue.append(("raw", version, why, text, anchor))
                return
            if tool != page:
                # Inside a man page, only the page's OWN command is a command:
                # everything else in an EXAMPLES paragraph is narrative.
                residue.append(("raw", version, "prose", text, anchor))
                return
            out.append({
                "command": text, "tool": tool, "kind": kind,
                "authority": "documentary", "license_class": "paraphrase-only",
                "family": "raw_captures",
                "verbatim_span": text in lines[n - 1],
                "occ": occurrence(version, **anchor),
            })

        if entry.get("source") == "help":
            for n, line in enumerate(lines, start=1):
                m = USAGE_RE.match(line)
                if m:
                    take(n, m.group(1), "synopsis", "USAGE")
            continue
        sections = man_sections(lines)
        for n, line in sections.get("SYNOPSIS", []):
            if line.strip():
                take(n, line.strip(), "synopsis", "SYNOPSIS")
        for n, line in sections.get("EXAMPLES", []):
            if line.strip():
                take(n, line.strip(), "invocation", "EXAMPLES")
    return out


# --------------------------------------------------------------------------
# C3 -- Red Hat product documentation (staged)
# --------------------------------------------------------------------------

GUIDE_BASE = "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/%s/"
GUIDE_URL = GUIDE_BASE + "html-single/%s/index"
GUIDE_COPYRIGHT = "(c) Red Hat, Inc., CC BY-SA 3.0 Unported"


def guide_title(slug):
    """The guide's title from its own file name. Derived, so this extractor
    carries no Red Hat prose at all -- not even a heading."""
    name = slug[:-4] if slug.endswith(".txt") else slug
    words = name.replace("_", " ").split()
    small = {"and", "or", "the", "a", "an", "to", "of", "in", "for", "on", "with", "using"}
    out = []
    for i, w in enumerate(words):
        out.append(w if (i and w in small) else (w[:1].upper() + w[1:]))
    return " ".join(out)


def guide_slug(name):
    return name[:-4] if name.endswith(".txt") else name


def staged_guide_path(version):
    return os.path.join(GUIDES_RAW, "rhel%s.candidates.jsonl" % version)


def read_staged_guides(version):
    """(manifest, [candidate, ...]) for one release, or (None, []) if not staged."""
    path = staged_guide_path(version)
    if not os.path.exists(path):
        return None, []
    manifest, rows = None, []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if i == 0:
                manifest = obj.get("_meta")
                continue
            rows.append(obj)
    return manifest, rows


def mine_redhat_guides(vocab, unavailable, residue, strong, sink):
    out, manifests = [], {}
    for version in VERSIONS:
        manifest, rows = read_staged_guides(version)
        if manifest is None:
            continue
        manifests[version] = manifest
        for row in rows:
            text = row.get("c") or ""
            anchor = {"g": guide_slug(row.get("f") or ""), "l": row.get("l")}
            sink.append({"text": text, "prompt": row.get("pr") or "#"})
            tool, why = classify(text, row.get("pr") or "#", "lowercase", vocab,
                                 unavailable.get(version, ()), strong)
            if tool is None:
                residue.append(("redhat", version, why, text, anchor))
                continue
            out.append({
                "command": text, "tool": tool, "kind": "invocation",
                "authority": "documentary", "license_class": "cc-by-sa-3.0",
                "family": "redhat_guides",
                # M3: a joined backslash continuation is this parser's
                # reconstruction, not a span of any single source line.
                "verbatim_span": not row.get("j"),
                "occ": occurrence(version, **anchor),
            })
    return out, manifests


def stage_guides(corpus_root):
    """Re-stage content-src/raw/redhat/ from the corpus. NEEDS THE CORPUS.

    Deliberately dumb: find a prompt, join backslash continuations, record the
    text and where it came from. Every judgment lives in the mining above, which
    runs offline against what this writes, so qa.py Q15 can re-run the judgment
    without reaching a lab host. The boundary is stated honestly: the gate
    re-runs the PARSE, not the STAGING, and the per-file sha256 in each
    manifest is what a reviewer with corpus access re-verifies the staging by.
    """
    if not os.path.isdir(GUIDES_RAW):
        os.makedirs(GUIDES_RAW)
    written = []
    for version in VERSIONS:
        directory = os.path.join(corpus_root, "rhel%s" % version)
        if not os.path.isdir(directory):
            continue
        files, rows, scanned = OrderedDict(), [], 0
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".txt"):
                continue
            with open(os.path.join(directory, name), "rb") as fh:
                raw = fh.read()
            lines = raw.decode("utf-8", "replace").split("\n")
            scanned += len(lines)
            here, i = 0, 0
            while i < len(lines):
                m = PROMPT_RE.match(lines[i].strip("\r").lstrip())
                if not m:
                    i += 1
                    continue
                start, joined, body = i + 1, 0, m.group(2).rstrip()
                while body.endswith("\\") and i + 1 < len(lines) and joined < 8:
                    i += 1
                    joined += 1
                    nxt = lines[i].strip()
                    if not nxt:
                        break
                    body = body[:-1].rstrip() + " " + nxt
                rows.append({"f": name, "l": start, "pr": m.group(1),
                             "c": escape(body), "j": joined})
                here += 1
                i += 1
            files[name] = {"sha256": hashlib.sha256(raw).hexdigest(),
                           "bytes": len(raw), "lines": len(lines), "candidates": here}
        meta = {"rhel_version": version, "docset": GUIDE_DOCSET,
                "staged_by": GENERATOR, "staged_on": EXTRACTED_ON,
                "corpus_root": ("<corpus>/extracted/redhat/%s/rhel%s" % (GUIDE_DOCSET, version)),
                "file_count": len(files), "lines_scanned": scanned,
                "candidate_count": len(rows),
                "note": ("prompt-prefixed candidate command lines ONLY, with backslash "
                         "continuations joined. No surrounding prose is staged, ever: the "
                         "licensing ruling permits the command line and nothing else."),
                "files": files}
        path = staged_guide_path(version)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"_meta": meta}, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")) + "\n")
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")
        written.append((path, len(rows)))
    return written


# --------------------------------------------------------------------------
# dedupe, overlap reattribution, unrated
# --------------------------------------------------------------------------

def record_id(command):
    return "ref-" + hashlib.sha256(command.encode("utf-8")).hexdigest()[:16]


# Occurrences are deduplicated to the anchor granularity that is worth keeping:
# every distinct STIG rule (so search-by-STIG-ID stays complete), and at most
# GUIDE_OCC_CAP distinct guides per release (a command in forty guides does not
# need forty citations to be attributable). The TRUE total is kept in `n`.
GUIDE_OCC_CAP = 2


def dedupe(hits):
    by_cmd = OrderedDict()
    for h in hits:
        rec = by_cmd.get(h["command"])
        if rec is None:
            rec = by_cmd[h["command"]] = {
                "id": record_id(h["command"]),
                "tier": "reference",
                "authority": h["authority"],
                "license_class": h["license_class"],
                "verbatim_span": bool(h["verbatim_span"]),
                "k": h["kind"],
                "t": h["tool"],
                "c": h["command"],
                "v": [],
                "o": [],
                "n": 0,
                "_families": set(),
                "_seen": set(),
            }
        rec["n"] += 1
        rec["_families"].add(h["family"])
        if h["occ"]["v"] not in rec["v"]:
            rec["v"].append(h["occ"]["v"])
        # ADR-002 ruling 2 / licensing condition 2: DISA wins on overlap. A
        # command that appears in BOTH the STIG text and a Red Hat guide is
        # sourced and attributed to DISA (public domain) -- and that is also the
        # stronger authority claim, so both fields move together.
        if h["authority"] == "governing":
            rec["authority"] = "governing"
            rec["license_class"] = "verbatim-ok"
        # M3: one non-verbatim occurrence makes the RECORD non-verbatim. The flag
        # is a promise about the text, and the text is shared.
        if not h["verbatim_span"]:
            rec["verbatim_span"] = False
        key = (h["occ"]["v"], h["occ"].get("s"), h["occ"].get("g"), h["occ"].get("p"))
        if key in rec["_seen"]:
            continue
        if h["occ"].get("g") and sum(1 for o in rec["o"] if o.get("g")) >= GUIDE_OCC_CAP:
            continue
        rec["_seen"].add(key)
        rec["o"].append(h["occ"])
    return by_cmd


def finalize(by_cmd, patterns):
    records, unrated = [], 0
    for rec in by_cmd.values():
        families = sorted(rec.pop("_families"))
        rec.pop("_seen")
        rec["v"] = sorted(rec["v"], key=int)
        rec["o"] = sorted(rec["o"], key=lambda o: (int(o["v"]), o.get("s") or "",
                                                   o.get("g") or "", o.get("p") or "",
                                                   o.get("l") or 0))
        stages = schema.stage_binaries(rec["c"])
        if len(stages) > 1:
            rec["st"] = stages
        if looks_truncated(rec["c"]):
            # M3 again: a truncated line is not a byte-exact usable command even
            # when it IS a byte-exact span, so it can never be evidence.
            rec["trunc"] = True
            rec["verbatim_span"] = False
        # `f` (source families) is NOT stored: it is derivable from the
        # occurrence shapes -- s is a STIG rule, g is a Red Hat guide, p is a
        # staged man capture -- and 14,558 copies of a derivable string is a
        # third of a megabyte crossing an air gap for nothing.
        # ADR-002: a mined command that matches no destructive pattern renders
        # UNRATED, never green. Green is a human claim in this product. The
        # value is recomputed in the browser from the same table; it is counted
        # here so the coverage gate can ratchet the fraction (M6).
        if not any(p.get("match", "").lower() in rec["c"].lower() for p in patterns):
            unrated += 1
        records.append(rec)
    # Condition 3 of the licensing ruling: OUR taxonomy, not theirs. Ordered by
    # tool then command text -- Red Hat's per-guide chapter ordering and
    # selection are deliberately not preserved anywhere in this file.
    records.sort(key=lambda r: (r["t"], r["c"], r["id"]))
    return records, unrated


# --------------------------------------------------------------------------
# residue
# --------------------------------------------------------------------------

FAMILY_FILES = {"stig": "stig_rules", "raw": "raw_captures", "redhat": "redhat_guides"}


def write_residue(dest_dir, residue):
    counts = {}
    buckets = {}
    for family, version, reason, text, anchor in residue:
        if reason not in RESIDUE_REASONS:
            reason = "unparseable"
        buckets.setdefault((family, version), []).append((reason, text, anchor))
        fam = FAMILY_FILES[family]
        counts.setdefault(fam, {}).setdefault(version, Counter())[reason] += 1
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    for (family, version), rows in sorted(buckets.items()):
        fam = FAMILY_FILES[family]
        rows.sort(key=lambda r: (r[0], json.dumps(r[2], sort_keys=True), r[1]))
        path = os.path.join(dest_dir, "%s_rhel%s.jsonl" % (fam, version))
        with open(path, "w", encoding="utf-8") as fh:
            header = {"_meta": {"family": fam, "rhel_version": version,
                                "generator": GENERATOR, "line_count": len(rows),
                                "reasons": dict(sorted(counts[fam][version].items())),
                                "text_encoding": ("every trojan character is written as a "
                                                  "\\\\uXXXX escape, never raw -- threat model "
                                                  "v2 M1, so Q21 keeps TROJAN_SCAN_EXCLUDE empty"),
                                "closed_reason_set": list(RESIDUE_REASONS)}}
            fh.write(json.dumps(header, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")) + "\n")
            for reason, text, anchor in rows:
                fh.write(json.dumps({"r": reason, "a": anchor, "x": escape(text)},
                                    ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")
    return counts


def write_baseline(dest_dir, counts, totals):
    path = os.path.join(dest_dir, "_baseline.json")
    payload = {
        "_meta": {
            "generator": GENERATOR,
            "pinned_on": EXTRACTED_ON,
            "what_this_is": ("the ratchet qa.py's coverage gate reads. Residue may SHRINK "
                             "(a better parser classifies more) and may never GROW, and the "
                             "unparseable count may never exceed its cap -- ADR-002: residue "
                             "is the real metric, so it is published and held."),
            "unparseable_cap": totals["unparseable_cap"],
        },
        "residue_total": totals["residue_total"],
        "unparseable_total": totals["unparseable_total"],
        "classified_total": totals["classified_total"],
        "records_total": totals["records_total"],
        "unrated_total": totals["unrated_total"],
        "unrated_fraction_max": totals["unrated_fraction_max"],
        "by_family": {fam: {v: dict(sorted(c.items())) for v, c in sorted(vs.items())}
                      for fam, vs in sorted(counts.items())},
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return path


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

SOURCE_MODULES = (
    ("stig_rules", "enabled",
     "content/rules_rhel{7,8,9,10}.json chk/fix text (DISA, public domain, verbatim-ok, governing)"),
    ("raw_captures", "enabled",
     "content-src/raw/rhel{7,8,10}/*.txt SYNOPSIS/EXAMPLES (man and --help, paraphrase-only, "
     "documentary)"),
    ("redhat_guides", "enabled",
     "content-src/raw/redhat/rhel{7,8,9,10}.candidates.jsonl, staged from 276 Red Hat guide text "
     "files (CC BY-SA 3.0 Unported, documentary) -- licensing ruling v1 Ruling 2, embed with "
     "conditions"),
    ("cac_remediations", "deferred",
     "482 ComplianceAsCode bash remediations: BSD-3 is a FOURTH license class this family does "
     "not have yet, with its own attribution requirement, and the remediations are SCRIPTS rather "
     "than command lines -- a different shape from everything here. Staging under "
     "content-src/raw/cac/ is the prerequisite, the same way redhat_guides was staged."),
)


def unavailable_binaries():
    """{version: {binary, ...}} this product records as absent on that release.

    Reads content/tools.json's availability block, which is the only place this
    codebase states it. Feeds the `binary-not-on-release` residue code.
    """
    out = {v: set() for v in VERSIONS}
    with open(os.path.join(CONTENT, "tools.json"), encoding="utf-8") as fh:
        tools = json.load(fh).get("tools", [])
    for t in tools:
        binary = t.get("binary") or t.get("id")
        for v in VERSIONS:
            a = (t.get("availability") or {}).get(v) or {}
            if a.get("available") is False:
                out[v].add(binary)
    return out, [t.get("id") for t in tools if t.get("id")]


def generate_payload():
    rulesets = {v: load_rules(v) for v in VERSIONS}
    flagsets = {}
    for v in VERSIONS:
        path = os.path.join(CONTENT, "flags_rhel%s.json" % v)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                flagsets[v] = json.load(fh)
    with open(os.path.join(CONTENT, "dangerous.json"), encoding="utf-8") as fh:
        patterns = json.load(fh).get("patterns", [])
    unavailable, tool_ids = unavailable_binaries()

    manifests, page_names = {}, set()
    for v in VERSIONS:
        path = os.path.join(RAW, "rhel%s" % v, "_manifest.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            manifests[v] = json.load(fh)
        for entry in manifests[v].values():
            if entry.get("page"):
                page_names.add(entry["page"])

    vocab = build_vocabulary(rulesets, tool_ids, page_names)

    # TWO PASSES. The first only collects candidate lines, so the second can ask
    # the corpus itself which heads it ever shows being invoked
    # (collect_strong_heads(), the TM2-F1 rule). Running the miners twice costs
    # about a second and duplicates no walking logic, which is worth more than
    # the second.
    candidates, throwaway = [], []
    mine_stig_rules(rulesets, vocab, unavailable, throwaway, (), candidates)
    mine_raw_captures(manifests, vocab, unavailable, throwaway, (), candidates)
    mine_redhat_guides(vocab, unavailable, throwaway, (), candidates)
    strong = collect_strong_heads(candidates)

    residue, sink = [], []
    stig = mine_stig_rules(rulesets, vocab, unavailable, residue, strong, sink)
    raw = mine_raw_captures(manifests, vocab, unavailable, residue, strong, sink)
    guides, guide_manifests = mine_redhat_guides(vocab, unavailable, residue, strong, sink)
    hits = stig + raw + guides

    by_cmd = dedupe(hits)
    records, unrated = finalize(by_cmd, patterns)

    # licensing ruling condition 2 -- the overlap figure, reported, not buried.
    guide_texts = set(h["command"] for h in guides)
    stig_texts = set(h["command"] for h in stig)
    overlap = sorted(guide_texts & stig_texts)

    per_family_cit = Counter(h["family"] for h in hits)
    per_family_release = {}
    for h in hits:
        per_family_release.setdefault(h["family"], Counter())[h["occ"]["v"]] += 1
    per_family_records = Counter()
    for rec in records:
        fams = set()
        for o in rec["o"]:
            fams.add("stig_rules" if o.get("s") else
                     "redhat_guides" if o.get("g") else "raw_captures")
        for fam in sorted(fams):
            per_family_records[fam] += 1

    sources = {}
    for v in VERSIONS:
        src = ((rulesets.get(v) or {}).get("_meta") or {}).get("source")
        if src:
            sources["disa-rhel%s-stig" % v] = dict(src)
        if os.path.isdir(os.path.join(RAW, "rhel%s" % v)):
            fsrc = ((flagsets.get(v) or {}).get("_meta") or {}).get("source")
            if fsrc:
                sources["raw-rhel%s" % v] = dict(fsrc)
        if v in guide_manifests:
            sources["redhat-rhel%s-guides" % v] = {
                "title": "Red Hat Enterprise Linux %s product documentation" % v,
                "url_or_man": GUIDE_BASE % v,
                "version": guide_manifests[v].get("docset") or GUIDE_DOCSET,
                "retrieved_on": EXTRACTED_ON,
                "license_class": "cc-by-sa-3.0",
                "attribution": GUIDE_COPYRIGHT,
                "notice": ("Licensed under the Creative Commons Attribution-Share Alike 3.0 "
                           "Unported license. Command lines are reproduced with attribution "
                           "under licensing ruling v1 Ruling 2 (2026-09-18), which is a "
                           "judgment call and not a settled question: attribution alone may "
                           "not discharge share-alike if counsel later disagrees."),
            }

    # Per-command attribution (licensing ruling v1 Ruling 2, condition 4): a
    # guide slug resolves to its TITLE here, and to its URL through
    # _meta.guide_url_template with the occurrence's own release. The URL is not
    # stored per slug because a slug exists on several releases and storing one
    # would silently pick a release the citation did not come from.
    guides_index = {}
    for rec in records:
        for o in rec["o"]:
            slug = o.get("g")
            if slug and slug not in guides_index:
                guides_index[slug] = {"title": guide_title(slug)}

    residue_counts = Counter()
    for _, _, reason, _, _ in residue:
        residue_counts[reason if reason in RESIDUE_REASONS else "unparseable"] += 1

    totals = {
        "residue_total": len(residue),
        "unparseable_total": residue_counts["unparseable"],
        "classified_total": len(hits),
        "records_total": len(records),
        "unrated_total": unrated,
        "unrated_fraction_max": round(unrated / float(len(records) or 1), 4),
        "unparseable_cap": max(1200, residue_counts["unparseable"]),
    }

    payload = {
        "_meta": {
            "tier": "reference",
            "generator": GENERATOR,
            "extractor_version": EXTRACTOR_VERSION,
            "extracted_on": EXTRACTED_ON,
            "extracted_on_note": ("the date of the pinned source set, not the date the extractor "
                                  "ran -- mining is a pure function of the committed sources, so "
                                  "a re-run is byte-identical (qa.py Q15)"),
            "what_this_is": ("vendor reference command text mined from sources this artifact "
                             "embeds or stages. NOT curated, NOT host-verified, NOT assembled by "
                             "this tool: no verify text, no undo text, no reviewed blast rating "
                             "and no capture receipt. content/commands.json is the only tier that "
                             "carries those, and extract/schema.py refuses those keys here."),
            "no_verification_claim": ("nothing in this family was checked against a running "
                                      "binary. Licensing ruling v1 condition 4 requires SME "
                                      "verification against each binary's own --help/man page per "
                                      "RHEL major version before any external or commercial "
                                      "release; internal lab use proceeds without it. No record "
                                      "here says or implies anything was verified."),
            "record_count": len(records),
            "citation_count": len(hits),
            "deduped_away": len(hits) - len(records),
            "counts_by_source_module": dict(sorted(per_family_cit.items())),
            "records_by_source_module": dict(sorted(per_family_records.items())),
            "citations_by_release": {fam: dict(sorted(c.items(), key=lambda kv: int(kv[0])))
                                     for fam, c in sorted(per_family_release.items())},
            "distinct_tools": len(set(r["t"] for r in records)),
            "candidate_lines": len(candidates),
            "strong_heads": len(strong),
            "verbatim_span_count": sum(1 for r in records if r["verbatim_span"]),
            "truncated_count": sum(1 for r in records if r.get("trunc")),
            "evidence_eligible_count": sum(1 for r in records
                                           if r["verbatim_span"] and r["authority"] == "governing"),
            "unrated_count": unrated,
            "disa_overlap": {
                "count": len(overlap),
                "note": ("commands appearing in BOTH the Red Hat guides and the DISA STIG text. "
                         "Licensing ruling v1 Ruling 2 condition 2: DISA wins on overlap, so "
                         "these are attributed to DISA (public domain) and their license_class "
                         "is verbatim-ok, not cc-by-sa-3.0. This nets the Red Hat count down."),
            },
            "residue": {
                "total": len(residue),
                "by_reason": dict(sorted(residue_counts.items())),
                "closed_reason_set": list(RESIDUE_REASONS),
                "where": "content-src/residue/",
                "note": ("every source line this parser declined, with a closed reason code. "
                         "Residue is the real coverage metric: the gate fails when it GROWS."),
            },
            "source_modules": [{"name": n, "status": s, "note": note}
                               for n, s, note in SOURCE_MODULES],
            "key_legend": {
                "id": "stable content-derived record id, always 'ref-' prefixed",
                "tier": "always 'reference' -- spelled out because it is a CLAIM about strength",
                "authority": "'governing' (DISA STIG, a requirement) or 'documentary' (a vendor "
                             "document describing a binary). Computed from the source, never declared",
                "license_class": "verbatim-ok | paraphrase-only | cc-by-sa-3.0",
                "verbatim_span": "true only when the text is a byte-exact contiguous span of one "
                                 "source line with nothing joined, split or rewritten. Only a "
                                 "verbatim_span record with authority 'governing' may cross into "
                                 "the evidence export, and there it renders as a QUOTATION with "
                                 "its anchor, never as a command for use (threat model v2, M3)",
                "k": "kind: invocation | synopsis",
                "t": "tool -- the binary stage one invokes, resolved through the wrapper chain",
                "c": "the command text, exactly as the source wrote it",
                "v": "RHEL releases this command was found in",
                "st": "per-stage binaries, present only on a multi-stage command",
                "o": "occurrences: {v, l} plus s (STIG id) + f (chk|fix), or g (guide slug), or "
                     "p (staged file path) + x (man section)",
                "n": "true occurrence count before the occurrence list was capped",
            },
            "guide_url_template": GUIDE_URL,
            "guide_attribution": GUIDE_COPYRIGHT,
            "guides": dict(sorted(guides_index.items())),
            "license_class": "verbatim-ok",
            "source": {
                "title": ("command lines mined from the DISA RHEL 7/8/9/10 STIG check and fix "
                          "text embedded in this artifact, the staged man/--help captures, and "
                          "the staged Red Hat product documentation"),
                "url_or_man": ("content/rules_rhel{7,8,9,10}.json; content-src/raw/rhel{7,8,10}/*.txt; "
                               "content-src/raw/redhat/rhel{7,8,9,10}.candidates.jsonl"),
                "version": EXTRACTOR_VERSION,
                "retrieved_on": EXTRACTED_ON,
                "license_class": "verbatim-ok",
            },
            "sources": sources,
        },
        "commands": records,
    }
    return payload, residue, totals


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")


def generate(content_dir, residue_dir):
    payload, residue, totals = generate_payload()
    write_json(os.path.join(content_dir, OUT_NAME), payload)
    counts = write_residue(residue_dir, residue)
    write_baseline(residue_dir, counts, totals)
    return payload, totals


def generated_files():
    out = [os.path.join("content", OUT_NAME), os.path.join("content-src", "residue", "_baseline.json")]
    if os.path.isdir(RESIDUE):
        for name in sorted(os.listdir(RESIDUE)):
            if name.endswith(".jsonl"):
                out.append(os.path.join("content-src", "residue", name))
    return out


def report(payload, totals):
    meta = payload["_meta"]
    print("mined %d citations -> %d distinct reference commands (%d deduped away)"
          % (meta["citation_count"], meta["record_count"], meta["deduped_away"]))
    print("  citations by family: %s" % ", ".join(
        "%s=%d" % kv for kv in sorted(meta["counts_by_source_module"].items())))
    print("  records by family:   %s" % ", ".join(
        "%s=%d" % kv for kv in sorted(meta["records_by_source_module"].items())))
    for fam, per in sorted(meta["citations_by_release"].items()):
        print("    %-14s %s" % (fam, ", ".join("RHEL %s=%d" % kv for kv in per.items())))
    print("  distinct tools: %d   verbatim spans: %d   evidence-eligible: %d   unrated: %d"
          % (meta["distinct_tools"], meta["verbatim_span_count"],
             meta["evidence_eligible_count"], meta["unrated_count"]))
    print("  DISA overlap reattributed from Red Hat to DISA: %d" % meta["disa_overlap"]["count"])
    print("  residue: %d lines" % totals["residue_total"])
    for reason, n in sorted(meta["residue"]["by_reason"].items(), key=lambda kv: (-kv[1], kv[0])):
        print("    %-24s %d" % (reason, n))


def main():
    args = sys.argv[1:]
    if "--stage-guides" in args:
        root = args[args.index("--stage-guides") + 1]
        for path, n in stage_guides(root):
            print("staged %s (%d candidate lines)" % (os.path.relpath(path, REPO), n))
        sys.exit(0)
    if "--report" in args:
        payload, _residue, totals = generate_payload()
        report(payload, totals)
        sys.exit(0)
    if "--check" in args:
        tmp_content = tempfile.mkdtemp(prefix="mcr-mine-c-")
        tmp_residue = tempfile.mkdtemp(prefix="mcr-mine-r-")
        try:
            generate(tmp_content, tmp_residue)
            fresh = {os.path.join("content", OUT_NAME): os.path.join(tmp_content, OUT_NAME)}
            for name in sorted(os.listdir(tmp_residue)):
                fresh[os.path.join("content-src", "residue", name)] = os.path.join(tmp_residue, name)
            drift = []
            for rel in sorted(set(fresh) | set(generated_files())):
                live = os.path.join(REPO, rel)
                new_path = fresh.get(rel)
                if new_path is None:
                    drift.append("%s: committed but a fresh run does not produce it" % rel)
                elif not os.path.exists(live):
                    drift.append("%s: a fresh run produces it and it is not committed" % rel)
                elif open(live, encoding="utf-8").read() != open(new_path, encoding="utf-8").read():
                    drift.append("%s: differs from a fresh extractor run" % rel)
            if drift:
                print("GENERATED-FILE DRIFT (%s):" % GENERATOR)
                for d in drift:
                    print("  " + d)
                sys.exit(1)
            print("%s: %d generated file(s) match a fresh extractor run" % (GENERATOR,
                                                                           len(generated_files())))
            sys.exit(0)
        finally:
            shutil.rmtree(tmp_content, ignore_errors=True)
            shutil.rmtree(tmp_residue, ignore_errors=True)

    payload, totals = generate(CONTENT, RESIDUE)
    report(payload, totals)
    for rel in generated_files():
        print("wrote %s (%d bytes)" % (rel, os.path.getsize(os.path.join(REPO, rel))))


if __name__ == "__main__":
    main()
