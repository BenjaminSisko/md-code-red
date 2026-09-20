---
type: deploy-receipt
status: draft
last_verified: 2026-09-20
---

# Pilot Receipt -- v1.0.0-alpha.3

This is a pre-deployment receipt template populated only with source-controlled
candidate facts. It is not evidence that alpha.3 was deployed, opened in a
browser, witnessed, or operationally accepted. A receiving admin and named Riley
witness must complete the pending fields after Jordan's integration/release
action and an authorized deployment.

| Field | Recorded value |
|---|---|
| Version | `v1.0.0-alpha.3` |
| Artifact | `dist/md-code-red_v1.0.0-alpha.3.html` |
| Artifact SHA-256 | `62c80e950d82ed55086f383ce1918b76ed1425cea9c064d791e9a2e5c7283818` |
| Content fingerprint | `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea` |
| Signature status | UNSIGNED -- SHA-256 integrity plus Git/release lineage only |
| Proposed tag | `v1.0.0-alpha.3` -- not created |
| Automated check | Q1-Q25+JS PASS; 336 unit tests PASS; 101,297 hostile checks PASS; rail-keyboard source and built-artifact contracts PASS; deterministic double-build PASS |
| Known limitations | `docs/CHANGELOG.md`, `docs/QA_REPORT_v1.0.0-alpha.3.md`, and `docs/SECURITY_REVIEW_v1.0.0-alpha.3.md` |
| Rollback artifact | `releases/v1.0.0-alpha.2/md-code-red_v1.0.0-alpha.2.html`, SHA-256 `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a` |
| Riley exact-head regression review | PENDING until recorded on the candidate PR |
| Deployment state | NOT DEPLOYED |
| Receiving host / browser | PENDING; no host or browser is claimed by this document |
| Deployed path | PENDING |
| Deployed by / time | PENDING |
| Independent verifier / time | PENDING |
| About version/fingerprint readback | NOT EXECUTED |
| Keyboard-only walkthrough | NOT EXECUTED in an approved receiving-host browser |
| Live zero-network observation | NOT EXECUTED |
| Named human operational use | NOT EXECUTED |
| Pilot verdict | HOLD until every pending receiving-host field is completed |

## Required receiving-host procedure

1. Record the approved host, operating-system level, browser/version, operator,
   Riley witness, start time, and end time.
2. Transfer the released alpha.3 artifact, sidecar, and stamped provenance using
   the approved path. Do not use this unstamped PR candidate as a release.
3. Verify the sidecar before opening the file.
4. Open the exact local alpha.3 file in the approved browser and confirm the
   About panel shows version `v1.0.0-alpha.3` and fingerprint
   `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea`.
5. Exercise `Ctrl+Alt+1` through `Ctrl+Alt+6`, confirming each shortcut selects
   and focuses its advertised rail, especially `Ctrl+Alt+6` for About.
6. Complete the ordinary command, search, evidence-export, favorites/recent,
   theme, print, and keyboard-only smoke paths required by the pilot SOP.
7. Observe and record zero network activity for the local-file session.
8. If any identity, sidecar, keyboard, console, network, or workflow check fails,
   close alpha.3 and return to the verified alpha.2 rollback artifact.

## Jordan handoff state

| Required field | Current state |
|---|---|
| Correction | `MCR-A2-KEY-001` automated regression PASS |
| Release-readiness packet | `docs/RELEASE_REPORT_v1.0.0-alpha.3.md` |
| Reviewer state | Awaiting Riley exact-head PR review |
| Deployment state | Not deployed |
| Browser/pilot state | Hold; no acceptance claimed |
| Forecast impact | Keyboard blocker removed in source; release depends on exact-head review, Jordan integration/tag/publish, then named-human browser/pilot evidence |
