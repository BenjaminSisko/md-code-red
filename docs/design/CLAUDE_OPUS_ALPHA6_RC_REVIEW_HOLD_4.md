# HOLD — MD CODE RED v1.0.0-alpha.6 exact-head review

## 1. Exact commit and clean-tree confirmation

| Item | Value |
|---|---|
| Reviewed HEAD | `88b233b8542b0c2189c86cab440d25dfb0e90020` on `codex/alpha6-responsive-ux`, 8 commits ahead of origin |
| Implementation commit | `19274c4f99a6a9b73ffd504d2bc2053957453a45`. `88b233b` changes only 7 files, all under `docs/`. |
| Working tree before | `git status --porcelain --untracked-files=all` was empty. The 64 ignored entries were all pre-existing `__pycache__/` files. No stashes. |
| Working tree after | Identical: HEAD unchanged, 0 changes, the same 64 ignored entries, no stashes, artifact hashes unchanged |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`, **8,913,823 bytes**, SHA-256 **`69ec4e6bcce72fc1ad4c05f632702120b4d983527a93d6c917da372c6568d18c`**, matching its sidecar |
| Sidecar / provenance SHA-256 | `4f9e6081…dcd3ea90` / `df95b0b4…86ee2e8c` |
| Provenance commit | `git_commit: TAG_COMMIT_PLACEHOLDER`, as expected until the tag exists |
| Content fingerprint | **`e377c108f895bf4ca26b476e26f246e0d6b80a2156f1b5a1cea0039019224225`** |

**Method.** Strictly read-only. All builds, gates and tests ran in two `git clone --no-hardlinks` copies under `/tmp/mdcr-r4/`. Browser work used isolated headless Chrome 154 profiles and a `127.0.0.1:8899` server rooted in the scratch clone; both were stopped afterwards. Probe scripts and results remain under `/tmp/mdcr-r4/` for reproduction.

## 2. Executive verdict

**HOLD.** There are no Blocker or Critical findings. **Three Major and seven Minor findings remain.**

**Independently confirmed as sound:**
- **Build and artifact:** the HTML, sidecar and placeholder provenance rebuild byte for byte at `88b233b`. Q1–Q26 plus the JavaScript check pass.
- **Tests:** 429 unit tests pass; the closure test passes 41/41 on both the template and the artifact.
- **Browser audit:** I reproduced 889/889 in both `file://` and HTTP mode, with zero exceptions and zero console errors. My records match the committed records assertion for assertion, except for timing and heap figures.
- **Repository hygiene:** Gitleaks is clean over 205 commits and the directory; the release facts are current; `git diff --check` is clean.
- **Prior findings:** R3-1 through R3-11 are fixed for the paths each one named, which I verified with real CDP key, text and mouse input.

**Why HOLD.** Real pointer and keyboard input exposes defects the audit cannot see, because it activates controls programmatically:
- **R4-1:** after a field edit, the first click on Copy is discarded, and a stale "Copied to clipboard" message sits over a different clipboard payload.
- **R4-2:** the alpha.6 trust label "Read only" is shown on twelve catalogue entries that change state. This is the same class as HOLD-1 M-2 and HOLD-2 N-1.
- **R4-3:** the Git clone form takes a free-text repository URL that accepts an `ext::` command. This contradicts the closed-grammar claim, the same class as HOLD-1 M-1.

The seven Minor findings are residuals of R3-4, R3-5, R3-10, R3-11 and HOLD-1 m-3, plus documentation that was not updated after the third review.

## 3. Findings by severity

### Blocker
None.

### Critical
None.

### Major

**R4-1. After a guided text field is edited, the first click on a result control is discarded. A Copy click then leaves the previous command on the clipboard under a stale "Copied to clipboard" message.**

- **Where:**
  - `document.addEventListener("change",onFieldChange)` (`template.html:6059`).
  - `onFieldChange()` (`:6023-6054`) handles the deferred `change` event that a text input fires on blur. The `input` handler (`:6055-6058`) has already stored the identical value, yet the change event re-renders everything again: `renderGeneratorResult()` (including `#blast-banner`), `renderPipelinePanel()`, `renderInspector()` and `renderStatusBar()`. Nothing preserves the focus or the pointer target on this path.
  - `toast()` (`:3794-3797`) sets `STATE.toast`, nothing ever clears it, and `renderStatusBar()` (`:5504`) keeps showing it.
