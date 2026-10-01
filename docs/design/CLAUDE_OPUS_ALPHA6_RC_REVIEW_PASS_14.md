PASS

I reviewed exact HEAD `e214972e3e51493255717db6607f03c0a6e0a803` (tree `cb60b43e32d77e488e1c76364bfbe2682f0dc009`) on `codex/alpha6-responsive-ux`. All test runs happened in disposable clones, and the reviewed repository is byte-for-byte unchanged.

I found no blocking, high or medium defect. The review-13 blocker H1 is closed. I reproduced the fix with a real merge commit, a committed post-merge stamp, the full release gates and 30 rejection controls (22 bad stamps, 8 protected-path changes).

The artifact is the same one review 13 assessed. Nothing that builds into it has changed since `bccd263`; only tests, the browser auditor and docs changed. What remains is two low-severity observations and four nits. None affects the shipped bytes.

## 1. Identity

| Item | Value |
|---|---|
| HEAD / tree | `e214972e3e51493255717db6607f03c0a6e0a803` / `cb60b43e32d77e488e1c76364bfbe2682f0dc009` |
| Implementation commit (browser evidence) | `11b167159cb2246004e5f457df6f0c155d1c32cb`. From it to HEAD only 9 docs/evidence files change; the protected-path diff is empty. |
| Artifact | 8,944,791 bytes, SHA-256 `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Content fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Sidecar SHA-256 | `b18d1303c69b81ca4bdf405d704313cc512751f1f265c35987742fb3ce31b335` |
| Placeholder provenance SHA-256 | `aa11a5fb4a81197e159802d8b72c216b1a4063b7ad725b55112db2722aa3f8c5` (Python 3.14.6, Node v22.23.2) |

## 2. Gates at exact HEAD

Toolchain: Python 3.14.6 and Node v22.23.2, the release-workstation toolchain.

- **Build:** byte-identical to the committed artifact. The CI drift step rebuilds identically, and regenerating the placeholder provenance gives the same bytes.
- **Unit suite:** ran 480 in 66.9 s; all 480 ok, 0 skipped, 0 failed.
  - Under Python 3.12.13 (the CI interpreter) it also discovers 480 and passes. The build is the same, `qa.py` passes and the tree stays clean.
- **QA gates:**
  - `qa.py`: Q1–Q26 + JS PASS.
  - `--accuracy`: Q10 and Q11 PASS.
  - `--size`: 8,944,791 bytes total; data island 3,193,385; shell 5,751,406.
  - STIG checksums 5/5 OK; generated release facts are current.
- **Hostile-input harness:**
  - 168,697 checks: 166,569 rejected, 2,128 quoted-safe.
  - 27,652 pipeline checks: 27,168 rejected, 484 composed.
  - 741 oracles, 232 one-stage invariants, 0 failures.
  - Template and artifact give identical results.
- **JavaScript suites:**
  - Review-closure suite: 78/78 on both template and artifact.
  - Rail keyboard, responsive controls, favorites, evidence export and invisible-coverage suites pass on both.
  - Search index, reference index and real export pass on the artifact. They fail on the template only because it holds `/*__DATA__*/` placeholders, which is by design.
- **`git diff --check`:** clean for the working tree, `11b1671..HEAD`, `bccd263..HEAD` and `origin/main..HEAD`.
- **Gitleaks 8.30.1** with `.gitleaks.toml`: 229 commits (about 137 MB) and the working tree (about 84 MB), no leaks.

## 3. Browser evidence

**Committed records.**
- Both modes are bound to `11b16715…` and have 898 records each, all PASS, with no failures, exceptions or console errors.
- Byte count, SHA-256, fingerprint, `loadedArtifactBytes` and `loadedArtifactSha256` all match disk in both modes.

**My own reproduction.**
- Setup: headless Chrome 154.0.8037.58 with separate profiles and ports, and my own `http.server` on 127.0.0.1:8941.
- `file://` and HTTP each gave 898/898, with no exceptions or console errors. The bytes Chrome loaded equal the bytes on disk in both modes.
- IDs, order and every field match the committed records, except the two performance rows.

**Network.** A passive CDP monitor saw 9 page loads per mode, all of the artifact itself. There were no other requests, websockets, load failures, CSP/Log entries or console warnings. The server log shows one 200 and one 304.

**896 + 2 is accurate.** The only unconditional records in the auditor are TC-PERF-001 and TC-PERF-002. Every other pass has a matching fail branch.

**O4 negative control.** I served a copy of the artifact one byte longer, over both `file://` and HTTP. The auditor stopped with "Browser loaded 8944792 bytes … but the audited dist artifact is 8944791 bytes" and wrote no result file.

## 4. H1 reproduction: post-merge stamp

