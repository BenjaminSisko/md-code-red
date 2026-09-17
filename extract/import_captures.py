#!/usr/bin/env python3
"""import_captures.py — CR-T-34. Folds tests/captures/ capture records into
content/expected_output.json.

    python3 extract/import_captures.py            # regenerate content/expected_output.json
    python3 extract/import_captures.py --check    # regenerate into a temp dir and diff (qa.py Q15)

CANONICAL CAPTURE PATH: tests/captures/<rhel_version>/<entry_id>.json, in this
repo. Eli Cross's ruling closes a three-way mismatch the CR-T-34 run's own
WADE_BLOCKED report surfaced between this path, content-src/captures/ (named
by this file's own predecessor docstring, extract/make_pending_skeletons.py,
before this extractor existed), and
07_QA_Test/MD_CODE_RED/captures/<rhel_version>/<entry_id>.json (named by the
content validation protocol, test-plan-skeleton-v1.md Part B §7/Appendix).
The company-record protocol document at that second path is now a pointer to
THIS path, not a second storage location for the files themselves.

CAPTURE RECORD SCHEMA — content validation protocol §7
(07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md Part B) is the field-name
authority; qa.py's Q16 adapts to these names, not the reverse (Eli Cross
ruling). Every capture record must carry:

    entry_id            content/commands.json's entry id
    rhel_version         "7" / "8" / "9" / "10"
    host                  census id (Home Lab/01 Devices/) or a throwaway-VM id
    redhat_release        literal `cat /etc/redhat-release` at capture time
    kernel                literal `uname -r` at capture time
    pkg_versions          {package: version} for whichever packages the tool touches
    command_as_run        the literal command string executed
    exit_code             numeric
    stdout                trimmed, secrets redacted
    stderr                trimmed, secrets redacted
    captured_on           ISO 8601 date
    captured_by           the SME who ran it
    blast_confirmed       the blast label as it actually behaved on the host
    undo_executed         {run: bool, ...} — must be run and confirmed, not assumed
    command_hash_at_capture   sha256(command_as_run) — see INTEGRITY RULE below
    verify_result          protocol §10: the entry's own `verify` text checked
                          against the real output, PASS/FAIL and why

command_hash_at_capture is not in the written protocol document, but every
real capture record carries one and it is load-bearing for the rule below;
folded into the authoritative field set by the same ruling that settled the
path question.

INTEGRITY RULE ("so an edited command resets to uncaptured"). Two checks, both
refuse the capture outright (it is left out of the regenerated index) rather
than warn and keep it:

  1. command_hash_at_capture must equal sha256(command_as_run) — computed
     from the file's own two fields, catching a corrupted or hand-edited
     capture record before it reaches anything else.
  2. For an entry whose command is a FIXED content/commands.json
     rhel_versions[version].command (never a generator's — MCR-SEC-006, a
     generator composes its command from validated FORM INPUT at render
     time, so there is no single "current" command to diff against), that
     command must equal command_as_run byte-for-byte, resolved the same way
     build.py's assemble() resolves a same_as pointer. If content has been
     edited since the capture was taken, the two strings disagree, the
     capture is refused, and the entry silently reverts to "not captured
     yet" (ADR-001 §6.5's own words for the state this index is meant to
     represent honestly) rather than going on narrating a command that no
     longer exists.

INDEXING. content/expected_output.json is keyed `entry_id|stig_id|rhel_version`
(its own `_meta.keyed_by`, unchanged by this file) because that is the key
build.py's assemble() joins onto a content entry's stig[] row. A capture for
an entry/version that carries no STIG mapping on this content (most generator
entries — content-validation records with no compliance claim attached) is
still validated in full above, but is not folded into the keyed index: there
is no stig[] row for build.py to join it onto, and putting it in under a
placeholder key would imply a STIG association this content does not make.
Its file is still counted in `_meta.files_validated`.

ADR-001 §6.3: generated files are never hand-edited. Fix a capture record, or
this extractor, then re-run — never content/expected_output.json directly.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(REPO, "content")
CAPTURES_DIR = os.path.join(REPO, "tests", "captures")
COMMANDS_JSON = os.path.join(CONTENT, "commands.json")
VERSIONS = ("7", "8", "9", "10")

REQUIRED_FIELDS = (
    "entry_id", "rhel_version", "host", "redhat_release", "kernel", "pkg_versions",
    "command_as_run", "exit_code", "stdout", "stderr", "captured_on", "captured_by",
    "blast_confirmed", "undo_executed", "command_hash_at_capture", "verify_result",
)


def load_entries():
    with open(COMMANDS_JSON, encoding="utf-8") as fh:
        return json.load(fh)["entries"]


def resolved_command(entry, version):
    """The entry's own rhel_versions[version].command, following one same_as
    hop — the same shape build.py's assemble()/extract/schema.py's
    resolve_chain() resolve. None for a generator entry (MCR-SEC-006: no
    fixed command exists to diff a capture against), an absent/unavailable
    version, or an unresolvable same_as (schema.py is the build-time
    authority on cycles; this function just declines to guess)."""
    if entry is None or "template" in entry or version not in VERSIONS:
        return None
    slot = (entry.get("rhel_versions") or {}).get(version)
    if not isinstance(slot, dict):
        return None
    if "same_as" in slot:
        target = slot["same_as"]
        if target == version or target not in VERSIONS:
            return None
        slot = (entry.get("rhel_versions") or {}).get(target)
        if not isinstance(slot, dict) or "same_as" in slot:
            return None  # content authors here only ever emit one hop
    return slot.get("command")


def capture_errors(rel_path, cap, entries_by_id):
    """§7/command_hash_at_capture field presence, then the two integrity
    checks. Field-presence failures short-circuit the rest — nothing else can
    be checked safely against a record missing the fields it would be checked
    against."""
    errs = []
    if not isinstance(cap, dict):
        return ["%s: capture record is not a JSON object" % rel_path]
    for field in REQUIRED_FIELDS:
        if field not in cap:
            errs.append("%s: missing required field '%s' (content validation protocol §7 / "
                       "command_hash_at_capture)" % (rel_path, field))
    if errs:
        return errs
    computed_hash = hashlib.sha256(cap["command_as_run"].encode("utf-8")).hexdigest()
    if computed_hash != cap["command_hash_at_capture"]:
        errs.append("%s: command_hash_at_capture '%s' does not match sha256(command_as_run) "
                   "'%s' — refused (a tampered or hand-edited capture record)"
                   % (rel_path, cap["command_hash_at_capture"], computed_hash))
    entry = entries_by_id.get(cap["entry_id"])
    if entry is None:
        errs.append("%s: entry_id '%s' does not exist in content/commands.json"
                   % (rel_path, cap["entry_id"]))
    else:
        current = resolved_command(entry, cap.get("rhel_version"))
        if current is not None and current != cap["command_as_run"]:
            errs.append(
                "%s: content/commands.json's current RHEL %s command for '%s' has changed since "
                "this capture ('%s' now vs '%s' captured) — refused, resets to uncaptured "
                "(ADR-001 §6.5)"
                % (rel_path, cap.get("rhel_version"), cap["entry_id"], current, cap["command_as_run"]))
    return errs


def stig_key(entry, cap):
    """entry_id|stig_id|rhel_version for the one stig[] row (per content's own
    shape, one row per RHEL release) matching this capture's rhel_version, or
    None when the entry has no STIG mapping on that release. Derived from the
    ENTRY's own stig[] row, never retyped from a capture's own
    (informational, unverified-by-this-script) stig_compliance block, so a
    capture record can never assert a stig_id the content doesn't actually
    carry for it."""
    for s in (entry.get("stig") or []):
        if s.get("rhel_version") == cap.get("rhel_version"):
            return "%s|%s|%s" % (entry["id"], s["stig_id"], cap["rhel_version"])
    return None


def build_index():
    """Walk CAPTURES_DIR, validate every file, and return
    (captures_by_key, errors, files_validated, files_indexed)."""
    entries_by_id = {e["id"]: e for e in load_entries()}
    captures_out = {}
    errors = []
    n_files = 0
    if not os.path.isdir(CAPTURES_DIR):
        return captures_out, errors, 0, 0
    for version_dir in sorted(os.listdir(CAPTURES_DIR)):
        vpath = os.path.join(CAPTURES_DIR, version_dir)
        if not os.path.isdir(vpath) or version_dir not in VERSIONS:
            continue
        for name in sorted(os.listdir(vpath)):
            if not name.endswith(".json"):
                continue
            n_files += 1
            path = os.path.join(vpath, name)
            rel = os.path.relpath(path, REPO)
            with open(path, encoding="utf-8") as fh:
                try:
                    cap = json.load(fh)
                except ValueError as exc:
                    errors.append("%s: not valid JSON (%s)" % (rel, exc))
                    continue
            errs = capture_errors(rel, cap, entries_by_id)
            if errs:
                errors.extend(errs)
                continue
            if cap["rhel_version"] != version_dir:
                errors.append("%s: rhel_version '%s' does not match its directory '%s'"
                             % (rel, cap["rhel_version"], version_dir))
                continue
            if cap["entry_id"] + ".json" != name:
                errors.append("%s: entry_id '%s' does not match its filename"
                             % (rel, cap["entry_id"]))
                continue
            entry = entries_by_id[cap["entry_id"]]
            key = stig_key(entry, cap)
            if key is None:
                continue  # validated above; no stig[] row on this release to index it under
            if key in captures_out:
                errors.append("%s: duplicate capture for key %s (already provided by another file)"
                             % (rel, key))
                continue
            captures_out[key] = cap
    return captures_out, errors, n_files, len(captures_out)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def generate(dest_dir):
    captures_out, errors, n_files, n_indexed = build_index()
    if errors:
        for e in errors:
            print("CAPTURE ERROR:", e, file=sys.stderr)
        sys.exit("FATAL: %d capture validation error(s) under tests/captures/ — fix the capture "
                 "record, or the content it no longer matches, then re-run" % len(errors))
    n_unindexed = n_files - n_indexed
    if n_files:
        status = ("%d capture record(s) validated and folded from tests/captures/ (CR-T-34); "
                 "%d carry no STIG mapping on this content and are validated but not indexed "
                 "(no stig[] row to join onto)" % (n_files, n_unindexed))
    else:
        status = "pending — no capture files under tests/captures/ (CR-T-34)"
    obj = {
        "_meta": {
            "generator": "extract/import_captures.py",
            "status": status,
            "keyed_by": "entry_id|stig_id|rhel_version",
            "capture_count": len(captures_out),
            "files_validated": n_files,
        },
        "captures": captures_out,
    }
    path = os.path.join(dest_dir, "expected_output.json")
    write_json(path, obj)
    return [path]


def main():
    if "--check" in sys.argv:
        tmp = tempfile.mkdtemp(prefix="mcr-captures-")
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
                print("GENERATED-FILE DRIFT (extract/import_captures.py):")
                for d in drift:
                    print("  " + d)
                sys.exit(1)
            print("extract/import_captures.py: %d generated file(s) match a fresh extractor run"
                  % len(written))
            sys.exit(0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    written = generate(CONTENT)
    for path in written:
        print("wrote %s (%d bytes)" % (os.path.relpath(path, REPO), os.path.getsize(path)))


if __name__ == "__main__":
    main()
