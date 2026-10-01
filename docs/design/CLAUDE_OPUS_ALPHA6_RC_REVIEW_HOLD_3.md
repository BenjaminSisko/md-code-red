# HOLD — MD CODE RED v1.0.0-alpha.6 exact-head review

## 1. Exact commit and clean tree

| Item | Value |
|---|---|
| HEAD | `9d53a4ca514a8455a48dbab4e9d1db05ba7fd18b` on `codex/alpha6-responsive-ux` |
| Push state | 6 commits ahead of `origin/codex/alpha6-responsive-ux` (`d0e79c9`); `origin/main` = `78ac717` |
| Working tree | Clean before and after the review: `git status --porcelain=v1 --untracked-files=all` is empty, there are no stashes, and the only ignored paths are the pre-existing `__pycache__/` folders. HEAD and the artifact hash were unchanged at the end. |
| Build inputs | Last changed in `fe2c6d8`. `9d53a4c` changes 9 files, all under `docs/`. |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`, 8,908,425 bytes |
| Artifact SHA-256 | `e3920993af6f7db57bbdf6fdd8c3ef4a53e1b5de4263f80a4cb2b956c1f4bdb3` |
| Sidecar SHA-256 | `be52332c…6c21b07` |
| Provenance SHA-256 | `e137f440…a924ae23` (`TAG_COMMIT_PLACEHOLDER`) |
| Content fingerprint | `3e1282a0…093df3b1` |

All of these values match `BQP_SUMMARY`, `RELEASE_REPORT`, the RC QA HTML and both RC JSON records.

**Method.** Nothing in the repository was modified. Builds, gates and tests ran in a `git archive` copy and a full `git clone` under `/tmp`. Browser work used an isolated headless Chrome 154 profile and a `127.0.0.1` server rooted in the temporary clone. Both have been removed. The probe scripts and audit results are kept outside the repository in `/tmp/mdcr-audit/`.

## 2. Executive verdict

**HOLD.** There are no Blocker or Critical findings. There is **one Major** and **ten Minor** unresolved findings.

**What is sound and independently confirmed:**
- **Artifact and build:**
  - The HTML, sidecar and placeholder provenance rebuild byte for byte.
  - Q1–Q26 plus the JavaScript check pass.
  - All 427 unit tests pass, and the closure test passes 31/31 on both the template and the artifact.
  - The release facts are current, `git diff --check` is clean, Gitleaks finds nothing, and the archived releases are intact.
- **Browser evidence:** I reproduced 878/878 in both `file://` and HTTP mode, with zero exceptions. My `file://` record matches the committed one except for timings.
- **Shell safety:**
  - Remote, URL, Git-path, shell-variable and PID values use closed grammars.
  - rsync always passes `-s`.
  - Canonical execution-sink spellings are refused.
- **Receipt binding is exact:**
  - All 18 receipts are reproducible by the shipped assembler.
  - A typed edit changes the trust bar, Inspector, status bar, export and release comparison to "Not host-verified".
  - Restoring the original values restores "Verified".
- **Pipeline trust separation:**
  - A composed pipeline is labelled "Composed — not host-verified" and carries no borrowed STIG identity on screen, in print, in the export or in the clipboard header.
  - Composed privilege and per-stage flag attribution are shown.
  - An incomplete pipeline cannot be exported.

**Why HOLD.** Testing with real keystrokes, which the release audit never does because it sets whole values programmatically, exposes a Major defect. The pipeline's file box cannot be typed into, and typing in it throws an uncaught exception (R3-1).

The ten Minor findings concern the issues alpha.6 set out to close:
- an incorrect destructive banner reason;
- an acknowledgement that is not bound to the command it acknowledged;
- path classification that depends on spelling, and gaps in it;
- a second path where the status bar does not refresh;
- remaining focus and live-region defects;
- contrast failures;
- STIG over-suppression while a pipeline exists;
- unsafe recovery text for downloads.

## 3. Findings by severity

### Blocker
None.

### Critical
None.

### Major

**R3-1. The pipeline file box and the `xargs -n` box cannot be typed into. Each keystroke destroys the focused input and throws an uncaught exception.**

