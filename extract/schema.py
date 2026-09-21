#!/usr/bin/env python3
"""schema.py — the ADR-001 §5 content schema, in one place.

Stdlib only, no I/O, no side effects: every function takes already-loaded JSON and
returns a list of human-readable error strings. Empty list means the content is
schema-clean.

WHY THIS FILE EXISTS (CR-T-06). Before it, the entry schema lived only inside
build.py's validate(), so tests/ could only assert the schema by shelling out to a
build. Two copies of a schema is one copy too many: the copy the tests exercise
drifts from the copy the build enforces, and the drift is invisible until a bad
entry ships. build.py and tests/test_schema.py now import this module, so there is
exactly one statement of what a valid entry is.

The rules implemented here are ADR-001 §5.1 (entry schema and field notes), §5.3
(RULES datasets), §5.4 (CCI map), §5.5 (FLAGS and TOOLS), and the provenance law
(§7.3 Q3). Gate numbering in qa.py stays the authority for the *assembled* file;
this module is the authority for the *sources* in content/.
"""

import re

VERSIONS = ("7", "8", "9", "10")
BLASTS = ("green", "yellow", "red")
# "cc-by-sa-3.0" is the THIRD class, added for the Red Hat product-documentation
# command lines (licensing ruling v1 Ruling 2, Alex Okafor, 2026-09-18: EMBED
# WITH CONDITIONS). It is not "verbatim-ok" -- that class means public-domain
# DISA text this product may reproduce freely -- and it is not "paraphrase-only",
# because the ruling permits the COMMAND LINE itself to be embedded. It carries
# obligations the other two do not: per-command attribution (guide title, URL,
# "(c) Red Hat, Inc., CC BY-SA 3.0 Unported"), a full CC BY-SA notice in the
# About panel, and the surrounding PROSE staying paraphrase-only with no
# exception. The ruling is explicitly a judgment call, and attribution alone may
# not discharge share-alike if counsel later disagrees -- nothing in this
# codebase may be written as though it settles the question.
LICENSE_CLASSES = ("verbatim-ok", "paraphrase-only", "cc-by-sa-3.0")
# G4(e): an entry's OWN command needs elevated privilege to run on a STIG'd
# host that the shipped command itself never requests (sudo/su) -- distinct
# from blast, which rates what the command DOES once it runs, not what it
# takes to run it. gen-sshd-test-config (`sshd -T -f <path>`) is the first:
# sshd_config is not world-readable on a STIG'd host (content validation
# protocol run CR-T-34, Caleb Stone, both defiant and saratoga: "Permission
# denied", deferred, no capture written). Optional; absent means no elevated
# privilege is declared. A small closed set, not a free string, so a future
# author cannot invent a fourth privilege level the UI has no copy for.
PRIVILEGES = ("root",)

# ---------------------------------------------------------------------------
# TROJAN_RANGES -- the ONE table of characters that must never appear raw
# (threat model v2, M8: "one trojan range table, never a second copy").
#
# qa.py states the same table for its own gates (Q17 on the shipped artifact,
# Q21 on every tracked file) because qa.py imports nothing from extract/ on
# principle -- a gate that re-uses the extractor's code path cannot catch the
# extractor being wrong. tests/test_schema.py asserts the two statements are
# IDENTICAL, element for element, exactly as it already does for the field-type
# and rich-rule slot tables, so they cannot drift.
#
# Written as numbers, never as the characters and never as backslash-u escapes
# inside a literal, so this file stays clean for Q21's own scan.
# ---------------------------------------------------------------------------
TROJAN_RANGES = [
    (0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F), (0x7F, 0x9F),   # C0 and C1, keeping tab/LF/CR
    (0xAD, 0xAD), (0x34F, 0x34F), (0x61C, 0x61C),             # soft hyphen, CGJ, Arabic letter mark
    (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180E),
    (0x200B, 0x200F), (0x2028, 0x2029), (0x202A, 0x202E),     # zero-width, line/paragraph
                                                              #   separators, bidi overrides
    (0x2060, 0x206F),                                         # word joiner, invisible format
                                                              #   and bidi isolates, 2065 included
    (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0),
]
TROJAN_RE = re.compile("[" + "".join("%s-%s" % (chr(a), chr(b)) for a, b in TROJAN_RANGES) + "]")


def escape_trojan(text):
    """Every character of TROJAN_RANGES rewritten as the six ASCII characters
    that NAME it, so a file recording hostile source text is itself readable,
    diffable and clean under Q21 (threat model v2, M1).

    M1 is a real contradiction, not a hypothetical: ADR-002 routes
    trojan-carrying source lines into content-src/residue/, Q21 refuses raw
    control/bidi/zero-width characters in EVERY tracked file with
    TROJAN_SCAN_EXCLUDE = (), and the first bidirectional override in a vendor
    PDF would break the build. Excluding residue from Q21 would re-open
    MCR-SEC-024 by hand. Escaping on the way in resolves it without weakening
    either rule.
    """
    return TROJAN_RE.sub(lambda m: "\\u%04X" % ord(m.group()), str(text))

# ---------------------------------------------------------------------------
# Header-bound strings must be single-line (MCR-SEC-003).
#
# `intent`, `verify`, `undo` and the stig[] rows are copied into the clipboard's
# comment header, where the screen never shows them: the UI renders `intent` as
# one <h2> and HTML collapses a newline, so a two-line intent reads as one title
# on screen and pastes as two lines into a root shell. The renderer's own
# defence is that every clipboard line is '# '-prefixed; this is the second,
# independent layer, and it fails the BUILD rather than the clipboard.
#
# The rule is "no control character at all", not "no newline": a lone \r, a NUL,
# a vertical tab and U+2028/U+2029 all end a line somewhere in the stack, and a
# tab in a header line is never intentional in curated prose.
#
# CR-T-33 will populate these fields from multi-line DISA prose. That extractor
# has to flatten the text; it does not get to move the failure to the clipboard.
# ---------------------------------------------------------------------------
CONTROL_RE = re.compile(r"[\u0000-\u001F\u007F-\u009F\u2028\u2029]")  # written as escapes, never as the characters themselves
HEADER_BOUND_FIELDS = ("intent", "verify", "undo")
# Captured console output is multi-line by nature and is never header-bound; it
# is the one stig[] value the single-line rule does not apply to.
NOT_HEADER_BOUND = ("expected_output",)


def control_char_name(s):
    m = CONTROL_RE.search(s)
    if not m:
        return None
    return "U+%04X" % ord(m.group(0))


def single_line_errors(where, value):
    """Every string reachable from a header-bound value must be one clean line."""
    errs = []
    if isinstance(value, str):
        cp = control_char_name(value)
        if cp:
            errs.append("%s contains the control character %s — this string is copied into the "
                        "clipboard comment header, which the operator never sees rendered, so it "
                        "must be a single line of printable text" % (where, cp))
    elif isinstance(value, dict):
        for k, v in sorted(value.items()):
            if k in NOT_HEADER_BOUND:
                continue
            errs += single_line_errors("%s.%s" % (where, k), v)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            errs += single_line_errors("%s[%d]" % (where, i), v)
    return errs

# ADR-001 §5.1 "source" field note. A source that cannot say which version of the
# document it came from cannot be re-checked, so `version` is mandatory alongside
# the other four. (A man-page source puts the package NVRA here.)
PROVENANCE_FIELDS = ("title", "url_or_man", "version", "retrieved_on", "license_class")

# The three legal shapes of an rhel_versions[v] value, ADR-001 §5.1.
VERSION_VALUE_SHAPES = (
    "{command, notes, changed_in_note}",
    '{same_as: "<other version key>", changed_in_note?}',
    "{unavailable: {reason, alternative}}",
)


# ---------------------------------------------------------------------------
# provenance
# ---------------------------------------------------------------------------

def provenance_errors(where, src):
    """Every embedded string must be traceable to a named, versioned source."""
    if not isinstance(src, dict):
        return ["%s: missing provenance (no source object)" % where]
    errs = []
    for field in PROVENANCE_FIELDS:
        if not src.get(field):
            errs.append("%s: missing provenance field source.%s" % (where, field))
    lc = src.get("license_class")
    if lc and lc not in LICENSE_CLASSES:
        errs.append("%s: source.license_class '%s' is not one of %s"
                    % (where, lc, ", ".join(LICENSE_CLASSES)))
    return errs


# ---------------------------------------------------------------------------
# rhel_versions
# ---------------------------------------------------------------------------

