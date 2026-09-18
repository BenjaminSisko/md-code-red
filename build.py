#!/usr/bin/env python3
"""build.py — assemble dist/md-code-red_<version>.html from template.html + content/.

Stdlib only. Usage:
    python3 build.py            # build the single-file artifact and its .sha256

The single-file output is the only artifact that crosses the air gap. It is
built, never patched: if the output is wrong, the fix goes into content/ or into
the extractor that produced it, and the file is rebuilt (ADR-001 §7.1/§7.4, the
Cardinal Rule). Nobody opens dist/*.html in an editor, at any size, ever.

Lineage: forked from grey-beard-ansible v1.0.1 build.py. The load -> validate ->
inject -> token-replace skeleton comes over unchanged (the island escaping does not:
see escape_island(), MCR-SEC-007); the CONTENT map and validate() are MD CODE RED's own (ADR-001 §4).
"""

import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))

# The content schema lives in extract/schema.py so that build.py and
# tests/test_schema.py enforce the same rules from one file (CR-T-06). extract/ is
# a plain directory of scripts, not a package, so it goes on the path explicitly.
sys.path.insert(0, os.path.join(REPO, "extract"))
import schema  # noqa: E402
APP_NAME = "MD CODE RED"
APP_VERSION = "v1.0.0-alpha.1"
# Pinned, not date.today(): a release commit fixes both the version and the
# build date together so the artifact this commit produces is reproducible on
# any machine, any day (readiness REL-2026-09-18-001, tag procedure step 2).
# date.today() was fine for -dev builds, where "when was this rebuilt" was the
# useful answer; a tagged release needs "when was this released" instead, and
# that value has to stop moving once it's committed. The next version bump
# repins this alongside APP_VERSION.
APP_BUILD_DATE = "2026-09-18"
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
    # glossary.json (AL-GATE3-011) is deliberately NOT embedded here for the
    # alpha: it shipped in the island, bound to DATASETS.GLOSSARY, and was
    # read by nothing -- no Glossary kind in the search index, no rail, no
    # panel, no renderer. CEO decision, Gate 3 review ENG-2026-09-18-002 §8.1
    # item 2: drop the unreachable payload rather than ship it unfinished.
    # The file stays committed in content/ for a later tranche that wires a
    # real glossary view (docs/ARCHITECTURE_BIBLE.md §25); qa.py's
    # content_family_liveness_failures() (Q8) is what would catch this
    # regressing back in without a renderer to justify it.
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
    # generated — extract/mine_commands.py. A DIFFERENT TIER from `commands`
    # above: vendor reference text mined out of the STIG check/fix prose, the
    # staged man/--help captures and the staged Red Hat product documentation.
    # It carries no verify/undo/blast/receipt and extract/schema.py refuses
    # those keys on it, so it can never be mistaken for the curated catalog.
    "reference_commands": "reference_commands.json",
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
        if "template" in e:
            # A generator spec composes its command at render time from validated
            # field values, so there is no same_as chain to resolve (MCR-SEC-006).
            # schema.spec_errors() has already validated its shape.
            for s in (e.get("stig") or []):
                key = "%s|%s|%s" % (e["id"], s.get("stig_id"), s.get("rhel_version"))
                cap = (data["expected_output"].get("captures") or {}).get(key)
                if cap:
                    s["expected_output"] = cap
            continue
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


def escape_island(payload):
    """Neutralise every HTML-significant character in the JSON data island.

    MCR-SEC-007. The inherited rule was `payload.replace("</", "<\\/")`, with the
    comment "keep the JSON safe inside a <script> block". That closes `</script>`
    and nothing else. It does NOT close the HTML tokeniser's
    script-data-double-escaped state: a payload carrying `<!--` followed by
    `<script` (neither of which has a slash, so neither was rewritten) puts the
    parser into that state, where `</script>` stops terminating the element. The
    island's own closing tag, the app script that follows it and the "Not built
    yet" fallback inside it are then all consumed as text data — a silent denial
    of use on a jump box mid-task, with no error shown.

    DISA XCCDF fix text is embedded verbatim and is vendor-controlled string
    data, so `<!--<script` is a content value away, not an attack away.

    Escaping `<` and `>` as \\u003c / \\u003e is valid JSON (JSON.parse restores
    the characters), costs nothing at parse time, and closes `</script`, `<!--`,
    `-->` and `<script` in one rule rather than enumerating sequences. Every `<`
    and `>` in a JSON document is inside string content — the structural
    characters are {}[],:" and the bare literals — so nothing else is touched.
    """
    return payload.replace("<", "\\u003c").replace(">", "\\u003e")