- **Observed** (real CDP mouse and key events, identical in `file://` and HTTP):
  - **Copy after typing** (grep form): the event sequence is `mousedown:copy → change:pattern → mouseup:copy`, with no `click`. Nothing is copied.
  - **Stale clipboard:**
    - After a successful copy of `grep 'laundry' '/etc'`, I edited the pattern to `laundry-new` and clicked Copy once.
    - The screen shows `grep 'laundry-new' '/etc'`.
    - The clipboard still holds `grep 'laundry' '/etc'`.
    - The status bar still says "Copied to clipboard — RHEL 8".
    - Copy with comment behaves the same way.
  - **Acknowledgement after typing** (red Git discard): the first click on "I have reviewed this command" is lost and focus falls to `<body>`.
  - **Add to pipeline** (journalctl): the first click on "Add current command as a stage" is lost.
  - **Tab after typing** (kill form): Tab out of the edited PID field fires `change`, and focus lands on `<body>`.
  - **Pre-existing:** the archived alpha.5 artifact drops the first Copy click the same way, but the defect ships in this candidate.
- **Impact:**
  - The primary flow, fill a form and then click Copy, silently fails. After any earlier copy, the operator sees a success message while the clipboard holds a different command, which breaks the product's "copy exactly what was reviewed" contract.
  - It is Major rather than Critical because the payload has no trailing newline, so the stale command is visible in the terminal before Enter.
  - Keyboard users lose focus when tabbing out of the last field (WCAG 2.4.3).
- **Correction:**
  - Make the change path idempotent: return early when the new value equals the stored `STATE.formValues[name]`, or ignore `change` from text inputs entirely, since `input` already covers them.
  - Clear `STATE.toast` whenever the result key changes.
  - Add CDP tests:
    - type, then one real mouse click on Copy, and assert the clipboard equals the displayed command;
    - Tab from the last field and assert focus lands on the next control;
    - after an edit, assert no stale "Copied" message remains.

**R4-2. "Read only" is shown for twelve catalogue entries that write files or change state.**

- **Where:**
  - Green maps to "Read only" in the guided trust bar (`template.html:5246`) and in `renderEditor()`'s static trust bar.
  - `USER_GUIDE:185` defines green as "(read-only)".
  - The ratings come from `content/commands.json`, for example `gen-git-clone` at `:7466` with its undo text at `:7465`.
- **Observed** (UI, RHEL 8). All twelve show **Read only**, and every entry's own Undo or Recover text reverses a change it made:

  | Entry | Command | Its own undo text |
  |---|---|---|
  | `cp-copy` | `cp -a /etc/httpd /root/httpd.bak` | Delete the copy at the destination |
  | `mkdir-create-directory` | `mkdir -p /opt/tool/etc/conf.d` | `rmdir` / `rm -r` |
  | `ln-links` | `ln -s … /opt/tool/latest` | Remove the link |
  | `git-clone` | `git clone https://…` | Delete the cloned directory |
  | `gen-git-clone` | `git clone '<repo>' '<dir>'` | Delete the new clone directory |
  | `git-add` | `git add -p` | `git restore --staged` |
  | `git-commit` | `git commit -m …` | `git reset --soft HEAD~1` |
  | `git-switch-branch` | `git switch …` | `git switch -` |
  | `git-stash` | `git stash push …` | `git stash drop` |
  | `git-tag` | `git tag -a …` | `git tag -d` |
  | `git-bisect` | `git bisect start` | `git bisect reset` |
  | `a-fetch` | Ansible `fetch … dest=evidence/` | `rm -r evidence/` |

- **Impact:**
  - This is the trust-label defect HOLD-1 M-2 and HOLD-2 N-1 raised (both Major), still present across the catalogue.
  - Two entries write under `/opt`, which the pipeline composer refuses outright as an execution sink (`PIPE_EXEC_SINK_DIRS`, `:2134-2140`).
  - The ratings pre-date alpha.6; the false "Read only" wording is new in alpha.6.
