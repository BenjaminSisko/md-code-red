VERDICT: HOLD

I'm holding this candidate for one Major issue that is new in this round. The sixth-review items are closed in the code, but the new NetworkManager rollback keeps its root-run state somewhere any local user can write. Everything else I reran reproduces the committed evidence exactly.

## Blocking finding

### MAJOR-1: NetworkManager rollback state sits at a fixed path in world-writable `/var/tmp`, and Recover trusts it without checking who created it

- **Where:**
  - Preflight: `content/instructional.json:1040`
  - Finalize (inside the Verify text): `content/commands.json:665`
  - Recover: `content/commands.json:666`
  - The "root-only" claim: the rendered UI text at `content/instructional.json:1041`, `docs/USER_GUIDE.md:522` and `docs/CHANGELOG.md:11`
- **Defect:**
  - The state lives at `/var/tmp/mdcr-nmcli-static-ipv4.txn`, which any local account can create.
  - Preflight checks the path exists only *before* its final `mv`, so the two steps are not atomic. If the path is created in between, `mv` places the snapshot inside it and Preflight still exits 0.
  - Recover and Finalize never check that the directory is a real directory (not a symlink), owned by root, with mode 0700. Recover then copies `$txn/before` over the live profile as root.
- **Evidence:** I ran the exact strings the browser rendered, with fake `sudo`/`nmcli`, under bash and dash.
  - When a directory or symlink that Preflight did not create was already at the path, Preflight correctly refused. Recover then exited 0 and restored that directory's content into the profile.
  - When the path appeared mid-Preflight, Preflight exited 0, but the snapshot was not at the documented location.
  - `/var/tmp` was clean afterwards.
  - The repo test covers only the normal path (`tests/test_instruction_command_binding.py:73`).
- **Impact:** a local unprivileged user can block the documented rollback of a change that can lock you out, or make root restore a profile that Preflight never saved. That contradicts the "root-only" wording shown to operators.
- **Fix:**
  - Keep the state in a root-owned directory, e.g. created with `install -d -m 0700 -o root -g root /var/lib/mdcr`.
  - Create the final transaction directory atomically (`mkdir` at its final name, or `mv -T`).
  - Make Recover and Finalize refuse unless `$txn` is a non-symlink directory owned by uid 0 with mode 0700.
  - Add execution tests for a pre-existing directory, a symlink, and a path created mid-Preflight.
  - Correct the "root-only" wording, or make it true.

## Sixth-review items

| # | Status | What I verified |
|---|---|---|
| 1 | **Functionally closed, but see MAJOR-1** | <ul><li>Values are shell-quoted for commands (`template.html:3293-3305`).</li><li>Exactly one FILENAME,NAME,UUID row is required. The corpus's Red Hat docs (RHEL 8, 9 and 10) list FILENAME as a field.</li><li>The snapshot is kept outside the profile directories.</li><li>12/12 functional checks pass under each of bash and dash: one-word name, UUID, duplicate and missing names refused, symlinked profile refused, a changed filename refused with the snapshot kept, restore + reload, finalize. TC-RUNBOOK-NMCLI-001 also passes.</li></ul> |
| 2 | Closed | Exact rendered scp/rsync strings, OpenSSH-style argument joining, GNU coreutils: **30/30 in each of bash and dash**. Covered: top-level symlinks, symlinks at the resolved `dir/basename` target, trailing-slash and dangling symlinks, a target swapped after Preflight (Recover and Finalize refuse), restores, absent-target recovery, stale state, no state, capacity refusal, finalize. |
| 3 | Closed | <ul><li>Both result files record 8,933,228 bytes, SHA `241ffd0c…81da` and fingerprint `26aa47f6…6e8b`, with 897/897 PASS.</li><li>The release-document counts match my reruns.</li></ul> |
| 4 | Closed | The fix is at `template.html:6122`. With real pointer clicks and Space, at 1440 and 390 px: unticking clears "Copied…" and disables both copy buttons, and a click while unticked leaves the clipboard unchanged. |
| 5 | Closed | The check is at `template.html:829`. Typing with real keys: `/.`, `/srv/./x`, `/srv/app/.`, `..`, `//` and relative paths are refused. `.bashrc`, `.hidden`, `..hidden`, `...` and `.config/` are accepted. |
| 6 | Closed | All 14 command-linked rules, plus Enter-key selection and standalone rules, 20 cases each at 390×844 (desktop and mobile emulation) and 320×568: 60/60. In every case the palette closed, focus was on `#stig-panel`, and the card was in view, still true after 1.2 s. |
| 7 | Closed | TC-BLAST-ACK-001 and TC-REF-002 now create a real "Copied" message, then revoke it with a real click. |
| 8 | Partly closed | <ul><li>The SCP overclaim is gone.</li><li>Remaining: two minor wording issues (in the observations below) plus the "root-only" claim in MAJOR-1.</li></ul> |

