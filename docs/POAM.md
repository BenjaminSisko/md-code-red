# Plan of Action and Milestones (POAM) -- MD CODE RED

**Status:** In Draft
**Owner:** Noor Patel (ISSO / security engineer, content) with Alex Okafor (Compliance Officer, control and evidence mapping)
**Last Updated:** 2026-10-01 (alpha.6 release-evidence reconciliation; no new
closure authority asserted)

---

## Overview

This POAM tracks open security findings, compliance gaps, and remediation
schedules for MD CODE RED.

**Finding Status Definitions:**
- **Open:** Identified, not yet resolved
- **In Progress:** Owner assigned, work underway
- **Remediated:** Fix implemented, awaiting verification
- **Verified:** Fix verified by security review, closed

---

## Open Findings

| Finding ID | Severity | Category | Owner | Status | Due Date | Description |
|---|---|---|---|---|---|---|
| POAM-CONTENT-001 | MEDIUM | Content Verification | Caleb Stone (or a named delegate) | Open | Not yet scheduled | RHEL 9 now has raw captures from `rhel9-stig-test` and a release-specific 22-tool flag dictionary (`content/flags_rhel9.json`; 20 tools available, 964 extracted flag rows). That capture work does not independently verify commands: none of the build's 18 QA-reviewed `verified[version]` receipts is for RHEL 9. The remaining action is to capture and independently review representative RHEL 9 command executions under `docs/WORKFLOW.md` Section 2a. Flag availability, curated flag explanation, and command verification are separate claims; this finding tracks the last of those. |
| POAM-CONTENT-002 | LOW | Content Coverage | Caleb Stone (RHEL 7 host access, or continued container use) | Open | Not yet scheduled | RHEL 7 flags are read from a UBI7 *container* standing in for a real RHEL 7 host (none exists in the lab) and cover only 6 of the probed tools (`systemctl`, `journalctl`, `yum`, `useradd`, `usermod`, `chage`); the container ships no `man`/`man-db` at all, so every result is `--help`-only, and kernel/systemd-manager-dependent behavior was never observed. RHEL 7's pinned STIG (V3R15) is also DISA's stated terminal release (`docs/WORKFLOW.md`, "The RHEL 7 frozen source") -- worth weighing against POAM-CONTENT-001 when prioritizing: RHEL 7's ceiling is fixed either way, RHEL 9's is not. |
| POAM-CONTENT-003 | LOW | Curation Coverage | Not yet assigned (RHEL SME) | Open | Not yet scheduled | 0 of 3,178 flag-dictionary entries across RHEL 7/8/9/10 carry a curated `explain` (the extractor deliberately writes `null`; curation is a separate human step that has not started). The curated catalog itself supplies explanations for 336 of 348 option/subcommand uses; the remaining 12 render the explicit unverified fallback. The no-guess rule means the dictionary gap does not cause invented guidance, but completing independent flag curation would broaden the Inspector beyond commands already covered by curated entry content. |
| POAM-QA-001 | LOW | Test Coverage | Not yet assigned | Open | Not yet scheduled | `docs/TEST_PLAN.md`'s Spot-Check Sampling section has no assigned rate or lead -- independent human re-verification of curated content (as distinct from the automated gates, which prove structure and safety but not "does this explanation read correctly") has no owner. |

### Example Entry (retained from the original skeleton for format reference)

| Finding ID | Severity | Category | Owner | Status | Due Date | Description |
|---|---|---|---|---|---|---|
| SSP-001 | MEDIUM | Input Validation | Zee | Remediated (awaiting formal closure) | Not scheduled | All form-field grammars reject NUL and enforce a per-type length cap; the hostile fixture includes NUL and 4,096-character overlength vectors, and `tests/test_hostile_inputs.py` requires them to be exercised against every field type. |

(SSP-001 above predates this pass and is retained as the format example the
skeleton originally used. The implementation and automated tests demonstrate
remediation: `template.html`'s field grammars reject controls and cap length,
and the current hostile harness completes with zero failures, including the
fixture's NUL and two overlength cases. No named security reviewer has recorded
formal closure, so the status remains Remediated rather than Verified.)

---

## D4 security-review residuals -- accepted with a date

Added by Milo Vance, 2026-09-17, under conditions E4 and E5 of Marcus Reed's D4
review of `salm/milo/generators`. These are the items the review raised that are
**not** closed by code in that branch, recorded here rather than dropped. Noor's
sections above are untouched.