def resolve_chain(entry_id, versions, key, errs):
    """Follow same_as pointers to the key that holds a concrete value.

    Returns that key, or None after appending the reason to errs. Detects cycles
    and pointers to a version key that is not one of the four.
    """
    seen = []
    cur = key
    while True:
        if cur in seen:
            errs.append("commands entry %s: same_as cycle %s"
                        % (entry_id, " -> ".join(seen + [cur])))
            return None
        seen.append(cur)
        val = versions.get(cur)
        if not isinstance(val, dict):
            errs.append("commands entry %s: rhel_versions['%s'] is not an object" % (entry_id, cur))
            return None
        if "same_as" not in val:
            return cur
        nxt = val.get("same_as")
        if nxt not in VERSIONS:
            errs.append("commands entry %s: rhel_versions['%s'].same_as '%s' is not one of %s"
                        % (entry_id, cur, nxt, ", ".join(VERSIONS)))
            return None
        cur = nxt


def rhel_versions_errors(eid, versions):
    """All four keys, always, each holding exactly one of the three legal shapes.

    'Not available' is a value, not an absence (ADR-001 §5.2 point 3): a missing
    key is the silent-omission failure the four-version P0 decision is exposed to,
    so it is an error and not a warning.
    """
    errs = []
    if not isinstance(versions, dict):
        return ["commands entry %s: rhel_versions missing" % eid]
    missing = [v for v in VERSIONS if v not in versions]
    extra = [k for k in versions if k not in VERSIONS]
    if missing:
        errs.append("commands entry %s: rhel_versions missing RHEL key(s) %s — "
                    "all four of 7/8/9/10 are mandatory, 'not available' is a value not an absence"
                    % (eid, ", ".join(missing)))
    if extra:
        errs.append("commands entry %s: rhel_versions has unknown key(s) %s" % (eid, ", ".join(extra)))
    for v in VERSIONS:
        val = versions.get(v)
        if val is None:
            continue
        if not isinstance(val, dict):
            errs.append("commands entry %s: rhel_versions['%s'] is not an object" % (eid, v))
            continue
        if "same_as" in val:
            resolve_chain(eid, versions, v, errs)
        elif "unavailable" in val:
            u = val.get("unavailable") or {}
            if not isinstance(u, dict) or not (u.get("reason") or "").strip():
                errs.append("commands entry %s: rhel_versions['%s'].unavailable has an empty reason — "
                            "the UI renders the reason, so there must be one" % (eid, v))
        elif "command" in val:
            if not (val.get("command") or "").strip():
                errs.append("commands entry %s: rhel_versions['%s'].command is empty" % (eid, v))
            cin = val.get("changed_in_note")
            if isinstance(cin, dict) and cin:
                for field in ("version", "what", "source_ref"):
                    if not cin.get(field):
                        errs.append("commands entry %s: rhel_versions['%s'].changed_in_note missing %s"
                                    % (eid, v, field))
        else:
            errs.append("commands entry %s: rhel_versions['%s'] is none of %s"
                        % (eid, v, " / ".join(VERSION_VALUE_SHAPES)))
    return errs


def resolved_command(entry, version):
    """The entry's own rhel_versions[version].command, resolving a same_as
    CHAIN of any length (cycle-guarded) via resolve_chain() above -- the same
    resolution build.py's assemble() performs before a same_as pointer ships.

    Single source of truth for "what command does this version actually run"
    (Riley Park's RILEY-F5: extract/import_captures.py's own resolver used to
    stop after one same_as hop, so a two-hop chain like RHEL 10 -> 9 -> 8
    silently skipped the "edit resets verified" integrity check for the far
    end of the chain). extract/import_captures.py and qa.py's Q16 gate both
    call this instead of re-walking rhel_versions by hand, so the chain is
    resolved the same way everywhere or not at all.

    None for a generator entry (MCR-SEC-006: composed at render time from
    validated form input, so there is no fixed command to diff against), a
    version not in VERSIONS, or a chain resolve_chain() cannot resolve (a
    cycle or a dangling same_as -- rhel_versions_errors() is the build-time
    authority on those; this function does not guess).
    """
    if not isinstance(entry, dict) or "template" in entry or version not in VERSIONS:
        return None
    versions = entry.get("rhel_versions")
    if not isinstance(versions, dict):
        return None
    errs = []
    target = resolve_chain(entry.get("id") or "?", versions, version, errs)
    if target is None or errs:
        return None
    slot = versions.get(target)
    if not isinstance(slot, dict):
        return None
    return slot.get("command")


# ---------------------------------------------------------------------------
# generator / spec shape (MCR-SEC-006)
#
# Before this section, extract/schema.py knew nothing about `fields`, `template`
# or `richRule`: it validated the curated commands.json entry form only. So the
# assembler's contract — the one CR-T-25 (Ansible generator) and CR-T-33
# (catalog authoring) will write fourteen P0 tool categories of templates
# against — had no build-time check at all, and `template[].flag` /
# `template[].lit` reached the shell raw and unquoted with nothing but the
# author's care between them and a command line.
#
# These rules MIRROR the runtime rules in template.html's assembler block. The
# runtime returns null; the build refuses to ship. tests/test_schema.py asserts
# the two statements of the field-type list and the rich-rule slot table agree,
# so they cannot drift apart silently.
# ---------------------------------------------------------------------------
FIELD_TYPE_NAMES = ("hostname", "ipv4", "ipv6", "ipaddr", "cidr", "port", "portrange",
                    "protocol", "family", "action", "unit", "username", "groupname",
                    "path", "zone", "service", "package", "selinux_boolean", "audit_key",
                    "interface", "integer", "lvm_size", "group_list", "git_refname",
                    "git_revision", "enum", "comment")

# Closed-grammar types only. `comment` and `enum` are deliberately absent from
# every slot: rich-rule attribute syntax has no escape for a double quote inside
# an attribute value, so free text cannot be made safe there (MCR-SEC-001).
RICHRULE_SLOT_TYPES = {
    "family": ("family",),
    "source": ("cidr", "ipaddr", "ipv4", "ipv6"),
    "destination": ("cidr", "ipaddr", "ipv4", "ipv6"),
    "service": ("service",),
    "port": ("port", "portrange"),
    "protocol": ("protocol",),
    "action": ("action",),
}

FLAG_TOKEN_RE = re.compile(r"^-{1,2}[A-Za-z0-9][A-Za-z0-9-]*$")
LIT_TOKEN_RE = re.compile(r"^[A-Za-z0-9_./=:,+-]+$")
FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def spec_fields_errors(where, fields, names):
    errs = []
    for i, f in enumerate(fields):
        if not isinstance(f, dict):
            errs.append("%s: fields[%d] is not an object" % (where, i))
            continue
        name = f.get("name")
        if not isinstance(name, str) or not FIELD_NAME_RE.match(name):
            errs.append("%s: fields[%d] has no usable name (%r)" % (where, i, name))
            continue
        if name in names:
            errs.append("%s: two fields are both named '%s'" % (where, name))
        names.add(name)
        if f.get("type") not in FIELD_TYPE_NAMES:
            errs.append("%s: field '%s' has type %r, which is not one of the %d types the "
                        "assembler validates" % (where, name, f.get("type"), len(FIELD_TYPE_NAMES)))
        vs = f.get("versions")
        if vs is not None:
            if not isinstance(vs, list) or not vs or any(v not in VERSIONS for v in vs):
                errs.append("%s: field '%s' versions %r is not a non-empty subset of %s"
                            % (where, name, vs, ", ".join(VERSIONS)))
        if f.get("type") == "enum":
            opts = f.get("options")
            if not isinstance(opts, list) or not opts:
                errs.append("%s: field '%s' is an enum with no options — an enum with no closed set "
                            "is free text wearing a <select>" % (where, name))
        control = f.get("control")
        if control is not None:
            if control != "checkbox":
                errs.append("%s: field '%s' control %r is not 'checkbox'" % (where, name, control))
            if f.get("type") != "enum" or f.get("options") != ["yes"] or f.get("required"):
                errs.append("%s: checkbox field '%s' must be an optional enum whose sole option "
                            "is 'yes' — unchecked means the field is absent" % (where, name))
    return errs


def token_gate(tok):
    """The field a token's presence depends on, or None if it always appears.

    A field token depends on its own field. A `{lit, requires}` token depends on
    the field `requires` names — that is what makes a literal conditional, and
    therefore what makes it able to vanish (MCR-SEC-013).
    """
    if not isinstance(tok, dict):
        return None
    if tok.get("field") is not None:
        return tok["field"]
    if tok.get("lit") is not None and tok.get("requires") is not None:
        return tok["requires"]
    return None


