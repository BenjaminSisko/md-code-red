VERDICT: HOLD

I reviewed exact HEAD `bccd26398cff847033e36f3dbb82d5852393264c` on `codex/alpha6-responsive-ux`. I rebuilt the artifact from HEAD sources under both toolchains and got the same bytes each time (`198ae590…`).

Every blocking item from the twelfth review is closed, and I reproduced each fix myself:
- **B1:** the full CI sequence passes on a fresh clone with Python 3.12.13 and Node 20.20.2.
- **B2 and B3:** all 16 mutants I planted in Recover/Finalize were caught, each for the intended reason.
- **N3 and N5:** closed.
- **N1, N2 and N4:** closed in substance, with some wording problems left (non-blocking).

I am holding for **one new, small blocking finding in the release procedure**. Following `docs/WORKFLOW.md` step 6 (stamping the provenance after merge) makes two of the release-readiness tests this candidate added fail. That stamped `main` commit is the one step 7 pushes to Forgejo and the one step 8 publishes from. The fix touches only a test or the docs. If H1 is fixed, nothing else I found is blocking.

## 1. Blocking finding

### H1 — MINOR (release procedure; the artifact, the candidate's own CI and the tag target are unaffected): the documented provenance stamp fails the new release-readiness gates

**Where**
- `docs/WORKFLOW.md:232-235`, step 6: on post-merge `main`, run `python3 extract/make_provenance.py --commit <tag-target>` and commit the result. This rewrites `dist/md-code-red_v1.0.0-alpha.6.provenance.json`.
- `docs/WORKFLOW.md:236-239`, step 7: push that commit to Forgejo.
- `docs/WORKFLOW.md:243-244`, step 8: publish the assets from that tree.
- `docs/WORKFLOW.md:190`: there is no protected-branch check, so nothing stops the push. `.forgejo/workflows/ci.yml:26-28` runs CI on every push.
- `tests/test_release_readiness.py:79` requires the SHA-256 of the provenance file to appear in the BQP summary. The BQP summary only lists the placeholder hash `aa11a5fb…`.
- `tests/test_release_readiness.py:130-137` fails on any committed change under `dist` after the browser-evidence commit `5b868f10`.

**Reproduction** (scratch clone of HEAD)
1. Run `make_provenance.py --commit bccd2639…`.
2. Set `RELEASE_REPORT` front matter to `status: released`, as step 6 says, and commit.
3. Run `python3 build.py`; the output is byte-identical.
4. Run `python3 -m unittest discover -s tests`. Result: **Ran 480, FAILED (failures=2), 0 skipped.**
   - `test_bqp_summary_names_the_current_artifact_bytes`: `'ddb14878…' not found` in the BQP summary.
   - `test_browser_results_and_release_docs_bind_to_current_candidate`: `1 != 0 : implementation files changed after the browser-evidence commit`.
   - `qa.py` still passes.
5. Controls:
   - A docs-only commit passes the readiness module (6/6).
   - A dist change can never be re-bound inside the same commit, because the evidence has to name a commit that already exists.

**Impact**
- After the documented release, `main` CI goes red at step 2. The QA gate, gitleaks, drift and upload steps never run on it.
- The tree the release assets are published from fails the repository's own unit suite.
- Getting back to green needs either an edit to a protected test after review, or re-running and re-binding the evidence. This is the same "regenerated provenance vs. protected evidence" conflict as B1, moved from CI step 1 to release step 6.
- None of the release documents disclose this.

**Smallest sound fix** (recommended first)
- **(a) Test change.** In `tests/test_release_readiness.py`:
  - Exclude `dist/*.provenance.json` from the protected `git diff`/`git status` pathspecs.
  - Instead, assert that HEAD's manifest equals the manifest at the implementation commit except for `git_commit`. That field must be `TAG_COMMIT_PLACEHOLDER` or a 40-hex SHA that is an ancestor of HEAD.
  - In the BQP check, hash the manifest after setting `git_commit` back to the placeholder. The serialization is deterministic, so this reproduces `aa11a5fb…`.
  - Either require the stamp to be generated with the same toolchain, or normalize `toolchain` as well.
- **(b) Docs only.** Change WORKFLOW steps 6 and 8 so the stamped manifest is produced and kept outside `dist/`. That keeps `dist/` byte-identical to the reviewed candidate.
- Whichever you choose, re-run the readiness module on a simulated stamp commit.

## 2. Twelfth-review closure map

