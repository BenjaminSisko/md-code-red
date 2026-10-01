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
source `19274c4f99a6a9b73ffd504d2bc2053957453a45`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,913,823 bytes |
| HTML SHA-256 | `69ec4e6bcce72fc1ad4c05f632702120b4d983527a93d6c917da372c6568d18c` |
| Content fingerprint | `e377c108f895bf4ca26b476e26f246e0d6b80a2156f1b5a1cea0039019224225` |
| Sidecar SHA-256 | `4f9e6081d9c565e8f0da2d1b858fa1bc5eb1769a1cd8907fa2c2f1d4dcd3ea90` |
| Placeholder provenance SHA-256 | `df95b0b4885f3422354b502776bc74fd4e77ac8a9d5ae76833b4c8fc86ee2e8c` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `19274c4f99a6a9b73ffd504d2bc2053957453a45` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
