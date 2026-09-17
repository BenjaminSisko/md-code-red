#!/usr/bin/env python3
"""build.py — assemble dist/md-code-red_<version>.html from template.html + content/.

Stdlib only. Usage:
    python3 build.py            # build the single-file artifact and its .sha256

The single-file output is the only artifact that crosses the air gap. It is
built, never patched: if the output is wrong, the fix goes into content/ or into
the extractor that produced it, and the file is rebuilt (ADR-001 §7.1/§7.4, the
Cardinal Rule). Nobody opens dist/*.html in an editor, at any size, ever.

Lineage: forked from grey-beard-ansible v1.0.1 build.py. The load -> validate ->
inject -> token-replace skeleton and the "</" escaping of the island payload come
over unchanged; the CONTENT map and validate() are MD CODE RED's own (ADR-001 §4).
"""

import hashlib
import json
import os
import sys
from datetime import date

REPO = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "MD CODE RED"
APP_VERSION = "v1.0.0-dev"
APP_BUILD_DATE = date.today().isoformat()
CLASSIFICATION = "UNCLASSIFIED"

VERSIONS = ("7", "8", "9", "10")
BLASTS = ("green", "yellow", "red")
LICENSE_CLASSES = ("verbatim-ok", "paraphrase-only")

# ADR-001 §4 content layout. Curated families are hand-authored; generated
# families are produced by extract/ and are never hand-edited.
CONTENT = {
    # curated
    "commands": "commands.json",
    "tools": "tools.json",
    "dangerous": "dangerous.json",
    "glossary": "glossary.json",
    # generated — extract/make_skeleton_content.py today, parse_xccdf.py at CR-T-07
    "rules_7": "rules_rhel7.json",
    "rules_8": "rules_rhel8.json",
    "rules_9": "rules_rhel9.json",
    "rules_10": "rules_rhel10.json",
    "flags_7": "flags_rhel7.json",
    "flags_8": "flags_rhel8.json",
    "flags_9": "flags_rhel9.json",
    "flags_10": "flags_rhel10.json",
    "cci_nist": "cci_nist.json",
    "expected_output": "expected_output.json",
}

CONTENT_SRC_SOURCES = os.path.join(REPO, "content-src", "SOURCES.json")


def content_dir(root=None):
    return os.path.join(root or REPO, "content")


def load_content(root=None):
    data = {}
    for key, fname in CONTENT.items():
        path = os.path.join(content_dir(root), fname)
        if not os.path.exists(path):
            sys.exit("FATAL: content/%s is missing" % fname)
        with open(path, encoding="utf-8") as f:
            try:
                data[key] = json.load(f)
            except json.JSONDecodeError as e:
                sys.exit("FATAL: %s is not valid JSON: %s" % (fname, e))
    data["rules"] = {v: data.pop("rules_" + v) for v in VERSIONS}
    data["flags"] = {v: data.pop("flags_" + v) for v in VERSIONS}
    data["meta"] = {
        "name": APP_NAME,
        "version": APP_VERSION,
        "built": APP_BUILD_DATE,
        "classification": CLASSIFICATION,
        "air_gap_certified": True,
    }
    return data


# --------------------------------------------------------------------------
# validate() — fails loud, never silently drops an entry
# --------------------------------------------------------------------------

def _provenance_errors(where, src):
    """source.title / url_or_man / retrieved_on / license_class are mandatory."""
    errs = []
    if not isinstance(src, dict):
        return ["%s: missing provenance (no source object)" % where]
    for field in ("title", "url_or_man", "retrieved_on", "license_class"):
        if not src.get(field):
            errs.append("%s: missing provenance field source.%s" % (where, field))
    lc = src.get("license_class")
    if lc and lc not in LICENSE_CLASSES:
        errs.append("%s: license_class '%s' is not one of %s" % (where, lc, ", ".join(LICENSE_CLASSES)))
    return errs


