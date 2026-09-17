# MD CODE RED — RHEL Admin Toolkit

A single-file, offline HTML toolkit for Red Hat Enterprise Linux 7–10 system administrators, DevOps engineers, and ISSOs on air-gapped networks. Generate exact, version-correct Linux commands, Ansible playbooks, and STIG compliance evidence without leaving the enclave.

**Who it's for:** Senior and junior sysadmins, automation engineers, and compliance officers across isolated enclaves.

**Air-gap guarantee:** Zero network requests, no CDN, no fetch calls. Works from `file://` in Firefox/Chromium on RHEL and Windows jump boxes.

**How to use:** Double-click `md-code-red.html` or open it in your browser from a desktop shortcut or USB share.

## Version & Release Info

**Current version:** v0.1.0-sketch (Blueprint stage)  
**STIG release date:** N/A  
**Last built:** 2026-09-17

## Recent changes

- **2026-09-17** — Repository created (Stage 03 Blueprint closed, scope signed by the Founder). Engine forked from
  Grey Beard Ansible v1.0.1 (`build.py`, `qa.py`, `template.html`, `extract/`, `content/`) — unmodified in this commit;
  the rename and the ADR-001 content model land in the first Build tasks. Etsy RHEL STIG pipeline copied as reference
  (`extract/parse_xccdf_reference.py`, `tests/qa_rhel_stig_reference.py`, `content-src/cci-map-reference.json`).
  STIG sources pinned in `stig-src/` (RHEL 7 V3R15, 8 V2R8, 9 V2R9, 10 V1R2, CCI 2025-01-23) with SHA-256.
  Companion doc skeleton in `docs/`. CI: build → QA gate → pin check → size report → artifact; gitleaks.

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md) — Core workflows and UI reference
- [CHANGELOG.md](CHANGELOG.md) — Version history and feature timeline
- [IDEAS.md](IDEAS.md) — Feature backlog and decision log
- [WORKFLOW.md](WORKFLOW.md) — Content pipeline and refresh cycles
- [TEST_PLAN.md](TEST_PLAN.md) — QA charter and validation protocols
- [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) — System design and data models
- [CODE_STANDARDS.md](CODE_STANDARDS.md) — Engineering patterns and security rules
- [SSP.md](SSP.md) — Security compliance and controls (NIST 800-53)
- [POAM.md](POAM.md) — Open findings and remediation plans

**Status:** In Design. Security Review pending.

**Contact:** Zee (Engineering) | Jordan Patel (PM) | Sam Kim (Technical Writer)
