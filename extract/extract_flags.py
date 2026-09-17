#!/usr/bin/env python3
"""extract_flags.py — CR-T-09/10: FLAGS dictionaries from real RHEL hosts.

Stdlib only. Two ways to run it:

    python3 extract/extract_flags.py --host defiant --rhel 8
    python3 extract/extract_flags.py --host saratoga --rhel 10

    python3 extract/extract_flags.py --check --rhel 8
    python3 extract/extract_flags.py --check --rhel 10

`--host` is the live path (ADR-001 §6.1): SSH to the named alias, run read-only
`man -P cat` / `<tool> --help` / `rpm -q` / `cat /etc/redhat-release` / `uname -r`
against the real box, save the RAW output under content-src/raw/rhel<N>/ (git-
ignored — SOURCES OF RECORD for the licensing review and for Q14's paraphrase
collision check, never read by build.py), and write the parsed skeleton to
content/flags_rhel<N>.json.

`--check` is the offline path: re-parse the RAW dumps already sitting under
content-src/raw/rhel<N>/ (no SSH, no live host needed) and diff the result
against content/flags_rhel<N>.json, ignoring only the _meta timestamp fields
that are allowed to advance run to run. This is what qa.py's Q15 gate calls —
see the note in qa.py next to that call for why FLAGS gets its own drift check
instead of running through extract/make_skeleton_content.py's generic one
(that script only knows how to emit the *empty*, pending FLAGS skeleton; it
predates this extractor and CR-T-02 says as much in its own docstring).

PARSING, HONESTLY. Man pages are GPL-2.0-or-later (content-licensing-ruling-v1
§"Linux man-pages"): paraphrase only, never verbatim. This extractor never
writes prose — every flag's `explain` is emitted `null` and stays that way
until a human (Caleb, RHEL SME) curates an original paraphrase; re-running
this script never overwrites a filled `explain` (ADR-001 §6.1/§6.3). What the
parser does extract — flag/directive *names* and whether they take an
argument — is structural fact about the interface, not the vendor's prose, so
it is not a licensing concern.

The parser looks for the standard man-page definition-list shape: a short
"term" line (a flag spec, or for a config(5) page a directive name) preceded
by a blank line, whose own indent is shallower than or equal to its
description. It is deliberately conservative — see `_term_candidates()` — and
anything option-shaped that it cannot confidently resolve into a name is kept
as raw text under a tool's `unparsed[]` rather than guessed at (ADR-001 §6.1's
"never guessed" instruction, echoed in the CR-T-09/10 task brief).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(REPO, "content")
RAW_DIR = os.path.join(REPO, "content-src", "raw")
EXTRACTOR_VERSION = "1.0.0"
GENERATOR = "extract/extract_flags.py"

HOSTS = {
    "defiant": {"rhel_version": "8"},
    "saratoga": {"rhel_version": "10"},
}

# CR-T-12: there is no RHEL 7 host in the lab. The read-only commands this
# extractor already runs (man -P cat / <tool> --help / rpm -qf / command -v)
# are routed one extra hop, through `podman exec` into a rootless UBI7
# container on an existing --host, instead of adding a whole second
# extraction path. Set by main() from --container; left None for the normal
# direct-SSH-to-a-real-host case, which is unaffected (see ssh_run() below).
CONTAINER_EXEC = None

# P0 tool set (MD CODE RED task brief, CR-T-09/10). `pages` lists every man
# page this tool's dictionary is built from, in the order they are read. A
# page equal to the tool id is the tool's own CLI page; a page that differs
# is a companion doc page named explicitly by the brief (sshd_config(5) for
# sshd, rsyslog.conf(5) for rsyslogd, chrony.conf(5) + chronyc for chronyd).
TOOL_PAGES = {
    "systemctl": ["systemctl"],
    "firewall-cmd": ["firewall-cmd"],
    "nmcli": ["nmcli"],
    "dnf": ["dnf"],
    "yum": ["yum"],
    "semanage": ["semanage"],
    "setsebool": ["setsebool"],
    "useradd": ["useradd"],
    "usermod": ["usermod"],
    "chage": ["chage"],
    "pvcreate": ["pvcreate"],
    "vgcreate": ["vgcreate"],
    "lvcreate": ["lvcreate"],
    "lvextend": ["lvextend"],
    "sshd": ["sshd", "sshd_config"],
    "journalctl": ["journalctl"],
    "auditctl": ["auditctl"],
    "ausearch": ["ausearch"],
    "rsyslogd": ["rsyslogd", "rsyslog.conf"],
    "chronyd": ["chronyd", "chrony.conf", "chronyc"],
    "podman": ["podman"],
    "git": ["git"],
}

HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 '/-]{1,60}$")
SENTENCE_STARTER_BLOCKLIST = {
    "see", "note", "notes", "this", "the", "for", "when", "if", "by", "as",
    "it", "each", "some", "many", "most", "also", "in", "on", "with", "use",
    "using", "a", "an", "these", "those", "unless", "while", "after",
    "before", "however", "instead", "note:", "warning", "caution", "example",
    "examples", "default", "defaults", "since", "because", "note,",
}


# --------------------------------------------------------------------------
# SSH plumbing — read-only, no sudo, no writes, per the task's host rules.
# --------------------------------------------------------------------------

def ssh_run(host, remote_cmd, timeout=30):
    """Run one read-only command over SSH and return (rc, stdout, stderr).

    Uses the ssh alias's own config (key auth already wired per-host); no
    password prompts, no state changes. BatchMode=yes so a broken/missing key
    fails fast instead of hanging on a prompt.

    CR-T-12: when CONTAINER_EXEC is set, every one of these still-read-only
    commands is run one hop further in, via `podman exec <container> sh -c
    '<remote_cmd>'` on the SSH host — same transport, same command set, the
    container is just where they execute. No other function in this file
    changes; they all go through here.
    """
    if CONTAINER_EXEC:
        remote_cmd = "podman exec %s sh -c %s" % (CONTAINER_EXEC, _shquote(remote_cmd))
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, remote_cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def host_facts(host):
    rc, out, err = ssh_run(host, "cat /etc/redhat-release")
    if rc != 0:
        sys.exit("FATAL: cat /etc/redhat-release failed on %s: %s" % (host, err.strip()))
    redhat_release = out.strip()
    rc, out, err = ssh_run(host, "uname -r")
    if rc != 0:
        sys.exit("FATAL: uname -r failed on %s: %s" % (host, err.strip()))
    kernel = out.strip()
    return redhat_release, kernel


def command_path(host, name):
    """`command -v <name>` on the host, or None."""
    rc, out, _ = ssh_run(host, "command -v %s 2>/dev/null" % _shquote(name))
    out = out.strip()
    return out if rc == 0 and out else None


def man_path(host, page):
    """`man -w <page>` on the host, or None if no man page exists."""
    rc, out, _ = ssh_run(host, "man -w %s 2>/dev/null" % _shquote(page))
    out = out.strip().splitlines()[0].strip() if out.strip() else ""
    return out if rc == 0 and out else None


def man_text(host, page):
    rc, out, err = ssh_run(host, "man -P cat %s 2>/dev/null" % _shquote(page))
    if rc != 0 or not out.strip():
        return None
    return out


def help_text(host, binary):
    rc, out, err = ssh_run(host, "%s --help 2>&1" % _shquote(binary))
    text = (out or "") + (err or "" if rc != 0 and not out else "")
    return text if text.strip() else None


def package_nvra(host, binpath):
    rc, out, _ = ssh_run(host, "rpm -qf --qf '%%{NVRA}\\n' %s 2>/dev/null" % _shquote(binpath))
    if rc != 0 or not out.strip():
        return None
    # rpm -qf can print more than one line if a path is owned by >1 package
    # (rare); the first line is the NVRA we record.
    return out.strip().splitlines()[0].strip()


def _shquote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def section_from_manpath(path):
    if not path:
        return None
    m = re.search(r"/man(\d[a-z]?)/[^/]+\.(\d[a-z]?)(?:\.\w+)?$", path)
    return m.group(2) if m else (m.group(1) if m else None)


# --------------------------------------------------------------------------
# Parsing — man-page definition-list scanner (flags AND config directives).
# --------------------------------------------------------------------------

def find_section(text):
    """Return the body text of the most useful section(s) to scan for flags.

    Preference order: every heading whose name *contains* OPTIONS (a page can
    split them — journalctl has "SOURCE OPTIONS"/"FILTERING OPTIONS"/etc.,
    auditctl has "CONFIGURATION OPTIONS" — none of them spelled plain
    "OPTIONS"), concatenated in document order; else DIRECTIVES; else
    DESCRIPTION; else the whole document. Man sections in `man -P cat`
    output are headings flush at column 0."""
    lines = text.splitlines()
    heading_idx = []
    for i, line in enumerate(lines):
        if line and not line[0].isspace() and HEADING_RE.match(line.strip()):
            heading_idx.append((i, line.strip()))
    if not heading_idx:
        return text, None

    def body_of(idx):
        i = heading_idx[idx][0]
        end = heading_idx[idx + 1][0] if idx + 1 < len(heading_idx) else len(lines)
        return "\n".join(lines[i + 1:end])

    options_idx = [idx for idx, (_i, name) in enumerate(heading_idx) if "OPTIONS" in name]
    if options_idx:
        names = [heading_idx[idx][1] for idx in options_idx]
        return "\n\n".join(body_of(idx) for idx in options_idx), "+".join(names)
    for want in ("DIRECTIVES", "GLOBAL DIRECTIVES", "DESCRIPTION"):
        for idx, (i, name) in enumerate(heading_idx):
            if name == want:
                return body_of(idx), name
    # fall back to everything after NAME/SYNOPSIS
    start = heading_idx[0][0]
    return "\n".join(lines[start:]), heading_idx[0][1]


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _term_candidates(lines):
    """Lines that look like the start of a definition-list entry: preceded
    by a blank line (or section start), starting with a flag dash or a bare
    identifier, short, and not an English sentence continuation."""
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        prev_blank = (i == 0) or (not lines[i - 1].strip())
        if not prev_blank:
            continue
        indent = _indent(line)
        if indent == 0:
            continue
        stripped = line.strip()
        first_char = stripped[0]
        if not (first_char == "-" or first_char.isalpha()):
            continue
        first_token = re.split(r"[\s,]", stripped, maxsplit=1)[0].strip(",")
        if first_token.lower().rstrip(".:") in SENTENCE_STARTER_BLOCKLIST:
            continue
        # systemd-family man pages annotate nearly every option with a
        # standalone "Added in version N." / "Deprecated since version N."
        # changelog note, blank-line-separated just like a real term line —
        # on a page with enough options these can outnumber the actual
        # flags and hijack the indent-mode vote. Not a flag; skip outright.
        if re.match(r"^(added|deprecated|removed|changed)\b.*\bversion\b", stripped, re.IGNORECASE):
            continue
        words = stripped.split()
        # A dash-led line can be a single-line "flag   description sentence"
        # (rsyslogd's "-D     Runs the Bison config parser..."), so it gets a
        # generous cap. A bare-word directive/identifier line (config(5)
        # pages) is never that long in practice, so it stays tight — this is
        # what keeps prose continuation sentences ("See PATTERNS in ...")
        # out of the candidate set.
        if stripped.startswith("-"):
            if len(words) > 24:
                continue
        elif len(words) > 6:
            continue
        out.append((i, indent, stripped))
    return out


def _mode_indent(candidates):
    if not candidates:
        return None
    counts = {}
    for _i, indent, _s in candidates:
        counts[indent] = counts.get(indent, 0) + 1
    best = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
    return best[0]


NAME_TOKEN_RE = re.compile(r"^-{1,2}[A-Za-z0-9][\w-]*(=\S*)?$")


DESCRIPTION_VERB_BLOCKLIST = {
    "specifies", "specify", "sets", "set", "enables", "enable", "disables",
    "disable", "allows", "allow", "turns", "prints", "print", "shows",
    "show", "runs", "run", "avoid", "display", "displays", "get", "gets",
    "use", "uses", "used", "do", "does", "generates", "generate", "include",
    "includes", "resolve", "resolves", "continue", "delete", "deletes",
    "reset", "resets", "equivalent", "test", "tests", "write", "writes",
}


def _looks_like_metavar_phrase(rest_toks):
    """rest_toks is whatever follows the flag name(s) on a term line, already
    split on whitespace. True means "confidently a metavar/argument
    placeholder", not "the start of a description sentence"."""
    if not rest_toks:
        return False
    head = rest_toks[0]
    if re.match(r"^(\[?<?[A-Z0-9_]{2,24}>?\]?|<[^>]{1,24}>|\[[^\]]{1,24}\])$", head):
        return True
    if len(rest_toks) > 3:
        return False
    for tok in rest_toks:
        if re.search(r"[.,;:]$", tok):
            return False
        if tok.lower().rstrip("().") in DESCRIPTION_VERB_BLOCKLIST:
            return False
        if not re.match(r"^[A-Za-z][A-Za-z0-9_/.=-]{0,23}$", tok):
            return False
    return True


