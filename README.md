# MD CODE RED — RHEL Admin Toolkit

A single-file, offline HTML toolkit for Red Hat Enterprise Linux 7–10 system administrators, DevOps engineers, and ISSOs on air-gapped networks. Generate exact, version-correct Linux commands, Ansible playbooks, and STIG compliance evidence without leaving the enclave.

**Who it's for:** Senior and junior sysadmins, automation engineers, and compliance officers across isolated enclaves.

**Air-gap guarantee:** Zero network requests, no CDN, no fetch calls. Works from `file://` in Firefox/Chromium on RHEL and Windows jump boxes.

**How to use:** Double-click `md-code-red.html` or open it in your browser from a desktop shortcut or USB share.

## Version & Release Info

**Current version:** v1.0.0-alpha.6 (release candidate, lab-only, unsigned)
**Pinned STIG releases:** RHEL 7 V3R15 (sunset) · RHEL 8 V2R8 · RHEL 9 V2R9 · RHEL 10 V1R2 · CCI List 2025-01-23  
**Last built:** 2026-10-01

## Recent changes

- **2026-09-30** -- **Guided storage inspection.** Adds an all-release `lsblk`
  builder with curated capacity, filesystem, parent-topology, and LVM-oriented
  column sets. Every preset keeps `NAME` first to preserve the device tree;
  RHEL 7/8 use the compatible `MOUNTPOINT` column, while RHEL 9/10 also offer
  `MOUNTPOINTS` for devices mounted in more than one place. The catalog now
  contains 200 entries across 102 tools: 58 guided generators and 142 static
  entries.

- **2026-09-30** -- **Task-centered operations-console UX.** Adds Home with
  common RHEL outcomes, working modes, learning starts, favorites, and recent
  work; separates reviewed Build content from the mined Reference Library; and
  presents guided tasks as Configure, Review, and Verify with a persistent
  command/trust area. The responsive shell also adds global search, visible
  navigator and inspector toggles, focus restoration, dialog containment, a
  keyboard skip link, and single-column narrow-screen flow without horizontal
  navigation scrolling. The released alpha.5 artifact remains archived unchanged.

- **2026-09-22** -- **Administrator and instructor feedback release.** Corrects
  firewalld, NetworkManager, package, service, LVM, cron, and configuration
  recovery; audits privilege metadata; and narrows commands whose old intent
  promised more than they performed. Adds complete value-bound operational
  plans and field instruction for every generator, Start Here learning paths,
  RHEL comparison and source guidance, nine troubleshooting trees, formal
  execution receipts, real-host validation tracking, generated release facts,
  and a fail-closed publisher-signing workflow. The browser export is now named
  **Export command and control reference** to state its evidentiary boundary.

- **2026-09-22** -- **Generalized command syntax oracle.** Q26 validates every
  resolved static release command and every hand-authored golden generator
  command, including every simple invocation after a real shell operator,
  against 420 independently loaded RHEL-specific grammar rows for 106 invoked
  binaries. Quoted and escaped operator text remains an operand. Git, DNF and
  systemctl use subcommand-scoped options and operand bounds. The exact golden
  table remains active as an independent generator regression oracle.

- **2026-09-21** -- **Configuration-file generators.** Adds guided builders
  for sshd, chrony, rsyslog, sudoers, systemd service units, and cron. YAML,
  INI, and token-line documents now share the same fail-closed schema/runtime
  contract, and the hostile harness independently parses every generated file.
  The catalog now contains 199 entries across 102 tools: 43 guided generators
  and 156 static entries.

- **2026-09-21** -- **Ansible generator completion.** The playbook builder now
  supports task-selection checkboxes for refreshing DNF metadata and starting
  and enabling a service whose name matches the selected package. The generated
  invocation remains a `--check --diff` dry run. Checkbox values are a closed
  one-option enum, and the YAML structure oracle covers every optional-task
  combination on all four RHEL selections.

- **2026-09-21** -- **Git Command Generator.** Adds a dedicated Git activity
  rail with all existing curated Git guidance plus eight guided forms: clone,
  branch, merge, rebase, annotated tag, bounded log, bisect, and lost-commit
  recovery. Git branch/tag names and revisions use closed validators, every
  generated value remains shell quoted, and all 32 release-specific outputs
  have hand-authored golden-command oracles. The catalog now contains 193
  entries across 102 tools: 37 guided generators and 156 static entries.

- **2026-09-21** -- **RHEL P0 command completion.** Adds guided `pvcreate`
  and `vgcreate` builders from the existing captured RHEL 8/10 manual corpus,
  with all-version golden-command oracles. Both operations are rated red and
  require the existing review acknowledgement because they write LVM metadata
  to a selected block device. The curated catalog now contains 185 entries
  across 102 tools, including 29 guided generators. All 21 non-Git RHEL P0
  administration tools now have guided builders.

