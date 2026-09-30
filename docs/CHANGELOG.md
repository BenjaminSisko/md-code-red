# Changelog

All notable changes to MD CODE RED are documented here. This project adheres to [Keep a Changelog](https://keepachangelog.com/).

## Unreleased -- v1.0.0-alpha.6-dev

### Changed -- Responsive operations-console UX

- Added an always-visible **Search all** control for tools, commands, STIGs,
  CCIs, and NIST controls, without changing the existing keyboard shortcuts.
- Added visible **Navigator** and **Inspector** controls whose pressed state
  reports whether each panel is open.
- Reworked the layout below 720 pixels into a single-column reading order with
  a horizontally scrollable, sticky activity rail and larger touch targets.
- Fixed the tablet layout so hiding the inspector also removes its empty row.
- Added a keyboard skip link, clearer product identity, stronger command-title
  hierarchy, and focused industrial typography while preserving the offline,
  zero-asset, single-file design.
- Archived the immutable alpha.5 HTML, SHA-256 sidecar, and provenance manifest
  before starting alpha.6 development.

## v1.0.0-alpha.5 - 2026-09-22

### Fixed -- Operational recovery and administrative accuracy

- Firewalld rich-rule generators now require an explicit zone, apply permanent
  changes to runtime with reload, verify both stores, and recover by removing
  the exact generated rule. The prior contradictory-rule and direct XML-edit
  advice is gone.
- NetworkManager, DNF/YUM, systemd, LVM, cron, and generated-configuration
  recovery now starts from captured pre-change state. Remote network changes
  require recovery access; destructive storage steps require exact device
  identity, signature, mount, holder, LVM-membership, backup, and review checks.
- Privilege metadata was audited across all 199 curated entries. Thirty-seven
  commands that normally require elevation on hardened RHEL now say so.
- Added curated consequence explanations for every previously unexplained
  option or subcommand used by a yellow/red static entry, including systemd
  `--now`, firewalld permanence/reload, group replacement, journal vacuuming,
  and Ansible Galaxy/Vault actions.
- NFS mount, journal vacuum, and local-repository metadata entries now describe
  exactly the single operation their command performs.

### Added -- Instructional workflows

- Added schema-validated instructional metadata for all 43 generators and all
  106 fields: labels, meanings, examples, consequences, discovery guidance,
  prerequisites, and preflight checks.
- Generated operations now render value-bound Preflight, Run, Verify, and
  Recover steps with per-step and full-plan copy controls. Copy fails closed if
  any instructional placeholder remains unresolved.
- Added Start Here learning pathways, RHEL 7-10 command/evidence comparisons,
  exact man-page commands and search hints, honest recovery-proof badges, and a
  working STIG-search rail action.

### Added -- Execution evidence, validation, and distribution controls

- Renamed the browser action to **Export command and control reference** so its
  expected output and source context cannot be mistaken for proof of execution.
- Added a formal execution-receipt schema and offline tool that bind actual
  output, stderr, exit status, target, operator, timestamp, ticket, command,
  artifact, fingerprint, verification, hashes, and attestation without running
  the command itself.
- Added nine RHEL troubleshooting decision trees, a real-host validation matrix
  with explicit unknowns, generated release facts with drift checks, and a
  signing workflow that refuses to choose or fabricate a publisher identity.
- Archived the released alpha.4 artifact set byte-for-byte under
  `releases/v1.0.0-alpha.4/` before building alpha.5.

## v1.0.0-alpha.4 - 2026-09-22

### Added -- Generalized command syntax oracle

- Completed roadmap item 260917-005: a generalized, source-cited per-tool
  command syntax oracle now validates all 865 simple invocations contained in
  620 resolved static and 169 hand-authored golden generator release commands.
  Its 420 grammar rows load independently by RHEL release; the tokenizer keeps
  quoted/escaped operators as operands and validates later compound commands.
  Git, DNF and systemctl options and operands are scoped by subcommand. The
  exact generator golden table remains active as an independent oracle.

### Added -- Configuration-file generators

- Completed roadmap item 260917-004 with guided builders for sshd, chrony,
  rsyslog, sudoers, systemd service units, and cron. Each form produces a
  reviewable file plus a validation or installation command with explicit
  verification and recovery guidance.
- Added a `lines` document kind for configuration formats that are neither
  YAML nor INI. Each line is assembled only from declared literal tokens and
  closed field grammars; free text, control characters, shell separators, and
  undeclared fields fail closed in both the build schema and browser runtime.
- Extended the hostile-input harness with an independent token-line parser and
  exact round-trip oracle. All six command invocations are also pinned for
  RHEL 7-10 in the hand-authored golden-command table.
- The catalog now has 199 entries across 102 tools: 43 guided generators and
  156 static entries.

### Added -- Ansible task-selection completion

- Completed roadmap item 260917-003 by upgrading the existing playbook,
  inventory, and `ansible.cfg` builders with real task-selection controls.
- The package playbook now offers checkboxes to refresh DNF metadata before the
  package task and to start and enable a same-named service afterward. The
  generated command remains `ansible-playbook site.yml --limit=... --check
  --diff`, so the offered invocation is a dry run.
- Checkbox controls are constrained to an optional enum whose sole value is
  `yes`; unchecked means absent. Build-time schema validation rejects any
  arbitrary checkbox payload or required checkbox.
- Every optional YAML task is gated as a complete block. The hostile harness
  parses and compares all optional-task combinations across RHEL 7–10, so a
  missing block header or orphaned nested line fails the release gate.

### Added -- Git Command Generator

- Added a dedicated **Git** activity rail (`Ctrl+Alt+4`) containing the full
  curated Git catalog and eight guided scenarios: clone, branch, merge,
  rebase, annotated tag, bounded log, bisect, and lost-commit recovery.
- Added closed `git_refname` and `git_revision` field grammars for branch, tag,
  commit, and reflog expressions. Repository addresses and annotation text use
  the existing capped, control-character-rejecting free-text path and still
  reach the command only as one shell-quoted operand.
- Palette and Favorites selections now return Git entries to the Git rail and
  Ansible entries to the Ansible rail. The Command Builder excludes both
  dedicated categories, so each tool appears in one activity slice.
- Added exact golden commands for every generator on RHEL 7, 8, 9, and 10,
  hostile-input coverage for both new field types, and a focused Git-rail
  regression test. The catalog now has 193 entries across 102 tools: 37 guided
  generators and 156 static entries.
- The activity-rail keyboard contract now covers seven rendered buttons:
  Favorites moves to `Ctrl+Alt+5`, Reference to `Ctrl+Alt+6`, and About to
  `Ctrl+Alt+7`.

### Added -- RHEL P0 LVM command completion

- Added guided `pvcreate` and `vgcreate` builders, closing the two remaining
  non-Git tools in the 22-tool P0 extraction matrix. Git stays in its separate
  P1 feature track.
- Both builders use absolute device-path validation, require root, cite the
  captured RHEL 8 manual pages, and carry explicit verification and recovery
  guidance.
- Both operations are rated red. `content/dangerous.json` now independently
  raises any assembled `pvcreate` or `vgcreate` command to the red floor, so
  Copy remains locked until the operator acknowledges review.
- Added exact golden commands for all four RHEL releases and a focused
  completion regression test. The curated catalog is now 185 entries across
  102 tools: 29 guided generators and 156 static entries.
- Validation: Q1-Q25 and JavaScript syntax pass; 339 Python unit tests pass;
  the hostile-input harness passes 101,957 checks, including all 29 real
  generators and 116 exact per-release golden-command comparisons.

## v1.0.0-alpha.3 - 2026-09-20

### Fixed -- MCR-A2-KEY-001 six-rail keyboard navigation

- The single `KEYMAP` rail-jump binding now accepts `Ctrl+Alt+1` through
  `Ctrl+Alt+6`, matching all six rendered rail buttons: Command Builder, STIG
  and Evidence Search, Ansible Generator, Favorites and Recent, Reference
  Commands, and About. `Ctrl+Alt+6` now selects and focuses About as its button
  title advertises.
- `docs/USER_GUIDE.md` and the README now use that same explicit six-item
  mapping; Reference remains `Ctrl+Alt+5` and About is `Ctrl+Alt+6`.
- `tests/test_rail_keyboard.js` executes the shipped `KEYMAP`, `railAt()` and
  modifier matcher against every rendered rail. Its unittest wrapper also
  requires one unique advertised/runtime binding per button and keeps the user
  guide's mapping in lockstep with the UI.
- Release impact: the historical `v1.0.0-alpha.2` tag and released files remain
  unchanged as evidence of what shipped. Alpha.2's current published artifact
  set is archived byte-for-byte under `releases/v1.0.0-alpha.2/`. This correction
  receives fresh exact-revision automation and independent regression review;
  browser/pilot acceptance remains a separate post-integration gate and is not
  claimed by this candidate.

## v1.0.0-alpha.2 - 2026-09-20

Recovery release built from the current main line. It preserves alpha.1 under
`releases/v1.0.0-alpha.1/`, closes the four remaining pipeline findings, retires
the dated Q20 waiver with evidence and authority, refreshes the three-family
reference corpus to 14,439 distinct commands, and makes Q21-Q25 continuous
release gates. The mined reference tier remains separate from the 183-entry
curated catalog and cannot enter the assembler.

### Added -- reference evidence and continuous corpus gates

- Q23 measures closure and independently samples classifier accuracy across all
  12 family/release cells.
- Q24 enforces reference/curated shape separation and exports governing-source
  quotations only from byte-exact, evidence-eligible spans.
- Q25 re-resolves all 23,447 citations and rejects source, anchor, text, or digest
  drift.
- Provenance now fingerprints all five JSON islands in declaration order.

### Added -- the pipeline composer (CR-T-31, branch `salm/milo/pipeline-finish`)

Founder requirement, verbatim: *"I need to be able to pipe commands together as
well."* `assemblePipeline(stages, version, opts)` lands beside
`assembleCommand()`, inside `MCR-ASSEMBLER`, pure, and never replacing it.

**The design constraint, which is the whole of the implementation:** a pipeline
is structure the tool owns, never a value the user supplies. The user picks a
KEY; the key is resolved by `hasOwnProperty` against `PIPE_OPERATORS`; that
table's own string literal is emitted. No code path copies operator text out of
a stage, so `|` never enters a form field -- which matters because `|` is
exactly the metacharacter the hostile harness rejects tens of thousands of times
over in every other field of this product.

- **Operator set, closed, ten:** `|`, `&&`, `||`, `;`, `>`, `>>`, `2>`, `2>&1`,
  `| tee`, `| tee -a`. A redirect TARGET is a validated `path` field, never free
  text. `xargs` is its own stage kind with `-0`, `-n` and `-I`; `-0` is refused
  unless the producing stage provably emits NUL-delimited records (`find
  -print0`, `grep -Z/-z/--null`), and `-n` alongside `-I` is refused because
  `xargs` resolves that contradiction silently.
- **A reference (mined) command can never be a stage.** A stage must carry a
  TEMPLATE the assembler emits word by word; a spec carrying a handed command
  STRING is refused by `isComposableSpec()`. Structural, not a filter on a
  picker. Two reasons, one rule (ADR-002): joining two vendor strings produces a
  command the vendor never published while the citation still claims they did,
  and a handed string is text this assembler did not compose, so it cannot know
  the string contains no `|`.
- **Blast is not the max of the stages.** A write outside a scratch path is at
  least yellow; a target under `/etc`, `/boot`, `/dev`, `/usr`, `/var/lib`,
  `/sys`, `/proc` is RED; an execution-sink target (`/etc/cron.d`,
  `/etc/profile.d`, `/usr/local/bin`, `/var/spool/cron`, ...) is REFUSED, not
  rated -- `> /etc/cron.d/x` is `| sh` with a timer; `| xargs rm` and any xargs
  feeding a red child are RED; `;`/`&&`/`||` carry the max; `dangerous.json` is
  evaluated against the de-quoted projection of the WHOLE pipeline, so a pattern
  spanning an operator still fires; and the redirect rule is applied a SECOND
  time to that same projection without consulting the `path` field type, so it
  stands on its own.
- **A target outside the protected list renders `unrated`, never green (PL4).**
  Green in this product is a human claim -- somebody curated an entry and said
  so. A path nobody has classified is unclassified, not safe.
- **An interpreter as the final consumer is REFUSED, not rated (PL2), as a
  CLASS:** a pipe (or `&&`, or a first stage) into `sh`/`bash`/`python`/`perl`;
  an `xargs` CHILD that is an interpreter, with and without `-0`/`-I`; and an
  execution sink reached by REDIRECT. `sed` and `awk` still compose -- the line
  is "does stdin or a written file become code", not "is it powerful".
- **TM2-F8, nested quoting domains: CLOSED BY REFUSAL.** `su -c`, `sh -c`,
  `sudo`, `timeout`, `find -exec` and every other wrapper that re-parses its
  argument is refused as a stage. A second escaping domain gets its own quoter
  AND its own parsing oracle in the same commit or it does not exist
  (MCR-SEC-010's rule). `xargs` is the one re-parser present on purpose: it
  re-parses its INPUT STREAM, not its argv, and that stream is the producing
  stage's output, never a value from a form.
- **`null` on every incomplete case, and the panel names the stage (PL6).**
  `validatePipeline()` gives the UI the same decision per stage, with `ok` being
  `assemblePipeline()`'s own answer rather than a second opinion. A composer
  that refuses without saying which stage is wrong gets worked around in a text
  editor, and a worked-around gate is worse than no gate.
- **A pipeline of one stage equals `assembleCommand()` byte for byte**, asserted
  on every generator and every release (108 invariants).
- **The UI:** a `#pipeline-panel` with one writer, an operator `<select>` whose
  option VALUES are the closed table's keys and whose LABELS render the emitted
  text, stage add/remove/reorder/edit, and `Copy`, `Copy with comment` and
  `Export as Evidence` all acting on the WHOLE pipeline -- the clipboard header
  and the evidence export name every stage, its operator, its rating and its
  citation.
- **Gates:** Q18 extended to cover pipeline assembly explicitly, failing closed
  on zero pipeline checks, zero oracle negative controls, zero one-stage
  invariants or zero redirect-target rating checks; 8 new Q5 markers; the
  harness gains the pipeline oracle (589 comparisons, 11 negative controls) and
  17,092 hostile-vector pipeline checks; `tests/test_pipeline_stig_shapes.py`
  re-derives the ADR-002 expressibility measurement from
  `content/rules_rhel*.json`; `tests/test_pipeline_ui_wiring.py` (15 tests, 9
  audits, 14 negative controls) gates the panel. Harness 81,577 -> 101,297
  checks; unit tests 251 -> 293.
- **PIPE-F1 closed:** exact descriptor sinks `/dev/null`, `/dev/stdout`,
  `/dev/stderr`, `/dev/fd/1`, and `/dev/fd/2` rate green; other `/dev/**` paths,
  including `/dev/zero`, remain red. The allow-list is exact and is exercised by
  the hostile harness.

### Fixed

- **qa.py dist/ artifact-selection fail-open (AL-GATE3-001-class).**
  `find_artifact()` used to glob `dist/` for `md-code-red_*.html` and take
  whichever name sorted last -- post-release verification (DECISION_LOG
  2026-09-17, three incidents this cycle) found the dangerous direction: a
  stale artifact that merely sorted last and carried the CURRENT version
  string could be gated and PASS instead of the fresh build, since every
  downstream check only reads the file it is handed. `find_artifact()` now
  derives the one filename `build.py`'s own `APP_VERSION` names instead of
  listing the directory, so a stale file cannot be selected regardless of
  naming, dating, or sort order. New `dist_integrity_failures()` refuses to
  proceed at all -- before Q1 or any other gate runs -- if `dist/` holds any
  other `md-code-red_*.html`/`.sha256`/`.provenance.json` (named, with the
  cleanup command) or if the correctly-named artifact predates `build.py`,
  `template.html`, or anything in `content/`. `tests/test_provenance_manifest.py`
  carried the identical glob-and-sort-last duplicate for locating the
  artifact under test; it now imports `qa.find_artifact()` instead of
  re-implementing it. Proven with `tests/test_dist_integrity.py` (5 tests,
  committed failing against the pre-fix code, now green). Released artifact
  `dist/md-code-red_v1.0.0-alpha.1.*` (sha256 `0234322c...4001`) is unaffected
  and unchanged.

- **`rm -rf dist` silently broke the standing clean-rebuild recipe.**
  `dist/` has carried tracked release artifacts (the shipped `.html`, its
  `.sha256`, its `.provenance.json`) since v1.0.0-alpha.1 was tagged, but
  `build.py` does not regenerate all of them -- so `rm -rf dist`, the exact
  command `docs/QA_GATES.md`, `docs/WORKFLOW.md`, `docs/CODE_STANDARDS.md`
  and `docs/ARCHITECTURE_BIBLE.md` all documented as the standing clean-build
  step, deletes a committed file that stays gone until someone notices and
  runs `git checkout -- dist`. Left alone, `python3 -m unittest discover -s
  tests` then fails with an unhandled `FileNotFoundError` in
  `tests/test_no_raw_trojan_chars.py` rather than a clear message. Every
  documented instance of `rm -rf dist && python3 build.py` is now
  `git clean -fdx dist && python3 build.py` (`docs/QA_GATES.md` gained a
  "Clean rebuild" section explaining why: `git clean -fdx dist` removes only
  untracked files, so it can never delete a release artifact). Historical,
  dated entries in this file and in `README.md`'s "Recent changes" describing
  what was actually run at the time are left as written -- they predate the
  v1.0.0-alpha.1 tag that made `rm -rf dist` unsafe, and rewriting a dated
  record to say something different from what was literally run would
  misrepresent it. `qa.py`'s `dist_integrity_failures()` gained a third
  check: a git-tracked `dist/` file missing from disk is now refused by name
  with `git checkout -- dist`, distinct from the stray-file message (whose
  fix, `git clean -fdx dist`, is the wrong command for a missing file).
  `tests/test_no_raw_trojan_chars.py` no longer crashes on a git-tracked
  file absent from the working tree; it reports the gap as a clear,
  named `FAIL` instead. Proven fail-first against the real tree (a real
  `rm -rf dist/*.provenance.json` reproduced the crash before the fix and a
  clear FAIL after it). Released artifact unaffected and unchanged.
### Added — Grey Beard content port, part 3: the Ansible generators, and MCR-SEC-010 closed

`yamlQuote()` was deleted in the alpha on purpose. It was correct, it had no
call site, and Q18's quoting-domain gate was therefore passing on a domain
that did not exist — which read as "Ansible YAML output is proven safe" and
was not true. It was removed with one standing condition attached (Marcus
Reed's D3): **the sink, the quoter and a YAML-parsing oracle ship in the same
commit, or not at all.** This is that commit.

**The sink.** `composeDoc()` in the assembler block. A generator may now
declare a `doc` alongside its `template`, and emits two things: the command
the operator runs, and the FILE that command runs against. Three generators
use it, ported from Grey Beard's own `wireSimpleGens()`:

| generator | file | command |
|---|---|---|
| `gen-ansible-playbook` | `site.yml` | `ansible-playbook site.yml --limit='…' --check --diff` |
| `gen-ansible-inventory` | `inventory.yml` | `ansible-inventory -i inventory.yml --graph` |
| `gen-ansible-cfg` | `ansible.cfg` | `ansible-config dump --only-changed` |

Grey Beard's own playbook generator quoted only the play name, and its YAML
inventory generator interpolated group and host names into the document with
no quoting at all. Both go through the quoter here — including the mapping
KEYS, which is the half that was bare, because a key is a scalar too.

**The quoter.** `yamlQuote()`, its own escaping domain, sharing no code and no
idiom with `shQuote()`. A YAML single-quoted scalar has exactly one escape and
it is `''`; there is no backslash escape, so `shQuote()`'s `'\''` is not
merely cosmetically wrong in this grammar, it produces a different value that
does not parse. Uniform, with no bare-value branch: the only unquoted scalars
a file can contain come from a `bool` line, whose value is a JSON boolean in
the curated spec. **There is no path from a form field to a bare YAML scalar.**

**The oracle.** `parseYamlSubset()` and `parseIniSubset()` in
`tests/hostile_harness.js`, built the way `parseRichRule()` was built and for
the same reason: shell tokenisation proves a value sits inside one shell word
and says nothing about the grammar of whatever consumes that word. Every
emitted file is parsed and compared line for line against the operator's
intent — every value back out exactly as it went in, **every operator value
quoted** (a value that parses while sitting bare is not contained, it is
lucky), every curated boolean bare, and the line count unchanged so an
injected or absorbed line fails on the count.

**`ansible.cfg` gets no quoter, on purpose.** An INI entry has no escape
sequence for a value carrying a newline, a `;`, a `#` or an `=`. Inventing a
fourth escaper that cannot be written correctly is the mistake MCR-SEC-001
refused for rich rules, so this grammar gets the same two rules rich rules
got instead: a closed field-type allow-list (`comment` and `enum` deliberately
absent) and a closed character re-check at composition time. "There is no
quoter here" is itself a claim, so the harness drives **every** field type
into an INI value slot: 13 refused structurally, 12 allow-listed and parsed
back.

**What the gates do now.**

- Q18's SHELL-ONLY line is gone. It states two quoting domains and one grammar
  with none, checks no pair of `shQuote`/`yamlQuote`/`esc`/`escapeAttr` nests
  in either direction, requires sink + quoter + both oracles to be present,
  and **fails on a zero oracle count** — because a quoter whose oracle quietly
  stopped running is the same finding with the call site filled in.
- Q5's `yamlQuote(` marker is live rather than PENDING, joined by
  `composeDoc(` and `doCopyDoc(`. 65/65 markers, 0 pending.
- `docs/QA_GATES.md`: the Q18 row rewritten, the Q5 row says why that marker
  was pending, and MCR-SEC-010's finding row records how it closed.
- `extract/schema.py` gains `doc_errors()`: the build refuses what the runtime
  would refuse to compose. `tests/test_doc_spec_schema.py` (new, 20 tests)
  holds the two copies to each other — the INI allow-list, the key/lit
  patterns and the indent bound are compared against `template.html` directly,
  the way `test_schema.py` already compares `FIELD_TYPES`.

**Fail-first evidence**, run before this was committed:

| break | result |
|---|---|
| `shQuote()` substituted for `yamlQuote()` in the sink | harness: **40 failures** ("text after the closing quote") |
| quoter removed, value emitted bare | harness: **312 failures** ("unquoted value that is not a boolean") |
| `parseYamlSubset()` renamed away, quoter kept | harness refuses to run; **Q18 FAIL** |
| a `comment`-typed field wired into an `ansible.cfg` value | **build FATAL** at schema time |

Harness totals: 84,205 checks, 0 failures — 316 YAML-file and 60 INI-file
oracle checks, 36 generated-file structure checks (every doc generator, every
release, every combination of its optional fields, every enum branch), 100 INI
type checks, 88 invariants.

### Added — Grey Beard content port, part 2: the 23 Ansible entries, and the Ansible rail goes live

The Ansible rail in v1.0.0-alpha.1 rendered a paragraph beginning "This rail
lands with its own task". That paragraph is what "I don't see any git or
ansible content" was: a rail wired to a placeholder over a catalog with no
Ansible in it.

- 23 Ansible entries carried across from Grey Beard, in six categories:
  **Check before you run** (5: `--syntax-check`, `--check --diff`,
  `--list-hosts`, `--list-tasks`, `ansible-config dump --only-changed`),
  **Target fewer hosts** (5: `--limit`, host patterns, `--start-at-task`,
  `--step`, `--tags`), **Debug a failure** (5: `-m ping`, `-vvv`,
  `ansible-inventory --host`, `ansible-doc`, `fetch`), **Facts & inventory**
  (2: `--graph`, `-m setup -a filter=`), **Run & operate** (3: ad-hoc
  `--become -K`, `--forks`, offline `ansible-galaxy collection install`),
  **Vault & secrets** (3: `create`, `encrypt_string --stdin-name`, `rekey`).
- 7 new `content/tools.json` records: `ansible`, `ansible-playbook`,
  `ansible-inventory`, `ansible-doc`, `ansible-config`, `ansible-vault`,
  `ansible-galaxy`. All seven are available on all four RHEL releases and
  each says why: a control-node command is governed by the ansible-core
  version on the machine you run it from, not by the release of the hosts it
  reaches.
- **`renderToolList()` slices tools.json by category.** The Ansible rail
  renders the seven `ansible-*` tools; the Command Builder rail renders the
  other 41. One renderer, one escaping idiom, one keyboard contract -- a
  second hand-written list would be a second place to get Q17's audit rule
  wrong. The placeholder paragraph no longer names the Ansible generator as
  pending.
- **Flag explanations come from Grey Beard's generated ansible-doc
  dictionary** (`content/flags.json`, `extract/extract_ansible_doc.py`,
  ansible-core 2.21.1). Records whose text is a `--help` usage-line fragment
  rather than a description are not carried; the flag is dropped instead.
  Three subcommand options that no top-level `--help` dictionary can hold
  (`--graph`'s empty record, `--stdin-name`, `--only-changed`) carry an
  explanation taken from that entry's own Grey Beard notes, which name the
  flag and say what it does.
- `tests/test_ansible_rail.py` (new, 6 tests): the rail's slice is a silent
  failure mode -- a drifted category string renders an empty list that reads
  as "this build has no content" rather than as a bug. These assert both
  slices are non-empty, that every Ansible tool has at least one entry, that
  every `a-*` entry is reachable from the rail, that no Ansible tool is gated
  off a RHEL release, and that the placeholder prose the Founder read is gone.

### Added — Grey Beard content port, part 1: the 41 RHEL entries (CR-T-33 tranche)

The Founder's verdict on v1.0.0-alpha.1 was that the daily ground is not
there. It was not: the alpha forked the Grey Beard Ansible field kit's ENGINE
and left its CONTENT behind. This is the first half of bringing it across --
41 RHEL entries from `orbit/grey-beard-ansible` `content/commands.json`, the
same owner's own curated, Founder-used catalog.

- Ten categories the catalog had nothing in: **Disks & LVM** (7), **systemd &
  services** (5), **Networking** (4, plus chrony), **SELinux** (5),
  **firewalld** (2), **Users & sudo** (4), **Logs & journald** (3),
  **Packages** (4), **Processes & performance** (2), **Files & permissions**
  (4).
- 22 new `content/tools.json` records for the binaries those entries invoke
  (`lsblk`, `df`, `du`, `pvs`, `findmnt`, `mount`, `ip`, `ss`, `chronyc`,
  `getenforce`, `restorecon`, `id`, `last`, `visudo`, `logrotate`, `rpm`,
  `createrepo_c`, `ps`, `kill`, `find`, `tar`, `stat`). Every one declares
  availability on all four releases and says, in its note, that it was NOT
  part of the CR-T-09/10 host extraction -- so no flag dictionary covers it
  and none is implied.
- **Versions, honestly.** Grey Beard is single-version and was authored and
  used on RHEL 9, so RHEL 9 holds the concrete row and the other three point
  at it with `same_as` -- which, by `extract/schema.py`'s own rule, can never
  carry a verified receipt. `verified` is `false` on all four keys of all 41
  entries; nothing here has been run on a host by this project yet. Three
  releases are marked `unavailable` with a stated reason rather than guessed:
  `dnf` on RHEL 7 (it is yum's release), and `findmnt --verify` and
  `createrepo_c` on RHEL 7, where no staged RHEL 7 source and no RHEL 7 host
  establishes the invocation.
- **Flags are carried, never invented.** A flag token gets a curated
  `explain` only when Grey Beard's own `content/rhel_flags.json` carried one;
  otherwise it is `explain: null` and resolves through the shipped
  `flags_rhel8`/`flags_rhel10` dictionaries, or it is a non-option subcommand
  marked with a `license_class`. An option-shaped token with neither was
  DROPPED from the panel rather than given prose this port made up -- Q22's
  three honest shapes, and no fourth.
- **Licence class follows the citation.** Where this repository already
  stages the manual page, the entry cites `content-src/raw/rhel8/<bin>.man.txt`
  as `paraphrase-only` and Q14's 8-gram check runs against the real bytes.
  Where it does not, the entry cites the Grey Beard entry itself as
  `verbatim-ok` -- the same owner's own prose in his own repository, which is
  what it actually is, rather than a `paraphrase-only` claim pointed at a
  corpus this repository does not hold (`qa.py attestation_failures()` would
  then want a human receipt, and a receipt signed on someone else's behalf is
  worth less than an honest licence class).
- Five Grey Beard entries shipped as multi-line shell blocks
  (`r-nfs-mount`, `r-journal-cap`, `r-localrepo`, `r-tar-restore`,
  `r-kill`). Each is now one command, with the rest of the sequence written
  out in its notes: a multi-line command cannot compose a clipboard payload
  (`commentPayload()` returns null on a control character), and a
  `<placeholder>` in shipped text is a placeholder someone runs. `r-tar` lost
  its `$(date +%F)` for the same reason -- the command on screen is the
  command on the clipboard.
- `tests/fixtures/evidence/firewalld-service-active.rhel9.txt` regenerated:
  its content-fingerprint line moves because the data island did.

`dist/` is deliberately NOT re-cut on this branch. The committed artifact is
the released v1.0.0-alpha.1; re-cutting it belongs to a release commit, and
the gate order (`rm -rf dist && python3 build.py` first) builds it fresh
anyway.

## v1.0.0-alpha.1 — 2026-09-18 (lab-only alpha)

First internal alpha, released to SALM-controlled lab pilot hosts only.
**Not GA, not signed, not for distribution outside the lab.** Readiness
assessment `REL-2026-09-18-001`; ship authorization Eli Cross (CEO).

### What's in

- Command builders for 19 P0 tools across RHEL 7, 8, 9 and 10 (24 generator
  entries plus 3 STIG check entries): `systemctl`, `firewall-cmd`, `nmcli`,
  `dnf`/`yum`, `semanage`/`setsebool`, `useradd`/`usermod`, `chage`, LVM
  (`lvcreate`, `lvextend`), sshd config test, `journalctl`, `auditctl`/
  `ausearch`, rsyslog config test, chronyd offset check, `podman`.
- Every rule of the four pinned DISA STIGs embedded with check and fix text:
  RHEL 7 V3R15 (sunset, frozen), RHEL 8 V2R8, RHEL 9 V2R9, RHEL 10 V1R2 --
  1,492 rules, 200 CCI-to-NIST-SP-800-53 mappings.
- Version awareness: options shown only for the RHEL versions that have
  them, with a stated reason when a tool is unavailable (`dnf` and `podman`
  on RHEL 7).
- Per-version verification labels on every command: verified by QA on a
  named host, captured and awaiting QA, or documented and not host-verified.
- Export as Evidence: a deterministic plain-text block with STIG ID, title,
  CAT, CCIs, NIST controls, check and fix text, the assembled command,
  expected output where captured, source citation, and the content
  fingerprint.
- Keyboard-first shell, dark and light themes, search across tools, flags,
  STIG IDs, CCIs and controls, favorites and recent by ID, print view, About
  panel with attribution and source provenance.
- Content fingerprint: SHA-256 of the embedded data island, shown in About
  and in every export, recomputable from the file alone.

### Verification status, stated plainly

| Claim | Status |
|---|---|
| Commands executed on a real host and reviewed by QA | 18 entry-and-version pairs, all on RHEL 8 (Defiant 8.10) and RHEL 10 (Saratoga 10.2). |
| STIG rows with captured expected compliant output | 5, all compliant on the real hosts. |
| Entries with no capture on any version | 19 of 27. |
| RHEL 9 | No flag dictionary, no captures. Commands are documentation-sourced. |
| RHEL 7 | Flag dictionary from an unsubscribed UBI7 container covers 6 of 22 tools. No captures. Every RHEL 7 command reads "documented, not host-verified." The RHEL 7 STIG is sunset at DISA. |
| Flag explanations | Mostly "unverified, see man page." Curated explanations are authored later with citations. |
| Firewall-cmd flag coverage | 16 of 205 long options in the RHEL 8 dictionary, because of an extractor parsing gap. The accepted-gap baseline expires 2026-09-25 and the build fails after that date unless renewed. |

### Known limitations

- Only Chromium-class browsers were tested. Firefox ESR on RHEL and Edge on
  Windows are untested in this build.
- No Ansible or Git generators (P1).
- Multi-STIG-row entries export their first row only.
- The glossary content is not shipped in this alpha (see AL-GATE3-011
  below).
- No deploy receipt exists yet for the pilot jump box; Avery Quinn signs
  the first one.

### Operator rules

Full procedure: "MD CODE RED v1.0.0-alpha -- Pilot Standard Operating
Procedure." Lab-controlled hosts only; verify the artifact SHA-256 and the
content fingerprint against the release page before every use; never copy
the file into another accreditation boundary; do not paste alpha evidence
exports into a real body of evidence; report every wrong command.

### Fixed — Gate 3 tag blockers 1, 2, 4 and the glossary drop (2026-09-17/18, branch `salm/milo/gate3-blockers`)

Closes three of Al Kowalski's four `v1.0.0-alpha.1` tag blockers from the
whole-tree Gate 3 review (`ENG-2026-09-18-002`, §8.1) plus the Q20 RHEL 7
POA&M item folded into the same tranche. The version bump (blocker 3) is
Taylor's, in the tag procedure, and is deliberately not part of this change.

- **AL-GATE3-009 (tag blocker 1).** `content/flags_rhel9.json` declared
  `_meta.generator: "extract/extract_rhel_flags.py"` — a script that has
  never existed; the real extractor is `extract/extract_flags.py`, which the
  other three `flags_rhel*.json` correctly name. The same stale name was
  baked into `extract/make_pending_skeletons.py`'s own placeholder template
  (the true generator of record while `flags_rhel9` stays empty), so both
  are corrected together. `qa.py`'s Q8 and Q15 never checked a FLAGS
  dataset's declared generator against anything — both now do, against all
  four `flags_rhel*.json`, naming the offending dataset by name if one ever
  declares a generator neither gate re-runs.
- **AL-GATE3-010 (Q20 RHEL 7 reach, POA&M, ratchet retires 2026-09-25).**
  `qa.py`'s `RAW_DIR_FOR` was `{"8": "rhel8", "10": "rhel10"}` — RHEL 7 was
  absent, so `content-src/flag_coverage_baseline.json`'s six `coverage["7"]`
  rows were read by nothing. Adding `"7"` alone would have measured nothing:
  `_long_options_in_raw()` filtered raw captures to `.man.txt`, and every
  RHEL 7 dump is `.help.txt` (UBI7 has no man-db — CR-T-12). Both are fixed:
  `RAW_DIR_FOR` now includes `"7": "rhel7"`, and the filter reads both
  suffixes. Q20 now measures 50 tool/release pairs (up from 44). The
  baseline's pre-recorded `accepted_missing` counts were not widened — they
  already covered the real RHEL 7 measurement (per the file's own
  `_rhel7_note`), so Q20 still reports zero failures under the existing
  owner and date (Caleb Stone, retires 2026-09-25).
- **AL-GATE3-011 (tag blocker 2) — the glossary is dropped for the alpha,
  CEO decision.** `content/glossary.json` (9.5 KB) shipped embedded in the
  data island, bound to `DATASETS.GLOSSARY` in `template.html`'s data-island
  loader, and read by nothing — no Glossary kind in the search index, no
  rail, no panel, no renderer. `build.py`'s `CONTENT` map no longer embeds
  it. **`content/glossary.json` stays committed in the repo, unchanged, for
  a later tranche** that wires a real glossary view (see
  `docs/ARCHITECTURE_BIBLE.md` §25 for what that would need) — this is a
  drop from the shipped artifact, not a deletion of the content. `qa.py`
  gained `content_family_liveness_failures()` (wired into Q8): every
  embedded `CONTENT` family must be referenced by the shipped app script
  beyond its own `DATASETS` assignment, or named as a documented exception
  (`expected_output`'s raw copy is redundant with the copy `build.py` joins
  onto `RULES` before the island is built, so it is exempt rather than
  orphaned). This is the check that would have caught AL-GATE3-011 on its
  own, and now would catch a regression back to embedding an unreferenced
  family without a renderer to justify it. Artifact effect: −9.2 KB
  (2,471,131 → 2,461,910 bytes); content fingerprint and artifact sha256
  both change, expected for any content change to the embedded island.

Gates after this change: `build.py` rc 0, `qa.py` rc 0, unit tests green,
`tests/hostile_harness.js` 0 FAILED. `tests/fixtures/evidence/firewalld-
service-active.rhel9.txt`'s embedded "Content fingerprint" line was
regenerated from the rebuilt artifact each time the island's sha256 moved
(the flags_rhel9 fix, then the glossary drop) — via the same
`buildRealExport()` path `test_evidence_export_real.js` uses, not hand-edited.

- **AL-GATE3-015 a/b (tag blocker 4) — `ci.yml` and `docs/QA_GATES.md` said
  the wrong gate range.** `.forgejo/workflows/ci.yml`'s two `"Q1-Q18"`
  strings (the header comment and the QA-gate step name) are corrected to
  `Q1-Q22 + JS`, the range `qa.py`'s own `GATES` list actually runs today.
  `docs/QA_GATES.md` gained the missing **Q22** row (declared tool is the
  invoked binary, every flag resolves/is curated/is honestly marked --
  Marcus Reed's PANEL-001 / condition G1) and its header count is corrected
  to Q1-Q22 + `JS`, 23 rows. Scope note: this pass touches only the Q22 row
  and the header line it invalidates -- the Q20 "44 tool/release pairs" and
  Q21 "226 tracked files" figures elsewhere in that document are separate,
  pre-existing drift (the former stale as of this same tranche's AL-GATE3-010
  fix, now 50 pairs; the latter already stale before it, `git ls-files | wc -l`
  is 271+) and are Sam's docs-alpha lane's to correct, not touched here.
- **Traceability notes (AL-GATE3-013, AL-GATE3-014a).** Recorded here since
  no board row exists yet for either: **CR-T-27** (`extract/build_cci_map.py`,
  a filtered CCI-to-800-53 map) was never built and never cited: its
  deliverable is produced instead by `extract/parse_xccdf.py` (`:398`) under
  **CR-T-07**, with 200 mappings filtered from the 5,137-item DISA CCI list,
  re-checked independently by Q11 -- one parser, one pin verification, one
  `--check` path, by architect ruling (Gate 3 review, 2026-09-18). **CR-T-31**
  (print view) and **CR-T-32** (About panel) both shipped, correct, under
  commit `163b20f`, whose subject cites `CR-T-26/28/29/30` -- neither ID was
  ever cited by any commit. Zee's board still needs CR-T-30/31/32 formally
  reconciled and a row opened for the nine-commit verified-per-version
  tranche (`HL-verified-per-version`); that reconciliation is Zee's, not
  done here.

### Fixed — Q14 widened to every curated free-text field, per-field license_class, guide receipt (2026-09-17, branch `salm/milo/q14-scope`)

Self-flagged by Milo Vance during H1: Q14's shingle check scanned only
`rhel_versions[].notes`, `.changed_in_note.what` and `flags[].explain`, and
decided whether to check an entry AT ALL by reading `entry.source.license_class`
once, before `curated_texts()` ever ran a single field. Caught by hand during
H1 (a paraphrase-only man-page sentence pasted into a curated field, since
reworded); this tranche closes the class of gap rather than the one instance.

- **Field coverage.** `intent`, `verify`, `undo` — the same clipboard-header
  fields `notes` and `flags[].explain` sit beside (`extract/schema.py`
  `HEADER_BOUND_FIELDS`, mirrored rather than imported: `qa.py` stays
  stdlib-only and keeps its own independent read of the content, same
  reasoning as Q8..Q11's own XCCDF parse) — had no check at all. Neither did
  a generator spec's `fields[].label`/`.help` (the form-facing UI copy on a
  `"template" in e` entry, no `type` restriction, exactly where a pasted man
  page sentence would land) or `stig[].notes` (not in the schema today;
  added defensively so a future one is not a silent hole).
- **Per-field license_class, not per-entry.** The real gap the 27-entry audit
  found: `firewalld-service-active`, `journald-service-active` and
  `ctrl-alt-del-target-masked` all cite a verbatim-ok DISA STIG at
  `entry.source`, but carry individual `flags[]` marked
  `license_class: paraphrase-only` (systemctl's `status`/`is-active`
  behaviour is documented, not STIG text). Under the old entry-level filter
  those flags' `explain` text was never read at all — a verbatim lift there
  would have shipped clean. `curated_texts()` now returns `(text,
  license_class)` pairs; a flag's own `license_class` overrides its entry's
  when present, everything else stays governed by the entry's.
- **Guide-citation offline mechanism (the decision this tranche made).** Q14
  stays a pure offline check against `content-src/raw/` — no reach to the
  corpus mirror on saratoga, which is not in this repo and not available
  air-gapped (the same reasoning `gate_q15`'s own docstring already gives for
  refusing a live-host dependency). A paraphrase-only entry whose
  `source.url_or_man` is not a `man ...` reference or a `content-src/raw/`
  path (`source_is_offline_checkable()` — i.e. it names a Red Hat guide,
  which this repo does not stage: copying guide prose into `content-src/`
  just to shingle-check it would itself be the verbatim embedding the
  licensing ruling exists to prevent) now requires a `source.
  paraphrase_attested_by {by, on}` receipt, checked against `content-src/
  roster.json`'s QA role through the same `normalize_person_name()`/
  `load_roster()` two-person-rule infrastructure `gate_q16` already uses
  (`attestation_failures()`). None of the 27 shipped entries hit this path —
  every one cites a staged man page or a DISA STIG — so this is forward cover
  for the first entry that cites a guide directly, not a change to what
  ships today.
- **Audit.** All 27 shipped command entries re-checked under the widened
  gate: **0 collisions, 0 entries need a `paraphrase_attested_by` receipt.**
  Every paraphrase-only entry's prose, including the three flag-level
  overrides above, genuinely paraphrases its cited man page.
- **Fail-first.** `tests/test_paraphrase.py` widened from 15 to 33 cases —
  `TheWidenedFieldsAreCaught`, `TheFlagLicenseClassOverride`,
  `TheChronydNearMiss` (the H1 incident re-created deterministically from
  `content-src/raw/rhel8/chronyd.man.txt`, plus a check that the real
  `gen-chronyd-one-shot-check` entry is clean) and `TheGuideAttestationReceipt`.
  Committed red at `23d340c` against the unwidened `qa.py`
  (`python3 -m unittest tests.test_paraphrase`: Ran 33 tests, FAILED —
  failures=9, errors=6, skipped=2); green after the `qa.py` fix at `de5c21d`
  (Ran 33 tests, OK, skipped=2 — the two end-to-end `TheWholeGate` cases,
  which need a `dist/` build).

### Fixed — Q16 closes J1/J2/J3, the Verified-per-version review's conditions (2026-09-18, branch `salm/milo/receipt-guards`)

Marcus Reed's Verified-per-version review (VER-001/002/003) approved the per-version receipt
schema with three conditions — all guard gaps, no live false claims: every one of the 18
shipped receipts was accurate today, but three guards behind them were narrower than they
looked.

- **J1 (MED, VER-001)** — `qa.py` Q16's drift check exempted generator entries outright
  (`if "template" not in e:`), so 12 of the 18 receipts had no binding to the command the build
  actually assembles: a template edit could change what a generator emits without invalidating
  any receipt that described the old behaviour. `gate_q16()` now diffs a generator receipt's
  `capture.command_as_run` against `tests/fixtures/golden-commands.json` for that
  entry/version — the same hand-authored validity oracle `tests/hostile_harness.js` already
  holds generators to. Fail-first: `tests/test_q16_receipts.py::Q16GoldenTableBinding` (4 cases)
  reproduces the gap directly against `gate_q16()` — a missing golden table, a missing row, and
  a template-drift case shaped exactly like Marcus's own repro (`gen-journalctl-unit-logs`
  template `+= {lit:"--extra"}`) — all three red against `qa.py` at
  `848fe7aae89de0f528f0507a37e0d08e343b0ce8d67b889936ef8655b58e4c06`, green after the fix.
  Content debt this exposed and closed in the same fix: `gen-chage-list`'s golden row was
  pinned to `username: svcacct`, which does not exist on either lab host — the real,
  receipted capture ran `adm-linux` instead (documented in the capture's own
  `field_substitutions`). The golden row is now pinned to the value that was actually,
  verifiably run; the other 5 generator receipts already matched their golden rows exactly.
- **J2 (MED, VER-002)** — the two-person rule was `by == captured_by`, byte-for-byte. Eight of
  Marcus's nine hostile variants bypassed it (lowercase, uppercase, leading/trailing space, a
  doubled space, a non-breaking space, and a trailing `"(SME)"` parenthetical); the ninth,
  a deliberate alias (`"C. Stone"`), cannot be closed by any string comparison of names at
  all — no normalisation rule catches someone who chooses to write a different name. Both
  names are now normalised (`normalize_person_name()`: casefold, collapse all Unicode
  whitespace including NBSP to one space, strip one trailing parenthetical) **and** checked
  against a new closed roster, `content-src/roster.json` (Caleb Stone and Renata Osei as SMEs,
  Riley Park as QA, extensible as intake lands) — `receipt.by` must hold the QA role,
  `capture.captured_by` must hold the SME role. The gate's own PASS diagnostics now state the
  residual in words, the way Q17's and Q20's already do: the deliberate-alias path is closed
  because the name fails to resolve against the roster, never because it is detected as an
  alias of a real person. Fail-first: `tests/test_q16_receipts.py::Q16TwoPersonRoster` (8 cases,
  including all nine of Marcus's variants via a `subTest` sweep) red against `qa.py` at
  `369ebc5a67c5961ef90200d2c3740c19a2dd7dd86a9a96e9186217593c61ac41`, green after the fix.
- **J3 (LOW, VER-003)** — a receipt's `host` and `capture` fields were free text with no closed
  grammar; a hostile capture path only happened to fail because the named file did not exist on
  disk, not because its shape was refused, and a hostile `host` string passed outright.
  `RECEIPT_HOST_RE` (`^[a-z0-9][a-z0-9.-]{1,62}$`, the app's own hostname-field grammar, reused)
  now gates `host`; `RECEIPT_CAPTURE_PATH_RE`
  (`^tests/captures/(7|8|9|10)/[a-z0-9-]+\.json$`) now gates `capture`, closing markup and
  `../` traversal; a receipt's `host` must also equal its own capture record's `host`. `by`'s
  grammar is the roster itself (J2) — no separate rule needed. Fail-first:
  `tests/test_q16_receipts.py::Q16ClosedGrammars` (4 cases: `<img src=x onerror=alert(1)>` in
  `host` and in `capture`, a `../../../etc/passwd.json` traversal, and a `host` that disagrees
  with its capture's own `host`) red against `qa.py` at
  `c178987a5611d57221dc4dab7c7f05849313614968247bade9cdb1f5be41d9ac`, green after the fix.

`tests/test_q16_receipts.py` grew from 4 to 21 cases. Full gate green throughout, rechecked at
every commit: `rm -rf dist && python3 build.py && python3 qa.py` -> QA GATE: PASS, artifact
sha256 unchanged at `bb950d9088060ed619c5e1178cc128b9b91d69d9240e9847001d1963573a9f06`;
`python3 -m unittest discover -s tests` -> 204 tests OK (was 187); `node
tests/hostile_harness.js` -> 81577 checks, 0 FAILED, byte-identical to the prior three
tranches — this change touches `qa.py`, `content-src/roster.json` (new) and
`tests/fixtures/golden-commands.json` (one content correction) only; the shell, the assembler
and the data island are untouched.

### Changed — `verified` is per RHEL version, not per entry (2026-09-17/18, branch `salm/milo/verified-per-version`)

CEO ruling closing Riley Park's first capture review (`capture-review-run1-2026-09-18.md`
RILEY-F1): a single whole-entry `verified` flag could not be set `true` for any of the 9
entries Caleb Stone's CR-T-34 run captured without overclaiming an RHEL version nobody ran the
command on (every one of them declares applicability to at least one version that was not
captured that night). `content/commands.json`'s `verified` field is now an object keyed
`"7"`/`"8"`/`"9"`/`"10"`, each value `false` or a `{by, on, host, capture}` receipt.

- **Schema** (`extract/schema.py`): `verified_errors()` rejects the old whole-entry boolean
  outright and requires all four RHEL keys on the new object, each `false` or a receipt. A
  version whose `rhel_versions` row is `unavailable` or a `same_as` pointer — or, for a
  generator spec, a version its own `versions` list excludes — can never carry a receipt of its
  own: it was never independently run on that version, and a `same_as` TARGET's receipt does
  not propagate onto the version pointing at it. `entry_has_any_receipt()` replaces the old
  `bool(entry.get("verified"))` check everywhere a "has this entry been claimed verified at
  all" test is needed (the flags-must-be-curated rule, most notably — a per-version object
  with every value `false` is truthy but claims nothing).
- **Migration**: all 27 entries' `verified: false` became `verified: {"7": false, "8": false,
  "9": false, "10": false}`. Two entries' RHEL 10 row (`firewalld-service-active`,
  `journald-service-active`) was promoted from a `same_as` pointer to its own concrete `command`
  (identical text; the same_as pointer was authored before either version was independently
  run) after Caleb Stone's CR-T-34 capture on `saratoga-rhel10` proved RHEL 10 genuinely was run
  on a real, distinct host — a same_as row can never carry its own receipt, and this version now
  has one to carry.
- **`qa.py` Q16** (`gate_q16`): a per-version receipt is now checked against its OWN capture
  file (the receipt's `capture` field) rather than only the STIG-keyed `expected_output.json`
  index (which does not cover the 6 of 9 batch entries with no STIG mapping): the capture must
  be for the exact (entry, RHEL version) pair, its `command_hash_at_capture` must match
  `sha256(command_as_run)`, its `command_as_run` must still match the command this build
  actually assembles for that version (content edited since capture now drifts this gate red
  instead of silently passing), and the receipt's `by` must not equal the capture's
  `captured_by` — the SME who captured it can never be the QA reviewer who verified it.
- **`same_as` chain resolution** (Riley Park's RILEY-F5): `extract/import_captures.py`'s own
  one-hop-only `resolved_command()` — which silently skipped the "edit resets verified"
  integrity check for a two-hop chain's far end (`firewalld-service-active`'s real RHEL
  10 -> 9 -> 8 chain, at the revision she reviewed) — now delegates to
  `extract/schema.py`'s `resolved_command()`/`resolve_chain()`, which resolves a chain of any
  length with a cycle guard. One resolver, not two that can drift apart.
- **Riley Park's 18 receipts** (capture-review-run1-2026-09-18.md §4) written into
  `content/commands.json`: `firewalld-service-active`, `ctrl-alt-del-target-masked`,
  `journald-service-active`, `gen-ausearch-by-key`, `gen-chage-list`,
  `gen-journalctl-unit-logs`, `gen-podman-ps`, `gen-rsyslogd-test-config`,
  `gen-systemctl-query` x RHEL 8 (`defiant-rhel8`) and RHEL 10 (`saratoga-rhel10`) — 18
  entry/version pairs, each `{"by": "Riley Park", "on": "2026-09-18", "host": "...",
  "capture": "tests/captures/<v>/<entry_id>.json"}`. Two `flags[].explain` values
  (`firewalld-service-active`/`ctrl-alt-del-target-masked`'s `status`, `firewalld-service-
  active`/`journald-service-active`'s `is-active`) were curated to close the resulting "a
  verified entry must carry a curated explain for every flag" schema check, paraphrased from
  `systemctl(1)` with no 8-gram collision against the staged raw corpus (Q14).
- **UI** (`template.html`): a new `verificationStatusForVersion(entry, version)` helper is the
  one place entry/version verification state becomes the three states the UI shows — "verified
  by NAME on DATE (HOST)" for a receipted version, "captured, awaiting QA" when a STIG-joined
  capture exists with no receipt yet, "not host-verified" otherwise. Used by the Inspector (a
  new "Verification" region above "Flag by flag"), the evidence exporter (`formatEvidenceText()`
  prints the receipt line for the EXPORTED version only, never every version the entry
  carries), and the status bar (a badge next to "RHEL N" reflecting the selected entry's state
  for the selected version).
- **Docs**: `tests/captures/README.md`'s stale `WADE_BLOCKED` section (reporting that
  `extract/import_captures.py` did not exist) is replaced with the resolved canonical path and
  the SME-captures/QA-verifies per-version flow; `docs/WORKFLOW.md` §2a documents the same flow
  and notes, for Riley/Caleb and not edited here, that the company-record protocol document
  (`test-plan-skeleton-v1.md` §7) should add `command_hash_at_capture` and `verify_result` to
  its written field table to match what the code has gated on since CR-T-34.

Fail-first: `tests/fixtures/schema/invalid/verified_true_without_receipt.json` (old boolean),
`verified_receipt_on_unavailable_version.json` and `verified_receipt_on_same_as_version.json`
(new), plus a Q16 capture-backing case and a two-hop same_as drift case — each asserted failing
before its fix landed. See the branch's own commits for the failing-then-passing hashes.
### Added — CR-T-12: the RHEL 7 flag dictionary, from a UBI7 container (2026-09-17, branch `salm/milo/flags-rhel7`)

There is no RHEL 7 host in the lab. Under the Founder's delegation (DECISION_LOG 2026-09-18), a
rootless UBI7 container on saratoga (RHEL 10.2) stood in as the RHEL 7 source:
`registry.access.redhat.com/ubi7/ubi:latest`, digest
`sha256:046e525722f14702c360dc6092324af7c21656e76b0c254b067871f1d4d3df68`. No sudo, no host
package installs, no host configuration changes; the container was removed after extraction, the
image kept.

**Extractor.** `extract/extract_flags.py` gained `--container` (plus `--container-image` /
`--container-image-digest`, recorded into `_meta` only): `ssh_run()` now wraps every one of its
already-read-only commands (`man -P cat`, `<tool> --help`, `rpm -qf`, `command -v`) one hop
further in, through `podman exec <container> sh -c '...'` on the named `--host`, instead of the
alternative of teaching the whole extractor to run inside the container against localhost — the
container has no Python, would need the script copied in, and would write raw captures inside the
container's own ephemeral filesystem instead of straight into this repo's `content-src/raw/`. The
`--host`/`--rhel` cross-check (`HOSTS[host]["rhel_version"] != rhel`) is skipped when `--container`
is given, since the container's guest OS, not the SSH host's, is what's being read. `_meta.host` is
written as `"ubi7 container on saratoga"` (never the bare host alias, so a RHEL 7 dictionary never
reads as if saratoga's own RHEL 10 were the source), and a new `kernel_caveat` field says plainly
that the `kernel` field is the container's shared HOST kernel (containers don't have their own) and
that kernel- and systemd-manager-dependent behaviour was NOT observed or exercised — only each
tool's own `--help`/man text as shipped in its package. No other function changed; every existing
direct-host extraction (`defiant`, `saratoga`) is byte-for-byte unaffected (`--container` unset,
`CONTAINER_EXEC` stays `None`).

**What the container could actually provide.** UBI7's public repos (`ubi-7`, `-optional`,
`-extras`, `-rhscl` — 240 packages total, no subscription) do not carry `man`/`man-db` at all, so
every tool here is `--help`-only (no man pages exist to install). Of the 22 P0 tools, 6 already had
a binary in the base image or installed cleanly from those repos — `systemctl`, `journalctl`
(systemd), `yum` (base image), `useradd`/`usermod`/`chage` (shadow-utils) — and were extracted.
The other 16 could not be, and are recorded `available: false` with the real reason, the same
honest treatment `podman`/`dnf` already get for genuinely not existing on RHEL 7: `firewalld`,
`NetworkManager`, `lvm2`, `audit`, `rsyslog`, `chrony`, `policycoreutils-python(-utils)` are not
in UBI7's public repos at all (they live in RHEL 7 Base/Extras channels UBI's CDN does not mirror);
`openssh-server`/`openssh-clients` and `git` resolve in `ubi-7` but their dependency chains
(`libfipscheck`, `libedit`, `perl` and its sub-modules) do not — nothing to `--skip-broken` around
without pulling in packages from outside the public UBI7 channel, which was out of scope (no other
source, no subscription-manager registration). `dnf` and `podman` are correctly `available: false`
for RHEL 7 itself (neither ever shipped there).

**Coverage baseline.** `content-src/flag_coverage_baseline.json` gained a `coverage["7"]` block
for the 6 available tools (same method as the RHEL 8/10 rows: distinct long options in the
committed raw capture vs. the dictionary, `accepted_missing` set to the honest gap at authoring
time) and a `_rhel7_note` explaining two things: (1) `qa.py`'s Q20 `RAW_DIR_FOR` is hardcoded to
`{"8": "rhel8", "10": "rhel10"}` and was not extended to `"7"` — Q20 does not gate RHEL 7 coverage
yet, so this block does not widen anything Q20 checks; it is recorded for the same reason the RHEL
8/10 rows were, and for whoever extends `RAW_DIR_FOR` next. (2) `firewall-cmd` is absent from the
block: `firewalld` isn't installable from UBI7's public repos, so there is no RHEL 7 firewall-cmd
capture to have the RHEL 8/10 synopsis-line regex gap (`README.md`'s Content authoring note) show
up in — the gap is very likely present on RHEL 7 too (it's in the parser, not the host), just not
observable with this source. Same ratchet owner and date as the rest of the file: Caleb Stone,
retires 2026-09-25 — no separate date invented for RHEL 7.

**`qa.py` Q15 (the one change outside `extract/` this task made, and it says so as instructed):**
its FLAGS special case filtered `flags_rhel8.json`/`flags_rhel10.json` out of
`make_pending_skeletons.py`'s drift report because those two were real data being diffed against
an empty-placeholder script; `flags_rhel7.json` needed the same filter now that CR-T-12 populated
it too, so `flags_reextracted` gained `"flags_rhel7.json"` and the offline `--check --rhel <v>`
re-parse loop gained `"7"` (docstring updated to match; RHEL 9 stays with the placeholder script,
unaffected, pending CR-T-11). Without this, Q15 fails permanently the moment the RHEL 7 dictionary
stops being empty — not a host-abstraction change, but the same one-line pattern CR-T-09/10
already established, now extended a third time.

`tests/fixtures/evidence/firewalld-service-active.rhel9.txt`'s committed `Content fingerprint` line
updated to match: the data island's sha256 changed because `flags_rhel7.json` grew real content
(38 flags, 90 unparsed hints across 6 tools), not because the entry's own command, flags or
citation changed — confirmed by diffing the real export before and after; every other line is
identical.

Gates: `build.py` reproducible (identical sha256 from a clean copy of `content/`+`content-src/`+
`extract/`+`build.py`+`template.html`+`stig-src/`) / `qa.py` (Q1-Q22, JS: PASS) /
`python3 -m unittest discover -s tests` (176 OK) / `node tests/hostile_harness.js` (81577 checks,
0 FAILED) all green.

### Fixed — H1/H2/H3: pre-merge corrections from Marcus Reed (2026-09-17, branch `salm/milo/panels-conditions`)

Three conditions raised before this branch merges, all against work already on it.

#### H1 — `gen-chronyd-one-shot-check` was wrongly raised to yellow

G4(d) raised `gen-chronyd-one-shot-check` to `blast: "yellow"` on Caleb Stone's CR-T-34 capture
run note that `chronyd -Q` "steps the system clock" — a misreading of `chronyd(8)` that an
earlier ruling repeated and this branch then encoded into content, intent and notes.

**Correction, from the pinned man page itself** (identical text on RHEL 8 and RHEL 10,
`content-src/raw/rhel{8,10}/chronyd.man.txt#L64-L74`):

> `-q` — When run in this mode, chronyd will set the system clock once and exit.
> `-Q` — This option is similar to the `-q` option, except it only prints the offset without
> making any corrections of the clock and disables server ports to allow chronyd to be started
> without root privileges.

This toolkit only ever generates `-Q`. `blast` reverts to `"green"`; `intent`, `verify`, `undo`
and `notes` are rewritten to say what the man page actually says, with the lines cited (`verify`
and `undo` were ALSO wrong before this branch ever touched the entry — both said "the step it
applied"/"performs one correction", the same `-Q`/`-q` conflation, predating G4(d)).
`tests/fixtures/golden-commands.json`'s `blast` field matches.

New assertions in `tests/test_blast_state_change_labels.py`
(`test_chronyd_one_shot_check_is_not_matched_and_stays_green`): the entry is not matched by the
state-changing sweep, declares green, and none of `intent`/`notes`/`verify`/`undo` claim `-Q`
steps the clock. Committed failing first (content still said yellow with the wrong claim), then
the content fix.

#### H3 — anchor the state-changing pattern table

The same file's `STATE_CHANGE_RE` matched its bare words (`install`, `remove`, `add`, `del`,
etc.) as a plain substring — which meant `gen-nmcli-static-ipv4` was flagged only because
`ipv4.addresses` contains the letters "add", and `gen-useradd-create` only because `useradd`
does. Neither command has a real `add` token; both entries stayed correctly labeled by accident
(already yellow for other fields), but the sweep was never proving what it claimed to for them.

`STATE_CHANGE_RE` now matches the bare-word entries with `\b` word boundaries and keeps
`--permanent` as a literal substring (distinctive enough that a false hit inside another flag is
not a realistic risk the way a 3-letter bare word is). `-Q` is also removed per H1. New negative-
case tests (`test_word_boundary_anchoring_excludes_substring_false_positives`) prove `del`/`add`
no longer fire inside `--delete`, `userdel`, `--address`, or `ipv4.addresses`; a companion
positive-case test (`test_word_boundary_anchoring_still_matches_real_tokens`) proves the
anchoring did not overcorrect into matching nothing.

#### H2 — one shared invisible-character range table

G2's evidence-export line-safety treatment (`evidenceHeaderSafe()`/`evidenceLineSafe()`) kept its
own hand-rolled numeric range table instead of sharing `MCR-ASSEMBLER`'s existing `INVISIBLE_RE`
(the range `MCR-SEC-004` already refuses in curated field values) — and that copy had already
drifted, missing `U+061C` (Arabic Letter Mark), `U+00AD` (soft hyphen), `U+206A`–`U+206F`
(deprecated text-direction/digit-shaping controls — it only went to `U+2069`), and all of
`U+FE00`–`U+FE0F` (variation selectors — it covered none).

**Fix: one shared table.** New `INVISIBLE_RE_G` — a global-flagged twin of `INVISIBLE_RE`,
defined once, immediately after it. `headerSafe()` (`MCR-SEC-003`'s clipboard comment header) is
widened to also strip it, applied AFTER the existing control-character pass so `\n`/`\r`/
`U+2028`/`U+2029` keep becoming a space exactly as before (`INVISIBLE_RE` also lists those two in
its own class; stripping first would have removed them outright instead of spacing them, and
`tests/hostile_harness.js` already has an invariant pinning the old behavior —
`headerSafe("a\nb\r\nc\u2028d") === "a b c d"` — which this fix keeps true by ordering, not by
exception). `evidenceHeaderSafe()` drops its own range tables entirely and does the same two
replacements minus the whitespace-collapsing step this export's own content needs to keep.

New `tests/test_evidence_invisible_coverage.js`/`.py`: lifts `INVISIBLE_RE` and
`evidenceLineSafe()` together out of the built file and enumerates every BMP codepoint
(`U+0000`–`U+FFFF`, surrogates excluded) against it — the codepoint list is read fresh from the
shipped regex every run, never hand-copied, so the two tables cannot silently diverge again
without this test catching it. Committed failing (35 of 58 codepoints `INVISIBLE_RE` rejects
survived `evidenceHeaderSafe()` unchanged), now 0.

`tests/test_evidence_export.js` is updated to lift `MCR-ASSEMBLER` alongside `MCR-EVIDENCE` —
`evidenceHeaderSafe()` now depends on `INVISIBLE_RE_G`/`HEADER_UNSAFE_G` from the assembler block,
so `MCR-EVIDENCE` is no longer self-sufficient lifted alone, on purpose (both
`tests/test_evidence_export_real.js` and the new coverage test already lifted both blocks
together, so liftability-alone was never a reason to keep two copies of the same table).

Gates: `rm -rf dist && python3 build.py && python3 qa.py && python3 -m unittest discover -s tests
&& node tests/hostile_harness.js` — 22/22 gates PASS, 176 unit tests PASS (171 + 5 new), hostile
harness 81,577 checks / 0 FAILED, including the `MCR-SEC-003` line-terminator invariant and the
140 enum-branch control checks (Marcus Reed's sweep, MCR-SEC-021, still green against the
corrected labels).

### Added/Fixed — G4: capture import, blast labels, privilege field (2026-09-17, branch `salm/milo/panels-conditions`)

Continuing on the same branch after G1-G3, from Caleb Stone's first content validation run
(`tests/captures/README.md`, branch `salm/caleb/captures-green`, cherry-picked `1db0b97`/`924f589`
to keep his authorship — his branch itself was not touched). Four rulings from Eli Cross.

#### (a) Canonical capture path

Three documents disagreed on where a capture record lives: `extract/make_pending_skeletons.py`'s
own docstring said `content-src/captures/` (written before any real extractor existed for this
file family); the content validation protocol document
(`07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md` Part B §7/Appendix) proposed a separate
`07_QA_Test/MD_CODE_RED/captures/` tree; Caleb's actual run task instructions put the files at
`tests/captures/<rhel_version>/<entry_id>.json`, which is where they actually are.

**Ruling: `tests/captures/<rhel_version>/<entry_id>.json`, in the `md-code-red` repo, is
canonical.** `extract/make_pending_skeletons.py`'s docstring is fixed. The protocol document's
"Record format" paragraph and Appendix file-layout diagram are fixed to state the repo path
explicitly and describe themselves as a company-record pointer to it, not a second storage
location — capture records live next to the extractor and the gate that read them, reviewable
in the same PR as the content entry they validate.

#### (b) Capture record field names

`qa.py`'s `gate_q16` checked capture records for fields
(`host`, `os_release`, `kernel`, `patch_level`, `command_run`, `exit_code`, `stdout`,
`captured_on`, `captured_by`) that no real capture record — Caleb's or the protocol's own worked
example — has ever carried.

**Ruling: the content validation protocol's own §7 schema is the field-name authority; `qa.py`
adapts to it, not the reverse.** New `CAPTURE_REQUIRED_FIELDS` in `qa.py` (also
`extract/import_captures.py`'s `REQUIRED_FIELDS`, kept textually identical across the two files):
`entry_id`, `rhel_version`, `host`, `redhat_release`, `kernel`, `pkg_versions`, `command_as_run`,
`exit_code`, `stdout`, `stderr`, `captured_on`, `captured_by`, `blast_confirmed`,
`undo_executed`, plus `command_hash_at_capture` and `verify_result` — present on every real
capture file though not in the written protocol text, folded into the authoritative set by the
same ruling. `template.html`'s `formatEvidenceText()` (MCR-EVIDENCE) and the STIG panel are
fixed to read these real names (`cap.redhat_release`, `cap.stig_compliance.compliant`) instead
of a shape no capture record ever had — without this fix, Caleb's real captures would have
rendered "not captured"/"not recorded" for release and compliance even with Q16 green.

#### (c) `extract/import_captures.py`

The extractor `content/expected_output.json`'s own `_meta.generator` had always named — and
that Caleb's run reported as `WADE_BLOCKED` because it did not exist — is now written.

Walks `tests/captures/`, validates every record against the §7/`command_hash_at_capture` field
set. **Integrity rule** ("so an edited command resets to uncaptured"): `command_hash_at_capture`
must equal a fresh `sha256(command_as_run)`, and for an entry whose command is a FIXED
`content/commands.json` `rhel_versions[version].command` (never a generator's — MCR-SEC-006, a
generator composes its command from validated form input, so there is no single "current"
command to diff a capture against), that command must equal `command_as_run` byte-for-byte,
resolved the same way `build.py`'s `assemble()` resolves a `same_as` pointer. A capture that
fails either check is refused outright. Regenerates `content/expected_output.json`, keyed
`entry_id|stig_id|rhel_version` (unchanged shape, `build.py`'s `assemble()` still joins onto
`stig[]` rows this way) — a capture for an entry/version with no STIG mapping (most generator
entries) is validated but not indexed, since there is no `stig[]` row to join it onto.
`extract/make_pending_skeletons.py` drops `expected_output_skeleton()`: this file is now solely
`extract/import_captures.py`'s, registered in `qa.py`'s `GENERATORS` and Q15.

Tested with Caleb's 18 real files: 5 fold into the keyed index (the five real STIG rows his run
documents — `firewalld-service-active`/`ctrl-alt-del-target-masked` on RHEL 8 and 10,
`journald-service-active` on RHEL 10 only, no RHEL 8 STIG mapping exists for it), 13 validated
but unindexed (six generator entries × two releases, no STIG mapping). `qa.py` Q16 now passes
WITH real captures (5 expected_output blocks, 5 capture records — always empty before this
branch). Verified by hand: the evidence exporter for `firewalld-service-active` RHEL 8 now
renders `Compliant: yes`, `Capture host: defiant-rhel8`, `Capture release: Red Hat Enterprise
Linux release 8.10 (Ootpa)`, `Capture kernel: 4.18.0-553.163.1.el8_10.x86_64` — Caleb's real
capture, not a placeholder.

#### (d) Three mislabeled blast ratings

`gen-dnf-package` and `gen-yum-package` declared `blast: "green"` covering BOTH enum branches
of their `action` field (`install`/`remove`) — installing a package changes host state exactly
as much as removing one does, and unlike remove (which `content/dangerous.json`'s
`dp-dnf-remove`/`dp-yum-remove` already escalate to yellow dynamically), install had nothing to
raise it. `gen-chronyd-one-shot-check` also declared green: `chronyd -Q` retrieves the offset
from an NTP source and STEPS THE SYSTEM CLOCK before exiting (`chronyd(8)`) — a state change
even though it touches no file, which the entry's own notes cited without ever calling it one.

New `tests/test_blast_state_change_labels.py`: a static sweep over
`tests/fixtures/golden-commands.json`'s own commands against a state-changing pattern table
(`install|remove|erase|-Q|--permanent|enable|start|stop|add|del`, Eli Cross's ruling verbatim,
matched as a plain substring) on every RHEL release the golden table gives a command for; every
generator entry whose golden command matches must declare `blast >= "yellow"`. Deliberately
coarser than and independent from `tests/hostile_harness.js`'s enum-branch sweep (which computes
the REAL blast via `assembleCommand()`/`blastFor()` and only ever raises the bar above the
DECLARED label) — this test asks whether the declared label even admits the command is
state-changing in the first place. Committed failing on exactly the three named entries (six
other matched generators already declared yellow and passed); content and the golden fixture's
own `blast` field both raised to `"yellow"`, now green. `tests/hostile_harness.js`'s enum-branch
sweep (Marcus Reed, MCR-SEC-021) still passes unchanged — its own `_not_listed` comment is
updated to note that no shipped generator with a destructive enum branch is declared green any
more, so its "a green-declared generator must still have one green branch" assertion has nothing
to check against today (kept for the next one).

#### (e) `privilege` field for `gen-sshd-test-config`

Caleb's real capture run hit this directly: `sshd -T -f '/etc/ssh/sshd_config'` returned
"Permission denied" on both `defiant` and `saratoga` — `sshd_config` is not world-readable on a
STIG'd host — and the run correctly deferred it (no `sudo` used, no capture written). The content
had no way to say that in advance.

New `extract/schema.py` `PRIVILEGES = ("root",)` — a small closed set, matching how `BLASTS`
already works, not a free string. `content/commands.json`'s `gen-sshd-test-config` gets
`privilege: "root"`, and its `intent` now states why in plain language. `template.html`'s
`renderEditor()` and `renderGeneratorResult()` both show a "requires root" badge next to blast;
`formatEvidenceText()` adds a `Requires: root` line. Built as three parallel ternaries (open tag
/ `esc()`'d value / close tag) rather than one ternary whose branch mixes literal markup and an
escaped value — Q17's static innerHTML auditor accepts one literal, one `esc()` call or an
accumulator per ternary branch, not a concatenation of the three inside one branch.

Gates: `rm -rf dist && python3 build.py && python3 qa.py && python3 -m unittest discover -s tests
&& node tests/hostile_harness.js` — 22/22 gates PASS (unchanged gate count from G1-G3; Q22 from
G1 already covers the new fields' referential integrity), 171 unit tests PASS (168 + 3 new: the
blast-label sweep), hostile harness 81,577 checks / 0 FAILED, including the 140 enum-branch
control checks and 96 golden-command checks green against the new declared labels.

### Fixed — Panels review conditions G1/G2/G3 (2026-09-17, branch `salm/milo/panels-conditions`)

Closes Marcus Reed's APPROVE WITH CONDITIONS on `636fd7f` (Panels review, CR-T-26/28/29/30).

#### G1 (MED, PANEL-001) — declared tool was not the invoked binary

`firewalld-service-active` (`tool: "firewall-cmd"`) and `journald-service-active`
(`tool: "journalctl"`) both emit `systemctl` commands on every RHEL release. The Inspector's
flag-by-flag panel resolves an explanation with `decodeCmd(res.tool, res.version, res.flags)`,
which reads `FLAGS[version].clis[toolId]` — the wrong binary's dictionary, so `status`/`is-active`
could never resolve there even after CR-T-09/10 populated real flag dictionaries.

- `content/commands.json` gains `explain_tool: "systemctl"` on both entries. Chosen over re-filing
  `tool: "systemctl"` because `tool` also drives the sidebar Tools rail (`entriesForTool()`) — both
  entries would become undiscoverable from the firewalld/journald tool page they belong on.
  `tool` is unchanged everywhere else (navigation, category, the evidence export's tool label).
- `template.html`'s `renderInspector()` resolves the flag dictionary through
  `entry.explain_tool || res.tool` — the one call site that mattered. `MCR-ASSEMBLER` untouched.
- `content/tools.json` gains a `binary` field per tool (id already equalled the real binary for
  all 19; now recorded explicitly).
- `extract/schema.py` and `qa.py` Q13 validate `explain_tool` resolves to a real `tools.json` id,
  the same rule `tool` already follows.
- New `qa.py` **Q22** gate: every entry's `rhel_versions` commands' first word (after one leading
  `sudo`) must match its declared tool's binary, and every `flags[].flag` must resolve in a
  populated flag dictionary, carry a curated `explain`, or be honestly marked (not option-shaped,
  i.e. a subcommand like `is-active` that can never appear in an OPTIONS dictionary, with a
  `license_class` on record). Committed failing first (8 FAILs, both entries × all 4 RHEL
  versions), then the content/template fix landed and it went green.

#### G2 (LOW, PANEL-002) — bidi overrides and NUL survived into the evidence export

`esc()` correctly stays an HTML-entity escaper, not a sanitiser — but a `U+202E` bidi override or a
raw NUL in a rule title or check/fix text still reached `formatEvidenceText()`'s plain-text output
unchanged, and that text crosses trust boundary 5 into an SCTM/ATO package.

- `template.html`'s `MCR-EVIDENCE` block gains `evidenceHeaderSafe()`/`evidenceLineSafe()`, and
  `push()` now routes every pushed value through them. Reimplemented rather than calling
  `MCR-ASSEMBLER`'s `headerSafe()` directly, so the block stays independently liftable and pure on
  its own (its purity check forbids reaching outside itself) and `MCR-ASSEMBLER` stays untouched.
  Deliberately not identical to `headerSafe()`: it does not collapse run-on whitespace, because this
  export's own content relies on it (`"STIG version: V2R8  benchmark date: ..."`), where
  `headerSafe()`'s single clipboard comment line does not.
- Removes bidi override/isolate and zero-width ranges (`U+200B`–`U+200F`, `U+202A`–`U+202E`,
  `U+2060`–`U+2069`, `U+FEFF`) outright; C0/C1 controls, NUL and line separators become a space —
  applied per physical line so multi-paragraph check/fix text keeps its structure. `<`, `"` and `'`
  are left exactly as authored: this is plain text, not markup.
- Fail-first hostile fixture added to `tests/test_evidence_export.js`: a rule title carrying
  `U+202E`/`U+200E`, check text carrying a raw NUL, fix text carrying literal `<`/`"`/`'`. Committed
  failing (all three hostile characters survived), then the fix landed and it went green.

#### G3 — where the CR-T-28 report's sample export citation actually came from

The CR-T-28 report pasted a sample export citing *"man firewall-cmd(1) … retrieved 2026-09-01"*
for `firewalld-service-active`. That line has never existed in this repository at any revision —
`content/commands.json`'s real `source` for that entry has always been the DISA STIG pin
(`retrieved_on: 2026-09-17`), and `renderEvidenceModal()` takes `src` from `ctx.entry.source`, so
the shipped export path cannot produce it. Traced to `tests/test_evidence_export.js`'s own
hand-written determinism fixture (`fixtureOpts()`) — a synthetic illustration built to prove two
calls are byte-identical, never meant to represent real content — pasted into the report as if it
were a real run.

- New `tests/test_evidence_export_real.js`/`.py`: lifts `MCR-ASSEMBLER` and `MCR-EVIDENCE`
  verbatim out of the built artifact and runs them against the REAL data island —
  `entryById("firewalld-service-active")` → `assembleCommand()` → `withCopyPayloads()` →
  `formatEvidenceText()`, never a fixture — and snapshots the result against
  `tests/fixtures/evidence/firewalld-service-active.rhel9.txt`, byte-for-byte except the
  `Operator date:` line, plus an explicit assertion the output can never reproduce the
  hand-written sample's citation. The report sample and the shipped artifact can no longer diverge.

Gates: `rm -rf dist && python3 build.py && python3 qa.py && python3 -m unittest discover -s tests
&& node tests/hostile_harness.js` — 22/22 gates PASS (new **Q22**), 168 unit tests PASS (167 + 1
new), hostile harness 81,577 checks / 0 FAILED, byte-identical to Marcus Reed's review count
(`MCR-ASSEMBLER` genuinely untouched).

### Added — CR-T-26/28/29/30, STIG panel, evidence exporter, typed search, favorites/recent/print/about (2026-09-17, branch `salm/milo/panels`)

Four renderer/index modules, all consuming the existing rendered-state object (`RESULT` /
`currentResult()`, MCR-SEC-012) — the `MCR-ASSEMBLER` block and the field validators are untouched.

#### CR-T-26 — STIG panel

`renderStigPanel()` writes the Inspector's `#stig-panel` (and, for print, `#print-stig-panel`, an
identical mirror in the editor) directly — its own sink, in its own statement, following the same
Q17-audited idiom every other renderer in this file uses. For the current entry's `stig[]` rows on the
selected RHEL version:

- Badge: STIG ID and Category, rendered **only when `stig[]` is non-empty** (CR-P0-03).
- Every cited CCI, plus the CCI → NIST SP 800-53 crosswalk (`nistForCci()`, against
  `content/cci_nist.json`; falls back to the rule's own `n[]` when a STIG row carries no `nist[]` of
  its own).
- Check text and Fix text as `<details>`/`<summary>` disclosures — verbatim DISA text through `esc()`,
  no manual line-break handling (`white-space:pre-wrap` on a `<pre>`, matching the existing
  `.copypreview` idiom).
- Expected compliant output when `build.py`'s `assemble()` has joined a capture record onto the row
  (`content/expected_output.json`), or the honest "No capture yet" line when it has not — `Q9`/`Q16`'s
  capture data has 0 records in this build, so every rule in this build renders the honest state today.
- The RHEL 7 sunset banner from `rules_rhel7._meta.sunset`/`.version`, and the entry's
  `rhel_versions[version].changed_in_note` above the panel.

A STIG rule reached via search with no command in this build's catalog opens standalone
(`selectStigRule()`): if the rule's build-time reverse link (`rules[].cmds`, from `build.py`'s
`assemble()`) names a real command entry, that entry opens instead — same panel, a real command; when
it does not, the panel still renders in full and the editor says plainly that no command is catalogued
for it yet, rather than showing a blank "no command selected" state.

#### CR-T-28 — Evidence exporter

`exportEvidence()` (`Ctrl+E`, or the **Export as Evidence** toolbar button) opens a modal previewing a
deterministic plain-text SCTM-ready block, formatted by `formatEvidenceText()` — a **pure** function
(MCR-EVIDENCE block, lifted and timed the same way `tests/hostile_harness.js` lifts the assembler)
that never reads DATASETS/STATE/the DOM/the clock: tool version, build date, the content fingerprint,
STIG ID, STIG version and benchmark date, rule title, CAT, CCI list, NIST controls, check text, fix
text, expected output (or "not captured"), the assembled command and its flags exactly as
`currentResult()` produced them, source citation, capture metadata (host/release/kernel/date) when
present, and the operator's own date line. The `<pre>` preview is the same string `Copy evidence text`
puts on the clipboard — nothing is recomputed between the two (threat-model-v1 §9, the MCR-SEC-003
rule applied to the exporter). Two exports of the same entry, only the operator date line differing,
are byte-identical (`tests/test_evidence_export.js`, run under `python3 -m unittest` via
`tests/test_evidence_export.py`).

**Content fingerprint**, shared by CR-T-28 and CR-T-30: `build.py` computes `sha256()` of the escaped
JSON payload — the exact bytes that ship inside `<script id="mcr-data">…</script>` — **before** that
payload is substituted into the template, and embeds the digest as the `CONTENT_FINGERPRINT` shell
constant (never inside the island itself, which would hash a string containing itself). `qa.py`'s Q1
gate independently re-hashes the shipped island and fails the build if the embedded constant and the
fresh hash disagree.

#### CR-T-29 — Lazy typed search index

The palette's build-time index seed is replaced by a real index: `buildIndex(datasets)` (pure —
MCR-INDEX block) is built **once**, on the first palette keystroke, over tools, command intents,
curated per-entry flags, the per-release flag dictionaries (`content/flags_rhel*.json`), every
embedded STIG rule (ID and title), every CCI, and every mapped NIST control — roughly 3,900 records on
this build's full dataset. `queryIndex(index, q)` requires every search term to match (whole-word
matches score higher than substrings) and groups hits by kind (Tool, Command, STIG, Flag, CCI, NIST,
in that order, each capped at 8 so one large family cannot crowd the palette). A CCI or NIST hit
resolves to the first embedded rule that cites it (current RHEL version first). A query with no
possible match renders an explicit "No matches for …" state. Both build and query measure well under
the 100 ms budget on the real embedded dataset — 1.5 ms to build, under 1 ms per query in this build's
measurement (`tests/test_search_index.js`, run under `python3 -m unittest` via
`tests/test_search_index.py`, which prints the timing).

#### CR-T-30 — Favorites, recent, print view, About panel

- **Favorites/recent:** a **Favorite**/**Favorited** toggle on every command's toolbar; a **Recent**
  list pushed on every `selectEntry()`. Both are ID lists only, under the existing schema-versioned
  storage guard (`mdcr.v1.favorites` / `mdcr.v1.recent`), sanitized through `sanitizeIdList()` (pure —
  MCR-FAVORITES block) against the live content island before use — never storing or rendering raw
  text (threat-model-v1 §7). `tests/test_favorites_store.js` (run via `tests/test_favorites_store.py`)
  drives it with hostile shapes: raw command text, objects, numbers, oversized lists, duplicates — only
  known-good ID strings ever survive. The **Favorites** rail (`Ctrl+Alt+4`) lists both, reusing the
  existing `data-entry`/`data-tool` click-router hooks.
- **Print view:** the print stylesheet's `.print-only` rule shows `#print-stig-panel` — the STIG panel
  mirror inside `#editor`, written by the same `renderStigPanel()` call as the screen version — so
  `Ctrl+P` prints the current entry and its full STIG panel with the rail, sidebar, inspector, status
  bar and any open overlay dropped, and no external resources (the artifact has none to begin with).
- **About panel:** the **About** rail (`Ctrl+Alt+5`) shows tool version and build date, the content
  fingerprint, every embedded STIG release's version/benchmark date/rule count (with a sunset marker
  for RHEL 7), the embedded source families and their license classes (read from each dataset's own
  `_meta.license_class`, never restated), and the SALM Content Licensing Ruling v1 attribution block,
  reproduced verbatim from `05_Compliance_Legal/MD_CODE_RED/content-licensing-ruling-v1.md` — with
  plain hyphens standing in for the source document's em dashes, so no hand-typed non-ASCII glyph
  enters a tracked file (Q21 scans every tracked file for exactly that class of character).

#### Gates and tests

Q5 markers added for every new function (`renderStigPanel`, `exportEvidence`, `buildIndex`,
`queryIndex`, `nistForCci`, `formatEvidenceText`, `sanitizeIdList`, `toggleFavorite`, `pushRecent`,
`renderFavoritesSidebar`, `renderAbout`, the `CONTENT_FINGERPRINT`/`ATTRIBUTION_BLOCK` constants, and
the print-only mirror element); the three previously-PENDING CR-T-26/28/29 markers now report PASS.
`rm -rf dist && python3 build.py && python3 qa.py && python3 -m unittest discover -s tests && node
tests/hostile_harness.js` is green: **21 QA gates + `JS` PASS** (was 20 + `JS`, one pending marker
resolved to 3), **167 unit tests PASS** (was 159, +8), hostile harness **0 failures over 81,577
checks** (unchanged — the assembler was not touched). Reproducible build re-verified: two consecutive
builds from the same sources are byte-identical. Three journeys walked in a real browser over a local
HTTP server: Command Builder → STIG panel → Favorite; search by NIST control → standalone STIG rule
(RHEL 7, sunset banner) → Export as Evidence (`Ctrl+E`, Copy evidence text); About panel and the print
stylesheet's `.print-only` rule (verified via computed style and the live `CSSOM`, screen and print
mirror byte-identical).

### Fixed — D4 review MCR-SEC-015..023, conditions E1–E7 (2026-09-17, branch `salm/milo/generators`)

Marcus Reed's D4 review of the generator tranche at `69fb1c2`/`996b504` returned **DENY** — one HIGH
that blocks on its own, plus conditions E1–E7 and two advisories. Everything below lands on the same
branch. E2 (MCR-SEC-017, the rebase onto `origin/main`) was already met at `996b504`; D3 (no YAML
sink without a YAML quoter *and* a YAML-parsing oracle) remains open and untouched, because this
branch has no YAML sink.

#### MCR-SEC-015 — HIGH — condition E1 — short options joined with `=`

The assembler joined **every** flag to its value with `=` unless the token carried `eq:false`, and
`eq:false` was used nowhere in the 24 shipped specs. 20 short-option tokens across 11 of 24
generators emitted `-X=value`, which getopt(3) does not accept — the `=` is passed through as the
first character of `optarg`.

    auditctl -w='/etc/motd' -p='r' -k='identity'      ->  auditctl -w '/etc/motd' -p 'r' -k 'identity'
    chage -M='60' -m='7' -W='14' 'svcacct'            ->  chage -M '60' -m '7' -W '14' 'svcacct'
    useradd -m -c='RFC-1234' -G='wheel' -s='/bin/bash' 'svcacct'
                                                      ->  useradd -m -c 'RFC-1234' -G 'wheel' -s '/bin/bash' 'svcacct'
    lvcreate -L='10G' -n='lv0' 'vg0'                  ->  lvcreate -L '10G' -n 'lv0' 'vg0'

Most fail loudly at the tool, which is the safe direction. Two do not: `auditctl` produces a STIG
control that looks applied and is not, and `useradd` silently sets GECOS to `=RFC-1234` and the login
shell to `=/bin/bash`.

**Fixed at the assembler, not per token.** A new `flagJoin()` inside the `MCR-ASSEMBLER` block
derives the join from the flag's own shape — `--long` joins with `=`, `-X` joins with a space — so
all 20 tokens are correct with **no content edit at all**, and a 25th generator inherits the rule.
Two escape hatches survive, each legal only on the shape it belongs to: `eq:false` on a long option,
`join:"glued"` on a short one for a tool that requires `-Xvalue`. Neither is used in the tranche.

**Deviation from the recommended fix, stated plainly.** MCR-SEC-015 recommended `eq:false` on every
single-dash token plus a schema rule refusing a single-dash flag whose `eq` is not `false`. That is
20 content edits and a rule an author can still defeat by forgetting a key on the twenty-first
generator. The derived rule inverts it: a short option carrying `eq` **at all** is refused, because
the join is derived and a declaration is a disagreement with the rule rather than a restatement of
it. `extract/schema.py`'s new `flag_join_errors()` is the build-time half; the assembler returns
`null` at run time for the same token.

#### MCR-SEC-022 (E7) and MCR-SEC-018 (E3) — the discriminator is now derived

`flag` beside `lit` was an unchecked off-switch for the D1 positional rule. It emits nothing on a lit
token; its only effect was to make `isPositionalToken()` and `positional_indexes()` look away — so
`{lit:"0644", flag:"-P", requires:"m"}` was accepted and reopened MCR-SEC-013 through the key meant
to close it. Marcus's four-row table is now a test, on every release, in both halves:

| template | build time | run time, gate supplied | run time, gate absent |
|---|---|---|---|
| `{lit:"0644",requires:"m"}` | REFUSED | — | — |
| `{lit:"-P",flag:"-P",requires:"m"}` | REFUSED | `null` | `null` |
| `{lit:"0644",flag:"-P",requires:"m"}` | REFUSED | `null` | `null` |
| `{lit:"/etc/shadow",flag:"-x",requires:"m"}` | REFUSED | `null` | `null` |
| `{lit:"-P",requires:"m"}` (derived) | accepted | `chmod -P '/etc/foo'` | `chmod '/etc/foo'` |

A token carrying both `lit` and `flag` is refused **even when they agree**: the branch shipped two
exemplars of the shape, and an author who hits the D1 build error should not have a
documented-looking lever to pull. Whether a literal is an option is derived from the literal — a
`lit` matching `FLAG_TOKEN_RE` is an option and never occupies an argument slot — so a real option
needs no key. `gen-lvextend-grow` and `gen-setsebool-set` lose their `flag` key and keep `requires`,
which is the regression Marcus said to watch for. This also closes MCR-SEC-018's over-refusal without
the dangerous workaround it invited: deleting `requires` to clear the build error would have made
every SELinux boolean change **persistent** when the operator asked for runtime-only.

#### MCR-SEC-023 — advisory — a lit-emitted option is now explained

The lit branch pushed the word and returned, so `sshd -T`, `setsebool -P`, `lvextend -r` and
`journalctl --no-pager --boot` appeared in the command and were absent from the flag-by-flag panel.
The same derived test decides it: an option-shaped literal goes into `flags[]`, in command order.
With no curated `explain` and no dictionary hit the panel renders *"unverified — see man page"* — the
no-guess law, not a guess.

#### MCR-SEC-016 — condition E4 — closed grammars where one exists

    lvm_size    ^([+-]?\d+(\.\d+)?[bBsSkKmMgGtTpPeE]?|\d+%(FREE|VG|PVS|ORIGIN))$
    group_list  ^[a-z_][a-z0-9_-]{0,31}(,[a-z_][a-z0-9_-]{0,31})*$

`gen-lvcreate-new-lv.size`, `gen-lvextend-grow.size`, `gen-useradd-create.groups` and
`gen-usermod-add-group.groups` move off `comment`, the one free-text type. Nothing here was
injectable — every value is `shQuote`d and every wrong one fails closed at the tool — but
`lvextend -L 'ticket RFC-1234' -r '/dev/vg0/lv0'` assembled and rendered Copy on a yellow-blast
storage command. The `lvm_size` label is load-bearing rather than decorative: it is the placeholder
and the refusal reason, and the only place in the UI that distinguishes `10G` (set the volume to) from
`+10G` (grow it by). The four `comment` fields Marcus called defensible stay free text; his unrated
note on `chronyd -Q` is recorded in `docs/POAM.md` instead of being dropped.

#### MCR-SEC-019 and MCR-SEC-020 — condition E5 — gate Q20

`gen-fw-allow-service` cited `firewall-cmd.man.txt#L310` — `--add-service`, an option it does not
emit, since it composes a rich rule. Repointed to `#L538`. **CLOSED.**

The dictionary finding was never "there is a gap": it was that nothing could see one, because Q15
re-runs the extractor and diffs the output against itself. New gate **Q20** has two halves, both
shown able to fail before commit (it is Q20, not Q19: the merge with `origin/main` at `da2ab47`
brought in Q19, the escaper property gate from Al Kowalski's Gate 3 review):

- **Coverage** — distinct long options in each committed raw capture against the dictionary, for all
  44 tool/release pairs, compared to `content-src/flag_coverage_baseline.json`, which records the gap
  with its acceptance date, who accepted it and the ticket that owns closing it (CR-T-09/10). A
  shortfall that **grows** fails; one that shrinks reports and asks for the baseline to be tightened.
  Measured: firewall-cmd 16 of 205 long options on RHEL 8, dnf/yum 61 of 140, nmcli 2 of 20.
- **Citations** — a generator citing a raw capture line must cite a line showing the option it emits,
  and the option that counts is the one bound to a value or a rich rule, not a decoration like
  `--permanent` that half the firewall-cmd man page mentions.

**MCR-SEC-020 was retired on 2026-09-20.** The named wrapped-term defect is closed:
`--add-rich-rule` is present in the RHEL 8, 9 and 10 dictionaries. Q20 remains active over all
70 captured tool/release pairs. The retirement record names its authority and evidence, and its
test proves both the post-expiry success path and the missing-evidence failure path.

#### MCR-SEC-021 — condition E6 — the harness gets a validity oracle

The 12,689 content-spec checks were a **containment** oracle only. They assert a hostile value is
rejected or confined to a single-quoted token whose skeleton matches the benign control, and never
assert the benign control is a valid invocation of its tool. That is exactly how 20 malformed joins
passed 76,225 checks with 0 failures.

- `tests/fixtures/golden-commands.json` — one row per generator: stated benign values and the **exact**
  command it must emit on each release (`null` where gated off), the flag list the inspector must show,
  the blast it must rate, and the man-page rule the row pins. Hand-authored from each tool's man page
  and getopt(3), never generated from the assembler: a table regenerated from the code it tests is a
  transcript. Completeness runs both ways — a generator with no row fails, a row naming no generator
  fails.
- `optionSyntaxErrors()` — getopt(3) syntax on every benign command the harness assembles, with three
  negative controls including MCR-SEC-015's own reproduction.
- `benignFor(field, rot)` — no longer pins every enum to `opts[0]`, so a hostile value is fuzzed
  against every branch of its neighbours rather than only the safest one.
- A new enum-branch **control** sweep: every generator × every enum field × every option × every
  release against the real `dangerous.json` — assembles, valid syntax, never below the declared blast,
  and every destructive branch (`remove`/`stop`/`disable`/`off`) at least yellow. Checked in the honest
  direction: a green-declared generator must have a branch **raised** and a branch still **green**, so
  a pattern table that rated everything yellow would fail.

#### Also

- `tests/test_positional_crosscheck.py` + `tests/shift_crosscheck_driver.js` — Marcus's exhaustive
  shift sweep re-run after the discriminator change and extended with option-shaped literals: every
  2-to-4-token template over 8 token kinds containing a literal (4,336 shapes), filtered to the 3,258
  `extract/schema.py` accepts, driven over 4 releases × 8 supplied/absent combinations — **104,256
  runs, 0 shift violations**. The expectation is computed in Python from `schema.positional_indexes()`
  and the answer comes from the assembler lifted through the harness's purity-checked extractor, so
  neither side restates the other's rule. Shown failing against the pre-fix tree.
- Nine new schema fixtures (seven invalid, two valid) covering the join rule and the dual-key token.
- **Fail-first commits**, both hashes recorded: `77a688f` (golden table RED, 44 harness failures) →
  `5315fef` (E1 green); `1389487` (discriminator table RED, 78 harness + 5 unit failures) → `dee9005`
  (E7/E3/MCR-SEC-023 green).

**Functions changed in `template.html`, all inside the `MCR-ASSEMBLER` block, and nothing else in that
file:** `flagJoin()` (new — the derived join rule), `isPositionalToken()` (the derived positional
discriminator), and `assembleCommand()` in three places (the field-flag branch and the richRule branch
call `flagJoin()`; the lit branch refuses a dual-key token and pushes option-shaped literals into
`flags[]`). Two rows were added to the `FIELD_TYPES` table for E4.

**Merged with `origin/main` at `da2ab47`** (the Gate 3 `qa.py` hardening merge). Only `qa.py`,
`README.md` and `docs/CHANGELOG.md` conflicted; both doc conflicts kept both sides, and in `qa.py`
both new gates were kept — theirs stays **Q19** (escaper behaviour, already referenced by
`docs/QA_GATES.md`) and this branch's coverage gate became **Q20**. `template.html`,
`extract/schema.py`, `content/` and every test file auto-merged.

#### Q21 — no tracked source file spells an invisible character

A defect of mine, found after the merge and fixed on the same branch. `dd01ad7` rewrote
`tests/fixtures/hostile-inputs.json` through `json.dump(..., ensure_ascii=False)` while adding the two
new benign values, and **eight** invisible-character vectors the file states as JSON `\u` escapes on
purpose — U+200B, U+200D, U+202E, U+FEFF, U+00AD, U+2028, U+2029, U+2065 — came back out as the raw
characters they name. Q17 could not see it (it scans the built artifact, which this fixture never
reaches) and the harness could not (it reads the file as JSON, where an escape and its character are
one value). The fixture is now byte-identical to `origin/main` apart from the two added field types,
and the harness still rejects all 11,744 invisible-character vectors, so what is tested did not change
— only how it is written. New gate **Q21** walks `git ls-files` with Q17's own `TROJAN_RANGES` table;
`tests/test_no_raw_trojan_chars.py` plants each character class in a temp directory and watches the
scanner fire before believing it. Committed fail-first at `484ec23` (Q21 FAIL, 8 findings).

#### Marcus Reed's D4 re-review — conditions F1, F2, F3

**F1** — the fixture carried **eight** raw characters, not three: U+200B, U+200D, U+202E, U+FEFF,
U+00AD, U+2028, U+2029, U+2065. All eight re-escaped; the file is byte-identical to `origin/main`
apart from the two field types E4 added, all 55 vectors parse identically, and the harness still
rejects 11,744 invisible-character vectors. Q21's character set is `qa.TROJAN_RANGES` — Q17's own
table — which already covers everything the condition lists. The gate was then **widened** on
Marcus's narrower rule: the exclusion list is now **empty**, all 226 tracked files are scanned
(`stig-src/` and `content-src/raw/` included, both measured clean), and the single allowance is a
U+FEFF at offset 0 — allowed at 0, caught one byte later, both halves tested.

**F2 / MCR-SEC-025** — settled from the pinned capture, and the spec **stays**: chronyd(8) SYNOPSIS is
`chronyd [OPTION]... [DIRECTIVE]...` (`content-src/raw/rhel8/chronyd.man.txt#L7`, identical on
RHEL 10) and `-Q` takes no argument (#L68), so configuration directives are **operands** accepted
after the options and `chronyd -Q 'server time.mil iburst'` is correct as emitted. The golden row is
unchanged. What was wrong was the *modelling* — the directive is a separate operand, not `-Q`'s value
— so the citation moves from `man 8 chronyd` to the `-Q` line in the capture, and the operand grammar
is recorded in the entry's `notes`, which the renderer surfaces.

**F3** — the Q20 ratchet gets a retirement plan: **owner Caleb Stone** (extractor fix, CR-T-09
follow-up), **retires 2026-09-25**. Q20 now FAILS from 2026-09-26 unless the baseline is regenerated
against the new dictionaries or re-dated in writing, and `tests/test_coverage_baseline_expiry.py`
watches that fire against an injected date rather than leaving it to be discovered on the day. An
accepted residual does not get to become a permanent one by nobody looking.

**Gates on the merged tree, from a clean `dist/`:** `build.py` OK and reproducible · `qa.py`
**Q1–Q21 PASS** (22 gates with `JS`) · `unittest discover` **159 OK** (135 from the hardening merge,
plus the 24 added here) · `node tests/hostile_harness.js` **81,577 checks, 0 FAILED** (was 76,225) ·
artifact sha256 `9eb3402689e8c4f68f914a8154515aa117b999da646e9fb6c0bb1ce8c40bab2b`.

### Added — CR-T-17..25 guided-form generators (2026-09-17, branch `salm/milo/generators`)

24 generator specs, one `GENERATORS` registry, form renderer and `decodeCmd()` — the P0 generator
tranche Zee assigned after the assembler merged. The assembler itself (`assembleCommand`,
`validateField`/`validateSpec`, `shQuote`, `composeRichRule`, `isPositionalToken`, `blastFor`) is
untouched; everything here is content (`content/commands.json`, `content/tools.json`,
`content/dangerous.json`) plus rendering code that calls the assembler the same way a static entry
does.

- **CR-T-17** — ported six Grey Beard generators: `gen-fw-set-default-zone`, `gen-fw-open-port`,
  `gen-fw-allow-service` (firewall-cmd), `gen-nmcli-static-ipv4`, `gen-journalctl-unit-logs`,
  `gen-lvcreate-new-lv`, `gen-lvextend-grow`, `gen-sshd-test-config`, `gen-useradd-create`,
  `gen-usermod-add-group`.
- **CR-T-18** — `gen-systemctl-query` (status/is-active/is-enabled/is-failed, blast green) and
  `gen-systemctl-manage` (start/stop/restart/reload/enable/disable, blast yellow) — split so a read
  action and a state-changing action never share one blast level.
- **CR-T-19** — `gen-dnf-package` (`versions: ["8","9","10"]`) and `gen-yum-package` (all four). RHEL 7
  never sees a fabricated `dnf` command: the generator is version-gated AND `tools.json`'s `dnf` entry
  is `unavailable` on RHEL 7 with `reason`/`alternative: "yum"`, so the sidebar shows the note twice
  over — once on the tool, once on the (absent) generator.
- **CR-T-20** — `gen-setsebool-set` (`-P` persist is an optional lit bound via `requires:`) and
  `gen-semanage-port-add`.
- **CR-T-21** — `gen-chage-list` (`-l`, read-only) and `gen-chage-set-aging` (`-M`/`-m`/`-W`), both
  man-page-sourced per ADR-001 §2.4 (no RHEL guide covers `chage`'s own flag grammar).
- **CR-T-22** — `gen-auditctl-watch` (`-w`/`-p`/`-k`) and `gen-ausearch-by-key` (`-k`/`-ts`).
- **CR-T-23** — `gen-rsyslogd-test-config` (`-N1 -f`, parses and validates, never starts the daemon).
- **CR-T-24** — `gen-chronyd-one-shot-check` (`-Q`, one correction and exit). The RHEL 7
  chronyd-default/legacy-ntpd note (CR-P0-05 AC3) is carried in the entry's own `notes` field, which
  `assembleCommand()` already surfaces to the renderer, and in `tools.json`'s `chronyd` availability
  notes per version.
- **CR-T-25** — `gen-podman-ps` and `gen-podman-stop` (`versions: ["8","9","10"]`), with `tools.json`'s
  `podman` entry `unavailable` on RHEL 7 (no supported package, base or Extras). RHEL 7 never fabricates
  a podman command (CR-P0-05 AC4): both the generator and the tool are gated, independently.

**Content authoring note.** `flags_rhel8.json`/`flags_rhel10.json` (CR-T-09/10) are the host-verified
source for every `flag`-typed token in these specs, EXCEPT `--add-rich-rule` and `--permanent` on the
two firewall-cmd rich-rule generators: both are real, present in the raw RHEL 8/10 man-page capture
(`content-src/raw/rhel{8,10}/firewall-cmd.man.txt` lines 538/247+), but missing from the generated
dictionary because `extract_flags.py`'s synopsis-line regex captures only the leading `[--permanent]`
token repeated ahead of firewalld's ~90 per-option lines and misses the option that follows it on the
same line (e.g. `--zone=zone`, `--add-service=service`). Cited from the raw capture directly instead of
invented; flagged as an extractor follow-on, not fixed here (extract/ is a different owner's surface).
RHEL 7/9 have no `flags_rhel{7,9}.json` (empty placeholders, no host read yet) — every field on those
releases is either gated off (`field.versions`) or documented from the RHEL 7 System Administrator's
Guide / RHEL 9 guides (source `url_or_man`/`sha256` from the corpus manifest,
`license_class: paraphrase-only`), never captured verbatim.

**Gates.** `qa.py` Q12 and `tests/test_schema.py` learned that `"template" in e` (a generator spec)
keeps the four-version promise via `spec.versions`/`field.versions`, not a `rhel_versions` object —
both would have failed the FIRST real generator spec, a gap `extract/schema.py`'s own `spec_errors()`
already closed at build time but these two had not caught up to. `tests/hostile_harness.js` gained a
content-spec sweep: it loads `content/commands.json` directly and fuzzes every field of every one of
the 24 generator entries with the full hostile-vector set, in that entry's own template rather than a
synthetic analog (12,689 checks; the harness's existing per-field-type sweep stays as-is and still runs
first). `python3 build.py && python3 qa.py && python3 -m unittest discover -s tests && node
tests/hostile_harness.js` all green.
### Fixed — BQP Gate 3 review of `qa.py`: AL-GATE3-001/003/004/005/006, plus Q2/Q5/Q14 (2026-09-17, branch `salm/milo/qa-hardening`)

Al Kowalski's Gate 3 diff review of `qa.py` as trust-path code returned **PASS WITH ISSUES**:
one HIGH, five MEDIUM/LOW, and two rows of the per-gate table marked "fail-open risk found"
with no negative control. `qa.py` is the merge gate — a bug in it fails open and nothing
downstream notices — so every fix below landed as a pair of commits: the gate shown to FAIL
first, then the change that turns it green.

**AL-GATE3-001 (HIGH) — the escapers were never proven to escape.** `segment_ok()` treats any
segment matching `^(esc|escapeAttr|escapeRegex)\s*\(` as safe, full stop, and `gate_q17` checks
that the strings `"function esc("` and `"function escapeAttr("` exist. Together those prove a
function under that name is defined and every render path funnels through a call to it. They
cannot prove the body does anything. Al's reproduction:

```python
qa.render_sink_failures(shell_with_identity_escapers)
# -> ([], 4)   — zero failures, 4 expressions "audited"
```

`function esc(s){return s;}` defeats the product's entire XSS defence with **zero change to any
call site**, and every call site keeps looking exactly as safe as it does today.

**Q19** closes it by running the functions instead of reading them. `extract_js_function()`
brace-matches `esc`, `escapeAttr` and `escapeRegex` out of the SHIPPED artifact over a lexically
masked copy — the same discipline `hostile_harness.js` applies to the assembler block, for the
same reason: the code that clears the gate has to be the code that crosses the air gap. The three
functions go to `tests/escaper_probe.js` under node against 92 declared vectors and 3 generated
ones (100k, 20k and 5k characters). The properties:

* `esc()` — no raw `<`, `>`, `"` or `'` in the output, every `&` opens a well-formed entity, and
  a strict decoder round-trips the output back to **the exact input**. The round trip is not
  decoration: an escaper that *deletes* the dangerous characters is XSS-safe and would silently
  eat every `<` in a DISA fix text, and a no-raw-metacharacter test alone would rate it clean.
* `escapeAttr()` — all of the above plus no raw `` ` `` and no raw `=`, which is the reason it
  exists as a separate function from `esc()`.
* `escapeRegex()` — every metacharacter present is backslash-escaped and none left bare, the
  pattern compiles, matches its own input, and does **not** match what only the unescaped pattern
  would (`a.c` must not match `abc`) — the half an identity function would otherwise pass.

The probe runs its own battery against three known-broken escapers (identity, drop-the-character,
half-escaped) **before reporting anything**, and refuses to report a PASS if any comes back clean.
Node is required, as for Q18: an escaping check that downgrades itself to PENDING on a thin runner
is a fail-open wearing a politer word. Mutation evidence: 76 named failures against the shipped
artifact with `return s;` spliced into `esc()`; 0 against it as it ships.

**AL-GATE3-003 (MEDIUM) — Q7's brace counter desynced on a literal.** `try_block_spans()` counted
raw `{`/`}`. One unbalanced brace inside a string literal inside a `try` body shifted the depth, so
the span ran past its own `catch` and swallowed the sibling code after it — and a genuinely
unguarded `localStorage` call in that sibling code was reported as one of the audited try/catch
references. New `mask_js_literals()` returns a same-length, same-line-breaks copy with comments
blanked entirely and the *contents* of strings, template literals and regex literals blanked, their
delimiters kept. The masking happens inside the span finder, not in its caller: a caller that has
to remember to launder its input is a caller that will one day forget, which is how this arrived.
Driven five ways in `tests/test_storage_guard.py`, including the closing-brace half that would
*shorten* a span and produce a false FAIL — a gate that cries wolf gets switched off.

**AL-GATE3-004 (MEDIUM) — six gates passed on an empty bundle.** Q3, Q4, Q8, Q12, Q13 and Q16 all
reported PASS with no entries, no tools and no rules, because a per-item loop records a failure only
by finding something wrong *with* an item. Q9 has guarded its own empty case since CR-T-07 with the
reasoning written out in a comment; that reasoning was never about CAT I rules. One shared
`empty_set_failure()` helper, and every gate says why *its* empty set is suspicious. Q7 and Q18 grew
the same guard in their own commits. Recorded and not fixed: `extract/schema.py`'s `content_errors()`
has the same shape one layer down, so an empty `commands.json` still clears build-time validation —
out of this branch's scope, caught by all six gates at the merge gate, written down in
`docs/QA_GATES.md`.

**AL-GATE3-005 (MEDIUM) — Q3 had drifted weaker than the check it doubles.** `qa.py` required four
provenance fields; `extract/schema.py` requires five. The missing one was `version`, the field
schema.py's own docstring calls mandatory because "a source that cannot say which version of the
document it came from cannot be re-checked". Masked only because `build.py` runs the stricter check
first. `parse_schema_tuple()` now reads `PROVENANCE_FIELDS` and `LICENSE_CLASSES` out of
`extract/schema.py`'s **text** — the same no-import discipline `load_build_constants()` uses on
`build.py`. The constant is shared; the independent *check* Q3 exists to be is not. An unreadable or
empty tuple is a FAIL, never a fallback.

**AL-GATE3-006 (LOW) — a malformed harness report crashed Q18.** `rep["checks"]` and seven siblings
were read unguarded, so a harness exiting 0 with key-incomplete JSON raised `KeyError('checks')` mid
run, with no `try/except` anywhere in `main()`. It failed closed — Python exits non-zero — so it was
never a silent pass; it was a stack trace that reads identically whether the harness broke or whether
it caught something real. `harness_report_failures()` now trusts nothing about the report's shape:
non-object bodies, a non-list `failures`, missing counts, counts of the wrong type (`True` is an
`int` in Python and is not a count) and zero checks are each one FAIL line naming the reason.

**Q2 — the air gap could be spelled around.** The scan was `re.findall` for `fetch(`,
`XMLHttpRequest`, `WebSocket`, `navigator.sendBeacon`, `import(`. Al placed it in the same
structural class as the Q17 computed-member gap MCR-SEC-014 closed, but undocumented and untested
rather than accepted and recorded. `network_call_failures()` applies D2's rule to the air gap and
adds the shape Q17 never needs: a render sink is always *written*, a network API only has to be
*reached*, so `var f = fetch;` is the whole bypass. Four routes closed — the name in real code
called or not, the name in brackets, the name fused out of string literals (inline, through a
variable, or split across a literal and a variable), and a CDN host assembled the same way — with
ten controls covering every computed-member shape `template.html` writes.

**Q5 — a marker in a comment counted as a feature.** A substring match over the whole file, standing
in for structural claims like "the rail renderer exists". `marker_kind()` derives the kind from the
marker's own text, leaving `MARKERS` a list of 3-tuples so tranches that add markers do not collide
over a schema change: `code` markers must start at a position that survived masking, `html` markers
must be in the markup outside every `<script>` and HTML comment, and `text` markers — user-visible
copy, a CSS at-rule, the assembler's own comment marker — are matched as text **on purpose**,
because copy lives in a string literal and there is nowhere else for it to live.

**Q14 — the gate nobody could drive.** ADR-001 §7.3 promised `tests/test_paraphrase.py`; it did not
exist, and Al's table carried Q14 as the one gate he could not rule out a fail-open for because there
was nothing to run. Q14 is split into pure pieces the way Q10 and Q17 already were, and the test file
plants a sentence lifted at run time out of a real staged source, checks honest paraphrase still
passes, checks the same sentence on a `verbatim-ok` entry still passes, and pins the 7-versus-8 word
boundary in both directions. Q14 also gained a refusal: a release whose flag dictionary ships
populated with no raw sources staged under `content-src/raw/rhel<N>/` is a FAIL, because the
dictionary was extracted *from* those files and without them the gate is comparing curated content
against a corpus it did not come from.

**New: `docs/QA_GATES.md`.** Every gate, what it proves stated narrowly, where it has been watched
failing, and what a PASS explicitly does not mean — including the four rows that still have no
negative control, named rather than left to be found. It also collects the ADR-001 §7 items that are
now stale (the superseded 8 MB ceiling, §7.3 still numbering Q1–Q17, the Q14 promise now met, the
Q10 parity layer that must not be removed as redundant) for Al, whose document it is.

Gates 19 → 20 (Q1–Q19 plus `JS`), all PASS. Unit tests 51 → 135, all OK. Hostile harness 63,536
checks, 0 failed. `template.html` untouched, so the artifact is byte-identical: sha256
`5fb9b7adfd8b60feb90baa96f43b2d622c78158959672d5c60940fcd87bd16ad`, reproducible across rebuilds.

### Fixed — re-review conditions D1/D2: MCR-SEC-013, MCR-SEC-014 (2026-09-17, branch `salm/milo/sec-013-014`)

Marcus Reed's re-review of `ac087c3` returned **APPROVE WITH CONDITIONS**: all three HIGH findings
closed, `block_flag` cleared, two new findings — one LOW, one INFORMATIONAL — carried as conditions
D1 and D2. Both are addressed here. The fixtures were committed FIRST, in a commit that fails the
gates (`93a0cbf`), and the fix follows in the commit that turns them green: D1 asks for the gate to
be shown to fail before it is shown to pass, which is the standard the CR-T-08 harness set.

**MCR-SEC-013 (LOW) — a conditional positional literal still shifted arguments.** The MCR-SEC-002
fix reasons about argument slots through `isPositionalToken(tok)`, which was `tok.field && !tok.flag`
— so a `lit` was never positional. A literal made conditional with `requires` could therefore vanish
without the later-positional check that every field token gets:

```js
fields:  [{name:"mode",type:"integer",required:false},{name:"p",type:"path",required:true}]
template:[{lit:"chmod"},{lit:"0644",requires:"mode"},{field:"p"}]
```

with `mode` absent assembled `chmod '/etc/foo'` — the path promoted into the mode slot — and
`spec_errors()` accepted the spec. Both halves now count a `requires`-carrying literal as positional.
At run time `tokenPresent()` answers the presence question for `requires` as well as for `field`, and
one shared `laterPositionalSurvives()` states the shift rule once for both callers. At build time
`positional_indexes()` and `shift_unsafe_after()` do the same, and `spec_template_errors()` refuses
a conditional literal that has a surviving positional after it. An *unconditional* literal stays out
of the positional set deliberately: it can never vanish, so it can never shift anything, and counting
it would refuse correct templates. The legal shape MCR-SEC-002 shipped — `{lit:"…toaddr=",
requires:"toaddr"}` followed by `{field:"toaddr", optional:true}`, both gated on the same field so
they leave together — is still accepted, and `tests/fixtures/schema/valid/` now holds it there so a
future tightening cannot quietly take it away.

**MCR-SEC-014 (INFORMATIONAL) — computed member access reached a render sink.** `el("x")["inner"+
"HTML"] = raw` was rated safe with `audited = 0`: every Q17 rule reads the dotted spelling, and the
spliced name never appears in the source for a regex to find. Marcus accepted either closing it or
recording it, provided the gate was not described as unbypassable. **Closed**, because the check is
mechanical and has no false positive on the code it guards. Q17 now reads the property expression of
every computed member assignment and refuses three things: a bracketed render-sink name
(`obj["innerHTML"]`), a property expression it cannot read (built from literals or operators), and a
sink name fused out of string literals — inline, through a variable, or across two statements
(`k = "inner"; k += "HTML"`). Identifiers, numbers and dotted/indexed chains are allowed, which is
what `out[fields[i].name] = …` in `fieldTypeMap()` and `out.resolved[f.name] = …` in
`validateSpec()` are; a gate with a false positive on the code it guards is a gate somebody switches
off, so a safe control fixture holds that line. The residual the rule genuinely cannot see — a
property name produced at run time from data rather than from string literals — is printed in Q17's
own PASS output instead of being left for the next reviewer to discover, and written into
`docs/CODE_STANDARDS.md` §1.

**Tests.** Four new render-bypass fixtures (`bypass_12`..`bypass_15`) plus
`safe_control_computed_index.js`; an invalid and a valid schema fixture for the conditional literal;
four new never-half-formed harness vectors across all four releases (60 → 76 checks). Gates after the
fix: `python3 qa.py` **QA GATE: PASS**, `python3 -m unittest discover -s tests` **51 tests OK**,
`node tests/hostile_harness.js` **63,536 checks, 0 FAILED**, byte-identical rebuild
(`5fb9b7adfd8b60fe…`).

### Fixed — security review MCR-SEC-001..012 (2026-09-17, branch `salm/milo/shell-assembler`)

Marcus Reed's security review of `4184ea8` returned **DENY with `block_flag`** — 3 HIGH, 5 MEDIUM,
2 LOW, 2 INFORMATIONAL. Every finding is addressed here. None of them was reachable from the shipped
UI (the form renderer is CR-T-25), and that is the reason they close now rather than later: the
assembler is the contract fourteen P0 tool categories of templates will be written against, and a
gate that clears a contract because nothing calls it yet is not a gate.

**MCR-SEC-001 (HIGH) — rich-rule grammar injection.** `composeRichRule()` carried a comment asserting
that no validated value could contain a double quote "because no field type's allow-list admits a
quote character". Two types did: `comment` (every printable character) and `enum` (whatever a content
author lists). A `comment`-typed field in a rich-rule slot could close an attribute and open new
elements — the review's reproduction installed an `accept` clause and a logging clause past the
`drop` the operator had selected, with shell quoting fully intact, so the hostile-input harness rated
it QUOTED-SAFE. Fixed structurally: `RICHRULE_SLOT_TYPES` lists the closed-grammar field types each
slot accepts and `comment`/`enum` are deliberately absent, because rich-rule attribute syntax has no
escape sequence for a quote inside an attribute value — there is no correct encoding, so there is no
free-text path into a rich rule at all. A character-level re-check at composition time is the second
layer. The false comment is replaced with the reasoning.

**MCR-SEC-002 (HIGH) — never-half-formed, per template rather than per field.** An optional field
that was not supplied made its token vanish and the command still assembled: `chown 'apache'
'/var/www'` became `chown '/var/www'` (the path promoted into the owner argument), and a literal that
owned a value could be left dangling as `--add-forward-port=port=443:proto=tcp:toaddr=` — the exact
artefact threat-model-v1 §3.4 names as its reason for existing. Token dropping is now declared:
`optional:true` is mandatory, a positional token may only drop if every later positional drops with
it, `{lit:"...", requires:"field"}` binds a literal to its value, and a version-gated field takes the
same path so one template cannot be well-formed on RHEL 9 and mis-positioned on RHEL 8.

**MCR-SEC-003 (HIGH) — the clipboard header.** "Copy with comment" built `"# label: " + raw content`
and copied it; none of the header is rendered, so a newline in `intent` put a second, never-displayed
line into a root shell — the reproduction copied `rm -rf /var/log/audit` off a screen showing one
title line, with blast green, because `blastFor()` only looked at `res.command`. Four independent
layers now: `headerSafe()` flattens every value to single-line printable text; `commentPayload()`
splits on CR/LF/CRLF anyway and prefixes **every** line with `# `, refusing to compose at all if the
command is not single-line; `blastFor()` runs over the whole payload so the banner fires before the
click and the acknowledgement covers what the clipboard receives; and `extract/schema.py` rejects any
control character in `intent`, `verify`, `undo` and every `stig[]` string, failing the build instead
of the clipboard. The header is also rendered as a read-only preview of exactly what gets copied
(threat-model-v1 §9).

**MCR-SEC-004 (MEDIUM) — the Q17 render audit had five mechanical bypasses** (`innerHTML +=`,
`html = html + x`, an intermediate accumulator under another name, `insertAdjacentHTML`,
`outerHTML`), all rated PASS. Now: forbidden sinks are refused outright (those two plus
`document.write`/`writeln`, `createContextualFragment`, `srcdoc=`), `.innerHTML` may only be an
assignment target, `setAttribute()` must name its attribute with a readable literal and may not name
`href`/`src`/`srcdoc`/`style`/`action`/`formaction`/`xlink:href`/`on*`, the accumulator set is
derived from the source and closed transitively, `=` and `+=` are audited alike, and `is_literal()`
parses the literal instead of comparing first and last characters. 13 negative fixtures under
`tests/fixtures/render-bypass/` prove each construct now fails; audited expressions 24 -> 85.

**MCR-SEC-005 (MEDIUM) — the rich-rule test's hostile-type parameter was dead.**
`richRuleSpec(hostileField, hostileType)` was only ever called as `richRuleSpec(null, null)`, which
is why MCR-SEC-001 survived 15,392 checks. It is now driven with every field type in every slot of
two rich-rule shapes, and the harness gained the second oracle the finding asked for: a rich-rule
parser that asserts the composed rule's element count, element order, attributes and ACTION equal the
operator's intent. Both oracles carry negative controls — the injected rule from the review and an
action-only swap must be caught — so the oracle has been seen to fail before it is believed.

**MCR-SEC-006 (MEDIUM) — `template[].flag` and `template[].lit` are trusted content, not unchecked
content.** `extract/schema.py` had no `template`/`fields`/`richRule` shape at all. It has one now —
field names and types, enum options, version subsets, token shapes, both allow-lists
(`^-{1,2}[A-Za-z0-9][A-Za-z0-9-]*$` for flags, `^[A-Za-z0-9_./=:,+-]+$` for lits), `requires:`
resolution, rich-rule slot types, MCR-SEC-002's droppability rules, and declared-but-unused fields.
The same two allow-lists are enforced at run time, where a bad token makes the whole template `null`.
`tests/test_schema.py` asserts the field-type list, the rich-rule slot table and both regexes are
identical on both sides, so the mirrored tables cannot drift silently.

**MCR-SEC-007 (MEDIUM) — the data island's `</` escaping.** It closed `</script>` and nothing else:
`<!--` followed by `<script` puts the HTML tokeniser into script-data-double-escaped state, where
`</script>` stops terminating the element and the island's closing tag, the app script and its own
"Not built yet" fallback are swallowed as text — a silent denial of use on a jump box, with
verbatim-embedded DISA fix text as the delivery vehicle. `build.py` now escapes every `<` and `>` as
`\u003c`/`\u003e`: valid JSON, reversible, one rule instead of a list of sequences. Q1 asserts no raw
`<` or `>` survives; `qa.py` parses the island without repairing it first.

**MCR-SEC-008 (MEDIUM) — a destructive pattern could not match across a value boundary.** `shQuote()`
inserts a quote at every literal-to-value boundary, so the first reviewer to add `rm -rf /` to
`dangerous.json` would have silently disabled that row. `blastFor()` now matches both the raw command
and its unquoted projection. `rm -rf /` is in the table (8 -> 9 patterns), the constraint is
documented in `_meta` where a reviewer authors, and the harness asserts every row fires on a
synthetic assembled command — a pattern that can never fire fails the build.

**MCR-SEC-009 (LOW)** — U+2028, U+2029 and U+2065 added to `INVISIBLE_RE`, to Q17's trojan-source
ranges, and to the fixture's `invisible character` class (52 -> 55 vectors).

**MCR-SEC-010 (LOW) — DECISION: `yamlQuote()` removed, not wired.** It was correct, used the right
YAML `''` idiom, and had no call site: `assembleCommand()` has no YAML output path, so Q18's
quoting-domain gate was passing on a domain that did not exist. A dead escaper reads as "Ansible YAML
output is proven safe", which the CR-T-25 review would have inherited as a false clean bill. The
gate is now explicitly **shell-only** until the Ansible generators land (CR-T-17+), the Q5 marker
reports PENDING rather than PASS, and two gates hold the door for its return: `qa.py` fails if a YAML
quoter appears in the shipped shell, and the harness refuses to run if one appears in the assembler
block without a YAML-parsing oracle beside it.

**MCR-SEC-012 (INFORMATIONAL) — one rendered-state object.** `currentResult()` was called
independently by `renderEditor()`, `renderBlastBanner()`, `renderInspector()` and `doCopy()`. `RESULT`
is now computed once per interaction, keyed on the state assembly reads and dropped at the top of
`renderAll()`; the gutter, the banner, the inspector, the clipboard preview, `doCopy()` and the
CR-T-28 exporter read it (threat-model-v1 §9).

**MCR-SEC-011 (INFORMATIONAL)** needed no code change: it records that no user-supplied value reaches
the assembler in the shipped UI. Condition **C10** is also closed — Q17's trojan-source scan now
covers the data island as well as the hand-written shell, because DISA fix text is rendered *and*
copied into evidence.

Gates on this work: `python3 build.py && python3 qa.py` -> Q1-Q18 PASS; `node tests/hostile_harness.js`
-> 63,536 checks, 0 failures, 27 invariants, 276 positive controls;
`python3 -m unittest discover -s tests` -> 51 tests OK; two builds byte-identical; verified in Chrome
with zero console errors.


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
