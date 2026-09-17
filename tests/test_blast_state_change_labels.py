#!/usr/bin/env python3
"""test_blast_state_change_labels.py — G4(d), Eli Cross's ruling on three
mislabeled generators.

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_blast_state_change_labels.py

gen-dnf-package and gen-yum-package declare `blast: "green"` in
content/commands.json for BOTH enum branches of their `action` field
(install/remove) — but installing a package changes host state exactly as
much as removing one does; "install" carries no dynamic escalation in
content/dangerous.json at all (only "dnf remove"/"yum remove" do,
blast_floor "yellow"), so the install branch has stayed green with nothing to
raise it. gen-chronyd-one-shot-check also declares green: `chronyd -Q`
retrieves the offset from an NTP source and STEPS THE SYSTEM CLOCK before
exiting (chronyd(8), cited in the entry's own `notes`), which is a state
change (logs, cron, anything time-sensitive) even though it touches no file
and dangerous.json has no pattern for a bare `-Q`.

This is a STATIC sweep over declared content, deliberately coarser and
independent from tests/hostile_harness.js's enum-branch sweep (which computes
REAL blast via assembleCommand()/blastFor() for every enum branch and asserts
it never rates below the entry's declared blast, or below yellow for a
declared-green entry with a destructive branch — a runtime check). This test
asks a simpler, prior question: does the entry's own DECLARED blast even
admit that its golden command, on any pinned RHEL release, is state-changing
in the first place? A generator whose golden table shows
`dnf 'remove' 'firewalld'` and whose content still says `blast: "green"` is
wrong before assembleCommand() is ever called.

STATE-CHANGING PATTERN TABLE (Eli Cross's ruling, verbatim):
install|remove|erase|-Q|--permanent|enable|start|stop|add|del
— matched as a plain substring against every golden command string (the same
"assembled text names its own risk" idiom content/dangerous.json's own
`match` field already uses), on every RHEL release the golden table gives a
non-null command for. A generator entry whose golden command matches on ANY
release must declare `blast` at least "yellow" in content/commands.json.

This is intentionally broad — it will flag a generator whose golden command
merely CONTAINS one of these words in an argument value it does not control
(a false positive is a human re-reading the entry and either fixing the
label or explicitly excluding it here with a stated reason, never a silent
narrowing of the pattern to make today's content pass). As shipped, every
OTHER generator this pattern matches (gen-fw-open-port, gen-fw-allow-service,
gen-nmcli-static-ipv4, gen-useradd-create, gen-systemctl-manage,
gen-podman-stop) already declares yellow; only the three named above are
wrong.
"""
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden-commands.json")
COMMANDS = os.path.join(REPO, "content", "commands.json")

STATE_CHANGE_RE = re.compile(r"install|remove|erase|-Q|--permanent|enable|start|stop|add|del")
BLAST_RANK = {"green": 0, "yellow": 1, "red": 2}


def load():
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)["generators"]
    with open(COMMANDS, encoding="utf-8") as fh:
        entries = {e["id"]: e for e in json.load(fh)["entries"]}
    return golden, entries


def state_changing_matches(golden):
    """{entry_id: sorted([matched RHEL versions])} for every golden generator
    with at least one non-null command matching the pattern table on some
    release."""
    out = {}
    for gid, g in golden.items():
        if gid.startswith("_"):
            continue
        matched = sorted(v for v, cmd in (g.get("commands") or {}).items()
                         if cmd and STATE_CHANGE_RE.search(cmd))
        if matched:
            out[gid] = matched
    return out


class BlastStateChangeLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden, cls.entries = load()
        cls.matches = state_changing_matches(cls.golden)

    def test_pattern_table_matches_something(self):
        # AL-GATE3-004 shape: a sweep over an empty match set proves nothing.
        self.assertGreater(len(self.matches), 0,
                           "the state-changing pattern table matched no golden command at all — "
                           "either the golden fixture regressed or this pattern is broken")

    def test_every_state_changing_generator_declares_at_least_yellow(self):
        failures = []
        for entry_id, versions in sorted(self.matches.items()):
            entry = self.entries.get(entry_id)
            if entry is None:
                failures.append("%s: golden fixture names an entry that does not exist in "
                               "content/commands.json" % entry_id)
                continue
            declared = entry.get("blast", "green")
            if BLAST_RANK.get(declared, 0) < BLAST_RANK["yellow"]:
                failures.append(
                    "%s: declares blast '%s' but its golden command matches the "
                    "state-changing pattern table on RHEL %s (e.g. %s) — must be at least "
                    "yellow" % (entry_id, declared, ", ".join(versions),
                                self.golden[entry_id]["commands"][versions[0]]))
        self.assertEqual(failures, [], "\n" + "\n".join(failures))

    def test_the_three_named_entries_are_covered_by_the_sweep(self):
        # This test exists to catch the sweep itself going silent (a golden-table
        # edit that stops matching these three would hide the real assertion
        # above behind an empty match set for exactly the entries this
        # condition is about).
        for entry_id in ("gen-dnf-package", "gen-yum-package", "gen-chronyd-one-shot-check"):
            self.assertIn(entry_id, self.matches,
                          "%s no longer matches the state-changing pattern table in the golden "
                          "fixture — this test can no longer prove what G4(d) asked it to" % entry_id)


if __name__ == "__main__":
    unittest.main()