- **2026-09-20** -- **v1.0.0-alpha.3 correction candidate.** Closes
  MCR-A2-KEY-001 by binding `Ctrl+Alt+1` through `Ctrl+Alt+6` to all six
  rendered activity rails, including About, and adds an executable
  rail/shortcut/documentation contract. The historical alpha.2 tag and release
  bytes remain immutable; its artifact set is archived byte-for-byte under
  `releases/v1.0.0-alpha.2/` before this candidate is built.

- **2026-09-20** -- **v1.0.0-alpha.2 recovery candidate.** Closes PIPE-003,
  PIPE-004, PIPE-F1, and PF6; retires the time-bounded MCR-SEC-020/Q20 waiver
  with authority and evidence while retaining the coverage regression gate;
  refreshes the mined reference tier to **14,439 distinct commands** across
  command, option, and workflow families; and promotes Q21-Q25 to continuous
  release gates. Q24 adds byte-exact governing-source quote export while
  keeping normalized discovery text separate from evidentiary source text.

- **2026-09-17** -- **The pipeline composer (CR-T-31)**, branch
  `salm/milo/pipeline-finish` (Milo Vance). `assemblePipeline()` joins several
  commands into one shell line -- `|`, `&&`, `||`, `;`, `>`, `>>`, `2>`,
  `2>&1`, `| tee`, `| tee -a`, plus an `xargs` stage -- under one rule: **a
  pipeline is structure the tool owns, never a value the user supplies.** The
  user picks a KEY out of a closed table and the table's own string literal is
  emitted, so `|` never enters a form field. A reference (mined) command cannot
  be a stage by construction; a stage that hands its argument to another
  interpreter (`su -c`, `sh -c`, `find -exec`) is REFUSED rather than escaped
  into a second quoting domain with no oracle (TM2-F8); `| sh` and a write into
  a directory the system executes are refused as one class; blast composes
  rather than taking the max of the stages, and a redirect target nobody has
  classified renders `unrated`, never green. New in the gates: the pipeline
  oracle (589 comparisons, 11 negative controls), 17,092 hostile-vector
  pipeline checks, 108 one-stage invariants, and
  `tests/test_pipeline_ui_wiring.py` on the panel. Harness 81,577 -> 101,297
  checks; unit tests 251 -> 293; all four gates rc=0.

- **2026-09-18** -- **v1.0.0-alpha.1**, branch `salm/taylor/v1.0.0-alpha.1`
  (Taylor Webb, Release Engineer). Version bump off `-dev` (`build.py`
  `APP_VERSION`/`APP_BUILD_DATE`, the single source Q1 checks against the
  built HTML and the dist filename), `docs/CHANGELOG.md` retitled from
  `Unreleased`, provenance manifest (`extract/make_provenance.py` ->
  `dist/md-code-red_v1.0.0-alpha.1.provenance.json`), `CODEOWNERS` gained
  explicit `/content-src/` and `/dist/` lines (SAR condition A5), and
  `docs/DEPLOY_RECEIPT_TEMPLATE.md` added for the pilot jump box. Readiness:
  `REL-2026-09-18-001`. This is a lab-only, unsigned alpha -- see the
  CHANGELOG entry above for the full verification status and known
  limitations, and the Pilot Standard Operating Procedure for the operator
  rules.
- **2026-09-18** -- Gate 3 tag blockers 1, 2, 4 + Q20 RHEL 7 reach, branch
  `salm/milo/gate3-blockers` (Milo Vance). Closes AL-GATE3-009 (`flags_rhel9.json`
  named a generator, `extract/extract_rhel_flags.py`, that never existed; Q8/Q15
  now check every FLAGS dataset's declared generator), AL-GATE3-010 (Q20 now
  reaches the six RHEL 7 baseline rows -- `RAW_DIR_FOR` plus reading
  `.help.txt`, no baseline widened), and AL-GATE3-011: **`content/glossary.json`
  is dropped from `build.py`'s `CONTENT` map for the alpha** -- it shipped
  embedded and unreachable (no renderer, no search-index kind), and is now
  removed from the artifact while the file itself stays committed for a later
  tranche that wires a real glossary view. `qa.py` gained a check
  (`content_family_liveness_failures()`, Q8) that would have caught this on
  its own and will catch a regression back to it. Artifact: 9.2 KB smaller;
  content fingerprint and sha256 both changed, as expected for any content
  change to the embedded island.
