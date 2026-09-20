---
type: release-report
status: released
last_verified: 2026-09-20
---

# Release Report -- v1.0.0-alpha.3

**Reviewed source revision:** `3f68ac1da3dac3bbb29fab6a07363ee0da1d5015`

**Tagged merge revision:** `e72c235fbb8e58c72c7ebf861696efeef5e4a27b`

This is the published correction release for `MCR-A2-KEY-001`. The release is
separate from deployment and pilot acceptance; neither is claimed by this
report.

| Required field | Released state |
|---|---|
| Original task base | `46507926500ea92aa8904c6a9d69698e2d3ba705` |
| Reconciled current-main base | `f5a29549a7b68b11ccdf20ac39bde834954c112f`; contains required receipt-history merge `b9906e460625fa7b63406854646e4666459e9450` |
| Reconciliation method | Isolated candidate branch fast-forward rebased before final build; alpha.2 receipt history retained under its original filename and not converted into alpha.3 evidence |
| Artifact | `dist/md-code-red_v1.0.0-alpha.3.html` (8,797,479 bytes) |
| Exact candidate SHA-256 | `62c80e950d82ed55086f383ce1918b76ed1425cea9c064d791e9a2e5c7283818` |
| SHA-256 sidecar | `dist/md-code-red_v1.0.0-alpha.3.html.sha256`; check passes |
| Five-island content fingerprint | `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea` |
| Fingerprint explanation | Expected metadata-only movement from alpha.2 because `meta.version` is hashed; after normalizing that one field, the first island is equal and the other four islands are byte-identical |
| Provenance | `dist/md-code-red_v1.0.0-alpha.3.provenance.json`; records tag target `e72c235fbb8e58c72c7ebf861696efeef5e4a27b` |
| Release tag | `v1.0.0-alpha.3`, targeting reviewed merge `e72c235fbb8e58c72c7ebf861696efeef5e4a27b` |
| Verification | Q1-Q25+JS PASS; 336/336 unit tests PASS; 101,297 hostile checks PASS; targeted source+artifact rail-keyboard contract PASS; deterministic double-build PASS; source/lineage review PASS; Gitleaks 8.30.1 full-tree scan PASS |
| Reviewer state | Riley Park APPROVE at exact candidate head `3f68ac1da3dac3bbb29fab6a07363ee0da1d5015`; no blocker, high, medium, or low findings |
| Deployment state | NOT DEPLOYED. No host, service, package, account, listener, firewall, DNS, route, or exposure change was made |
| Browser/pilot state | NOT EXECUTED / NOT ACCEPTED. No About-panel visual readback, live network observation, named operator use, or pilot witness is claimed |
| Forecast impact | Low implementation risk and no corpus change; alpha.3 removes the known keyboard blocker. Remaining timing depends on deployment and the existing named-human browser/pilot gates |

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

## Release operation record

1. PR #6 merged the exact Riley-reviewed candidate without changing candidate
   files.
2. A clean rebuild at the merge revision reproduced the recorded artifact
   SHA-256 and content fingerprint.
3. Q1-Q25 plus JavaScript and all 336 unit tests passed at the merge revision.
4. Provenance was stamped with the selected tag target through the normal
   post-merge release commit.
5. The annotated tag and release assets were published without changing the
   historical alpha.2 tag or assets. Deployment and browser/pilot acceptance
   remain separate actions.
