# MD CODE RED — RHEL Admin Toolkit

A single-file, offline HTML toolkit for Red Hat Enterprise Linux 7–10 system administrators, DevOps engineers, and ISSOs on air-gapped networks. Generate exact, version-correct Linux commands, Ansible playbooks, and STIG compliance evidence without leaving the enclave.

**Who it's for:** Senior and junior sysadmins, automation engineers, and compliance officers across isolated enclaves.

**Air-gap guarantee:** Zero network requests, no CDN, no fetch calls. Works from `file://` in Firefox/Chromium on RHEL and Windows jump boxes.

**How to use:** Double-click `md-code-red.html` or open it in your browser from a desktop shortcut or USB share.

## Version & Release Info

**Current version:** v1.0.0-dev (Build stage — runtime shell + command assembler + 24 guided-form generators (CR-T-17..25) + full STIG datasets, 1,492 rules)  
**Pinned STIG releases:** RHEL 7 V3R15 (sunset) · RHEL 8 V2R8 · RHEL 9 V2R9 · RHEL 10 V1R2 · CCI List 2025-01-23  
**Last built:** 2026-09-17

## Recent changes

- **2026-09-17** — D4 review fixes MCR-SEC-015..023, conditions E1–E7, branch
  `salm/milo/generators` (Milo Vance). Marcus Reed's D4 review of the generator tranche returned
  **DENY** on one HIGH that blocks on its own, plus six conditions and two advisories. All are closed
  on this branch. **MCR-SEC-015 (HIGH, E1)** — the assembler joined every flag to its value with `=`
  unless the token said `eq:false`, and `eq:false` was used nowhere in the 24 shipped specs, so 20
  short-option tokens across 11 of 24 generators emitted `-X=value`, which getopt(3) does not accept:
  it hands the `=` to the tool as the first character of the argument. `chage -M=60` sets max-days to
  `"=60"`; `useradd -c=RFC-1234 -s=/bin/bash` silently sets a wrong GECOS and an invalid login shell;
  `auditctl -w=/etc/motd` watches nothing while looking, to the operator recording the STIG control,
  like it worked. Fixed at the assembler rather than per token: a new `flagJoin()` derives the join
  from the flag's own shape — `--long` takes `=`, `-X` takes a space — so all 20 are correct with **no
  content edit** and the defect is unwritable rather than merely absent. Two escape hatches survive,
  each legal only on the shape it belongs to (`eq:false` on a long option, `join:"glued"` on a short
  one), and `extract/schema.py` refuses the disagreement at build time while the assembler returns
  null at run time. **MCR-SEC-022 (E7) and MCR-SEC-018 (E3)** — the D1 positional rule had an
  unchecked off-switch: a `flag` key beside `lit` told it to look away, so `{lit:"0644",flag:"-P",
  requires:"m"}` was accepted and reopened MCR-SEC-013 through the key meant to close it. Replaced
  with the **derived** discriminator Marcus recommended — a `lit` matching `FLAG_TOKEN_RE` is an
  option and never occupies an argument slot — in both halves; a token carrying both `lit` and `flag`
  is now refused outright, including when they agree, and the two shipped exemplars of the shape lose
  their `flag` key (both keep `requires`). That also closes MCR-SEC-018's over-refusal without the
  dangerous workaround it invited — deleting `requires` would have made every SELinux boolean change
  persistent when the operator asked for runtime-only. **MCR-SEC-023** — the lit branch pushed the
  word and returned, so `sshd -T`, `setsebool -P`, `lvextend -r` and `journalctl --no-pager --boot`
  appeared in the command and were absent from the flag-by-flag panel; option-shaped literals now
  reach the inspector, rendering *"unverified — see man page"* where no explanation is curated.
  **MCR-SEC-016 (E4)** — `lvm_size` and `group_list` field types; four fields retyped off `comment`,
  the one free-text type, so `lvextend -L 'ticket RFC-1234'` no longer assembles. The LVM placeholder
  now distinguishes `10G` (set to) from `+10G` (grow by), which nothing in the UI did. **MCR-SEC-019 /
  MCR-SEC-020 (E5)** — `gen-fw-allow-service`'s citation repointed from `#L310` (`--add-service`, an
  option it does not emit) to `#L538`, and a new **gate Q19** measures the flag dictionary against the
  raw captures for all 44 tool/release pairs and checks that every generator citation shows the option
  that generator actually emits. The dictionary gap is accepted with a date and a ticket in
  `docs/POAM.md` and `content-src/flag_coverage_baseline.json`; what was missing was not the coverage
  but anything able to see the gap, since Q15 re-runs the extractor and diffs its output against
  itself. **MCR-SEC-021 (E6)** — the harness was a containment oracle only: it never asserted the
  benign command is a valid invocation of its tool, which is how 20 malformed joins passed 76,225
  checks. It gains a hand-authored **golden-command table** (`tests/fixtures/golden-commands.json`,
  one row per generator per release, never generated from the assembler), a getopt(3) syntax oracle,
  and an enum-branch sweep — `benignFor()` no longer pins every enum to `opts[0]`, and every
  destructive branch must come out at least yellow while a green generator must still have a green
  branch. The E1 and E7 fixes were committed **fail-first**: `77a688f` (44 harness failures) before
  `5315fef`, and `1389487` (78 harness + 5 unit failures) before `dee9005`. E2 was already met at
  `996b504`. Also new: `tests/test_positional_crosscheck.py`, which re-runs Marcus's exhaustive shift
  sweep extended with option-shaped literals — 3,258 schema-accepted shapes, 104,256 runs, 0 shift
  violations, and shown failing against the pre-fix tree. Gates: `build.py` reproducible / `qa.py`
  Q1–Q19 PASS / `unittest` 57 OK (was 51) / harness 81,577 checks 0 FAILED (was 76,225).

