---
type: release-readiness-packet
status: candidate
last_verified: 2026-09-20
---

# Release Readiness Packet -- v1.0.0-alpha.3

This is the correction candidate for `MCR-A2-KEY-001`. It is prepared for
Jordan's integration/release action after exact-head regression review. It is
not a release, deployment, publication, or pilot-acceptance receipt.

| Required field | Candidate state |
|---|---|
| Original task base | `46507926500ea92aa8904c6a9d69698e2d3ba705` |
| Reconciled current-main base | `f5a29549a7b68b11ccdf20ac39bde834954c112f`; contains required receipt-history merge `b9906e460625fa7b63406854646e4666459e9450` |
| Reconciliation method | Isolated candidate branch fast-forward rebased before final build; alpha.2 receipt history retained under its original filename and not converted into alpha.3 evidence |
| Artifact | `dist/md-code-red_v1.0.0-alpha.3.html` (8,797,479 bytes) |
| Exact candidate SHA-256 | `62c80e950d82ed55086f383ce1918b76ed1425cea9c064d791e9a2e5c7283818` |
| SHA-256 sidecar | `dist/md-code-red_v1.0.0-alpha.3.html.sha256`; check passes |
| Five-island content fingerprint | `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea` |
| Fingerprint explanation | Expected metadata-only movement from alpha.2 because `meta.version` is hashed; after normalizing that one field, the first island is equal and the other four islands are byte-identical |
| Provenance | `dist/md-code-red_v1.0.0-alpha.3.provenance.json`; intentionally contains `TAG_COMMIT_PLACEHOLDER` until Jordan integrates and knows the tag target |
| Proposed tag | `v1.0.0-alpha.3` -- proposal only; not created or pushed |
| Verification | Q1-Q25+JS PASS; 336/336 unit tests PASS; 101,297 hostile checks PASS; targeted source+artifact rail-keyboard contract PASS; deterministic double-build PASS; source/lineage review PASS; Gitleaks 8.30.1 full-tree scan PASS |
| Reviewer state | Riley Park exact-head regression review required on the PR. The PR review is authoritative so the reviewed commit does not change merely to record the verdict |
| Deployment state | NOT DEPLOYED. No host, service, package, account, listener, firewall, DNS, route, or exposure change was made |
| Browser/pilot state | NOT EXECUTED / NOT ACCEPTED. No About-panel visual readback, live network observation, named operator use, or pilot witness is claimed |
| Forecast impact | Low implementation risk and no corpus change; alpha.3 removes the known keyboard blocker. Release timing depends on Riley's exact-head review and Jordan's integration/tag/publish action, followed by the existing human browser/pilot gates |

## Lineage and rollback

- Historical tag `v1.0.0-alpha.2` remains at
  `8186e104fdc3ebbe08a037442787ae5d2c7b01d7`; no tag was moved or overwritten.
- Alpha.2's published set is preserved byte-for-byte under
  `releases/v1.0.0-alpha.2/`:
  - HTML SHA-256:
    `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a`.
  - Sidecar-file SHA-256:
    `73ff4f56d857bc7c6b957ae24c377f5c89dfa6a6a2bc7267c52adf8e49ba24a8`.
  - Post-tag-stamped provenance-file SHA-256:
    `e6dbb00c242be2fcee3eef7569e6c745ae2e0d707f26a6490c586d78d523a88c`.
- Rollback is a file-level return to the immutable alpha.2 set. Close alpha.3
  tabs, verify the alpha.2 sidecar, and open the alpha.2 file. No daemon or
  service needs stopping because MD CODE RED is a static local HTML artifact.

## Jordan integration/release actions

1. Confirm the PR head is the exact commit Riley reviewed and that required CI
   remains green.
2. Merge without modifying candidate files. If the head changes, require a fresh
   Riley exact-head review.
3. Rebuild cleanly and compare the artifact SHA-256 and content fingerprint to
   this packet.
4. Re-run `extract/make_provenance.py --commit <tag-target-full-sha>` and commit
   the stamped provenance through the normal release process.
5. Only then create/push the proposed annotated tag and publish the release
   assets. Deployment and browser/pilot acceptance remain separate actions.