## What I reran (independently)

- **Build:** two rebuilds were byte-identical to the committed artifact, and the sidecar and regenerated provenance match. `generate_release_facts --check` passes.
- **`qa.py`:** Q1–Q26 + JS, 27/27 PASS. `--accuracy` and `--size` pass, and the `stig-src` SHA256SUMS check is 5/5.
- **Unit suite:** 443 tests, OK, none skipped.
- **Hostile harness, on the template and the artifact:** 168,697 checks (166,569 rejected, 2,128 quoted-safe), 0 failed. Q18 reports 27,652 pipeline checks, 741 oracle comparisons and 232 one-stage invariants.
- **JS suites:** the closure suite is 78/78 on both the template and the artifact, and the other 8 JS suites pass.
- **Gitleaks 8.30.1:** 215 commits and the working tree, no leaks.
- **Diff and branch:** `git diff --check origin/main...HEAD` is clean, and HEAD is 21 commits ahead of `origin/main`.
- **Browser audit, on my own Chrome 154 and HTTP server:**
  - file:// 897/897 and HTTP 897/897, with zero exceptions and zero console errors.
  - Results are identical to the committed files except the two timing rows (TC-PERF-001/002).
  - Clipboard contents equal the displayed text for all 6 steps I checked (Preflight, Verify and Recover for SCP and nmcli).

## Non-blocking observations

- **`SECURITY_REVIEW:42-45` wording:**
  - "Preflight refuses … remote dot segments": dot segments are actually refused by the app's validator, not by the Preflight script.
  - "exact app-bound strings": the repo's tests use the app's binder but compute the derived path values themselves (`test_remote_transfer_transactions.py:47-53`). My own runs used the exact browser-rendered strings and pass.
  - `:27` "may conservatively remain yellow": yellow is the lower rating, so "conservatively" is the wrong word.
- **Weaker NetworkManager Recover guidance:** it no longer says to reactivate from the console. `nmcli connection reload` does not re-apply settings to an already-active device.
- **Needs a host check:** "Wired connection 1" profiles that NetworkManager generates in memory may get a new filename on the first modify. Recover would then refuse (fails safe).
- **Focus loss:** after activating Copy with the keyboard, focus moves to `<body>`.
- **Weak test assertions:**
  - TC-STIG-SELECT-001 does not check that the palette closed.
  - `test_release_readiness` checks counts with plain substring matches such as `"443"`.
- **Carried-over residuals:** "Copy complete plan" runs Recover right after Run if pasted into a shell, and the Verify step mixes prose with the finalize command.
- **SCP/rsync in shared directories:** their transaction directories sit next to the target, so a shared parent such as `/tmp` has a narrower version of MAJOR-1's non-atomic publish.

## Limitations

- **No live RHEL host:** I ran nothing on RHEL, sshd, scp, rsync or nmcli. Every execution used fake ssh/sudo/nmcli on macOS, with GNU coreutils, bash 3.2 in POSIX mode and dash. RHEL's bash 4/5 and gawk were not tested.
- **Unsigned:** the artifact is unsigned and provenance `git_commit` is still `TAG_COMMIT_PLACEHOLDER`.
- **Partial host coverage:** host receipts for RHEL 7/8/9/10 are 0/9/0/9.
- **Browser and assistive tech:** only Chrome was tested, and no screen reader.

## How I ran it

- **Disk space:** my first clone filled the nearly-full disk. I deleted it and worked in an APFS copy-on-write copy instead.
- **Author's processes:** I didn't touch your Chrome (9232), HTTP server (8878) or `/tmp/mdcr_functional_audit_results.json`. In my copy of the audit script I changed only the output path.
- **Cleanup:** my Chrome, HTTP server and temp files are all removed.

## Tree state

- **Initial HEAD:** `647850b9ca783ebeb03897671b05fdeffd2c5326`
- **Final HEAD:** `647850b9ca783ebeb03897671b05fdeffd2c5326`
- **`git status --short`:** empty, both at the start and the end. There are no stashes and no extra worktrees.
- **Unchanged tree:** yes. A SHA-256 manifest of all 511 working-tree files (including the ignored `__pycache__`) was byte-identical at the start and end.