- **Where:**
  - `pipelineSetField()` (`template.html:4708-4719`) re-renders on every `input` and `change` event, routed by `onFieldChange()` (`:5942-5950`, `:5967-5971`).
  - It calls `renderPipelinePanel()` (`:4729-4856`), which replaces the whole panel (`target.innerHTML=html`, `:4855`). That includes the focused `#pipetgt-N` (`:4788-4791`) and `#pipen-N` (`:4813-4816`) inputs.
  - Focus is restored only in `renderAll()` (`:5801-5818`), not on this path.
- **Observed** (real CDP key and text events, in both delivery modes):
  - Steps: RHEL 8 → journalctl → **Add to pipeline** → **Add a redirection** → type `/tmp/x.log` in the file box.
  - After the first `/`, focus moves to `<body>`, and `tmp` is lost.
  - The next `/` triggers the global palette shortcut, so `x.log` is typed into the palette instead.
  - The stage is left as `… --boot > '/'`.
  - The detached input then fires `change`, which re-enters the render, and Chrome throws `NotFoundError: Failed to set the 'innerHTML' property … at renderPipelinePanel (:4855)`.
  - Using `Input.insertText` gives the same result. Typing `25` into `-n` leaves `2`.
- **Impact:**
  - Five of the ten operators (`>`, `>>`, `2>`, `| tee`, `| tee -a`) depend on this box, and `USER_GUIDE:106-108` tells the operator to "type the path in the file box".
  - It cannot be used from the keyboard (WCAG 2.1.1, 2.4.3, 3.2.2), and with a mouse it needs one click per character. Pasting is the only practical workaround.
  - The "zero runtime exceptions" claims (`QA_REPORT:24-25`, `SECURITY_REVIEW:38-41`) hold only for programmatic input.
  - The code predates alpha.6 (`cd72e32`; alpha.5 is identical), but it ships in this candidate.
- **Correction:**
  - Do not rebuild the stage list on text input. Update the row, bump the pipeline revision, and re-render the result, Inspector and status bar. Then patch only that stage's badge and reason, or save and restore the element id and cursor position around the render.
  - Ignore events from detached targets.
  - Add a CDP regression test that types character by character into every text control and asserts the value, the focus and zero exceptions.

### Minor

**R3-2. The destructive banner misattributes red ratings that come from the write target, and drops the real reason.**

- **Where:**
  - `assembleCommand()` records a `WRITE-TARGET` reason (`:1693-1695`).
  - `withCopyPayloads()` replaces the reason list with `blastFor()`'s pattern-only list (`:3687-3689`).
  - `assemblePipeline()` records no reason for target-class ratings (`:2441-2446`).
  - With an empty list, `renderBlastBanner()` falls back to "This entry is catalogued as blast radius red by its content reviewer." (`:4413-4415`).
- **Observed:** That sentence appears for `curl -o '/etc/hosts'` and `wget -O '/etc/hosts'` (both catalogued yellow) and for `journalctl … > '/root/.bashrc'` (catalogued green). No screen says that the target path caused the rating.
- **Impact:** This is a false statement of where the rating came from, on the destructive-operation banner. `USER_GUIDE:199-204` promises the banner names "which pattern matched and why", and also omits write targets as a source of red. The issue is new for the alpha.6 download and transfer forms and pre-existing for pipeline redirects.
- **Correction:**
  - Merge the reason lists instead of replacing them.
  - Have the pipeline assembler emit `WRITE-TARGET` and `XARGS-RED` reasons.
  - Show the fallback text only when the entry itself is catalogued red.
  - Assert the banner text in the browser audit.

**R3-3. The red-command acknowledgement is not bound to the command it acknowledged.**

- **Where:**
  - `STATE.acked` is cleared only in `setVersion()` (`:3231`), `selectTool()` (`:5642`) and `selectEntry()` (`:5707`).
  - It is not cleared by `onFieldChange()` (`:5939-5966`) or by any pipeline change (`:4568-4719`).
  - The Copy gates that check it are at `:3761`, `:3768`, `:3788`, `:5022` and `:5201`.
