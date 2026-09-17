# Changelog

All notable changes to MD CODE RED are documented here. This project adheres to [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added — content schema module and the real XCCDF pipeline (2026-09-17, CR-T-06/07)
- `extract/schema.py`: the ADR-001 §5 content schema as one pure, importable module — provenance,
  the four mandatory RHEL keys and the three legal version-value shapes, `same_as` chains and cycles,
  `stig[]` referential integrity, `blast` enum, the `{by, on, host}` `verified` receipt, flag shape,
  generated-dataset `_meta`, the tools availability matrix, and the filtered CCI map. `build.py` and
  `tests/test_schema.py` both import it, so the build and the tests cannot enforce different rules.
- `tests/test_schema.py`: 11 tests, stdlib only, no third-party dependency. The shipping `content/`
  is validated first as the control, then 2 valid and 30 invalid bundles under
  `tests/fixtures/schema/`, each declaring the error it expects so a fixture cannot pass by failing
  for the wrong reason.
- `extract/parse_xccdf.py`: the full RULES pipeline. Verifies `stig-src/SHA256SUMS` before reading a
  byte, cross-checks each benchmark's in-XML version against its pinned filename, and emits every
  rule of all four releases — **1,492 total: RHEL 7 V3R15 244, RHEL 8 V2R8 369, RHEL 9 V2R9 445,
  RHEL 10 V1R2 434** — with STIG ID, `SV-…_rule` id, CAT, title, all `ident` CCIs, the mapped NIST
  SP 800-53 controls, and verbatim uncapped check and fix text. `_meta` carries benchmark id,
  release-info version and date, source SHA-256, CAT counts, `partial: false`, and `extracted_on`.
- `build_cci_map` step in the same script rewrites `content/cci_nist.json` from `U_CCI_List.xml`,
  filtered to the 200 CCIs the four benchmarks cite and recording the full list's 5,137 items.
- Determinism: nothing in the extractor reads a clock, so a re-run is byte-identical and two builds
  of the same sources produce the same artifact SHA-256 on any day.

### Changed (2026-09-17, CR-T-06/07)
- `source.version` is mandatory provenance. A source that cannot say which version of the document it
  came from cannot be re-checked.
- A flag's `explain: null` is legal only while `content/flags_rhel*.json` are empty. Once a dictionary
  is curated, a null explain is a schema error rather than a shipped blank.
- Q8 requires exact per-release parity with a live re-parse; `_meta.partial` is now a failure, because
  no extractor in the repo produces a partial dataset any more.
- Q9 reports CAT I check-and-fix completeness per release and fails a release that reports zero CAT I
  rules (which would mean the severity parse dropped them and the gate had nothing to check).
- Q10 compares the full check and fix text, not only a 100-character prefix, and fails if the fixed
  stride cannot yield the 20 samples ADR-001 §7.3 requires.
- Q11 also fails on a CCI map carrying mappings no embedded rule cites — the map is filtered by design.
- Q15 re-runs every extractor and additionally verifies that each generated dataset declares a
  generator this gate actually executes, so a file cannot name an extractor nobody runs and then drift.
- CI runs `python3 -m unittest discover -s tests` instead of one test file by name.

### Removed (2026-09-17, CR-T-07)
- `extract/make_skeleton_content.py`. Its RULES and CCI half is replaced by `extract/parse_xccdf.py`;
  the genuinely sourceless half — empty flag dictionaries and the empty capture index — moved to
  `extract/make_pending_skeletons.py`.

### Added — v1.0.0-dev engine skeleton (2026-09-17, CR-T-02..05)
- `build.py`: MD CODE RED identity constants, 14-file `CONTENT` map, `validate()` (four mandatory RHEL
  keys, `stig_id` referential integrity, provenance, capture-backed `verified`), `same_as` resolution
  with cycle detection, STIG reverse links, search-index seed, `dist/md-code-red_<version>.html` + `.sha256`.
- `qa.py`: gates Q1-Q17 with a PASS/FAIL line each, the pinned-XCCDF accuracy re-check and CCI
  re-check (`--accuracy`), generated-file integrity, mechanical `innerHTML` audit, and a size
  **report** (`--size`) that can never fail a build.
- `template.html`: five-region shell skeleton (RAIL/SIDEBAR/EDITOR/INSPECTOR/STATUSBAR + PALETTE),
  CSP meta tag, dark/light theme tokens, ES5 IIFE with escaping helpers, guarded storage, theme
  module, data-island loader, and status-bar renderer.
- Skeleton content: 3 STIG-sourced command entries, 3 tools, destructive-pattern table, and generated
  rules/CCI/flags datasets from the pinned DISA sources.
- `tests/test_build_fails_on_broken.py` and six deliberately broken fixtures.
- CI: seven steps — build, QA, accuracy re-check, gitleaks, size report, reproducible-build drift
  check, artifact upload with sha256.

### Planned
- Command Builder engine (P0)
- STIG/NIST tagging and Export as Evidence (P0)
- Git Command Generator (P1)
- Ansible Playbook, Inventory, Config generators (P1)
- Config file generators: sshd_config, chrony.conf, rsyslog.conf, sudoers, systemd units (P2)
- Scenario mode: "Harden a new RHEL 9 host" (P2)
- Bulk evidence export for full STIG checklist (P2)

## v1.0.0 — TBD

### Added
- **Command Builder:** Core toolset (systemctl, firewall-cmd, nmcli, dnf/yum, semanage, useradd, chage, lvm, ssh/sshd, journalctl, auditctl, rsyslog, chronyd, podman) across RHEL 7–10
- **Flag-by-flag explanations** for every generated command
- **STIG/NIST tagging:** CAT I checks with control mappings and expected compliant output
- **Export as Evidence:** SCTM-ready format (command + control + result)
- **Version awareness:** Flags hidden/greyed per RHEL version with "changed in RHEL X" notes
- **Full-text search** across tools, flags, STIG IDs, control numbers
- **Single HTML file:** Zero external dependencies, air-gap clean
- **Source citation:** Every entry cites Red Hat docs, man pages, STIG version/date
- **Dark/light mode** toggle
- **Print-optimized stylesheet**
- **Keyboard operation** for locked-down boxes
- **Favorites & recent** (browser localStorage only)

### Known Issues
- TODO: Backlog items from pilot feedback (add as they surface)

---

## Release Policy

Versioning follows semantic versioning: `MAJOR.MINOR.PATCH`.

- **PATCH:** Bug fixes, source citation updates, single-tool additions
- **MINOR:** New tool or generator, new journey, UI improvements
- **MAJOR:** Architectural change, RHEL version drop, product pivot

Content updates tied to **DISA STIG release cycles** (quarterly).
