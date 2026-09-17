#!/usr/bin/env python3
"""parse_xccdf.py — the RULES and CCI datasets, from the pinned DISA sources.

Stdlib only. Deterministic: the same pinned sources in, byte-identical files out.

    python3 extract/parse_xccdf.py            # regenerate content/rules_rhel*.json
                                              # and content/cci_nist.json
    python3 extract/parse_xccdf.py --check    # regenerate into a temp dir and diff
                                              # against content/ (qa.py Q15)

WHAT THIS PRODUCES

  content/rules_rhel7.json    RHEL 7  V3R15   every rule in the benchmark
  content/rules_rhel8.json    RHEL 8  V2R8    every rule in the benchmark
  content/rules_rhel9.json    RHEL 9  V2R9    every rule in the benchmark
  content/rules_rhel10.json   RHEL 10 V1R2    every rule in the benchmark
  content/cci_nist.json       the CCI -> NIST SP 800-53 map, filtered to the CCIs
                              those four benchmarks actually cite

FULL, not partial. It replaces extract/make_skeleton_content.py, which embedded
only the handful of rules the skeleton command entries cited and stamped
_meta.partial so nobody could mistake it for coverage. The Founder ruled the size
ceiling unlimited on 2026-09-17 and ADR-001 §7.2's budget already assumed full
check and fix text, so every rule ships with its verbatim check-content and
fixtext. _meta.partial is now false in every release, and qa.py Q8 demands exact
parity with a live re-parse rather than accepting a declared shortfall.

Lineage: forked from the Etsy pipeline's build-rhel-stig.py (kept here as
extract/parse_xccdf_reference.py). clean() comes over unchanged. Three changes,
all required by ADR-001 §6.2:

  (a) ALL ident CCIs are collected. The original breaks on the first, and real
      rules carry more than one — RHEL 9 has rules citing 26 of them.
  (b) One file per release, so a single benchmark can be re-pinned without
      rebuilding the other three.
  (c) No cap() on check or fix text and no CURATED_II allow-list. The Etsy build
      trimmed to fit a size budget this product does not have; a trimmed check
      text is not evidence.

DETERMINISM, AND WHY THERE IS NO WALL CLOCK IN HERE. Q15 re-runs this extractor
and diffs the result against content/. If any field came from datetime.today(),
that gate would pass on the day of the build and fail every day after. So
extraction is a pure function of the pinned inputs: _meta.extracted_on carries
the date of the pinned SOURCE SET (stig-src/SOURCES.md, 2026-09-17), not the date
the script ran, and it changes only when the pins change.

ADR-001 §6.3: generated files are never hand-edited. Fix the extractor, re-run.
"""

import hashlib
import html as htmllib
import json
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STIG_SRC = os.path.join(REPO, "stig-src")
CONTENT = os.path.join(REPO, "content")

NS = {"x": "http://checklists.nist.gov/xccdf/1.1"}
CCI_NS = {"c": "http://iase.disa.mil/cci"}
GENERATOR = "extract/parse_xccdf.py"

# The date stig-src/SOURCES.md records for the whole pinned set. It is the only
# date in the emitted files, and it moves only in a dep-bump that re-pins the XML.
PINS_RETRIEVED_ON = "2026-09-17"

# RHEL version -> pinned XCCDF filename (must match stig-src/SHA256SUMS).
XCCDF = {
    "7": "U_RHEL_7_STIG_V3R15_Manual-xccdf.xml",
    "8": "U_RHEL_8_STIG_V2R8_Manual-xccdf.xml",
    "9": "U_RHEL_9_STIG_V2R9_Manual-xccdf.xml",
    "10": "U_RHEL_10_STIG_V1R2_Manual-xccdf.xml",
}
CCI_LIST = "U_CCI_List.xml"

# RHEL 7 is SUNSET at DISA (stig-src/SOURCES.md); the UI renders that label
# unconditionally, so the dataset has to carry the fact.
SUNSET = {"7": True, "8": False, "9": False, "10": False}