- **Correction:**
  - Rate these entries yellow, or stop rendering green as "Read only".
  - Add a schema or QA gate: a green entry's undo text must be of the "nothing to undo" kind.
  - Add browser assertions for a sample of these entries.

**R4-3. The Git clone repository is free text, so an `ext::` transport value assembles as a "Read only" command.**

- **Where:**
  - `content/commands.json:7440`: the `repository` field is type `comment`, which admits any printable text (`template.html:916`).
  - `:7466`: the entry is green.
  - The claims it contradicts: "SSH, SCP, rsync, URL … values use purpose-specific closed grammars" (`SECURITY_REVIEW:17-18`, `CHANGELOG:9-12`).
- **Observed:** on RHEL 7 and RHEL 8, repository `ext::sh -c touch% /tmp/pwned` produces `git clone 'ext::sh -c touch% /tmp/pwned'`. The trust bar says "Read only", there is no banner, and Copy is enabled.
- **Mechanism:**
  - `git-remote-ext(1)` runs the given `<command>`.
  - Upstream Git has defaulted `ext` to "never" only since 2.12; RHEL 7 ships Git 1.8.3.1.
  - With local Git 2.53 in `/tmp`, the default policy refused ("transport 'ext' not allowed"). With `ext` allowed, which was the pre-2.12 default, the command ran and created the marker file.
  - Not executed on a RHEL 7 host.
- **Impact:** this is the second-interpreter problem of HOLD-1 M-1. A value displayed as one quoted operand is re-parsed by Git into a command, under a "Read only" label.
- **Correction:**
  - Give the repository field a closed Git-URL grammar: `https://`, `ssh://`, scp-style `user@host:path`, or an absolute local path. Refuse `::`, leading `-`, whitespace and `%`.
  - Add hostile vectors that model Git's transport parsing.
  - Re-rate the clone forms (see R4-2).

### Minor

**R4-4. The `/var/run` alias bypasses the `/run/systemd/system` execution-sink refusal (residual of R3-4).**
- **Where:** the alias map (`template.html:2188-2195`) covers only `/bin`, `/sbin`, `/lib` and `/lib64`. `/run/systemd/system` was added to the sink list (`:2140`).
- **Observed:** this is the shipped assembler, for pipeline `>`, `curl -o` and scp alike.
  - `/run/systemd/system/x.service` and `…/sshd.service.d/o.conf` are **refused**.
  - The same directory spelled `/var/run/systemd/system/…` is **yellow**, with no banner. On RHEL 7–10, `/var/run` is a link to `../run`.
  - Less severe, because they are still red and still gated: `/etc/rc.local` and `/etc/rc3.d/…` are red, while their `/etc/rc.d/…` targets are refused.
- **Impact:** contradicts `SECURITY_REVIEW:21` and `USER_GUIDE:145-146` ("systemd … refused").
- **Correction:** add `/var/run` → `/run` and the `/etc/rc*.d` links to the alias map, with test vectors for each.

**R4-5. Remote-directory and user-startup classification still depends on spelling and on a fixed list (residual of R3-5).**
- **(a) The directory rule keys on a trailing slash** (`template.html:1706-1713`):
  - `rsync … '/etc/app/' 'alice@host:/tmp/app/'` is red, but `'alice@host:/tmp/app'` is yellow. For a directory source, rsync performs the same writes either way.
  - `scp '/tmp/.bashrc' 'root@host:/var/www'` is yellow, while `…/var/www/` and `…/var/www/.bashrc` are red.
  - The reason text says "(red target class)" for `/tmp/app/`, which attributes the rating to the wrong cause.
  - Every canonical `rsync src/ host:/dst/` is now red; the golden row was changed to red in `19274c4`.
- **(b) Startup files are still an enumerated list** (`isSensitiveUserTarget()`, `:2219-2232`):
  - `.zshrc` and `.zprofile` are red.
  - `.zshenv` (which zsh reads on every start), `.zlogin` and `.zlogout` are yellow.
  - X session files (`.xinitrc`, `.xsession`, `.Xclients`, `.xprofile`) and `~/.config/environment.d/` are also yellow.
