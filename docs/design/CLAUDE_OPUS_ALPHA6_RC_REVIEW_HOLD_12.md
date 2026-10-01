VERDICT: HOLD

The shipped artifact is correct, and it is byte-identical to what the eleventh review examined: no product file changed since `62101c7`. All three eleventh-review blockers are closed for every broken form you named. I'm holding for three reasons:
- **Broken CI:** the new CI order makes the candidate's own Forgejo CI fail on a clean checkout.
- **Weaker test:** the same fix commit made one test weaker.
- **Unprotected fail-closed paths:** two of Recover's fail-closed paths can be broken with every gate still passing.

Each fix is a change to CI, tests or docs only; none touches the artifact.

## 1. Blocking findings (most severe first)

### B1 — MAJOR (release process; artifact unaffected): Forgejo CI fails at step 2 on this HEAD
- **Where:**
  - CI step 1 now runs `python3 extract/make_provenance.py` (`.forgejo/workflows/ci.yml:54`) on Python 3.12 / Node 20 (`:38`, `:43`).
  - The provenance file records those versions (`extract/make_provenance.py:341-343`). The committed copy says 3.14.6 / v22.23.2.
  - Two release-readiness checks then fail: the new "no uncommitted protected changes" check, which covers `dist` (`tests/test_release_readiness.py:138-145`), and the BQP summary's provenance-hash check (`:79`).
- **Reproduction:** fresh clone of `79af6d18`, with `python3` pointing at 3.12.13.
  - `build.py` produces a byte-identical artifact (`198ae590…`).
  - `make_provenance.py` dirties `dist/md-code-red_v1.0.0-alpha.6.provenance.json`; the only change is `"python3": "3.12.13"`.
  - Unit discovery: **Ran 477, FAILED (failures=2)**. The two failures are `test_browser_results_and_release_docs_bind_to_current_candidate` ("protected implementation paths have uncommitted changes") and `test_bqp_summary_names_the_current_artifact_bytes`.
  - Node 20 would change the `node` field the same way.
- **Control:** with the committed provenance restored, both tests pass on 3.12. `qa.py`, `--accuracy`, `--size`, the STIG sums and the drift check also pass.
- **Impact:** CI stops before the QA gate, gitleaks, drift and upload steps. `RELEASE_REPORT:63` and the QA HTML evidence row (`docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html:14`) describe a CI gate that cannot pass.
- **Fix:** take provenance generation out of CI step 1 (the build alone runs the 18 artifact-backed tests), or keep `toolchain` out of the binding. Then re-run the sequence on the workflow's toolchain.

### B2 — MINOR (test regression): writing through the attacker's link is no longer detected
- **Where:**
  - 2e181c8 replaced `assertEqual(list(outside.iterdir()),[])` with a sentinel-content check at `tests/test_remote_transfer_transactions.py:481` and `:508`.
  - The persistent test (`:534`) also checks only the sentinel's text.
  - Claims this weakens: `RELEASE_REPORT:55` ("does not follow the attacker link") and `SECURITY_REVIEW:60` ("without following it").
- **Mutation:** the rsync Recover retry (`content/commands.json:5846`) was changed to `cp -R -- "$saved"/. "$target_path"/; rm -f -- "$target_path" || return 1`. This copies the saved tree into the link's target on each retry.
  - The transfer suite passes 24/24.
  - On a rebuilt artifact, 474 of 477 tests pass and `qa.py` passes. The three failures pin artifact hashes or evidence snapshots; a benign one-space edit fails the same three.
  - The **62101c7** version of this test file catches the mutant (2 failures), and the real product passes that older file.
- **Fix:** in the race tests, the persistent test and the symlinked-destination tests, also assert `sorted(p.name for p in outside.iterdir()) == ['sentinel']`.

### B3 — MINOR (evidence gap, same function as HOLD_11 MINOR-1): two fail-closed exits are unprotected
This is outside the three named closures, but it is in the same `replace_target` function and the same claim.
- **Where:** in `replace_target` (`commands.json:5846` rsync, `:5784` SCP), `[ -L "$target_path" ] || return 1`, `rm -f -- "$target_path" || return 1`, and the `exit 1` in the else branch.
- **Mutations that pass every gate:** `rm -f … || return 0` (rsync and SCP), `[ -L … ] || return 0` (rsync), `exit 0`, and `rm -rf -- "$txn"; exit 1`.
  - All pass the transfer, NetworkManager and closure suites (46 tests).
  - On a rebuilt artifact only the three artifact-pinning tests fail, and `qa.py` passes.
  - The rsync rm-fail mutant also passes the full browser audit, 898/898.
