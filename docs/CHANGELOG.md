# Changelog

All notable changes to MD CODE RED are documented here. This project adheres to [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added — runtime shell, keyboard controller and the command assembler (2026-09-17, CR-T-08/13/14/15/16)

**The security-critical tranche.** The command assembler is the surface the threat model ranks as the
product's top risk: a string this code builds is executed by a trusted human as root on a production
host, with no sandbox, no approval step and no rollback behind it.

- **`assembleCommand(specOrEntry, version, values)` (CR-T-15)** — pure, DOM-free, data-free, and
  fenced between `MCR-ASSEMBLER-BEGIN` / `MCR-ASSEMBLER-END` markers so it can be lifted out of the
  *shipped artifact* and executed under Node by the test harness. `null` is the only answer for an
  incomplete or invalid input: there is no second return shape carrying a half-built string
  (threat-model-v1 §3.4). A companion `validateSpec()` tells the UI *which* field is wrong without the
  assembler ever handing out a partial command to explain itself with.
- **A per-field TYPE system with 23 allow-list validators** — hostname, ipv4, ipv6, ipaddr, cidr,
  port, portrange, protocol, family, action, unit, username, groupname, path, zone, service, package,
  selinux_boolean, audit_key, interface, integer, enum and comment. Full match, length-capped, and
  preceded by universal checks that reject control characters (NUL, newline, carriage return, tab),
  invisible and bidirectional-override characters, non-ASCII look-alikes, and any leading dash
  (argument injection). `comment` is the **only** free-text type, the only one that accepts non-ASCII
  text, and it is still single-quoted before it can reach a shell.
- **`shQuote()` and `yamlQuote()` as separate functions** — POSIX `'\''` for the shell, `''` for YAML,
  and `esc()`/`escapeAttr()` for the DOM: three escaping domains, three functions, never nested.
  `shQuote()` deliberately has **no** "this value looks harmless, leave it bare" branch; quoting is
  uniform, which costs `--zone='public'` in the rendered command and buys a rule with no exceptions
  to audit.
- **firewalld rich rules composed from validated sub-fields** (`composeRichRule()`), never from one
  free-text box — the highest-risk field class in threat-model-v1 §3.1.
- **Blast evaluation against `dangerous.json` matched on the fully assembled, post-quoting command**,
  with a content entry's own `blast: "red"` tripping the banner independently (§3.3). The red banner
  is `role="alert"` and holds Copy until the reviewer checkbox is ticked.
- **Version gating that is structural, not cosmetic** — a field or an enum option that a release does
  not carry is dropped from the template before assembly, so it is *impossible* to include in that
  release's command, and the control renders disabled with "Not available in RHEL N" rather than
  disappearing.

- **Runtime shell (CR-T-13)** — the five regions per UI spec §2 with real content: a rail with
  focus-revealed text labels (no images anywhere), the version selector persisted by id through the
  storage guard, the tool list from `tools.json` gated by per-release availability with its reason and
  alternative, an editor rendering the assembled command in a monospace block with a real line-number
  gutter (`role="button"`, focusable), an inspector listing every flag the command actually uses with
  its curated `explain` or the honest "unverified — see man page", and the status bar. Dark and light
  tokens per UI spec §6 with the theme resolved in an inline `<head>` style, so there is no flash of
  the wrong theme. Empty, gated and error states per UI spec §7 — with no tool selected the toolbar is
  *absent*, not merely disabled, so there is no dead control to tab through. Everything renders through
  `esc()`/`escapeAttr()`; interaction is `data-*` delegation; zero inline handlers.
- **Keyboard controller (CR-T-14)** — one delegated `keydown` listener over one `KEYMAP` table: `/`
  and `Ctrl/Cmd+K` for the palette, `Esc`, `Ctrl+B`/`Ctrl+I` panel toggles, `Ctrl+Shift+L` theme,
  `Ctrl+Shift+C` copy-with-comment, `Ctrl+Alt+1..5` rail jumps, arrow navigation in every list, a
  focus-trapped palette, and a visible focus ring on every control. Documented in
  `docs/USER_GUIDE.md`, which replaces its keyboard TODO with the table the code actually implements.
- **Shell-level command palette** over the build-time index seed, so the keyboard controller has a
  real palette to drive. The lazy typed index over flags, STIG IDs and control numbers is still
  CR-T-29 and is marked as such on screen.

### Added — gates that can be shown to fail (2026-09-17, CR-T-08/16)
- **`qa.py --accuracy` hardening (CR-T-08).** The Q10 comparison moved into a pure
  `accuracy_failures()` that `gate_q10` and the tests both call, and it grew a second layer: the
  20-per-release stride sample still catches drifted text, and a new **full ID-set parity check**
  catches a rule added, dropped or renamed *outside* the sample, which 20-in-445 would otherwise walk
  straight past.
- **A committed mutated fixture.** `tests/fixtures/accuracy/clean_rules_rhel9.json` is the
  deterministic sample of the shipping RHEL 9 dataset, unmodified; `mutated_rules_rhel9.json` is the
  same file with six planted edits, one per field the gate compares (title, rule id, CCI set, CAT,
  fix text past the 100-character prefix window, check text). `tests/test_accuracy_gate.py` proves the
  gate passes on the clean file and names every planted mutation in its failure output on the other —
  the control case first, because a mutated fixture failing proves nothing if the clean one fails too.
- **Hostile-input harness (CR-T-16), Marcus's CI merge-gate #4.**
  `tests/fixtures/hostile-inputs.json` carries **52 vectors across 18 classes** — command
  substitution, statement separators, redirection, grouping, globbing, newline and CR injection,
  option injection, unicode look-alikes, invisible and bidi characters, path traversal, NUL,
  quote-breaking, over-length, empty. `tests/hostile_harness.js` runs every vector against every field
  type on all four releases in three argument shapes, plus five rich-rule sub-fields: **15,392 checks**
  per run. Each pair has a *required* outcome — every closed-grammar type must reject every vector,
  and the one free-text type's expectation is declared per vector — so a validator that stopped
  enforcing its grammar fails the gate even when the shell quoting still holds.
- **The harness does not execute `/bin/sh`.** Proving the quoting by running it would mean executing
  attacker-controlled text in CI on precisely the build where the quoting is broken. It tokenises the
  assembled command under POSIX rules instead and compares its shell-visible shape against the same
  command built from a benign value.
- **Controls in both directions.** 276 positive controls assert every field type's benign value still
  assembles on every release in every shape, so a gate cannot pass by rejecting everything; two
  negative controls assert the checker itself still fails an unquoted `$(whoami)` and an appended
  `; id`.
- **`qa.py` Q18** runs that harness against the **built artifact**, so the code CI clears is the code
  that crosses the air gap, and adds threat-model §11 gate #9: a static check that `shQuote`,
  `yamlQuote` and `esc` are never nested inside one another.
- **Q17 gained a trojan-source scan** — zero raw C0/C1 control, zero-width or bidirectional-override
  characters in the hand-written shell. This is not theoretical: it caught 29 such characters in this
  very branch (below).

### Fixed (2026-09-17, CR-T-15/16)
- **The `unit` field type admitted a backslash.** Its character class was written `[A-Za-z0-9_.@:\\-]`,
  and the escaped backslash put `\` *inside* the class. A backslash is inert once single-quoted, so no
  injection was possible — but it is the one character whose meaning differs between the shell, YAML
  and a systemd unit name, and the allow-list is supposed to be a grammar, not just an injection
  filter. **Found by the hostile-input harness on its first policy-enforcing run**, not by review.
- **29 raw control and invisible characters in `template.html`.** The two regex literals meant to
  *reject* control and bidi characters had been written with real control characters instead of
  escapes — including a NUL and five bidirectional overrides — which broke the regex at load time in
  Chromium (Node's `--check` parsed it happily). Repaired to escapes and now gated by the Q17
  trojan-source scan, which is the control that stops it recurring.

### Changed (2026-09-17, CR-T-16)
- **Node is now REQUIRED in CI** (`actions/setup-node@v4` in `.forgejo/workflows/ci.yml`). The
  assembler is JavaScript and Q18 runs it; a Python re-implementation of the quoting would be a second
  assembler to keep in sync and the shipped one would be the untested one. The older `node --check`
  syntax gate stays optional, because a missing syntax check is an inconvenience and a missing
  injection check is a production RHEL host.
- **Q5 feature markers** now cover the shell, the keyboard controller and every assembler module, and
  the assembler / keyboard markers moved from PENDING to required. The generator registry, flag
  decoder, STIG panel, evidence exporter and lazy typed index stay PENDING against their own tasks.

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

### Added — real FLAGS dictionaries from Defiant and Saratoga (2026-09-17, CR-T-09/10, Milo Vance)
- `extract/extract_flags.py`: SSH (read-only, no sudo) to a RHEL host, run `man -w`/`man -P cat`/
  `<tool> --help`/`rpm -qf --qf '%{NVRA}'`/`cat /etc/redhat-release`/`uname -r` for the 22 P0 tools
  (systemctl, firewall-cmd, nmcli, dnf, yum, semanage, setsebool, useradd, usermod, chage, pvcreate,
  vgcreate, lvcreate, lvextend, sshd + sshd_config(5), journalctl, auditctl, ausearch, rsyslogd +
  rsyslog.conf(5), chronyd + chrony.conf(5) + chronyc, podman, git), save the raw output under
  `content-src/raw/rhel<N>/` (git-ignored — the paraphrase-only source of record for Q14's collision
  check and for licensing review), and parse the OPTIONS-style definition list in each page into
  `content/flags_rhel<N>.json`: `names[]`, `takes_arg`, `explain: null` per flag, `package` (NVRA) and
  `pages[]` (man section, source, `raw_ref`) per tool. The parser never writes prose — man pages are
  GPL-2.0-or-later, paraphrase-only per `content-licensing-ruling-v1.md` — and anything option-shaped
  it cannot confidently resolve into a name/arg boundary is recorded under a tool's `unparsed[]` rather
  than guessed. Re-running is non-destructive: a curated `explain` survives, and a flag no longer seen
  is marked `removed_in` rather than silently dropped.
- `--check` mode (no SSH): re-parses the committed raw dumps under `content-src/raw/rhel<N>/` and
  diffs the result against `content/flags_rhel<N>.json`, so reproducibility can be proven offline and
  in CI without a live dependency on lab hosts.
- Ran against **Defiant (RHEL 8.10)**: 22/22 tools present, package NVRA recorded for each,
  **952 flags parsed, 1 unparsed**. Ran against **Saratoga (RHEL 10.2)**: 22/22 tools present,
  **1,019 flags parsed, 3 unparsed**. `content-src/raw/rhel{8,10}/` hold 27 raw man/help dumps each.
- `qa.py` Q15: `extract/make_pending_skeletons.py` still owns the placeholder empty
  `flags_rhel{7,9}.json` (RHEL 9/7 extraction is CR-T-11/12, still blocked/at-risk), but no longer
  gates `flags_rhel8.json`/`flags_rhel10.json` — those are real data now, so a diff against the empty
  placeholder would always show expected drift. Q15 instead runs `extract_flags.py --check` for RHEL
  8 and 10 directly against the committed raw dumps. Documented inline in `gate_q15`.

### Known conflict — content/commands.json vs. the new explain:null schema rule (CR-T-06 × CR-T-09/10)
- `extract/schema.py`'s `flags_errors()` (added this same day by the concurrent `salm/milo/xccdf-pipeline`
  branch) makes a command entry's `flags[].explain: null` a schema error once *any* `flags_rhel*.json`
  is non-empty — and CR-T-09/10 just made two of them non-empty. `content/commands.json` currently has
  4 such flags across 3 skeleton entries (`firewalld-service-active`: `status`, `is-active`;
  `ctrl-alt-del-target-masked`: `status`; `journald-service-active`: `is-active`), so as of this branch
  **`python3 build.py` FATALs with 4 schema errors** and `tests/test_schema.py`'s
  `test_flag_explain_nulls_are_still_honest` / `test_content_dir_validates` and
  `tests/test_build_fails_on_broken.py`'s `test_00_real_content_builds` fail — all three failures trace
  to the same 4 flags, confirmed with `python3 -m unittest discover -s tests`.
  `content/commands.json` (curated content) and `extract/schema.py` (CR-T-06) are both outside this
  branch's file scope (`extract/extract_flags.py`, `content/flags_rhel{8,10}.json`, `content-src/raw/`,
  docs, and this one `qa.py` addition only), so this is reported rather than worked around, per the
  task brief. Needs one of: (a) curate those 4 flags' `explain` (content authoring, CR-T-33 territory),
  or (b) scope the schema rule to the RHEL version(s) a flags dictionary actually covers rather than
  "any dictionary anywhere is non-empty" (an entry whose `rhel_versions` never reaches 8 or 10 has no
  honest way to satisfy a global rule), or (c) a sequencing call from Zee/Al/Devon on CR-T-09/10 landing
  ahead of CR-T-33. Until resolved, `salm/milo/flags-extract` cannot get a green `build.py`/`qa.py`
  end to end on top of current `main`, though every gate this branch's own files are responsible for
  (Q15's flags check, the extractor's own idempotency) is verified green in isolation — see README.

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