- **Impact:** contradicts `SECURITY_REVIEW:21-22` and `USER_GUIDE:143-145`.
- **Correction:**
  - For scp, rate the stronger of the destination itself and the destination joined with the source's file name.
  - For rsync, rate a directory source's destination as a directory regardless of the slash, and state that reason.
  - Rate every dotfile directly under a home directory red, or narrow the claim.

**R4-6. A STIG rule opened from search shows no rule text in the default layout (residual of R3-10).**
- **Where:**
  - alpha.6 changed the Inspector default to off (`<body … data-inspector="off">`, `template.html:388`); alpha.5 defaulted it on.
  - A standalone rule page still says its text is "in the Inspector panel on the right" (`:5025-5028`).
  - `renderStigPanel()` writes only to the Inspector and to the print panel, which is hidden on screen.
- **Observed:**
  - Fresh session at 1440×1000, with or without a pipeline: the page shows only `RHEL-08-010000` and that sentence. The status bar reads "Inspector: Off". No check or fix text is visible.
  - TC-PIPE-CONTROL-002 asserts the panel's text, not that it is visible.
- **Impact:** Journey 2 (`USER_GUIDE:160-170`) and the Compliance rail open to an empty page. `QA_REPORT:48-49` ("remain visible") is true only once the Inspector is opened.
- **Correction:** show the rule card in the editor, or auto-open the Inspector for standalone rules. Assert on-screen visibility in the audit.

**R4-7. The scp and rsync runbooks do not protect existing remote files (residual of R3-11).**
- **Where:**
  - rsync Recover (`commands.json:5846`): "Restore … from the backups kept before the run". The rsync preflight (`instructional.json:1865`) only asks for a dry run, and no step keeps backups.
  - scp Recover (`commands.json:5784`) leads with "Delete the copy at the destination". It is not bound to the destination field, and its preflight is advisory (`instructional.json:1827`).
- **Impact:** the rsync recovery depends on backups the runbook never creates. This is inconsistent with the bound backup-and-restore fix made for curl and wget.
- **Correction:**
  - For rsync, add a bound preflight that keeps backups (for example `--backup --backup-dir=<dir>`).
  - For scp, add a bound step that preserves the existing remote file, and change Recover to restore first.

**R4-8. Placeholder text contrast is below 4.5:1 in both themes (WCAG 1.4.3).**
- **Where:** there is no `::placeholder` rule in `template.html`, so Chrome's default `#757575` is used.
- **Observed:** in a rendered sweep of 11 UI states in both themes, with translucent backgrounds composited, placeholders measured 4.33–4.41:1 (light) and 4.19–4.32:1 (dark). Affected text includes:
  - example values such as `laundry` and `sshd.service`;
  - the pipeline file box's only format hint, "absolute path".

  All other visible text passed. The three R3-9 fixes measured 8.25, 6.19 and 5.55:1.
- **Correction:** add `::placeholder{color:var(--text-muted);opacity:1}` and extend the audit to a full rendered contrast sweep.

**R4-9. Fields that are not firewalld services report "is not a valid firewalld service name" (residual of HOLD-1 m-3).**
- **Where:** `FIELD_TYPES.service` (`template.html:890`) is used for:
  - the Git clone directory (`commands.json:7445`);
  - the podman container;
  - LVM logical and volume group names;
  - the NetworkManager connection.
- **Observed:** "directory: is not a valid firewalld service name", "container: …" and "name: …".
- **Correction:** give each a purpose-specific type with an accurate label.

**R4-10. Documentation and evidence were not updated after the third review, or overstate it.**
- **`USER_GUIDE:199-204`:**
  - It still says a red rating comes from "an entry's own content, or from the destructive-pattern table", and that the banner names "which pattern matched".
  - It omits write targets, remote directories and xargs children. R3 asked for these lines to be corrected.
  - Both `USER_GUIDE` and `CHANGELOG` are unchanged since `9d53a4c`.
- **The CHANGELOG's alpha.6 section** (`:5-35`) is the change record named in the provenance manifest, yet it records none of the fourth-round behaviour changes:
  - remote directory destinations are now red, so routine rsync syncs require acknowledgement;
  - any change clears the destructive acknowledgement;
  - usrmerge alias classification;
  - the new `.mdcr-before-download` backup preflight;
  - the dark-theme primary-button text colour;
  - STIG panel behaviour beside a pipeline.
