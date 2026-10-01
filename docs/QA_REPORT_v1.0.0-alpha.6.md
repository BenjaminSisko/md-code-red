---
type: release-evidence
status: candidate
last_verified: 2026-09-30
---

# QA Report -- v1.0.0-alpha.6

The final-version candidate completed the full verification sequence on
2026-09-30. The detailed rendered-browser record is available in
[`docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html`](qa/QA_REPORT_v1.0.0-alpha.6-rc.html)
and its machine-readable companion
[`docs/qa/QA_RESULTS_v1.0.0-alpha.6-rc.json`](qa/QA_RESULTS_v1.0.0-alpha.6-rc.json).

| Check | Result |
|---|---|
| Reproducible build | PASS; two clean HTML, sidecar, and placeholder-provenance cycles were byte-identical |
| Build-time schema validation | PASS |
| QA gates | PASS; Q1-Q26 plus JavaScript syntax |
| Python unit suite | PASS; 419 tests |
| Hostile-input harness | PASS; 128,449 checks, zero failures |
| Rendered-browser audit | PASS; 867 of 867 assertions, zero runtime exceptions, zero console errors |
| Entry/release matrix | PASS; all 200 entries across RHEL 7, 8, 9, and 10 |
| Responsive layouts | PASS; 320, 390, 768, 1024, and 1440 pixel widths |
| Standalone file delivery | PASS; zero network resources, no overflow, editable grep result exact |
| Generator golden commands | PASS; 232 release-specific comparisons |
| Command syntax oracle | PASS; 869 simple invocations, 420 release-specific grammar rows |
| Real reference-export snapshot | PASS after deliberate alpha.6 version and fingerprint refresh |
| Generated release facts | PASS; current against source data |
| Gitleaks | PASS; 200 reachable commits and 97.90 MB scanned, no leaks |
| `git diff --check` | PASS |

The candidate contains 200 curated entries across 102 tools: 58 guided
generators and 142 static entries. The audit exercised navigation, search,
clipboard payloads, evidence export, persisted state, reference acknowledgement,
generated files, invalid input, task routes, responsive reading order, and
pipeline composition. The user-reported grep task produced exactly
`grep -r -n -i 'laundry' '/etc'` from five editable controls. The pipeline
inspector rendered stage verification without an exception.

Known evidence limits remain visible: RHEL 7 and RHEL 9 have no independently
reviewed command receipts; RHEL 8 and RHEL 10 have nine each. Browser-generated
reference text is not proof that a command ran. Live assistive-technology
sessions are a separate acceptance activity and are not claimed by this report.
