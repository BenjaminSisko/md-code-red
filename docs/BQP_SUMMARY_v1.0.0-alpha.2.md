---
type: build-quality-summary
status: current
last_verified: 2026-09-20
---

# Build Quality Protocol Summary -- v1.0.0-alpha.2

**Candidate revision reviewed:** `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a`

**Decision:** PASS WITH ONE ACCEPTANCE LIMITATION for the lab-only, unsigned
alpha.2 release. The local browser automation provider blocked `file://` by URL
policy, so this run cannot claim an interactive Chrome walkthrough. The shipped
JavaScript, UI wiring, search, evidence export, and command/pipeline behavior are
covered by executable gates and tests listed below. A receiving human still must
complete the deploy receipt's post-deploy browser check.

## Gate 1 -- build and artifact integrity: PASS

- Reproducible build produced `dist/md-code-red_v1.0.0-alpha.2.html`.
- Artifact SHA-256:
  `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a`.
- Ordered five-island content fingerprint:
  `f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83`.
- Q1 independently matched the artifact, sidecar, version, build date, five
  island order, and recomputed content fingerprint.
- The provenance generator was corrected to hash all five islands, then its
  output was independently checked by the unit suite.
- Alpha.1 remains byte-for-byte archived under `releases/v1.0.0-alpha.1/` and
  its existing tag/release lineage.

## Gate 2 -- automated verification: PASS

- `python3 qa.py`: Q1-Q25 and JS PASS.
- `python3 -m unittest discover -s tests`: 333 tests PASS.
- `node tests/hostile_harness.js`: 101,297 checks, 0 failures.
- Pipeline evidence includes 17,092 hostile pipeline checks, 593 oracle
  comparisons, 11 oracle negative controls, 123 blast-composition checks, 156
  refusal checks, 68 redirect-rating checks, and 108 one-stage invariants.
- Q25 re-resolved 23,447 of 23,447 citations over 14,439 reference records.
- Gate 2's one-script expectation has a declared architecture deviation: the
  artifact contains five inert `application/json` islands and one executable app
  script. Q1 enforces that exact shape and order.

## Gate 3 -- review and release controls: PASS WITH ACCEPTANCE LIMITATION

- PIPE-003, PIPE-004, PIPE-F1, and PF6 are closed with executable controls.
- MCR-SEC-020/Q20 is retired with evidence and named authority; Q20 continues to
  measure all 70 tool/release capture pairs and fails on regression.
- Q23-Q25 are continuous release gates. Reference records remain structurally
  separate from curated records and cannot enter the assembler.
- No credential material was introduced. Matches from the focused secret scan
  were vendor/manual example prose and mined reference commands, not credentials.
- The candidate remains unsigned. Integrity is SHA-256 plus Git/release lineage;
  it does not establish publisher identity.
- The live local-file browser check remains a receiving-admin action because the
  automation provider rejected the URL. This is recorded in the QA report and
  pending deploy receipt rather than represented as completed.