SEVERITY_TO_CAT = {"high": "I", "medium": "II", "low": "III"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def clean(s):
    """Strip XCCDF's embedded markup and unescape entities (Etsy pipeline, verbatim)."""
    if s is None:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    s = s.replace("\r\n", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pins():
    """stig-src/SHA256SUMS is the source of record. Refuse to parse an unpinned file.

    This runs before a single byte is read out of the XML. An extractor that will
    parse whatever it finds on disk is not a pipeline, it is a rumour.
    """
    sums = {}
    path = os.path.join(STIG_SRC, "SHA256SUMS")
    if not os.path.exists(path):
        sys.exit("FATAL: stig-src/SHA256SUMS is missing — refusing to parse unpinned sources")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            digest, name = line.split(None, 1)
            sums[name.strip()] = digest
    bad = []
    for name in list(XCCDF.values()) + [CCI_LIST]:
        p = os.path.join(STIG_SRC, name)
        if not os.path.exists(p):
            bad.append(name + ": missing")
            continue
        got = sha256_file(p)
        if sums.get(name) != got:
            bad.append("%s: sha256 %s != pinned %s" % (name, got[:16], (sums.get(name) or "?")[:16]))
    if bad:
        sys.exit("FATAL: stig-src pin check failed:\n  " + "\n  ".join(bad))
    return sums


def filename_version_tag(fname):
    m = re.search(r"_(V\d+R\d+)_", fname)
    return m.group(1) if m else ""


def release_info(root, fname):
    """Read the benchmark's own identity out of the XML, then cross-check the filename.

    <version>3</version> plus <plain-text id="release-info">Release: 15 Benchmark
    Date: 24 Jul 2024</plain-text> is V3R15, benchmark-dated 24 Jul 2024. The
    filename says V3R15 too — if the two ever disagree, the file on disk is not
    the file the pin claims, and that is a stop, not a warning.
    """
    ver_el = root.find("x:version", NS)
    major = clean(ver_el.text) if ver_el is not None else ""
    raw = ""
    for pt in root.findall("x:plain-text", NS):
        if pt.get("id") == "release-info":
            raw = clean(pt.text)
            break
    m = re.search(r"Release:\s*([0-9.]+)", raw)
    release = m.group(1) if m else ""
    m = re.search(r"Benchmark Date:\s*(.+)$", raw)
    benchmark_date = m.group(1).strip() if m else ""
    tag = "V%sR%s" % (major, release) if major and release else ""
    from_name = filename_version_tag(fname)
    if tag and from_name and tag != from_name:
        sys.exit("FATAL: %s declares %s inside the XML but the pinned filename says %s"
                 % (fname, tag, from_name))
    status_el = root.find("x:status", NS)
    return {
        "benchmark_id": root.get("id") or "",
        "version": tag or from_name,
        "release": release,
        "benchmark_date": benchmark_date,
        "release_info": raw,
        "status": clean(status_el.text) if status_el is not None else "",
        "status_date": (status_el.get("date") if status_el is not None else "") or "",
    }


# ---------------------------------------------------------------------------
# one release
# ---------------------------------------------------------------------------

def parse_release(version):
    """Parse one pinned XCCDF in full. Returns (meta, rules[]) in document order.

    Document order is the benchmark's own order, which is STIG ID order. It is
    kept rather than sorted so a reviewer can read the emitted file alongside the
    official STIG Viewer and follow the same sequence.
    """
    fname = XCCDF[version]
    path = os.path.join(STIG_SRC, fname)
    root = ET.parse(path).getroot()
    info = release_info(root, fname)

    rules = []
    seen = {}
    for g in root.findall("x:Group", NS):
        rule = g.find("x:Rule", NS)
        if rule is None:
            continue
        ver_el = rule.find("x:version", NS)
        stig_id = clean(ver_el.text) if ver_el is not None else ""
        if not stig_id:
            sys.exit("FATAL: RHEL %s: %s has a Rule with no <version> (STIG ID)" % (version, g.get("id")))
        if stig_id in seen:
            sys.exit("FATAL: RHEL %s: duplicate STIG ID %s — the dataset is keyed by it" % (version, stig_id))
        seen[stig_id] = True

        # ADR-001 §6.2 change (a): collect ALL ident CCIs, never break on the first.
        ccis = []
        for ident in rule.findall("x:ident", NS):
            if "cci" in (ident.get("system") or "").lower():
                val = (ident.text or "").strip()
                if val and val not in ccis:
                    ccis.append(val)

        severity = rule.get("severity") or ""
        cat = SEVERITY_TO_CAT.get(severity)
        if cat is None:
            sys.exit("FATAL: RHEL %s %s: severity '%s' is not high/medium/low"
                     % (version, stig_id, severity))

        title_el = rule.find("x:title", NS)
        chk_el = rule.find("x:check/x:check-content", NS)
        fix_el = rule.find("x:fixtext", NS)
        rules.append({
            "v": g.get("id"),
            "i": stig_id,
            "rid": rule.get("id"),
            "c": cat,
            "t": clean(title_el.text) if title_el is not None else "",
            "cci": ccis,
            "n": [],                       # filled from the CCI map, below
            "chk": clean(chk_el.text) if chk_el is not None else "",
            "fix": clean(fix_el.text) if fix_el is not None else "",
        })

    cat_counts = {c: sum(1 for r in rules if r["c"] == c) for c in ("I", "II", "III")}
    label = "RHEL %s · STIG %s · benchmark %s" % (version, info["version"], info["benchmark_date"])
    meta = {
        "rhel_version": version,
        "version": info["version"],
        "release": label,
        "release_info": info["release_info"],
        "benchmark_id": info["benchmark_id"],
        "benchmark_date": info["benchmark_date"],
        "status": info["status"],
        "status_date": info["status_date"],
        "source_file": fname,
        "sha256": sha256_file(path),
        "sunset": SUNSET[version],
        "generator": GENERATOR,
        "partial": False,
        "rule_count": len(rules),
        "source_rule_count": len(rules),
        "cat_counts": cat_counts,
        "severity_map": SEVERITY_TO_CAT,
        "extracted_on": PINS_RETRIEVED_ON,
        "extracted_on_note": "the date of the pinned source set in stig-src/SOURCES.md, not the date "
                             "the extractor ran — extraction is a pure function of the pins, so a "
                             "re-run is byte-identical (qa.py Q15)",
        "license_class": "verbatim-ok",
        "source": {
            "title": "DISA Security Technical Implementation Guide, " + label,
            "url_or_man": "stig-src/" + fname,
            "version": info["version"],
            "retrieved_on": PINS_RETRIEVED_ON,
            "license_class": "verbatim-ok",
        },
    }
    return meta, rules


# ---------------------------------------------------------------------------
# CCI -> NIST SP 800-53 (CR-T-27's build_cci_map, folded in here)
# ---------------------------------------------------------------------------

def build_cci_map(referenced):
    """DISA CCI list -> {cci: {nist, rev, text}}, filtered to the CCIs actually cited.

    ADR-001 §5.4: the four pinned benchmarks cite a small fraction of the list, and
    shipping the rest would be dead weight in an air-gapped single file. The full
    list's item count is recorded in _meta so the About panel can say what
    fraction is embedded rather than implying the whole list is present.

    Where a CCI carries several NIST references, the one with the highest revision
    number wins — that is Rev 5 today. qa.py Q11 re-derives the same choice from
    the same XML through its own independent parse and diffs the result.
    """
    path = os.path.join(STIG_SRC, CCI_LIST)
    root = ET.parse(path).getroot()

    publish_date = ""
    md = root.find("c:metadata", CCI_NS)
    if md is not None:
        pv = md.find("c:publishdate", CCI_NS)
        publish_date = (pv.text or "").strip() if pv is not None else ""

    out = {}
    total = 0
    for item in root.findall(".//c:cci_item", CCI_NS):
        total += 1
        cci = item.get("id")
        if cci not in referenced:
            continue
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
                best = (vnum, idx, ref.get("version") or "")
        definition = item.find("c:definition", CCI_NS)
        out[cci] = {
            "nist": [best[1]] if best else [],
            "rev": best[2] if best else None,
            "text": clean(definition.text) if definition is not None else "",
        }

    missing = sorted(c for c in referenced if c not in out)
    if missing:
        sys.exit("FATAL: CCI(s) referenced by a pinned XCCDF are absent from %s: %s"
                 % (CCI_LIST, ", ".join(missing)))
    no_nist = sorted(c for c, v in out.items() if not v["nist"])

    meta = {
        "generator": GENERATOR,
        "source_file": CCI_LIST,
        "sha256": sha256_file(path),
        "cci_list_version": publish_date,
        "entry_count": len(out),
        "source_cci_count": total,
        "filtered_to": "the %d of %d CCI items cited by the four pinned RHEL benchmarks "
                       "(ADR-001 §5.4)" % (len(out), total),
        "unmapped_cci": no_nist,
        "extracted_on": PINS_RETRIEVED_ON,
        "license_class": "verbatim-ok",
        "source": {
            "title": "DISA Control Correlation Identifier (CCI) List, publish date " + publish_date,
            "url_or_man": "stig-src/" + CCI_LIST,
            "version": publish_date,
            "retrieved_on": PINS_RETRIEVED_ON,
            "license_class": "verbatim-ok",
        },
    }
    return meta, out


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def generate(dest_dir):
    verify_pins()
    releases = {}
    referenced = set()
    for version in ("7", "8", "9", "10"):
        meta, rules = parse_release(version)
        releases[version] = (meta, rules)
        for r in rules:
            referenced.update(r["cci"])

    cci_meta, cci_map = build_cci_map(referenced)

    written = []
    for version in ("7", "8", "9", "10"):
        meta, rules = releases[version]
        for r in rules:
            nist = []
            for c in r["cci"]:
                for n in cci_map.get(c, {}).get("nist", []):
                    if n not in nist:
                        nist.append(n)
            r["n"] = nist
        meta["cci_list_version"] = cci_meta["cci_list_version"]
        meta["distinct_cci_count"] = len(set(c for r in rules for c in r["cci"]))
        path = os.path.join(dest_dir, "rules_rhel%s.json" % version)
        write_json(path, {"_meta": meta, "rules": rules})
        written.append(path)

    path = os.path.join(dest_dir, "cci_nist.json")
    write_json(path, {"_meta": cci_meta, "cci": cci_map})
    written.append(path)
    return written


def main():
    if "--check" in sys.argv:
        tmp = tempfile.mkdtemp(prefix="mcr-xccdf-")
        try:
            written = generate(tmp)
            drift = []
            for path in written:
                name = os.path.basename(path)
                live = os.path.join(CONTENT, name)
                if not os.path.exists(live):
                    drift.append(name + ": absent from content/")
                elif open(live, encoding="utf-8").read() != open(path, encoding="utf-8").read():
                    drift.append(name + ": differs from a fresh extractor run")
            if drift:
                print("GENERATED-FILE DRIFT (%s):" % GENERATOR)
                for d in drift:
                    print("  " + d)
                sys.exit(1)
            print("%s: %d generated file(s) match a fresh extractor run" % (GENERATOR, len(written)))
            sys.exit(0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    written = generate(CONTENT)
    for path in written:
        print("wrote %s (%d bytes)" % (os.path.relpath(path, REPO), os.path.getsize(path)))
    for version in ("7", "8", "9", "10"):
        with open(os.path.join(CONTENT, "rules_rhel%s.json" % version), encoding="utf-8") as f:
            meta = json.load(f)["_meta"]
        print("  RHEL %-2s %-6s %4d rules  (CAT I %3d / II %3d / III %3d)  %d distinct CCIs"
              % (version, meta["version"], meta["rule_count"], meta["cat_counts"]["I"],
                 meta["cat_counts"]["II"], meta["cat_counts"]["III"], meta["distinct_cci_count"]))


if __name__ == "__main__":
    main()
