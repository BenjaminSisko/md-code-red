#!/usr/bin/env python3
"""test_mine_commands.py -- the miner's refusals, proven on lines that get past
the primitive they are protecting.

Threat model v2, M4: `su -c`, `sh -c` and `env VAR=value` prefixes go to
RESIDUE, not to parsing. A test that only asserts "classify() returns a reason"
proves nothing on its own -- a function that refused EVERY line would pass it.
So each case here also asserts the thing M4 is protecting against: that
`schema.command_head()`, the primitive the miner would otherwise have used,
resolves the same line to a program name and would have produced a record.

That pairing is the negative control. It is what distinguishes "M4 is enforced"
from "the corpus happens not to contain one today", and it is why these cases
are written from the REAL lines the pre-M4 extractor mined into the product:

  BINFMTFS_MAGIC=0x42494e4d          -> filed under the tool `shell`
  CERT=`cat ad_user_cert.pem | ...`  -> filed under the TOOL `ad_user_cert.pem`
  DCONF_PROFILE=gdm gsettings ...    -> filed under `gsettings`

None of the three is a command. All three counted as `classified` AND as
`recorded`, so the residue ledger balanced while they sat in the product under a
citation -- TM2-F1 exactly.
"""

import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "extract"))

import mine_commands as mine  # noqa: E402
import schema  # noqa: E402

CORPUS = os.path.join(REPO, "content", "reference_commands.json")

# Lines lifted from the pre-M4 corpus, plus the two wrapper shapes M4 names
# explicitly. Every one of them resolves to a head through command_head().
ENV_PREFIXED = (
    "BINFMTFS_MAGIC=0x42494e4d",
    "BUCKET=<bucketname>",
    "DCONF_PROFILE=gdm gsettings list-recursively org.gnome.login-screen",
    "KRB5_TRACE=/dev/stdout kinit admin",
    "NO_COLOR=1 c \"How to install python?\"",
    "machine_id=$(cat /etc/machine-id)",
)
WRAPPER_PREFIXED = (
    "su -c 'grep -i pam_faillock /etc/pam.d/system-auth'",
    "sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'",
    "bash -c 'systemctl is-enabled auditd'",
    "env LANG=C rpm -qa",
)


def classify(text, prompt="#", policy="lowercase"):
    """classify() with a vocabulary wide enough that nothing here is refused for
    lack of evidence. If M4 were removed, these lines would be ACCEPTED."""
    vocab = {"gsettings", "kinit", "c", "cat", "grep", "echo", "systemctl", "rpm",
             "su", "sh", "bash", "env"}
    return mine.classify(text, prompt, policy, vocab, set(), strong=vocab)


class M4RefusesEnvAssignmentPrefixes(unittest.TestCase):

    def test_the_primitive_would_have_parsed_every_one_of_these(self):
        """The negative control. Without this, the cases below prove nothing."""
        resolved = []
        for text in ENV_PREFIXED:
            stages = schema.split_stages(text)
            self.assertTrue(stages, text)
            head = schema.command_head(stages[0])
            if head:
                resolved.append((text, head))
        self.assertGreaterEqual(
            len(resolved), 4,
            "command_head() no longer resolves these lines, so M4's refusal is "
            "guarding nothing and these cases have stopped being a test")

    def test_every_env_prefixed_line_is_refused(self):
        for text in ENV_PREFIXED:
            tool, reason = classify(text)
            self.assertIsNone(tool, "M4: %r was parsed as the tool %r" % (text, tool))
            self.assertEqual(mine.REFUSED_ENV_PREFIX_REASON, reason, text)

    def test_the_refusal_reason_is_in_the_closed_set(self):
        self.assertIn(mine.REFUSED_ENV_PREFIX_REASON, mine.RESIDUE_REASONS)
        self.assertIn(mine.REFUSED_WRAPPER_REASON, mine.RESIDUE_REASONS)

    def test_an_env_prefixed_line_cannot_vouch_for_a_head(self):
        """collect_strong_heads() must refuse the same shape, or the refusal is
        cosmetic: the evidence pass would promote `gsettings` off a line M4
        declined, and the head would then carry other lines through."""
        candidates = [{"text": "DCONF_PROFILE=gdm gsettings list-recursively org.gnome.login-screen",
                       "prompt": "$"}]
        self.assertEqual(set(), mine.collect_strong_heads(candidates))
        # Positive control: the same line WITHOUT the assignment prefix does vouch.
        candidates = [{"text": "gsettings list-recursively org.gnome.login-screen",
                       "prompt": "$"}]
        self.assertEqual({"gsettings"}, mine.collect_strong_heads(candidates))


class M4RefusesShellWrapperPrefixes(unittest.TestCase):

    def test_every_wrapper_prefixed_line_is_refused(self):
        for text in WRAPPER_PREFIXED:
            tool, reason = classify(text)
            self.assertIsNone(tool, "M4: %r was parsed as the tool %r" % (text, tool))
            self.assertIn(reason, mine.RESIDUE_REASONS, text)

    def test_the_refused_head_set_names_the_shapes_m4_names(self):
        for head in ("su", "sh", "env"):
            self.assertIn(head, schema.REFUSED_HEADS)


class TheShippedCorpusHoldsM4(unittest.TestCase):
    """M4 asserted against the product, not only against the function. A rule
    enforced in classify() and violated in content/ is not enforced."""

    @classmethod
    def setUpClass(cls):
        with open(CORPUS, encoding="utf-8") as fh:
            cls.records = json.load(fh)["commands"]

    def test_no_record_is_headed_by_an_assignment(self):
        bad = [r["id"] for r in self.records
               if schema.ENV_ASSIGN_RE.match((schema.split_tokens(r["c"]) or [""])[0])]
        self.assertEqual([], bad[:20], "%d record(s) head-assigned" % len(bad))

    def test_no_record_resolves_to_a_refused_wrapper(self):
        bad = []
        for r in self.records:
            stages = schema.stage_binaries(r["c"])
            if stages and stages[0] in schema.REFUSED_HEADS:
                bad.append(r["id"])
        self.assertEqual([], bad[:20], "%d record(s) headed by a refused wrapper" % len(bad))

    def test_no_record_is_filed_under_the_tool_shell(self):
        """`shell` was never a binary. It was the label the pre-M4 extractor
        reached for when the head it wanted did not exist."""
        self.assertEqual([], [r["id"] for r in self.records if r["t"] == "shell"])


if __name__ == "__main__":
    unittest.main()