- **Claims contradicted by the findings above:**
  - `SECURITY_REVIEW:17-18` (closed URL grammars), contradicted by R4-3.
  - `SECURITY_REVIEW:20-23` (sinks, startup files, directories), contradicted by R4-4 and R4-5.
  - `QA_REPORT:47` (partial re-renders keep focus), contradicted by the R4-1 Tab path.
  - `QA_REPORT:48-49` (searched STIG rules remain visible), contradicted by R4-6.
- **Overstatement:** `QA_REPORT:26` calls the typing matrix "Real-keystroke", but it sends only CDP `char` events, never keydown or keyup.
- **Correction:** update these documents after the fixes.

**Non-blocking observations** (not counted as findings):
- With a complete pipeline, the first keystroke in an unrelated form announces "Command ready" spuriously. The starting state is seeded from `assembleCommand` (`:5342`), but the live check reads the pipeline result.
- The pipeline banner repeats the same write-target reason twice.
- When a pipeline stage is red only by catalogue, the fallback text does not name the stage.
- The download preflight keeps an older `.mdcr-before-download` copy and never removes backups.
- The `.ssh` and `.config` regular expressions contain unescaped dots; they only match more, never less.
- Ctrl+Shift+C and Ctrl+E act on a pipeline that is not shown while a standalone STIG page is open.
- Other systemd execution directories (`system-generators`, `system.conf.d`, `/etc/systemd/user`) are rated red rather than refused.

## 4. Closure of every prior HOLD finding

### HOLD 1 (`CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD.md`)

| ID | Status | Evidence at `88b233b` |
|---|---|---|
| M-1 (remote shell injection via scp, rsync, ssh) | **Closed** | `isRemotePath()` (`:810`) closed grammar; ssh uses `-l` plus a hostname type; rsync `-s`; the closure test refuses `;id` and `$(id)`; Q18. A different free-text URL remains (R4-3). |
| M-2 (curl/wget "Read only") | **Closed for curl/wget** | Both at least yellow; http(s) only; sinks refused; `/etc/hosts` is red with a write-target reason. The same class persists elsewhere (R4-2). |
| M-3 (hardcoded runbook values) | **Closed** | Every runbook placeholder binds a closed-grammar field or a computed value; none is free text or version-gated. TC-RUNBOOK-001..003 and TC-RUNBOOK-DOWNLOAD-001 pass. |
| M-4 (pipelines "Verified") | **Closed** | "Composed — not host-verified" in the trust bar, status bar, Inspector and export |
| m-1 (stale counts) | **Closed** | 429 / 145,345 / 23,032 / 889 are current; the release-facts check passes |
| m-2 (evidence wording) | **Closed** | `git diff --check` exits 0; Gitleaks is clean. New overstatements are in R4-10. |
| m-3 (field types) | **Closed for cited items** | Other misuses of the `service` type remain (R4-9) |
| m-4 / m-5 / m-7 / m-8 | **Closed** | Recovery entries both yellow; Home routing (TC-HOME-002); pipeline UX; "GNU grep 2.20-3.11" |
| m-6 (contrast) | **Closed for cited colours** | Placeholders fail (R4-8) |
| m-9 (test strength) | **Partly closed** | Real-input checks were added, but clicks after an edit (R4-1) and on-screen visibility (R4-6) are still untested |

### HOLD 2 (`…_HOLD_2.md`)

