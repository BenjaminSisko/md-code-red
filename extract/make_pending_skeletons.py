#!/usr/bin/env python3
"""make_pending_skeletons.py — the two content families that have no source yet.

Stdlib only. Deterministic: no inputs, so byte-identical output on every run.

    python3 extract/make_pending_skeletons.py            # regenerate content/
    python3 extract/make_pending_skeletons.py --check    # regenerate into a temp
                                                         # dir and diff (qa.py Q15)

WHAT THIS PRODUCES, AND WHY IT IS EMPTY

  content/flags_rhel<N>.json   the per-version flag dictionaries — EMPTY.
                               ADR-001 §6.1: a flag dictionary may only describe
                               flags a real binary on a real host of that RHEL
                               version actually accepts. No host has been read
                               yet; extract/extract_rhel_flags.py (CR-T-09) is the
                               extractor that will read one, and CR-T-10/11/12 run
                               it. Until then these files are empty by design
                               rather than filled with anything we cannot pin to a
                               running binary.

  content/expected_output.json is NO LONGER this script's responsibility
                               (CR-T-34). extract/import_captures.py folds real
                               capture files from tests/captures/ into that
                               index now, and is qa.py Q15's authority for it;
                               this script only emits the per-version flag
                               dictionaries below.

Every emitted file carries a _meta.status that says in words why it is empty and
which task fills it, and _meta.generator names the extractor that will own it
once it has a source — not this script. build.py refuses an empty flags
dictionary that does not explain itself (extract/schema.py), so the silence is
enforced to be a stated silence.

HISTORY. This file was extract/make_skeleton_content.py, the CR-T-02 stand-in that
also emitted partial RULES and CCI datasets. CR-T-07 replaced that half with
extract/parse_xccdf.py, which emits the full four benchmarks from the pinned XML.
What is left here is only the genuinely sourceless half, and the name now says so.

ADR-001 §6.3: generated files are never hand-edited. Fix the extractor, re-run.
"""

import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(REPO, "content")

VERSIONS = ("7", "8", "9", "10")


def flags_skeleton(version):
    """An empty per-version flag dictionary that states its own emptiness."""
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


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def generate(dest_dir):
    written = []
    for version in VERSIONS:
        path = os.path.join(dest_dir, "flags_rhel%s.json" % version)
        write_json(path, flags_skeleton(version))
        written.append(path)
    return written


def main():
    if "--check" in sys.argv:
        tmp = tempfile.mkdtemp(prefix="mcr-pending-")
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
                print("GENERATED-FILE DRIFT (extract/make_pending_skeletons.py):")
                for d in drift:
                    print("  " + d)
                sys.exit(1)
            print("extract/make_pending_skeletons.py: %d generated file(s) match a fresh extractor run"
                  % len(written))
            sys.exit(0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    written = generate(CONTENT)
    for path in written:
        print("wrote %s (%d bytes)" % (os.path.relpath(path, REPO), os.path.getsize(path)))


if __name__ == "__main__":
    main()
