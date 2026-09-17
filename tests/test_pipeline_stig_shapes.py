#!/usr/bin/env python3
"""test_pipeline_stig_shapes.py - CR-T-31 / ADR-002.

DISA's own STIG check text is full of pipelines. Al Kowalski's ADR-002 put the
consequence plainly: a command corpus that cannot compose cannot express the
checks the corpus itself contains, so the Founder's two asks -- every command,
and pipes -- are one requirement.

This test re-derives the measurement in tests/fixtures/stig-pipeline-shapes.json
from the STIG rules embedded in content/rules_rhel{7,8,9,10}.json, so the claim
"the closed operator set expresses the shapes a real DISA check uses" cannot go
stale the way a hand-written number does. It asserts three things:

  1. Every top-level shell operator the corpus actually uses is either in the
     closed operator set or is named in the fixture's out_of_scope list WITH a
     reason. An operator that is neither is a FINDING about the operator set --
     reported here, loudly -- and never a reason to widen the set quietly.
  2. The fraction of operator-bearing command lines the set can fully express
     stays at or above the fixture's stated floor.
  3. The out_of_scope list is non-empty and every entry carries a reason, so
     assertion 1 cannot pass by declaring everything out of scope.

WHY THE COUNTING IS THE WAY IT IS. Operators are counted at TOP LEVEL only:
text inside single quotes, double quotes, backticks, $( ) and after a backslash
is skipped. Without that, awk's `($3>=1000)&&($7 !~ /nologin/)` contributes a
`>` and an `&&` and find's `-exec ... \\;` contributes a `;`, and the measurement
says the corpus uses three operators it does not use. The naive count was 703
pipes, 68 semicolons and 35 ampersands; the honest one is 625, 22 and 6.
"""
import glob
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "stig-pipeline-shapes.json")

# The operator emissions the composer owns, restated here rather than parsed out
# of template.html: this test is an INDEPENDENT check on the set, and reading
# the set out of the code it is checking would make it agree with itself.
CLOSED_SET = {"|", "&&", "||", ";", ">", ">>", "2>", "2>&1"}

# Longest match first, so "2>&1" is never read as "2>" and ">>" never as ">".
OPERATOR_TOKENS = ["2>&1", "2>>", "2>", "|&", "||", "|", ">>", ">", "&&", ";"]