| Item | Status | Evidence |
|---|---|---|
| **B1** CI toolchain | **Closed** | Workflow inspected: Python 3.12 (`ci.yml:37-38`), Node 20 (`:42-43`). Step 1 runs only `python3 build.py` (`:54-55`); nothing in the workflow regenerates provenance. Fresh clone with Python 3.12.13 and the official Node v20.20.2 build (SHA-256 checked): steps 1–7 all pass in order. Build is byte-identical; the unit suite ran 480 tests, OK, 0 skipped; protected paths show no changes after every step; all three dist hashes are unchanged. `main` is an ancestor of HEAD, so a pull-request merge ref has the same tree. |
| **B2** Writes through the attacker link | **Closed** | Exact-inventory assertions at `tests/test_remote_transfer_transactions.py:438, 498, 526, 553` and in the new tests (`:590, 622, 659`). HOLD_12's rsync copy-through mutant fails 5 tests (`['old','sentinel'] != ['sentinel']`). The SCP version fails 2 tests. Write-then-refuse mutants in Recover and Finalize for SCP and rsync: 4/4 caught (`['leak','sentinel']`). **Control:** the same rsync mutant passes the prior HEAD's sentinel-only test file 24/24, so the new inventory check is what catches it. |
| **B3** Fail-closed recovery paths | **Closed** | Three new tests: scenario (a) at `:563-597`, (b) at `:599-628`, (c) at `:630-666`. Each has SCP and rsync subtests and checks exit status exactly 1, a 5 s timeout, `state`/`before`/`after` retained, and the directory inventory. In (c), `after` is moved back to the target and there are exactly 4 removals. All 10 mutants were caught for the intended reason (§5). |
| **N1** Operator guidance | Closed in substance | I ran the documented procedure end to end in three failure cases: SCP and rsync with an unremovable link in a sticky parent, and rsync with a persistent replant. Each time `before` was restored, the transaction removed, and the outside directory left untouched. Nothing in the guide destroys rollback state. One sentence is wrong; see O1. |
| **N2** Keyboard coverage | Closed for the named forms | Late window `keydown` and `keyup` synthetic-click mutants are rejected; so are property handlers and `addEventListener.call`. Other evasions survive and some docs claim more than the test checks; see O2. |
| **N3** SCP final return | **Closed** | The SCP final `return 0`, outer `exit 0`, and delete-transaction-on-failure mutants are all caught by the SCP subtest of (c). |
| **N4** Probe scope | Partly closed | The QA documents now say "external". `SECURITY_REVIEW:87-88` still says "independent"; see O3. |
| **N5** Audit output path | **Closed** | `AUDIT_OUTPUT` is honored (`mdcr_functional_ui_audit.mjs:24`); my two runs wrote separate files and `/tmp/mdcr_functional_audit_results.json` was not touched. The two committed result files are genuinely separate runs: different URLs and different performance readings. Each is bound to 8,944,791 bytes, `198ae590…`, `871abbea…` and commit `5b868f10`. |

## 3. Non-blocking observations

- **O1 — N1 wording.** `USER_GUIDE:184-185` says a direct retry "will correctly stop with `recovery swap already exists`".
  - While the hostile link is still in place, the retry actually stops with `Refusing: symlinked scp/rsync destination`. The "swap" message only appears after the link is removed. Both are safe refusals.
  - The failed Recover itself prints no MD CODE RED-specific diagnostic, only `mv`/`rm` errors.
- **O2 — N2 leftovers.**
  - The structural test does **not** catch: a late `keypress` listener; a `` `keyup` `` template literal; `window["addEventListener"]`; `.apply`; a KEYMAP binding on Enter/Space that dispatches a click; or `dispatchEvent(new MouseEvent("click"))` inside the approved handler.
  - I built N2l (`dispatchEvent`) and N2g (`keypress`) into artifacts. Both pass the browser audit 898/898.
  - N2l also passes `qa.py`; only the two hash-pinning tests fail, which happens for any artifact change.
  - Behaviour stays single-fire, but these docs claim more than the test checks: `ARCHITECTURE_BIBLE:439-441` ("rejects every `keyup` listener", "refuses any … synthetic click"), the QA HTML row at line 16, `RELEASE_REPORT:73-74` and `CHANGELOG:19-21`.
  - Fix: narrow the wording. Or count listeners at runtime through CDP `DOMDebugger.getEventListeners`, and forbid `dispatchEvent(`/`doCopy(`/`copyText(` in the approved handler and Enter/Space in KEYMAP.
- **O3 — N4.** The probe runs the same `operationalPlan()` text sliced out of `template.html` (`instruction_binding_probe.js:16-20`).
  - Byte equality therefore proves the click routing and that template and artifact agree. It does not prove the plan is correct; the fake-SSH tests cover that by executing the same probe output.
  - Only rsync Recover is compared byte for byte.
  - Fix: change "independent" to "external" in `SECURITY_REVIEW:88`.
