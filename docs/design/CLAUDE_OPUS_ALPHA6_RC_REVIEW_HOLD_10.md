VERDICT: HOLD

The shipped artifact behaved correctly in everything I ran. The hold is because ninth-review item 7 is not met for rsync. Its test only passes because the test's fake `mv` does the "replacement" itself, and three release documents describe that as proven. Items 1 and 2 also have smaller test gaps: some broken versions of the scripts still pass the tests.

## Blocking findings

### MAJOR-1: rsync's raced-symlink recovery fails closed instead of replacing the link, and the evidence says otherwise (item 7, and item 10's honesty requirement)
- **Where:**
  - The test's fake `mv`: `tests/test_remote_transfer_transactions.py:75-93`. At `:87` it deletes the symlink itself before renaming.
  - The race test: `:324-344`, which asserts success at `:338`.
  - The script under test: the rsync Recover at `content/commands.json:5846`.
  - The claims: `docs/CHANGELOG.md:35-37`, `docs/QA_REPORT_v1.0.0-alpha.6.md:62` ("raced-symlink replacement") and `docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html:12` ("SCP and rsync … replace a raced target symlink with `mv -T`").
- **Reproduction (real GNU coreutils 9.10):**
  - `mv -T <dir> <symlink>` fails with "cannot overwrite non-directory … with directory".
  - I ran the app-bound Recover scripts with a wrapper `mv` that plants the symlink between the two moves and then hands off to real GNU `mv`:
    - **SCP (file):** the link is replaced, exit 0, nothing outside the target touched.
    - **rsync (directory):** exit 1, the target is still the planted symlink, and the transaction is left holding `after`, `before` and `state`.
  - I then ran the repo's own race test with only its fake `-T` branch replaced by real GNU `mv`. The rsync subtest fails at `:338` with both `mv` refusals; the SCP subtest passes.
- **Impact:**
  - The product is safe: it never follows the link, changes nothing outside the target, and keeps the data. But for rsync it does not do what the closure requires.
  - The next Recover refuses (symlinked target, then "recovery swap already exists"), so the operator has to recover by hand.
  - The test and three documents claim replacement for both methods. The HTML report credits the "fake-SSH execution matrix" without saying that `mv -T` itself is faked, with different behaviour from the real command.
- **Fix:**
  - Make the fake faithful: hand `-T` to real GNU `mv`, which is native on Linux CI and available as `gmv` on macOS.
  - Then choose one:
    - Remove a symlinked target without following it immediately before the restore move, and test with real `mv` both a link planted before the restore and one re-planted after the removal.
    - Or assert and document fail-closed behaviour for directory targets, with operator recovery steps.
  - Correct the three documents and regenerate the HTML report.

### MINOR-1: The signal tests accept "the remote shell died from the signal" as a pass (item 1)
- **Where:**
  - Transfer tests: any nonzero result passes at `test_remote_transfer_transactions.py:375`; the fake `ssh` turns a signal death into status 241 at `:39`.
  - NetworkManager test: the same pattern at `test_instruction_command_binding.py:307` and `:47`.
- **What's right:**
  - The tests do signal the generated `sh -s` itself (I confirmed the PID with `ps`).
  - They pause on the final `%u` check (`$txn/state` for SCP/rsync, `$txn/profile_path` for NetworkManager) and then release it.
  - Deleting the trap line, or restoring the pre-fix `trap cleanup EXIT HUP INT TERM`, is caught on every shell.
