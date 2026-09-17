# Plan of Action and Milestones (POAM) — MD CODE RED

**Status:** In Draft  
**Owner:** Noor Patel (ISSO / security engineer, content) with Alex Okafor (Compliance Officer, control and evidence mapping)  
**Last Updated:** 2026-09-17

---

## Overview

This POAM tracks open security findings, compliance gaps, and remediation schedules for MD CODE RED.

**Finding Status Definitions:**
- **Open:** Identified, not yet resolved
- **In Progress:** Owner assigned, work underway
- **Remediated:** Fix implemented, awaiting verification
- **Verified:** Fix verified by security review, closed

---

## Open Findings

**Format:** [Finding ID] | Severity | Category | Owner | Status | Due Date | Description

**TODO:** Populate after initial security review. Expected categories: Input Validation, Output Encoding, Air-Gap Compliance, Third-Party Dependencies, Access Control.

### Example Entry (Delete after skeleton approval)

| Finding ID | Severity | Category | Owner | Status | Due Date | Description |
|---|---|---|---|---|---|---|
| SSP-001 | MEDIUM | Input Validation | Zee | Open | 2026-10-01 | Validate that all form fields reject null bytes and overly long strings |

---

## D4 security-review residuals — accepted with a date

Added by Milo Vance, 2026-09-17, under conditions E4 and E5 of Marcus Reed's D4
review of `salm/milo/generators`. These are the items the review raised that are
**not** closed by code in this branch, recorded here rather than dropped. Noor's
sections above are untouched.

| Finding ID | Severity | Category | Owner | Status | Accepted on | Description and what holds it |
|---|---|---|---|---|---|---|
| MCR-SEC-020 | LOW | Provenance / Explainer | **Caleb Stone** (extractor fix, CR-T-09 follow-up) | Accepted, retires **2026-09-25** | 2026-09-17 | The flag dictionary is systematically incomplete against the raw captures — `firewall-cmd` carries 16 of 205 long options on RHEL 8, `--add-rich-rule` among the missing. No product risk: the three firewall generators carry `flags: null`, so the inspector renders *"unverified — see man page"* rather than a fabricated explanation, which is the no-guess law working under a dictionary gap. The defect was that **nothing could see the gap** (Q15 re-runs the extractor and diffs its output against itself). Held by: new gate **Q19**, measuring every tool/release pair against `content-src/flag_coverage_baseline.json` and failing when a shortfall **grows**. Closing the shortfall itself belongs to CR-T-09/10. **Retirement plan (condition F3):** Caleb Stone owns the extractor fix; the baseline retires 2026-09-25, and Q20 FAILS from 2026-09-26 unless the file is regenerated against the new dictionaries or re-dated in writing — proved firing in `tests/test_coverage_baseline_expiry.py`, not taken on trust. An accepted residual does not get to become a permanent one by nobody looking. |
| MCR-SEC-016 (residual) | LOW | Input Validation | Milo Vance | Accepted | 2026-09-17 | `gen-chronyd-one-shot-check`'s `-Q` field stays `comment` (free text): it takes a whole chrony config directive, which is structurally the same class as the rich-rule field that produced MCR-SEC-001 — a config grammar overlapping nothing in the shell and everything in chrony. Bounded today: one-shot, writes no config, correctly `shQuote`d, and it is the only such field. **Before `-Q` grows a second use it must be composed from validated sub-fields the way rich rules now are.** Marcus raised this without rating it; it is recorded so the next author meets it. |
| MCR-SEC-014 | INFORMATIONAL | Render safety | Milo Vance | Accepted (D2, re-confirmed) | 2026-09-17 | Q17's render-sink audit cannot catch a run-time-derived property name (`el[k] = raw` with `k` from a data object). Documented in `qa.py` and `docs/CODE_STANDARDS.md`; reaching it takes two deliberate acts by someone with commit rights, across two CODEOWNERS-protected paths. Unchanged by this branch. |
| MCR-SEC-025 | INFO | Provenance / Explainer | Milo Vance | Closed | 2026-09-17 | `gen-chronyd-one-shot-check` modelled the chrony directive as `-Q`'s value. The pinned capture settles it: chronyd(8) SYNOPSIS is `chronyd [OPTION]... [DIRECTIVE]...` (content-src/raw/rhel8/chronyd.man.txt#L7, identical on RHEL 10) and `-Q` takes no argument (#L68) — directives are OPERANDS accepted after the options, so the emitted command `chronyd -Q 'server time.mil iburst'` is correct and stays. Citation repointed from `man 8 chronyd` to the `-Q` line in the capture, and the operand grammar recorded in the entry's `notes`, which the renderer surfaces to the operator. |

---

## Compliance Gaps (NIST 800-53)

**TODO:** Noor to identify any control implementations delayed until post-v1.0.0.

| Control | Status | Plan | Target Date |
|---|---|---|---|
| AC-2 (Account Management) | Deferred | N/A (offline tool, no user accounts) | N/A |
| TODO | TODO | TODO | TODO |

---

## Remediation Schedule

**Phase 1 (Pre-Pilot):**
- TODO: Resolve critical findings before first enclave test
- Target: 2026-09-30

**Phase 2 (Post-Pilot):**
- TODO: Address medium findings from pilot feedback
- Target: 2026-10-31

**Phase 3 (Pre-Release):**
- TODO: All findings resolved before v1.0.0 ship
- Target: TBD (depends on pilot success)

---

## Metrics

**TODO:** Track and report weekly to security review board.

- Total findings opened: N/A (skeleton)
- Total findings remediated: N/A (skeleton)
- Average remediation time: N/A (skeleton)
- Critical findings aging > 30 days: None

---

**Contact:** Noor Patel, Alex Okafor (via Dani Mercer, XO)
