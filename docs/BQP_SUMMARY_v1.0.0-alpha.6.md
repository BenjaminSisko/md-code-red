---
type: release-evidence
status: candidate
last_verified: 2026-09-30
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

The release candidate was assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive clean build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,895,469 bytes |
| HTML SHA-256 | `e25e88a7ced014aa45273bd865a27d8860aa56126b03e1867ca7d0cadd12c1e9` |
| Content fingerprint | `327324da688bf7c04bad4952832671958f16d64824c7e5839166397422a4557e` |
| Sidecar SHA-256 | `e896ed436bac0fce002035ba70da61d1b83ba3dce4cdc88c51b3a1a8e9cd8b9f` |
| Placeholder provenance SHA-256 | `74f00e8b3b9e84c0766e7d36f1255a8473204135da5db67f1cb63d3cf2d39d43` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-09-30, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive clean cycles matched all three files byte for byte |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Candidate source | `271fc9f08d048d9f3da038f6dc487d8187480b0b` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
