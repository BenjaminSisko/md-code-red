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
| Rollback artifact | `releases/v1.0.0-alpha.1/md-code-red_v1.0.0-alpha.1.html` |
| Receiving host census ID | **Pending receiving admin** |
| Deployed path | **Pending receiving admin** |
| Deployed by / on | **Pending receiving admin** |
| Independent verifier | **Pending receiving admin** |
| Browser/About/network check | **Pending: local `file://` automation was blocked by provider policy; static Q1/Q2 checks are not a visual About readback or live network receipt** |
| Approved matrix readiness | **Blocked: Defiant has Firefox ESR 140.14.0; no Firefox/Chromium package was observed on Saratoga or `rhel9-stig-test`; no RHEL Chromium cell or approved Windows jump-box host is named** |
| Browser defects | **Blocking: six rails ship, About advertises `Ctrl+Alt+6`, but the key map binds only `1`-`5`; user/pilot shortcut documentation conflicts** |
| Operational pilot acceptance | **Pending named human use; not inferred from automated QA** |

## Evidence boundary and current verdict

The exact released bytes passed automated acceptance and the required content
sample. No approved-host browser was opened in this review, so the About-panel
version/fingerprint were not visually read back and zero network activity was not
observed live. The browser provider rejected the local URL and explicitly barred
alternate-surface workarounds; no bypass was attempted.

**Pilot verdict: HOLD.** The tagged artifact has a blocking keyboard defect and
the approved host/browser matrix is not ready. Leave receiving host, deployment,
independent verifier, browser/network check, and operational acceptance fields
pending until actual named-human evidence exists.
