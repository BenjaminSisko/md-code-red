VERDICT: HOLD

The shipped artifact did everything right in every scenario I ran. The hold is about the tests, as in the ninth and tenth reviews. You asked that the closure tests be mutation-sensitive. For three properties you named (items 1, 3 and 4), a broken version of the code still passes every test, and the release documents say those properties are proven. Each fix is a test change only; the artifact bytes would not change.

## Blocking findings (most severe first)

### MINOR-1: Nothing tests that Recover's retry is bounded and fails closed (item 1)
- **Where:**
  - The race tests: `tests/test_remote_transfer_transactions.py:378-401` and `:403-424`. The fake `rm` replants the link only once (`:99-104`), so the 3-attempt limit and the final `return 1` are never reached.
  - The decoy directory the link points to starts empty (`:388`, `:408`), so the tests can't see anything deleted from it.
  - The scripts: `content/commands.json:5784` (SCP) and `:5846` (rsync).
  - The claims: `docs/QA_REPORT_v1.0.0-alpha.6.md:69-70` ("exercises … bounded raced-symlink replacement"), `docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html:12`, `docs/CHANGELOG.md:35-38`.
- **Reproduction:** these broken versions all pass the full transfer suite:
  - **Fail-open:** the final `return 1` changed to `return 0` (SCP and rsync). Against an attacker who replants the link after every removal, rsync Recover exits **0**, leaves the attacker's link in place, and deletes both `before` and `after`. That is silent loss of all the data.
  - **Unbounded:** the loop changed to `while :`. It never terminates.
  - **Deleting through the link:** removal changed to `rm -rf -- "$target_path"/*; rm -f …`. Nothing catches it because the decoy directory is empty.
- **The product is correct.** In my persistent-attacker harness (bash-as-`sh`, dash, zsh; link to a directory or to a file), rsync exits 1 after exactly 6 removals. The link is not followed, a sentinel file in the link target survives, and `before`, `after` and `state` are kept. SCP's `mv -T` replaces the link on the first try.
- **Fix:**
  - Add a test with an `rm` that replants after every removal. Assert exit status exactly 1, the link still in place, the sentinel intact, all three transaction pieces kept, at most 6 removals, and a hard timeout.
  - Put a sentinel file in the decoy directory in both existing tests.

### MINOR-2: The red-runbook check doesn't verify which script was copied (item 4)
- **Where:**
  - The check: `tools/qa/mdcr_functional_ui_audit.mjs:500` only tests `clipboard.includes('MDCR_RSYNC_RECOVER')`.
  - The code it protects: `template.html:3971`.
  - The claims: `QA_REPORT_v1.0.0-alpha.6-rc.html:18` ("marked transaction scripts stay individually copyable", citing TC-RUNBOOK-RED-GATE-001) and `CHANGELOG.md:43-45`.
- **Reproduction:**
  - I made Recover copy all four steps joined together, which is the "Copy complete plan" hazard removed in the eighth round.
  - The audit still passed **898/898**; the copied text began with `# MDCR_RSYNC_PREFLIGHT`. All 470 unit tests and the 78 closure checks also passed.
  - Pasting that would rerun the destructive rsync and then Finalize, which deletes the rollback, before Recover runs.
- **The product is correct.** My own browser probe checked rsync, SCP and NetworkManager, each of the four steps, with both Space and Enter. Every one gave exactly 1 click and 1 copy, with the payload byte-identical to `operationalPlan()`, and focus stayed on the button. Before acknowledgement, force-enabling and clicking the rsync buttons copied nothing.
- **Fix:** assert the copied text equals the exact bound Recover script. The audit can compute it with `tests/instruction_binding_probe.js`. At minimum, check its start and end and that no other step's marker appears.

### MINOR-3: The NetworkManager pre-`install` symlink check is still removable (item 3; carried over from tenth-review MINOR-2)
- **Where:**
  - The test: `tests/test_instruction_command_binding.py:222-228`.
  - The check: `content/instructional.json:1040`.
- **Why it survives:**
  - The check after `install` refuses a symlinked state root with the *same* message.
  - The test's link target is already mode 0700, so the fake `install` changing its mode through the link has no visible effect.
