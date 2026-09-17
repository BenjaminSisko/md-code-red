#!/usr/bin/env python3
"""Build grey-beard-ansible.html from template.html + content/.

Stdlib only. Usage:
    python3 build.py                      # build
    python3 build.py --merge patch.json   # merge an exported annotations patch
                                          # into content/ (notes -> mentor_note
                                          # additions file), then build

The single-file output is the only artifact that crosses the air gap.
"""

import json
import os
import sys
from datetime import date

REPO = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.0.1"
CHANGELOG = [
    "v1.0.1 (2026-08-24) — sysadmin-review fix pass (Caleb): copy buttons no longer prepend their label; blast verdicts fixed (verb-less RHEL CLIs like firewall-cmd default yellow, --diff alone is not a rehearsal, destructive modules on group patterns go red); truthful Ctrl-C guidance on the Panic page (now with action buttons and copyable commands); reboot snippet accepts degraded hosts; 'Shared connection closed' is its own honest low-confidence signature; ansible.posix snippets declare their collection dependency; ansible 2.9 compatibility toggle in the Task Builder + About guidance; 8 new entries (offline collection install, fetch evidence, air-gapped dnf repo, chrony, journald cap, logrotate, tar restore, NFS mount) + fetch/slurp in the Task Builder; new-host enrollment ritual; chrony Day One step; rituals genuinely reset on entry; linter no longer flags times like 14:00; old-Firefox polyfills.",
    "v1.0.0 (2026-08-24) — first release: intent index (56 entries), 14 generators, command/error decoders, gotcha linter, precedence explorer, 8 decision trees, rituals, day-one recon, drills, 30/60/90, glossary, scar ledger, dossier, annotations export.",
]

CONTENT = {
    "commands": "commands.json",
    "modules": "modules.json",
    "flags": "flags.json",
    "rhelFlags": "rhel_flags.json",
    "errors": "errors.json",
    "trees": "trees.json",
    "snippets": "snippets.json",
    "checklists": "checklists.json",
    "glossary": "glossary.json",
    "scars": "scars.json",
    "drills": "drills.json",
    "dossier": "dossier.json",
}


def load_content():
    data = {}
    for key, fname in CONTENT.items():
        path = os.path.join(REPO, "content", fname)
        with open(path) as f:
            try:
                data[key] = json.load(f)
            except json.JSONDecodeError as e:
                sys.exit(f"FATAL: {fname} is not valid JSON: {e}")
    with open(os.path.join(REPO, "content", "letter.md")) as f:
        data["letter"] = f.read()
    data["meta"] = {"version": VERSION, "built": date.today().isoformat(), "changelog": CHANGELOG}
    return data


def validate(data):
    """Schema gate — the same promises qa.py re-checks on the built file."""
    errs = []
    for e in data["commands"]["entries"]:
        for field in ("id", "world", "category", "intent", "command", "notes", "verify", "undo", "blast", "source", "verified"):
            if not e.get(field):
                errs.append(f"commands entry {e.get('id','?')}: missing {field}")
        if e.get("blast") not in ("green", "yellow", "red"):
            errs.append(f"commands entry {e.get('id')}: bad blast '{e.get('blast')}'")
        if e.get("world") not in ("ansible", "rhel"):
            errs.append(f"commands entry {e.get('id')}: bad world")
        elif e.get("category") not in data["commands"]["categories"][e["world"]]:
            errs.append(f"commands entry {e.get('id')}: category '{e.get('category')}' not in {e['world']} category list")
    ids = [e["id"] for e in data["commands"]["entries"]]
    if len(ids) != len(set(ids)):
        errs.append("duplicate command entry ids")
    for s in data["errors"]["signatures"]:
        for field in ("id", "pattern", "title", "meaning", "disease", "first_moves", "source"):
            if not s.get(field):
                errs.append(f"error signature {s.get('id','?')}: missing {field}")
        if s.get("tree"):
            tree_ids = [t["id"] for t in data["trees"]["trees"]]
            if s["tree"] not in tree_ids:
                errs.append(f"error signature {s['id']}: unknown tree {s['tree']}")
    for t in data["trees"]["trees"]:
        if "start" not in t["nodes"]:
            errs.append(f"tree {t['id']}: no start node")
        for nid, n in t["nodes"].items():
            if "q" in n:
                for o in n["options"]:
                    if o["next"] not in t["nodes"]:
                        errs.append(f"tree {t['id']} node {nid}: dangling next '{o['next']}'")
            elif "answer" not in n:
                errs.append(f"tree {t['id']} node {nid}: neither question nor answer")
    if errs:
        for e in errs:
            print("SCHEMA:", e, file=sys.stderr)
        sys.exit(f"FATAL: {len(errs)} schema error(s)")


def merge_patch(path):
    """Fold an exported annotations JSON into content/annotations-merged.md
    for human review, and append notes onto matching entries' mentor_note."""
    with open(path) as f:
        patch = json.load(f)
    if patch.get("tool") != "grey-beard-ansible":
        sys.exit("FATAL: not a grey-beard-ansible annotations export")
    notes = patch.get("notes", {})
    if not notes:
        print("no notes in patch; nothing to merge")
        return
    cpath = os.path.join(REPO, "content", "commands.json")
    with open(cpath) as f:
        commands = json.load(f)
    merged = 0
    for e in commands["entries"]:
        if e["id"] in notes:
            addition = notes[e["id"]].strip()
            if addition and addition not in (e.get("mentor_note") or ""):
                e["mentor_note"] = ((e.get("mentor_note") or "").rstrip()
                                    + (" " if e.get("mentor_note") else "")
                                    + "[field note] " + addition)
                merged += 1
    with open(cpath, "w") as f:
        json.dump(commands, f, indent=1, ensure_ascii=False)
    leftover = {k: v for k, v in notes.items() if k not in {e["id"] for e in commands["entries"]}}
    if leftover:
        lpath = os.path.join(REPO, "content", "unmerged-notes.json")
        with open(lpath, "w") as f:
            json.dump(leftover, f, indent=1, ensure_ascii=False)
        print(f"{len(leftover)} note(s) had no matching entry -> content/unmerged-notes.json")
    print(f"merged {merged} note(s) into commands.json mentor_note fields")


def build():
    data = load_content()
    validate(data)
    with open(os.path.join(REPO, "template.html")) as f:
        tpl = f.read()
    if "/*__DATA__*/" not in tpl:
        sys.exit("FATAL: template.html has no /*__DATA__*/ placeholder")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # keep the JSON safe inside a <script> block
    payload = payload.replace("</", "<\\/")
    out = tpl.replace("/*__DATA__*/", payload)
    out = out.replace("__VERSION__", VERSION).replace("__BUILT_DATE__", data["meta"]["built"])
    dest = os.path.join(REPO, "grey-beard-ansible.html")
    with open(dest, "w") as f:
        f.write(out)
    size = os.path.getsize(dest)
    n = len(data["commands"]["entries"])
    print(f"built grey-beard-ansible.html  ({size/1024:.0f} KiB, {n} command entries, "
          f"{len(data['trees']['trees'])} trees, {len(data['errors']['signatures'])} error signatures, "
          f"core {data['modules']['_meta']['core_version']})")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--merge":
        merge_patch(sys.argv[2])
    build()