# --------------------------------------------------------------------------
# The reference corpus: lazy per-family hydration and a build-time inverted
# index (Al Kowalski's standing ruling, restated on this tranche).
#
# THE RULING. "Lazy per-family, per-tier hydration becomes mandatory at 5,000
# corpus records, and the inverted search index must be in place before the
# second family lands." This tranche is 14,488 records across three families,
# so both clocks expired before it was written, and the measurement (see
# docs/PERF_MEASUREMENT.md) is what decides HOW to obey rather than WHETHER.
#
# WHAT WAS MEASURED, on the real built artifact over a local HTTP server. The
# eager 8.08 MB build parsed its island in 10.7 ms against the 2.46 MB build's
# 4.2 ms, reached DOMContentLoaded in ~70 ms against ~31 ms, first contentful
# paint in ~204 ms against ~176 ms, and settled at ~20 MB of JS heap against
# ~7 MB. Worst-case palette latency was 9.5 ms for a single-letter query that
# matched 16,061 of 19,137 index records. Nothing there fails to open, even
# derated an order of magnitude for a jump box. So the whole corpus ships --
# and it ships in the shape the ruling names, because the ruling is not "ship
# if it measures fine": it is an architecture the next family has to land into.
#
# THE SHAPE.
#   mcr-data              everything except the reference RECORDS. Parsed at
#                         boot, and it is the only island that is.
#   mcr-ref-index         the inverted index: token -> posting list. Parsed on
#                         the first palette keystroke, never at boot.
#   mcr-ref-<family>      one island per source family, each the records of
#                         that family alone. Parsed when that family is first
#                         needed and never again.
#
# Boot therefore parses 2.3 MB, which is what the pre-corpus alpha parsed. A
# palette keystroke parses the 0.7 MB index. Only a search that actually HITS
# the Red Hat family pays for the Red Hat family.
#
# WHY SEPARATE ISLANDS rather than one island holding pre-serialised strings.
# The string-in-string shape keeps `exactly two <script> elements` true and was
# measured first: it costs 32.8% -- 1.6 MB -- to JSON-escape the inner
# documents, and it hides the families from every tool that reads the shipped
# file (qa.py, the test harnesses, a human with a text editor). Separate
# islands cost nothing, and Q1's structure check gets STRONGER rather than
# weaker: it goes from counting to two, to naming the exact set of islands that
# may exist and proving each one parses.
# --------------------------------------------------------------------------

# Declaration order. It fixes the island order in the file, the fingerprint
# input order, and the family index used by the posting encoding, so all three
# are one statement rather than three that can drift. Smallest and highest
# authority first: a jump box that only ever opens the DISA family never pays
# for the other two.
REFERENCE_FAMILIES = ("stig_rules", "raw_captures", "redhat_guides")
# Which occurrence key identifies which family. `s` is a STIG rule id, `g` a
# Red Hat guide slug, `p` a staged capture path -- extract/schema.py already
# refuses an occurrence that names anything other than exactly one of them.
FAMILY_BY_OCC_KEY = {"s": "stig_rules", "g": "redhat_guides", "p": "raw_captures"}
# A posting is one integer: family index * FAMILY_STRIDE + ordinal within that
# family. One number per posting rather than a two-element array cuts the index
# island roughly in half, and the stride is asserted against the real family
# sizes at build time so it can never silently wrap.
FAMILY_STRIDE = 1000000
# Tokens shorter than this are not worth a posting list: every one of them
# matches most of the corpus, so the list costs bytes and saves no work. The
# app's own term handling knows this number and falls back to scanning the
# token DICTIONARY for a short term, which is 13k short strings rather than
# 14k records.
REF_INDEX_MIN_TOKEN = 2
REF_TOKEN_RE = re.compile(r"[a-z0-9_.+-]+")


def reference_family_of(rec):
    """The source family one mined record belongs to, read off its FIRST
    occurrence. Deterministic: extract/mine_commands.py emits the occurrence
    list in a fixed order, and a record is never mined from two families --
    the DISA-overlap rule reattributes such a record to DISA whole, it does not
    split it (licensing ruling v1 Ruling 2 condition 2)."""
    occ = (rec.get("o") or [{}])[0]
    for key, family in sorted(FAMILY_BY_OCC_KEY.items()):
        if occ.get(key):
            return family
    return "raw_captures"