def positional_indexes(template):
    """Token indexes that occupy an ARGUMENT slot, mirroring isPositionalToken().

    A flag token carries its own name and is position-independent. An
    UNCONDITIONAL lit can never vanish, so it can never shift anything. What is
    left is field tokens and conditional literals — the tokens whose absence
    promotes argument n+1 into slot n (MCR-SEC-002, MCR-SEC-013).
    """
    out = []
    for i, t in enumerate(template):
        if not isinstance(t, dict) or t.get("flag"):
            continue
        if t.get("field") is not None:
            out.append(i)
            continue
        lit = t.get("lit")
        if lit is None or t.get("requires") is None:
            continue
        # MCR-SEC-018 / MCR-SEC-022, conditions E3 and E7. The discriminator is
        # DERIVED from the word the token emits, not declared beside it: a lit
        # matching FLAG_TOKEN_RE is an OPTION and never occupies an argument
        # slot, so `setsebool -P` and `lvextend -r` may be conditional with a
        # positional token after them and nothing shifts when they drop.
        # `0644` and `/etc/shadow` do not match and stay refused by
        # construction — there is no key to disagree with the literal.
        if isinstance(lit, str) and FLAG_TOKEN_RE.match(lit):
            continue
        out.append(i)
    return out


def shift_unsafe_after(template, positional, i):
    """Positional tokens after index i that do NOT vanish when token i does.

    Empty means the drop is safe: either nothing positional follows, or
    everything that follows is gated on the same field, so it leaves with it.
    The second case is the shape MCR-SEC-002 shipped — `{lit:"…toaddr=",
    requires:"toaddr"}` followed by `{field:"toaddr", optional:true}` — and a
    rule that refused it would refuse the fix for the finding before this one.
    """
    gate = token_gate(template[i])
    return [j for j in positional if j > i and token_gate(template[j]) != gate]


def flag_join_errors(at, tok, flag):
    """MCR-SEC-015 (condition E1) — the build-time half of the derived join rule.

    template.html's flagJoin() derives how a flag is joined to its value from the
    flag's own shape: `--long` takes '=', `-X` takes ' '. Deriving it is what
    fixed twenty wrong tokens at once and what keeps the twenty-first from being
    written. These errors close the other half: a token that DECLARES a join for
    a shape that derives it is a disagreement between the content and the rule,
    and the assembler returns null rather than pick a winner. The build says so
    by name instead of leaving the author with a blank Copy button.

    Two escape hatches survive, each legal only on the shape it belongs to:
      eq:false      on --long, for a long option that wants a space
      join:"glued"  on -X, for a tool that requires -Xvalue
    """
    errs = []
    long_opt = flag.startswith("--")
    if long_opt:
        if "join" in tok:
            errs.append("%s is a LONG option (%s) carrying `join`: a long option joins with '=', "
                        "and `join` is the short-option escape hatch (join:\"glued\" for -Xvalue). "
                        "Use eq:false if this option really wants a space (MCR-SEC-015)"
                        % (at, flag))
        if "eq" in tok and not isinstance(tok["eq"], bool):
            errs.append("%s has eq %r, which is not true or false" % (at, tok["eq"]))
    else:
        if "eq" in tok:
            errs.append("%s is a SHORT option (%s) carrying `eq`: a single-dash option NEVER joins "
                        "its value with '=' — getopt(3) passes the '=' through as the first "
                        "character of the argument, so `chage -M=60` sets max-days to \"=60\" and "
                        "`auditctl -w=/etc/motd` watches nothing. The join is DERIVED from the "
                        "flag's shape; delete the key (MCR-SEC-015)" % (at, flag))
        if "join" in tok and tok["join"] != "glued":
            errs.append("%s has join %r; the only declared join is \"glued\", which emits "
                        "-Xvalue for a tool that requires it (MCR-SEC-015)" % (at, tok["join"]))
    return errs


def spec_template_errors(where, template, fields_by_name):
    errs = []
    positional = positional_indexes(template)
    last_positional = positional[-1] if positional else None

    for i, tok in enumerate(template):
        at = "%s: template[%d]" % (where, i)
        if not isinstance(tok, dict):
            errs.append("%s is not an object" % at)
            continue
        shapes = [k for k in ("lit", "field", "richRule") if tok.get(k) is not None]
        if len(shapes) != 1:
            errs.append("%s must be exactly one of {lit}, {field} or {richRule}, not %s"
                        % (at, shapes or "none of them"))
            continue
        if tok.get("flag") is None and ("eq" in tok or "join" in tok):
            errs.append("%s declares a flag join (%s) but has no `flag` to join — a key that "
                        "applies to nothing is a key the next author will trust (MCR-SEC-015)"
                        % (at, " and ".join(k for k in ("eq", "join") if k in tok)))
        if tok.get("flag") is not None:
            flag = tok["flag"]
            if not isinstance(flag, str) or not FLAG_TOKEN_RE.match(flag):
                errs.append("%s flag %r is not an option token — it reaches the command line "
                            "unquoted, so it must match %s (no whitespace, no quote, no shell "
                            "metacharacter)" % (at, flag, FLAG_TOKEN_RE.pattern))
            else:
                errs += flag_join_errors(at, tok, flag)
        if "lit" in shapes:
            lit = tok["lit"]
            if not isinstance(lit, str) or not LIT_TOKEN_RE.match(lit):
                errs.append("%s lit %r reaches the command line unquoted and must match %s"
                            % (at, lit, LIT_TOKEN_RE.pattern))
            if tok.get("flag") is not None:
                # MCR-SEC-022, condition E7. A lit token emits its `lit`; a
                # `flag` beside it emits nothing and only told positional_indexes()
                # to look away — unchecked, for whatever literal it was attached
                # to, which is how {lit:"0644", flag:"-P"} reopened MCR-SEC-013.
                # Refused even when flag == lit: the branch shipped two exemplars
                # of the shape, and an author who hits the D1 build error should
                # not have a documented-looking lever to pull. Whether a literal
                # is an option is derived from the literal itself, so a real
                # option needs no key at all.
                errs.append("%s carries both `lit` and `flag`. The word this token emits is its "
                            "`lit` (%r); `flag` emits nothing here and only switched the positional "
                            "rule off for it. An option-shaped literal is recognised as an option "
                            "by matching %s — delete the `flag` key (MCR-SEC-022)"
                            % (at, lit, FLAG_TOKEN_RE.pattern))
            req = tok.get("requires")
            if req is not None and req not in fields_by_name:
                errs.append("%s requires field '%s', which this spec does not declare" % (at, req))
            if req is not None and i in positional and shift_unsafe_after(template, positional, i):
                errs.append("%s is a conditional POSITIONAL literal: it drops when field '%s' is "
                            "absent, and a positional token after it does not drop with it. "
                            "Argument n+1 would be promoted into slot n — `chmod '/etc/foo'` with "
                            "the path in the mode slot — so the assembler returns null at run time "
                            "and this literal can never be conditional here. Put it last among the "
                            "positional tokens, or gate the tokens after it on the same field "
                            "(MCR-SEC-013)" % (at, req))
        elif "field" in shapes:
            name = tok["field"]
            f = fields_by_name.get(name)
            if f is None:
                errs.append("%s cites field '%s', which this spec does not declare" % (at, name))
                continue
            droppable = (not f.get("required")) or bool(f.get("versions"))
            if droppable and tok.get("optional") is not True:
                errs.append("%s uses field '%s', which can be absent (optional or version-gated), "
                            "without declaring optional:true. Token dropping is a property of the "
                            "TEMPLATE: undeclared, the assembler returns null rather than shifting "
                            "the command (MCR-SEC-002)" % (at, name))
            if (tok.get("optional") is True and not tok.get("flag")
                    and i != last_positional and shift_unsafe_after(template, positional, i)):
                errs.append("%s is a droppable POSITIONAL token with another positional token after "
                            "it. Dropping it would promote argument n+1 into slot n, so the "
                            "assembler refuses it at run time and this template can never omit the "
                            "value it says is optional (MCR-SEC-002)" % at)
        else:
            plan = tok["richRule"]
            if not isinstance(plan, dict) or not plan:
                errs.append("%s richRule is not a slot map" % at)
                continue
            for slot, fname in sorted(plan.items()):
                if slot not in RICHRULE_SLOT_TYPES:
                    errs.append("%s richRule names slot '%s', which is not a rich-rule element "
                                "this assembler composes" % (at, slot))
                    continue
                f = fields_by_name.get(fname)
                if f is None:
                    errs.append("%s richRule slot '%s' cites field '%s', which this spec does not "
                                "declare" % (at, slot, fname))
                    continue
                if f.get("type") not in RICHRULE_SLOT_TYPES[slot]:
                    errs.append("%s richRule slot '%s' is filled by field '%s' of type '%s'. That "
                                "slot takes %s only: rich-rule syntax has no escape for a quote "
                                "inside an attribute value, so no free-text type may reach it "
                                "(MCR-SEC-001)"
                                % (at, slot, fname, f.get("type"),
                                   " / ".join(RICHRULE_SLOT_TYPES[slot])))
            if "family" not in plan or "action" not in plan:
                errs.append("%s richRule has no %s slot — a rich rule with no family or no action "
                            "is half-formed and the assembler returns null"
                            % (at, "family" if "family" not in plan else "action"))
    return errs


