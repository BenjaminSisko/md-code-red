---
type: deploy-receipt
status: pending-human-acceptance
last_verified: 2026-09-20
---

# Pilot Receipt -- v1.0.0-alpha.2

This is a real candidate handoff record for the recovery build. It is not a human
operational-acceptance claim. The receiving admin completes the remaining named
fields after opening the exact artifact on the pilot host.

| Field | Recorded value |
|---|---|
| Version | v1.0.0-alpha.2 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.2.html` |
| Artifact SHA-256 | `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a` |
| Sidecar verified during build acceptance | Yes |
| Content fingerprint | `f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83` |
| Signature status | UNSIGNED -- SHA-256 integrity only |
| Candidate source revision | `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a` |
| Tagged merge revision | `8186e104fdc3ebbe08a037442787ae5d2c7b01d7` |
| Built on | Mac control workstation recovery worktree |
| Built on date | 2026-09-20 |
| Automated post-build check | Fresh exact-tag run on 2026-09-20: Q1-Q25 + JS PASS; 333 unit tests PASS; 101,297 hostile checks PASS |
| Content sample | PASS: deterministic 2/18 verified receipts (10%, rounded up), fresh read-only reruns on Defiant RHEL 8 and Saratoga RHEL 10; 0 red-blast receipts |
| Known limitations | `docs/CHANGELOG.md`, v1.0.0-alpha.2; `docs/QA_REPORT_v1.0.0-alpha.2.md` |
| Rollback artifact | Repository: `releases/v1.0.0-alpha.1/md-code-red_v1.0.0-alpha.1.html`; Defiant staging: `/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.1/md-code-red_v1.0.0-alpha.1.html`, SHA-256 `65de40be58477d3bb1b781d7e2188b2d78329616732971a8bf37fbc7e7b2c665` |
| Receiving host census ID | Defiant / `01 Devices/Defiant RHEL 8.md` |
| Deployed path | `/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/md-code-red_v1.0.0-alpha.2.html` (read-only staging; not yet the path used for browser QA) |
| Deployment staging readback | PASS on 2026-09-20: file is 8,797,475 bytes, mode `0440`, owner `adm-linux:adm-linux`; sidecar check passed; provenance reports the exact tag, artifact SHA-256, and fingerprint |
| Deployed by / on | Staged by `MCR-REC-20260920-09` task on 2026-09-20; **named human operator/time acknowledgment pending** |
| Independent verifier | **Pending receiving admin** |
| Browser/About/network check | **B-1 PASS WITH LIMITATION:** exact-byte temporary copy opened through `file://` on Defiant/RHEL 8.10 with Firefox ESR 140.14.0; About matched version/fingerprint; console was empty; monitored reload showed one local document row at 0 B and zero external requests. The remote session required networking, so OS-network-disabled acceptance remains pending |
| Approved matrix readiness | **Partial, 1/6:** Defiant/Firefox B-1 PASS; no Firefox/Chromium package was observed on Saratoga or `rhel9-stig-test`; no RHEL Chromium cell or approved Windows jump-box host is named. Edge/B-6 is added-value; B-2 through B-5 remain required gaps |
| Browser defects | **Blocking: six rails ship, About advertises `Ctrl+Alt+6`, but the key map binds only `1`-`5`; user/pilot shortcut documentation conflicts** |
| Content review | **FAIL WITH TWO MEDIUM DEFECTS:** fixed-stride reference-corpus sample reviewed 59/23,447 positive citations plus 55/19,413 residue rows; false truncation and omitted runnable commands are recorded in the QA report |
| Operational pilot acceptance | **Pending named human use; not inferred from automated QA or the Riley-owned browser receipt** |

## Evidence boundary and current verdict

The exact released bytes passed automated acceptance and the required 2/18
verified-receipt sample. An exact-byte temporary copy also passed a true local-
file browser walkthrough on Defiant in Firefox ESR: About identity, core journeys,
zero console errors, and zero external network requests were observed. This was
a QA receipt on a temporary copy, not named-human use of the read-only staged
path and not operational acceptance. The temporary graphical environment was
removed after testing.

**Pilot verdict: HOLD.** The tagged artifact has a blocking keyboard defect, two
Medium reference-corpus defects, and only 1/6 browser cells completed. The exact
bytes are staged read-only on Defiant and independently re-hashed; browser QA
used a different temporary path with the same hash. Leave named human operator/
time, independent verifier, staged-path browser use, remaining matrix cells,
OS-network-disabled check, and operational acceptance pending until actual
evidence exists.
