# Plan of Action and Milestones (POAM) -- MD CODE RED

**Status:** In Draft
**Owner:** Noor Patel (ISSO / security engineer, content) with Alex Okafor (Compliance Officer, control and evidence mapping)
**Last Updated:** 2026-09-17 (content-gap items added by Sam Kim, Technical Writer, Stage 07)

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
| MCR-SEC-020 | LOW | Provenance / Explainer | Caleb Stone (extractor fix, CR-T-09 follow-up) | Open (ratchet expiring) | 2026-09-25 | See "D4 security-review residuals" below -- carried here as the same finding, same owner, same date, not a duplicate. |
| POAM-CONTENT-001 | MEDIUM | Content Coverage | Caleb Stone (or a named delegate) | Open | Not yet scheduled | RHEL 9 has no flag dictionary and no captures at all (`content/flags_rhel9.json` is an empty, pending skeleton; blocked on a reachable RHEL 9 host). Every RHEL 9 command's Inspector panel reads "unverified -- see man page" regardless of curation done for the same flag on RHEL 8/10, and no RHEL 9 entry can carry a `verified` receipt. RHEL 9 is also this build's default version on load (`docs/ARCHITECTURE_BIBLE.md` Section 23), so it is the first thing a new operator sees. |
| POAM-CONTENT-002 | LOW | Content Coverage | Caleb Stone (RHEL 7 host access, or continued container use) | Open | Not yet scheduled | RHEL 7 flags are read from a UBI7 *container* standing in for a real RHEL 7 host (none exists in the lab) and cover only 6 of the probed tools (`systemctl`, `journalctl`, `yum`, `useradd`, `usermod`, `chage`); the container ships no `man`/`man-db` at all, so every result is `--help`-only, and kernel/systemd-manager-dependent behavior was never observed. RHEL 7's pinned STIG (V3R15) is also DISA's stated terminal release (`docs/WORKFLOW.md`, "The RHEL 7 frozen source") -- worth weighing against POAM-CONTENT-001 when prioritizing: RHEL 7's ceiling is fixed either way, RHEL 9's is not. |
| POAM-CONTENT-003 | LOW | Curation Coverage | Not yet assigned (RHEL SME) | Open | Not yet scheduled | 0 of 2,009 flag-dictionary entries across RHEL 7/8/10 carry a curated `explain` (the extractor deliberately writes `null`; curation is a separate human step that has not started). Only 4 flags anywhere in the shipped build carry curated text, all on the 3 static STIG-sourced entries. The no-guess rule means this is not a defect in what ships, but it means the Inspector is not yet a teaching tool for most of the catalog. |
| POAM-QA-001 | LOW | Test Coverage | Not yet assigned | Open | Not yet scheduled | `docs/TEST_PLAN.md`'s Spot-Check Sampling section has no assigned rate or lead -- independent human re-verification of curated content (as distinct from the automated gates, which prove structure and safety but not "does this explanation read correctly") has no owner. |

### Example Entry (retained from the original skeleton for format reference)

| Finding ID | Severity | Category | Owner | Status | Due Date | Description |
|---|---|---|---|---|---|---|
| SSP-001 | MEDIUM | Input Validation | Zee | Open | 2026-10-01 | Validate that all form fields reject null bytes and overly long strings |

(SSP-001 above predates this pass and is retained as the format example the
skeleton originally used -- it is not re-verified here. All form fields
currently do reject control characters and enforce a per-type length cap,
per `docs/ARCHITECTURE_BIBLE.md` Section 5's `FIELD_TYPES` table and
`tests/hostile_harness.js`'s 81,577 checks, so this specific item reads as
already addressed; Zee/Noor should confirm and close it formally rather than
this document asserting closure on their behalf.)

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
- Close or formally accept-with-date the four content-coverage findings above
  (POAM-CONTENT-001/002/003, POAM-QA-001) before scheduling
  `docs/TEST_PLAN.md`'s pilot -- running a pilot against RHEL 9's empty flag
  dictionary and mostly-uncurated flag panel would surface these as pilot
  findings rather than validate a feature-complete build.
- Target: 2026-09-30 (retained from the original skeleton; not re-committed to
  by this pass).

**Phase 2 (Post-Pilot):**
- Address medium findings from pilot feedback.
- Target: 2026-10-31.

**Phase 3 (Pre-Release):**
- All findings resolved before v1.0.0 ship.
- Target: TBD (depends on pilot success).

---

## Metrics

**Current counts, read directly off this build rather than left as N/A:**

- Total findings tracked in this file: 9 (4 open in the main table, 4 in the
  D4 residuals table -- one of which, MCR-SEC-020, is the same underlying
  finding as its main-table counterpart and is not double-counted -- and 1
  retained example).
- Findings closed: 2 (MCR-SEC-025, and MCR-SEC-016/MCR-SEC-014 accepted rather
  than closed, so not counted here as closed).
- Findings with a hard expiry date: 1 (MCR-SEC-020 / Q20's baseline, 2026-09-25
  -- 8 days out as of this writing).
- Critical findings aging > 30 days: none tracked in this file at CRITICAL
  severity.

---

**Contact:** Noor Patel, Alex Okafor (via Dani Mercer, XO)
