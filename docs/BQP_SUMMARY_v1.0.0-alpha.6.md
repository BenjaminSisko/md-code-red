---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

Verification totals: 457 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 897 rendered-browser assertions in each delivery mode.

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `1bedeba652a3197be10adae371b5c99fc7b2e49e`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,458 bytes |
| HTML SHA-256 | `0ef9e0351c685605580a5733f18bcbdd9e61ba68b4e3d9a62ad2fd9504ae8bcc` |
| Content fingerprint | `d079b65452ad7611fa328a77880422bb12a3d261807b46e2f1fcb9e62b71aa94` |
| Sidecar SHA-256 | `80f18b7ed806fb280b885fa6f0ad054c7b83009e7bb9e487d8ea30c3f4767344` |
| Placeholder provenance SHA-256 | `bfad46891414f89f366d0177fcf258fd96e22c6a5f25e3d5f21ec3b8521fc4ef` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `1bedeba652a3197be10adae371b5c99fc7b2e49e` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
