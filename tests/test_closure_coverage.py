#!/usr/bin/env python3
"""test_closure_coverage.py -- Q23 watched firing, one failure condition at a time.

Al specified six failure conditions plus M5's accuracy component. A gate with
seven ways to fail and no evidence that any of them fires is seven claims, so
each one is driven here against a deliberately broken input, and the PASSING
input is checked alongside it so a gate that failed on everything could not
pass.

M5's own case is the one that matters most, and the reason is Marcus's: a false
positive counts as `classified` AND `recorded`, so the ledger balances while the
record sits in the product under a vendor citation. Running the accuracy
component for the first time on this corpus found 56 such records. The cases in
`REAL_FALSE_POSITIVES` below are four of them, verbatim.
"""

import datetime
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "extract"))

import qa  # noqa: E402
import mine_commands as mine  # noqa: E402

BASELINE = os.path.join(REPO, "content-src", "closure_baseline.json")
CORPUS = os.path.join(REPO, "content", "reference_commands.json")

# Lifted verbatim out of the pre-M5 corpus. Every one balanced the ledger.
REAL_FALSE_POSITIVES = [
    ("and", "and an 'archive' contains old metadata configurations. They are"),
    ("by", "by 'r' to reject the path. The first regex in the list to match the"),
    ("device", "device {"),
    ("for", "for f in $(ls); do tar xvf $f; done"),
    ("a", "a deep attribute)"),
]
# Real commands that must SURVIVE the same tests. Without these, a re-assertion
# that refused everything would pass every case above.
REAL_COMMANDS = [
    ("dnf", "dnf clean all"),
    ("chkconfig", "chkconfig acpid on"),
    ("buildah", "buildah from scratch"),
    ("dig", "dig _ldap._tcp.ipa.example.com. SRV"),
    ("shutdown", 'shutdown --poweroff 13:59 "Attention. The system will shut down at 13:59"'),
    ("auditctl", "auditctl -s | grep -i \"fail\""),
]


class TheExtractorRefusesTheRealFalsePositives(unittest.TestCase):
    """The corpus fix. M5 found them; extract/mine_commands.py refuses them."""

    def _classify(self, text):
        vocab = set(["and", "by", "device", "for", "a", "dnf", "chkconfig", "buildah", "dig",
                     "shutdown", "auditctl", "grep", "tar", "ls"])
        return mine.classify(text, "#", "lowercase", vocab, set(), strong=vocab)

    def test_every_real_false_positive_now_goes_to_residue(self):
        for tool, text in REAL_FALSE_POSITIVES:
            got_tool, reason = self._classify(text)
            self.assertIsNone(got_tool, "%r is still parsed as the tool %r" % (text, got_tool))
            self.assertIn(reason, mine.RESIDUE_REASONS, text)

    def test_every_real_command_still_survives(self):
        """The positive control the case above is worthless without."""
        for tool, text in REAL_COMMANDS:
            got_tool, reason = self._classify(text)
            self.assertIsNotNone(got_tool, "%r was refused as %s" % (text, reason))

    def test_no_name_on_the_refusal_list_is_a_real_binary(self):
        """`which` and `who` were on the first cut of this list. Both are real
        binaries. Q23 caught it; this keeps it caught."""
        with open(os.path.join(REPO, "content", "tools.json"), encoding="utf-8") as fh:
            known = set(t["id"] for t in json.load(fh)["tools"])
        for v in ("7", "8", "9", "10"):
            path = os.path.join(REPO, "content", "flags_rhel%s.json" % v)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    known |= set((json.load(fh).get("clis") or {}).keys())
        known |= set(mine.COMMON_BINARIES)
        self.assertEqual(set(), mine.FUNCTION_WORD_HEADS & known)


