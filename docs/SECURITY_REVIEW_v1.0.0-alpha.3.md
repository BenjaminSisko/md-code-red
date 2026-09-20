---
type: security-review
status: candidate
last_verified: 2026-09-20
---

# Security Review -- v1.0.0-alpha.3

**Original task base:** `46507926500ea92aa8904c6a9d69698e2d3ba705`

**Reconciled current-main base:**
`f5a29549a7b68b11ccdf20ac39bde834954c112f`, including required ancestor
`b9906e460625fa7b63406854646e4666459e9450`.

**Disposition:** APPROVE for PR review as a lab-only unsigned correction
candidate. Tagging, publishing, deployment, browser acceptance, and pilot
acceptance remain outside this disposition.

## Scope reviewed

- The executable correction is one closed-table change: the existing rail-jump
  binding accepts key `6` in addition to `1` through `5`.
- The regression tests execute the shipped keyboard controller against every
  rendered rail and reconcile runtime keys, tooltips, focus behavior, and the
  current user-guide mapping.
- Release metadata moves from alpha.2 to separately versioned alpha.3.
- Alpha.2 assets are relocated to the release archive without byte changes.
- No command assembler, validator, escaper, evidence exporter, curated content,
  STIG source, flag dictionary, receipt, capture, or reference record changes.

## Automated security evidence

- Q2 air-gap law PASS: no external asset or network API path.
- Q17 render safety PASS.
- Q18 command-assembly safety PASS: 101,297 hostile checks, 0 failures.
- Q19 escaper behavior PASS.
- Q21 raw control/bidi/zero-width scan PASS over every tracked file.
- Q24 reference/curated shape separation PASS.
- Q25 re-resolved all 23,447 citations.
- Focused source review PASS: `git diff --check` is clean; alpha.2 archive blobs
  equal the exact files previously tracked in `dist/`; the immutable alpha.2 tag
  still resolves to its original target; and no alpha.3 tag exists.
- Secret review PASS: Gitleaks 8.30.1 scanned the complete candidate tree with
  `.gitleaks.toml` and reported no leaks.

## Content and integrity assessment

The five-island fingerprint changes from
`f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83`
to `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea`.
This is explained by the `meta.version` field inside the hashed first island.
The first island is equal after normalizing that field, all non-metadata keys
are equal, and the other four islands are byte-identical.

## Residuals and limits

- The artifact remains unsigned; SHA-256 plus Git/release lineage proves
  integrity and reproducibility, not publisher identity.
- Static gates do not replace a receiving-host browser walkthrough.
- The candidate has not been deployed, so no live About-panel, network, or
  operational acceptance evidence exists for alpha.3.
- Any change after Riley's review invalidates the exact-head review and requires
  a fresh regression disposition.