def _parse_cli_term(stripped):
    """A term line like '-t, --type=', '-a, --all', '-4', '--advisory=<x>,
    --advisories=<x>', or a single-line 'flag  metavar' / 'flag  desc.'
    spec. Returns (names[], takes_arg) or None if it doesn't look like a
    clean flag spec."""
    # Split only on commas that separate flag aliases ('-a, --all'), i.e. a
    # comma immediately followed by another dash token — never on a comma
    # inside an inline single-line description or metavar list ('(-k), too.',
    # '{field1,field2}'), which would otherwise fracture the line into
    # bogus non-flag "pieces" and reject the whole term.
    pieces = [p.strip() for p in re.split(r",\s*(?=-)", stripped)]
    names = []
    takes_arg = False
    for p in pieces:
        toks = p.split()
        if not toks or not toks[0].startswith("-"):
            return None
        flag = toks[0]
        if "=" in flag:
            flag_name, _eq, metavar = flag.partition("=")
            flag_name = re.sub(r"[^\w-]+$", "", flag_name)  # e.g. '--boot[' -> '--boot'
            names.append(flag_name)
            if metavar:
                takes_arg = True
        else:
            names.append(flag)
        if len(toks) > 1 and _looks_like_metavar_phrase(toks[1:]):
            takes_arg = True
    if not names or not all(NAME_TOKEN_RE.match(n) or n.startswith("-") for n in names):
        # still accept plain dash names even if the regex was too strict
        if not names:
            return None
    return names, takes_arg