- **2026-09-18** -- Stage 07 companion docs, branch `salm/sam/docs-alpha` (Sam Kim).
  `docs/USER_GUIDE.md`, this README, `docs/ARCHITECTURE_BIBLE.md`,
  `docs/WORKFLOW.md` and `docs/CODE_STANDARDS.md` rewritten from the shipped
  artifact (`rm -rf dist && python3 build.py`) and the QA gates rather than
  from the original PRD. Three real user journeys documented as they actually
  run today: guided-form generation (24 of 27 entries), STIG evidence via the
  command palette (the STIG Search and Ansible rail items are documented as
  placeholders, per `renderToolList()`'s own sidebar copy, not as features),
  and reviewing a command's blast level before copying it (no entry in this
  build is rated red, so the confirmation banner is documented as tested but
  not currently observable). The full `KEYMAP` table, the three per-version
  verification badges, Copy vs. Copy with comment, the evidence export's
  field list and content fingerprint (and how an ISSM checks one offline
  against the About panel), search, favorites/recent, print, theme and About
  are written from `template.html` directly. `docs/USER_GUIDE.md` gains an
  honest Known Limitations section with numbers read off the build: 27
  entries/19 tools, RHEL 7 flags parsed for 6 of the probed tools from a UBI7
  container (no RHEL 7 host in the lab), RHEL 9 has no flag dictionary or
  captures yet, only 5 STIG ID/version pairs carry a captured expected
  output, and 0 of the 2,009 flag-dictionary entries carry a curated
  explanation (only 4 flags anywhere in the build do, on the 3 static
  entries). `docs/ARCHITECTURE_BIBLE.md`'s sections are filled from
  `extract/schema.py`, `build.py`, `template.html` and `docs/QA_GATES.md`
  (pointed to, not duplicated) rather than from ADR-001, which stays an
  internal SALM record. `docs/TEST_PLAN.md`/`docs/SSP.md`/`docs/POAM.md` TODOs
  that are now answered are removed; `docs/POAM.md` gains the Q20 flag-
  coverage baseline's 2026-09-25 expiry and the RHEL 9/RHEL 7 content gaps as
  open items with owners. `docs/IDEAS.md` gains four Proposed entries raised
  in review: a per-tool syntax oracle, a `qa.py` module split, an ELS host to
  stand in for RHEL 7, and a second RHEL SME. No file under `content/`,
  `extract/`, `tests/`, or `template.html` itself is touched by this branch;
  `python3 qa.py` (Q1-Q25 + JS) passes on the unmodified artifact, and the
  unit test and hostile-harness counts are unchanged because no code changed.
- **2026-09-18** — Q16 closes J1/J2/J3 (VER-001/002/003), branch `salm/milo/receipt-guards`
  (Milo Vance). Marcus Reed's Verified-per-version review approved the per-version receipt
  schema with three conditions. **J1**: 12 of the 18 shipped receipts sat on generator entries,
  exempt from Q16's command-drift check (`if "template" not in e:`) — a template edit could not
  invalidate the receipts describing its old behaviour. The generator half now diffs a receipt's
  `capture.command_as_run` against `tests/fixtures/golden-commands.json`, the same hand-authored
  validity oracle the harness already uses — closing content debt this exposed along the way:
  `gen-chage-list`'s golden row was pinned to a username (`svcacct`) that does not exist on
  either lab host, while its real, receipted capture ran `adm-linux`; the golden row is now
  pinned to the value actually, verifiably run. **J2**: the two-person rule was byte-for-byte
  string equality — eight of Marcus's nine hostile variants (case, padding, doubled/NBSP
  whitespace, a `(SME)` suffix) bypassed it, and a deliberate alias (`"C. Stone"`) cannot be
  closed by any string comparison at all. Both names are now normalised
  (`normalize_person_name()`) and checked against a new closed roster,
  `content-src/roster.json` (Caleb Stone and Renata Osei as SMEs, Riley Park as QA) — `by` must
  hold the QA role, `captured_by` the SME role — and the gate's own PASS diagnostics state the
  residual plainly: the deliberate-alias path is closed by roster membership, not by string
  matching. **J3**: `host` and `capture` had no closed grammar; both are now regex-bound
  (`RECEIPT_HOST_RE`, `RECEIPT_CAPTURE_PATH_RE`), and a receipt's `host` must equal its own
  capture's `host`. Fail-first throughout: `tests/test_q16_receipts.py` grew from 4 to 21 cases,
  each shown red against the pre-fix gate before the fix landed. Full gate green
  (`rm -rf dist && python3 build.py && python3 qa.py && python3 -m unittest discover -s tests &&
  node tests/hostile_harness.js`); artifact sha256 unchanged at
  `bb950d9088060ed619c5e1178cc128b9b91d69d9240e9847001d1963573a9f06` (QA-gate and content-src
  work only — the shell, the assembler and the data island are untouched). See
  `docs/CHANGELOG.md` for the full breakdown.
