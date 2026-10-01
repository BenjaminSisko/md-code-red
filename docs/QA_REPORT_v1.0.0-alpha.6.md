---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# QA Report -- v1.0.0-alpha.6

The final candidate completed the full verification sequence on 2026-10-01.
The detailed rendered-browser record is available in
[`docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html`](qa/QA_REPORT_v1.0.0-alpha.6-rc.html)
and its machine-readable companion
[`docs/qa/QA_RESULTS_v1.0.0-alpha.6-rc.json`](qa/QA_RESULTS_v1.0.0-alpha.6-rc.json).
The same audit was also run through the local HTTP delivery path; that record is
[`docs/qa/QA_RESULTS_v1.0.0-alpha.6-rc-http.json`](qa/QA_RESULTS_v1.0.0-alpha.6-rc-http.json).

| Check | Result |
|---|---|
| Reproducible build | PASS; two HTML, sidecar, and placeholder-provenance cycles were byte-identical and matched the committed artifact |
| Build-time schema validation | PASS |
| QA gates | PASS; Q1-Q26 plus JavaScript syntax |
| Python unit suite | PASS; 429 tests |
| Hostile-input harness | PASS; 145,345 checks, zero failures |
| Standalone rendered-browser audit | PASS; 889 of 889 assertions, zero runtime exceptions, zero console errors |
| HTTP rendered-browser audit | PASS; 889 of 889 assertions, zero runtime exceptions, zero console errors |
| Real-keystroke guided-field matrix | PASS; 109 text controls, complete values, retained focus, zero exceptions |
| Entry/release matrix | PASS; all 200 entries across RHEL 7, 8, 9, and 10 |
| Responsive layouts | PASS; 320, 390, 768, 1024, and 1440 pixel widths |
| Standalone file delivery | PASS; zero network resources, no overflow, editable grep result exact |
| Generator golden commands | PASS; 232 release-specific comparisons |
| Command syntax oracle | PASS; 869 simple invocations, 420 release-specific grammar rows |
| Pipeline hostile-input checks | PASS; 23,032 checks plus 232 one-stage invariants |
| Real reference-export snapshot | PASS after deliberate date and fingerprint refresh |
| Generated release facts | PASS; current against source data |
| `git diff --check` | PASS |

The candidate contains 200 curated entries across 102 tools: 58 guided
generators and 142 static entries. The audit exercised navigation, search,
clipboard payloads, evidence export, persisted state, reference acknowledgement,
generated files, invalid input, task routes, responsive reading order, pipeline
composition, composed-command verification state, incomplete pipelines, Home
package routing, exact receipt binding, form-driven status-bar refresh, and
value-bound runbooks. The third independent review's real-input reproduction is
now a release gate: every guided text control is typed character by character,
and the pipeline redirect path and xargs batch size have dedicated CDP checks.
The audit also verifies that editing a red command clears its acknowledgement,
partial re-renders retain focus, the first valid input announces readiness,
rendered warning/control contrast exceeds 4.5:1, searched STIG rules remain
visible beside a pipeline, target-specific blast reasons survive composition,
and download recovery preserves an existing destination. The user-reported grep task produced
exactly `grep -r -n -i 'laundry' '/etc'` from five editable controls.

Known evidence limits remain visible: RHEL 7 and RHEL 9 have no independently
reviewed command receipts; RHEL 8 and RHEL 10 have nine each. A composed
pipeline is explicitly labeled not host-verified and cannot inherit an
individual stage receipt. Browser-generated reference text is not proof that a
command ran. Live assistive-technology sessions are a separate acceptance
activity and are not claimed by this report.
