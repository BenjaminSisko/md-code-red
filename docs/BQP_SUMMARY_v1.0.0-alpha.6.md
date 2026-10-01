---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

Verification totals: 443 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 897 rendered-browser assertions in each delivery mode.

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `eda403cfb6f08d2642c02f4b50d96770b4bc2a47`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,933,228 bytes |
| HTML SHA-256 | `241ffd0cf0942d13c4a38509a31adf24849c86090fdf3f54e9daee78f19b81da` |
| Content fingerprint | `26aa47f62622a94ae6c4522808eca86aca8522c0e679be9e94fb4ad2cccb6e8b` |
| Sidecar SHA-256 | `7855a162af4ec6ec7bdd4f37d4c52abf421d2bc5dad0ac94e36a4c5dd7f69a16` |
| Placeholder provenance SHA-256 | `348656b3bd1f822332e90b0eb094df3c908ffa3775341db48f92a8077051f47c` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `eda403cfb6f08d2642c02f4b50d96770b4bc2a47` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
