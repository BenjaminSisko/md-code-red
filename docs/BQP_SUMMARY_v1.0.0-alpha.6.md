---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Build Quality Protocol Summary -- v1.0.0-alpha.6

Verification totals: 451 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 897 rendered-browser assertions in each delivery mode.

The final candidate is assembled from the pinned `APP_VERSION` and
`APP_BUILD_DATE` in `build.py`. Two consecutive build and placeholder-
provenance cycles produced byte-identical HTML, sidecar, and provenance files.
The resulting bytes also match the artifact committed with implementation
source `1bedeba652a3197be10adae371b5c99fc7b2e49e`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,941,777 bytes |
| HTML SHA-256 | `7e49fcbfae2b9c4985602ce9fc28cd99175d2b6ee598a9fd8caeddd2c0972164` |
| Content fingerprint | `8ee4a5e9eb86489f1730ef4b71e18ca620284f266ae0fa029e7ff71cc649d271` |
| Sidecar SHA-256 | `8b34f67c2f1cb9967f56fd74ab34e0dce6f85f2db154556f463fff334906e991` |
| Placeholder provenance SHA-256 | `edd3f1560890989eb5575afc933d9d506ed96c1dfe437eb0990425e08085398a` |
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
