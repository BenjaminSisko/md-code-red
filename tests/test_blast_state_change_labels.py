#!/usr/bin/env python3
"""test_blast_state_change_labels.py — G4(d), corrected by Marcus Reed's H1/H3.

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_blast_state_change_labels.py

gen-dnf-package and gen-yum-package declare `blast: "green"` in
content/commands.json for BOTH enum branches of their `action` field
(install/remove) — but installing a package changes host state exactly as
much as removing one does; "install" carries no dynamic escalation in
content/dangerous.json at all (only "dnf remove"/"yum remove" do,
blast_floor "yellow"), so the install branch has stayed green with nothing to
raise it. Both stay yellow.

gen-chronyd-one-shot-check does NOT belong in that set. G4(d) originally
raised it too, on Caleb Stone's CR-T-34 note that `chronyd -Q` "steps the
system clock" — a misreading of chronyd(8), which Eli Cross's ruling then
repeated and this file (wrongly) encoded. The pinned man page is explicit
and identical on both RHEL 8 and RHEL 10
(content-src/raw/rhel{8,10}/chronyd.man.txt#L64-L74): `-q` "will set the
system clock once and exit"; `-Q` "is similar to the -q option, EXCEPT it
only prints the offset without making any corrections of the clock and
disables server ports to allow chronyd to be started WITHOUT ROOT
privileges". `-Q` is the read-only, unprivileged half of that pair — `-q` is
the one this toolkit does not generate a command for. Marcus Reed's H1
correction: gen-chronyd-one-shot-check goes back to green, and its
intent/notes now say what the man page actually says (content/commands.json,
same commit as this test's fix).

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

STATE-CHANGING PATTERN TABLE (Eli Cross's ruling, corrected by Marcus Reed's
H1 and H3): install|remove|erase|--permanent|enable|start|stop|add|del.
`-Q` is REMOVED (H1 — it is not state-changing; see above). The bare words
are matched with WORD BOUNDARIES, not as a plain substring (H3): the original
substring form matched `gen-nmcli-static-ipv4` only because
`ipv4.addresses` CONTAINS the letters "add", and `gen-useradd-create` only
because `useradd` CONTAINS them — neither command has a real `add` token,
and both entries only stayed correctly-labeled by accident (both were
already declared yellow for real destructive fields elsewhere in the same
generator, so the false match never actually changed the test's verdict, but
it was never proving what it claimed to). Word-boundary matching means `del`
does not fire inside `--delete` or `userdel`, and `add` does not fire inside
`--address` or `useradd` — those stay OUT of this sweep's matched set (they
are not asserted safe; they are simply not this sweep's job — a compound
identifier like `userdel` is content/dangerous.json's `dp-userdel` pattern's
job, at the dynamic/runtime layer, not this static content-label sweep's).
`--permanent` (the one flag-shaped entry) is matched as an exact literal
substring, the same "assembled text names its own risk" idiom
content/dangerous.json's own `match` field already uses — it is a
distinctive enough token that a false substring match inside another flag is
not a realistic risk the way a 3-letter bare word is.

This is intentionally broad even so — it will flag a generator whose golden
command contains a real, standalone one of these words/flags in an argument
value it does not control (a false positive is a human re-reading the entry
and either fixing the label or explicitly excluding it here with a stated
reason, never a silent narrowing of the pattern to make today's content
pass). As shipped, every OTHER generator this pattern still matches
(gen-fw-open-port, gen-fw-allow-service, gen-systemctl-manage,
gen-podman-stop) already declares yellow; only gen-dnf-package and
gen-yum-package needed the entry-level fix, and gen-chronyd-one-shot-check
needed the OPPOSITE fix.
"""
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden-commands.json")
COMMANDS = os.path.join(REPO, "content", "commands.json")

