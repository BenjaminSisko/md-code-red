---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# QA Report -- v1.0.0-alpha.6

Verification totals: 480 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser records in each delivery mode (896 pass/fail assertions and 2 performance observations).

The final candidate completed the full verification sequence on 2026-10-01.
The detailed rendered-browser record is available in
[`docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html`](qa/QA_REPORT_v1.0.0-alpha.6-rc.html)
and its machine-readable companion
[`docs/qa/QA_RESULTS_v1.0.0-alpha.6-rc.json`](qa/QA_RESULTS_v1.0.0-alpha.6-rc.json).
The same audit was also run through the local HTTP delivery path; that record is
[`docs/qa/QA_RESULTS_v1.0.0-alpha.6-rc-http.json`](qa/QA_RESULTS_v1.0.0-alpha.6-rc-http.json).

| Traceability fact | Candidate value |
|---|---|
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,791 bytes |
| Artifact SHA-256 | `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Content fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Implementation source | `11b167159cb2246004e5f457df6f0c155d1c32cb` |

| Check | Result |
|---|---|
| Reproducible build | PASS; two HTML, sidecar, and placeholder-provenance cycles were byte-identical and matched the committed artifact |
| Build-time schema validation | PASS |
| QA gates | PASS; Q1-Q26 plus JavaScript syntax |
| Python unit suite | PASS; 480 tests |
| Hostile-input harness | PASS; 168,697 checks, zero failures |
| Standalone rendered-browser audit | PASS; 896 of 896 pass/fail assertions plus 2 informational performance observations, zero runtime exceptions, zero console errors |
| HTTP rendered-browser audit | PASS; 896 of 896 pass/fail assertions plus 2 informational performance observations, zero runtime exceptions, zero console errors |
| Real-key guided-field matrix | PASS; 109 text controls entered with CDP key-down/key-up sequences, complete values, retained focus, zero exceptions |
| Entry/release matrix | PASS; all 200 entries across RHEL 7, 8, 9, and 10 |
| Responsive layouts | PASS; 320, 390, 768, 1024, and 1440 pixel widths |
| Standalone file delivery | PASS; zero network resources, no overflow, editable grep result exact |
| Generator golden commands | PASS; 232 release-specific comparisons |
| Command syntax oracle | PASS; 869 simple invocations, 420 release-specific grammar rows |
| Pipeline hostile-input checks | PASS; 27,652 checks plus 232 one-stage invariants |
| Real reference-export snapshot | PASS after deliberate date and fingerprint refresh |
| Generated release facts | PASS; current against source data |
| `git diff --check` | PASS |

The candidate contains 200 curated entries across 102 tools: 58 guided
generators and 142 static entries. The audit exercised navigation, search,
clipboard payloads, evidence export, persisted state, reference acknowledgement,
generated files, invalid input, task routes, responsive reading order, pipeline
composition, composed-command verification state, incomplete pipelines, Home
package routing, exact receipt binding, form-driven status-bar refresh, and
value-bound runbooks. The independent reviews' real-input reproductions are now
release gates: every guided text control is typed with key-down/key-up pairs,
and the pipeline redirect path and xargs batch size have dedicated CDP checks.
The audit also uses real pointer input to prove that the first Copy,
acknowledgement, and Add-to-pipeline click after typing is not swallowed; the
clipboard matches the changed command; stale success text clears; and Tab moves
to the next control. It verifies that editing a red command clears its
acknowledgement, partial re-renders retain focus, the first valid input announces
readiness, rendered warning/control/placeholder contrast exceeds 4.5:1, linked
STIG selection closes the palette and focuses evidence in view at 390 pixels,
keyboard Copy retains focus, target-specific blast reasons survive composition,
and the browser renders bound transfer protocols. The transaction execution
matrix uses the app's own instruction binder, reproduces OpenSSH
argument joining, and exercises existing-target restore, directory-target
resolution, absent-target recovery, stale-state refusal, rsync tree restore,
transaction finalization, SCP/rsync symlink refusal, atomic race handling,
foreign-owner refusal, unsafe shared-parent refusal, explicit symlinked-parent
refusal, GNU `mv -T` behavior, bounded raced-symlink replacement before and
after removal, and exact status-1 HUP, INT, and TERM cleanup for both transfer
methods. A persistent-replant case runs with a hard timeout and proves the
failure path exits exactly 1 after six bounded removals, leaves the attacker
link in place, does not touch its sentinel, and retains transaction `state`,
`before`, and `after`. Every link-race check also requires the outside directory
to contain only that sentinel, so a write through the link cannot pass. Separate
SCP and rsync cases prove exact status 1 and rollback preservation when a raced
link cannot be removed, when a non-link directory is planted at the target, and
when an attacker stops after three replants. Mutation controls catch returning
success from the link check, removal failure, retry exhaustion, or outer
failure, and catch deleting the transaction on failure. Recover and Finalize
also run against symlinked
destinations, unsafe or symlinked parents, and positive SCP/rsync finalization
paths. The NetworkManager execution matrix proves a space-bearing connection
name backs up and restores the actual profile, while
missing/duplicate/numeric-looking names and pre-existing, symlinked, raced,
incorrectly permissioned, or forged-owner transaction state are handled
through the app-bound command. Its pre-install symlink case starts the link
target at mode `0755` and proves the target remains unchanged; Recover and
Finalize independently reject an incorrectly permissioned state root. Positive
Finalize coverage proves the trusted state is cleared, and signal execution
uses child processes with default handlers before asserting exact status 1.
The browser audit compares the copied rsync Recover payload byte for byte with
the external instruction-binding probe, refuses any Preflight or Finalize
marker in that payload, and counts exactly one keyboard activation and one
clipboard write. Its structural companion scans the complete shell and permits
one literal delegated `keydown` listener, rejects literal `keyup`/`keypress`,
property, and call/apply registration forms, forbids copy or synthetic-event
routing in the approved handler, and keeps Enter and Space out of the global
shortcut table. Forgejo CI builds the HTML before test discovery but preserves the
committed, release-workstation provenance rather than dirtying protected
evidence with runner-specific toolchain versions. Standalone and HTTP audits
write separate raw result files and compare the main-document bytes returned by
CDP with the audited file before recording results. The user-reported
grep task produced
exactly `grep -r -n -i 'laundry' '/etc'` from five editable controls.

Known evidence limits remain visible: RHEL 7 and RHEL 9 have no independently
reviewed command receipts; RHEL 8 and RHEL 10 have nine each. A composed
pipeline is explicitly labeled not host-verified and cannot inherit an
individual stage receipt. Browser-generated reference text is not proof that a
command ran. Live assistive-technology sessions are a separate acceptance
activity and are not claimed by this report.