# ---------------------------------------------------------------------------
# generated-file spec (MCR-SEC-010, CR-T-25)
#
# A generator may declare a `doc` alongside its `template`: the FILE its command
# runs against. These rules MIRROR composeDoc() in template.html's assembler
# block, exactly as spec_template_errors() mirrors assembleCommand(). The runtime
# returns null; the build refuses to ship.
#
# The INI half carries no quoter, here or there, and that is deliberate: an INI
# file has no escape sequence for a value containing its own delimiters, so the
# honest answer is a closed type allow-list and a closed character set rather
# than a fourth escaper nobody can write correctly (MCR-SEC-001's ruling,
# applied to a second grammar).
# ---------------------------------------------------------------------------
DOC_KINDS = ("yaml", "ini")
DOC_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
DOC_LIT_RE = re.compile(r"^[A-Za-z0-9_./:@+-]+$")
DOC_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
INI_FIELD_TYPES = ("path", "username", "groupname", "integer", "port", "hostname",
                   "interface", "package", "unit", "ipv4", "ipv6", "ipaddr")
DOC_MAX_INDENT = 8
DOC_LINE_SHAPES = ("field", "lit", "bool")


def _doc_line_gate(line):
    for key in ("requires", "field", "keyField"):
        if line.get(key) is not None:
            return line[key]
    return None


def doc_errors(where, doc, fields_by_name):
    errs = []
    if not isinstance(doc, dict):
        return ["%s: doc is not an object" % where]
    kind = doc.get("kind")
    if kind not in DOC_KINDS:
        errs.append("%s: doc.kind %r is not one of %s" % (where, kind, ", ".join(DOC_KINDS)))
    name = doc.get("filename")
    if not isinstance(name, str) or not DOC_FILENAME_RE.match(name):
        errs.append("%s: doc.filename %r is not a plain file name -- it is shown on the Copy "
                    "button and in the file preview, so it is a closed token, not free text"
                    % (where, name))
    lines = doc.get("lines")
    if not isinstance(lines, list) or not lines:
        return errs + ["%s: doc.lines must be a non-empty list" % where]

    yaml = (kind == "yaml")
    for i, line in enumerate(lines):
        at = "%s: doc.lines[%d]" % (where, i)
        if not isinstance(line, dict):
            errs.append("%s is not an object" % at)
            continue
        if line.get("section") is not None:
            if yaml:
                errs.append("%s carries an INI `section` in a yaml document" % at)
            elif not DOC_KEY_RE.match(str(line["section"])):
                errs.append("%s section %r is emitted unquoted and must match %s"
                            % (at, line["section"], DOC_KEY_RE.pattern))
            continue
        indent = line.get("indent")
        if yaml:
            if not isinstance(indent, int) or isinstance(indent, bool) \
                    or indent < 0 or indent > DOC_MAX_INDENT:
                errs.append("%s indent %r is not an integer in 0..%d" % (at, indent, DOC_MAX_INDENT))
        elif indent not in (None, 0):
            errs.append("%s declares indent %r, and an INI file has no nesting" % (at, indent))

        has_keyfield = line.get("keyField") is not None
        if has_keyfield:
            if not yaml:
                errs.append("%s uses a keyField: an INI key is never operator text" % at)
            elif line.get("keyField") not in fields_by_name:
                errs.append("%s keyField cites field '%s', which this spec does not declare"
                            % (at, line.get("keyField")))
        elif line.get("key") is None or not DOC_KEY_RE.match(str(line.get("key"))):
            errs.append("%s has no usable key (%r) -- a key is emitted unquoted and must match %s"
                        % (at, line.get("key"), DOC_KEY_RE.pattern))

        shapes = [k for k in DOC_LINE_SHAPES if line.get(k) is not None]
        if len(shapes) > 1:
            errs.append("%s carries %s: a line emits exactly one value, or none"
                        % (at, " and ".join(shapes)))
        if not shapes and not yaml:
            errs.append("%s has a key and no value; a bare INI key is not a thing" % at)
        if line.get("lit") is not None and not DOC_LIT_RE.match(str(line["lit"])):
            errs.append("%s lit %r must match %s" % (at, line["lit"], DOC_LIT_RE.pattern))
        if line.get("bool") is not None and line["bool"] not in (True, False):
            errs.append("%s bool %r is not true or false" % (at, line["bool"]))
        fname = line.get("field")
        if fname is not None:
            f = fields_by_name.get(fname)
            if f is None:
                errs.append("%s cites field '%s', which this spec does not declare" % (at, fname))
            elif not yaml and f.get("type") not in INI_FIELD_TYPES:
                errs.append("%s fills an INI value from field '%s' of type '%s'. An INI entry has "
                            "no escape sequence for a value carrying a newline, a ';', a '#' or an "
                            "'=', so only a closed grammar may reach one: %s. `comment` and `enum` "
                            "are deliberately absent, for the same reason they are absent from "
                            "every rich-rule slot (MCR-SEC-001)"
                            % (at, fname, f.get("type"), ", ".join(INI_FIELD_TYPES)))
        req = line.get("requires")
        if req is not None and req not in fields_by_name:
            errs.append("%s requires field '%s', which this spec does not declare" % (at, req))

        # droppability, and the block rule
        gated_names = [n for n in (line.get("field"), line.get("keyField"), req) if n]
        droppable = False
        for n in gated_names:
            f = fields_by_name.get(n)
            if f is None:
                continue
            if (not f.get("required")) or bool(f.get("versions")):
                droppable = True
        if droppable and line.get("optional") is not True:
            errs.append("%s can be absent (its field is optional or version-gated) without "
                        "declaring optional:true. Dropping a line is a property of the DOCUMENT: "
                        "undeclared, composeDoc() returns null rather than emit a file with a hole "
                        "in it" % at)
        if line.get("optional") is True and yaml:
            gate = _doc_line_gate(line)
            own = line.get("indent") or 0
            for j in range(i + 1, len(lines)):
                nxt = lines[j]
                if not isinstance(nxt, dict):
                    break
                if (nxt.get("indent") or 0) <= own:
                    break
                if _doc_line_gate(nxt) != gate:
                    errs.append("%s is a droppable BLOCK HEADER and doc.lines[%d] is indented "
                                "under it on a different gate. Dropping this line would leave that "
                                "one orphaned under the wrong parent -- a structural rewrite of the "
                                "document, exactly as an argument promoted into the wrong slot is "
                                "of a command line. Gate them on the same field so they leave "
                                "together" % (at, j))
                    break
    return errs


def spec_errors(where, spec):
    """A generator spec: fields[] the form renders and template[] the assembler walks."""
    errs = []
    fields = spec.get("fields")
    template = spec.get("template")
    if not isinstance(fields, list):
        return ["%s: fields must be a list (a spec with no fields renders no form)" % where]
    if not isinstance(template, list) or not template:
        return ["%s: template must be a non-empty list" % where]

    names = set()
    errs += spec_fields_errors(where, fields, names)
    fields_by_name = {f.get("name"): f for f in fields if isinstance(f, dict)}
    errs += spec_template_errors(where, template, fields_by_name)
    if "doc" in spec:
        errs += doc_errors(where, spec.get("doc"), fields_by_name)

    used = set()
    for tok in template:
        if not isinstance(tok, dict):
            continue
        if tok.get("field"):
            used.add(tok["field"])
        if isinstance(tok.get("richRule"), dict):
            used.update(v for v in tok["richRule"].values() if isinstance(v, str))
        if tok.get("requires"):
            used.add(tok["requires"])
    # A `doc` line is as real a consumer of a field as a template token is: an
    # Ansible inventory generator's group and host names reach the FILE, not the
    # command line, and the "declared but never used" rule has to see that or it
    # refuses the generator for asking a question it does answer.
    for line in ((spec.get("doc") or {}).get("lines") or []):
        if not isinstance(line, dict):
            continue
        for key in ("field", "keyField", "requires"):
            if line.get(key):
                used.add(line[key])
    for name in sorted(names - used):
        errs.append("%s: field '%s' is declared but no template token uses it — the form would ask "
                    "for a value that never reaches the command" % (where, name))

    vs = spec.get("versions")
    if vs is not None and (not isinstance(vs, list) or not vs or any(v not in VERSIONS for v in vs)):
        errs.append("%s: versions %r is not a non-empty subset of %s" % (where, vs, ", ".join(VERSIONS)))
    return errs


# ---------------------------------------------------------------------------
# one command entry
# ---------------------------------------------------------------------------