- **Reproduction:**
  - Deleting the pre-`install` check passes the suite.
  - I added a variant where the link target starts at 0755 and must stay 0755. It passes on the product and fails on the broken version (the mode becomes 0700).
- **Impact:** without the check, real `install -d -o 0 -g 0 -m 0700` would change the owner and mode of whatever directory the link points to before the later refusal.
- **Fix:** adopt that variant, or have the fake `install` log calls and assert it never ran.

**Evidence refresh:** these fixes touch `tests/` and `tools/qa`, so they need a new implementation commit, a browser re-run, and updated release documents. Also reword "exercises … bounded" in the QA report.

## Non-blocking observations
1. **Refusal checks outside the named cases are still mostly untested.** I removed each one and reran the suites with nothing else running:
   - 28 of 62 refusal guards and 64 of 70 individual non-owner conditions can be removed with everything still passing.
   - No Recover or Finalize test uses a symlinked destination or an unsafe parent. Removing both symlink checks survives in all four of those scripts; rsync Preflight's parent checks are also untested.
   - `CHANGELOG.md:52-54` (written in the sixth round) says the fake-SSH suite runs symlinked-destination cases for recovery and finalization. It doesn't.
2. **No positive Finalize test for SCP or NetworkManager.** A Finalize that never clears the transaction, or always refuses, survives. rsync's is covered.
3. **NetworkManager state-root mode in Recover/Finalize isn't tested on its own.** Dropping only the mode part of that check survives.
4. **The signal tests fail if the test runner starts with SIGHUP or SIGINT ignored** (for example under `nohup`, or as a background job of a script). The shell can't trap a signal ignored at startup, so it finishes normally and exits 0. That is correct behaviour, but the test reports a failure. Resetting signal handling to default in the fake `ssh`/`sudo` would fix it.
   - This is also why some of my broad-sweep results first looked like "kills": I had launched those sweeps that way. I discarded them and re-ran everything with default signal handling.
5. **A reintroduced copy-button handler that calls `preventDefault()` then `click()` would go unnoticed.** It still fires once. One that skips `preventDefault()` is caught.
6. **CI never runs 18 artifact-backed tests.** It runs the unit tests before `build.py`, and on a fresh checkout `dist/` looks stale, so those 18 always skip.
7. **The release gate only compares commits.** Uncommitted edits to protected paths pass it, and `extract/` is not in the protected list.
8. **Wording:** `CHANGELOG.md:13` still says "nonzero"; the behaviour and tests are exactly 1.
9. **No operator guidance when Recover refuses.** The data is preserved under `<target>.mdcr-*.txn/`; the manual steps should be documented.
10. **Pre-existing:** `test_search_index.py`, `test_reference_index.py` and `test_evidence_export_real.py` pick the artifact by sorting `dist/`. That is harmless while there is only one artifact.

## Tenth-review closure map
| # | Status | Evidence |
|---|---|---|
| 1 `mv -T` race | Product closed; bound untested (MINOR-1) | The fake `mv` hands off to real GNU `mv` 9.10. Caught: single attempt, two attempts, no `-T` (SCP and rsync), retry without removal. |
| 2 Signals | **Closed** | 54/54 broken trap variants caught under bash-as-`sh`, dash and zsh; 9/9 controls pass. `ps` shows the signal goes to the `sh -s` process. Child and pipeline status are asserted to be exactly 1. |
| 3 Trust cases | One case open (MINOR-3) | Caught: pre-existing `after` as file and as directory, NetworkManager symlinked and different profile, mode 0755 in all four Recover/Finalize scripts. All 24 owner/mode checks and all 12 owner-only checks are caught when removed. |
| 4 Red runbook | Payload weak (MINOR-2) | Opens the runbook, real Space, 1 click, 1 copy, focus kept. A double-firing handler is caught. |
| 5 Native keys | **Closed** | `template.html` has one `keydown` listener (`:6328`), which handles code lines and shortcuts only. TC-COPY-001/002 count 1 activation; `ARCHITECTURE_BIBLE` §12, `USER_GUIDE.md:391-396` and `template.html:6261-6264` are accurate. |
| 6 Release gate | **Closed** | 13/13 broken evidence variants rejected; `05b96e5` is an ancestor of HEAD; only 8 documentation/evidence files changed after it. |
| 7 Stale skips | **Closed** | Fresh clone: 470 tests, OK, 18 skipped, each with "artifact is missing or stale". `qa.py`, `--size` and `--accuracy` all exit 1 on the stale artifact. |
| 8 Report citations | Citations closed | Every cited ID was recorded. TC-COPY-001/002 and TC-RUNBOOK-RED-GATE-001 are cited, with TC-RUNBOOK-003 and TC-BLAST-ACK-001. No live-host claim. |
| 9 Documentation | Closed, with nits | The `mv -T`, bounded-retry, exact-status-1 and tenth-review lineage statements are present; release facts are current. |

