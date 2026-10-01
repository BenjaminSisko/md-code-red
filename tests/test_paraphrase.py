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


def a_sentence_from(rel_path, n_words=12, offset=200):
    """n consecutive words lifted out of ONE named staged raw source.

    Unlike a_real_sentence() (first file found, alphabetical), this pulls
    from a specific file — needed to plant into an entry that names that file
    as its own source, the way gen-chronyd-one-shot-check cites
    content-src/raw/rhel8/chronyd.man.txt directly (the H1 near miss this
    fixture class re-creates: Milo Vance pasted chronyd(8) text into a
    curated field during H1 and caught it by hand before this gate existed
    to catch it for him).
    """
    import re
    path = os.path.join(REPO, rel_path)
    with open(path, encoding="utf-8", errors="replace") as f:
        toks = re.sub(r"[^a-z0-9\s-]", " ", f.read().lower()).split()
    assert len(toks) > offset + n_words, "%s too short to plant a fixture from" % rel_path
    return " ".join(toks[offset:offset + n_words])


def entry(entry_id, source, notes=None, explain=None, intent=None, verify=None,
          undo=None, fields=None, stig=None, flag_license_class=None):
    e = {
        "id": entry_id,
        "source": dict(source),
        "rhel_versions": {v: {"command": "true"} for v in qa.VERSIONS},
        "flags": [],
    }
    if notes:
        e["rhel_versions"]["9"]["notes"] = notes
    if explain:
        fl = {"flag": "-n", "explain": explain}
        if flag_license_class:
            fl["license_class"] = flag_license_class
        e["flags"] = [fl]
    if intent:
        e["intent"] = intent
    if verify:
        e["verify"] = verify
    if undo:
        e["undo"] = undo
    if fields:
        e["fields"] = fields
    if stig:
        e["stig"] = stig
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