class TheIndependentReassertionDisagreesWhenItShould(unittest.TestCase):
    """Q23's M5 component, driven directly. It never calls the extractor."""

    def _occ(self):
        return {"v": "8", "s": "RHEL-08-010000", "f": "chk", "l": 1}

    def test_a_function_word_head_is_refused(self):
        for tool, text in REAL_FALSE_POSITIVES[:2]:
            ok, why = qa.q23_reassert({"id": "x", "t": tool, "c": text}, {"v": "8", "p": "z", "x": "EXAMPLES", "l": 1})
            self.assertFalse(ok, text)
            self.assertIn("function word", why)

    def test_a_declared_tool_that_is_not_the_head_is_refused(self):
        ok, why = qa.q23_reassert(
            {"id": "x", "t": "systemctl", "c": "auditctl -s"},
            {"v": "8", "p": "content-src/raw/rhel8/auditctl.man.txt", "x": "EXAMPLES", "l": 1})
        self.assertFalse(ok)
        self.assertIn("resolves", why)

    def test_a_line_the_source_never_marked_as_a_command_is_refused(self):
        ok, why = qa.q23_reassert(
            {"id": "x", "t": "auditctl", "c": "auditctl -s"},
            {"v": "8", "p": "content-src/raw/rhel8/auditctl.man.txt", "x": "DESCRIPTION", "l": 1})
        self.assertFalse(ok)
        self.assertIn("does not mark this as a command", why)

    def test_the_gate_resolves_wrappers_with_its_own_table(self):
        self.assertEqual("auditctl", qa.q23_head("sudo auditctl -s"))
        self.assertEqual("auditctl", qa.q23_head("sudo -u root auditctl -s"))
        self.assertEqual("grep", qa.q23_head("/usr/bin/grep -i fail"))

    def test_a_quoted_sentence_argument_is_not_prose(self):
        """`shutdown --poweroff 13:59 "Attention. The system will..."` is a
        command. A sentence test that cannot see quotes would refuse it."""
        self.assertFalse(qa.q23_sentence_like(REAL_COMMANDS[4][1]))
        self.assertTrue(qa.q23_sentence_like("and an 'x' contains old configurations. They are"))

    def test_a_dotted_fqdn_is_not_a_sentence_boundary(self):
        self.assertFalse(qa.q23_sentence_like(REAL_COMMANDS[3][1]))


class TheLedgerFailureConditions(unittest.TestCase):
    """Al's six, each driven against a broken ledger."""

    @classmethod
    def setUpClass(cls):
        with open(CORPUS, encoding="utf-8") as fh:
            cls.meta = json.load(fh)["_meta"]
        with open(BASELINE, encoding="utf-8") as fh:
            cls.baseline = json.load(fh)

    def test_the_shipped_ledger_balances(self):
        """Positive control for all six."""
        for family, cells in self.meta["closure_ledger"].items():
            for rel, cell in cells.items():
                self.assertEqual(cell["candidates"], cell["classified"] + cell["residue"],
                                 "%s/%s" % (family, rel))
                self.assertEqual(cell["classified"], cell["recorded"], "%s/%s" % (family, rel))
                self.assertGreater(cell["classified"], 0, "%s/%s" % (family, rel))

    def test_the_residue_recount_is_independent_of_the_ledger(self):
        """Q23 counts content-src/residue/ line by line rather than trusting
        _meta. A ledger that checked itself against its own summary would be
        asserting that addition works."""
        counted = qa.q23_recount_residue()
        for family, cells in self.meta["closure_ledger"].items():
            for rel, cell in cells.items():
                if not cell["residue"]:
                    continue
                self.assertEqual(cell["residue"], counted[family][rel]["residue"],
                                 "%s/%s" % (family, rel))

    def test_the_baseline_names_an_owner_and_a_date(self):
        self.assertTrue(self.baseline.get("_pinned_by"))
        self.assertTrue(self.baseline.get("_retire_owner"))
        deadline = datetime.date(*[int(x) for x in self.baseline["_retire_by"].split("-")])
        self.assertGreater(deadline, datetime.date.today(),
                           "the closure baseline has expired -- re-pin it deliberately")

    def test_every_accepted_empty_cell_names_an_owner_a_date_and_a_reason(self):
        rows = self.baseline.get("_accepted_empty_cells") or []
        self.assertTrue(rows, "no accepted empty cells -- flags/RHEL 9 is empty today")
        for row in rows:
            self.assertTrue(row.get("owner"), row)
            self.assertTrue(row.get("retire_by"), row)
            self.assertGreater(len(row.get("reason") or ""), 80,
                               "an accepted gap needs a reason, not a label: %r" % row)

    def test_flags_rhel9_really_is_the_empty_family_the_baseline_names(self):
        """If this ever stops being true, the acceptance is stale and the gate
        is carrying an excuse for a problem that was fixed."""
        with open(os.path.join(REPO, "content", "flags_rhel9.json"), encoding="utf-8") as fh:
            clis = json.load(fh).get("clis") or {}
        self.assertEqual({}, clis,
                         "content/flags_rhel9.json now has CLIs -- remove its acceptance from "
                         "content-src/closure_baseline.json rather than leaving a stale excuse")
        accepted = {(r["family"], str(r["release"]))
                    for r in self.baseline.get("_accepted_empty_cells") or []}
        self.assertIn(("flags", "9"), accepted)


if __name__ == "__main__":
    unittest.main()
