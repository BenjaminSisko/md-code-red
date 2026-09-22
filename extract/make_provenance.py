#!/usr/bin/env python3
"""make_provenance.py -- REL-2026-09-18-001 item 4: the build-provenance
manifest for a tagged release.

Stdlib only.

    python3 build.py                          # build the artifact first
    python3 extract/make_provenance.py        # emit dist/md-code-red_<version>.provenance.json
    python3 extract/make_provenance.py --commit <full git sha>   # at tag time

WHY THIS INSTEAD OF AN SPDX/CycloneDX SBOM. MD CODE RED has zero runtime
dependencies (no npm, no pip, no CDN, no framework -- ADR-001 section 11.D, the
air-gap law, Q2) and its build tooling is stdlib-only Python plus a handful
of hand-written extractors, also stdlib-only. A traditional package-dependency
SBOM for this artifact would be formally correct and substantively empty. The
readiness assessment (REL-2026-09-18-001, item 4) recommends this instead as
"the minimum honest SBOM for this artifact": a manifest naming the four
pinned STIG sources with exact versions/dates/hashes, the CCI List pin, the
content roster (who is authorized as SME/QA), the flag-dictionary provenance
per RHEL version, the receipt/capture counts, the build toolchain, and the
chain of review documents this candidate cleared -- the things that actually
vary release to release and actually need to be checked. A formal SPDX/
CycloneDX document remains warranted at GA if a customer's ATO package
requires one in that format; not before.

DETERMINISM. Every field below is read from a file already committed to the
repo, or computed from the built artifact this script is pointed at. The one
field that is NOT reproducible before the tag exists is `git_commit`: this
script does not know its own repo's commit until the integrator merges and
tags it (this worktree's HEAD is a release *branch* commit, not the merge
commit Eli/Devon eventually tag). Rather than guess, this script writes the
literal string "TAG_COMMIT_PLACEHOLDER" unless `--commit <sha>` is given, and
the tag procedure documents that the integrator re-runs this script with
--commit right after the merge, once the real merge-commit sha is known, and
re-commits the regenerated manifest as part of the tag step. Every other
field is byte-for-byte reproducible from the same committed sources.

This script never re-derives content the extractors already own (RULES,
FLAGS, CCI_NIST) -- it reads their own _meta blocks and stig-src/'s pin files,
the same "independent source parse, not a re-use of extract/" discipline
qa.py's verify_pins()/parse_source() already follow, so a provenance claim
here is never just an echo of a claim the artifact makes about itself.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
CONTENT = os.path.join(REPO, "content")
CONTENT_SRC = os.path.join(REPO, "content-src")
STIG_SRC = os.path.join(REPO, "stig-src")
VERSIONS = ("7", "8", "9", "10")
EXPECTED_ISLANDS = ("mcr-data", "mcr-ref-index", "mcr-ref-stig_rules",
                    "mcr-ref-raw_captures", "mcr-ref-redhat_guides")

XCCDF = {
    "7": "U_RHEL_7_STIG_V3R15_Manual-xccdf.xml",
    "8": "U_RHEL_8_STIG_V2R8_Manual-xccdf.xml",
    "9": "U_RHEL_9_STIG_V2R9_Manual-xccdf.xml",
    "10": "U_RHEL_10_STIG_V1R2_Manual-xccdf.xml",
}
CCI_LIST_FILE = "U_CCI_List.xml"

PLACEHOLDER_COMMIT = "TAG_COMMIT_PLACEHOLDER"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_build_constants():
    """Read APP_VERSION/APP_BUILD_DATE out of build.py without importing it.

    Same discipline as qa.py's load_build_constants(): no import, no code path
    shared with build.py, so a manifest bug and a build bug cannot both hide
    behind one shared implementation.
    """
    with open(os.path.join(REPO, "build.py"), encoding="utf-8") as fh:
        src = fh.read()
    out = {}
    for key in ("APP_VERSION", "APP_BUILD_DATE"):
        m = re.search(r'^%s\s*=\s*"([^"]+)"' % key, src, re.M)
        out[key] = m.group(1) if m else None
    return out


def find_artifact(version):
    path = os.path.join(DIST, "md-code-red_%s.html" % version)
    if not os.path.exists(path):
        sys.exit("FATAL: %s does not exist -- run `git clean -fdx dist && "
                 "python3 build.py` first"
                  % os.path.relpath(path, REPO))
    return path


def content_fingerprint_from_artifact(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    islands = re.findall(
        r'<script id="([^"]+)" type="application/json">(.*?)</script>',
        html, re.S)
    found_ids = tuple(island_id for island_id, _payload in islands)
    if found_ids != EXPECTED_ISLANDS:
        sys.exit("FATAL: JSON island order in %s is %r, expected %r"
                 % (path, found_ids, EXPECTED_ISLANDS))
    return sha256_bytes("\n".join(payload for _island_id, payload in islands).encode("utf-8"))


def load_sha256sums():
    path = os.path.join(STIG_SRC, "SHA256SUMS")
    sums = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                digest, name = line.split(None, 1)
                sums[name.strip()] = digest
    return sums


def parse_sources_md():
    """stig-src/SOURCES.md's pin table -> {row_key: {benchmark_date, zip_url, zip_sha256, status}}.

    Independent of qa.py on purpose (this manifest is meant to be checkable
    against the repo by someone who has never read qa.py). Reads the markdown
    table only; the zip sha256 recorded here is the download-time pin, not
    the same value as the extracted XML's own sha256 in SHA256SUMS -- both are
    reported, and they are deliberately different numbers (one hashes the
    DISA zip, the other the XML this repo actually parses).
    """
    path = os.path.join(STIG_SRC, "SOURCES.md")
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 6 or cells[0] in ("RHEL",):
                continue
            key, version, bench_date, zip_url, zip_sha256, status = cells[:6]
            rows[key] = {
                "version": version,
                "benchmark_date": bench_date,
                "zip_url": zip_url,
                "zip_sha256": zip_sha256,
                "status": status,
            }
    return rows


def stig_pins(sha256sums, sources_rows):
    pins = {}
    for v in VERSIONS:
        xml_name = XCCDF[v]
        row = sources_rows.get(v, {})
        pins[v] = {
            "benchmark_version": row.get("version"),
            "benchmark_date": row.get("benchmark_date"),
            "xccdf_file": xml_name,
            "xccdf_sha256": sha256sums.get(xml_name),
            "zip_url": row.get("zip_url"),
            "zip_sha256": row.get("zip_sha256"),
            "status": row.get("status"),
        }
    return pins


def cci_list_pin(sha256sums, sources_rows):
    row = sources_rows.get("CCI", {})
    cci_meta = {}
    cci_path = os.path.join(CONTENT, "cci_nist.json")
    if os.path.exists(cci_path):
        cci_meta = load_json(cci_path).get("_meta", {})
    return {
        "list_date": cci_meta.get("cci_list_version") or row.get("version"),
        "xccdf_file": CCI_LIST_FILE,
        "xccdf_sha256": sha256sums.get(CCI_LIST_FILE),
        "zip_url": row.get("zip_url"),
        "zip_sha256": row.get("zip_sha256"),
        "entry_count": cci_meta.get("entry_count"),
        "filtered_from": cci_meta.get("source_cci_count"),
    }


def flag_dictionary_provenance():
    out = {}
    for v in VERSIONS:
        path = os.path.join(CONTENT, "flags_rhel%s.json" % v)
        if not os.path.exists(path):
            out[v] = None
            continue
        meta = load_json(path).get("_meta", {})
        out[v] = {
            "host": meta.get("host"),
            "redhat_release": meta.get("redhat_release"),
            "kernel": meta.get("kernel"),
            "generator": meta.get("generator"),
            "extractor_version": meta.get("extractor_version"),
            "status": meta.get("status"),
            "container_image_digest": meta.get("container_image_digest"),
        }
    return out


def receipt_and_capture_counts():
    commands = load_json(os.path.join(CONTENT, "commands.json"))
    receipts = 0
    for e in commands.get("entries", []):
        for _, val in (e.get("verified") or {}).items():
            if isinstance(val, dict):
                receipts += 1
    expected = load_json(os.path.join(CONTENT, "expected_output.json"))
    captures = len(expected.get("captures", {}))
    return receipts, captures


def roster():
    path = os.path.join(CONTENT_SRC, "roster.json")
    d = load_json(path)
    return [{"name": p.get("name"), "roles": p.get("roles")} for p in d.get("people", [])]


def flag_coverage_baseline_summary():
    path = os.path.join(CONTENT_SRC, "flag_coverage_baseline.json")
    d = load_json(path)
    return {
        "accepted_on": d.get("_accepted_on"),
        "accepted_by": d.get("_accepted_by"),
        "retire_owner": d.get("_retire_owner"),
        "retire_by": d.get("_retire_by"),
        "ticket": d.get("_ticket"),
    }


def extractor_versions():
    versions = {}
    flags_path = os.path.join(REPO, "extract", "extract_flags.py")
    with open(flags_path, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'^EXTRACTOR_VERSION\s*=\s*"([^"]+)"', src, re.M)
    versions["extract/extract_flags.py"] = m.group(1) if m else None
    # parse_xccdf.py and make_pending_skeletons.py declare no version constant
    # of their own today; recorded as null rather than guessed.
    versions["extract/parse_xccdf.py"] = None
    versions["extract/make_pending_skeletons.py"] = None
    return versions


def node_version():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def review_lineage(version):
    """Return release evidence pointers without claiming a review occurred.

    The manifest generator also runs on development builds, before a release
    packet or tag exists.  Keep these values version-derived and procedural:
    version-specific reports may record a result, while this manifest only
    names the evidence that a publisher must supply.  Historical governance
    records remain useful as the baseline, but are not represented as approval
    of the current version.
    """
    return {
        "release_version": version,
        "change_record": "docs/CHANGELOG.md -- heading for %s" % version,
        "required_release_evidence": [
            "docs/BQP_SUMMARY_%s.md" % version,
            "docs/QA_REPORT_%s.md" % version,
            "docs/SECURITY_REVIEW_%s.md" % version,
            "docs/RELEASE_REPORT_%s.md" % version,
        ],
        "independent_review": (
            "Exact-head regression, security, and content review must be recorded "
            "for this version before publication; this manifest does not itself "
            "assert that those reviews passed."
        ),
        "governance_baseline": {
            "readiness_assessment": "REL-2026-09-18-001",
            "sar": "SAR-v1.0.0-alpha-candidate-01abbc3-2026-09-18",
            "ter": "TER-v1.0.0-alpha-candidate-01abbc3-2026-09-18",
            "gate3_whole_tree": "ENG-2026-09-18-002",
            "gate3_qa_py": "ENG-2026-09-18-001",
            "adr": "ADR-001-engine-and-content, section 9, 2026-09-18",
            "pilot_sop": "MD CODE RED v1.0.0-alpha Pilot Standard Operating Procedure, 2026-09-18",
        },
    }


def build_manifest(commit):
    consts = load_build_constants()
    version = consts["APP_VERSION"]
    artifact_path = find_artifact(version)
    artifact_sha256 = sha256_file(artifact_path)
    fingerprint = content_fingerprint_from_artifact(artifact_path)

    sha256sums = load_sha256sums()
    sources_rows = parse_sources_md()
    receipts, captures = receipt_and_capture_counts()

    return {
        "version": version,
        "build_date": consts["APP_BUILD_DATE"],
        "git_commit": commit or PLACEHOLDER_COMMIT,
        "artifact": {
            "filename": os.path.basename(artifact_path),
            "sha256": artifact_sha256,
            "bytes": os.path.getsize(artifact_path),
        },
        "content_fingerprint": fingerprint,
        "stig_pins": stig_pins(sha256sums, sources_rows),
        "cci_list": cci_list_pin(sha256sums, sources_rows),
        "flag_dictionaries": flag_dictionary_provenance(),
        "receipt_count": receipts,
        "capture_count": captures,
        "roster": roster(),
        "flag_coverage_baseline": flag_coverage_baseline_summary(),
        "toolchain": {
            "python3": sys.version.split()[0],
            "node": node_version(),
            "extractors": extractor_versions(),
        },
        "review_lineage": review_lineage(version),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", default=None,
                     help="full git sha of the tagged merge commit; omit to write "
                          "%s (the integrator fills this in after merge)" % PLACEHOLDER_COMMIT)
    args = ap.parse_args()

    manifest = build_manifest(args.commit)
    version = manifest["version"]
    dest = os.path.join(DIST, "md-code-red_%s.provenance.json" % version)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True, ensure_ascii=True)
        f.write("\n")
    print("wrote %s" % os.path.relpath(dest, REPO))
    print("  git_commit: %s%s" % (manifest["git_commit"],
          "  <- placeholder, integrator re-runs with --commit after merge"
          if manifest["git_commit"] == PLACEHOLDER_COMMIT else ""))
    print("  artifact sha256: %s" % manifest["artifact"]["sha256"])
    print("  content fingerprint: %s" % manifest["content_fingerprint"])


if __name__ == "__main__":
    main()