- **2026-09-18** — `verified` is per RHEL version, branch `salm/milo/verified-per-version`
  (Milo Vance). CEO ruling closing Riley Park's first capture review
  (`capture-review-run1-2026-09-18.md` RILEY-F1): a single whole-entry `verified` flag could not
  be set `true` for any of Caleb Stone's CR-T-34 batch without overclaiming an RHEL version
  nobody captured. `content/commands.json`'s `verified` is now an object keyed `"7"`/`"8"`/
  `"9"`/`"10"`, each `false` or a `{by, on, host, capture}` receipt; the old boolean is rejected
  by `extract/schema.py`, and a version whose row is `unavailable` or a `same_as` pointer can
  never carry a receipt of its own (it was never independently run — a `same_as` target's
  receipt does not propagate). `qa.py`'s Q16 gate now checks each receipt against its own
  capture file for that exact entry/version pair (hash-matched against the currently assembled
  command; the SME who captured it can never be the QA reviewer who verified it). Riley Park's
  18 cleared entry/version pairs (`firewalld-service-active`, `ctrl-alt-del-target-masked`,
  `journald-service-active`, `gen-ausearch-by-key`, `gen-chage-list`,
  `gen-journalctl-unit-logs`, `gen-podman-ps`, `gen-rsyslogd-test-config`,
  `gen-systemctl-query` x RHEL 8/10) are now written in. `extract/import_captures.py`'s
  one-hop-only same_as resolver (Riley's RILEY-F5) now delegates to `extract/schema.py`'s
  cycle-guarded, any-length chain resolver. The Inspector, the evidence exporter and the status
  bar now show per-version verification state ("verified by NAME on DATE (HOST)" / "captured,
  awaiting QA" / "not host-verified"). See `docs/CHANGELOG.md` for the full breakdown.
- **2026-09-17** — CR-T-12, branch `salm/milo/flags-rhel7` (Milo Vance): `flags_rhel7.json` is
  populated for the first time, from a rootless UBI7 container on saratoga standing in for the
  RHEL 7 host the lab doesn't have (`registry.access.redhat.com/ubi7/ubi:latest`, digest
  `sha256:046e525722f14702c360dc6092324af7c21656e76b0c254b067871f1d4d3df68`; no sudo, no host
  package installs, container removed after, image kept). `extract/extract_flags.py` gained
  `--container` (podman-exec routing inside `ssh_run()`, the same read-only commands one hop
  further in — smaller than teaching the whole extractor to run inside the container), and
  `_meta.host`/`kernel_caveat` say plainly this is a container standing in for RHEL 7, not
  saratoga's own RHEL 10. UBI7's public repos carry no `man`/`man-db` at all, so every tool is
  `--help`-only; of the 22 P0 tools, 6 had a binary available (`systemctl`, `journalctl`, `yum`,
  `useradd`, `usermod`, `chage`) and are extracted (38 flags, 90 unparsed raw hints). The other 16
  are honestly `available: false`: `dnf`/`podman` because neither ever shipped on RHEL 7 (same
  treatment those two already had), the rest (`firewalld`, `NetworkManager`, `lvm2`, `audit`,
  `rsyslog`, `chrony`, `policycoreutils-python`, `openssh-server`, `git`) because their packages
  or dependency chains (`perl`, `libfipscheck`, `libedit`) are not in UBI7's public repos — nothing
  worked around, no other source substituted. `content-src/flag_coverage_baseline.json` gained a
  `coverage["7"]` block for the 6 available tools plus a note that Q20 (`qa.py`'s `RAW_DIR_FOR`)
  is not extended to RHEL 7 here, so this does not widen anything the gate currently checks, and
  that `firewall-cmd`'s RHEL 8/10 synopsis-line regex gap almost certainly reproduces on RHEL 7 too
  but isn't observable without a `firewalld` capture — same ratchet owner/date, Caleb Stone,
  2026-09-25. One change outside `extract/`: `qa.py`'s Q15 FLAGS special case (the filter that
  keeps a populated flags dictionary from permanently "drifting" against the empty-placeholder
  skeleton script) gained `flags_rhel7.json`, extending the exact pattern CR-T-09/10 already used
  for RHEL 8/10 a third time — not a host-abstraction change, but required the moment RHEL 7 stopped
  being empty. `tests/fixtures/evidence/firewalld-service-active.rhel9.txt`'s committed content
  fingerprint updated to match the new data island (confirmed byte-diff: only that one line moved).
  Gates: `build.py` reproducible / `qa.py` (Q1-Q25, JS: PASS) / `python3 -m unittest discover -s
  tests` (176 OK) / `node tests/hostile_harness.js` (81577 checks, 0 FAILED) all green.

- **2026-09-17** — H1/H2/H3, branch `salm/milo/panels-conditions` (Milo Vance), Marcus Reed's
  three post-G4 conditions before merge. **H1 (correction):** `gen-chronyd-one-shot-check` goes
  back to `blast: "green"` — G4(d) wrongly raised it to yellow on Caleb Stone's CR-T-34 note that
  `chronyd -Q` "steps the system clock", which misread `chronyd(8)` and was repeated by an
  earlier ruling and then encoded into content. The pinned man page is explicit and identical on
  RHEL 8 and RHEL 10 (`content-src/raw/rhel{8,10}/chronyd.man.txt#L64-L74`): `-q` steps the
  clock; `-Q` "only prints the offset without making any corrections of the clock and disables
  server ports to allow chronyd to be started without root privileges" — this toolkit only ever
  generates `-Q`. `intent`/`verify`/`undo`/`notes` are rewritten to say what the man page actually
  says, with the lines cited. **H3:** `tests/test_blast_state_change_labels.py`'s
  `STATE_CHANGE_RE` drops `-Q` and anchors its bare-word entries with `\b` word boundaries instead
  of matching as a plain substring — the old form matched `gen-nmcli-static-ipv4` only because
  `ipv4.addresses` contains the letters "add", and `gen-useradd-create` only because `useradd`
  does; new negative-case tests lock in that `del`/`add` no longer fire inside `--delete` or
  `--address`. Fail-first: both corrections landed as a failing test first (chronyd's `blast`
  assertion; the anchoring's negative cases already passed, added alongside as a regression
  guard), then the content/pattern fix. **H2:** the evidence exporter's line-safety treatment
  (`evidenceHeaderSafe()`/`evidenceLineSafe()`, condition G2) had its own hand-rolled numeric
  range table that had already drifted from `MCR-ASSEMBLER`'s `INVISIBLE_RE` — missing `U+061C`,
  `U+00AD`, `U+206A`–`U+206F` and `U+FE0F`. Both now share ONE table: a new global-flagged
  `INVISIBLE_RE_G` twin of `INVISIBLE_RE`, used by both `headerSafe()` (widened, MCR-SEC-003's
  clipboard header) and `evidenceHeaderSafe()` (rewritten to delete its own separate table).
  New `tests/test_evidence_invisible_coverage.js`/`.py` lift `INVISIBLE_RE` and
  `evidenceLineSafe()` straight out of the built file and enumerate every BMP codepoint against
  it, so the two tables can never silently diverge again — committed failing (35 of 58 rejected
  codepoints survived the old table), now 0. `tests/test_evidence_export.js` now lifts
  `MCR-ASSEMBLER` alongside `MCR-EVIDENCE` (evidence is no longer self-sufficient lifted alone, on
  purpose). 22/22 `qa.py` gates PASS, 176 unit tests PASS (171 + 5 new), hostile harness
  81,577 / 0 FAILED, including the `MCR-SEC-003` line-terminator invariant H2's reordering had to
  keep true.

- **2026-09-17** — G4, branch `salm/milo/panels-conditions` (Milo Vance), continuing on the
  same branch after G1-G3. Rulings from Eli Cross closing CR-T-34's WADE_BLOCKED (Caleb Stone's
  content validation run, `tests/captures/README.md`, cherry-picked from `salm/caleb/captures-green`
  `1db0b97`/`924f589` to keep his authorship). **(a)** Canonical capture path is
  `tests/captures/<rhel_version>/<entry_id>.json` in this repo — `extract/make_pending_skeletons.py`'s
  own docstring (which named `content-src/captures/`) and the `07_QA_Test/MD_CODE_RED/`
  content validation protocol document (which proposed a separate `07_QA_Test/MD_CODE_RED/captures/`
  tree) are both fixed; the protocol document is now a company-record pointer to the repo path,
  not a second storage location. **(b)** `qa.py`'s Q16 checked capture records against field
  names no real capture has ever carried — the protocol's own §7 schema
  (`entry_id`, `rhel_version`, `host`, `redhat_release`, `kernel`, `pkg_versions`,
  `command_as_run`, `exit_code`, `stdout`, `stderr`, `captured_on`, `captured_by`,
  `blast_confirmed`, `undo_executed`, plus `command_hash_at_capture` and `verify_result`) is now
  the authority `CAPTURE_REQUIRED_FIELDS` in both `qa.py` and the new extractor check against;
  `template.html`'s evidence exporter and STIG panel are fixed to read the same real field names
  (`redhat_release`, `stig_compliance.compliant`) instead of a shape no capture ever had. **(c)**
  New `extract/import_captures.py`: walks `tests/captures/`, validates every record against that
  field set, verifies `command_hash_at_capture` against a fresh `sha256(command_as_run)` and,
  for entries with a fixed `rhel_versions[version].command` (never a generator's — MCR-SEC-006),
  against the entry's CURRENT command, so an edited command silently reverts the entry to "not
  captured yet" rather than going on narrating a command that no longer exists; regenerates
  `content/expected_output.json` (now solely this extractor's file — `extract/make_pending_skeletons.py`
  drops it). Tested with Caleb's 18 real files: 5 fold into the STIG-keyed index (the five real
  STIG rows his run documents), 13 validated but unindexed (no STIG mapping). `qa.py` Q16 now
  passes WITH real captures; the STIG panel and evidence exporter show Caleb's real compliant
  output, host, release and kernel for `firewalld-service-active` and `ctrl-alt-del-target-masked`
  on RHEL 8/10 and `journald-service-active` on RHEL 10. **(d)** `gen-dnf-package`,
  `gen-yum-package` (both `blast: "green"` covered install AND remove; install has no dynamic
  escalation in `content/dangerous.json` at all) and `gen-chronyd-one-shot-check`
  (`chronyd -Q` steps the system clock, a real state change its own notes only argued the
  negative about) are raised to `blast: "yellow"`, content and `tests/fixtures/golden-commands.json`
  both. New `tests/test_blast_state_change_labels.py`: a static sweep asserting every generator
  whose golden command matches a state-changing pattern table
  (`install|remove|erase|-Q|--permanent|enable|start|stop|add|del`) declares at least yellow —
  committed failing on exactly these three, now green; Marcus Reed's enum-branch sweep
  (`tests/hostile_harness.js`, MCR-SEC-021) still passes unchanged. **(e)** `gen-sshd-test-config`
  (`sshd -T` — `Permission denied` on both `defiant` and `saratoga` in Caleb's real run, since
  `sshd_config` is not world-readable on a STIG'd host) gets a new `privilege: "root"` field
  (`extract/schema.py`'s new `PRIVILEGES` enum); the UI shows a "requires root" badge next to
  blast on both the static and generator entry cards, and the evidence exporter adds a
  `Requires: root` line. 22/22 `qa.py` gates PASS, 171 unit tests PASS (168 + 3 new), hostile
  harness 81,577 / 0 FAILED.

- **2026-09-17** — Panels review conditions G1/G2/G3, branch `salm/milo/panels-conditions`
  (Milo Vance), closing Marcus Reed's APPROVE WITH CONDITIONS on `636fd7f`. **G1 (MED,
  PANEL-001):** `firewalld-service-active` and `journald-service-active` declared
  `tool: "firewall-cmd"`/`"journalctl"` while every `rhel_versions` command is a `systemctl`
  invocation, so the Inspector's flag panel (`decodeCmd(res.tool, ...)`) looked `status`/`is-active`
  up in the wrong binary's dictionary and could never resolve them, even once CR-T-09/10 populated
  real dictionaries. Fixed with an `explain_tool: "systemctl"` field on both entries (simpler than
  re-filing `tool`, which drives the sidebar Tools rail and would have buried both entries under
  `systemctl`'s long entry list) — `renderInspector()` now resolves the flag dictionary through
  `entry.explain_tool || res.tool`. New `qa.py` **Q22** gate (committed failing first, 8 FAILs on
  the two entries) checks every entry's declared tool resolves, through `tools.json`'s new `binary`
  field, to the actual binary its commands invoke, and every flag resolves in a populated
  dictionary, carries a curated `explain`, or is honestly marked (non-option-shaped with a
  `license_class`, since a systemctl subcommand like `is-active` can never appear in a man-page
  OPTIONS dictionary). **G2 (LOW, PANEL-002):** `esc()` correctly stays an HTML-entity escaper, not
  a sanitiser, but a bidi override or a raw NUL in a rule title/check text still reached
  `formatEvidenceText()`'s plain-text output unchanged — this text crosses trust boundary 5 into an
  SCTM/ATO package. New `evidenceHeaderSafe()`/`evidenceLineSafe()` in the `MCR-EVIDENCE` block
  (reimplemented rather than calling `MCR-ASSEMBLER`'s `headerSafe()`, so the block stays
  independently liftable and pure, and per physical line so multi-paragraph check/fix text keeps
  its structure) strip C0/C1 controls, NUL, and bidi/zero-width ranges from every interpolated
  value; `<`, `"` and `'` still come through literally, since this is plain text, not markup.
  Fail-first hostile fixture (U+202E, U+200E, NUL) added to `tests/test_evidence_export.js`.
  **G3:** the CR-T-28 report's sample export citation ("man firewall-cmd(1) … retrieved 2026-09-01")
  traced to `tests/test_evidence_export.js`'s own hand-written determinism fixture — a synthetic
  illustration, never real content — pasted into the report as if it were a real run;
  `content/commands.json`'s real `source` for that entry has always been the DISA STIG pin. New
  `tests/test_evidence_export_real.js`/`.py` build the REAL evidence export for
  `firewalld-service-active` on RHEL 9 by lifting `MCR-ASSEMBLER`/`MCR-EVIDENCE` over the real
  built data island and snapshot it against `tests/fixtures/evidence/firewalld-service-active.rhel9.txt`,
  so the report sample and the shipped artifact can never diverge again. 22/22 `qa.py` gates PASS
  (new **Q22**), 168 unit tests PASS (167 + 1), hostile harness 81,577 / 0 FAILED — byte-identical
  to Marcus Reed's review, `MCR-ASSEMBLER` untouched.

- **2026-09-17** — CR-T-26/28/29/30, branch `salm/milo/panels` (Milo Vance). Four renderer/index
  modules landed on top of `0ba8cf5`, all consuming the existing rendered-state object — the
  `MCR-ASSEMBLER` block and the field validators were not touched. **CR-T-26 STIG panel:**
  `renderStigPanel()` now owns the Inspector's STIG display — badge (STIG ID, CAT), every cited CCI
  with the CCI → NIST SP 800-53 crosswalk (`nistForCci()`, against `content/cci_nist.json`),
  expandable Check text / Fix text (verbatim DISA text through `esc()`), expected compliant output
  when a capture exists or the honest "no capture yet" state when it does not, the RHEL 7 sunset
  banner from `rules_rhel7._meta.sunset`, and the entry's "changed in RHEL X" note. The badge renders
  only when `stig[]` is non-empty. A STIG rule reached via search with no command in the catalog opens
  on its own (`selectStigRule()`), with the same panel and an honest "no command yet" message in the
  editor. **CR-T-28 reference exporter:** `Ctrl+E` / the Export command and control reference button opens a deterministic
  plain-text command/control reference — tool version, the new content fingerprint, STIG ID/version/benchmark
  date, CAT, CCI → NIST controls, check/fix text, expected output (or "not captured"), the assembled
  command exactly as `currentResult()` produced it (never recomputed), source citation, capture
  metadata when present, and the operator's own date line — previewed in an escaped `<pre>` that is
  byte-for-byte what Copy puts on the clipboard. Two exports of the same entry are identical except
  that one line (`tests/test_evidence_export.js`). **Content fingerprint**, defined once for both
  CR-T-28 and CR-T-30: sha256 of the embedded data island, computed by `build.py` before the payload
  is substituted into the template and embedded as the `CONTENT_FINGERPRINT` constant — `qa.py`'s Q1
  gate now independently re-hashes the shipped island and fails the build if the two disagree.
  **CR-T-29 search:** the palette's index is now a lazily built, typed index (`buildIndex()` /
  `queryIndex()`) over tools, flags (curated and per-release dictionaries), STIG IDs and titles, CCIs
  and NIST controls — built once, on first use, grouped by kind in the results, with an explicit
  no-match state. Build and query both measure well under the 100 ms budget on the full ~4,000-record
  embedded dataset (`tests/test_search_index.js`). **CR-T-30:** favorites and recent — entry IDs only,
  under the existing schema-versioned storage guard, never rendering stored text
  (`sanitizeIdList()`, `tests/test_favorites_store.js`); a print stylesheet extension so
  `Ctrl+P` prints the current entry and its STIG panel (mirrored into a `.print-only` element,
  identical content, hidden on screen) with no other chrome; an About panel with tool version, build
  date, content fingerprint, per-release STIG versions/dates, the embedded source families and their
  license classes, and the SALM Content Licensing Ruling v1 attribution block, reproduced verbatim
  (hyphens in place of the source's em dashes, so no hand-typed non-ASCII glyph enters a tracked
  file). All 21 QA gates + `JS` pass, 167 unit tests pass (159 existing + 8 new), and the hostile-input
  harness reports 0 failures over 81,577 checks — none of it touched, since nothing here reaches into
  the assembler.

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
  option it does not emit) to `#L538`, and a new **gate Q20** measures the flag dictionary against the
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
  violations, and shown failing against the pre-fix tree. Merged with `origin/main` at `da2ab47` (the
  Gate 3 qa.py hardening), where the new coverage gate takes the number **Q20** because Q19 is now the
  escaper property gate. Gates on the merged tree, from a clean `dist/`: `build.py` reproducible /
  `qa.py` **Q1–Q21 PASS** / `unittest` **159 OK** (135 from the hardening merge + 24 added here) /
  harness **81,577 checks, 0 FAILED** (was 76,225) / artifact sha256
  `9eb3402689e8c4f68f914a8154515aa117b999da646e9fb6c0bb1ce8c40bab2b`. Also closed on this branch:
  **Q21**, after a `json.dump(..., ensure_ascii=False)` round-trip in `dd01ad7` turned eight
  invisible-character vectors in `tests/fixtures/hostile-inputs.json` into the raw characters they
  name — no gate could see it, because Q17 scans the artifact and the harness reads the file as JSON.
  Marcus's D4 re-review then took Q21 wider (all 226 tracked files, nothing excluded, a U+FEFF at
  offset 0 the only allowance), settled **MCR-SEC-025** from the pinned chronyd capture (directives
  are operands, so the command stands; the citation and notes were the part that was wrong), and gave
  the **Q20** coverage ratchet a retirement plan — owner Caleb Stone, 2026-09-25, enforced by the gate.

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
- **2026-09-17** — QA gate hardening against fail-open, branch `salm/milo/qa-hardening`
  (Milo Vance). Al Kowalski's BQP Gate 3 diff review of `qa.py` returned **PASS WITH ISSUES**
  with one HIGH finding and five MEDIUM/LOW. `qa.py` is the merge gate, so its own defects are
  trust-path defects, and every fix here landed with the gate first shown to FAIL.
  **AL-GATE3-001 (HIGH)** — Q17 proved `esc()`/`escapeAttr()` are *called* at every render sink
  and could never prove they *escape*: a one-line `return s;` in either body defeated the whole
  render-safety property with zero change to any call site (`render_sink_failures()` returned
  `([], 4)` on identity escapers). New **Q19** lifts the three escapers verbatim out of the
  shipped artifact and RUNS them under node against 92 hostile vectors plus 3 generated long
  ones — every HTML metacharacter, the OWASP XSS basics, already-escaped and doubly-escaped
  entity text, C0/C1 and bidi and zero-width characters, lone surrogate halves, every regex
  metacharacter. `esc()` must leave no raw `< > " '` and no bare `&` **and** round-trip exactly,
  so an escaper that *deletes* the dangerous character fails too rather than silently corrupting
  DISA fix text. The probe fails three known-broken escapers before it will report a PASS.
  **AL-GATE3-003 (MED)** — one unbalanced brace inside a string literal inside a `try{}` block
  desynced Q7's brace counter and rated a genuinely unguarded `localStorage` call "guarded";
  braces are now counted over a lexically masked copy. **AL-GATE3-004 (MED)** — Q3/Q4/Q8/Q12/
  Q13/Q16 all reported PASS on a bundle with no entries, no tools and no rules; every one now
  fails, naming what was empty, carrying across the reasoning Q9 has had since CR-T-07.
  **AL-GATE3-005 (MED)** — Q3's provenance field list had drifted *weaker* than
  `extract/schema.py`'s, missing `version`; it is now read out of that file's text, a shared
  constant and never a shared code path. **AL-GATE3-006 (LOW)** — a harness report that parsed
  but was key-incomplete crashed Q18 with an uncaught `KeyError` instead of printing a named
  FAIL. **Q2** gained the MCR-SEC-014 treatment the render sinks already had: a network API
  reached by a bracketed name, a name fused from string literals, or an alias never called on
  the same line is now caught. **Q5** markers are classified from their own text and must appear
  where their kind lives — code in live code, region ids in the markup, user-visible copy in a
  string, which is the only place copy can be. **Q14** finally has the `tests/test_paraphrase.py`
  ADR-001 §7.3 promised, and refuses a build whose populated flag dictionary has no raw sources
  staged. New `docs/QA_GATES.md` lists every gate, what it proves, its negative control and its
  residuals, and collects the ADR-001 §7 items that are now stale, for Al. Gates: 19 → 20
  (Q1–Q19 + JS), all PASS. Tests: 51 → 135, all OK. Harness 63,536 checks / 0 failed. Artifact
  byte-identical (`template.html` untouched), sha256 `5fb9b7ad…`.

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