def entry_errors(e, ctx):
    """ADR-001 §5.1. ctx carries the cross-file facts this entry is checked against."""
    errs = []
    eid = e.get("id") or "?"
    for field in ("id", "tool", "category", "intent", "verify", "undo", "blast", "source"):
        if not e.get(field):
            errs.append("commands entry %s: missing %s" % (eid, field))
    if e.get("blast") not in BLASTS:
        errs.append("commands entry %s: blast '%s' is not one of %s"
                    % (eid, e.get("blast"), ", ".join(BLASTS)))
    if e.get("category") and e["category"] not in ctx["categories"]:
        errs.append("commands entry %s: category '%s' not in commands.json categories" % (eid, e["category"]))
    if e.get("tool") and e["tool"] not in ctx["tool_ids"]:
        errs.append("commands entry %s: tool '%s' does not exist in tools.json" % (eid, e["tool"]))
    # explain_tool (Marcus Reed Panels review PANEL-001 / condition G1): optional
    # override telling the inspector's flag dictionary lookup which BINARY the
    # rhel_versions commands actually invoke, when that differs from `tool` (the
    # subject `tool` stays what the sidebar rail groups by). Same existence rule
    # as `tool` — it names a real tool, never a guess.
    if "explain_tool" in e and e["explain_tool"] not in ctx["tool_ids"]:
        errs.append("commands entry %s: explain_tool '%s' does not exist in tools.json"
                    % (eid, e.get("explain_tool")))
    if "privilege" in e and e["privilege"] not in PRIVILEGES:
        errs.append("commands entry %s: privilege '%s' is not one of %s"
                    % (eid, e.get("privilege"), ", ".join(PRIVILEGES)))
    # MCR-SEC-003: everything that reaches the clipboard comment header is
    # checked here, at build time, as well as being '# '-prefixed at render time.
    for field in HEADER_BOUND_FIELDS:
        if isinstance(e.get(field), str):
            errs += single_line_errors("commands entry %s: %s" % (eid, field), e[field])
    for i, s in enumerate(e.get("stig") or []):
        errs += single_line_errors("commands entry %s: stig[%d]" % (eid, i), s)
    errs += provenance_errors("commands entry %s" % eid, e.get("source"))
    if "template" in e:
        # A generator spec: the form-and-template shape the assembler walks. Its
        # commands are composed per release from validated field values, so it
        # carries no rhel_versions block and no curated flags[] (MCR-SEC-006).
        errs += spec_errors("commands entry %s" % eid, e)
    else:
        errs += rhel_versions_errors(eid, e.get("rhel_versions"))
        errs += flags_errors(eid, e.get("flags"),
                             dict(ctx, entry_verified=entry_has_any_receipt(e.get("verified"))))
    errs += stig_errors(eid, e.get("stig"), ctx)
    errs += verified_errors(eid, e.get("verified"), e)
    return errs


def flags_errors(eid, flags, ctx):
    """Every flag names itself and carries an explain key — null until the entry is verified.

    ADR-001 §5.1: `explain` is *curated*, never generated at render time, and a
    flag with no curated explain is emitted as null so the UI can say "unverified —
    see man page". Reading a RHEL host (CR-T-09..12) yields flag *names* and
    package versions, not explanations; those are authored later with a citation
    (man pages are paraphrase-only). So null stays honest until the entry is marked
    `verified: true`; a verified entry with a null explain skipped the curation step,
    and that is a schema error. Integrator ruling, Eli Cross, 2026-09-17 (replaces the
    CR-T-06 "null only while dictionaries are empty" rule, which conflated extraction
    with curation and turned red the moment CR-T-10 landed real flags).
    """
    errs = []
    if flags is None:
        return errs
    if not isinstance(flags, list):
        return ["commands entry %s: flags must be a list" % eid]
    for i, fl in enumerate(flags):
        if not isinstance(fl, dict):
            errs.append("commands entry %s: flags[%d] is not an object" % (eid, i))
            continue
        name = fl.get("flag")
        if not (name or "").strip():
            errs.append("commands entry %s: flags[%d] has no flag token (the flag's own name)" % (eid, i))
            name = "?"
        if "explain" not in fl:
            errs.append("commands entry %s: flag '%s' has no explain key — a flag with no curated "
                        "explanation is emitted as explain:null, never omitted" % (eid, name))
        elif fl.get("explain") is None and ctx.get("entry_verified"):
            errs.append("commands entry %s: flag '%s' has explain:null but the entry is verified:true — "
                        "a verified entry must carry a curated, cited explanation for every flag"
                        % (eid, name))
        lc = fl.get("license_class")
        if lc and lc not in LICENSE_CLASSES:
            errs.append("commands entry %s: flag '%s' license_class '%s' is not one of %s"
                        % (eid, name, lc, ", ".join(LICENSE_CLASSES)))
        ref = fl.get("source_ref")
        if ref:
            if not ctx["have_sources_json"]:
                errs.append("commands entry %s: flag '%s' cites source_ref '%s' but "
                            "content-src/SOURCES.json does not exist yet" % (eid, name, ref))
            elif ref not in ctx["source_ids"]:
                errs.append("commands entry %s: flag '%s' source_ref '%s' does not resolve in "
                            "content-src/SOURCES.json" % (eid, name, ref))
    return errs


def stig_errors(eid, stig, ctx):
    """Every stig[] row resolves to a real rule in that release's RULES dataset."""
    errs = []
    if stig is None:
        return errs
    if not isinstance(stig, list):
        return ["commands entry %s: stig must be a list" % eid]
    for s in stig:
        if not isinstance(s, dict):
            errs.append("commands entry %s: a stig[] item is not an object" % eid)
            continue
        sid = s.get("stig_id")
        v = s.get("rhel_version")
        if not sid:
            errs.append("commands entry %s: a stig[] item has no stig_id" % eid)
            continue
        if v not in VERSIONS:
            errs.append("commands entry %s: stig %s has rhel_version '%s', not one of %s"
                        % (eid, sid, v, ", ".join(VERSIONS)))
            continue
        rec = ctx["rule_index"].get(v, {}).get(sid)
        if rec is None:
            errs.append("commands entry %s: stig_id %s does not resolve to a record in rules_rhel%s.json"
                        % (eid, sid, v))
            continue
        if s.get("rule_id") != rec.get("rid"):
            errs.append("commands entry %s: stig %s rule_id '%s' != rules_rhel%s record rid '%s'"
                        % (eid, sid, s.get("rule_id"), v, rec.get("rid")))
        if s.get("cci") and list(s["cci"]) != list(rec.get("cci") or []):
            errs.append("commands entry %s: stig %s cci %s != source-parsed %s"
                        % (eid, sid, s.get("cci"), rec.get("cci")))
        if s.get("nist") and list(s["nist"]) != list(rec.get("n") or []):
            errs.append("commands entry %s: stig %s nist %s != CCI-map-derived %s"
                        % (eid, sid, s.get("nist"), rec.get("n")))
        if s.get("expected_output"):
            key = "%s|%s|%s" % (eid, sid, v)
            if key not in ctx["captures"]:
                errs.append("commands entry %s: stig %s carries expected_output with no capture record "
                            "'%s' in content/expected_output.json — expected output is captured, never typed"
                            % (eid, sid, key))
    return errs


VERIFIED_RECEIPT_FIELDS = ("by", "on", "host", "capture")


def entry_has_any_receipt(ver):
    """True if ANY RHEL version of this entry's per-version `verified` object
    carries a real receipt (a dict), never a bare truthiness check on the
    object itself.

    `verified` used to be a single whole-entry value, where `bool(e.get(
    "verified"))` was a fine proxy for "has this been claimed verified". CEO
    ruling (capture-review-run1-2026-09-18.md RILEY-F1) made it per-version:
    {"7": false, "8": false, "9": false, "10": false} is a non-empty dict and
    therefore truthy, but it asserts nothing about any version. Only a real
    receipt on at least one version means the entry has been claimed verified
    at all -- which is what flags_errors()'s "a verified entry must curate
    every flag" rule is actually about.
    """
    if not isinstance(ver, dict):
        return False
    return any(isinstance(v, dict) for v in ver.values())


def _unreceiptable_versions(entry):
    """Versions of THIS entry a receipt can never attach to, with why.

    A `same_as` row's own text is borrowed from its resolved target and an
    `unavailable` row has no command at all -- neither one was independently
    run on a real host of that stated version, so neither can carry its own
    {by, on, host, capture} receipt (CEO ruling, per verified_errors()'s
    docstring). A generator spec (MCR-SEC-006, no rhel_versions block) draws
    the same line from its own `versions` restriction: a version the spec
    excludes was never offered to a form and so was never run either.
    """
    out = {}
    if not isinstance(entry, dict):
        return out
    if "template" in entry:
        vs = entry.get("versions")
        if isinstance(vs, list) and vs:
            for v in VERSIONS:
                if v not in vs:
                    out[v] = "not applicable to this generator (versions: %s)" % ", ".join(vs)
        return out
    versions = entry.get("rhel_versions")
    if not isinstance(versions, dict):
        return out
    for v in VERSIONS:
        val = versions.get(v)
        if not isinstance(val, dict):
            continue
        if "unavailable" in val:
            out[v] = "unavailable"
        elif "same_as" in val:
            out[v] = "a same_as pointer"
    return out