- **Observed:**
  - Tick the box for `git --literal-pathspecs checkout -- 'config/prod.yml'`, then change the path to `src`.
  - Copy stays enabled and copies `… -- 'src'` with no new review. Pipelines behave the same way.
- **Impact:**
  - The documentation says Copy is locked "until you tick 'I have reviewed this command'" (`USER_GUIDE:204-206`, `:479`). The architecture guide says "a new version is a new command to review" (`ARCHITECTURE_BIBLE:400-401`).
  - This is the same binding gap alpha.6 just closed for receipts. It is pre-existing.
- **Correction:**
  - Store the acknowledged payload and treat the acknowledgement as valid only while it still equals the current payload, or clear it whenever the result key changes.
  - Add a test.

**R3-4. RHEL's `/lib` and `/lib64` aliases bypass the execution-sink refusal and the red system-path rating.**

- **Where:**
  - `PIPE_SYSTEM_DIRS` (`:2113`) has no `/lib` or `/lib64`.
  - `PIPE_EXEC_SINK_DIRS` (`:2115-2122`) handles the `/bin` and `/sbin` aliases but not `/lib/systemd/system`.
  - `lexicalPath()` (`:2147-2166`) does not map these aliases to `/usr`.
  - The rule is used by pipeline redirects (`:2326-2329`) and by write-target fields (`:1681-1696`).
- **Observed** (the shipped assembler, for curl, scp and pipeline `>` alike):

  | Target | Result | `/usr` spelling of the same path |
  |---|---|---|
  | `/lib/systemd/system/x.service` | **yellow** | refused |
  | `/lib64/libc.so.6` | **yellow** | red |
  | `/lib/udev/rules.d/99-x.rules` | **yellow** | red |

- **Impact:** On RHEL 7–10, `/lib` points to `usr/lib`, so the result depends on spelling. This contradicts `SECURITY_REVIEW:20-22` and `USER_GUIDE:141-148`.
- **Correction:**
  - Map `/bin`, `/sbin`, `/lib` and `/lib64` to their `/usr` paths before classifying (and consider `/run/systemd/system`).
  - Add test vectors for each alias.

**R3-5. Sensitive user targets and directory destinations are rated more narrowly than the release claims.**

- **Where:**
  - `isSensitiveUserTarget()` (`:2187-2195`) lists six startup files, `.ssh`, and `.config/systemd/user`, and only under `/home/` and `/root/`.
  - `remoteWritePath()` (`:2198-2201`) rates the destination exactly as typed.
- **Observed — these are rated yellow:**
  - shell startup and logout files: `.bash_logout`, `.cshrc`, `.tcshrc`, `.login`, `.kshrc`;
  - login-trust files: `.k5login`, `.shosts`, `.rhosts`;
  - `~/.config/autostart/` (the system-wide equivalent, `/etc/xdg/autostart`, is refused);
  - `~/.local/share/systemd/user/` (`~/.config/systemd/user/` is red);
  - homes outside `/home` and `/root`, such as `/srv/app/.ssh/authorized_keys` and `/var/www/.bashrc`;
  - directory destinations: `scp '/tmp/.bashrc' 'root@host:/root/'` and `rsync … '/home/alice/' 'root@host:/root/'`, while `…:/root/.bashrc` is red even though it is the same resulting write.
- **Impact:**
  - `SECURITY_REVIEW:20-22` and `CHANGELOG:27-28` describe this as a class of targets. In practice it holds only for the listed names and for destinations typed as full file paths.
  - None of these targets is labelled "Read only".
- **Correction:**
  - Treat any `.ssh` path component as sensitive.
  - Widen the startup and trust list, or rate every dotfile directly in a home directory red.
  - Rate a directory destination at the strongest class it can contain.
  - Otherwise, narrow the claim.

**R3-6. The status-bar refresh fix does not cover pipeline field edits.**

- **Where:** `renderStatusBar()` was added to the generator-field path (`:5964`) but not to `pipelineSetField()` (`:4708-4719`). The pipeline status logic is at `:5446-5451`.
- **Observed:**
  - Add a redirection (the status bar says "Pipeline incomplete"), then set the target to `/root/.bashrc`.
  - The editor shows the red `… > '/root/.bashrc'`, but the status bar still says "Pipeline incomplete".
  - The reverse change leaves a stale "Composed — not host-verified" over an unassembled pipeline.