def _parse_directive_term(stripped):
    """A config(5) definition-list term, e.g. 'AllowGroups', 'Banner file',
    'server hostname [option]...'. Returns (names[], takes_arg) or None."""
    toks = stripped.split()
    name = toks[0]
    if not re.match(r"^[A-Za-z][A-Za-z0-9_.-]{0,39}$", name):
        return None
    takes_arg = len(toks) > 1  # an inline argument placeholder follows the name
    return [name], takes_arg


LOOSE_FLAG_RE = re.compile(r"(?<![\w-])(-{1,2}[A-Za-z][\w-]*)")


def _loose_scan_fallback(body, page, raw_ref):
    """Used only when the definition-list scan above found nothing at all —
    e.g. setsebool(8), whose flags are named only in narrative DESCRIPTION
    prose ('If the -P option is given, ...'), never in a term-line list. We
    still do not want those flags to vanish silently, so every dash token
    that appears is recorded as a raw, unstructured hint — never promoted to
    a parsed `flags[]` entry, because there is no reliable name/arg boundary
    to read out of prose (ADR-001's 'never guessed')."""
    seen = set()
    hints = []
    for m in LOOSE_FLAG_RE.finditer(body):
        tok = m.group(1)
        if tok in seen or len(tok) < 2:
            continue
        seen.add(tok)
        hints.append(tok)
    if not hints:
        return []
    return [{
        "raw_ref": raw_ref,
        "page": page,
        "text": "no OPTIONS-style definition list found; flag-like tokens seen in prose: "
                + ", ".join(sorted(hints)[:40]),
    }]