def verified_errors(eid, ver, entry=None):
    """`verified` is an object keyed by RHEL version, each value false or a
    {by, on, host, capture} receipt -- never a single whole-entry claim.

    CEO ruling (capture-review-run1-2026-09-18.md RILEY-F1, closing Riley
    Park's first capture review): the old single boolean/receipt overclaimed
    every RHEL version a batch never captured, because a real capture batch
    is per-version and the entry-level field was not. `verified` is now
    keyed "7"/"8"/"9"/"10" like `rhel_versions` itself -- false is a value,
    not an absence, so all four keys are mandatory.

    A version whose rhel_versions row is `unavailable`, or is a `same_as`
    pointer (or, for a generator spec, a version its own `versions` list
    excludes) was never independently run on a real host of that stated
    version, so it can never carry a receipt of its own -- and a same_as
    TARGET's receipt never propagates onto the version that points at it.
    The UI says "not host-verified" for that version rather than silently
    reusing the target's evidence (see template.html's verification-status
    helpers).
    """
    if ver in (False, None):
        return []
    if ver is True:
        return ["commands entry %s: verified is the old boolean 'true' -- verified is now an "
                "object keyed by RHEL version (7/8/9/10), each value false or a "
                "{by, on, host, capture} receipt (CEO ruling: per-version, not per-entry)" % eid]
    if not isinstance(ver, dict):
        return ["commands entry %s: verified must be false or an object keyed by RHEL version "
                "(7/8/9/10)" % eid]
    errs = []
    missing = [v for v in VERSIONS if v not in ver]
    extra = [k for k in ver if k not in VERSIONS]
    if missing:
        errs.append("commands entry %s: verified is missing RHEL key(s) %s -- all four of "
                    "7/8/9/10 are mandatory, false is a value not an absence"
                    % (eid, ", ".join(missing)))
    if extra:
        errs.append("commands entry %s: verified has unknown key(s) %s" % (eid, ", ".join(extra)))

    unreceiptable = _unreceiptable_versions(entry)
    for v in VERSIONS:
        if v not in ver:
            continue
        rv = ver[v]
        if rv is False or rv is None:
            continue
        if rv is True:
            errs.append("commands entry %s: verified['%s'] is true with no receipt -- it must be "
                        "false or {by, on, host, capture}" % (eid, v))
            continue
        if not isinstance(rv, dict):
            errs.append("commands entry %s: verified['%s'] must be false or "
                        "{by, on, host, capture}" % (eid, v))
            continue
        if v in unreceiptable:
            errs.append("commands entry %s: verified['%s'] carries a receipt, but RHEL %s is %s "
                        "on this entry -- that version was never independently captured and "
                        "cannot carry its own receipt (a same_as target's receipt does not "
                        "propagate)" % (eid, v, v, unreceiptable[v]))
            continue
        for field in VERIFIED_RECEIPT_FIELDS:
            if not rv.get(field):
                errs.append("commands entry %s: verified['%s'] is set but has no '%s'" % (eid, v, field))
    return errs


# ---------------------------------------------------------------------------
# generated datasets
# ---------------------------------------------------------------------------

def rules_dataset_errors(v, ds):
    errs = []
    meta = (ds or {}).get("_meta") or {}
    rules = (ds or {}).get("rules")
    errs += provenance_errors("rules_rhel%s _meta" % v, meta.get("source"))
    if not meta.get("generator"):
        errs.append("rules_rhel%s: _meta.generator missing (a generated file declares its extractor)" % v)
    if not isinstance(rules, list):
        return errs + ["rules_rhel%s: rules is not a list" % v]
    if meta.get("rule_count") != len(rules):
        errs.append("rules_rhel%s: _meta.rule_count %s != %d embedded rules"
                    % (v, meta.get("rule_count"), len(rules)))
    if meta.get("partial") and not (meta.get("partial_reason") or "").strip():
        errs.append("rules_rhel%s: _meta.partial is set with no partial_reason" % v)
    for r in rules:
        rid = r.get("v") or r.get("i") or "?"
        for field, label in (("i", "STIG ID"), ("rid", "XCCDF rule id"), ("t", "title")):
            if not r.get(field):
                errs.append("rules_rhel%s: rule %s has no %s" % (v, rid, label))
        if r.get("c") not in ("I", "II", "III"):
            errs.append("rules_rhel%s: rule %s has CAT '%s', not I/II/III" % (v, rid, r.get("c")))
    return errs


def flags_dataset_errors(v, ds):
    """An empty dictionary embeds nothing to cite — but it must say why, in words."""
    errs = []
    meta = (ds or {}).get("_meta") or {}
    if (ds or {}).get("clis"):
        errs += provenance_errors("flags_rhel%s _meta" % v, meta.get("source"))
    elif not (meta.get("status") or "").strip():
        errs.append("flags_rhel%s: dictionary is empty and _meta.status does not say why" % v)
    if not meta.get("generator"):
        errs.append("flags_rhel%s: _meta.generator missing" % v)
    return errs


def tools_errors(tools):
    errs = []
    for t in tools:
        tid = t.get("id", "?")
        errs += provenance_errors("tools entry %s" % tid, t.get("source"))
        avail = t.get("availability") or {}
        if set(avail.keys()) != set(VERSIONS):
            errs.append("tools entry %s: availability keys %s != the four RHEL keys"
                        % (tid, sorted(avail.keys())))
        for v in VERSIONS:
            a = avail.get(v) or {}
            if "available" not in a:
                errs.append("tools entry %s: availability['%s'] has no 'available' value" % (tid, v))
            elif a.get("available") is False and not a.get("reason"):
                errs.append("tools entry %s: availability['%s'] is unavailable with no reason" % (tid, v))
    return errs


def cci_map_errors(ds, referenced):
    errs = []
    meta = (ds or {}).get("_meta") or {}
    errs += provenance_errors("cci_nist _meta", meta.get("source"))
    cci = (ds or {}).get("cci") or {}
    if meta.get("entry_count") is not None and meta["entry_count"] != len(cci):
        errs.append("cci_nist: _meta.entry_count %s != %d embedded mappings"
                    % (meta.get("entry_count"), len(cci)))
    missing = sorted(referenced - set(cci))
    if missing:
        errs.append("cci_nist: CCI(s) referenced by an embedded rule and absent from the map: %s"
                    % ", ".join(missing[:8]))
    return errs


# ---------------------------------------------------------------------------
# the whole content bundle
# ---------------------------------------------------------------------------

def make_ctx(data, source_ids=None, have_sources_json=False):
    """Derive every cross-file fact an entry is checked against, from the bundle."""
    return {
        "categories": set(data.get("commands", {}).get("categories") or []),
        "tool_ids": set(t.get("id") for t in data.get("tools", {}).get("tools", [])),
        "rule_index": {v: {r["i"]: r for r in (data.get("rules", {}).get(v) or {}).get("rules", [])
                           if r.get("i")} for v in VERSIONS},
        "captures": (data.get("expected_output", {}) or {}).get("captures") or {},
        "source_ids": set(source_ids or ()),
        "have_sources_json": bool(have_sources_json),
        # ADR-001 §6.1: no RHEL host has been read yet, so every dictionary is empty
        # and a null flag explain is the honest value. See flags_errors().
        "flags_datasets_empty": not any((data.get("flags", {}).get(v) or {}).get("clis")
                                        for v in VERSIONS),
    }


def content_errors(data, source_ids=None, have_sources_json=False):
    """Validate a loaded content bundle (build.py load_content() shape).

    Returns a list of error strings, most specific first. Never raises on shape:
    a malformed bundle produces errors, not a traceback.
    """
    errs = []
    ctx = make_ctx(data, source_ids, have_sources_json)

    for v in VERSIONS:
        errs += rules_dataset_errors(v, (data.get("rules") or {}).get(v))
        errs += flags_dataset_errors(v, (data.get("flags") or {}).get(v))
    errs += tools_errors((data.get("tools") or {}).get("tools", []))

    referenced = set()
    for v in VERSIONS:
        for r in ((data.get("rules") or {}).get(v) or {}).get("rules", []):
            referenced.update(r.get("cci") or [])
    errs += cci_map_errors(data.get("cci_nist"), referenced)

    ids = []
    for e in (data.get("commands") or {}).get("entries", []):
        ids.append(e.get("id") or "?")
        errs += entry_errors(e, ctx)
    dupes = sorted(set(i for i in ids if ids.count(i) > 1))
    if dupes:
        errs.append("duplicate command entry ids: %s" % ", ".join(dupes))

    # The mined vendor-reference family. Checked against the CURATED ids so a
    # mined record can never occupy an id the assembler would resolve.
    if "reference_commands" in data:
        errs += reference_commands_errors(data.get("reference_commands"), curated_ids=ids)
    return errs