- **Impact:** This is the same defect that was found and fixed during the final HTTP audit, on a second input path. It contradicts `USER_GUIDE:240-244` ("…cannot disagree"). TC-RECEIPT-001 covers generator fields only.
- **Correction:**
  - Refresh the status bar from `pipelineSetField()`, or route every change that alters the result through one refresh function.
  - Extend the audit to the pipeline target, `-n`, `-0` and `-I` edits.

**R3-7. Focus still falls to `<body>` after a palette selection and after partial re-renders.**

- **Where:**
  - `activateHit()` (`:5615-5630`) runs a full render, which restores focus to `#palette-input` (`:5770`). It then calls `closePalette(false)` (`:5583-5591`), which hides that input without moving focus.
  - These paths re-render without restoring focus:
    - the acknowledgement box (`:5882`), via `reRenderEditorAndInspector()` (`:5907-5912`);
    - the Favorite button (`:5893-5897`);
    - a gutter line, by click (`:5855-5859`) or by Enter/Space (`:6077-6083`);
    - the Library acknowledgement box (`:5883`);
    - the xargs `-0` and `-I` checkboxes.
- **Observed:**
  - Selecting a palette result with Enter or the mouse leaves focus on `<body>`.
  - Space on "I have reviewed this command" leaves focus on `<body>`, with Copy now enabled but no longer in reach.
  - The same happens for Favorite, gutter Enter (documented at `USER_GUIDE:380`) and `-I`.
- **Impact:** The code comment at `:5763-5766` and the RC report (`QA_REPORT_v1.0.0-alpha.6-rc.html:14`) claim focus survives these renders. The palette is the main keyboard route. TC-A11Y-FOCUS-001 tests only a Home card, a sidebar row and a version button.
- **Correction:**
  - Close the palette before selecting, so focus falls back to the task heading.
  - Wrap the partial renders with the existing save/restore helpers.
  - Test them with real key events.

**R3-8. The completion announcement never fires for the first completion of a single-field form.**

- **Where:**
  - `announceGeneratorCompletion()` (`:5917-5930`) records its starting state only on the first field change, and announces nothing then.
  - `selectEntry()` resets that state (`:5709`).
  - `renderGeneratorEditor()` (`:5257-5273`) never sets it.
- **Observed:** Typing `4` into the kill form produces `kill -TERM '4'`, but `#gen-announcement` stays empty.
- **Impact:**
  - 24 of the 58 guided forms have exactly one required field. In those forms the first "Command ready" is silent unless an optional field was edited first.
  - This contradicts `CHANGELOG:31-32` and the RC report.
- **Correction:** Record the starting state when the form renders. Assert the announcement after the first keystroke.

**R3-9. Contrast failures remain (WCAG 1.4.3), measured from rendered styles.**

| Theme | Element | Colours | Ratio |
|---|---|---|---|
| Dark | `.primaryaction` (`:328`): "Copy command" (`:5024`, `:5203`) and "Find a reviewed task" (`:4186`), 13px bold | `#fff` on `#f59e0b` (`:45`, `:54`) | **2.15:1** |
| Light | `.blast h2` (`:206`), 14px bold, on the banner fill (`:204-205`) | `#dc2626` on `#f4ebed` | **4.13:1** |
| Light | `.panelbtn[aria-pressed="true"]` (`:168-169`), 12px | `#b45309` on `#f8eee6` | **4.39:1** |

- The dark primary button is new in alpha.6.
- The contrast test (`tests/test_responsive_controls.py:85-123`) checks hand-picked colour pairs, not rendered ones.
- **Correction:**
  - Dark primary button text `#18181b` (8.25:1).
  - Banner heading `#b91c1c` (5.53:1).
  - Pressed panel button text `#92400e` (6.2:1).
  - Add a rendered contrast sweep to the audit.

**R3-10. While any pipeline exists, a STIG rule opened from search cannot be viewed, yet the editor says it is in the Inspector.**

