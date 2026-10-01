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
`python3 qa.py` -- 26 gates plus an optional Node syntax check, against the
**shipped artifact**. `docs/QA_GATES.md` is the full authority -- what each
gate proves, how it has been watched fail, and its stated residual -- and is not
duplicated here. On this build: all 26 gates plus `JS` PASS; the unit suite and
hostile harness must also pass with zero failures
(`python3 -m unittest discover -s tests` and `node tests/hostile_harness.js`).
The harness reports its current check count; documentation does not pin that
implementation-dependent number.

The release browser audit runs twice against the same built bytes: once by
opening the standalone HTML directly with `file://`, which is the primary
delivery contract, and once through a local HTTP server to catch origin- and
transport-dependent behavior. A pass in one mode is not reported as a pass in
the other; both machine-readable records are retained under `docs/qa/`.

**The pipeline composer (CR-T-31)** is gated by the same suite and is documented
in `docs/QA_GATES.md`'s own pipeline section, which is the authority. In short,
what runs on every build: 26,992 hostile-vector checks into every field of every
stage; at least 717 pipeline-oracle comparisons with negative controls that FAIL if
the oracle agrees with a line it should reject; 332 operator-seam refusals; 100
interpreter-class checks; at least 68 redirect-target rating checks; 232 one-stage
invariants (a pipeline of one stage equals `assembleCommand()` byte for byte);
and `tests/test_pipeline_ui_wiring.py` (17 tests, 10 audits, 15 negative
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

- [x] **Syntax verified, where captured:** 18 of 800 possible (entry, RHEL
      version) pairs carry an independent QA-reviewed receipt as of this build.
      The remaining 782 have not been independently run on a real host; see
      `docs/USER_GUIDE.md`'s per-version verification badges for how this shows
      in the UI.
- [x] **Flags accurate, where curated:** every flag a command shows either
      resolves to a curated explanation or honestly renders "unverified -- see
      man page" (`qa.py`'s Q22 gate, and the assembler's no-guess rule --
      `docs/ARCHITECTURE_BIBLE.md` Section 5). As of this build, 0 of 3,178
      release-specific flag-dictionary rows carry a curated explanation. The
      curated command entries separately carry 348 flag rows, of which 336 have
      explanations and 12 deliberately fall back to the dictionary/no-guess copy.
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
`wipefs`, `lvremove`, `dnf remove`, and 11 other rows) are rated blast red and
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
`tests/hostile_harness.js`) -- and **seven entries in this build are rated red**. Three are guided forms
(`gen-pvcreate-initialize`, `gen-vgcreate-new-vg`, and
`git-checkout-discard-changes`) and four are static reviewed commands
(`rm-remove`, `git-push`, `git-reset-hard`, and `a-adhoc-become`). Each provides
a live confirmation-flow example in the running UI.

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

**Status: alpha.3 is published, deployed, and integrity-verified on Defiant;
pilot acceptance remains on hold pending named-human browser use and Riley's
attended witness.** RHEL 9 has captured flag sources and a release-specific
dictionary. The remaining sparse flag explanations and evidence captures are
disclosed findings for the pilot rather than hidden assumptions. The alpha.3
pilot receipt identifies the exact artifact SHA-256 and does not claim human
operational acceptance before a named operator has actually used it.
