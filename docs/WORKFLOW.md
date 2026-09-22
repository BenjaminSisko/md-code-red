# Content Pipeline & Refresh Workflow

The exact pipeline this repo runs, as verified against the code and the 2026-09-17
build. Where a step is a company-record process outside this repo (SME staffing,
review board membership), this file points at the record rather than restating it
-- see `docs/DESIGN_INDEX.md` for those paths.

## 1. Sources & Extraction

Four source families feed the build, each with its own extractor and its own
staged-raw archive for licensing audit:

| Family | Source | Extractor | Output |
|---|---|---|---|
| STIG rules + CCI map | Pinned DISA XCCDF zips in `stig-src/`, hash-verified against `stig-src/SHA256SUMS` before parsing | `extract/parse_xccdf.py` | `content/rules_rhel{7,8,9,10}.json`, `content/cci_nist.json` |
| CLI flags/options | `man -P cat`/`--help` output read (read-only, no `sudo`) from a real host over SSH, or from a UBI7 container standing in for RHEL 7 | `extract/extract_flags.py` | `content/flags_rhel<N>.json`, raw text staged under `content-src/raw/rhel<N>/` |
| STIG-linked evidence | SME-run captures under `tests/captures/<rhel_version>/<entry_id>.json` | `extract/import_captures.py` | `content/expected_output.json` |
| Ansible module/flag docs | `ansible-doc --json`, CLI `--help` | `extract/extract_ansible_doc.py` | `content/modules.json`, `content/flags.json` -- **not currently loaded by `build.py`'s `CONTENT` map**; this extractor predates the RHEL-focused product and its output does not reach the shipped artifact |

Every extractor that produces content committed to `content/` supports a
`--check` mode: re-run the same parse (against the pinned zips, or against the
already-staged raw text -- neither needs a live host or network) into a temp
location and diff it byte-for-byte against what is committed. `qa.py`'s Q15 gate
calls every extractor's `--check` mode and fails the build if a re-run does not
reproduce the committed content exactly, so a hand-edited generated file cannot
silently drift from what its own extractor would produce.

**Command intent, notes, and flag curation are hand-authored, not extracted.**
`content/commands.json`, `content/tools.json`, and `content/dangerous.json` are
curated directly by an RHEL SME and never regenerated from a script -- see
Section 3.

## 2. Content JSON Schema

The schema is stated once, in `extract/schema.py`, and imported by both
`build.py`'s `validate()` and `tests/test_schema.py` -- there is no second,
looser definition anywhere else. Full field-by-field shapes for a command entry,
a tool, a rule, a flag dictionary, and a capture record are in
`docs/ARCHITECTURE_BIBLE.md` Section 4; this section states only the promises
that make the pipeline trustworthy:

- Every command entry, flag, rules dataset, the CCI map, and the destructive-
  pattern table carry all five provenance fields (`title`, `url_or_man`,
  `version`, `retrieved_on`, `license_class`) -- enforced at build time by
  `extract/schema.py`'s `provenance_errors()` and independently re-checked
  against the shipped artifact by `qa.py`'s Q3.
- A flag's `explain` is `null` until a human curates original paraphrase for it
  (man pages are GPL-2.0-or-later; the extractor never writes prose) -- and once
  any flag dictionary ships non-empty, an uncurated `explain: null` on a
  `commands.json` entry's own `flags[]` becomes a schema error, so a static
  entry cannot ship silently uncurated once the dictionary that could answer it
  exists.