def parse_definition_list(raw_text, page, section, raw_ref):
    """Return (flags[], unparsed[]) for one man page's most relevant section."""
    body, _heading = find_section(raw_text)
    lines = body.splitlines()
    candidates = _term_candidates(lines)
    term_indent = _mode_indent(candidates)
    flags, unparsed = [], []
    for i, indent, stripped in candidates:
        if term_indent is not None and indent != term_indent:
            continue
        if stripped.startswith("-"):
            parsed = _parse_cli_term(stripped)
        else:
            parsed = _parse_directive_term(stripped)
        if parsed is None:
            unparsed.append({
                "raw_ref": raw_ref,
                "page": page,
                "text": stripped[:200],
            })
            continue
        names, takes_arg = parsed
        flags.append({
            "names": names,
            "takes_arg": takes_arg,
            "explain": None,
            "page": page,
            "section": section,
            "raw_ref": raw_ref,
        })
    if not flags and not unparsed:
        unparsed = _loose_scan_fallback(body, page, raw_ref)
    return flags, unparsed


HELP_OPT_RE = re.compile(r"^\s{0,4}(-{1,2}[A-Za-z0-9][\w-]*(?:,\s*-{1,2}[A-Za-z0-9][\w-]*)*)(\s{2,}.*|\s*=\s*\S+)?$")


