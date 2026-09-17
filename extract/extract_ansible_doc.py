#!/usr/bin/env python3
"""Vendor extraction: ansible-doc --json + CLI --help -> content/modules.json, content/flags.json.

Stdlib only. Run from the repo root:
    python3 extract/extract_ansible_doc.py

Sources are the vendor's own tooling (ansible-core in ~/HomeLab/tools/ansible-venv),
so every emitted entry is vendor documentation, stamped with the core version it
came from. Re-run against a different venv (e.g. the work box's version) by
setting ANSIBLE_VENV_BIN.
"""

import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_BIN = os.environ.get(
    "ANSIBLE_VENV_BIN", "/Users/benny/HomeLab/tools/ansible-venv/bin"
)

# Modules the Task Builder offers forms for. Short name -> candidate FQCNs in
# preference order (builtin first, then the collections shipped in the venv).
TASK_MODULES = {
    "file": ["ansible.builtin.file"],
    "copy": ["ansible.builtin.copy"],
    "template": ["ansible.builtin.template"],
    "lineinfile": ["ansible.builtin.lineinfile"],
    "blockinfile": ["ansible.builtin.blockinfile"],
    "user": ["ansible.builtin.user"],
    "group": ["ansible.builtin.group"],
    "service": ["ansible.builtin.service"],
    "systemd_service": ["ansible.builtin.systemd_service"],
    "dnf": ["ansible.builtin.dnf"],
    "cron": ["ansible.builtin.cron"],
    "command": ["ansible.builtin.command"],
    "shell": ["ansible.builtin.shell"],
    "get_url": ["ansible.builtin.get_url"],
    "unarchive": ["ansible.builtin.unarchive"],
    "hostname": ["ansible.builtin.hostname"],
    "reboot": ["ansible.builtin.reboot"],
    "fetch": ["ansible.builtin.fetch"],
    "slurp": ["ansible.builtin.slurp"],
    "mount": ["ansible.posix.mount"],
    "authorized_key": ["ansible.posix.authorized_key"],
    "firewalld": ["ansible.posix.firewalld"],
    "seboolean": ["ansible.posix.seboolean"],
    "selinux": ["ansible.posix.selinux"],
    "sysctl": ["ansible.posix.sysctl"],
    "timezone": ["community.general.timezone"],
}

# Params that matter for form-building; everything else is offered under
# "more options" so forms stay usable. Per-module curated ordering.
PRIMARY_PARAMS = {
    "file": ["path", "state", "owner", "group", "mode", "recurse", "src"],
    "copy": ["src", "dest", "owner", "group", "mode", "backup", "content", "validate"],
    "template": ["src", "dest", "owner", "group", "mode", "backup", "validate"],
    "lineinfile": ["path", "line", "regexp", "state", "insertafter", "insertbefore", "backup", "create", "validate"],
    "blockinfile": ["path", "block", "marker", "state", "insertafter", "backup", "create"],
    "user": ["name", "state", "groups", "append", "shell", "home", "create_home", "system", "comment"],
    "group": ["name", "state", "gid", "system"],
    "service": ["name", "state", "enabled"],
    "systemd_service": ["name", "state", "enabled", "daemon_reload", "masked", "scope"],
    "dnf": ["name", "state", "enablerepo", "disablerepo", "update_cache", "security"],
    "cron": ["name", "job", "minute", "hour", "day", "month", "weekday", "user", "state", "special_time"],
    "command": ["cmd", "chdir", "creates", "removes"],
    "shell": ["cmd", "chdir", "creates", "removes", "executable"],
    "get_url": ["url", "dest", "owner", "group", "mode", "checksum", "validate_certs"],
    "unarchive": ["src", "dest", "remote_src", "owner", "group", "mode", "creates"],
    "hostname": ["name", "use"],
    "reboot": ["reboot_timeout", "msg", "test_command"],
    "fetch": ["src", "dest", "flat", "validate_checksum"],
    "slurp": ["src"],
    "mount": ["path", "src", "fstype", "opts", "state", "boot"],
    "authorized_key": ["user", "key", "state", "exclusive", "key_options"],
    "firewalld": ["service", "port", "zone", "state", "permanent", "immediate", "rich_rule", "source", "interface"],
    "seboolean": ["name", "state", "persistent"],
    "selinux": ["state", "policy"],
    "sysctl": ["name", "value", "state", "reload", "sysctl_file"],
    "timezone": ["name"],
}