def split_reference_families(records):
    """{family: [record, ...]} in REFERENCE_FAMILIES order, records in the order
    the extractor emitted them. Order is load-bearing twice over: it is the
    ordinal a posting resolves against, and Q15 re-runs this and diffs."""
    out = dict((f, []) for f in REFERENCE_FAMILIES)
    for rec in records:
        out[reference_family_of(rec)].append(rec)
    return out


def reference_haystack(rec):
    """The text one record is searchable by: the command itself, the tool it is
    filed under, and every STIG id it cites. Exactly what the flat index built
    at runtime used to lower-case per record per keystroke -- computed once,
    here, and shipped."""
    stigs = " ".join(o.get("s") or "" for o in (rec.get("o") or []))
    return ("%s %s %s" % (rec.get("c") or "", rec.get("t") or "", stigs)).lower()


def build_reference_index(families):
    """The inverted index: {token: [posting, ...]} plus the family order it
    encodes against.

    Sorted everywhere -- the token map by key, each posting list ascending --
    because this is generated content and Q15 re-runs the build and diffs the
    bytes. A dict iteration order accident here is a reproducibility failure.
    """
    postings = {}
    for fi, family in enumerate(REFERENCE_FAMILIES):
        records = families[family]
        if len(records) >= FAMILY_STRIDE:
            sys.exit("FATAL: family %s holds %d records and the posting stride is %d -- "
                     "the encoding would wrap and postings would resolve to the wrong record"
                     % (family, len(records), FAMILY_STRIDE))
        for i, rec in enumerate(records):
            posting = fi * FAMILY_STRIDE + i
            for token in set(REF_TOKEN_RE.findall(reference_haystack(rec))):
                if len(token) < REF_INDEX_MIN_TOKEN:
                    continue
                postings.setdefault(token, []).append(posting)
    # Posting lists are DELTA-encoded: [first, d1, d2, ...], each element the gap
    # from the previous. The values are large (a Red Hat posting is 2,0xx,xxx)
    # and the gaps are small, so this is the difference between ~8 characters per
    # posting and ~3. Measured over this corpus: 0.78 MB of index island becomes
    # 0.34 MB, on 80,905 postings. Decoding is a running sum, four lines in the
    # app, and the encoding is declared in the island itself ("enc") rather than
    # being a convention both sides have to remember.
    encoded = {}
    for tok, ps in postings.items():
        ps.sort()
        out, prev = [], 0
        for p in ps:
            out.append(p - prev)
            prev = p
        encoded[tok] = out
    return {
        "f": list(REFERENCE_FAMILIES),
        "enc": "delta",
        "stride": FAMILY_STRIDE,
        "min_token": REF_INDEX_MIN_TOKEN,
        "counts": dict((f, len(families[f])) for f in REFERENCE_FAMILIES),
        "postings": sum(len(ps) for ps in postings.values()),
        "t": dict(sorted(encoded.items())),
    }


def compute_default_version(data):
    """Which RHEL version the version selector should open on, derived from the
    content instead of a hard-coded literal (Founder alpha feedback, 2026-09-17:
    the selector defaulted to RHEL 9, the one release with no host captures, so
    the first screen was a wall of "Documented, not host-verified" notes).

    The metric: count, per RHEL version, how many command entries carry a REAL
    verified receipt for that version (extract/schema.py's entry_has_any_receipt
    shape — a dict of {by, on, host, capture}, never the bare `false` every
    unreceipted version also holds). The version with the most receipts is the
    one host-verified content actually backs. Ties break toward the lower RHEL
    version number, for a result that is deterministic and easy to state out
    loud rather than an arbitrary dict-ordering accident.

    Returns (version, counts) — counts is returned too so build()'s own
    printed report shows the numbers this decision came from, not just the
    conclusion.
    """
    counts = {v: 0 for v in VERSIONS}
    for e in data["commands"]["entries"]:
        verified = e.get("verified")
        if not isinstance(verified, dict):
            continue
        for v in VERSIONS:
            if isinstance(verified.get(v), dict):
                counts[v] += 1
    default_version = sorted(VERSIONS, key=lambda v: (-counts[v], int(v)))[0]
    return default_version, counts