| Finding ID | Severity | Category | Owner | Status | Accepted on | Description and what holds it |
|---|---|---|---|---|---|---|
| MCR-SEC-020 | LOW | Provenance / Explainer | **Caleb Stone** (extractor, CR-T-09 follow-up) | **Retired 2026-09-20** | 2026-09-17 | The named parser defect is closed: `--add-rich-rule` is present in the independently captured RHEL 8, 9 and 10 dictionaries. Q20 still compares all 70 captured tool/release pairs and fails if any recorded shortfall grows. The remaining raw-token differences are retained as a regression ratchet because that numerator deliberately includes prose and per-subcommand mentions; the inspector continues to say *"unverified -- see man page"* when prose has not been curated. Jordan Patel and Zee Carter recorded retirement under Benny's recovery authorization. `tests/test_coverage_baseline_expiry.py` proves that a retired record remains valid after the former deadline only when named authority and retirement evidence are present; deleting that evidence fails the test. |
| MCR-SEC-016 (residual) | LOW | Input Validation | Milo Vance | Accepted | 2026-09-17 | `gen-chronyd-one-shot-check`'s `-Q` field stays `comment` (free text): it takes a whole chrony config directive, which is structurally the same class as the rich-rule field that produced MCR-SEC-001 -- a config grammar overlapping nothing in the shell and everything in chrony. Bounded today: one-shot, writes no config, correctly `shQuote`d, and it is the only such field. **Before `-Q` grows a second use it must be composed from validated sub-fields the way rich rules now are.** Marcus raised this without rating it; it is recorded so the next author meets it. |
| MCR-SEC-014 | INFORMATIONAL | Render safety | Milo Vance | Accepted (D2, re-confirmed) | 2026-09-17 | Q17's render-sink audit cannot catch a run-time-derived property name (`el[k] = raw` with `k` from a data object). Documented in `qa.py` and `docs/CODE_STANDARDS.md` Section 1. Unchanged by this branch. |
| MCR-SEC-025 | INFO | Provenance / Explainer | Milo Vance | Closed | 2026-09-17 | `gen-chronyd-one-shot-check` modelled the chrony directive as `-Q`'s value. The pinned capture settles it: chronyd(8) SYNOPSIS is `chronyd [OPTION]... [DIRECTIVE]...` (content-src/raw/rhel8/chronyd.man.txt#L7, identical on RHEL 10) and `-Q` takes no argument (#L68) -- directives are OPERANDS accepted after the options, so the emitted command `chronyd -Q 'server time.mil iburst'` is correct and stays. Citation repointed from `man 8 chronyd` to the `-Q` line in the capture, and the operand grammar recorded in the entry's `notes`, which the renderer surfaces to the operator. |

---

## Compliance Gaps (NIST 800-53)

| Control | Status | Plan | Target Date |
|---|---|---|---|
| AC-2 (Account Management) | Deferred | N/A (offline tool, no user accounts) | N/A |
| The remaining selected-baseline controls | Not yet mapped | `docs/SSP.md` Section 4 states what is informally checkable today (CM-6, CM-7, AC-17, SC-7, SI-2); a full control-by-control narrative is Alex Okafor's work, not started | TBD |

---

## Remediation Schedule

**Phase 1 (Pre-Pilot):**
- Close or formally disposition the four open content and QA findings above
  (POAM-CONTENT-001/002/003, POAM-QA-001) before scheduling
  `docs/TEST_PLAN.md`'s pilot. RHEL 9 flag capture is complete; RHEL 9 command
  receipts, RHEL 7 host evidence, flag-explanation curation, and independent
  content spot-check ownership remain separate gaps.
- Target: Not scheduled. The former 2026-09-30 skeleton date had no recorded
  recommitment and is not presented as an approved deadline.

**Phase 2 (Post-Pilot):**
- Address medium findings from pilot feedback.
- Target: Not scheduled until the pilot is authorized and run.

**Phase 3 (Pre-Release):**
- All findings resolved before v1.0.0 ship.
- Target: TBD (depends on pilot success).

---

## Metrics

**Current counts, read directly off this build rather than left as N/A:**

- Total findings tracked in this file: 9 (4 open in the main table, 4 in the
  D4 residuals table, and 1 retained example).
- Status counts: 4 Open, 1 Remediated awaiting formal closure, 2 Accepted,
  1 Retired, and 1 Closed.
- Findings closed or retired: 2 (MCR-SEC-025 closed; MCR-SEC-020 retired with
  authority and evidence on 2026-09-20). MCR-SEC-016 and MCR-SEC-014 remain
  Accepted, and SSP-001 remains Remediated, so none is counted as closed.
- Findings with a live hard expiry date: 0. MCR-SEC-020's baseline retains its
  historical 2026-09-25 retirement date, but the tested retirement evidence
  keeps that former deadline from remaining an open expiry.
- Critical findings aging > 30 days: none tracked in this file at CRITICAL
  severity.

---

**Contact:** Noor Patel, Alex Okafor (via Dani Mercer, XO)