CLIS = [
    "ansible",
    "ansible-playbook",
    "ansible-vault",
    "ansible-galaxy",
    "ansible-config",
    "ansible-inventory",
    "ansible-doc",
    "ansible-pull",
    "ansible-console",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def core_version():
    out = run([os.path.join(VENV_BIN, "ansible"), "--version"]).stdout
    m = re.search(r"ansible \[core ([^\]]+)\]", out)
    return m.group(1) if m else "unknown"


def first_sentence(desc):
    """description may be a list or string; return a compact one-liner."""
    if isinstance(desc, list):
        desc = desc[0] if desc else ""
    desc = re.sub(r"[ICBM]\(([^)]*)\)", r"\1", str(desc))  # strip doc markup
    desc = re.sub(r"[UL]\(([^)]*)\)", r"\1", desc)
    desc = re.sub(r"R\(([^,)]*)[^)]*\)", r"\1", desc)
    return desc.strip()


def extract_module(short, candidates, ver):
    for fqcn in candidates:
        r = run([os.path.join(VENV_BIN, "ansible-doc"), "--json", fqcn])
        if r.returncode != 0 or not r.stdout.strip():
            continue
        data = json.loads(r.stdout)
        key = next(iter(data))
        doc = data[key].get("doc", {})
        examples = data[key].get("examples") or ""
        opts = doc.get("options", {}) or {}
        primary = PRIMARY_PARAMS.get(short, [])
        params = []
        for name in primary:
            if name not in opts:
                continue
            o = opts[name]
            params.append({
                "name": name,
                "required": bool(o.get("required", False)),
                "type": o.get("type", "str"),
                "choices": o.get("choices", []),
                "default": o.get("default"),
                "desc": first_sentence(o.get("description", "")),
            })
        extra = sorted(n for n in opts if n not in primary and not n.startswith("_"))
        # first example block from the vendor docs, trimmed
        ex = examples.strip()
        if ex:
            blocks = re.split(r"\n(?=- name:)", ex)
            ex = blocks[0].strip()[:800]
        return {
            "fqcn": key,
            "short_desc": first_sentence(doc.get("short_description", "")),
            "params": params,
            "extra_params": extra,
            "example": ex,
            "source": f"ansible-doc (core {ver})",
        }
    return None


HELP_OPT = re.compile(r"^\s{2,}(-{1,2}[^\s,]+(?:,\s*-{1,2}[^\s,]+)*)\s*(.*)$")


def extract_cli_flags(cli, ver):
    """Parse `<cli> --help` argparse output into flag entries."""
    r = run([os.path.join(VENV_BIN, cli), "--help"])
    text = r.stdout or r.stderr
    flags, seen = [], set()
    current = None
    for line in text.splitlines():
        m = HELP_OPT.match(line)
        starts_with_dash = line.lstrip().startswith("-")
        if m and starts_with_dash:
            names_part = m.group(1)
            rest = m.group(2).strip()
            # argparse prints "--flag FLAG, -f FLAG  desc"; strip metavars
            names = []
            for tok in names_part.split(","):
                tok = tok.strip().split()[0].split("=")[0]
                if tok.startswith("-"):
                    names.append(tok)
            if not names:
                continue
            current = {"flags": names, "desc": rest}
            key = tuple(names)
            if key not in seen:
                seen.add(key)
                flags.append(current)
        elif current and line.startswith("    ") and line.strip() and not starts_with_dash:
            current["desc"] = (current["desc"] + " " + line.strip()).strip()
    return {
        "source": f"{cli} --help (core {ver})",
        "flags": [f for f in flags if f["desc"] or len(f["flags"]) > 1 or f["flags"][0].startswith("--")],
    }


def main():
    ver = core_version()
    print(f"ansible-core {ver} at {VENV_BIN}")

    modules = {"_meta": {"core_version": ver, "generator": "extract/extract_ansible_doc.py"}}
    for short, cands in TASK_MODULES.items():
        entry = extract_module(short, cands, ver)
        if entry:
            modules[short] = entry
            print(f"  module {short:16s} <- {entry['fqcn']} ({len(entry['params'])} primary params)")
        else:
            print(f"  module {short:16s} MISSING — not emitted", file=sys.stderr)

    flags = {"_meta": {"core_version": ver, "generator": "extract/extract_ansible_doc.py"}}
    for cli in CLIS:
        entry = extract_cli_flags(cli, ver)
        flags[cli] = entry
        print(f"  cli    {cli:16s} {len(entry['flags'])} flags")

    with open(os.path.join(REPO, "content", "modules.json"), "w") as f:
        json.dump(modules, f, indent=1, sort_keys=True)
    with open(os.path.join(REPO, "content", "flags.json"), "w") as f:
        json.dump(flags, f, indent=1, sort_keys=True)
    print("wrote content/modules.json, content/flags.json")


if __name__ == "__main__":
    main()