def _resolve_chain(entry_id, versions, key, errs):
    """Follow same_as pointers to a concrete value. Detects cycles and dangling keys."""
    seen = []
    cur = key
    while True:
        if cur in seen:
            errs.append("commands entry %s: same_as cycle %s" % (entry_id, " -> ".join(seen + [cur])))
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


def validate(data):
    errs = []
    cmds = data["commands"]
    categories = set(cmds.get("categories") or [])
    tool_ids = set(t.get("id") for t in data["tools"].get("tools", []))
    have_sources_json = os.path.exists(CONTENT_SRC_SOURCES)
    source_ids = set()
    if have_sources_json:
        with open(CONTENT_SRC_SOURCES, encoding="utf-8") as f:
            source_ids = set(json.load(f).get("sources", {}).keys())

    # ---- generated datasets: provenance and shape ----
    for v in VERSIONS:
        rules = data["rules"][v]
        meta = rules.get("_meta") or {}
        errs += _provenance_errors("rules_rhel%s _meta" % v, meta.get("source"))
        if not meta.get("generator"):
            errs.append("rules_rhel%s: _meta.generator missing (generated files declare their extractor)" % v)
        if meta.get("rule_count") != len(rules.get("rules", [])):
            errs.append("rules_rhel%s: _meta.rule_count %s != %d embedded rules"
                        % (v, meta.get("rule_count"), len(rules.get("rules", []))))
        for r in rules.get("rules", []):
            if not r.get("i") or not r.get("rid") or not r.get("t"):
                errs.append("rules_rhel%s: rule %s missing STIG ID, rule id, or title" % (v, r.get("v", "?")))
        flags = data["flags"][v]
        fmeta = flags.get("_meta") or {}
        if flags.get("clis"):
            # A dictionary that embeds flag text must name where the text came from.
            errs += _provenance_errors("flags_rhel%s _meta" % v, fmeta.get("source"))
        elif not (fmeta.get("status") or "").strip():
            # An empty dictionary embeds nothing, so it has nothing to cite — but it
            # must say, in words, why it is empty. Silence is not an option.
            errs.append("flags_rhel%s: dictionary is empty and _meta.status does not say why" % v)
        if not fmeta.get("generator"):
            errs.append("flags_rhel%s: _meta.generator missing" % v)
    errs += _provenance_errors("cci_nist _meta", (data["cci_nist"].get("_meta") or {}).get("source"))
    for t in data["tools"].get("tools", []):
        errs += _provenance_errors("tools entry %s" % t.get("id", "?"), t.get("source"))
        avail = t.get("availability") or {}
        if set(avail.keys()) != set(VERSIONS):
            errs.append("tools entry %s: availability keys %s != the four RHEL keys"
                        % (t.get("id", "?"), sorted(avail.keys())))
        for v in VERSIONS:
            a = avail.get(v) or {}
            if "available" not in a:
                errs.append("tools entry %s: availability['%s'] has no 'available' value" % (t.get("id", "?"), v))
            elif a.get("available") is False and not a.get("reason"):
                errs.append("tools entry %s: availability['%s'] is unavailable with no reason" % (t.get("id", "?"), v))

    # ---- rule lookup for referential integrity ----
    rule_by_version = {}
    for v in VERSIONS:
        rule_by_version[v] = {r["i"]: r for r in data["rules"][v].get("rules", []) if r.get("i")}

    captures = (data["expected_output"].get("captures") or {})

    # ---- command entries ----
    ids = []
    for e in cmds.get("entries", []):
        eid = e.get("id") or "?"
        ids.append(eid)
        for field in ("id", "tool", "category", "intent", "verify", "undo", "blast", "source"):
            if not e.get(field):
                errs.append("commands entry %s: missing %s" % (eid, field))
        if e.get("blast") not in BLASTS:
            errs.append("commands entry %s: bad blast '%s'" % (eid, e.get("blast")))
        if e.get("category") and e.get("category") not in categories:
            errs.append("commands entry %s: category '%s' not in commands.json categories" % (eid, e.get("category")))
        if e.get("tool") and e.get("tool") not in tool_ids:
            errs.append("commands entry %s: tool '%s' does not exist in tools.json" % (eid, e.get("tool")))
        errs += _provenance_errors("commands entry %s" % eid, e.get("source"))

        # four RHEL keys, always, with an explicit value shape
        versions = e.get("rhel_versions")
        if not isinstance(versions, dict):
            errs.append("commands entry %s: rhel_versions missing" % eid)
        else:
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
                if not isinstance(val, dict):
                    continue
                if "same_as" in val:
                    _resolve_chain(eid, versions, v, errs)
                elif "unavailable" in val:
                    u = val.get("unavailable") or {}
                    if not (u.get("reason") or "").strip():
                        errs.append("commands entry %s: rhel_versions['%s'].unavailable has an empty reason" % (eid, v))
                elif "command" in val:
                    if not (val.get("command") or "").strip():
                        errs.append("commands entry %s: rhel_versions['%s'].command is empty" % (eid, v))
                    cin = val.get("changed_in_note")
                    if cin not in (None, {}) and isinstance(cin, dict):
                        for field in ("version", "what", "source_ref"):
                            if not cin.get(field):
                                errs.append("commands entry %s: rhel_versions['%s'].changed_in_note missing %s"
                                            % (eid, v, field))
                else:
                    errs.append("commands entry %s: rhel_versions['%s'] is none of "
                                "{command,notes,changed_in_note} / {same_as} / {unavailable}" % (eid, v))

        # flags
        for fl in (e.get("flags") or []):
            if not fl.get("flag"):
                errs.append("commands entry %s: a flags[] item has no flag token" % eid)
            ref = fl.get("source_ref")
            if ref:
                if not have_sources_json:
                    errs.append("commands entry %s: flag '%s' cites source_ref '%s' but "
                                "content-src/SOURCES.json does not exist yet" % (eid, fl.get("flag"), ref))
                elif ref not in source_ids:
                    errs.append("commands entry %s: flag '%s' source_ref '%s' does not resolve in "
                                "content-src/SOURCES.json" % (eid, fl.get("flag"), ref))

        # stig[] referential integrity
        for s in (e.get("stig") or []):
            sid = s.get("stig_id")
            v = s.get("rhel_version")
            if not sid:
                errs.append("commands entry %s: a stig[] item has no stig_id" % eid)
                continue
            if v not in VERSIONS:
                errs.append("commands entry %s: stig %s has rhel_version '%s', not one of %s"
                            % (eid, sid, v, ", ".join(VERSIONS)))
                continue
            rec = rule_by_version[v].get(sid)
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
            exp = s.get("expected_output")
            if exp:
                key = "%s|%s|%s" % (eid, sid, v)
                if key not in captures:
                    errs.append("commands entry %s: stig %s carries expected_output with no capture record "
                                "'%s' in content/expected_output.json — expected output is captured, never typed"
                                % (eid, sid, key))

        # verified is a receipt, not a boolean claim
        ver = e.get("verified")
        if ver not in (False, None):
            if not isinstance(ver, dict):
                errs.append("commands entry %s: verified must be false or {by,on,host}" % eid)
            else:
                for field in ("by", "on", "host"):
                    if not ver.get(field):
                        errs.append("commands entry %s: verified is set but has no capture record field '%s'"
                                    % (eid, field))

    dupes = sorted(set(i for i in ids if ids.count(i) > 1))
    if dupes:
        errs.append("duplicate command entry ids: %s" % ", ".join(dupes))

    if errs:
        for e in errs:
            print("SCHEMA:", e, file=sys.stderr)
        sys.exit("FATAL: %d schema error(s)" % len(errs))


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def assemble(data):
    """Resolve same_as, join captures, build reverse links, seed the search index."""
    errs = []
    for e in data["commands"]["entries"]:
        versions = e["rhel_versions"]
        resolved = {}
        for v in VERSIONS:
            val = versions[v]
            if "same_as" in val:
                target = _resolve_chain(e["id"], versions, v, errs)
                if target is None:
                    continue
                base = dict(versions[target])
                base["resolved_from"] = target
                if val.get("changed_in_note"):
                    base["changed_in_note"] = val["changed_in_note"]
                resolved[v] = base
            else:
                resolved[v] = val
        e["rhel_versions"] = resolved
        # join captured expected output onto the STIG rows
        for s in (e.get("stig") or []):
            key = "%s|%s|%s" % (e["id"], s.get("stig_id"), s.get("rhel_version"))
            cap = (data["expected_output"].get("captures") or {}).get(key)
            if cap:
                s["expected_output"] = cap
    if errs:
        for msg in errs:
            print("ASSEMBLY:", msg, file=sys.stderr)
        sys.exit("FATAL: %d assembly error(s)" % len(errs))

    # RULES.cmds[] reverse links: STIG ID -> command entry ids
    back = {v: {} for v in VERSIONS}
    for e in data["commands"]["entries"]:
        for s in (e.get("stig") or []):
            back[s["rhel_version"]].setdefault(s["stig_id"], []).append(e["id"])
    for v in VERSIONS:
        for r in data["rules"][v].get("rules", []):
            r["cmds"] = back[v].get(r.get("i"), [])

    # search index seed — ids and display strings only, never the full haystacks
    seed = {"tools": [], "commands": [], "stig": []}
    for t in data["tools"].get("tools", []):
        seed["tools"].append({"id": t.get("id"), "label": t.get("label")})
    for e in data["commands"]["entries"]:
        seed["commands"].append({"id": e["id"], "label": e.get("intent"), "tool": e.get("tool")})
    for v in VERSIONS:
        for r in data["rules"][v].get("rules", []):
            seed["stig"].append({"id": r.get("i"), "v": v, "cat": r.get("c"), "label": r.get("t")})
    data["index_seed"] = seed
    return data