| ID | Status | Evidence |
|---|---|---|
| N-1 (pipeline writes "Read only") | **Closed for pipeline targets** | Residuals are R4-4 and R4-5; the same label problem exists in the catalogue (R4-2) |
| M-4(A) / M-4(B) | **Closed** | Q16 binds all 18 receipts by hash; any typed edit shows Not host-verified; an incomplete pipeline gives "Nothing to export" |
| m-1 residuals, N-4, N-7 | **Closed** | Per-stage flag attribution and `Requires: root` in the export; SIGTERM text; `export -n <variable>` is bound |
| N-2(a) / N-2(b) | **Closed** | Pipeline export and clipboard header say "STIG/control identity: none"; a searched rule is absent from the export |
| N-3 (remote destinations unrated) | **Closed for file paths** | Directory residual is R4-5(a) |
| N-5 (focus, live region, badge contrast) | **Closed for cited paths** | Tab out of an edited field is part of R4-1 |
| N-6 (evidence and docs) | **Closed for cited items** | New gaps are in R4-10 |
| Observations | **Unchanged, non-blocking** | grep needs a file argument; CI pins actions by tag; generic `man git` rows |

### HOLD 3 (`…_HOLD_3.md`)

| ID | Status | Evidence (real CDP key, text and mouse input; both delivery modes) |
|---|---|---|
| R3-1 typing into pipeline controls | **Closed** | `/tmp/x.log` typed with full keyDown/keyUp sequences: value, caret, mid-string insert and Backspace all correct; `/` no longer opens the palette; `insertText` works; Tab and Shift+Tab move correctly; `-n` accepts `25`; Space on `-0` and `-I` keeps focus; 0 exceptions |
| R3-2 banner reasons | **Closed** | curl/wget `/etc/hosts` and pipeline `/root/.bashrc` banners show "File write target …"; xargs adds XARGS-RED; the catalogue fallback appears only when an entry or stage is catalogued red. Directory wording is in R4-5. |
| R3-3 acknowledgement binding | **Closed** | Typed edits, operator changes, stage edits, target typing, Edit and version changes all clear it and disable Copy; the Library acknowledgement resets per record |
| R3-4 usrmerge aliases | **Closed for `/bin`, `/sbin`, `/lib`, `/lib64`** | `/lib/systemd/system` refused, `/lib64/libc.so.6` red. `/var/run` is R4-4. |
| R3-5 sensitive targets and directories | **Partly closed** | Any `.ssh` path is red, as are `/srv/app/.ssh/…`, `/var/www/.bashrc`, `.bash_logout`, `.k5login`, autostart, user units and `…:/root/`. Residuals are R4-5. |
| R3-6 pipeline status bar | **Closed** | Switches between "Pipeline incomplete" and "Composed — not host-verified" on every pipeline field edit |
| R3-7 focus | **Closed for cited paths** | All 7 palette hit kinds focus the opened heading; acknowledgement (Space), Favorite (Enter), gutter, Add, Redirect and Move keep focus |
| R3-8 first completion announced | **Closed** | 8 single-field forms announce "Command ready" on the first keystroke and "incomplete" when cleared, using the same live node |
| R3-9 rendered contrast | **Closed** | 0 failures in visible text across 11 states in both themes; placeholders are R4-8 |
| R3-10 searched STIG rule beside a pipeline | **Closed for the suppression rule** | The rule renders and does not leak into export or the clipboard; hidden by default is R4-6 |
| R3-11 recovery text | **Closed for curl/wget, the scp title and rsync `--delete`** | Bound backup preflight and restore-first Recover; Copy Recover is gated on red. scp/rsync residuals are R4-7. |

## 5. Commands and tests run

