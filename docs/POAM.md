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