def build():
    data = load_content()
    validate(data)
    data = assemble(data)

    tpl_path = os.path.join(REPO, "template.html")
    with open(tpl_path, encoding="utf-8") as f:
        tpl = f.read()
    if "/*__DATA__*/" not in tpl:
        sys.exit("FATAL: template.html has no /*__DATA__*/ placeholder")

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    payload = payload.replace("</", "<\\/")  # keep the JSON safe inside a <script> block
    out = tpl.replace("/*__DATA__*/", payload)
    out = (out.replace("__APP_NAME__", APP_NAME)
              .replace("__VERSION__", APP_VERSION)
              .replace("__BUILT_DATE__", APP_BUILD_DATE)
              .replace("__CLASSIFICATION__", CLASSIFICATION))

    dist = os.path.join(REPO, "dist")
    if not os.path.isdir(dist):
        os.makedirs(dist)
    dest = os.path.join(dist, "md-code-red_%s.html" % APP_VERSION)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    digest = hashlib.sha256(out.encode("utf-8")).hexdigest()
    with open(dest + ".sha256", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (digest, os.path.basename(dest)))

    size = os.path.getsize(dest)
    n_rules = sum(len(data["rules"][v].get("rules", [])) for v in VERSIONS)
    print("built %s" % os.path.relpath(dest, REPO))
    print("  %s %s  built %s  (%s)" % (APP_NAME, APP_VERSION, APP_BUILD_DATE, CLASSIFICATION))
    print("  size: %.2f MB (%d bytes) — REPORT ONLY, no ceiling (Founder ruling 2026-09-17)"
          % (size / 1024.0 / 1024.0, size))
    print("  sha256: %s" % digest)
    print("  %d command entries, %d tools, %d embedded STIG rules (%s), %d CCI mappings"
          % (len(data["commands"]["entries"]),
             len(data["tools"].get("tools", [])),
             n_rules,
             ", ".join("RHEL %s: %d" % (v, len(data["rules"][v].get("rules", []))) for v in VERSIONS),
             len(data["cci_nist"].get("cci", {}))))


if __name__ == "__main__":
    build()