- **O4 — Audit identity comes from disk.** `mdcr_functional_ui_audit.mjs:25-30` hashes the repo's dist file. Nothing checks the bytes the browser actually rendered, so an HTTP run against a stale server root would still record the disk hash.
  - My own HTTP run closes that gap for this candidate (see §4).
- **O5 — Two of the 898 assertions cannot fail.** TC-PERF-001 (`:168`) and TC-PERF-002 (`:571`) are informational and always PASS. The QA HTML shows them as PASS without saying so. 896 assertions are real checks.
- **O6 — The evidence-binding tests are candidate-specific but run on every push.** By design, any later change to a protected path fails them; for example, a comment-only `qa.py` commit fails, while a docs-only commit passes. After release, `main` and every development branch will stay red until a new candidate is bound. This should be disclosed or scoped (related to H1).
- **O7 — SCP retry bound.** Changing `-lt 3` to `-lt 4` survives (still bounded). `-lt 2` and `while :` are caught. The rsync bound is pinned by the "6 removals" assertion.
- **O8 — Skips on a stale artifact.** If the artifact is older than its sources, 18 artifact-backed tests skip and the suite still says OK. Building first in CI prevents this.
- **O9 — Review index.** `docs/design/README.md` does not list the twelve alpha.6 review records, although all twelve exist.
- **O10 — zsh.** In native mode, zsh reads `$((0$parent_mode))` as decimal and fails 6 tests. That does not apply, because the runbook calls `sh -s`; zsh in sh emulation passes 27/27.

## 4. Checks run and totals

- **CI simulation (B1).** Fresh clone, Python 3.12.13, Node v20.20.2:
  - build, then unit suite: **Ran 480 in 70.2 s, OK, 480 `... ok`, 0 skipped**;
  - `qa.py` PASS;
  - STIG sums 5/5 OK; `--accuracy` PASS;
  - gitleaks 8.30.1 on 226 commits and the working tree (~84.8 MB): no leaks;
  - size report; drift check byte-identical.
- **Normal toolchain** (Python 3.14.6, Node v22.23.2):
  - **Ran 480 in 66.0 s, OK, 0 skipped**;
  - two build + placeholder-provenance cycles were byte-identical to the committed HTML, sidecar and provenance;
  - `qa.py` Q1–Q26 + JS PASS; `--accuracy` (Q10, Q11) PASS;
  - `--size`: 8,944,791 bytes total, data island 3,193,385, shell 5,751,406;
  - STIG sums 5/5; release facts current;
  - `git diff --check` clean for the working tree, `79af6d1..HEAD` and `origin/main..HEAD`;
  - gitleaks over all 42 refs (scratch mirror, 229 commits): no leaks.
- **Hostile-input harness** (template and artifact give identical results):
  - 168,697 checks (166,569 rejected, 2,128 quoted-safe);
  - 27,652 pipeline checks (27,168 rejected, 484 composed);
  - 741 oracles, 232 one-stage invariants, 492 positive controls, **0 failures**.
- **JavaScript suites:**
  - review-closure suite 78/78 on both template and artifact;
  - rail keyboard, responsive controls, favorites, evidence export and invisible-coverage suites: 0 failures on both;
  - search index, reference index and real export: 0 failures on the artifact. They only run on the artifact by design, since the template has placeholder islands.
- **Browser audits.** Fresh Chrome 154.0.8037.58 headless, separate profiles and ports (9341 for `file://`, 9342 for HTTP), my own `http.server` on 127.0.0.1:8897 serving a clone whose artifact hash I had checked, and separate `AUDIT_OUTPUT` files:
  - **`file://` 898/898 and HTTP 898/898**, 0 exceptions, 0 console errors, 109 controls typed key by key.
  - Assertion IDs and their order are identical across my two runs and the two committed records; only TC-PERF-001/002 differ.
  - A passive CDP monitor saw 9 Document loads per mode, all of the artifact itself: no other requests, failures, websockets or Log/CSP entries.
  - The server log shows one 200 and one 304, both for the artifact.
  - Chrome's NetLog shows only Chrome's own background Google traffic (initiator "not an origin").
  - CSP: `default-src 'none'; connect-src 'none'`. The shell has no fetch/XHR/WebSocket/`src=`/CSS `url()`; its eight `https://` strings are attribution text.
- **Release documents:**
  - BQP, QA, Security and Release reports each contain the canonical totals line exactly once, plus the byte count, SHA-256, fingerprint and `5b868f10`; the BQP summary also has the sidecar and provenance hashes. No stale tokens remain.
  - The QA HTML's 898-row table matches the standalone JSON exactly (ID, order, area, description, status, observed value). All 9 cited IDs are recorded.
  - `5b868f10..HEAD` changes only 8 docs/evidence files; the protected-path diff is empty.
