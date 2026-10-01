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
source `95c9d9ebf05d9cb9aad294d26a388b9ffb708f6b`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,928,004 bytes |
| HTML SHA-256 | `fd21f27561b03e9dc17e892dbef7845b0621ad0751d571d903d70129277d0feb` |
| Content fingerprint | `13884109fdb87981016611b9017e25ddc46fce607490ea9e178f3230cd7dd9a2` |
| Sidecar SHA-256 | `643224222fd015c23c5fdb301ddfff4c6bfba88de53c8020e47a293906737644` |
| Placeholder provenance SHA-256 | `d0709855360c411242666176229ad6cf5d05b3b87888b0b7182e70ce8962ff2e` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `95c9d9ebf05d9cb9aad294d26a388b9ffb708f6b` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