## Attribution

Reproduced verbatim from SALM's Content Licensing Ruling v1, the same text shown
in the running tool's About panel (`Ctrl+Alt+7`, `ATTRIBUTION_BLOCK` in
`template.html`):

```
Content Sources & Licensing:

This toolkit embeds content derived from the following sources under their respective terms:

- DISA STIG & CCI Lists (Public Domain, US Government work) - https://www.cyber.mil/stigs/
- NIST SP 800-53 Rev 5 / OSCAL (CC0 1.0, Public Domain) - https://github.com/usnistgov/oscal-content
- ComplianceAsCode Project (BSD-3-Clause License) - https://github.com/ComplianceAsCode/content
- Red Hat Enterprise Linux Documentation (CC-BY-SA 3.0) - https://docs.redhat.com/
- Linux man-pages & GNU Utilities (GPL-2.0-or-later) - https://www.kernel.org/doc/man-pages/
- Ansible Project (GPLv3) - https://github.com/ansible/ansible

Paraphrased content, remediation code, and identifiers are integrated to provide a unified toolkit for RHEL 9 compliance. Full compliance details: [link to detailed licensing document].
```

See `NOTICE` at the repo root for the fuller, per-family derivation statement
(what is verbatim public-domain text versus paraphrase-only, and where each
family's raw source is staged for a licensing audit).

## Documentation

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) -- Core workflows and UI reference
- [docs/CHANGELOG.md](docs/CHANGELOG.md) -- Version history and feature timeline
- [docs/IDEAS.md](docs/IDEAS.md) -- Feature backlog and decision log
- [docs/WORKFLOW.md](docs/WORKFLOW.md) -- Content pipeline and refresh cycles
- [docs/TEST_PLAN.md](docs/TEST_PLAN.md) -- QA charter and validation protocols
- [docs/QA_GATES.md](docs/QA_GATES.md) -- Every gate: what it proves, its negative control, its residuals
- [docs/ARCHITECTURE_BIBLE.md](docs/ARCHITECTURE_BIBLE.md) -- System design and data models
- [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) -- Engineering patterns and security rules
- [docs/SSP.md](docs/SSP.md) -- Security compliance and controls (NIST 800-53)
- [docs/POAM.md](docs/POAM.md) -- Open findings and remediation plans

**Status:** Build stage, Phase 1 engineering scope on `main`. `python3 qa.py`
passes all 26 gates plus the JS syntax check; see `docs/QA_GATES.md` for what
each gate proves and does not prove, and `docs/POAM.md` for open findings.
Current release counts and the receipt-derived default RHEL release are generated
in `docs/generated/RELEASE_FACTS.md`. Known content gaps (RHEL 9 command
receipts, RHEL 7 host coverage, and uncurated flag explanations) are listed in
`docs/USER_GUIDE.md`'s Known Limitations section, not hidden in this status line.

**Contact:** Zee (Engineering) | Jordan Patel (PM) | Sam Kim (Technical Writer)