1. In a clone with its remote removed, I ran `git merge --no-ff` of the candidate into `main` (`78ac717`). The merge commit M is `660cee39…`; its tree equals the candidate tree, and it rebuilds identically.
2. I ran `make_provenance.py --commit M` on the same toolchain. Exactly one line changed (`git_commit`). I then set the release report to `status: released`.
3. Staging:
   - Plain `git add` of the manifest does stage it, but exits 1 with the "paths are ignored" hint.
   - The documented `git add -f` exits 0. The WORKFLOW instruction is sufficient and clear.
   - Commit S is `e2b92da…`; the tree is clean.
4. The stamped manifest, normalized back to the placeholder, hashes to `aa11a5fb…`. It is byte-equal to the manifest at the implementation commit, and the BQP summary names that hash.
5. Full Section 5 sequence on S, all passing:
   - identical build, `qa.py` PASS, `--accuracy` PASS;
   - 480/480 OK, including both readiness tests;
   - hostile harness 0 failures, release facts current, CI drift step identical;
   - tree clean afterwards.
   - The readiness module also passes on S under Python 3.12.

**Controls.** Each started from M with one change, committed unless the control was about uncommitted state.

| Result | Controls |
|---|---|
| Accepted, correctly | Committed stamp written by hand; committed stamp written by `make_provenance` |
| Rejected: uncommitted | Stamped but not committed; staged but not committed; committed stamp plus a dirty rewrite |
| Rejected: "does not resolve" | All-zero ID, random nonexistent ID, a tree SHA, a blob SHA |
| Rejected: "not an ancestor" | Orphan commit, side-branch commit |
| Rejected: "full lowercase SHA" | Uppercase, 12-character, trailing newline, null |
| Rejected: "fields other than git_commit" | Stamp made with Python 3.12 or Node v25; changed `build_date`, `artifact.sha256` or review lineage; extra key; `roster` removed |
| Rejected by the BQP hash test | 18→18.0 and 5→5.0 type drift |
| Protected paths still guarded | With a valid committed stamp, changes to `template.html`, dist HTML, sidecar, tests, `ci.yml`, `content`, `qa.py`, or an uncommitted `template.html` edit all fail |
| Accepted edge cases | Stale ancestors, a tag-object SHA, reformatted JSON, nested extra manifests (see L1, L3, L4) |

## 5. Review-13 observations

| Item | Status | Evidence |
|---|---|---|
| O1 retry wording | Closed | Ran SCP and rsync through the fake-SSH harness. The failed Recover exits 1. A retry with the link present gives `Refusing: symlinked scp\|rsync destination`. After the link is removed it gives `recovery swap already exists`. The guided `mv -T` then a retry exits 0, restores `before`, removes the transaction, and leaves the outside sentinel alone. Matches `USER_GUIDE.md:183-187`. |
| O2 keyboard guard | Named forms closed; wording slightly broad (L2) | Every named form I tried (13 variants) is rejected, and the one real keydown listener survives. |
| O3 probe wording | Closed | "External" in `SECURITY_REVIEW:88`, `QA_REPORT:94` and the QA HTML. |
| O4 loaded bytes | Closed | See §3, including the negative control. |
| O5 896 vs 898 | Closed | All four reports carry the canonical line once, and the QA HTML headline says 896 + 2. The per-row table still shows a PASS badge on the two performance rows. |
| O6 candidate-specific binding | Closed in substance | `WORKFLOW.md:267-270` scopes it, and the paths match the code. The cost is implied rather than stated (L5). |
| O9 review index | Closed, minimally | A `CLAUDE_OPUS_ALPHA6_RC_REVIEW_*.md` pattern row; all 13 records exist. Records 9–13 are byte-identical to the raw review outputs in `/tmp`. |

O7, O8 and O10 were not asked about. Their code and tests are unchanged.

## 6. Security and scope

- **Recovery, fallback and no write-through:**
  - The transaction suite passes.
  - Four targeted Recover mutants were caught by the intended tests: `return 0` in the link check, an unbounded retry loop, `exit 0` after a failed swap, and dropping the SCP destination refusal.
  - The O1 run left the outside directory untouched.
- **CSP and network:**
  - CSP: `default-src 'none'`, `connect-src 'none'`, `img-src data:`, `object-src`/`base-uri`/`form-action 'none'`, `script-src 'unsafe-inline'`.
  - The application shell (the HTML without its data islands) has no fetch/XHR/WebSocket/beacon/Image/Worker/`window.open`/`location` sinks, no external `src`, `url()`, `link` or `iframe`, and no `eval` or `new Function`.
  - Its eight `https://` strings are attribution text.
  - The 45 `innerHTML` writes remain under the existing escaper gates.
- **Keyboard and evidence export:** TC-COPY-001/002 confirm one click and one clipboard write; Q24 and the export suites pass.
- **No evidence laundering found:** the committed browser records reproduced exactly, and the committed review records match the raw outputs.
- **Trust anchor (informational, pre-existing):** the provenance baseline comes from an immutable Git object. However, the commit that selects it is the `meta.commit` field in the unprotected `docs/qa` JSON.
- **Release process:** no contradiction between WORKFLOW steps 5–8 and the gates.