- **Archives.** alpha.1 through alpha.5: HTML and sidecars are identical to each tag's `dist/` and the sidecars verify. Provenance differs only in `git_commit`, which matches each tag's target commit.

## 5. Mutation and control results

| Mutant (in `commands.json:5784` SCP, `:5846` rsync) | SCP | rsync |
|---|---|---|
| `rm -f … \|\| return 0` | (a) `0 != 1` | (a) `0 != 1` |
| `[ -L … ] \|\| return 0` | (b) `0 != 1` | (b) `0 != 1` |
| final `return 0` | (c) `0 != 1` | (c) and persistent test: `0 != 1` |
| outer `exit 0` | (c) `0 != 1` | (c) `0 != 1` |
| `rm -rf -- "$txn"; exit 1` | (c) `FileNotFoundError …/state` | same |
| copy through the link | 2 inventory failures | 5 inventory failures |
| write-then-refuse, Recover / Finalize | inventory, both | inventory, both |

- In each run, only the intended tests failed; the rest of the 27-test module passed.
- Remote shell variations: dash, bash-as-`sh` and zsh-as-`sh` each pass 27/27, with 125 remote `sh -s` calls logged per run.
- **Keyboard mutants:** 7 of 13 caught by the structural test (late window keydown/keyup, `.onkeyup=`, `.call`, single-quote and newline forms, `.click()` in the handler). The 6 that survive are listed in O2.
- **Negative controls:**
  - `shQuote()` without escaping: 241 hostile-harness failures.
  - `esc()` without `'`: 2 escaper unit failures and `qa.py` Q19 FAIL.

## 6. Identifiers

| Item | Value |
|---|---|
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`, 8,944,791 bytes |
| SHA-256 | `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Sidecar SHA-256 | `b18d1303c69b81ca4bdf405d704313cc512751f1f265c35987742fb3ce31b335` |
| Provenance SHA-256 | `aa11a5fb4a81197e159802d8b72c216b1a4063b7ad725b55112db2722aa3f8c5` (`TAG_COMMIT_PLACEHOLDER`; python3 3.14.6, node v22.23.2) |
| Content fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Implementation commit | `5b868f10eec73bf6207113f56c41d42eb6802b1d` |
| Reviewed HEAD / tree | `bccd26398cff847033e36f3dbb82d5852393264c` / `6de2763a86e5f6d7fee67affe17b3e9f8db8a8ad` |

## 7. Limitations

- **No live receiving RHEL host.** All remote scripts ran through the repo's fake `ssh`/`stat`/`mv`/`rm`/`mkdir` on macOS, with GNU `mv` 9.10. EPERM, sticky-directory and mv-over-link failures are simulated by wrappers. Real sshd, scp, rsync, nmcli, SELinux and root were not exercised.
- **CI was simulated locally**, on macOS rather than a Linux Forgejo runner. Gitleaks ran as the local binary, not through the action, and the upload step was not run.
- **Browser coverage is headless Chrome only**, with no assistive technology.
- **The artifact is unsigned**; integrity rests on SHA-256 and Git history.
- **Mutation testing was targeted**, not exhaustive.

## 8. Tree state and cleanup

- **Repository unchanged** from start to end:
  - HEAD and branch;
  - `git status` including ignored files;
  - index entries and bytes (mtime 13:05:01, the HEAD commit time);
  - `.git` HEAD and config;
  - all 42 refs, with 0 stashes and 1 worktree;
  - all 583 working-tree files by SHA-256, size, mode and mtime.
- **`.git` directory timestamp.** It read 13:05:55 at my first snapshot, probably from my first plain `git status`. It later moved to 13:42:34 with the same 11 entries and no lock files. I ran only read-only git commands there, with optional locks disabled.
- **Disk space.** The shared volume had about 1 GB free. My parallel scratch clones briefly filled it (ENOSPC). I deleted only my own finished clones; the hash comparison above shows the reviewed repository was never written. Other processes on this machine could have hit write errors during that short window.
- **Scratch area.** Everything ran under `/private/tmp/mdcr-review-bccd263`, including the downloaded Node 20, and that directory has been removed.
- **Processes.** I stopped my Chrome instances, HTTP server and monitors by their own PIDs or profile paths, and deleted the profiles. No test temp directories remain.
- **Left alone:** your PIDs 1071, 18179 and 20963–20972; `/tmp/mdcr_functional_audit_results.json` (`a0167262…`, unchanged); and the system clipboard, since copies were intercepted inside the page.

Several MCP connectors (Figma, Google Drive and others) need authorization, in claude.ai connector settings or via `/mcp`. A few others (anvil-cyber, anvil-qa, Gmail/Calendar plugins) failed to connect. This review did not need any of them.