- **Reproduction:** I tried two broken versions that keep the literal trap text the test checks for:
  - moving `trap 'exit 1' HUP INT TERM` to after the final check;
  - resetting it immediately after it is set.
  - Under bash running as `sh` (this host's `/bin/sh`, and also RHEL's `sh`), both pass all 9 signal subtests. Bash runs the EXIT trap and then dies from the signal, which still yields a nonzero result.
  - Under dash (Ubuntu CI's `sh`), both are caught.
- **The product is correct:** in 27 runs (SCP, rsync and NetworkManager × HUP/INT/TERM × bash-as-`sh`, dash and zsh-as-`sh`), the transaction existed when the signal arrived, the shell exited exactly 1, and the transaction was removed.
- **Fix:** have the fakes record the child's exit status and assert it is exactly 1, and the pipeline's status too.

### MINOR-2: Item 2's trust checks are only partly isolated by tests
- **Owner checks are fully covered.** All 24 owner/mode `stat` checks are caught when removed one at a time. Re-adding an owner check on the preserved backup is also caught (the foreign-owned-backup test works).
- **These checks can be removed with every test still passing:**
  - SCP and rsync Recover's check that refuses an existing `after` ("recovery swap already exists").
  - Two checks on the actual profile file the transaction names, in NetworkManager Recover (`content/commands.json:666`):
    - the resolved profile must be a regular file, not a symlink;
    - the resolved profile must equal the saved path ("connection now resolves to a different profile file").
  - Dropping only the `:700` mode check on SCP/rsync transactions (NetworkManager's equivalent is caught).
  - NetworkManager Preflight's symlinked-state-root check before `install`. The fake `install` at `test_instruction_command_binding.py:51-57` refuses symlinks itself, which hides this; real `install -d` follows the link.
  - Overall, 32 of the 41 non-owner refusal checks across the nine scripts can be removed with the suites still green.
- **Fix:** add one isolated test per case:
  - a pre-existing `after`, as both a file and a directory;
  - NetworkManager resolving to a different file, or to a symlink;
  - a mode-0755 SCP/rsync transaction;
  - a symlinked state root, with an `install` fake that follows links as the real one does.

## Non-blocking observations
1. **Wrong citations in the HTML report (lines 15 and 18).** These rows cite TC-BLAST-ACK-001 for red runbook-step gating, but that check never touches plan-step buttons. The real evidence is TC-RUNBOOK-RED-GATE-001, and Space is covered by TC-COPY-002; neither is cited in the closure table.
2. **The "Evidence integrity" row (line 13) overstates the release gate.**
   - `test_release_readiness.py` checks hashes only for the BQP summary and the two result files.
   - Nothing checks the commit recorded in the results, which the operator supplies through `AUDIT_COMMIT` (`mdcr_functional_ui_audit.mjs:560`).
   - The current values are correct; I checked them by hand.
3. **TC-RUNBOOK-RED-GATE-001 only checks the `disabled` state.** It never actually copies a red plan step after acknowledgement.
4. **The extra keyboard handler for copy buttons is untested.** Removing it entirely (`template.html:6176-6186`) still passes, because the browser's own Enter/Space activation fires exactly once.
5. **Stale-artifact skips are worded wrongly.** The skip message says "no dist/ artifact" even when the artifact exists but is stale, and `test_paraphrase.py:435` passes without checking anything instead of skipping.

## Ninth-review closure map

| # | Status | Evidence |
|---|---|---|
| 1 | Product closed; test gap | Exits exactly 1 in 27/27 runs. Two broken versions survive under bash-as-`sh` (MINOR-1). |
| 2 | Partly closed | Owner checks 24/24 caught; missing-state and foreign-backup cases covered. Gaps in MINOR-2. |
| 3 | Closed | Markers are found only in authored text. With the pre-fix code, an injected marker makes prose copyable and the repo test catches it. All six authored scripts still copy. |
| 4 | Closed | Real Enter/Space: 1 click and 1 copy. Removing `preventDefault` or double-clicking is caught (2 and 2); ungated and never-enabled red steps are caught. |
| 5 | Closed | `template.html:6172-6175` and `6276-6280`, `ARCHITECTURE_BIBLE.md` §12 and `USER_GUIDE.md:390-395` are accurate. |
| 6 | Closed | `PAGER=cat` at `instructional.json:1036`. `nmcli(1)` on RHEL 9/10 documents `PAGER`. No other multi-line Preflight starts with a paging command. |
| 7 | **Not closed for rsync** | MAJOR-1. SCP is closed. |
| 8 | Closed | With no `AUDIT_*` variables the audit derived 465 / 168,697 / 27,652. All 7 bad-input cases stop before the browser starts. |
| 9 | Closed | With a stale artifact: 465 tests run, OK, 17 skipped. `qa.py`, `--size` and `--accuracy` all exit 1. |
| 10 | Values closed; claims not | BQP, release report, both result files and the HTML match the bytes, SHA, fingerprint and `4d61c90`. All 885 cited IDs were recorded and passed. Closure row 12 is false (MAJOR-1). |

**Eighth-review closures still hold:**
- NetworkManager rollback state stays under root-owned, mode-0700 `/var/lib/md-code-red`.
- SCP/rsync transactions are still created atomically, and unsafe parents are refused.
- "Copy complete plan" is gone.
- Keyboard copy fires once and keeps focus.
- Prose steps are not copyable.
- A two-pass binding mutant is caught.

## What I reran

| Check | Result |
|---|---|
| Changes since the implementation commit | `4d61c90` → HEAD touches only 8 documentation/evidence files; `dist/` is unchanged. |
| Unit suite | 465 tests, OK, 0 skipped. My first run had 2 failures caused by the host disk being full; they passed on rerun. |
| `qa.py` | Q1–Q26 + JS PASS (27/27); `--accuracy` PASS; `--size` 8,944,842 bytes; STIG checksums 5/5; release facts current. |
| Hostile-input harness (template and artifact, identical) | 168,697 checks (166,569 rejected, 2,128 quoted-safe), 0 failures; 27,652 pipeline checks; 741 oracles; 232 one-stage invariants. |
| JavaScript suites | Closure suite 78/78 on template and artifact; all 9 suites pass on the artifact. |
| Two rebuilds plus provenance | Byte-identical to each other and to the claims: `bd419fff…a06aa`, `cc74d3dc…c778`, `0fd83c9b…8157`. |
| Browser audit (my own Chrome 154 on port 9431 with an isolated profile, and my own HTTP server on 8931) | 898/898 in `file://` and 898/898 over HTTP; 0 exceptions; 0 console errors. IDs identical to the committed results; only the TC-PERF-001/002 timings differ. |
| Gitleaks 8.30.1 | 223 commits plus the working tree: no leaks. |
| Repository hygiene | `git diff --check` clean; alpha.1–alpha.5 archives verify; the alpha.5 archive matches its tag. |

## Limitations
- **No live RHEL host.** All script execution was controlled fakes on macOS (fake `ssh`, `sudo`, `nmcli`, `install`; root uid simulated through a `stat` wrapper), plus my own harnesses using real GNU coreutils 9.10 with bash 3.2 as `sh`, dash and zsh.
- **Not exercised:** real sshd, scp, rsync and nmcli; SELinux; real root.
- **Unsigned:** the artifact is unsigned and provenance `git_commit` is still `TAG_COMMIT_PLACEHOLDER`.
- **Browser coverage:** headless Chrome only; no screen reader.

## Tree state
- **Initial HEAD:** `f7732ae921c10e373c2a88bba1e9fe5b045c4f2c`
- **Final HEAD:** `f7732ae921c10e373c2a88bba1e9fe5b045c4f2c` (the reviewed HEAD)
- **`git status --short`:** empty at start and end; no stashes; one worktree.
- **Unchanged tree:** yes. The SHA-256 manifest of all 514 working-tree files (including ignored ones), `.git/index`, `.git/HEAD` and all refs was identical at start and end.
- **Cleanup:**
  - Removed: my Chrome (9431) and HTTP server (8931), stopped by their own PIDs; my scratch directory `/tmp/mdcr_review10`. No temp directories were left behind.
  - Untouched: your `/tmp/mdcr_functional_audit_results.json` (I redirected the audit's output) and the system clipboard.
- **Your headless Chrome (PID 7005, port 9232) is no longer running.**
  - It was alive at the start and right after I stopped my own browser. By the end it had exited and its profile `/tmp/mdcr-alpha6-rc-chrome` was gone.
  - I never signaled it or touched that path.
  - Twice during my run the disk ran completely out of space, and my scratch copies (about 200 MB at peak) contributed to that. Free space then jumped to about 1.5 GB when that profile disappeared, so something else on the host probably shut it down and cleaned it up. I can't tell what.
  - Your HTTP server (PID 7004, port 8878) is still running.