- **Impact:** a scratch probe built on the shipped test harness shows real data loss.
  - **(A) Shared sticky directory:** the parent check explicitly allows these. An attacker-owned link there can be neither replaced nor removed (EPERM). The rm-fail mutant exits **0** and deletes both `before` and `after` — the same total loss as HOLD_11 MINOR-1.
  - **(B) A directory planted at the target:** the not-link mutant also exits 0 and deletes the transaction.
  - **(C) An attacker who stops after three replants:** the product exits 1 and keeps `before`. The `exit 0` mutant reports false success; the discard mutant deletes `before`.
  - The product passes A, B and C under bash-as-`sh`, dash and zsh.
- **Claims this breaks:** `USER_GUIDE:179-180` ("A refusal is designed to preserve all rollback material") and `RELEASE_REPORT:53-55` ("preserves the full transaction").
- **Fix:** commit scenarios A (SCP and rsync), B and C as tests. Each should assert exit 1, that `state` and `before` (and `after` where present) remain, and that the decoy directory holds only the sentinel.

**Non-blocking issues (fix recommended):**
- **N1 — operator guidance is incomplete.** After the documented persistent failure, following `USER_GUIDE:175-179` ("resolve the symlink… then retry the generated Recover step") gives `Refusing: recovery swap already exists`. The target path is left empty, and the guide never says what to do with `after`. Document the manual swap-back step.
- **N2 — the keyboard structural check only scans one region.** A `window.addEventListener("keydown", …preventDefault(); click())` handler, or a keyup handler with a synthetic click, placed after the boot marker passes every gate. It is still single-fire, so only the "native button semantics" wording is at risk (`ARCHITECTURE_BIBLE:437`, `USER_GUIDE:405`).
- **N3 — SCP's final `return 0` still survives** (HOLD_11 named SCP and rsync). It is practically unreachable, because `mv -T` of a file replaces a link in one rename.
- **N4 — the "independent" probe shares `operationalPlan()` with the page.** Byte equality checks the click handler, not the plan itself; the marker checks and fake-SSH runs cover the rest.
- **N5 — the audit always writes to `/tmp/mdcr_functional_audit_results.json`** (`mdcr_functional_ui_audit.mjs:575`), overwriting earlier runs.

## 2. Eleventh-review closure map
| Item | Status | Evidence |
|---|---|---|
| MINOR-1 Persistent replant | **Closed** for all named forms (gaps B2, B3) | Test has `timeout=5` and asserts exit 1, link still pointing outside, sentinel unchanged, exactly 6 removals, and `state`/`before`/`after` kept. Caught: final `return 0`; `while :` and a missing increment (timeout); `-lt 2/4/1` and `-le 3`; deletion through the link three ways; dropped rollback; missing `-T`. Product passes 42/42 under bash-as-`sh`, dash and zsh (shell use confirmed by an invocation log). |
| MINOR-2 Exact Recover clipboard | **Closed** | Six wrong handlers each fail only TC-RUNBOOK-RED-GATE-001 (897/898): all four steps joined, Recover copying Finalize, Preflight or Run, Recover plus Finalize, and a trailing newline. The unmutated control passes 898/898. `preventDefault()`+`click()` inside the keydown handler fails the new structural test. My own probe (rsync, SCP and NM × 4 steps × Space/Enter): 1 click, 1 byte-exact copy, focus kept every time. Before acknowledgement, forced clicks copied nothing. |
| MINOR-3 NM pre-install | **Closed** | Target starts at 0755. Deleting the guard fails with `448 != 493 … must prevent chmod through the link`. Mode-only removal in Recover and in Finalize is caught. Finalize that never clears, or always refuses, is caught. |
| NB1 Refusal cases | Closed | 16 mutants caught: destination/target symlink, parent symlink and sticky checks in SCP/rsync Recover and Finalize, and both Preflights' parent checks. |
| NB2 Positive Finalize | Closed | SCP and NM never-clears and always-refuses mutants are caught. |
| NB3 NM state-root mode | Closed | See MINOR-3. |
| NB4 Signals | Closed | Pass with HUP and INT ignored at startup (9 subtests, exact status 1). Resetting the trap fails 9/9 (statuses 241/254/255). |
| NB5 Keydown guard | Partly closed | See N2. |
| NB6 CI builds first | Implemented, but CI now fails | Without a build, a fresh clone gives 477 OK with 18 skipped. With the new order, 2 failures (B1). |
| NB7 Release gate | Closed (see B1) | Uncommitted `extract/` and `.forgejo` edits, untracked files, and a later committed `extract/` change are all rejected. Clean and docs-only controls pass. |
| NB8 Wording | Closed | `CHANGELOG:13` says "Exit with status `1`". |
| NB9 Operator guidance | Partly closed | See N1. |
| NB10 Exact artifact selection | Closed | With a decoy `v9.9.9` artifact, 8/8 tests pass; the 62101c7 selector picks the decoy. |