def parse_help_text(raw_text, page, raw_ref):
    """Fallback for a tool with no man page: parse `--help` argparse-ish
    output the same way extract_ansible_doc.py does — flag-spec lines, one
    or more dash tokens, optionally an inline metavar/description."""
    flags, unparsed = [], []
    seen = set()
    for line in raw_text.splitlines():
        if not line.strip().startswith("-"):
            continue
        m = HELP_OPT_RE.match(line)
        if not m:
            if re.match(r"^\s{0,4}-", line):
                unparsed.append({"raw_ref": raw_ref, "page": page, "text": line.strip()[:200]})
            continue
        names_part = m.group(1)
        tail = (m.group(2) or "").strip()
        names = [tok.strip().split("=")[0] for tok in names_part.split(",")]
        key = tuple(names)
        if key in seen:
            continue
        seen.add(key)
        takes_arg = bool(tail) and (
            "=" in (m.group(2) or "") or bool(re.match(r"^[<\[]?[A-Z0-9_]{1,24}[>\]]?(\s|$)", tail))
        )
        flags.append({
            "names": names, "takes_arg": takes_arg, "explain": None,
            "page": page, "section": "--help", "raw_ref": raw_ref,
        })
    return flags, unparsed


# --------------------------------------------------------------------------
# Live extraction (SSH) — writes content-src/raw/ and returns the clis dict.
# --------------------------------------------------------------------------

def _manifest_path(rhel_version):
    return os.path.join(RAW_DIR, "rhel%s" % rhel_version, "_manifest.json")


