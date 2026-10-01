---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

Verification totals: 480 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser records in each delivery mode (896 pass/fail assertions and 2 performance observations).

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `d1b0a44fe293f3933e998630917ee0af6c60c078`.

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
| Forgejo CI candidate build | PASS; Python 3.12 rebuild leaves HTML and sidecar clean while preserving committed toolchain-specific provenance for release-readiness checks |
| Post-merge stamp simulation | PASS; disposable no-ff merge `1e96531d84e62c40f1bd20d2c349554eb030bdd2` contains implementation `3e5c95402e7349a9ad7f6be233673728e301410d` and exact candidate `4e5c2887a71e20ee49ae3ac27a7403566c29bbcd`; committed stamp `f25279d5eef6ba9d563344cac5f49ba1c0cf26e7` passed all 480 tests and Q1-Q26 + JS with a clean tree |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `d1b0a44fe293f3933e998630917ee0af6c60c078` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The placeholder provenance hash above is also the normalized release hash: the
readiness gate permits only `git_commit` to change, requires the stamped commit
to be a lowercase commit object at or after the browser-reviewed implementation
and in the release tree's ancestry, requires canonical generator-formatted JSON,
and requires every other manifest field, including the release-workstation
toolchain, to remain byte-identical after normalization.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
