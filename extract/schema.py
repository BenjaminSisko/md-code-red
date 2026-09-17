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

VERSIONS = ("7", "8", "9", "10")
BLASTS = ("green", "yellow", "red")
LICENSE_CLASSES = ("verbatim-ok", "paraphrase-only")

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
    errs += provenance_errors("commands entry %s" % eid, e.get("source"))
    errs += rhel_versions_errors(eid, e.get("rhel_versions"))
    errs += flags_errors(eid, e.get("flags"), dict(ctx, entry_verified=bool(e.get("verified"))))
    errs += stig_errors(eid, e.get("stig"), ctx)
    errs += verified_errors(eid, e.get("verified"))
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


def verified_errors(eid, ver):
    """`verified` is a receipt ({by, on, host}), never a bare boolean claim."""
    if ver in (False, None):
        return []
    if ver is True:
        return ["commands entry %s: verified is true with no receipt — it must be "
                "{by, on, host} naming who ran it, when, and on which host" % eid]
    if not isinstance(ver, dict):
        return ["commands entry %s: verified must be false or {by, on, host}" % eid]
    errs = []
    for field in ("by", "on", "host"):
        if not ver.get(field):
            errs.append("commands entry %s: verified is set but has no capture record field '%s'" % (eid, field))
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
    return errs
