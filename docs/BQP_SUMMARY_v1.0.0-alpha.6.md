---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `669924a6df0208f7e239985091ff227de9713168`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,902,185 bytes |
| HTML SHA-256 | `d1949c9e16b6b479167058a38c6bfd3062e480c22ea029386da1e7aca4f65a04` |
| Content fingerprint | `552816ec5cab1416f3463f3b43e247a58e1de9ffd17577916b4600435c0d982a` |
| Sidecar SHA-256 | `9059fb60fdee797daa66a4e02f3be0f023280a83a8232b2ad3ca8b1d14dd12ab` |
| Placeholder provenance SHA-256 | `954c9138fad7e1ef671391ffb92e22c1ba8c8c0be3299497fa38940b2b4f5d4d` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `669924a6df0208f7e239985091ff227de9713168` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