class TheWidenedFieldsAreCaught(unittest.TestCase):
    """H1 gap (Milo Vance, self-flagged): Q14 scanned rhel_versions[].notes,
    .changed_in_note.what and flags[].explain, and nothing else. `intent`,
    `verify` and `undo` are copied into the clipboard comment header right
    alongside notes and explain (extract/schema.py HEADER_BOUND_FIELDS) —
    exactly the kind of field a paraphrase-only sentence gets pasted into —
    and a generator's fields[].label/.help never had a check at all. Every
    method here fails on the pre-widening curated_texts(); that is the point.
    """

    @classmethod
    def setUpClass(cls):
        cls.grams = qa.raw_shingles(REPO)
        cls.lifted = a_real_sentence()

    def test_lifted_into_intent(self):
        failures = qa.paraphrase_failures([entry("w1", PARAPHRASE_SOURCE, intent=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside `intent`")
        self.assertIn("w1", " ".join(failures))

    def test_lifted_into_verify(self):
        failures = qa.paraphrase_failures([entry("w2", PARAPHRASE_SOURCE, verify=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside `verify`")

    def test_lifted_into_undo(self):
        failures = qa.paraphrase_failures([entry("w3", PARAPHRASE_SOURCE, undo=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside `undo`")

    def test_lifted_into_a_generator_fields_label(self):
        failures = qa.paraphrase_failures(
            [entry("w4", PARAPHRASE_SOURCE, fields=[{"name": "x", "type": "comment",
                                                       "label": self.lifted}])],
            self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside a generator's "
                                  "fields[].label — the UI copy on a `template` entry's form")

    def test_lifted_into_a_generator_fields_help(self):
        failures = qa.paraphrase_failures(
            [entry("w5", PARAPHRASE_SOURCE, fields=[{"name": "x", "type": "comment",
                                                       "help": self.lifted}])],
            self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside a generator's "
                                  "fields[].help")

    def test_lifted_into_a_stig_row_note(self):
        """Schema does not define stig[].notes today; a future one must not be a silent hole."""
        failures = qa.paraphrase_failures(
            [entry("w6", PARAPHRASE_SOURCE, stig=[{"stig_id": "X", "rhel_version": "9",
                                                     "notes": self.lifted}])],
            self.grams)
        self.assertTrue(failures, "a lifted sentence survived Q14 inside a stig[] row's notes")

    def test_honest_paraphrase_in_every_widened_field_still_passes(self):
        """A gate that flags honest paraphrase in the new fields is as useless as one that
        flags it in the old ones — same rule from ThePlantedSentenceIsCaught, re-run here."""
        e = entry("w7", PARAPHRASE_SOURCE, intent=CLEAN, verify=CLEAN, undo=CLEAN,
                  fields=[{"name": "x", "type": "comment", "label": CLEAN, "help": CLEAN}],
                  stig=[{"stig_id": "X", "rhel_version": "9", "notes": CLEAN}])
        self.assertEqual([], qa.paraphrase_failures([e], self.grams),
                         "Q14 flagged prose written from scratch in a widened field")


class TheFlagLicenseClassOverride(unittest.TestCase):
    """The real gap this tranche found while auditing the 27 shipped entries:
    firewalld-service-active, journald-service-active and ctrl-alt-del-target-
    masked all cite a verbatim-ok DISA STIG at entry.source, but carry
    individual flags[] marked license_class: paraphrase-only (systemctl's
    `status`/`is-active` behaviour is documented, not STIG text). Under the
    old entry-level gate — `if entry.source.license_class != "paraphrase-
    only": continue` before curated_texts() ever ran — none of those flags'
    `explain` text was checked at all. The fix makes the check per-field: a
    flag's own license_class overrides the entry's.
    """

    @classmethod
    def setUpClass(cls):
        cls.grams = qa.raw_shingles(REPO)
        cls.lifted = a_real_sentence()

    def test_a_paraphrase_only_flag_is_caught_even_under_a_verbatim_ok_entry(self):
        e = entry("o1", VERBATIM_SOURCE, explain=self.lifted, flag_license_class="paraphrase-only")
        failures = qa.paraphrase_failures([e], self.grams)
        self.assertTrue(failures, "a flag explicitly marked license_class: paraphrase-only was "
                                  "not checked because its entry's own source is verbatim-ok — "
                                  "this is the exact shape of firewalld-service-active's `status` "
                                  "and `is-active` flags")

    def test_a_verbatim_ok_flag_is_exempt_even_under_a_paraphrase_only_entry(self):
        """The inverse case, so the override is proven to cut both ways, not just widen scope."""
        e = entry("o2", PARAPHRASE_SOURCE, explain=self.lifted, flag_license_class="verbatim-ok")
        failures = qa.paraphrase_failures([e], self.grams)
        self.assertEqual([], failures, "a flag explicitly marked license_class: verbatim-ok was "
                                       "flagged anyway — the entry's paraphrase-only source must "
                                       "not override a flag's own, more specific, license_class")


class TheChronydNearMiss(unittest.TestCase):
    """The H1 incident this whole tranche is named for, re-created as a fixture.

    gen-chronyd-one-shot-check cites content-src/raw/rhel8/chronyd.man.txt
    directly (source.url_or_man = "content-src/raw/rhel8/chronyd.man.txt#L68")
    and is paraphrase-only. Milo Vance pasted a run of that man page's text
    into a curated field during H1 and caught it by hand before Q14 covered
    that field. This fixture plants the same shape of mistake — a real,
    deterministic run of words out of that exact file — into `notes` (already
    covered before this tranche; a locked-in regression check) and into
    `intent` (the field that was actually blind).
    """

    CHRONYD_MAN = "content-src/raw/rhel8/chronyd.man.txt"

    @classmethod
    def setUpClass(cls):
        cls.grams = qa.raw_shingles(REPO)
        cls.lifted = a_sentence_from(cls.CHRONYD_MAN)

    def test_lifted_from_chronyd_man_into_notes(self):
        failures = qa.paraphrase_failures([entry("h1-notes", PARAPHRASE_SOURCE, notes=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "text lifted verbatim from chronyd(8) survived Q14 inside `notes`")

    def test_lifted_from_chronyd_man_into_intent(self):
        failures = qa.paraphrase_failures([entry("h1-intent", PARAPHRASE_SOURCE, intent=self.lifted)],
                                          self.grams)
        self.assertTrue(failures, "text lifted verbatim from chronyd(8) survived Q14 inside "
                                  "`intent` — the field the real gen-chronyd-one-shot-check entry "
                                  "carries its paraphrased explanation in")

    def test_the_real_entry_is_clean(self):
        """gen-chronyd-one-shot-check itself, exactly as shipped: proves Milo's hand-fix holds,
        not just that a synthetic fixture works."""
        with open(os.path.join(REPO, "content", "commands.json"), encoding="utf-8") as f:
            data = json.load(f)
        real = [e for e in data["entries"] if e["id"] == "gen-chronyd-one-shot-check"]
        self.assertTrue(real, "gen-chronyd-one-shot-check is missing from content/commands.json")
        failures = qa.paraphrase_failures(real, self.grams)
        self.assertEqual([], failures, "the real gen-chronyd-one-shot-check entry now collides "
                                       "with its own cited source: %s" % failures)


class TheGuideAttestationReceipt(unittest.TestCase):
    """The offline-mechanism decision for a guide-cited entry (task framing: 'decide whether
    Q14 can check against the guides offline ... or whether entries that cite a guide must
    carry a paraphrase_attested_by receipt instead'). Chosen: the second one. Guide prose is
    not staged under content-src/raw/ (staging it would itself be the verbatim copy the
    licensing ruling exists to prevent — see qa.source_is_offline_checkable's docstring), so
    Q14 cannot shingle-check a guide citation at all; it requires a human receipt instead,
    reusing the roster/two-person-rule infrastructure gate_q16 already has.
    """

    GUIDE_SOURCE = dict(PARAPHRASE_SOURCE, title="RHEL 9 Security Hardening Guide",
                        url_or_man="https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/security_hardening")

    def test_a_guide_citation_with_no_receipt_fails(self):
        e = entry("g1", self.GUIDE_SOURCE)
        failures = qa.attestation_failures([e])
        self.assertTrue(failures, "a paraphrase-only entry citing a Red Hat guide URL, with no "
                                  "paraphrase_attested_by receipt, was not flagged")
        self.assertIn("g1", " ".join(failures))

    def test_a_guide_citation_with_a_valid_qa_receipt_passes(self):
        src = dict(self.GUIDE_SOURCE, paraphrase_attested_by={"by": "Riley Park", "on": "2026-09-17"})
        failures = qa.attestation_failures([entry("g2", src)])
        self.assertEqual([], failures, "a valid QA-role receipt on content-src/roster.json was "
                                       "not accepted: %s" % failures)

    def test_a_receipt_from_someone_off_the_roster_fails(self):
        src = dict(self.GUIDE_SOURCE, paraphrase_attested_by={"by": "Nobody Nowhere", "on": "2026-09-17"})
        failures = qa.attestation_failures([entry("g3", src)])
        self.assertTrue(failures, "a paraphrase_attested_by.by name not on content-src/roster.json "
                                  "was accepted")

    def test_a_receipt_from_a_non_qa_role_fails(self):
        """Caleb Stone and Renata Osei are SME, not QA, on content-src/roster.json."""
        src = dict(self.GUIDE_SOURCE, paraphrase_attested_by={"by": "Caleb Stone", "on": "2026-09-17"})
        failures = qa.attestation_failures([entry("g4", src)])
        self.assertTrue(failures, "an SME-only name was accepted as a paraphrase_attested_by.by — "
                                  "this receipt names who reviews the paraphrase, the QA role")

    def test_a_man_page_citation_needs_no_receipt(self):
        """Control: every one of the 27 shipped entries cites a man page or DISA STIG, never a
        guide URL, so none of them should need this receipt at all."""
        src = dict(PARAPHRASE_SOURCE, url_or_man="content-src/raw/rhel8/chronyd.man.txt#L68")
        failures = qa.attestation_failures([entry("g5", src)])
        self.assertEqual([], failures, "a man-page citation staged under content-src/raw/ was "
                                       "told it needed a receipt Q14 can already check offline")

    def test_the_27_shipped_entries_need_no_receipt(self):
        with open(os.path.join(REPO, "content", "commands.json"), encoding="utf-8") as f:
            data = json.load(f)
        failures = qa.attestation_failures(data["entries"])
        self.assertEqual([], failures, "a shipped entry now needs a paraphrase_attested_by "
                                       "receipt this repo has never carried: %s" % failures)


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
        ctx = qa.build_ctx_if_current()
        if not ctx:
            self.skipTest("artifact is missing or stale — run python3 build.py first")
        self.assertEqual([], qa.raw_coverage_failures(ctx["data"], REPO),
                         "a flags dictionary ships populated with no raw sources staged for it")


class TheWholeGate(unittest.TestCase):

    def test_q14_passes_on_the_shipped_bundle(self):
        ctx = qa.build_ctx_if_current()
        if not ctx:
            self.skipTest("artifact is missing or stale — run python3 build.py first")
        failures, details = qa.gate_q14(ctx)
        self.assertEqual([], failures, "Q14 fails on the shipped bundle:\n  " + "\n  ".join(failures))
        self.assertTrue(details)

    def test_q14_fails_when_a_planted_sentence_is_in_the_shipped_bundle(self):
        """End to end, through the gate, not only through the pure function."""
        ctx = qa.build_ctx_if_current()
        if not ctx:
            self.skipTest("artifact is missing or stale — run python3 build.py first")
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
