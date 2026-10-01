---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

Verification totals: 465 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser assertions in each delivery mode.

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `4d61c901001f631690954d4bdb8f345d9c33742a`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,842 bytes |
| HTML SHA-256 | `bd419fffba2e2c1c7a2218c0a550bf6eda368619315b7f54d6a91207887a06aa` |
| Content fingerprint | `98974cb6efa8bf67c42e4869c03c3d9e5ae35b5d6631500cdeda1a35b418c358` |
| Sidecar SHA-256 | `cc74d3dcf4211fc42d9c77b2f43151d206a6fcbef253cefb65b9f5f0f017c778` |
| Placeholder provenance SHA-256 | `0fd83c9b18b20742c1786742456a91bbc23e822cfdb409b0c9935b930d1d8157` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `4d61c901001f631690954d4bdb8f345d9c33742a` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