- **Where:**
  - `renderStigPanel()` returns early whenever a pipeline exists (`:4027-4031`).
  - The editor text is at `:4959-4966`; the Inspector text is at `:5285-5288`.
- **Observed:**
  - Open `RHEL-08-010000` from search while a pipeline exists.
  - The editor says the check and fix text "are in the Inspector panel on the right".
  - The STIG panel is empty, and the Inspector shows the pipeline review instead.
- **Impact:**
  - The N-2 fix suppresses more than it needs to. The operator can only read the rule by clearing the pipeline and losing it.
  - Related: a composed pipeline is labelled "Build / pipeline / reviewed command" (`:5001`).
- **Correction:**
  - Suppress only STIG rows that come from the selected entry. Still render a rule opened from search, and keep it out of the pipeline export.
  - Use "composed command" in the label.

**R3-11. Recovery and intent text for the new download and transfer forms is wrong.**

- **Where:**
  - `content/commands.json:5671`: wget recovery says "Delete the downloaded file -- wget makes no other change on the local host."
  - `:5615`: curl recovery says "For a plain fetch, nothing to undo… A downloaded file can simply be deleted".
  - `:5782`: the scp task title says "Copy a file to **or from** a remote host".
  - `:5846`: rsync recovery discusses `--delete`, which this form never emits.
  - The Recover step uses this text (`operationalPlan()`, `template.html:3155-3157`) and Copy Recover copies it (`:3765-3775`).
- **Observed:**
  - For `wget -q -O '/etc/hosts' …` (red, allowed after acknowledgement), Copy Recover produces "Delete the downloaded file…".
  - Meanwhile the field help already warns that "An existing file at this path can be replaced" (`instructional.json:1707`, `:1738`).
  - The scp form only offers a local source and a remote destination.
- **Impact:** Following the recovery step after an overwrite deletes the system file. This is the same class of problem as N-7.
- **Correction:**
  - Add a preflight step that keeps a copy of any existing target.
  - Change Recover to "restore the kept copy; delete only if the file did not exist before".
  - Remove the "plain fetch" and `--delete` text, and retitle the scp task "Copy a local file to a remote host".
  - Add a test using a protected target.

## 4. Closure of every prior HOLD finding

### HOLD 1 (`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD.md`)

| ID | Status | Evidence at `9d53a4c` |
|---|---|---|
| M-1: remote shell injection via scp, rsync and ssh | **Closed** | `isRemotePath()` (`:807-821`); `-l` for the ssh user; rsync `-s`. `;id`, `$(id)`, spaces, `~` and `::` are all refused (closure test and probes). |
| M-2: curl and wget shown as "Read only" | **Closed** (residual R3-4) | Both are rated yellow at least; only http(s) is accepted; canonical execution sinks are refused. |
| M-3: hardcoded runbook values | **Closed** | PID, path and user values are bound, and unresolved recovery stays blocked (TC-RUNBOOK-001..003 reproduced). |
| M-4: pipelines shown as "Verified" | **Closed** | "Composed — not host-verified" appears in the trust bar, status bar, Inspector and export. |
| m-1: stale counts | **Closed** | 427 / 145,345 / 23,032 / 717 / 232 / 68 / 878×2 / 58-142-200-102 / 36-19-3 / 7 red / 18 receipts all match what I reproduced. |
| m-2: evidence wording | **Closed** | `git diff --check` exits 0; Gitleaks is clean. |
| m-3: field types and task titles | **Closed** for the cited items | New stale scp title is in R3-11. |
| m-4: Git recovery entries rated differently | **Closed** | Both are yellow. |
| m-5: Home "Install a package" card | **Closed** | yum on RHEL 7, dnf on 8–10 (TC-HOME-002). |
| m-6: contrast | **Closed** for the cited colours | Muted text 5.96:1; focus ring at least 4.6:1. New failures are in R3-9. |
| m-7: pipeline UX | **Closed** | "Complete the pipeline" message; flags looked up per stage; operators shown as emitted. |
| m-8: grep source label | **Closed** | "GNU grep 2.20-3.11". |
| m-9: test strength | **Partly closed** | Runtime tests were added, but the browser audit never types, which is how R3-1, R3-6 and R3-7 went unnoticed. |