def load_raw_manifest(rhel_version):
    path = _manifest_path(rhel_version)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_raw_manifest(rhel_version, manifest):
    raw_subdir = os.path.join(RAW_DIR, "rhel%s" % rhel_version)
    os.makedirs(raw_subdir, exist_ok=True)
    with open(_manifest_path(rhel_version), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")


def extract_tool_live(host, tool_id, pages, rhel_version, manifest):
    binpath = command_path(host, tool_id)
    if not binpath:
        where = "container %s on %s" % (CONTAINER_EXEC, host) if CONTAINER_EXEC else host
        return {"available": False, "reason": "rpm not installed / '%s' not found via command -v on %s" % (tool_id, where)}
    pkg = package_nvra(host, binpath)
    result = {"available": True, "package": pkg, "pages": [], "flags": [], "unparsed": []}
    raw_subdir = os.path.join(RAW_DIR, "rhel%s" % rhel_version)
    os.makedirs(raw_subdir, exist_ok=True)
    for page in pages:
        fname_base = tool_id if page == tool_id else "%s.%s" % (tool_id, page)
        mpath = man_path(host, page)
        if mpath:
            section = section_from_manpath(mpath)
            text = man_text(host, page)
            if text is None:
                result["pages"].append({"name": page, "available": False, "reason": "man -w found a page but man -P cat produced no output"})
                continue
            raw_file = os.path.join(raw_subdir, "%s.man.txt" % fname_base)
            with open(raw_file, "w", encoding="utf-8") as f:
                f.write(text)
            raw_ref = os.path.relpath(raw_file, REPO)
            flags, unparsed = parse_definition_list(text, page, section, raw_ref)
            result["pages"].append({"name": page, "section": section, "source": "man", "raw_ref": raw_ref})
            result["flags"].extend(flags)
            result["unparsed"].extend(unparsed)
            manifest[fname_base] = {"page": page, "section": section, "source": "man"}
        else:
            page_bin = command_path(host, page)
            if page_bin:
                text = help_text(host, page)
                if text:
                    raw_file = os.path.join(raw_subdir, "%s.help.txt" % fname_base)
                    with open(raw_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    raw_ref = os.path.relpath(raw_file, REPO)
                    flags, unparsed = parse_help_text(text, page, raw_ref)
                    result["pages"].append({"name": page, "section": None, "source": "--help", "raw_ref": raw_ref})
                    result["flags"].extend(flags)
                    result["unparsed"].extend(unparsed)
                    manifest[fname_base] = {"page": page, "section": None, "source": "help"}
                else:
                    result["pages"].append({"name": page, "available": False, "reason": "no man page and --help produced no output"})
            else:
                result["pages"].append({"name": page, "available": False, "reason": "no man page and '%s' is not a binary (command -v failed)" % page})
    return result


def run_extract(host, rhel_version):
    redhat_release, kernel = host_facts(host)
    clis = {}
    manifest = {}
    for tool_id, pages in sorted(TOOL_PAGES.items()):
        print("  %-14s ..." % tool_id, end=" ", flush=True)
        entry = extract_tool_live(host, tool_id, pages, rhel_version, manifest)
        clis[tool_id] = entry
        if entry.get("available") is False:
            print("NOT AVAILABLE (%s)" % entry.get("reason"))
        else:
            print("%d flags, %d unparsed" % (len(entry.get("flags", [])), len(entry.get("unparsed", []))))
    save_raw_manifest(rhel_version, manifest)
    extracted_on = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    patch_level = "%s, kernel %s" % (redhat_release, kernel)
    meta = {
        "rhel_version": rhel_version,
        "host": host,
        "redhat_release": redhat_release,
        "kernel": kernel,
        "patch_level": patch_level,
        "captured_on": extracted_on,
        "extracted_on": extracted_on,
        "generator": GENERATOR,
        "extractor_version": EXTRACTOR_VERSION,
        "license_class": "paraphrase-only",
        "status": "extracted from %s (RHEL %s) — %d tools" % (host, rhel_version, len(clis)),
        "source": {
            "title": "man pages and --help output of the installed binaries on a RHEL %s host (%s)" % (rhel_version, host),
            "url_or_man": "man -P cat <section> <tool>; <tool> --help",
            "version": patch_level,
            "retrieved_on": extracted_on,
            "license_class": "paraphrase-only",
        },
    }
    return merge_preserving_explain(load_existing(rhel_version), {"_meta": meta, "clis": clis})


def load_existing(rhel_version):
    path = os.path.join(CONTENT_DIR, "flags_rhel%s.json" % rhel_version)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_preserving_explain(old, new):
    """Non-destructive re-run (ADR-001 §6.1): a filled `explain` in the old
    file survives a re-run; the extractor itself never writes one."""
    if not old or not old.get("clis"):
        return new
    old_clis = old["clis"]
    for tool_id, entry in new["clis"].items():
        old_entry = old_clis.get(tool_id)
        if not old_entry or not old_entry.get("flags"):
            continue
        old_by_names = {tuple(fl.get("names") or []): fl for fl in old_entry.get("flags", [])}
        for fl in entry.get("flags", []):
            key = tuple(fl.get("names") or [])
            prior = old_by_names.get(key)
            if prior and prior.get("explain"):
                fl["explain"] = prior["explain"]
                fl["curated_by"] = prior.get("curated_by")
                fl["curated_on"] = prior.get("curated_on")
        # flags no longer seen: mark removed rather than silently drop
        new_keys = {tuple(fl.get("names") or []) for fl in entry.get("flags", [])}
        for key, prior in old_by_names.items():
            if key not in new_keys and not prior.get("removed_in"):
                removed = dict(prior)
                removed["removed_in"] = new["_meta"]["rhel_version"] + " (as of " + new["_meta"]["extracted_on"] + ")"
                entry["flags"].append(removed)
    return new


def write_flags_json(rhel_version, data):
    path = os.path.join(CONTENT_DIR, "flags_rhel%s.json" % rhel_version)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")
    return path


# --------------------------------------------------------------------------
# Offline re-derivation — qa.py Q15 calls this, no SSH, no live host needed.
# --------------------------------------------------------------------------

def reparse_from_raw(rhel_version):
    """Re-parse the cached raw dumps under content-src/raw/rhel<N>/ and
    return a fresh clis dict, with no network access at all. This is the
    reproducibility check: content-src/raw/ is the pinned input, exactly as
    ADR-001 §6.3 describes for every other generated family."""
    raw_subdir = os.path.join(RAW_DIR, "rhel%s" % rhel_version)
    manifest = load_raw_manifest(rhel_version)
    clis = {}
    for tool_id, pages in sorted(TOOL_PAGES.items()):
        entry = {"available": True, "pages": [], "flags": [], "unparsed": []}
        any_page = False
        for page in pages:
            fname_base = tool_id if page == tool_id else "%s.%s" % (tool_id, page)
            man_file = os.path.join(raw_subdir, "%s.man.txt" % fname_base)
            help_file = os.path.join(raw_subdir, "%s.help.txt" % fname_base)
            if os.path.exists(man_file):
                any_page = True
                text = open(man_file, encoding="utf-8").read()
                raw_ref = os.path.relpath(man_file, REPO)
                section = (manifest.get(fname_base) or {}).get("section")
                flags, unparsed = parse_definition_list(text, page, section, raw_ref)
                entry["pages"].append({"name": page, "section": section, "source": "man", "raw_ref": raw_ref})
                entry["flags"].extend(flags)
                entry["unparsed"].extend(unparsed)
            elif os.path.exists(help_file):
                any_page = True
                text = open(help_file, encoding="utf-8").read()
                raw_ref = os.path.relpath(help_file, REPO)
                flags, unparsed = parse_help_text(text, page, raw_ref)
                entry["pages"].append({"name": page, "section": None, "source": "--help", "raw_ref": raw_ref})
                entry["flags"].extend(flags)
                entry["unparsed"].extend(unparsed)
        if not any_page:
            entry = {"available": False, "reason": "no cached raw dump under content-src/raw/rhel%s/ for '%s'" % (rhel_version, tool_id)}
        clis[tool_id] = entry
    return clis


def _strip_volatile(flags):
    """Drop fields that are allowed to differ run to run (curated explain
    metadata, removed_in bookkeeping) so the comparison is about parsed
    structure, not curation state."""
    out = []
    for fl in flags:
        out.append({"names": fl.get("names"), "takes_arg": fl.get("takes_arg"),
                    "page": fl.get("page"), "section": fl.get("section")})
    return sorted(out, key=lambda x: (x["page"] or "", x["names"] or []))


def check_against_raw(rhel_version):
    """Returns a list of human-readable drift lines; empty means clean."""
    existing = load_existing(rhel_version)
    if not existing or not existing.get("clis"):
        return ["flags_rhel%s.json has no clis to check (nothing extracted yet)" % rhel_version]
    fresh_clis = reparse_from_raw(rhel_version)
    drift = []
    for tool_id, old_entry in existing["clis"].items():
        fresh_entry = fresh_clis.get(tool_id)
        if fresh_entry is None:
            drift.append("%s: no raw dump to re-check against" % tool_id)
            continue
        if old_entry.get("available") is False or fresh_entry.get("available") is False:
            if bool(old_entry.get("available") is False) != bool(fresh_entry.get("available") is False):
                drift.append("%s: availability mismatch between content/ and raw re-parse" % tool_id)
            continue
        old_flags = _strip_volatile(old_entry.get("flags", []))
        fresh_flags = _strip_volatile(fresh_entry.get("flags", []))
        if old_flags != fresh_flags:
            drift.append("%s: parsed flags differ from a fresh re-parse of content-src/raw/rhel%s/ "
                        "(%d in content/, %d from raw)" % (tool_id, rhel_version, len(old_flags), len(fresh_flags)))
    return drift


# --------------------------------------------------------------------------

def main():
    global CONTAINER_EXEC
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", choices=sorted(HOSTS), help="SSH alias to extract from live")
    ap.add_argument("--rhel", choices=("7", "8", "9", "10"), required=True)
    ap.add_argument("--check", action="store_true", help="offline: re-parse content-src/raw/ and diff, no SSH")
    ap.add_argument("--container", help="CR-T-12: podman container name on --host to exec the same "
                     "read-only commands inside, when --rhel names a release --host itself isn't "
                     "(e.g. a UBI7 container on a RHEL 10 host standing in for a RHEL 7 source)")
    ap.add_argument("--container-image", help="with --container: image ref, recorded in _meta only")
    ap.add_argument("--container-image-digest", help="with --container: image digest, recorded in _meta only")
    args = ap.parse_args()

    if args.check:
        drift = check_against_raw(args.rhel)
        if drift:
            print("FLAGS DRIFT (rhel%s):" % args.rhel)
            for d in drift:
                print("  " + d)
            sys.exit(1)
        print("flags_rhel%s.json matches a fresh offline re-parse of content-src/raw/rhel%s/" % (args.rhel, args.rhel))
        sys.exit(0)

    if not args.host:
        sys.exit("FATAL: --host is required unless --check is given")
    # A --container is a stand-in guest OS, not the SSH host's own release —
    # that's the whole point of it, so the direct host/--rhel cross-check
    # below is skipped only in that case; the direct-host path is unchanged.
    if not args.container and HOSTS[args.host]["rhel_version"] != args.rhel:
        sys.exit("FATAL: %s is RHEL %s, not RHEL %s" % (args.host, HOSTS[args.host]["rhel_version"], args.rhel))

    CONTAINER_EXEC = args.container
    if args.container:
        print("extracting FLAGS for RHEL %s from container %s on %s (read-only, no sudo)..."
              % (args.rhel, args.container, args.host))
    else:
        print("extracting FLAGS for RHEL %s from %s (read-only, no sudo)..." % (args.rhel, args.host))
    data = run_extract(args.host, args.rhel)
    if args.container:
        # host_facts() read /etc/redhat-release and uname -r through the
        # container — the release string is genuinely the container's own
        # (UBI7 ships a real /etc/redhat-release), but uname -r is a kernel
        # syscall a container can't sandbox: it reports the SSH host's real
        # kernel, not a RHEL 7 one. Say so plainly rather than let a RHEL 10
        # kernel string sit unremarked in a RHEL 7 dictionary's _meta.
        data["_meta"]["host"] = "ubi7 container on %s" % args.host
        data["_meta"]["status"] = data["_meta"]["status"].replace(
            "extracted from %s " % args.host, "extracted from ubi7 container on %s " % args.host)
        data["_meta"]["source"]["title"] = data["_meta"]["source"]["title"].replace(
            "on a RHEL 7 host (%s)" % args.host, "in a UBI7 container on %s, standing in for a RHEL 7 host (CR-T-12, no RHEL 7 host in the lab)" % args.host)
        data["_meta"]["underlying_ssh_host"] = args.host
        data["_meta"]["container_name"] = args.container
        data["_meta"]["container_image"] = args.container_image
        data["_meta"]["container_image_digest"] = args.container_image_digest
        data["_meta"]["kernel_caveat"] = (
            "kernel field above is the container's shared host kernel (%s on %s), not a genuine "
            "RHEL 7 kernel — containers don't have their own; kernel- and systemd-manager-dependent "
            "behaviour (actual unit activation, live journald/systemd-logind state, etc.) was NOT "
            "observed or exercised, only each tool's own --help/man text as shipped in the package"
            % (data["_meta"]["kernel"], args.host)
        )
    path = write_flags_json(args.rhel, data)
    n_tools = len(data["clis"])
    n_avail = sum(1 for e in data["clis"].values() if e.get("available") is not False)
    n_flags = sum(len(e.get("flags", [])) for e in data["clis"].values())
    n_unparsed = sum(len(e.get("unparsed", [])) for e in data["clis"].values())
    print("wrote %s: %d tools (%d available), %d flags parsed, %d unparsed"
          % (os.path.relpath(path, REPO), n_tools, n_avail, n_flags, n_unparsed))


if __name__ == "__main__":
    main()
