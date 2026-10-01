VERDICT: HOLD

I'm holding this candidate, but not for a product defect. The shipped artifact did the right thing in every scenario I ran: about 2,000 browser checks, 498 shell-transaction scenarios and 16 static red-entry checks. The hold is about the evidence. This round required the repo's tests to exercise the promised behaviour and the release documents to cite only what tests observe. For the signal, ownership and keyboard-copy items, the tests still pass when the fix is reverted or broken. Meanwhile the release documents say those tests prove the behaviour.

The eighth review called this kind of gap non-blocking. I'm treating it as blocking for three reasons:
- This round made test strength an explicit closure criterion.
- The documents now make new, specific verification claims that are false.
- The gaps sit on the root-run rollback trust boundary that was the previous Major (seventh review, MAJOR-1).

None of the fixes below changes the product's behaviour.

## Blocking findings

### MAJOR-1: The signal test passes against the exact bug it was written to catch

- **Where:**
  - The test: `tests/test_remote_transfer_transactions.py:223-236`. It kills the whole process group at `:233`, and its fake `stat` pauses on `$txn` at `:49-52`.
  - The claims: `docs/QA_REPORT_v1.0.0-alpha.6.md:56-62` ("nonzero SIGTERM cleanup"), `docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html:12` ("exit nonzero while cleaning partial state on termination signals"), and `docs/CHANGELOG.md:19-22`.
- **Reproduction:**
  - I restored the exact pre-fix line from `0a5815e` (`trap cleanup EXIT HUP INT TERM`): the test passed 5 of 5 runs.
  - With no signal trap at all, it also passed 5 of 5.
  - I instrumented the test's own procedure: `proc.returncode = -15`. The nonzero result comes from the test killing its own outer shell, not from the transaction script.
  - The pause also kills the first validation's `stat`, so that validation fails whatever trap is installed.
  - When I sent the signal only to the transaction shell, at the last validation, the pre-fix code exited **0** after deleting the transaction under dash and bash. That is the eighth review's observation 4, and this test cannot see it.
- **Impact:** there is no regression guard for that observation, yet the release evidence says there is. The browser checks TC-RUNBOOK-REMOTE-001/002 only catch that one exact line of text. They miss equivalent mistakes such as `trap cleanup HUP INT TERM`.
- **The product is correct.** I sent TERM, INT and HUP only to the transaction shell at three points: the first validation, during `cp -a`, and the last validation. Every case exited 1 and removed the transaction, under dash, bash `--posix` and zsh in sh-emulation mode.
- **Fix:**
  - Signal only the remote `sh`, recording its PID through a wrapper, not the process group.
  - Pause on the last validation (`stat -c %u -- "$txn/state"`) and let that `stat` finish.
  - Assert that the pipeline's own exit status is nonzero and that the transaction is gone.
  - Parametrize over HUP, INT and TERM, and over the SCP, rsync and NetworkManager Preflights.

### MAJOR-2: The rollback ownership checks are almost untested, but documented as tested