### HOLD 2 (`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD_2.md`)

| ID | Status | Evidence |
|---|---|---|
| N-1: pipeline file writes shown as "Read only" | **Closed** for the cited targets (residuals R3-4, R3-5) | `/tmp` is yellow; `/root/.bashrc`, `authorized_keys` and `.bash_profile` are red. |
| M-4(A): a generator receipt applied to any values | **Closed** | `command_as_run` matches the capture (Q16 checks this). All 18 receipts are reproducible. A typed edit changes every label, and RHEL 9 and 7 stay unverified. |
| M-4(B): an incomplete pipeline exported a receipt | **Closed** | `evidenceContext()` (`:3824-3826`); the export shows "Nothing to export". |
| N-2(a): STIG panel on screen and in print | **Closed** | Over-suppression is in R3-10. |
| N-2(b): STIG rule attached to the export | **Closed** | The export says "Pipeline STIG/control identity: none". |
| m-1 residuals: "muted blast line", `Requires: root` wording | **Closed** | `USER_GUIDE` updated. |
| N-3: remote destinations not rated | **Closed** for full file paths | Directory destinations and aliases are in R3-4 and R3-5. |
| N-4: flag sources and export privilege | **Closed** | Inspector shows "Stage 1 · journalctl"; the export prefixes each flag with its stage and tool and includes `Requires: root`. |
| N-5: focus | **Partly closed** | Home card, sidebar row, version, panel toggles and pipeline buttons now keep focus. Palette selection and partial re-renders do not (R3-7), and the pipeline file box is unusable (R3-1). |
| N-5: live region | **Replaced** | Now a concise, dedicated announcer; the first-completion gap is in R3-8. |
| N-5: "Verified" badge contrast | **Closed** | `#047857` is 5.48:1. |
| N-6: evidence and docs | **Closed** | Wording corrected; both browser modes reproduced at `fe2c6d8`; closure test 31/31; TC-DOCS-002 checks real values. Some new behavioural claims are overstated (R3-1, R3-2, R3-4, R3-5, R3-7, R3-8). |
| N-7: `-HUP` and `VARNAME` in kill/export guidance | **Closed** | A new instance for the download and transfer forms is in R3-11. |
| Observations | Still apply as non-blocking items | See section 6. |
| Status-bar refresh defect (found in the final HTTP audit) | **Closed for generator fields** | Not fixed for pipeline fields (R3-6). |

## 5. Commands and tests run

| Command or method | Result |
|---|---|
| `git rev-parse`, `status --porcelain --untracked-files=all --ignored`, `stash list`, `log`, `show --stat`, `diff --stat 9d8934e HEAD` | Exact HEAD; clean before and after; `9d53a4c` touches docs only |
| `shasum -a 256 dist/*` | Matches the sidecar, provenance and release documents |
| `git archive 9d53a4c` then `python3 build.py` in `/tmp` | HTML and sidecar **byte-identical**; default release RHEL 8 (receipts 0/9/0/9) |
| `extract/make_provenance.py` (placeholder) | Provenance **byte-identical** (Python 3.14.6, Node v22.23.2) |
| `PYTHONDONTWRITEBYTECODE=1 python3 qa.py` (clone; file times refreshed after a fresh clone tripped the Q1 freshness check) | **PASS** Q1–Q26 + JS (details below) |
| `python3 -m unittest discover -s tests` (full git clone) | **427 run, OK** |
| `node tests/test_alpha6_review_closure.js` on the template and the artifact | **31/31** both |
| `tools/generate_release_facts.py --check` | PASS |
| `git diff --check origin/main...HEAD`; `git diff --check 9d8934e HEAD` | exit 0 |
| `shasum -c` on the alpha.1–alpha.5 archives; alpha.5 archive vs the `v1.0.0-alpha.5` tag; `stig-src/SHA256SUMS` | All OK; identical to the tag |
| `gitleaks git` and `gitleaks dir` 8.30.1 with `.gitleaks.toml` | 203 commits; no leaks |
| Release browser audit (repository script; only the output path changed), headless Chrome 154, `file://` and `http://127.0.0.1` | **878/878** in each mode; 0 exceptions; 0 console errors; 0 network resources |
| Node, using the shipped assembler: every receipt vs the assembled command; a 32-target classification matrix; directory destinations | 18/18 match; R3-4, R3-5 |
| CDP probes with real input (`dispatchKeyEvent`, `insertText`, mouse) in both modes | R3-1, R3-3, R3-6, R3-7, R3-8; receipt binding confirmed |
| CDP rendered contrast sweep (light and dark; Home, generator, red and pipeline states) | R3-9 |
| CDP banner, runbook and STIG-view probes | R3-2, R3-10, R3-11 |