def build():
    data = load_content()
    validate(data)
    data = assemble(data)
    default_version, version_verified_counts = compute_default_version(data)

    tpl_path = os.path.join(REPO, "template.html")
    with open(tpl_path, encoding="utf-8") as f:
        tpl = f.read()

    # The reference RECORDS leave the main island and become one island per
    # family; the family's _meta stays in the main island, because the About
    # panel and the tier banners have to be able to say what the build holds
    # without hydrating a megabyte to find out.
    ref = data["reference_commands"]
    ref_records = ref.get("commands") or []
    ref_families = split_reference_families(ref_records)
    ref_index = build_reference_index(ref_families)
    data["reference_commands"] = {"_meta": ref["_meta"], "_lazy": {
        "index_island": "mcr-ref-index",
        "families": [{"name": f, "island": "mcr-ref-" + f, "count": len(ref_families[f])}
                     for f in REFERENCE_FAMILIES],
        "note": ("the reference RECORDS are not in this island. Each family sits in its own "
                 "<script type=\"application/json\"> element and is parsed on first use, never "
                 "at boot; mcr-ref-index is the build-time inverted index the palette reads "
                 "before deciding which families to hydrate."),
    }}

    islands = [("mcr-data", "/*__DATA__*/", data),
               ("mcr-ref-index", "/*__REF_INDEX__*/", ref_index)]
    for family in REFERENCE_FAMILIES:
        islands.append(("mcr-ref-" + family,
                        "/*__REF_%s__*/" % family.upper(),
                        ref_families[family]))
    for _id, placeholder, _payload in islands:
        if placeholder not in tpl:
            sys.exit("FATAL: template.html has no %s placeholder" % placeholder)

    payloads = []
    for _id, _placeholder, obj in islands:
        payloads.append(escape_island(
            json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)))

    # CR-T-28. The evidence exporter and the About panel (CR-T-30) both print a
    # content fingerprint OFFLINE, on a jump box with no way to hash the file
    # against anything else. It was defined as the sha256 of exactly the bytes
    # inside <script id="mcr-data">...</script>; now that the corpus ships as
    # its own islands, it is the sha256 of EVERY island's bytes joined by a
    # newline in ISLAND DECLARATION ORDER — so a change to a mined record still
    # moves the fingerprint, which is the entire point of having one. Computed
    # here, before substitution, so the fingerprint is never a hash of a string
    # that contains itself, and embedded as a plain constant
    # (CONTENT_FINGERPRINT) rather than inside any island, because a hash inside
    # the thing it hashes is circular. qa.py Q1 checks the two independently:
    # it re-extracts every island from the shipped file, joins them the same
    # way, and compares.
    content_fingerprint = hashlib.sha256("\n".join(payloads).encode("utf-8")).hexdigest()

    out = tpl
    for (_id, placeholder, _obj), payload in zip(islands, payloads):
        out = out.replace(placeholder, payload)
    out = (out.replace("__APP_NAME__", APP_NAME)
              .replace("__VERSION__", APP_VERSION)
              .replace("__BUILT_DATE__", APP_BUILD_DATE)
              .replace("__CLASSIFICATION__", CLASSIFICATION)
              .replace("__CONTENT_FINGERPRINT__", content_fingerprint)
              .replace("__DEFAULT_VERSION__", default_version))

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
    print("  content fingerprint (sha256 of every island, in declaration order): %s"
          % content_fingerprint)
    print("  default version selector: RHEL %s (verified-receipt counts by version: %s)"
          % (default_version,
             ", ".join("RHEL %s=%d" % (v, version_verified_counts[v]) for v in VERSIONS)))
    ref_meta = ref.get("_meta") or {}
    print("  %d REFERENCE commands (tier: reference, not curated, not host-verified) "
          "across %d tools, %d of them evidence-eligible verbatim spans"
          % (len(ref_records), ref_meta.get("distinct_tools", 0),
             ref_meta.get("evidence_eligible_count", 0)))
    boot = len(payloads[0])
    print("  islands: %s"
          % ", ".join("%s %.2f MB" % (iid, len(p) / 1024.0 / 1024.0)
                      for (iid, _ph, _o), p in zip(islands, payloads)))
    print("  boot parses %.2f MB of %.2f MB (%.0f%%); the reference corpus is hydrated per family "
          "on first use, and %d index tokens decide which family that is"
          % (boot / 1024.0 / 1024.0, sum(len(p) for p in payloads) / 1024.0 / 1024.0,
             100.0 * boot / max(1, sum(len(p) for p in payloads)), len(ref_index["t"])))
    print("  %d command entries, %d tools, %d embedded STIG rules (%s), %d CCI mappings"
          % (len(data["commands"]["entries"]),
             len(data["tools"].get("tools", [])),
             n_rules,
             ", ".join("RHEL %s: %d" % (v, len(data["rules"][v].get("rules", []))) for v in VERSIONS),
             len(data["cci_nist"].get("cci", {}))))


if __name__ == "__main__":
    build()
