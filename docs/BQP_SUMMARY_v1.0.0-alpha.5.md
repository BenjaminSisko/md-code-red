---
type: release-evidence
status: candidate
last_verified: 2026-09-22
---

# Build Quality Protocol Summary -- v1.0.0-alpha.5

The candidate was built from the pinned `APP_VERSION` and `APP_BUILD_DATE` in
`build.py`. Two consecutive build and placeholder-provenance cycles produced
byte-identical outputs.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.5.html`; 8,892,535 bytes |
| HTML SHA-256 | `c64337a2aee3c494171bc9b6f7bb89a0b1006992fc26c7fbe8793579cd8ada7a` |
| Content fingerprint | `41fb7c1e59cc32805fa06a240aca2913e16acb496689c2de0ec9dff598b34c91` |
| Sidecar SHA-256 | `12ed3773854353f47c57904d2ab39f18f0aa922d8316c2fa42c4a7f3ec07bf39` |
| Placeholder provenance SHA-256 | `769823bc5f5d33026b93cc39b2c562528a072713e62075fbde058a0073662dc2` |
| Build identity | MD CODE RED `v1.0.0-alpha.5`, built 2026-09-22, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files |
| Historical archive | Released alpha.4 files moved byte-for-byte to `releases/v1.0.0-alpha.4/` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
