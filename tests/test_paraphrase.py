#!/usr/bin/env python3
"""test_paraphrase.py — Q14, the gate nobody had ever watched (AL-GATE3 §1, Q14 row).

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_paraphrase.py

ADR-001 §7.3 promised this file. It did not exist. Al Kowalski's Gate 3 review
put Q14 in the per-gate table as **Unverified — zero test coverage**, the one
gate where he could not rule out a fail-open *because there was nothing to run*:

    "No test_*.py drives gate_q14 or a shingle-collision fixture at all
     (contrast with Q10's test_accuracy_gate.py or Q17's test_render_audit.py).
     ADR-001 §7.3 promises tests/test_paraphrase.py with fixtures in both
     directions; that file does not exist in this revision."

Q14 is the legal gate. A man page under a licence that permits reading and not
reproduction is marked `paraphrase-only`, and the promise this product makes is
that nothing curated from such a source is lifted verbatim. The check is an
8-gram shingle collision between every curated string on a paraphrase-only entry
and every raw source staged under content-src/. If it is wrong, it is wrong
quietly, and the first person to find out is a lawyer.

Fixtures run in both directions, as the ADR asked:

  * planted    a sentence lifted word-for-word out of a real staged raw source,
               in notes and in a flag explanation, must FAIL.
  * clean      curated prose that says the same thing in its own words must PASS
               — a gate that flags honest paraphrase is a gate that gets turned
               off, and then the real one goes with it.
  * exempt     the same planted sentence on a verbatim-ok entry must PASS; the
               licence is the whole point of the distinction.
  * boundary   seven consecutive words must NOT collide and eight MUST, because
               "8-gram" is the actual promise and an off-by-one in either
               direction is a different gate than the one that was specified.

And the empty-input half, which is the AL-GATE3-004 shape applied to Q14: this
gate used to report PASS with the note "no raw sources present under
content-src/ — nothing to collide with". That is honest while nothing is staged.
It stops being honest the moment a populated flag dictionary ships for a release
whose raw sources are not there: the dictionary was extracted FROM those sources,
so their absence means the corpus Q14 compares against is not the corpus the
content came from, and every comparison it makes is vacuous.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import qa  # noqa: E402

RAW = os.path.join(REPO, "content-src", "raw")

PARAPHRASE_SOURCE = {
    "title": "sshd_config(5)",
    "url_or_man": "man:sshd_config(5)",
    "version": "openssh-8.7p1-38.el9",
    "retrieved_on": "2026-09-17",
    "license_class": "paraphrase-only",
}
VERBATIM_SOURCE = dict(PARAPHRASE_SOURCE, license_class="verbatim-ok")

CLEAN = ("Turn the setting off so the root account cannot open a session directly; "
         "administrators log in as themselves and elevate afterwards.")


def a_real_sentence(n_words=12):
    """n consecutive words lifted out of a real staged raw source.

    Taken from the corpus at run time rather than pasted into this file: a
    fixture that quotes a paraphrase-only man page is the thing Q14 exists to
    prevent, and it would also rot the moment the staged sources change.
    """
    import re
    for root, _dirs, files in os.walk(RAW):
        for name in sorted(files):
            if not name.endswith((".txt", ".md")):
                continue
            with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                toks = re.sub(r"[^a-z0-9\s-]", " ", f.read().lower()).split()
            # a run from the middle, away from headers and boilerplate
            if len(toks) > 400:
                return " ".join(toks[200:200 + n_words])
    return None


def entry(entry_id, source, notes=None, explain=None):
    e = {
        "id": entry_id,
        "source": dict(source),
        "rhel_versions": {v: {"command": "true"} for v in qa.VERSIONS},
        "flags": [],
    }
    if notes:
        e["rhel_versions"]["9"]["notes"] = notes
    if explain:
        e["flags"] = [{"flag": "-n", "explain": explain}]
    return e


class TheCorpusIsThere(unittest.TestCase):
    """Control zero: if there were no raw sources, every test below would be empty air."""

    def test_raw_sources_are_staged(self):
        self.assertTrue(os.path.isdir(RAW), "content-src/raw/ is missing")
        _staged, corpus = qa.raw_source_paths(REPO)
        self.assertGreater(len(corpus), 5, "too few staged raw files for this gate to mean anything")

    def test_a_sentence_can_be_lifted(self):
        self.assertTrue(a_real_sentence(), "no staged raw source long enough to plant from")


class ThePlantedSentenceIsCaught(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.grams = qa.raw_shingles(REPO)
        cls.lifted = a_real_sentence()

    def test_lifted_into_notes(self):
        failures = qa.paraphrase_failures([entry("e1", PARAPHRASE_SOURCE, notes=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "a sentence lifted word-for-word out of a paraphrase-only raw "
                                  "source survived Q14 inside rhel_versions[].notes")
        self.assertIn("e1", " ".join(failures))

    def test_lifted_into_a_flag_explanation(self):
        failures = qa.paraphrase_failures([entry("e2", PARAPHRASE_SOURCE, explain=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside a flag explanation")

    def test_lifted_but_licensed_verbatim_is_allowed(self):
        failures = qa.paraphrase_failures([entry("e3", VERBATIM_SOURCE, notes=self.lifted)],
                                          self.grams)
        self.assertEqual([], failures, "Q14 flagged a verbatim-ok entry; the licence class is the "
                                       "whole distinction this gate is about")

    def test_honest_paraphrase_passes(self):
        failures = qa.paraphrase_failures([entry("e4", PARAPHRASE_SOURCE, notes=CLEAN)], self.grams)
        self.assertEqual([], failures, "Q14 flagged prose written from scratch: %s" % failures)

    def test_the_shingle_length_is_the_one_that_was_promised(self):
        """Seven words must not collide; eight must. ADR-001 §7.3 says 8-gram."""
        short = a_real_sentence(7)
        long_enough = a_real_sentence(8)
        self.assertEqual([], qa.paraphrase_failures([entry("e5", PARAPHRASE_SOURCE, notes=short)],
                                                    self.grams),
                         "a seven-word overlap was flagged — the gate is stricter than the 8-gram "
                         "rule it documents, and honest paraphrase will trip it")
        self.assertTrue(qa.paraphrase_failures([entry("e6", PARAPHRASE_SOURCE, notes=long_enough)],
                                               self.grams),
                        "an eight-word verbatim run was NOT flagged — the gate is looser than the "
                        "8-gram rule it documents")

    def test_an_empty_corpus_collides_with_nothing(self):
        """Stated, so the next reader knows why the coverage check below exists."""
        self.assertEqual([], qa.paraphrase_failures(
            [entry("e7", PARAPHRASE_SOURCE, notes=self.lifted)], set()))


class TheCorpusMustCoverWhatShipped(unittest.TestCase):
    """A populated dictionary whose raw sources are absent makes Q14 vacuous."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mcr-q14-")
        os.makedirs(os.path.join(self.tmp, "content-src", "raw", "rhel8"))
        with open(os.path.join(self.tmp, "content-src", "raw", "rhel8", "sshd.man.txt"),
                  "w", encoding="utf-8") as f:
            f.write("some staged man page text\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _data(self, populated):
        return {"flags": {v: {"clis": ({"sshd": {}} if v in populated else {}),
                              "_meta": {"status": "x"}} for v in qa.VERSIONS}}

    def test_a_populated_dictionary_with_staged_sources_passes(self):
        self.assertEqual([], qa.raw_coverage_failures(self._data({"8"}), self.tmp))

    def test_a_populated_dictionary_with_no_staged_sources_fails(self):
        failures = qa.raw_coverage_failures(self._data({"8", "10"}), self.tmp)
        self.assertTrue(failures, "flags_rhel10.json ships a populated dictionary and no raw "
                                  "source for RHEL 10 is staged — Q14 is comparing the curated "
                                  "content against a corpus it did not come from, and reporting "
                                  "PASS")
        self.assertIn("10", " ".join(failures))

    def test_an_empty_dictionary_needs_nothing_staged(self):
        self.assertEqual([], qa.raw_coverage_failures(self._data(set()), self.tmp))

    def test_an_empty_raw_directory_does_not_count_as_coverage(self):
        os.makedirs(os.path.join(self.tmp, "content-src", "raw", "rhel9"))
        failures = qa.raw_coverage_failures(self._data({"9"}), self.tmp)
        self.assertTrue(failures, "an EMPTY content-src/raw/rhel9/ directory was accepted as "
                                  "coverage — a directory is not a corpus")

    def test_the_real_repo_is_covered(self):
        self.assertEqual([], qa.raw_coverage_failures(qa.build_ctx()["data"], REPO)
                         if qa.find_artifact() else [],
                         "a flags dictionary ships populated with no raw sources staged for it")


class TheWholeGate(unittest.TestCase):

    def test_q14_passes_on_the_shipped_bundle(self):
        if not qa.find_artifact():
            self.skipTest("no dist/ artifact — run python3 build.py first")
        ctx = qa.build_ctx()
        failures, details = qa.gate_q14(ctx)
        self.assertEqual([], failures, "Q14 fails on the shipped bundle:\n  " + "\n  ".join(failures))
        self.assertTrue(details)

    def test_q14_fails_when_a_planted_sentence_is_in_the_shipped_bundle(self):
        """End to end, through the gate, not only through the pure function."""
        if not qa.find_artifact():
            self.skipTest("no dist/ artifact — run python3 build.py first")
        ctx = qa.build_ctx()
        lifted = a_real_sentence()
        entries = ctx["data"]["commands"]["entries"]
        self.assertTrue(entries, "no entries to plant into")
        planted = json.loads(json.dumps(entries[0]))
        planted["source"] = dict(PARAPHRASE_SOURCE)
        planted["rhel_versions"]["9"] = dict(planted["rhel_versions"].get("9") or {},
                                             notes=lifted)
        ctx["data"]["commands"]["entries"] = [planted]
        failures, _ = qa.gate_q14(ctx)
        self.assertTrue(failures, "Q14 passed a bundle carrying a sentence lifted verbatim out of "
                                  "a paraphrase-only source")


if __name__ == "__main__":
    unittest.main(verbosity=2)