- **Where:**
  - The tests: `tests/test_instruction_command_binding.py:51-61` (the fake `stat` can forge a uid under only one path prefix) and `:208-213` (the only forged-owner test, which targets Preflight's state root).
  - The SCP foreign-owner test: `tests/test_remote_transfer_transactions.py:185-195`.
  - The claims: `QA_REPORT_v1.0.0-alpha.6-rc.html:11` ("Recover and Finalize reject … non-root-owned … or incomplete state", citing "nine exact-binder execution tests"), `QA_REPORT_v1.0.0-alpha.6.md:62-66`, and `CHANGELOG.md:16-18`.
- **Reproduction:** I deleted each check in turn and reran the repo's tests.
  - The three NetworkManager scripts contain 12 root-uid checks. **11 of the 12 can be deleted without any of the 10 tests failing.** Only Preflight's state-root check is covered, so every uid check in Recover and Finalize is unguarded.
  - No test covers a missing `before` or `profile_path` file.
  - SCP Recover's transaction-directory owner check can also be deleted with all 13 transfer tests still passing. The foreign-owner test marks the directory, state and backup together, and its assertion at `:193` is a substring that also matches the state-file refusal.
  - Adding back an owner requirement on the preserved backup (the root `cp -a` regression) also leaves all 13 passing.
- **Impact:** these are the checks that closed the seventh review's MAJOR-1. They are also the new trust model: the docs say "the protected transaction directory … establishes trust". Any of them can be removed silently.
- **The product is correct.** In my NetworkManager harness (180/180), a forged owner on each of state root, transaction, `before` and `profile_path` was refused by both Recover and Finalize, with the profile untouched and the state kept. Missing pieces were refused too. A preserved backup owned by another user stays recoverable for both SCP and rsync.
- **Fix:**
  - Forge exactly one path per test case, across {state root, transaction, `before`, `profile_path`} × {Preflight, Recover, Finalize}.
  - Add missing-file cases.
  - Split the SCP test into a transaction-only and a state-only case, each asserting its specific message.
  - Add a positive test where only `$txn/before` (or its nested files) has a foreign uid, and Preflight plus Recover must succeed.

### MINOR-1: The clipboard evidence can't detect double activation

- **Where:**
  - TC-COPY-001: `tools/qa/mdcr_functional_ui_audit.mjs:249-255`. It presses keys through `pressKey` at `:74-77`, which sends a key-down with no character, so the browser never fires the keypress that triggers a button's own activation.
  - The claims: `QA_REPORT_v1.0.0-alpha.6-rc.html:15` ("Enter activates Copy once") and `:16`, where TC-BLAST-ACK-001 is cited for red *plan* copies but never checks the plan-step buttons (`:452`).
- **Reproduction:**
  - I built a mutant with `ev.preventDefault()` removed (`template.html:6180`).
  - Real Enter and Space keys copied **twice** on that mutant.
  - The repo's full audit still passed **897/897** on it, with TC-COPY-001 recording `calls:1`.
- **The product is correct.** In the shipped artifact, real Enter and Space produce exactly 1 copy and 1 click on Copy, Copy with comment, the plan steps and evidence copy, and focus stays on the button.
- **Fix:**
  - Dispatch Enter with `text:"\r"` and Space with `text:" "`, and assert one copy and one click.
  - Add assertions that plan-step buttons are disabled before acknowledgement and enabled after it.

### MINOR-2: The keydown-listener description is still wrong (item 8)

- **Where:** the comment at `template.html:6272-6275` says the separate narrow handler is "below" and covers "code lines and clipboard buttons".
- **What's actually there:**
  - The narrow handler is *above*, at `:6172`, and handles only clipboard buttons.
  - Code-line Enter/Space is handled by the primary listener at `:6339` (the branch at `:6375`).
  - `docs/ARCHITECTURE_BIBLE.md:430` and `docs/USER_GUIDE.md:391-392` still say there is one delegated `keydown` listener.
- **Note:** fixing the comment changes the artifact bytes, so it needs a rebuild and an evidence refresh. MAJOR-1, MAJOR-2 and MINOR-1 are test and doc changes only (MINOR-1 also needs the browser audit rerun).

## Non-blocking observations

1. **Garbled sentence:** `USER_GUIDE.md:234-236` reads "**Copy** and **Copy with comment** are command, runbook command steps, … are disabled".
2. **nmcli Preflight paste (pre-existing):** Copy Preflight is two lines, and the first, `nmcli connection show`, opens a pager when output doesn't fit the screen (`content-src/raw/rhel9/nmcli.man.txt:1073-1085`). In a shell without bracketed paste, the pager can swallow the transaction line. Recover then refuses, so it fails safe.
3. **Fresh-clone test abort (pre-existing):** on a fresh clone, `python3 -m unittest discover` stops after about 90 tests. Checkout order leaves `dist/` older than `template.html`, `qa.py`'s timestamp check (`qa.py:533-539`) raises `SystemExit` inside class setup (`tests/test_content_family_liveness.py:43-45`), and that ends the whole run. CI runs unit tests before building, so it may hit this too.
4. **Recover race (pre-existing hardening):** between Recover's two `mv` calls, a symlink to a directory planted at `$target` would redirect the restore into that directory. This needs a parent directory owned by an untrusted user. Use `mv -T`, or also check who owns the parent.
5. **`markedScript` runs on bound text** (`template.html:3343`). It's safe in this build because no free-text field reaches a prose Verify/Recover step, but it would be sturdier to find the marker in the authored text.
6. **TC-DOCS-002** needs the `AUDIT_*` environment variables; without them the audit reports 896/897.

## Closure map

| # | Product | Evidence |
|---|---|---|
| 1 | Closed | My sweep of 229 entry/release pairs: 217 prose Verify/Recover steps disabled; 12 marked scripts copy exactly the `printf …` script; 44 Preflight payloads contain only commands; all 16 red pairs gated on every copy surface, even with the buttons force-enabled. 16/16 static red pairs gated, and the acknowledgement clears on a release switch. |
| 2 | Closed | The two-pass mutant is caught by `test_instruction_values_are_bound_once`. |
| 3 | Closed | Gaps: MAJOR-1 and MAJOR-2. |
| 4 | Closed (numeric names select the right file; zero, duplicate and cross-field duplicate matches print the diagnostic) | Numeric and diagnostic mutants are caught; ownership is not (MAJOR-2). |
| 5 | Scripts now come from `operationalPlan` | Symlinked-parent, missing/duplicate and numeric-name tests catch their mutants; the signal and ownership tests don't (MAJOR-1, MAJOR-2). |
| 6 | Red evidence copy disabled before acknowledgement and enabled after: observed by TC-BLAST-ACK-001 | "Exactly one write" not proven (MINOR-1). |
| 7 | The verification-total gate derives live counts (`test_release_readiness.py:123-138`); the transaction mechanism prose is accurate | Over-citations in MAJOR-1, MAJOR-2, MINOR-1 and MINOR-2. |
| 8 | Partly closed | MINOR-2. |

## What I reran

| Check | Result |
|---|---|
| Changes since the implementation commit | `7498685` → HEAD touches only 6 documentation/test files; `dist/` is unchanged. |
| Unit suite | 457 tests, OK, 0 skipped, against the exact committed artifact bytes |
| `qa.py` gates | Q1–Q26 + JS PASS; `--accuracy` PASS; `--size` 8,944,458 bytes; `stig-src` checksums 5/5; release facts current |
| Hostile harness (template and artifact, identical) | 168,697 checks (166,569 rejected, 2,128 quoted-safe), 0 failures; 27,652 pipeline checks; 741 oracles; 232 one-stage invariants |
| JavaScript suites | Closure suite 78/78 on both template and artifact; all 9 suites pass on the artifact |
| Two clean rebuilds plus provenance | Byte-identical to the committed files. Artifact `0ef9e035…bcc`, sidecar `80f18b7e…344`, provenance `bfad4689…4ef`, fingerprint `d079b654…a94` all match the claims. |
| Browser audit (my own Chrome 154 on port 9419 and HTTP server on 8919; only the output path changed) | 897/897 in `file://` and 897/897 over HTTP; 0 exceptions, 0 console errors; IDs identical to the committed results; only TC-PERF-001/002 timings differ |
| My execution harness | Transfers 318/318; NetworkManager 180/180 |
| Gitleaks 8.30.1 | 218 commits plus the working tree: no leaks |
| Repository hygiene | `git diff --check` clean; alpha.1–alpha.5 archives verify, and the alpha.5 archive matches its tag |

## Limitations

- **No live RHEL host.** Everything ran on a controlled fake transport on macOS:
  - fake `ssh` with OpenSSH-style argument joining;
  - fake `sudo` with `/var/lib/md-code-red` redirected into a temp directory;
  - fake `nmcli`, with uid 0 simulated through a `stat` wrapper;
  - root `cp -a` simulated by reporting a foreign uid for the backup;
  - GNU coreutils 9.10, bash 3.2 (`--posix`), dash, zsh 5.9, and BWK awk.
- **Not exercised:** RHEL's bash 4/5, gawk, real sshd/scp/rsync/nmcli, SELinux, and real root.
- **Your tailnet:** it lists RHEL machines, but I didn't run anything on them.
- **Unsigned:** the artifact is unsigned, and provenance `git_commit` is still `TAG_COMMIT_PLACEHOLDER`.
- **Browser coverage:** headless Chrome 154 only, and no screen reader.

## Tree state

- **Initial HEAD:** `2ceec78dcf216097a9675ff73feb42e59a7fb22e`
- **Final HEAD:** `2ceec78dcf216097a9675ff73feb42e59a7fb22e` (the reviewed HEAD)
- **`git status --short`:** empty at start and end; no stashes; one worktree.
- **Cleanup:**
  - Removed: my Chrome (9419), my HTTP server (8919), and the scratch clone and harness in `/tmp/mdcr_review9`.
  - Untouched: your Chrome (PID 7005, port 9232, still responding) and `/tmp/mdcr_functional_audit_results.json`.
  - The system clipboard was never used; copy calls were intercepted inside the page.
- **Unchanged tree:** yes. The SHA-256 manifest of all 513 working-tree files, `.git/index` and all refs were identical at start and end.