STATE_CHANGE_WORDS = ("install", "remove", "erase", "enable", "start", "stop", "add", "del")
STATE_CHANGE_FLAGS = ("--permanent",)
STATE_CHANGE_RE = re.compile(
    r"\b(?:" + "|".join(STATE_CHANGE_WORDS) + r")\b|" +
    "|".join(re.escape(f) for f in STATE_CHANGE_FLAGS))
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

    def test_dnf_and_yum_are_covered_by_the_sweep(self):
        # This test exists to catch the sweep itself going silent (a golden-table
        # edit that stops matching these two would hide the real assertion
        # above behind an empty match set for exactly the entries this
        # condition is about).
        for entry_id in ("gen-dnf-package", "gen-yum-package"):
            self.assertIn(entry_id, self.matches,
                          "%s no longer matches the state-changing pattern table in the golden "
                          "fixture — this test can no longer prove what G4(d) asked it to" % entry_id)

    def test_chronyd_one_shot_check_is_not_matched_and_stays_green(self):
        # H1 (Marcus Reed): -Q is read-only and needs no root (chronyd(8),
        # content-src/raw/rhel{8,10}/chronyd.man.txt#L64-L74) — it must never
        # be flagged by this sweep, and the entry must stay declared green.
        self.assertNotIn("gen-chronyd-one-shot-check", self.matches,
                         "gen-chronyd-one-shot-check matches the state-changing pattern table — "
                         "either -Q crept back into STATE_CHANGE_FLAGS/WORDS, or the golden "
                         "command changed to something that actually is state-changing")
        entry = self.entries["gen-chronyd-one-shot-check"]
        self.assertEqual(entry.get("blast"), "green",
                         "gen-chronyd-one-shot-check must declare blast green — chronyd(8) -Q "
                         "makes no clock correction and needs no root")
        for field in ("intent", "notes", "verify", "undo"):
            text = (entry.get(field) or "").lower()
            self.assertNotIn("steps the system clock", text,
                             "%s still claims -Q steps the system clock — chronyd(8) says the "
                             "opposite (#L68-L74): '-Q ... only prints the offset without making "
                             "any corrections of the clock'" % field)

    def test_word_boundary_anchoring_excludes_substring_false_positives(self):
        # H3 (Marcus Reed): `del`/`add` must not fire inside a larger
        # identifier or a differently-named flag. These are commands that
        # were never in the golden fixture verbatim — synthetic negative
        # cases proving the ANCHORING, independent of what today's golden
        # table happens to contain.
        must_not_match = [
            "nmcli connection modify 'lab-eth0' ipv4.addresses '10.0.0.1/24'",  # 'add' in 'addresses'
            "useradd -m -s '/bin/bash' 'svcacct'",                              # 'add' in 'useradd'
            "firewall-cmd --zone=public --address='10.1.1.5'",                  # 'add' in '--address'
            "firewall-cmd --zone=public --delete-something",                    # 'del' in '--delete...'
            "userdel -r 'olduser'",                                             # 'del' in 'userdel'
        ]
        for cmd in must_not_match:
            self.assertIsNone(STATE_CHANGE_RE.search(cmd),
                              "STATE_CHANGE_RE matched %r — a bare word fired inside a larger "
                              "identifier or a different flag, which H3 exists to prevent" % cmd)

    def test_word_boundary_anchoring_still_matches_real_tokens(self):
        # The anchoring must not overcorrect into matching nothing.
        must_match = [
            "systemctl 'stop' 'sshd.service'",
            "dnf 'remove' 'firewalld'",
            "firewall-cmd --permanent --add-service=ssh",
            "firewall-cmd --zone=public --add-forward-port=port=8080:proto=tcp:toport=80",
        ]
        for cmd in must_match:
            self.assertIsNotNone(STATE_CHANGE_RE.search(cmd),
                                 "STATE_CHANGE_RE did not match %r — the anchoring overcorrected "
                                 "and lost a real token" % cmd)


if __name__ == "__main__":
    unittest.main()
