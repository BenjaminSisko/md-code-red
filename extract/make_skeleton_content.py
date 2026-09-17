#!/usr/bin/env python3
"""make_skeleton_content.py — emit the GENERATED content families for MD CODE RED.

Stdlib only. Deterministic: same pinned sources in, byte-identical files out.

    python3 extract/make_skeleton_content.py            # regenerate content/
    python3 extract/make_skeleton_content.py --check    # regenerate into a temp
                                                        # dir and diff (qa.py Q15)

SCOPE AND LIFETIME (read this before extending it)
--------------------------------------------------
This is the CR-T-02 stand-in for two extractors that ADR-001 §4 assigns to later
tasks, and it is deliberately smaller than either:

  * `extract/parse_xccdf.py`  (CR-T-07) — full per-release RULES datasets.
  * `extract/build_cci_map.py` (CR-T-27) — the filtered CCI -> 800-53 map.

Until those land, `content/rules_rhel<N>.json` is an honest PARTIAL dataset: it
carries only the rules named in INCLUDE below (the ones tonight's skeleton
command entries actually cite), parsed from the pinned XCCDF, never hand-typed.
Every emitted file declares `_meta.partial` and `_meta.source_rule_count`, so
qa.py Q8 can compare the embedded count against a live re-parse and still say
something true instead of pretending to full coverage. When CR-T-07 lands, this
script is deleted and `_meta.partial` goes away with it.

ADR-001 §6.3: generated files are never hand-edited. Fix the extractor, re-run.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import html as htmllib
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STIG_SRC = os.path.join(REPO, "stig-src")
CONTENT = os.path.join(REPO, "content")
NS = {"x": "http://checklists.nist.gov/xccdf/1.1"}
CCI_NS = {"c": "http://iase.disa.mil/cci"}
GENERATOR = "extract/make_skeleton_content.py"

# RHEL version -> pinned XCCDF filename (must match stig-src/SHA256SUMS).
XCCDF = {
    "7": "U_RHEL_7_STIG_V3R15_Manual-xccdf.xml",
    "8": "U_RHEL_8_STIG_V2R8_Manual-xccdf.xml",
    "9": "U_RHEL_9_STIG_V2R9_Manual-xccdf.xml",
    "10": "U_RHEL_10_STIG_V1R2_Manual-xccdf.xml",
}
CCI_LIST = "U_CCI_List.xml"

# RHEL 7 is SUNSET at DISA (SOURCES.md); the UI renders that label unconditionally.
SUNSET = {"7": True, "8": False, "9": False, "10": False}

# The pinned partial: STIG IDs cited by content/commands.json tonight.
# One line per rule, so a reviewer can see exactly what the partial covers.
INCLUDE = {
    "7": ["RHEL-07-040520", "RHEL-07-020230"],
    "8": ["RHEL-08-040101", "RHEL-08-040170"],
    "9": ["RHEL-09-251015", "RHEL-09-211050", "RHEL-09-211040"],
    "10": ["RHEL-10-200531", "RHEL-10-700960", "RHEL-10-500000"],
}


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
    """stig-src/SHA256SUMS is the source of record. Refuse to parse an unpinned file."""
    sums = {}
    with open(os.path.join(STIG_SRC, "SHA256SUMS")) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            digest, name = line.split(None, 1)
            sums[name.strip()] = digest
    bad = []
    for name in list(XCCDF.values()) + [CCI_LIST]:
        path = os.path.join(STIG_SRC, name)
        if not os.path.exists(path):
            bad.append(name + ": missing")
            continue
        got = sha256_file(path)
        if sums.get(name) != got:
            bad.append("%s: sha256 %s != pinned %s" % (name, got[:16], (sums.get(name) or "?")[:16]))
    if bad:
        sys.exit("FATAL: stig-src pin check failed:\n  " + "\n  ".join(bad))
    return sums


def release_label(version, benchmark_date, tag):
    return "RHEL %s · STIG %s · benchmark %s" % (version, tag, benchmark_date)


def version_tag(fname):
    m = re.search(r"_(V\d+R\d+)_", fname)
    return m.group(1) if m else "?"


def parse_release(version):
    """Parse one pinned XCCDF. Returns (meta, {stig_id: rule_record}, source_rule_count)."""
    fname = XCCDF[version]
    path = os.path.join(STIG_SRC, fname)
    root = ET.parse(path).getroot()
    benchmark_date = ""
    for pt in root.findall("x:plain-text", NS):
        m = re.search(r"Benchmark Date:\s*(.+)$", clean(pt.text))
        if m:
            benchmark_date = m.group(1).strip()
            break
    rules = {}
    total = 0
    for g in root.findall("x:Group", NS):
        rule = g.find("x:Rule", NS)
        if rule is None:
            continue
        total += 1
        ver = rule.find("x:version", NS)
        stig_id = clean(ver.text) if ver is not None else ""
        if stig_id not in INCLUDE[version]:
            continue
        # ADR-001 §6.2 change (a): collect ALL ident CCIs, never break on the first.
        ccis = []
        for ident in rule.findall("x:ident", NS):
            if "cci" in (ident.get("system") or "").lower():
                val = (ident.text or "").strip()
                if val and val not in ccis:
                    ccis.append(val)
        chk_el = rule.find("x:check/x:check-content", NS)
        fix_el = rule.find("x:fixtext", NS)
        rules[stig_id] = {
            "v": g.get("id"),
            "i": stig_id,
            "rid": rule.get("id"),
            "c": {"high": "I", "medium": "II", "low": "III"}.get(rule.get("severity"), "?"),
            "t": clean(rule.find("x:title", NS).text),
            "cci": ccis,
            "n": [],  # filled from the CCI map below
            "chk": clean(chk_el.text) if chk_el is not None else "",
            "fix": clean(fix_el.text) if fix_el is not None else "",
        }
    missing = [i for i in INCLUDE[version] if i not in rules]
    if missing:
        sys.exit("FATAL: RHEL %s: pinned STIG ID(s) not found in %s: %s"
                 % (version, fname, ", ".join(missing)))
    meta = {
        "rhel_version": version,
        "version": version_tag(fname),
        "release": release_label(version, benchmark_date, version_tag(fname)),
        "benchmark_date": benchmark_date,
        "source_file": fname,
        "sha256": sha256_file(path),
        "sunset": SUNSET[version],
        "generator": GENERATOR,
        "partial": True,
        "partial_reason": "CR-T-02 skeleton: only rules cited by content/commands.json. "
                          "extract/parse_xccdf.py (CR-T-07) emits the full dataset.",
        "rule_count": len(rules),
        "source_rule_count": total,
        "license_class": "verbatim-ok",
        "source": {
            "title": "DISA Security Technical Implementation Guide, " + release_label(version, benchmark_date, version_tag(fname)),
            "url_or_man": "stig-src/" + fname,
            "version": version_tag(fname),
            "retrieved_on": "2026-09-17",
            "license_class": "verbatim-ok",
        },
    }
    return meta, rules, total


def load_cci_map(referenced):
    """DISA CCI list -> {cci: {nist: [...], text: "..."}}, filtered to referenced CCIs."""
    path = os.path.join(STIG_SRC, CCI_LIST)
    root = ET.parse(path).getroot()
    meta_version = ""
    md = root.find("c:metadata", CCI_NS)
    if md is not None:
        pv = md.find("c:publishdate", CCI_NS)
        meta_version = (pv.text or "").strip() if pv is not None else ""
    out = {}
    for item in root.findall(".//c:cci_item", CCI_NS):
        cci = item.get("id")
        if cci not in referenced:
            continue
        best = None
        for ref in item.findall("c:references/c:reference", CCI_NS):
            title = (ref.get("title") or "")
            if "800-53" not in title or "800-53A" in title:
                continue
            ver = ref.get("version") or "0"
            idx = (ref.get("index") or "").strip()
            if not idx:
                continue
            try:
                vnum = int(re.sub(r"\D", "", ver) or 0)
            except ValueError:
                vnum = 0
            if best is None or vnum > best[0]:
                best = (vnum, idx, ver)
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
    meta = {
        "generator": GENERATOR,
        "source_file": CCI_LIST,
        "sha256": sha256_file(path),
        "cci_list_version": meta_version,
        "entry_count": len(out),
        "filtered_to": "CCIs referenced by the pinned XCCDF rules embedded in content/rules_rhel*.json",
        "license_class": "verbatim-ok",
        "source": {
            "title": "DISA Control Correlation Identifier (CCI) List, publish date " + meta_version,
            "url_or_man": "stig-src/" + CCI_LIST,
            "version": meta_version,
            "retrieved_on": "2026-09-17",
            "license_class": "verbatim-ok",
        },
    }
    return meta, out


def flags_skeleton(version):
    """Empty per-version flag dictionary.

    The FLAGS dictionaries come from the box (`man -P cat` / `--help`) on a real
    host of that RHEL version — CR-T-09 builds the extractor, CR-T-10/11/12 run
    it. No host has been read yet, so these files are empty by design rather
    than populated with anything we cannot attribute to a running binary.
    """
    return {
        "_meta": {
            "rhel_version": version,
            "host": None,
            "patch_level": None,
            "captured_on": None,
            "generator": "extract/extract_rhel_flags.py",
            "status": "pending — no RHEL %s host read yet (CR-T-09/10/11/12)" % version,
            "license_class": "paraphrase-only",
            "source": {
                "title": "man pages and --help output of the installed binaries on a RHEL %s host" % version,
                "url_or_man": "man -P cat <section> <tool>; <tool> --help",
                "version": "not captured",
                "retrieved_on": None,
                "license_class": "paraphrase-only",
            },
        },
        "clis": {},
    }


def expected_output_skeleton():
    """Expected output is captured, never typed (ADR-001 §6.5). None captured yet."""
    return {
        "_meta": {
            "generator": "extract/import_captures.py",
            "status": "pending — no capture files under content-src/captures/ (CR-T-34)",
            "keyed_by": "entry_id|stig_id|rhel_version",
            "capture_count": 0,
        },
        "captures": {},
    }


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def generate(dest_dir):
    verify_pins()
    written = []
    referenced = set()
    releases = {}
    for version in ("7", "8", "9", "10"):
        meta, rules, total = parse_release(version)
        releases[version] = (meta, rules)
        for r in rules.values():
            referenced.update(r["cci"])
    cci_meta, cci_map = load_cci_map(referenced)
    for version, (meta, rules) in releases.items():
        for r in rules.values():
            nist = []
            for c in r["cci"]:
                for n in cci_map.get(c, {}).get("nist", []):
                    if n not in nist:
                        nist.append(n)
            r["n"] = nist
        meta["cci_list_version"] = cci_meta["cci_list_version"]
        path = os.path.join(dest_dir, "rules_rhel%s.json" % version)
        write_json(path, {"_meta": meta, "rules": [rules[i] for i in INCLUDE[version]]})
        written.append(path)
        path = os.path.join(dest_dir, "flags_rhel%s.json" % version)
        write_json(path, flags_skeleton(version))
        written.append(path)
    path = os.path.join(dest_dir, "cci_nist.json")
    write_json(path, {"_meta": cci_meta, "cci": cci_map})
    written.append(path)
    path = os.path.join(dest_dir, "expected_output.json")
    write_json(path, expected_output_skeleton())
    written.append(path)
    return written


def main():
    if "--check" in sys.argv:
        tmp = tempfile.mkdtemp(prefix="mcr-gen-")
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
                print("GENERATED-FILE DRIFT:")
                for d in drift:
                    print("  " + d)
                sys.exit(1)
            print("generated files match a fresh extractor run (%d files)" % len(written))
            sys.exit(0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    written = generate(CONTENT)
    for path in written:
        print("wrote %s (%d bytes)" % (os.path.relpath(path, REPO), os.path.getsize(path)))


if __name__ == "__main__":
    main()
