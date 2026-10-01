PASS

I reviewed exact HEAD `eded0563c7a78a15c66c053db9e2e6db78c07ce5` (tree `2721274573069460a9bc8a49f4d35b8410739f30`); the tree is clean. The three commits after review 15 close L1, N1 and N2, and N3 stays closed by contract. They add no blocking, high, medium or low defect. Two nits and two informational notes remain, and none affects the shipped bytes. I worked read-only, and the checkout is unchanged.

## 1. Identity and scope

| Item | Result |
|---|---|
| HEAD / tree | `eded056…` / `27212745…`; 0 porcelain entries before and after my checks |
| `4e5c288..d1b0a44` | The only code change is `tests/test_instructional_ux.py`. The rest is six docs plus the new `PASS_15.md`. |
| `d1b0a44..HEAD` | `3f210fc` changes the 4 release docs and the 3 `docs/qa` evidence files; `eded056` changes the 4 release docs. Nothing else changed. |
| Protected paths after `d1b0a44` | No changes under the test's exact pathspec (`git diff --quiet` returns 0). `tools`, `stig-src`, `content-src`, `releases` and `.forgejo` are also unchanged. |
| Build inputs and `dist` | Unchanged since `3e5c954`, so the shipped bytes are the ones review 15 assessed |
| Review records | `PASS_15.md` is byte-identical to the raw review-15 output; earlier HOLD/PASS records are untouched |

## 2. Browser evidence
- **Records.** Both records bind to `d1b0a44`: 898/898 PASS, 0 fail, no exceptions or console errors, and the same 898 IDs in the same order.
- **Hashes.** The recorded and browser-loaded bytes and SHA match disk:
  - artifact: 8,944,791 bytes, SHA-256 `198ae590…4dacb`
  - fingerprint `871abbea…113a`, sidecar `b18d1303…b335`, placeholder provenance `aa11a5fb…f8c5`
- **It was a real re-run.**
  - Compared with `4e5c288`, only `meta.commit`, the HTTP port and TC-PERF-001/002 changed.
  - The raw outputs `/private/tmp/mdcr-alpha6-review16-{file,http}.json` were written at 15:17, after `d1b0a44` (15:16:36), and are byte-identical to the committed records.
  - The Chrome logs contain only display, updater and GCM noise.
- **HTML report.** It has 898 record rows in JSON order, all PASS, with the new performance values and no `3e5c954`.

## 3. L1 closed
- **No stale SHAs.** `c97a614`, `1e96531`, `f25279d`, `3e5c954` and `4e5c288` appear nowhere in `docs` outside `docs/design`.
- **Content.** All four reports record:
  - merge `edc5e1b`, implementation `d1b0a44` and stamp `f8b3c07`;
  - 480/480, Q1–Q26 + JS PASS, and a clean tree.
  
  BQP and RELEASE also name candidate `3f210fc`.
- **The review16 logs agree.**
  - The merge stat equals `git diff --stat --summary main 3f210fc`. `main` (`78ac717`) is an ancestor, so the merge tree is the candidate tree.
  - The clone was made at 15:18:42, between `3f210fc` (15:18:28) and `eded056` (15:20:24).
  - The provenance log stamps `edc5e1b` with the same artifact SHA and fingerprint.
  - `f8b3c07` changed 2 files, with 2 lines in and 2 lines out. The stamp rebuild produced the same SHA, and `qa.py` on the stamp passed.
- **Rule text.** The text matches `canonical_placeholder_provenance` at `BQP:35-40`, `RELEASE_REPORT:78-81`, `SECURITY_REVIEW:125-127` and `WORKFLOW:238-243`. It covers:
  - canonical JSON, identical to the `make_provenance.py` writer;
  - a full lowercase SHA that names a commit object;
  - a stamp at or after the implementation;
  - a stamp in HEAD's ancestry;
  - only `git_commit` normalized, every other field byte-compared, and an uncommitted stamp refused.

## 4. N1 closed
- **Template.**
  - Outside comments, `KEYMAP` appears only at lines 6288 (declaration), 6370 (length check) and 6371 (indexed read).
  - There is exactly one keydown literal and listener (6328).
  - There is no `onkey*` in any case, and no `dispatchEvent`, `MouseEvent` or click-call form.