**Q18 hostile-input detail:**
- 145,345 checks: 142,993 refused and 2,352 accepted but confined to a single quoted argument;
- 408 positive controls;
- pipeline coverage: 23,032 pipeline checks, 332 operator-seam checks, 717 oracle comparisons, 11 negative controls, 100 interpreter checks, 36 stage-naming checks, 232 one-stage checks and 68 redirect-target checks.

**Q26:** 869 invocations checked against 420 grammar rows.

**Not performed:** screen-reader sessions, Firefox ESR or other browsers, real RHEL host execution, and CI.

## 6. Residual limitations that do not block this candidate

- **Signing and provenance:** the release is unsigned, and provenance stays at `TAG_COMMIT_PLACEHOLDER` until the merge is tagged, rebuilt, retested and stamped.
- **Host verification:** receipts cover RHEL 7/8/9/10 as 0/9/0/9 (18 of 800 entry/release pairs).
- **Flag data:**
  - RHEL 7 flags come from a UBI7 container.
  - The flag dictionaries carry 0 explanations; the curated entries explain 336 of their 348 flags.
- **Reference material:** about 98.68% of mined reference records are unrated; they are kept separate and copying requires an acknowledgement.
- **Evidentiary scope:** the export is reference material, not proof that a command ran. No assistive-technology, cross-browser or real-host execution testing was done.
- **Pipeline semantics (operational, not safety):**
  - A grep stage requires a file argument, so `| grep` cannot filter piped output.
  - Privilege is not derived from write targets.
  - rsync `--dry-run` is rated as a write, which is conservative.
- **Latent or unverified:**
  - The "Captured" status is not bound to the exact command, but no entry in this build can reach it.
  - Status messages are inserted with a freshly created `role="status"` element on every status-bar render; whether screen readers announce them is unverified.
- **CI and toolchain:**
  - CI pins its actions by tag.
  - CI uses Python 3.12 / Node 20, while provenance records Python 3.14.6 / Node 22.23.2.
  - Git grammar rows for RHEL 7 and 9 cite a generic `man git`.

## 7. Final recommendation

**HOLD. Do not tag, merge for release, or publish `9d53a4c`.**

The core security work has been verified. That covers the closed grammars, the write-target rating floors, exact receipt binding, pipeline trust separation, artifact reproducibility and both browser evidence modes.

To reach PASS:

1. Fix **R3-1**. Add real-keystroke CDP coverage for every text control, asserting value, focus and zero exceptions.
2. Resolve **R3-2 to R3-11**. Each fix is local. Any item the owner chooses to defer must be formally risk-accepted and disclosed in `USER_GUIDE` Known Limitations and `SECURITY_REVIEW`.
3. Correct the claims these findings contradict:
   - `SECURITY_REVIEW:20-22` and `:38-41`;
   - `QA_REPORT:24-25`;
   - RC report line 14;
   - `USER_GUIDE:106-108`, `141-148`, `199-206` and `240-244`;
   - `CHANGELOG:27-32`.
4. Rebuild, then rerun Q1–Q26, the unit suite, the hostile-input harness, both browser modes and Gitleaks. Regenerate the evidence and repeat the exact-head review.

---

Not part of the review: several connectors (Figma, Google Drive, GitHub, Linear and others) need authorization in claude.ai connector settings or via `/mcp`. None was needed here.
