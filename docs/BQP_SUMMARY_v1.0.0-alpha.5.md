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
| HTML | `dist/md-code-red_v1.0.0-alpha.5.html`; 8,891,476 bytes |
| HTML SHA-256 | `334dc3f5f094e1e14ef300a519cba273082213b708ed650d3af62f48bd1ae554` |
| Content fingerprint | `f5a709078b6eb96e130937282116e10788825cdb4e3c4ea687d3ffb41b52629a` |
| Sidecar SHA-256 | `f62403ac7ed4dd7f92e2a64f92e8e3f6a5232fc274981687f8b7a6c64bda92bd` |
| Placeholder provenance SHA-256 | `fbb6cefa66efd1f71dc3ab68d35c3fca3802b2cdce8b64b64510f0404a16ae20` |
| Build identity | MD CODE RED `v1.0.0-alpha.5`, built 2026-09-22, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files |
| Historical archive | Released alpha.4 files moved byte-for-byte to `releases/v1.0.0-alpha.4/` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