- **2026-09-17** — Guided-form generators CR-T-17..25, branch `salm/milo/generators` (Milo Vance).
  24 generator specs across the 9 tool areas Zee assigned this tranche: firewall-cmd (default zone,
  open-port and allow-service rich rules), nmcli (static IPv4), journalctl, lvcreate/lvextend, sshd
  (`-T -f`), useradd/usermod, systemctl (query and manage, split so a read action and a state-changing
  action never share one blast level), dnf and yum (RHEL 7 is yum-only — `dnf`'s tools.json entry is
  `unavailable` on RHEL 7 with `alternative: "yum"`, never a fabricated `dnf` command), setsebool and
  semanage port, chage (list and set-aging, man-page-sourced per ADR §2.4), auditctl/ausearch, rsyslogd
  (`-N1` config test), and chronyd (`-Q` one-shot check, with the RHEL 7 chronyd-default/legacy-ntpd
  note carried in the entry's `notes` field). Every generator is a `commands.json` entry shaped
  `{fields[], template[]}` — no second registry to keep in sync — consumed by a new `GENERATORS`
  registry, form renderer and `decodeCmd()` added to `template.html` on top of the existing assembler
  (`assembleCommand`/`shQuote`/`composeRichRule`/`isPositionalToken`/`blastFor` were not touched).
  16 new tools.json entries record, per RHEL version, whether a tool's flags are host-verified
  (Defiant RHEL 8.10 / Saratoga RHEL 10.2, CR-T-09/10) or documented from the corpus (RHEL 7 System
  Administrator's Guide / RHEL 9 guides, cited by manifest `source_url` + `sha256`) — RHEL 7/9 carry no
  fabricated flags. Two firewall-cmd generators (`--add-rich-rule`, `--permanent`) cite the raw RHEL
  8/10 man-page capture directly (`content-src/raw/rhel{8,10}/firewall-cmd.man.txt`) rather than
  `flags_rhel{8,10}.json`: those two real, host-captured flags are absent from the generated dictionary
  because `extract_flags.py`'s synopsis-line regex only captures the `[--permanent]` prefix token
  repeated ahead of firewalld's ~90 per-option lines and misses the option that follows it on the same
  line — a real extractor gap, flagged for a follow-on fix, not worked around by inventing a flag.
  `tests/hostile_harness.js` gained a content-spec sweep that loads `content/commands.json` directly
  and fuzzes every field of every one of the 24 real generator entries with the full hostile-vector set
  in its own template (12,689 checks), on top of the existing per-field-type sweep — 76,225 checks
  total, 0 failed. `qa.py` Q12 and `tests/test_schema.py` learned that a generator spec (`"template" in
  e`) keeps the four-version promise via `spec.versions`/`field.versions` rather than a `rhel_versions`
  object, closing a gap where the first real generator spec would have failed a gate that predates
  CR-T-17. Verified rendering, live command assembly (including rich-rule composition), version-gating
  (podman/dnf disabled-with-reason on RHEL 7, values persisting across a version switch) and dangerous-
  pattern blast escalation (`yum remove` → yellow) in a real browser against `dist/` over a local HTTP
  server. Gates: `build.py` / `qa.py` (Q1-Q18 PASS) / `python3 -m unittest discover -s tests` (51 OK) /
  `node tests/hostile_harness.js` (0 FAILED) all green before and after.

- **2026-09-17** — Re-review conditions D1 and D2: MCR-SEC-013 and MCR-SEC-014, branch
  `salm/milo/sec-013-014` (Milo Vance). Marcus Reed's re-review of the fix tranche returned
  **APPROVE WITH CONDITIONS** — no CRITICAL, no HIGH — with two new findings held as conditions.
  **MCR-SEC-013 (LOW)** — the never-half-formed rule reasoned about argument slots with
  `isPositionalToken()`, which asked `tok.field && !tok.flag`, so a *literal* was never positional.
  A literal made conditional with `requires` could therefore vanish while a later positional stayed:
  `[{lit:"chmod"},{lit:"0644",requires:"mode"},{field:"p"}]` with `mode` absent assembled to
  `chmod '/etc/foo'`, the path sitting in the mode slot — MCR-SEC-002 again, through the one path
  its rule did not cover. A conditional literal is now positional in both halves: it may only drop
  if every later positional drops with it (run time), and `spec_errors()` refuses the construct at
  build time. The shape MCR-SEC-002 shipped — literal and value gated on the *same* field, dropping
  together — stays legal and now has a valid fixture holding it there. **MCR-SEC-014 (INFO)** —
  `el("x")["inner"+"HTML"] = raw` evaded the Q17 sink inventory, because every rule was written
  against the dotted spelling and the spliced name never appears in the source. **Closed rather than
  recorded:** Q17 now refuses a computed member assignment whose property expression it cannot read,
  refuses a bracketed sink name, and refuses a sink name fused out of string literals — inline, via a
  variable, or across two statements. It costs the product nothing: the two computed assignments
  `template.html` actually contains (`out[fields[i].name]`, `out.resolved[f.name]`) pass untouched,
  and a safe control fixture proves it. What the rule cannot see — a property name built at run time
  from data rather than from literals — is printed by the gate itself rather than claimed away.
  Four new bypass fixtures, one safe control, one invalid and one valid schema fixture, and 16 more
  never-half-formed harness checks (60 → 76). Gates: `qa.py` Q1–Q18 PASS, 51 unit tests OK, harness
  63,536 checks / 0 failed, byte-identical rebuild.
- **2026-09-17** — Security review fixes MCR-SEC-001..012, branch `salm/milo/shell-assembler`
  (Milo Vance). **Marcus Reed reviewed the assembler tranche and returned DENY with `block_flag`:
  three HIGH, five MEDIUM, two LOW, two INFORMATIONAL. All twelve are addressed on this branch.**
  The three blockers were real defects in code the UI cannot reach yet, which is exactly why they
  had to close now: CR-T-25 and CR-T-33 build fourteen P0 tool categories of templates against this
  contract. **MCR-SEC-001** — a `comment`-typed field wired into a firewalld rich-rule slot could
  close an attribute and inject a whole `accept` clause past the operator's `drop`, with shell
  quoting intact, so the harness rated it safe; rich-rule slots now take closed-grammar types only
  (`comment` and `enum` are deliberately not rich-rule sub-field types, because rich-rule syntax has
  no escape for a quote inside an attribute value), every mapped value is re-checked at composition
  time, and the harness gained a rich-rule parser that compares the composed rule to the operator's
  intent element by element. **MCR-SEC-002** — the never-half-formed rule was enforced per field, so
  an absent optional value made its token vanish and `chown 'apache' '/var/www'` became
  `chown '/var/www'`; dropping a token is now a declared property of the template, positional
  arguments can never shift, and `{lit:"...", requires:"field"}` makes a literal disappear with the
  value it owns. **MCR-SEC-003** — "Copy with comment" built its header from raw content text, so a
  newline in `intent` put an unrendered `rm -rf /var/log/audit` on the clipboard with blast still
  green; every header line is now rendered, escaped, single-line and `# `-prefixed, the schema
  rejects control characters in `intent`/`verify`/`undo`/`stig[]` at build time, `blastFor()` reads
  the whole clipboard payload, and the header is rendered on screen as a read-only preview of
  exactly what gets copied. The MEDIUM findings closed five mechanical bypasses of the Q17 render
  audit (now a sink inventory with source-derived accumulators and a real literal parser, with 13
  negative fixtures), gave the generator/spec shape a build-time schema with flag and lit token
  allow-lists, escaped every `<` and `>` in the data island so `<!--<script` cannot swallow the app,
  and taught the destructive-pattern table to match the de-quoted command so `rm -rf /` fires on
  `rm -rf '/etc/pki'`. The dead `yamlQuote()` was **removed** rather than left looking like proof
  (the quoting-domain gate is shell-only until the Ansible generators land), and render, copy and
  the future exporter now read one rendered-state object. **The harness grew from 15,392 to 63,536
  checks** — every field type substituted into every rich-rule slot, 60 never-half-formed checks, 65
  clipboard-payload checks, 32 flag/lit allow-list checks, and a check that every row of
  `dangerous.json` can actually fire. `qa.py` is green on all 18 gates, `python3 -m unittest
  discover -s tests` runs 51 tests green, two builds of the same sources are byte-identical, and the
  artifact was driven in Chrome with zero console errors.

- **2026-09-17** — CR-T-08/13/14/15/16, branch `salm/milo/shell-assembler` (Milo Vance). **The tool has
  a working shell and, with it, the command assembler — the piece the threat model ranks as this
  product's top risk.** The five UI regions are real: a rail with focus-revealed text labels, the
  version selector persisted through the storage guard, a tool list gated per release with its reason
  and alternative, an editor rendering the assembled command in a monospace block with a line-number
  gutter, an inspector naming every flag the command uses with its curated explanation or the honest
  "unverified — see man page", and the status bar. One delegated `keydown` listener over one binding
  table implements the whole UI-spec keyboard map (documented in `docs/USER_GUIDE.md`), so no control
  is mouse-only. Dark and light resolve in an inline `<head>` style with no flash of the wrong theme.
  **`assembleCommand()` is pure, DOM-free, and fenced by extraction markers so CI runs the shipped
  assembler itself**: 23 allow-list field types, `shQuote()` and `yamlQuote()` as separate escaping
  domains, rich rules composed from validated sub-fields, blast matched on the fully assembled
  post-quoting command, and `null` — never a half-formed command — whenever a required field is
  missing or invalid. **The hostile-input harness runs 15,392 checks** (52 vectors x 23 field types x
  4 releases x 3 argument shapes, plus 5 rich-rule sub-fields) with a required outcome per pair, 276
  positive controls and 2 negative controls, wired into `qa.py` as **Q18** against the built artifact;
  Node is now a required CI dependency because of it. `qa.py --accuracy` gained full ID-set parity
  alongside the 20-per-release sample, plus a committed mutated fixture and a test proving the gate
  fails on it and passes on the clean copy. **Two real defects came out of this work, both found by
  the new gates rather than by review:** the `unit` field type's character class admitted a backslash,
  and `template.html` carried 29 raw control and bidi characters where escapes were intended —
  including a NUL that broke the tool at load time in Chromium while Node's syntax check passed.
  Q17 now scans for that class of character so it cannot come back. `qa.py` is green on all 18 gates,
  `python3 -m unittest discover -s tests` runs 26 tests green, and two builds of the same sources are
  byte-identical.

- **2026-09-17** — CR-T-09/10, branch `salm/milo/flags-extract` (Milo Vance). **The FLAGS dictionaries
  are now real, not empty skeletons — for two of the four RHEL releases.** `extract/extract_flags.py`
  SSHes (read-only, no sudo) to Defiant (RHEL 8.10) and Saratoga (RHEL 10.2), pulls `man -P cat` /
  `--help` / `rpm -qf` for the 22 P0 tools, saves the raw text under `content-src/raw/rhel<N>/`
  (git-ignored — the paraphrase-only source of record), and parses each tool's OPTIONS-style
  definition list into `content/flags_rhel<N>.json`: flag names, whether each takes an argument, and
  `explain: null` — man-page text is GPL-2.0-or-later, paraphrase-only, and this extractor never writes
  prose; curation is a separate, later, human step (Caleb, RHEL SME) that a re-run never clobbers.
  Anything option-shaped the parser can't confidently resolve is left as raw text under `unparsed[]`
  rather than guessed. **Defiant: 22/22 tools, 952 flags parsed, 1 unparsed. Saratoga: 22/22 tools,
  1,019 flags parsed, 3 unparsed.** `--check` mode re-parses the committed raw dumps offline (no SSH)
  so `qa.py` Q15 can prove reproducibility without depending on the lab hosts being reachable in CI.
  RHEL 9 (CR-T-11) stays blocked on VM provisioning; RHEL 7 (CR-T-12) stays gated on the UBI7 path.
  **Known conflict, not worked around:** the concurrent CR-T-06 schema module makes a command entry's
  `flags[].explain: null` an error once any FLAGS dictionary is non-empty, and `content/commands.json`
  currently has 4 such flags — so `build.py`/`qa.py`/the unit tests do not go green end to end on this
  branch until that's resolved (content curation, a schema scoping fix, or a sequencing call — none of
  them this branch's file, see `docs/CHANGELOG.md`).

- **2026-09-17** — CR-T-06/07, branch `salm/milo/xccdf-pipeline` (Milo Vance). **The RULES datasets are now
  the whole benchmark, not a sample.** `extract/parse_xccdf.py` replaces the CR-T-02 stand-in and parses all
  four pinned DISA XCCDFs after verifying `stig-src/SHA256SUMS`: **1,492 rules — RHEL 7 244, RHEL 8 369,
  RHEL 9 445, RHEL 10 434**, each with its STIG ID, `SV-…_rule` id, CAT, title, *every* CCI from its `ident`
  elements (RHEL 9 has rules citing 26), the NIST SP 800-53 controls those CCIs map to, and verbatim
  uncapped check and fix text. `_meta` carries the benchmark id, the release-info version and date, the
  source file's SHA-256, CAT counts, and `partial: false`. The same script rewrites `content/cci_nist.json`
  from `U_CCI_List.xml`, filtered to the **200 CCIs the four benchmarks actually cite** out of the list's
  5,137. Extraction is a pure function of the pins — no wall clock anywhere in it — so a re-run is
  byte-identical and the artifact rebuilds to the same SHA-256 on any day. Artifact: **1.87 MB**
  (1,961,080 bytes), of which 1.86 MB is the data island.
  `extract/make_skeleton_content.py` is gone; what genuinely has no source yet — the flag dictionaries and
  the capture index — moved to `extract/make_pending_skeletons.py`, whose name now says what it is.
  `extract/schema.py` (CR-T-06) is the single statement of the ADR-001 §5 content schema, imported by both
  `build.py` and `tests/test_schema.py` so the build and the tests can no longer enforce different rules;
  `source.version` is now mandatory provenance, and a flag's `explain: null` is legal only while the flag
  dictionaries are still empty. `tests/test_schema.py` pins all of it with 2 valid and 30 invalid content
  bundles, each naming the error it expects, so a fixture cannot pass by failing for the wrong reason.
  QA: Q8 now demands exact per-release parity with a live re-parse (a partial dataset no longer has a
  generator that can honestly produce one), Q9 reports CAT I check-and-fix completeness per release,
  Q10 compares full check and fix text rather than a prefix, Q11 also fails on a CCI map carrying
  mappings nothing cites, and Q15 re-runs **every** extractor and cross-checks that each generated file
  declares one this gate actually executes. All 18 gates green; `python3 -m unittest discover -s tests`
  green (11 tests, stdlib only) and now runs in CI.

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