def top_level_operators(cmd):
    """Every shell operator in `cmd` that a shell would actually act on."""
    out, i, n, depth = [], 0, len(cmd), 0
    while i < n:
        c = cmd[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = cmd.find("'", i + 1)
            i = n if j < 0 else j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n:
                if cmd[j] == "\\":
                    j += 2
                    continue
                if cmd[j] == '"':
                    break
                j += 1
            i = j + 1
            continue
        if c == "`":
            j = cmd.find("`", i + 1)
            i = n if j < 0 else j + 1
            continue
        if cmd.startswith("$(", i):
            depth += 1
            i += 2
            continue
        if c == "(" and depth > 0:
            depth += 1
            i += 1
            continue
        if c == ")" and depth > 0:
            depth -= 1
            i += 1
            continue
        if depth > 0:
            i += 1
            continue
        hit = None
        for tok in OPERATOR_TOKENS:
            if cmd.startswith(tok, i):
                hit = tok
                break
        if hit:
            out.append(hit)
            i += len(hit)
            continue
        i += 1
    return out


PROMPT_RE = re.compile(r"^[\$#]\s*(.+)$")
COMMANDISH_RE = re.compile(r"^(sudo\s+)?[a-z][a-z0-9_.-]*(\s|$)")
LOOP_RE = re.compile(r"\bfor\b.*\bdo\b|\bwhile\b.*\bdo\b|\bfunction\b")


def measure():
    """Re-derive the corpus measurement from the embedded STIG rules."""
    op_counts, lines, with_op, expressible = {}, 0, 0, 0
    for path in sorted(glob.glob(os.path.join(REPO, "content", "rules_rhel*.json"))):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for rule in data.get("rules", []):
            for field in ("chk", "fix"):
                for raw in (rule.get(field) or "").split("\n"):
                    m = PROMPT_RE.match(raw.strip())
                    if not m:
                        continue
                    cmd = m.group(1).strip()
                    if not COMMANDISH_RE.match(cmd):
                        continue
                    lines += 1
                    found = top_level_operators(cmd)
                    if not found:
                        continue
                    with_op += 1
                    for tok in found:
                        op_counts[tok] = op_counts.get(tok, 0) + 1
                    substitution = "$(" in cmd or "`" in cmd
                    loop = bool(LOOP_RE.search(cmd))
                    if all(t in CLOSED_SET for t in found) and not substitution and not loop:
                        expressible += 1
    return {"operators": op_counts, "command_lines": lines,
            "lines_with_operator": with_op, "expressible": expressible}


class TheClosedSetAgainstDisasOwnCheckText(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, "r", encoding="utf-8") as fh:
            cls.fixture = json.load(fh)
        cls.measured = measure()

    def test_the_corpus_is_not_empty(self):
        """Control first: a measurement over nothing would satisfy everything below."""
        self.assertGreater(self.measured["command_lines"], 500,
                           "fewer than 500 command lines were found in the embedded STIG rules -- "
                           "the corpus collapsed and every assertion below is vacuous")
        self.assertGreater(self.measured["lines_with_operator"], 100,
                           "fewer than 100 STIG command lines carry a top-level operator, which "
                           "contradicts the premise of this test")

    def test_every_operator_the_corpus_uses_is_expressible_or_named_out_of_scope(self):
        out_of_scope = {row["name"] for row in self.fixture["out_of_scope"]}
        self.assertTrue(out_of_scope, "the fixture declares nothing out of scope, so this test "
                                      "could pass by declaring everything out of scope")
        for row in self.fixture["out_of_scope"]:
            self.assertTrue(row.get("why", "").strip(),
                            "out_of_scope entry %r carries no reason" % row["name"])
        for token, count in sorted(self.measured["operators"].items()):
            with self.subTest(operator=token):
                self.assertIn(token, CLOSED_SET,
                              "the operator %r occurs %d times at top level in the embedded STIG "
                              "rules and the closed set cannot express it. That is a FINDING about "
                              "the operator set -- record it in the fixture's known_findings and "
                              "put it to the Founder -- and never a reason to widen the set "
                              "quietly." % (token, count))

    def test_the_expressible_fraction_holds(self):
        floor = self.fixture["min_expressible_ratio"]
        ratio = self.measured["expressible"] / float(self.measured["lines_with_operator"])
        self.assertGreaterEqual(
            ratio, floor,
            "only %.2f%% of the STIG command lines carrying a top-level operator can be expressed "
            "by the closed set, below the %.2f%% floor this fixture states. A command corpus that "
            "cannot compose cannot express the checks the corpus itself contains."
            % (ratio * 100, floor * 100))

    def test_the_fixture_has_not_drifted_from_the_corpus(self):
        """The recorded numbers are re-derived, not trusted."""
        recorded = {row["token"]: row["count"] for row in self.fixture["corpus_operators"]}
        self.assertEqual(recorded, self.measured["operators"],
                         "tests/fixtures/stig-pipeline-shapes.json no longer matches the embedded "
                         "STIG rules. Regenerate it: a stale measurement is an expressibility "
                         "claim about content that is no longer in this build")
        self.assertEqual(self.fixture["lines_with_a_top_level_operator"],
                         self.measured["lines_with_operator"])
        self.assertEqual(self.fixture["lines_fully_expressible"], self.measured["expressible"])

    def test_the_counting_excludes_operators_that_are_not_operators(self):
        """The negative control for the measurement itself.

        A naive scanner counts awk's comparison and find's -exec terminator as
        shell operators, which inflates every number in the fixture and would
        make the expressibility ratio look worse than it is on shapes the set
        was never asked to express.
        """
        self.assertEqual([], top_level_operators(
            "awk -F: '($3>=1000)&&($7 !~ /nologin/){print $6}' /etc/passwd"),
            "an awk program's own >= and && were counted as shell operators")
        self.assertEqual([], top_level_operators(
            "find / -type d -perm -0002 -exec ls -ld {} \\;"),
            "find's -exec terminator was counted as a statement separator")
        self.assertEqual(["|"], top_level_operators(
            "grep -i 'a|b' /etc/foo | wc -l"),
            "a pipe inside a quoted pattern was counted, or the real pipe was missed")
        self.assertEqual(["2>&1", "|"], top_level_operators(
            "sshd -dd 2>&1 | awk '/filename/ {print $4}'"),
            "2>&1 was read as 2> followed by something else")


if __name__ == "__main__":
    unittest.main()