# ---------------------------------------------------------------------------
# command-head resolution and stage splitting (ADR-002 ruling 1, Al Kowalski)
#
# WHY. qa.py Q22 asserts "the declared tool is the invoked binary" by taking the
# first word of a command and stripping ONE leading "sudo". Measured against the
# command text this product now mines out of DISA check/fix prose, that rule is
# wrong on a large fraction of real lines: 57% are sudo-headed (several of those
# with sudo's OWN options in front of the binary) and 462 are multi-stage
# pipelines. A gate that is wrong that often gets loosened until it proves
# nothing, so the resolution is fixed here instead, once, and shared.
#
# TWO INDEPENDENT STATEMENTS, ON PURPOSE. This module is the authority for
# content (build.py and extract/ import it). qa.py keeps its own implementation
# of the same rule, as it does for the provenance and header-bound field rules,
# because a gate that re-uses the extractor's code path cannot catch the
# extractor being wrong. tests/test_command_head.py runs BOTH over one fixture
# table and asserts they agree -- and asserts that the NAIVE rule this replaces
# gets those same rows wrong, so the table cannot be satisfied by weakening the
# resolver back to where it started.
#
# WHAT IS AND IS NOT DESCENDED INTO. `sudo`, `doas`, `env`, `nohup`, `timeout`,
# `nice`, `ionice`, `stdbuf`, `setsid`, `xargs`, `command`, `exec`, `time` and
# `runuser` are transparent wrappers: the binary the operator cares about is
# behind them. `su`, `sh`, `bash` and `sudo -s`/`sudo -i` are NOT -- they take
# their command as a quoted STRING argument, and the binary this line invokes
# really is su/sh/bash. Guessing at the contents of a quoted -c argument would
# be inventing a fact; the honest head is the wrapper itself.
# ---------------------------------------------------------------------------

# wrapper -> options of that wrapper which consume a following argument.
#
# DELIBERATELY SMALL (threat model v2, M4). ADR-002 named sudo, sudo -u X, env
# VAR=v, nohup, timeout N and xargs. Marcus Reed narrowed that and the narrowing
# is adopted: `env VAR=value`, `su -c` and `sh -c`/`bash -c` prefixes go to
# RESIDUE, not parsing. His reason -- asking a gate to grow a parser puts a
# parser in the trust path -- is the right one, so this table holds only the
# wrappers that are both unambiguous and unavoidable: `sudo` heads 57% of the
# command text this product mines, and dropping it would mis-file the majority
# of the catalog under a tool called "sudo".
#
# NOT here, on purpose: env (M4), su/sh/bash (their -c argument is a quoted
# string this module will not guess the contents of -- M4 routes those lines to
# residue), and the long tail (nice, ionice, stdbuf, setsid, runuser, command,
# exec, time). For that tail the wrapper IS the invoked binary and is reported
# as such; that is a true statement with no parsing behind it.
TRANSPARENT_WRAPPERS = {
    "sudo": ("-u", "-g", "-p", "-C", "-U", "-r", "-t", "-h", "-D", "-R",
             "--user", "--group", "--prompt", "--role", "--type", "--close-from",
             "--host", "--chdir", "--chroot"),
    "doas": ("-u", "-C"),
    "nohup": (),
    "xargs": ("-I", "-i", "-n", "-P", "-d", "-E", "-e", "-s", "-a", "-L", "-l",
              "--replace", "--max-args", "--max-procs", "--delimiter", "--eof",
              "--max-chars", "--arg-file", "--max-lines"),
    "timeout": ("-s", "-k", "--signal", "--kill-after"),
}
# Wrappers whose first non-option POSITIONAL argument is their own (a duration,
# not the program): `timeout 5 systemctl ...`.
WRAPPER_EATS_ONE_POSITIONAL = ("timeout",)
# A wrapper option that means "run a shell", so there is no further binary to
# resolve to and the wrapper itself is the head.
WRAPPER_STOPS_HERE = ("-s", "-i", "--shell", "--login", "-c")

# Heads whose command is a quoted string argument. M4: a line headed by one of
# these is REFUSED, not parsed -- it is recorded in residue instead. Naming them
# here keeps the refusal a property of the shared table rather than a rule each
# caller reinvents.
REFUSED_HEADS = ("su", "sh", "bash", "ksh", "zsh", "dash", "env", "chroot", "eval")

ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Top-level stage separators. `|&` is bash's "pipe stderr too"; `|` covers it.
STAGE_SEPARATORS = ("||", "&&", "|", ";", "\n")


def split_tokens(cmd):
    """Whitespace tokens, honouring single and double quotes.

    Not a shell parser and never used as one: the command TEXT is always kept
    exactly as the source wrote it. This exists only to find the program name.
    """
    out, buf, quote = [], "", None
    for ch in str(cmd):
        if quote:
            buf += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf += ch
            continue
        if ch.isspace():
            if buf:
                out.append(buf)
                buf = ""
            continue
        buf += ch
    if buf:
        out.append(buf)
    return out


def split_stages(cmd):
    """Top-level pipeline/list stages, in order, quotes and $( ) respected.

    A command substitution is NOT a stage: `stat -c %U $(ls -d /x | head -1)`
    runs stat, and the pipe inside the substitution belongs to the substitution.
    """
    stages, buf, quote, depth, i = [], "", None, 0, 0
    s = str(cmd)
    while i < len(s):
        ch = s[i]
        if quote:
            buf += ch
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            buf += ch
            i += 1
            continue
        if ch == "`":
            depth += 1 if depth == 0 else -1     # backticks toggle rather than nest
            buf += ch
            i += 1
            continue
        if s.startswith("$(", i):
            depth += 1
            buf += "$("
            i += 2
            continue
        if ch == "(" and depth > 0:
            depth += 1
            buf += ch
            i += 1
            continue
        if ch == ")" and depth > 0:
            depth -= 1
            buf += ch
            i += 1
            continue
        if depth == 0:
            hit = None
            for sep in STAGE_SEPARATORS:
                if s.startswith(sep, i):
                    hit = sep
                    break
            if hit:
                stages.append(buf.strip())
                buf = ""
                i += len(hit)
                continue
        buf += ch
        i += 1
    stages.append(buf.strip())
    return [st for st in stages if st]


def command_head(stage):
    """The binary ONE stage invokes, resolved through the transparent wrappers.

    Returns the token as written (so an absolute path stays absolute); use
    head_binary() for the basename. None when the stage names no program.
    """
    toks = split_tokens(stage)
    i = 0
    while True:
        while i < len(toks) and ENV_ASSIGN_RE.match(toks[i]):
            i += 1
        if i >= len(toks):
            return None
        name = toks[i].rsplit("/", 1)[-1]
        if name not in TRANSPARENT_WRAPPERS:
            return toks[i]
        opts_with_arg = TRANSPARENT_WRAPPERS[name]
        i += 1
        stop = False
        while i < len(toks) and toks[i].startswith("-") and toks[i] != "-":
            opt = toks[i]
            if opt == "--":
                i += 1
                break
            if opt in WRAPPER_STOPS_HERE:
                stop = True
                break
            i += 1
            if opt in opts_with_arg:
                i += 1
        if stop:
            # `sudo -i`, `sudo -s`, `runuser -c '...'`: the program run is a shell
            # the wrapper starts, and its -c argument is a quoted string this
            # module will not guess the contents of. The wrapper IS the head.
            return name
        if name in WRAPPER_EATS_ONE_POSITIONAL and i < len(toks):
            i += 1
        if i >= len(toks):
            return name                              # a bare wrapper invokes itself
    # unreachable


def head_binary(stage):
    """command_head() as a bare program name (basename, no path)."""
    head = command_head(stage)
    return head.rsplit("/", 1)[-1] if head else None


def stage_binaries(cmd):
    """The binary each top-level stage invokes, in order, duplicates kept.

    ADR-002 ruling 1: a multi-stage command is asserted PER STAGE, never for the
    line -- `sudo grep x /etc/f | grep -v '^#'` runs grep twice and `sshd -T |
    awk '{print $1}'` runs two different binaries, and a gate that only looks at
    the line's first word cannot tell those apart.
    """
    return [head_binary(st) for st in split_stages(cmd)]


def naive_head(cmd):
    """The rule this replaces, kept so a test can prove the fixture has teeth.

    NEVER call this for a real answer. It is the pre-ADR-002 Q22 rule: first
    word, one leading `sudo` stripped.
    """
    words = str(cmd).split()
    if words and words[0] == "sudo":
        words = words[1:]
    return words[0] if words else None


