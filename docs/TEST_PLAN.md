# Test Plan & QA Charter

MD CODE RED uses a two-tier QA model: **automated gates** during build (structure,
air-gap, safety, provenance, accuracy) and **content validation** (SME capture,
independent QA verification) before a command entry's `verified` receipt is
written. This file is a pointer into both, not a restatement of either.

## QA Ownership

**Build Quality Protocol (BQP):** Al Kowalski (Chief Architect). See
`issm-company-playbook` Section 10.2.

**Manual QA & Content Validation:** Riley Park (QA Engineer). Owns the formal
test plan and charter, and is the QA role checked against
`content-src/roster.json` by every `verified` receipt this repo ships
(`docs/WORKFLOW.md` Section 2a).

## Automated Gate Suite

This is the part of the two-tier model this repo actually runs and can prove:
`python3 qa.py` -- 22 gates plus an optional Node syntax check, against the
**shipped artifact**. `docs/QA_GATES.md` is the full authority -- what each
gate proves, how it has been watched fail, and its stated residual -- and is not
duplicated here. On this build: all 22 gates plus `JS` PASS, 293 unit tests OK
(`python3 -m unittest discover -s tests`), and 101,297 hostile-input checks with
0 failures (`node tests/hostile_harness.js`).

**The pipeline composer (CR-T-31)** is gated by the same suite and is documented
in `docs/QA_GATES.md`'s own pipeline section, which is the authority. In short,
what runs on every build: 17,092 hostile-vector checks into every field of every
stage; 589 pipeline-oracle comparisons with 11 negative controls that FAIL if
the oracle agrees with a line it should reject; 332 operator-seam refusals; 100
interpreter-class checks; 44 redirect-target rating checks; 108 one-stage
invariants (a pipeline of one stage equals `assembleCommand()` byte for byte);
and `tests/test_pipeline_ui_wiring.py` (15 tests, 9 audits, 14 negative
controls) on the panel the harness cannot see. Q18 fails closed on a zero in any
of those counts, so a harness that stopped checking pipelines cannot pass by
saying nothing about them.

## Formal Test Plan (company record)

**Location:** `/Users/benny/Documents/SALM LLC/07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md`

The test plan covers:
- Feature matrix (which tool/RHEL version pairs are tested)
- Regression suite (commands that must work across releases)
- Pilot enclave validation protocol
- Known limitations and acceptance criteria

This repo's own copy of "known limitations" is `docs/USER_GUIDE.md`'s Known
Limitations section, kept current against the built artifact rather than
against a plan document; the two should agree, and a disagreement is worth
raising with Riley Park rather than silently trusting one over the other.

## Content Validation Protocol

Every command entry in the toolkit must pass this validation before its
`verified[version]` field can carry a receipt. The full end-to-end flow (SME
captures, QA reviews, the roster and two-person rule, the closed grammars on
`host`/`capture`) is `docs/WORKFLOW.md` Section 2a -- not restated here.

### Pre-Release Content Checklist

- [x] **Syntax verified, where captured:** 18 of 108 possible (entry, RHEL
      version) pairs carry an independent QA-reviewed receipt as of this build.
      The remaining 90 have not been independently run on a real host; see
      `docs/USER_GUIDE.md`'s per-version verification badges for how this shows
      in the UI.
- [x] **Flags accurate, where curated:** every flag a command shows either
      resolves to a curated explanation or honestly renders "unverified -- see
      man page" (`qa.py`'s Q22 gate, and the assembler's no-guess rule --
      `docs/ARCHITECTURE_BIBLE.md` Section 5). As of this build, 0 of 2,009
      flag-dictionary entries carry a curated explanation; only 4 flags
      anywhere in the build do, all on the 3 static entries.
- [x] **STIG mapping correctness, mechanically checked:** `qa.py`'s Q10 gate
      re-parses the pinned XCCDF and requires full ID-set parity plus a
      deterministic content sample, on every build -- not a one-time
      spot-check. `docs/QA_GATES.md`'s Q10 row states exactly what is sampled
      versus exhaustive.
- [x] **Source cited, mechanically checked:** `qa.py`'s Q3 gate requires all
      five provenance fields on every entry, flag, and dataset; the field list
      is read from `extract/schema.py`, not restated in the gate.
- [x] **Air-gap clean, mechanically checked:** `qa.py`'s Q2 gate, backed by the
      shipped file's own CSP meta tag -- `docs/CODE_STANDARDS.md` Section 5.
- [ ] **Explainer plain-English, for every flag:** not yet true for most flags
      (see above) -- curation is a separate, ongoing human step, not a gate.

### Dangerous Operations

Commands whose assembled text matches a row of `content/dangerous.json` (`rm -rf`,
`wipefs`, `lvremove`, `dnf remove`, and 7 other rows) are rated blast red and
must show:
- [x] Red confirmation banner in the UI, blocking Copy until reviewed
      (`renderBlastBanner()`, `docs/USER_GUIDE.md` Journey 3)
- [x] Explicit warning naming which pattern matched and why (the banner's own
      `reasons[]` text, sourced from `content/dangerous.json`)
- [x] Recovery command, where applicable (the entry's own `undo` field, shown
      under every command regardless of blast level)
- [x] STIG justification, where compliance-required (the entry's `stig[]` rows,
      shown in the Inspector)

**All four are real, gate-tested mechanisms** (`content/dangerous.json`'s rows
are each proved to fire against a synthetic command by
`tests/hostile_harness.js`) -- but **no entry in this shipped build is rated
red**, and no generator's currently offered values assemble into a command
matching a dangerous pattern. This checklist item is honestly satisfied by
construction, not by an example anyone can currently click through in the
running UI.

### Spot-Check Sampling

**Open, not yet decided.** No sampling rate or spot-check lead has been
assigned in any record this repo can see. The automated gates above cover
structural correctness on every build; a sampling *rate* is specifically about
independent human re-verification of content the gates cannot judge (does this
flag explanation actually read correctly to a junior admin, for instance), and
that decision has not been made. Track against `docs/POAM.md` rather than
leaving it silently unresolved here.

## Pilot Validation (Phase 1)

Three senior admins + one ISSO in one enclave, 4 weeks. Success criteria:

- Zero incorrect or non-working commands reported
- Average time-to-command < 30 seconds per search
- Pilot users adopt toolkit for 3+ daily tasks
- ISSO confirms STIG evidence quality meets body-of-evidence standard

**Status: not yet run.** No pilot report exists in this repo or in the records
this document has visibility into. Given `docs/USER_GUIDE.md`'s Known
Limitations (RHEL 9's flag dictionary is empty, most flags are uncurated, only
5 STIG rows carry a captured expected output), a pilot run today would surface
those gaps as findings rather than validate a feature-complete build -- worth
weighing before scheduling it.