- **Committed mutants.** All 25 (14 earlier and 11 new) are rejected. `test_instructional_ux` plus `test_release_readiness` pass 18/18 on Python 3.14.6, 3.12.13 (the CI interpreter) and 3.11.15.
- **My own in-memory probes.**
  - 32 code payloads in 3 places (before boot, inside the approved handler, before the controller) were 96/96 rejected.
  - 16 table payloads as the first, middle or last entry were 48/48 rejected.
  - These cover every form listed in review-15 N1 and the earlier variants.
- **Docs.** `ARCHITECTURE_BIBLE:439-448`, `QA_REPORT:96-103`, `CHANGELOG:16-20` and `RELEASE_REPORT:73-75` describe source-shape checks for named forms and disclaim call-graph or obfuscation analysis.

## 5. N2 closed
- No numeric review total remains.
- `RELEASE_REPORT:14-15` now cites the "preserved independent Claude Opus review history".

## 6. Exact-head gates
- **My targeted runs:**
  - The two test modules passed 18/18, and discovery counts 480 tests.
  - The hostile-input harness ran 168,697 checks (166,569 rejected, 2,128 quoted-safe), 27,652 pipeline checks and 232 one-stage invariants, with no failures.
  - `generate_release_facts --check` passes.
  - `git diff --check` is clean for the working tree, the index, and `4e5c288..`, `d1b0a44..`, `3f210fc..` and `main..HEAD`.
- **Logged runs:** `mdcr-review16-final-qa.log` (15:21:54, after `eded056`) shows Q1–Q26 + JS PASS. The accuracy log shows Q10/Q11 PASS, and the size log shows 8,944,791 bytes.

## 7. N3 closed by contract
`WORKFLOW:227-261` (steps 5–8) still requires the exact merge SHA as the tag target, a stamp naming it, and a read-back. No report claims the automated gate checks the tag target, so there is no contradiction.

## 8. Findings
**Blocking, high, medium and low: none.**

**Nits**
- **N-A — the keyboard guard is still slightly looser than its docs.**
  - **Lost coverage.** The old explicit `push`/`unshift`/`splice` regex was replaced by "exactly 3 `KEYMAP` after comment stripping". That loses two contrived forms the `4e5c288` guard rejected; I ran both against the old and new test code:
    1. A `KEYMAP` write on the same line after a `//` inside a string. The comment stripper does not know about strings, and at least 17 template lines contain `"https://…"`-style strings.
    2. A count-preserving swap: remove the `KEYMAP.length` read and add a push.
  - **Unlisted forms that also pass:**
    - shorthand `keys`, computed `["keys"]`, or a getter;
    - escaped `"\u0045nter"`/`"\x20"`;
    - `b.keys.push("Enter")` inside the approved loop.
  - **Doc gap.** "may appear only in its declaration, length check, and indexed read" (`ARCHITECTURE_BIBLE:442-443`, `QA_REPORT:100-101`) names positions, but the test only counts occurrences.
  - **Why it is only a nit.** None of these forms is in the shipped bytes, and TC-COPY-001/002 still prove single-fire Enter and Space.
  - **Optional fix.** Assert the three exact spans and keep the method regex on the raw text.
- **N-B — stale wording in the release report.**
  - `RELEASE_REPORT:89-91` reads "The first prior … review records…". The word "first" is left over from the old "first through thirteenth".
  - The list also omits the now-preserved fifteenth PASS. Because the list is introduced with "including", this is not inaccurate.

**Informational**
- **I-1 — part of the stamp result has no saved log.**
  - No persisted log in `/private/tmp/mdcr-review16-*` shows the stamp's 480/480 or clean-tree result, and the disposable clone has been deleted.
  - Everything that was logged matches the docs, and the claim is consistent with the gate logic at HEAD.
  - I did not re-run it, as you instructed.
- **I-2 — one historical row understates the rule.** In the QA HTML report, the stamp row under the "Thirteenth-review closure" heading still describes the earlier ancestor-only rule. It understates rather than overclaims, and it was outside L1's scope.

## 9. Limits and state
- I used no clone, worktree or Chrome, and did not rerun the full suite. Python ran with `PYTHONDONTWRITEBYTECODE=1` and git with `GIT_OPTIONAL_LOCKS=0`.
- HEAD, the hash of `git status --ignored`, the hash of the index entries, and the `.git/index` mtime (15:21:04) are identical before and after.
- My only write was a 448 KB tool-output file that the harness spilled under `~/.claude/projects/…`.
- The volume is still at 100% with about 1.2 GiB free.
- Several MCP connectors need authorization or failed to connect. This review didn't need any of them.