- No curated string may share an 8-word run with any staged raw source
  (`tests/test_paraphrase.py`, `qa.py`'s Q14) -- the mechanical floor under
  "paraphrase, don't copy."

### 2a. Content Validation Protocol -- capture records and per-version `verified`

The full protocol (who runs what, on which host, under what safety rules) is
Riley Park's and Caleb Stone's company record, not a repo file:
`07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md` Part B, section 7-11. This
section is a pointer into it plus the two rules that are actually enforced in
this repo's code.

- **Canonical capture path** (Eli Cross ruling, closing an earlier three-way
  path mismatch): `tests/captures/<rhel_version>/<entry_id>.json`, one JSON file
  per entry per RHEL version, read by `extract/import_captures.py` and enforced
  by `qa.py`'s Q16 gate. This is the only storage location -- the protocol
  document's own Appendix is a pointer to this path, not a second tree.
- **`verify_result` and `command_hash_at_capture` are mandatory capture-record
  fields**, not optional narrative. `extract/import_captures.py`'s
  `REQUIRED_FIELDS` and `qa.py`'s `CAPTURE_REQUIRED_FIELDS` both refuse a
  capture record missing either. (The written protocol document's own field
  table has not yet been updated to list both explicitly, even though the code
  has enforced both since this rule was adopted -- a documentation gap in the
  company-record file, not a difference in what is actually enforced; that edit
  belongs to that file's own owners, not to this repo.)
- **`verified` is per RHEL version, not per entry** (a CEO ruling: a single
  whole-entry `verified` flag could not be set for a real batch of captures
  without overclaiming a version nobody actually ran). `content/commands.json`'s
  `verified` field is an object keyed `"7"`/`"8"`/`"9"`/`"10"`, each value
  `false` or a `{by, on, host, capture}` receipt naming the QA reviewer, the
  date, the host, and the capture file that backs it. A version whose row is
  `unavailable` or a `same_as` pointer can never carry a receipt of its own --
  it was never independently run -- and a `same_as` target's receipt never
  propagates onto the version pointing at it.

**The flow, end to end, per entry per RHEL version:**

1. **SME captures.** The RHEL SME (Caleb Stone, or a named delegate) runs the
   entry's command on a real host of the stated version, writes the capture
   record under `tests/captures/`, and sets nothing in `content/commands.json`
   -- a capture record on its own asserts nothing about `verified`.
2. **QA reviews.** The QA reviewer (Riley Park, in this build's history)
   independently re-runs or re-derives from the capture's own evidence. For each
   (entry, version) pair cleared, she writes a receipt into
   `content/commands.json`'s `verified[version]`.
3. **`qa.py`'s Q16 gate enforces the pairing on every build**: the receipt's
   `capture` path must resolve to a real file for that exact (entry, version)
   pair; its `command_hash_at_capture` must match `sha256(command_as_run)`; its
   `command_as_run` must still match the command this build actually assembles
   for that version today (a fixed command diffs against the shipped,
   `same_as`-resolved artifact; a generator entry diffs against the
   hand-authored validity oracle in `tests/fixtures/golden-commands.json`,
   since a generator has no single "current" command to diff without one); and
   the receipt's `by` and the capture's `captured_by`, both normalized
   (casefold, collapsed whitespace, one stripped trailing parenthetical) and
   checked against the closed roster in `content-src/roster.json`, must never
   be the same person -- the SME who ran it is never the QA reviewer who
   verified it, and a name not on the roster does not resolve, full stop,
   regardless of whose alias it might be.
4. See `tests/captures/README.md` for a worked example (Caleb Stone's real run
   against `defiant`/`saratoga`) and `docs/QA_GATES.md`'s Q16 row for the exact
   gate mechanics and every negative case it has been watched fail against.

This build's state: 18 capture files validated and folded, 5 of them carrying a
STIG mapping this content can index (the other 13 validated but with no `stig[]`
row to join onto), and 18 of 108 possible (entry x RHEL-version) pairs carrying a
verified receipt. See `docs/USER_GUIDE.md`'s Known Limitations for the same
numbers from the operator's side.

## 3. Content Review

No formal, seated content review board is codified in this repo -- the roles that
exist in practice, read off the commit history and the roster this pipeline
actually checks against, are:

- **RHEL SME** (`content-src/roster.json`'s `SME` role -- Caleb Stone, Renata
  Osei in this build): authors and captures command syntax.
- **QA** (`content-src/roster.json`'s `QA` role -- Riley Park): independently
  verifies captures and writes `verified` receipts (Section 2a).
- **Security** (Marcus Reed, by commit history): reviews the assembler, the
  render sinks, and the QA gates themselves -- not content per se, but every
  content shape the assembler and the gates have to accept or refuse.

The roster file is the one place these roles are machine-checked (Section 2a's
two-person rule); there is no separate sign-off document this pipeline reads.

## 4. Build Assembly

`python3 build.py`, stdlib only: load every file in `CONTENT` (fail loud if one
is missing or is not valid JSON), validate against `extract/schema.py`, assemble
(`same_as` resolution with cycle detection, STIG reverse links, the search-index
seed, joining `expected_output.json`'s captures onto `commands.json`'s `stig[]`
rows), then substitute the JSON payload and five identity tokens
(`__APP_NAME__`, `__VERSION__`, `__BUILT_DATE__`, `__CLASSIFICATION__`,
`__CONTENT_FINGERPRINT__`) into `template.html`. Output:
`dist/md-code-red_<version>.html` plus a `.sha256` sidecar. See
`docs/ARCHITECTURE_BIBLE.md` Section 2 for the full pipeline diagram and Section
3 for what each file does.

## 5. QA Gate

`python3 qa.py` runs 26 independent gates plus an optional `node --check`
against the **shipped artifact** (not `content/` -- that is `build.py`'s own
`validate()`, a separate check). Every gate, what it proves, how it has been
watched fail, and what it explicitly does not prove is `docs/QA_GATES.md`, not
restated here. The full local verification sequence, in order:

```
git clean -fdx dist && python3 build.py
python3 qa.py
python3 -m unittest discover -s tests
node tests/hostile_harness.js
```

`git clean -fdx dist`, never `rm -rf dist`: `dist/` has carried tracked release
artifacts (the shipped `.html`, its `.sha256` sidecar, its `.provenance.json`)
since v1.0.0-alpha.1 was tagged, and `build.py` does not regenerate all three
on its own -- `rm -rf dist` deletes committed files a plain rebuild will not
restore. `git clean -fdx dist` removes only what git does not track.

All four must be green before a branch is considered mergeable -- this is the
same sequence `docs/ARCHITECTURE_BIBLE.md`'s rebuild verification checklist
walks through with expected output numbers for this build.

## 6. Release & Distribution

Releases are prepared and verified locally, merged through a release pull
request, mirrored to Forgejo, and published as a GitHub prerelease. There is no
publisher-signing identity in this repository. Until an authorized release key
is provisioned, release notes and receipts must say **unsigned**. When a key is
provisioned, follow `docs/RELEASE_SIGNING.md`; the tooling requires an explicit
key fingerprint and verifies both the detached signature and every artifact
digest. SHA-256 without that signature proves integrity, not publisher identity.

The browser's reference export and a real execution receipt are separate
artifacts. `docs/EXECUTION_EVIDENCE.md` defines the latter and the validated v1
format; never infer execution from expected output or the reference export.
There is no automated release workflow or protected-branch check in this
repository; a publisher must
run and record every step below. A GitHub release is publication, not deployment
or pilot acceptance. Transfer to a receiving host still follows that enclave's
approved channel and `docs/DEPLOY_RECEIPT_TEMPLATE.md`.

1. **Prepare one final-version candidate.** Start from synchronized, clean
   `main` and confirm that the proposed tag and release do not already exist.
   Set `APP_VERSION` and the pinned `APP_BUILD_DATE` together in `build.py`,
   update the matching current-version documentation and fixtures, and move the
   prior release's three files from `dist/` to its versioned directory under
   `releases/` only if that archival move has not already happened. Never alter
   an archived file or an existing tag.
2. **Build the candidate and placeholder provenance.** Run:

   ```text
   git clean -fdx dist && python3 build.py
   python3 extract/make_provenance.py
   ```

   Before merge, `git_commit` must be `TAG_COMMIT_PLACEHOLDER`: the merge commit
   that the release tag will identify does not exist yet. Verify the generated
   `.html.sha256` sidecar and create the version-specific BQP, QA, security, and
   release-readiness reports named in the manifest.
3. **Prove reproducibility and run the release gates.** Run the four commands in
   Section 5, `git diff --check`, the repository-configured Gitleaks scan when
   Gitleaks is available, and all focused tests for the release's changed
   behavior. Repeat the clean build and provenance generation; the HTML,
   sidecar, and placeholder manifest must be byte-identical across the two
   cycles. Record actual counts, hashes, and the content fingerprint in the
   reports rather than carrying numbers forward from an older release.
4. **Commit and review the exact candidate.** `dist/` is ignored on development
   branches, so explicitly force-add exactly the current HTML, sidecar, and
   provenance manifest. Open a release PR and record independent regression,
   security, and content review against its exact head. A changed head requires
   fresh review. Do not represent publication, deployment, or browser/pilot
   acceptance as completed in a candidate report.
5. **Merge and retest the tag target.** Merge without changing candidate files.
   Record the full merge SHA as the tag target, rebuild from that exact tree,
   rerun the complete release gates, and compare the artifact SHA-256 and
   fingerprint with the reviewed candidate. The pinned version and date make
   this comparison deterministic.
6. **Stamp provenance in a later commit.** From post-merge `main`, run
   `python3 extract/make_provenance.py --commit <full-tag-target-sha>`, change the
   release report from candidate to released state, and commit those updates.
   The manifest names the merge that produced the artifact. The later commit
   carries that now-knowable fact; it is deliberately not the tag target.
7. **Create and mirror the immutable tag.** Create an annotated tag named exactly
   like `APP_VERSION`, explicitly targeting the merge SHA from step 5, and push
   the same tag plus the post-stamp `main` commit to GitHub and Forgejo. Existing
   tags are never moved. Unless an approved signing identity has been provisioned,
   state plainly that the tag and artifact are unsigned and rely on SHA-256 plus
   Git lineage for integrity, not publisher identity.
8. **Publish and verify the GitHub prerelease.** Publish exactly three assets
   from the post-stamp tree: the HTML, its `.html.sha256` sidecar, and the stamped
   `.provenance.json`. Release notes must name the tag target, artifact hash,
   content fingerprint, gate results, known limitations, and unsigned status.
   Read the release back from GitHub and verify that it is a non-draft prerelease,
   the tag peels to the intended merge on both remotes, all three remote asset
   digests match local bytes, and provenance contains the tag target rather than
   the placeholder.
9. **Keep deployment separate.** Do not infer receiving-host or browser
   acceptance from source, build, or publication evidence. If deployment is
   authorized, preserve the prior version as rollback and create one completed
   deploy receipt per artifact/host pair. When development of the next version
   begins, archive the just-released three-file set byte-for-byte under
   `releases/<version>/`; until then, the current release remains in `dist/`.

## Quarterly STIG Refresh Cycle

`stig-src/SOURCES.md` states the refresh rule directly: **first week of each
quarter, re-check the DISA library for RHEL 8/9/10**; RHEL 7 is re-checked only
semi-annually, and only to confirm whether it should be *removed* from the
library, not for a new release -- see "The RHEL 7 frozen source" below. A refresh
that finds a new benchmark:

1. Download the new zip from `dl.dod.cyber.mil`, compute its SHA-256, and update
   `stig-src/SOURCES.md` and `stig-src/SHA256SUMS` **in the same commit** as the
   new zip (`stig-src/SOURCES.md`'s own header states this as a rule, not a
   suggestion -- re-pinning is a `dep-bump` PR, never a silent file swap).
2. Run `python3 extract/parse_xccdf.py` to regenerate
   `content/rules_rhel<N>.json` and `content/cci_nist.json` from the new pin.
3. Diff the regenerated rule set against the prior one for the affected
   release: new rule IDs, removed rule IDs, and check/fix text changes on
   existing IDs all need an RHEL SME to confirm whether any catalogued command
   entry's `stig[]` rows, `intent`, or `notes` need updating to match.
4. Rebuild and run the full QA sequence (Section 5) -- Q8/Q9/Q10 will fail loud
   on any count mismatch or ID drift the extractor introduces, and Q10's ID-set
   parity check in particular would catch a release whose rule count changed
   without every ID being re-verified.
5. Update `docs/CHANGELOG.md` and this repo's `README.md` Recent changes with
   the new pinned version and benchmark date.

**The RHEL 7 frozen source.** RHEL 7's pinned STIG (V3R15, benchmark 24 Jul
2024) is marked SUNSET at DISA -- a **terminal release**: DISA has stated no
further RHEL 7 STIG updates are expected, ever. `stig-src/SOURCES.md` records it
as "frozen terminal version. In project only while RHEL 7 can be validated
(Founder, 2026-09-17)" -- meaning RHEL 7 support in this tool is contingent on
being able to keep validating its content (flags, captures) at all, not on a
future benchmark that will never arrive. The semi-annual RHEL 7 re-check exists
only to confirm the benchmark has not been pulled from DISA's library entirely,
not to look for an update. If RHEL 7 support is ever formally deprecated from
this tool, this is the reason that decision would cite.

## Flag-Coverage Baseline and Its Expiry

`content-src/flag_coverage_baseline.json` is a **ratchet**, not a resting place.
It records, per tool and RHEL release, how many long options a flag dictionary
currently carries against how many the raw `man`/`--help` capture actually shows
-- `qa.py`'s Q20 gate re-measures this on every build and fails only when a
shortfall **grows** past what is recorded here, so a real extractor gap
(`firewall-cmd` carries 16 of 205 long options on RHEL 8, for one) is an accepted,
dated residual rather than an unowned one, and cannot silently get worse without
the gate noticing.

**The baseline expires 2026-09-25.** `content-src/flag_coverage_baseline.json`
names its own owner (Caleb Stone, the extractor fix that would close the
shortfall) and its own retirement date; `tests/test_coverage_baseline_expiry.py`
proves `qa.py` actually fails the build starting 2026-09-26 if the file has not
been regenerated against improved dictionaries or explicitly re-dated by then.
An accepted residual with a date does not get to become a permanent one by
nobody looking again -- see `docs/POAM.md` for this same item tracked as an open
finding with an owner and a due date.

## File Organization

The layout this pipeline actually reads and writes, as opposed to the original
skeleton's proposal:

```
docs/                     companion documentation (this folder)
content/                  build.py's inputs -- curated + generated JSON,
                           per docs/ARCHITECTURE_BIBLE.md Section 3's table
content-src/               build-time-only sources: the roster, the flag-
                           coverage baseline, staged raw man/--help text
extract/                  every extractor (build.py imports extract/schema.py;
                           the rest are standalone scripts, not a package)
stig-src/                 pinned DISA XCCDF/CCI zips + SHA-256 sums
tests/                    unittest suite, the hostile harness, golden-command
                           table, and real SME capture records
template.html             the UI shell + app script build.py injects into
build.py                  assembly script
qa.py                     QA gates against the shipped artifact
dist/                     build output (git-ignored -- see
                           docs/ARCHITECTURE_BIBLE.md Section 24 for why a
                           committed artifact cannot stay byte-identical
                           across days)
```