## 7. Findings

Blocking, high and medium: none.

**L1 — Low: the stamp check proves ancestry, not that the stamp names the tag target** (`tests/test_release_readiness.py:41-52`)
- These were all accepted with both readiness tests passing:
  - the alpha.5 tag target `e2991029…`;
  - the repository's root commit `004a768…`;
  - the pre-alpha.6 `main` commit `78ac717…`;
  - an annotated-tag object SHA, because `^{commit}` and `merge-base` both peel it to its commit.
- Impact: a copy-paste slip at step 6 would pass CI. Only the manual read-back in step 8 would catch it.
- The docs accurately say "ancestor", so this is not an overclaim.
- Fix:
  - require `git cat-file -t <sha>` to be `commit`;
  - require `git merge-base --is-ancestor 11b1671 <sha>`;
  - optionally, require an empty protected-path diff from the implementation commit to the stamped commit.

**L2 — Low: the keyboard source guard is narrower than three doc sentences** (`tests/test_instructional_ux.py:77,95,98`)
- These ordinary, non-obfuscated forms get past it:
  - `KEYMAP.push({keys:["Enter"],…})`;
  - `keys: ["Enter"]` written with a space, or `"keys":[…]`;
  - a shared key constant, or an inner `];` that cuts the KEYMAP slice short;
  - a helper called from the handler;
  - inline `onkeyup=`/`onkeydown=` attributes, which the CSP allows, plus `setAttribute("onkeyup")` and `Object.assign({onkeyup})`.
- I built a `KEYMAP.push` Enter/Space→`click()` artifact (`b5a572c0…`).
  - It passed `qa.py` and the browser audit at 898/898, with TC-COPY still single-fire.
  - Only the two artifact-hash tests failed, and those fail on any byte change.
- Docs broader than what is enforced:
  - `QA_REPORT…:99`: "keeps Enter and Space out of the global shortcut table";
  - `ARCHITECTURE_BIBLE.md:439-442`;
  - `RELEASE_REPORT…:73-74`: "prevents a late synthetic copy handler".
- The shipped template has none of these forms. Fix by tolerating whitespace and quotes in the KEYMAP check, banning `KEYMAP.push/unshift/splice` and `onkey*` everywhere, or checking KEYMAP at runtime. Alternatively, narrow those three sentences.

**Nits**
- **L3** (`:179`): `:(exclude)dist/*.provenance.json` matches at any depth. A committed `dist/sub/evil.provenance.json` passed both readiness tests and `qa.py`; a top-level stray is caught by `qa.py`. Exclude the exact file instead.
- **L4:** validation is semantic, not byte-level. Reformatted JSON and duplicate `git_commit` keys are accepted (Python keeps the last). Type drift is caught only by the BQP hash test.
- **L5:** O6 states the rule but not its effect. CI on `main` and every branch goes red on any protected-path change until a new candidate is bound. Step 9's archive move also removes the alpha.6 files these tests open.
- **L6:** a Recover that fails on an unremovable link prints no MD CODE RED message; `USER_GUIDE:183-184` calls that "refused". The guidance still restores correctly.

## 8. Limits

- **No live RHEL host.** The remote scripts ran through the repo's fake `ssh`/`stat`/`mv`/`rm`/`mkdir` on macOS, with GNU `mv` 9.10.
- **CI was simulated locally**, with Python 3.12.13 and Node 22, not Node 20 on a Linux runner. Gitleaks ran as the local binary, not through the action.
- **The release was simulated** with a local `--no-ff` merge: no push, remote tag or publication. A squash or rebase merge would drop `11b1671` from `main`'s history. If the release branch is then deleted, the readiness tests could not find that commit. WORKFLOW implies a merge commit, and alpha.5 used one.
- **Other limits:** browser coverage is headless Chrome only, with no assistive technology; the artifact is unsigned; mutation testing was targeted, not exhaustive.

## 9. Tree state and cleanup

- **Reviewed repository unchanged.** Snapshots before and after are identical: HEAD and branch, `status --ignored`, 42 refs, stash, worktrees, index bytes, `.git` HEAD/config/index, and all 584 files by SHA-256, size, mode and mtime.
- **Possible `.git` timestamp touch.** My first plain `git status`, run before I set `GIT_OPTIONAL_LOCKS=0`, may have updated the `.git` directory mtime. The index itself was not rewritten.
- **Cleanup done.**
  - Clones, Chrome profiles and the mutant server directory are deleted, and all my processes are stopped.
  - `/tmp/mdcr_functional_audit_results.json` is untouched (`a0167262…`).
  - Logs and scripts (1.9 MB) are in `/private/tmp/mdcr-review14-e214972/`.

Several MCP connectors (Figma, Google Drive and others) need authorization in claude.ai connector settings or via `/mcp`. anvil-cyber, anvil-qa, ayoitson-command-center and some plugins failed to connect. This review needed none of them.
