# MD CODE RED — RHEL Admin Toolkit

A single-file, offline HTML toolkit for Red Hat Enterprise Linux 7–10 system administrators, DevOps engineers, and ISSOs on air-gapped networks. Generate exact, version-correct Linux commands, Ansible playbooks, and STIG compliance evidence without leaving the enclave.

**Who it's for:** Senior and junior sysadmins, automation engineers, and compliance officers across isolated enclaves.

**Air-gap guarantee:** Zero network requests, no CDN, no fetch calls. Works from `file://` in Firefox/Chromium on RHEL and Windows jump boxes.

**How to use:** Double-click `md-code-red.html` or open it in your browser from a desktop shortcut or USB share.

## Version & Release Info

**Current version:** v1.0.0-dev (Build stage, engine skeleton)  
**Pinned STIG releases:** RHEL 7 V3R15 (sunset) · RHEL 8 V2R8 · RHEL 9 V2R9 · RHEL 10 V1R2 · CCI List 2025-01-23  
**Last built:** 2026-09-17

## Recent changes

- **2026-09-17** — CR-T-02..05, branch `salm/milo/engine-fork` (Milo Vance). Engine forked to MD CODE RED:
  `build.py` renamed and rebuilt around ADR-001's content model — a 14-file `CONTENT` map, `same_as`
  resolution with cycle detection, STIG reverse links, a search-index seed, and a `validate()` that
  fails loud on a missing RHEL key, a dangling `stig_id`, missing provenance, or a `verified` claim with
  no capture receipt; output is `dist/md-code-red_<version>.html` plus a `.sha256` sidecar.
  `qa.py` merged with the Etsy STIG pipeline's accuracy re-check: 17 gates (Q1–Q17) plus an optional
  `node --check`, one PASS/FAIL line each, the pinned XCCDF re-parsed and diffed against the embedded
  rules after verifying `stig-src/SHA256SUMS`, a mechanical `innerHTML` audit with a documented
  allow-list, and **size reported in MB, never enforced** (Founder ruling, ceiling unlimited).
  `template.html` replaced with the five-region shell skeleton + palette overlay: CSP meta tag, dark and
  light token sets from UI spec v1 §6, ARIA landmarks, exactly two `<script>` elements (JSON data island
  + one ES5 IIFE with `esc()`/`escapeAttr()`/`escapeRegex()`, a schema-versioned guarded storage module,
  the theme module, the island loader, and the status-bar renderer). Skeleton content: 3 STIG-sourced
  command entries across all four RHEL versions, 3 tools, the destructive-pattern table, and generated
  `rules_rhel{7,8,9,10}.json` / `cci_nist.json` / empty `flags_rhel*.json` from the pinned sources.
  `tests/fixtures/broken-content/` + `tests/test_build_fails_on_broken.py` prove the build fails on six
  deliberate defects. CI replaced with the seven-step gate (build, QA, accuracy re-check, gitleaks,
  size report, reproducible-build drift check, artifact upload with sha256) on Python 3.12, no Node.
  Open item for Devon/Al: `dist/` is git-ignored on working branches because a committed artifact
  embeds its own build date and cannot stay byte-identical to a rebuild across days (ADR-001 §9).

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