| Command or method | Result |
|---|---|
| `git rev-parse`, `status --porcelain --untracked-files=all --ignored`, `stash list` (start and end) | Exact HEAD; clean both times |
| `git show --stat 19274c4 88b233b`; `git diff --stat 9d53a4c HEAD`; `git diff --name-only 19274c4 88b233b` | `88b233b` changes docs only |
| `stat` and `shasum -a 256` on `dist/*` | All reported facts match |
| Scratch clone: `python3 build.py` then `extract/make_provenance.py` | HTML, sidecar and provenance **byte-identical** |
| `PYTHONDONTWRITEBYTECODE=1 python3 qa.py` | **PASS**, Q1–Q26 plus JS (details below) |
| `python3 -m unittest discover -s tests -v` | **429 run, OK**. The first attempt tripped the Q1 artifact-freshness check because clone timestamps were equal; I refreshed the `dist/` timestamps without changing content. |
| `node tests/test_alpha6_review_closure.js` on the template and the artifact | **41/41** both |
| `tools/generate_release_facts.py --check`; `git diff --check` (from `origin/main` and from `9d53a4c`) | PASS; exit 0 |
| `shasum -c` on the alpha.1–5 archives and `stig-src` | All OK; archived alpha.5 HTML equals the tag's bytes (`c64337a2…`) |
| `gitleaks git` and `gitleaks dir` (8.30.1) | 205 commits; no leaks |
| Repository audit script, `file://` and HTTP (only the output path changed) | **889/889 each**, 0 exceptions, 0 console errors; identical to the committed records apart from timing and heap. One initial `file://` run scored 888/889 only because I had not supplied the `AUDIT_*` counts TC-DOCS-002 needs. |
| CDP real-input probes (keyDown/keyUp with text, `insertText`, mouse) | R3 closure verification, R4-1, R4-6 |
| Assembler lifted from the artifact | Classification matrix for R4-3 to R4-5; reason lists |
| Rendered contrast sweep (11 states, both themes) | R4-8 |
| Local Git `ext::` demonstration in `/tmp` | Default policy refuses; with `ext` allowed, the command runs |
| alpha.5 artifact comparison | R4-1 is pre-existing |

**Q18 detail:**
- 145,345 hostile-input checks: 142,993 refused outright and 2,352 accepted but confined to a single quoted argument.
- 23,032 pipeline checks.
- 332 operator-seam checks.
- 717 oracle comparisons.
- 11 negative controls.
- 100 interpreter checks.
- 36 naming checks.
- 232 one-stage checks.
- 68 redirect-target checks.

**Q26:** 869 commands checked against 420 grammar rows. **Q16:** 18 receipts.

**Not performed:** screen-reader sessions, other browsers, execution on real RHEL hosts, and CI.

## 6. Residual limitations that do not block this candidate

- **Signing and provenance:** the release is unsigned, and provenance stays at `TAG_COMMIT_PLACEHOLDER` until the exact tag target exists, after which the artifact is rebuilt, retested and stamped.
- **Host verification:** receipts cover RHEL 7/8/9/10 as 0/9/0/9.
- **Flag data:** RHEL 7 flags come from a UBI7 container. The flag dictionaries carry no explanations; 336 of the 348 curated flags are explained.
- **Reference material:** about 98.68% of mined reference records are unrated. They are kept separate, and copying them requires an acknowledgement.
- **Pipeline semantics:**
  - a grep stage needs a file argument;
  - required privilege is not derived from write targets;
  - enumerated sink lists cannot cover every execution path.
- **Accessibility, unverified:** whether screen readers re-announce the re-created status toast, or the pipeline field that is re-created on every keystroke.
- **CI and toolchain:** CI pins its actions by tag rather than by commit, and its toolchain differs from the one recorded in provenance. The Git grammar rows for RHEL 7 and 9 cite a generic `man git`.

## 7. Final release recommendation

**HOLD. Do not tag, merge for release, or publish `88b233b`.**

The prior reviews' core work holds up under real input: the closed grammars, pipeline trust separation, receipt binding, acknowledgement binding, typing in the pipeline controls, focus restoration, the announcer, the cited contrast pairs and reproducibility. Two promises alpha.6 makes are still broken:
- what you copy is what you see (R4-1);
- the trust label tells the truth (R4-2, R4-3).

To reach PASS:
1. Fix R4-1 to R4-3. Add tests that use real pointer input (edit a field, then one click on Copy, then check the clipboard and the message), and a catalogue gate that stops green entries changing state.
2. Resolve R4-4 to R4-10, or formally risk-accept them and disclose them in the `USER_GUIDE` Known Limitations and the `SECURITY_REVIEW`.
3. Update `USER_GUIDE`, `CHANGELOG`, `SECURITY_REVIEW` and `QA_REPORT`.
4. Rebuild, rerun Q1–Q26, the unit suite, the hostile-input harness, both browser modes and Gitleaks, then repeat the exact-head review.

---

*Not part of the review: several connectors (including Figma, Google Drive and GitHub) need authorization in claude.ai connector settings or via `/mcp`, and a few others failed to connect. None was needed here. The scratch clones and probes under `/tmp/mdcr-r4/` can be deleted after this report has been reviewed.*
