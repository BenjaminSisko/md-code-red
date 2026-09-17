# Test Plan & QA Charter

MD CODE RED uses a two-tier QA model: **automated gates** during build (Air-gap, Syntax, Features) and **content validation** before release.

## QA Ownership

**Build Quality Protocol (BQP):** Al Kowalski (Chief Architect). See issm-company-playbook Section 10.2.

**Manual QA & Content Validation:** Riley Park (QA Engineer). Owns the formal test plan and charter.

---

## Formal Test Plan

**Location:** `/Users/benny/Documents/SALM LLC/07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md`

The test plan covers:
- Feature matrix (which tool/RHEL version pairs are tested)
- Regression suite (commands that must work across releases)
- Pilot enclave validation protocol
- Known limitations and acceptance criteria

**TODO:** Link to test plan once Riley completes it.

---

## Content Validation Protocol

Every command entry in the toolkit must pass this validation before release.

### Pre-Release Content Checklist

- [ ] **Syntax verified:** Command tested on actual RHEL version (7/8/9/10) in test lab
- [ ] **Flags accurate:** All flags match vendor documentation or `man` output for that RHEL version
- [ ] **STIG mapping correct:** STIG ID exists; control numbers match NIST 800-53 rev 5; expected output matches real system behavior
- [ ] **Source cited:** Entry includes URL/doc title, date verified, SME name
- [ ] **Air-gap clean:** No URLs in command output, no fetch calls, no external references
- [ ] **Explainer plain-English:** Every flag has a one-sentence plain-English explanation a junior admin can understand

### Dangerous Operations

Commands tagged as destructive (rm -rf, wipefs, lvremove, dnf remove) must include:
- Red confirmation banner in UI
- Explicit warning in explanation
- Recovery command if applicable
- STIG justification if compliance-required

### Spot-Check Sampling

**TODO:** Define sampling rate. Minimum: 3-5 entries per tool per RHEL version during each release.

**TODO:** Assign spot-check lead (SME or ISSO).

---

## Pilot Validation (Phase 1)

Three senior admins + one ISSO in one enclave, 4 weeks. Success criteria:

- Zero incorrect or non-working commands reported
- Average time-to-command < 30 seconds per search
- Pilot users adopt toolkit for 3+ daily tasks
- ISSO confirms STIG evidence quality meets body-of-evidence standard