## 3. Checks run and totals
- **Builds:** two build + placeholder-provenance cycles were byte-identical to the committed HTML, sidecar and provenance.
- **Unit suite:** **477 tests, OK, 0 skipped.**
- **`qa.py`:** Q1–Q26 + JS PASS; `--accuracy` PASS; `--size` 8,944,791 bytes (data island 3,193,385, shell 5,751,406).
- **STIG checksums:** 5/5 OK. Release facts current. `git diff --check` clean.
- **Hostile-input harness** (template and artifact identical): 168,697 checks (166,569 rejected, 2,128 quoted-safe), 27,652 pipeline checks, 741 oracles, 232 one-stage invariants, 0 failures.
- **JavaScript suites:** closure 78/78 and rail keyboard (7 rails) on both template and artifact; the other 7 suites on the artifact with 0 failures.
- **Browser audits:** fresh Chrome 154 and my own server for each mode. `file://` 898/898 and HTTP 898/898, with 0 exceptions and 0 console errors.
  - The audit derived 477 / 168,697 / 27,652 itself.
  - Assertion IDs match each other and the committed records; only TC-PERF-001/002 differ.
  - The server served only the artifact (one 200, one 304).
  - The only network request in my own probe was the artifact itself. The CSP sets `connect-src 'none'`.
- **Committed records:** both JSON files show 898 PASS / 0 FAIL, identical ID sets, the exact bytes, hash and fingerprint, and commit `2e181c84…`. All four canonical documents carry 477 / 168,697 / 27,652 / 898 and the same implementation commit. The QA HTML cites only recorded IDs.
- **Archives:** alpha.1–alpha.5 are byte-identical to their tags. Their provenance differs only by the documented `git_commit` stamp.
- **Gitleaks 8.30.1:** 227 commits and the working tree (about 83.5 MB), no leaks.
- **Mutation totals:** 23/23 for item 3 and NB1–3. Item 1: 12/17 caught; the 5 survivors are B2 and B3. Item 2: 6/6 payload mutants caught; of 5 double-routing variants, 1 caught by the structural test, 2 by an accident of another harness, 2 survive (N2).

## 4. Identifiers
| Item | Value |
|---|---|
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`, 8,944,791 bytes |
| SHA-256 | `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Sidecar SHA-256 | `b18d1303c69b81ca4bdf405d704313cc512751f1f265c35987742fb3ce31b335` |
| Provenance SHA-256 | `aa11a5fb4a81197e159802d8b72c216b1a4063b7ad725b55112db2722aa3f8c5` (`TAG_COMMIT_PLACEHOLDER`) |
| Fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Implementation commit | `2e181c84c0a8621c33dd3fc8d76b0a0917135930` |
| Reviewed HEAD | `79af6d18ae3dd0302c17ff571ad9e0aa43d74688` (`codex/alpha6-responsive-ux`) |

## 5. Limitations
- **No live RHEL host.** All script runs used the repo's fakes on macOS: GNU `mv` 9.10, simulated root, and simulated EPERM. Real sshd, scp, rsync, nmcli, SELinux and root were not exercised.
- **NM owner change not observable.** The fake `install` changes only mode.
- **CI was simulated locally,** with Python 3.12.13 and Node 22. Node 20 was not available, and Forgejo itself was not run.
- **Browser coverage** is headless Chrome only, with no screen reader.
- **The artifact is unsigned.**
- **Mutation coverage was targeted,** not a sweep of every refusal guard.

## 6. Tree and cleanup
- **Repository unchanged.** HEAD and branch are the same at start and end, with one worktree and empty status. Also identical:
  - all 516 working-tree files (including the 66 ignored ones) by SHA-256, and their mtime/size/mode
  - `.git/index`, HEAD and config
  - all 42 refs, with no stashes
- **`.git` timestamp.** The `.git` directory's own timestamp moved from 11:20 to 12:42:31 while its contents stayed identical.
  - My first `git status`, run before I switched to `--no-optional-locks`, explains 11:20.
  - The 12:42 change matches no git command of mine; it was most likely the harness checking the working directory.
- **Scratch area.** All work ran in copies under `/private/tmp`, which I removed.
- **My processes.** I stopped my three Chrome instances and my HTTP server by their own PIDs, and removed the three Chrome temp folders they created. No test leftovers remain.
- **Left alone:** your PIDs 1071, 1087, 2530 and 20963–20972; `/tmp/mdcr_functional_audit_results.json`, whose hash is unchanged; and the system clipboard, since copies were intercepted inside the page.

Several MCP connectors (Figma, Google Drive and others) need authorization in their settings before they can be used; this review didn't need them.
