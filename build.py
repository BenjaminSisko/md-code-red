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

# The content schema lives in extract/schema.py so that build.py and
# tests/test_schema.py enforce the same rules from one file (CR-T-06). extract/ is
# a plain directory of scripts, not a package, so it goes on the path explicitly.
sys.path.insert(0, os.path.join(REPO, "extract"))
import schema  # noqa: E402
APP_NAME = "MD CODE RED"
APP_VERSION = "v1.0.0-dev"
APP_BUILD_DATE = date.today().isoformat()
CLASSIFICATION = "UNCLASSIFIED"

VERSIONS = schema.VERSIONS
BLASTS = schema.BLASTS
LICENSE_CLASSES = schema.LICENSE_CLASSES

# ADR-001 §4 content layout. Curated families are hand-authored; generated
# families are produced by extract/ and are never hand-edited.
CONTENT = {
    # curated
    "commands": "commands.json",
    "tools": "tools.json",
    "dangerous": "dangerous.json",
    "glossary": "glossary.json",
    # generated — extract/parse_xccdf.py (rules_*, cci_nist),
    #             extract/make_pending_skeletons.py (flags_*, expected_output)
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
#
# The rules themselves live in extract/schema.py (CR-T-06). This function is the
# build's enforcement point: load the one cross-file fact schema.py cannot derive
# from content/ (the source_ref ids in content-src/SOURCES.json), ask for the error
# list, and refuse to assemble anything if it is non-empty.
# --------------------------------------------------------------------------

def validate(data):
    have_sources_json = os.path.exists(CONTENT_SRC_SOURCES)
    source_ids = set()
    if have_sources_json:
        with open(CONTENT_SRC_SOURCES, encoding="utf-8") as f:
            source_ids = set(json.load(f).get("sources", {}).keys())

    errs = schema.content_errors(data, source_ids=source_ids, have_sources_json=have_sources_json)
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
                target = schema.resolve_chain(e["id"], versions, v, errs)
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