**Ninth- and eighth-review closures still hold:**
- A two-pass binding version and a version that looks for markers in bound text are both caught.
- NetworkManager state stays under root-owned mode 0700; SCP/rsync transactions are created atomically.
- "Copy complete plan" is gone; prose steps aren't copyable.
- `PAGER=cat` is in place, and names are matched as strings.
- An edit revokes the red acknowledgement.

## What I reran
- **Builds:** two rebuild-plus-provenance cycles were byte-identical to each other and to the committed files: `198ae590…`, sidecar `b18d1303…`, provenance `aa11a5fb…`, fingerprint `871abbea…`, 8,944,791 bytes.
- **Unit suite:** 470 tests, OK, 0 skipped.
- **`qa.py`:** Q1–Q26 + JS PASS; `--accuracy` PASS; `--size` OK; STIG checksums 5/5; release facts current; `git diff --check` clean.
- **Hostile-input harness** (template and artifact, identical): 168,697 checks (166,569 rejected, 2,128 quoted-safe), 0 failures; 27,652 pipeline checks; 741 oracles; 232 one-stage invariants.
- **JavaScript suites:** closure 78/78 and the rail-keyboard check pass on both template and artifact; the other seven suites pass on the artifact.
- **Browser audit** (my own Chrome 154 on port 9451 with an isolated profile, and my own HTTP server on 8951):
  - 898/898 in both `file://` and HTTP; 0 exceptions; 0 console errors.
  - IDs identical to the committed results; only the TC-PERF-001/002 timings differ.
  - It derived 470 / 168,697 / 27,652 itself; the server served only the document.
- **Gitleaks:** 222 commits plus the working tree, no leaks. The alpha.1–alpha.5 archives verify, and alpha.5 matches its tag.

## Limitations
- **No live RHEL host.** All script execution used controlled fakes on macOS: fake `ssh`, `sudo`, `nmcli` and `install`; root simulated through a `stat` wrapper; real GNU `mv` 9.10; bash 3.2 as `sh`, dash, and zsh.
- **Not exercised:** real sshd, scp, rsync, nmcli, SELinux, or real root.
- **Browser coverage:** headless Chrome only; no screen reader.
- **Unsigned:** the artifact is unsigned and provenance `git_commit` is `TAG_COMMIT_PLACEHOLDER`.

## Tree state
- **Initial and final HEAD:** `62101c7e1ae5e67f64112b2a0f5fce75b0e2c159` (the reviewed HEAD).
- **`git status --short`:** empty at start and end; no stashes; one worktree.
- **Unchanged tree:** yes. A SHA-256 manifest of all 515 working-tree files (including ignored ones) was identical at start and end, as were `.git/index`, HEAD, all refs, stashes and worktrees.
- **Cleanup:**
  - Removed: my Chrome and HTTP server (stopped by their own PIDs), the processes from one hung test I ran, and all scratch and temp files.
  - Untouched: your HTTP servers (PIDs 7004 and 1071), the headless Chrome processes that were already running (PIDs 20963–20965), `/tmp/mdcr_functional_audit_results.json` (hash unchanged), and the system clipboard (copies were intercepted inside the page).
  - About 838 `TemporaryDirectory.*` folders in your temp directory were created during my run by other Swift tooling on the host; none relate to this review, so I left them.
