---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

Verification totals: 470 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser assertions in each delivery mode.

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `05b96e5c74c7de5b3795df5e1ee9fa87b28583b8`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,791 bytes |
| HTML SHA-256 | `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Content fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Sidecar SHA-256 | `b18d1303c69b81ca4bdf405d704313cc512751f1f265c35987742fb3ce31b335` |
| Placeholder provenance SHA-256 | `aa11a5fb4a81197e159802d8b72c216b1a4063b7ad725b55112db2722aa3f8c5` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `05b96e5c74c7de5b3795df5e1ee9fa87b28583b8` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
