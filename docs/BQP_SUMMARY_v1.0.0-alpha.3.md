---
type: build-quality-summary
status: candidate
last_verified: 2026-09-20
---

# Build Quality Protocol Summary -- v1.0.0-alpha.3

**Original task base:** `46507926500ea92aa8904c6a9d69698e2d3ba705`

**Reconciled current-main base:**
`f5a29549a7b68b11ccdf20ac39bde834954c112f`, which contains required receipt
history merge `b9906e460625fa7b63406854646e4666459e9450`.

**Correction:** `MCR-A2-KEY-001` -- the six rendered activity rails now have six
matching `Ctrl+Alt+1` through `Ctrl+Alt+6` runtime bindings, with the user guide
and button titles held to the same executable contract.

**Decision:** PASS for source-controlled build quality and READY FOR independent
exact-head regression review. Browser and pilot acceptance remain HOLD: this
candidate has not been tagged, published, deployed, or opened on an approved
receiving-host browser.

## Gate 1 -- build and artifact integrity: PASS

- Reproducible build produced `dist/md-code-red_v1.0.0-alpha.3.html`
  (8,797,479 bytes).
- Artifact SHA-256:
  `62c80e950d82ed55086f383ce1918b76ed1425cea9c064d791e9a2e5c7283818`.
- Ordered five-island content fingerprint:
  `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea`.
- Q1 independently matched the artifact, sidecar, version, build date, five
  island order, and recomputed fingerprint.
- Two clean build/provenance cycles were byte-identical for the HTML artifact,
  SHA-256 sidecar, and provenance manifest.
- The alpha.2 fingerprint was
  `f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83`.
  The alpha.3 fingerprint changes only because `meta.version` inside the first
  island changes from alpha.2 to alpha.3. After normalizing that field, the full
  first island is equal; the other four islands are byte-identical. All
  non-metadata corpus keys are equal.
- Alpha.2's published artifact set is preserved byte-for-byte under
  `releases/v1.0.0-alpha.2/`; the historical tag was not moved or rewritten.
- The isolated candidate branch was fast-forward rebased from the original task
  base to current `main` before the final build. Both alpha.2 receipt-history
  updates remain unchanged in their original alpha.2 document.

## Gate 2 -- automated verification: PASS

- `python3 qa.py`: Q1-Q25 and JS PASS.
- `python3 -m unittest discover -s tests`: 336 tests PASS.
- `node tests/hostile_harness.js`: 101,297 checks, 0 failures.
- Targeted `MCR-A2-KEY-001` regression: three Python contract tests PASS, and
  the Node contract passes independently against both `template.html` and the
  built alpha.3 artifact. Every rendered rail has one unique advertised and
  working runtime binding; `Ctrl+Alt+6` selects and focuses About.
- Q25 re-resolved 23,447 of 23,447 citations over 14,439 reference records.

## Gate 3 -- release controls: READY FOR REVIEW, NOT RELEASED

- The change set is limited to the already-merged keyboard correction, release
  metadata/evidence, version-aware fixtures/docs, and archival relocation of
  the exact alpha.2 release assets.
- Focused source review PASS: the alpha.2 archive blobs equal the exact files
  previously tracked in `dist/`, the alpha.2 tag still resolves to its original
  target, no alpha.3 tag exists, and `git diff --check` is clean.
- Secret review PASS: Gitleaks 8.30.1 scanned the complete candidate tree with
  the repository configuration and reported no leaks.
- Proposed tag: `v1.0.0-alpha.3`. It does not exist and must not be created by
  this candidate task.
- Riley Park's regression disposition must be recorded against the exact PR
  head. That review belongs on the PR so recording it cannot mutate the commit
  that was reviewed.
- Browser/pilot acceptance, About-panel visual readback, live zero-network
  observation, publication, and deployment are explicitly unclaimed.