# ---------------------------------------------------------------------------
# reference_commands -- the mined vendor-reference family (extract/mine_commands.py)
#
# A GENERATED family, and a DIFFERENT TIER from content/commands.json. The 27
# curated entries carry verify text, undo text, a reviewed blast rating and 18
# human capture receipts. A mined record carries none of that and must never be
# able to look as though it does, so this schema REFUSES the keys that would
# make it look curated -- above all `verified`. ADR-002: "no extractor may ever
# write a verified receipt -- the schema must refuse it, so a miner cannot
# invent one while Q16 stays true and silent." That is this function.
#
# KEY NAMING. Fields that carry a CLAIM (`tier`, `authority`, `license_class`)
# are spelled out in full: a reader of the data island must not have to decode
# an abbreviation to find out how strong a claim a record is making. Bulk fields
# (`t` tool, `c` command, `k` kind, `v` versions, `st` stage binaries, `o`
# occurrences) are compact, the same trade the RULES datasets already make.
# ---------------------------------------------------------------------------

REFERENCE_KINDS = ("invocation", "synopsis")
# ADR-002 ruling 2. `governing`: DISA STIG check/fix text, for the release that
# STIG governs -- a requirement, attributable to DISA. `documentary`: a man page
# or --help capture -- how a binary documents itself, and no requirement at all.
# Computed from the source, never declared by hand, and never flattened together.
REFERENCE_AUTHORITIES = ("governing", "documentary")
# Keys whose presence would make a mined record indistinguishable from a curated
# one. There is no legitimate reason for an extractor to emit any of them.
REFERENCE_FORBIDDEN_KEYS = (
    "verified", "receipt", "capture", "expected_output", "blast", "blast_floor",
    "rhel_versions", "template", "fields", "stig", "flags", "verify", "undo",
    "intent", "category", "privilege", "same_as",
)
REFERENCE_OCC_FIELDS = ("v", "l")


def reference_record_errors(rec, i, source_ids, seen_ids, curated_ids):
    errs = []
    where = "reference_commands[%d]" % i
    if not isinstance(rec, dict):
        return [where + " is not an object"]
    rid = rec.get("id")
    where = "reference_commands %s" % (rid or "#%d" % i)
    if not isinstance(rid, str) or not rid.startswith("ref-"):
        errs.append("%s: id must be a string starting with 'ref-' -- the prefix is what keeps a "
                    "mined record out of the curated id space the assembler resolves against"
                    % where)
    elif rid in seen_ids:
        errs.append("%s: duplicate reference command id" % where)
    elif rid in curated_ids:
        errs.append("%s: id collides with a curated commands.json entry id -- entryById() would "
                    "resolve one of them and the operator could not tell which" % where)
    if rid:
        seen_ids.add(rid)

    present = [k for k in REFERENCE_FORBIDDEN_KEYS if k in rec]
    if present:
        errs.append("%s: carries the key(s) %s. A mined record is vendor reference text: it has "
                    "no verify/undo/blast/receipt and an extractor may never write one. The "
                    "curated catalog's 18 human receipts mean something only because nothing "
                    "else can claim one (ADR-002)" % (where, ", ".join(present)))

    if rec.get("tier") != "reference":
        errs.append("%s: tier is %r, and every record in this family is 'reference'"
                    % (where, rec.get("tier")))
    if not isinstance(rec.get("verbatim_span"), bool):
        errs.append("%s: verbatim_span must be true or false -- it is the flag that decides "
                    "whether this text may be quoted as the vendor's own in an evidence export "
                    "(threat model v2, M3), and an absent flag is not a false one" % where)
    if rec.get("verbatim_span") and rec.get("trunc"):
        errs.append("%s: is flagged truncated AND verbatim_span -- a line the vendor's own page "
                    "wrapped and cut is not a usable span of anything" % where)
    if rec.get("verbatim_span") and rec.get("authority") != "governing":
        # Not an error in itself, but the pair is what the evidence gate reads,
        # so a documentary record claiming a governing-only property is worth
        # saying out loud rather than leaving for the UI to interpret.
        pass
    if rec.get("authority") not in REFERENCE_AUTHORITIES:
        errs.append("%s: authority %r is not one of %s -- it is COMPUTED from the source "
                    "(DISA check/fix text governs; a man page documents) and must never be blank"
                    % (where, rec.get("authority"), ", ".join(REFERENCE_AUTHORITIES)))
    if rec.get("k") not in REFERENCE_KINDS:
        errs.append("%s: kind %r is not one of %s" % (where, rec.get("k"), ", ".join(REFERENCE_KINDS)))
    if rec.get("license_class") not in LICENSE_CLASSES:
        errs.append("%s: license_class %r is not one of %s"
                    % (where, rec.get("license_class"), ", ".join(LICENSE_CLASSES)))

    cmd = rec.get("c")
    if not isinstance(cmd, str) or not cmd.strip():
        errs.append("%s: c (the command text) is empty" % where)
    else:
        cp = control_char_name(cmd)
        if cp:
            errs.append("%s: command text contains the control character %s -- a mined line "
                        "reaches the clipboard and the evidence export" % (where, cp))
    tool = rec.get("t")
    if not isinstance(tool, str) or not tool.strip():
        errs.append("%s: t (the tool this command is filed under) is empty" % where)
    elif isinstance(cmd, str) and cmd.strip():
        # ADR-002 ruling 1: the declared tool IS the resolved head of stage one,
        # through the wrapper chain -- not the first word.
        stages = stage_binaries(cmd)
        head = stages[0] if stages else None
        if head and head != tool:
            errs.append("%s: declared tool '%s' but stage one invokes '%s'" % (where, tool, head))
        declared_stages = rec.get("st")
        if len(stages) > 1:
            if declared_stages != stages:
                errs.append("%s: st %r does not match the per-stage binaries %r -- a multi-stage "
                            "command is asserted per stage, never for the line"
                            % (where, declared_stages, stages))
        elif declared_stages is not None:
            errs.append("%s: single-stage command declares st %r" % (where, declared_stages))

    versions = rec.get("v")
    if not isinstance(versions, list) or not versions or any(v not in VERSIONS for v in versions):
        errs.append("%s: v %r is not a non-empty subset of %s" % (where, versions, ", ".join(VERSIONS)))

    occ = rec.get("o")
    if not isinstance(occ, list) or not occ:
        errs.append("%s: o (occurrences) is empty -- a record with no citation is a command with "
                    "no source, which is the one thing this product never ships" % where)
        return errs
    for j, o in enumerate(occ):
        at = "%s: o[%d]" % (where, j)
        if not isinstance(o, dict):
            errs.append(at + " is not an object")
            continue
        for field in REFERENCE_OCC_FIELDS:
            if o.get(field) in (None, ""):
                errs.append("%s: missing %s" % (at, field))
        if o.get("v") not in VERSIONS:
            errs.append("%s: rhel version %r is not one of %s" % (at, o.get("v"), ", ".join(VERSIONS)))
        shapes = [k for k in ("s", "g", "p") if o.get(k)]
        if len(shapes) != 1:
            errs.append("%s: an occurrence cites exactly ONE of a STIG rule (s), a Red Hat guide "
                        "(g) or a staged capture file (p) -- it named %s"
                        % (at, ", ".join(shapes) or "none of them"))
            continue
        ref = {"s": "disa-rhel%s-stig", "g": "redhat-rhel%s-guides",
               "p": "raw-rhel%s"}[shapes[0]] % o.get("v")
        if source_ids and ref not in source_ids:
            errs.append("%s: derived source_ref '%s' does not resolve in _meta.sources" % (at, ref))
        if isinstance(versions, list) and o.get("v") not in versions:
            errs.append("%s: cites RHEL %s, which is not in this record's v %r"
                        % (at, o.get("v"), versions))
    return errs


def reference_commands_errors(ds, curated_ids=()):
    """The whole reference_commands family."""
    errs = []
    meta = (ds or {}).get("_meta") or {}
    records = (ds or {}).get("commands")
    if not meta.get("generator"):
        errs.append("reference_commands: _meta.generator missing (a generated file declares its "
                    "extractor, and Q15 re-runs it)")
    if meta.get("tier") != "reference":
        errs.append("reference_commands: _meta.tier must be 'reference'")
    errs += provenance_errors("reference_commands _meta", meta.get("source"))
    sources = meta.get("sources")
    if not isinstance(sources, dict) or not sources:
        errs.append("reference_commands: _meta.sources is empty -- every occurrence resolves its "
                    "provenance through it")
        sources = {}
    for sid in sorted(sources):
        errs += provenance_errors("reference_commands _meta.sources['%s']" % sid, sources[sid])
    if not isinstance(records, list):
        return errs + ["reference_commands: commands is not a list"]
    if meta.get("record_count") != len(records):
        errs.append("reference_commands: _meta.record_count %s != %d embedded records"
                    % (meta.get("record_count"), len(records)))
    seen = set()
    source_ids = set(sources)
    curated = set(curated_ids or ())
    for i, rec in enumerate(records):
        errs += reference_record_errors(rec, i, source_ids, seen, curated)
    return errs
