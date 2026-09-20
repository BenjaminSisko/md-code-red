---
type: release-report
status: released
last_verified: 2026-09-20
---

# Release Report -- v1.0.0-alpha.2

**Reviewed source revision:** `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a`

**Tagged merge revision:** `8186e104fdc3ebbe08a037442787ae5d2c7b01d7`

**Artifact:** `dist/md-code-red_v1.0.0-alpha.2.html`

**SHA-256:**
`692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a`

**Content fingerprint:**
`f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83`

This recovery candidate closes the remaining pipeline findings, retires the Q20
waiver without disabling the measurement, refreshes the reference corpus from
current main, and adds continuous Q23-Q25 coverage. Alpha.1 artifacts are archived
under `releases/v1.0.0-alpha.1/` and remain available through the existing tag and
release record.

Release validation is Q1-Q25 plus JS, 333 unit tests, and 101,297 hostile-harness
checks. The release is lab-only and unsigned. The interactive local-file browser
step is pending on the receiving host because the available automation provider
blocked `file://`; the deployment receipt must record that check before operational
  pilot acceptance.
