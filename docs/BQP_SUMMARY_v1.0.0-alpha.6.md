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
source `fe2c6d8230e59f18d3a6a6ef92be0b707990799f`.

| Item | Result |
|---|---|
| HTML | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,908,425 bytes |
| HTML SHA-256 | `e3920993af6f7db57bbdf6fdd8c3ef4a53e1b5de4263f80a4cb2b956c1f4bdb3` |
| Content fingerprint | `3e1282a01d1429ab25d9e0da353c709c629e2081f4f4e19687cc8a27093df3b1` |
| Sidecar SHA-256 | `be52332cb514685e96db5c5b975be44eda94abc968428e99cfebc4d8a6c21b07` |
| Placeholder provenance SHA-256 | `e137f440fff9371a79ee547487f62a050f9e7ffadfa1969dc05b9628a924ae23` |
| Build identity | MD CODE RED `v1.0.0-alpha.6`, built 2026-10-01, UNCLASSIFIED |
| Reproducibility | PASS; two consecutive cycles matched all three files byte for byte and matched the committed bytes |
| Assembly | PASS; `build.py` assembled five escaped JSON islands and one application script without external assets |
| Historical archive | Released alpha.5 files remain byte-for-byte under `releases/v1.0.0-alpha.5/` |
| Implementation source | `fe2c6d8230e59f18d3a6a6ef92be0b707990799f` |

The candidate provenance intentionally contains `TAG_COMMIT_PLACEHOLDER`.
After merge, the release procedure must rebuild and retest the exact merge,
then regenerate provenance with that immutable tag-target SHA in a later commit.
The candidate is unsigned because no authorized publisher signing key is
provisioned.
