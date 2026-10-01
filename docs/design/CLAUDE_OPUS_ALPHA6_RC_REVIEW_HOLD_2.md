# MD CODE RED v1.0.0-alpha.6 — final release review of HEAD `9d8934e`

## Decision: **HOLD**

There are no Blocker or Critical findings. The artifact is intact and rebuilds byte-for-byte. All QA gates pass (Q1–Q26 plus the JavaScript check), all 424 unit tests pass, the 145,345 hostile-input checks pass, and Gitleaks is clean. The three prior shell-safety and runbook findings (M-1, M-2, M-3) are genuinely fixed.

It is still a HOLD for three reasons. Three problems of Major severity remain, all about trust labels and evidence attribution. Two documentation items from prior m-1 are still wrong. And there are seven new Minor findings.

## Target and worktree state

- **HEAD:** `9d8934e6c891b38963ccca456baf4c66ab7746b5` on `codex/alpha6-responsive-ux`. It is 4 commits ahead of origin, so it has not been pushed.
- **Worktree:** clean before and after the review. Only the ignored `__pycache__/` folders exist, and there are no stashes.
- **Artifact:** `d1949c9e…` (8,902,185 bytes); sidecar `9059fb60…`; provenance `954c9138…` (still `TAG_COMMIT_PLACEHOLDER`). All three match the build-quality summary, the release report and the RC QA HTML.
- **Method:** nothing in the repository was modified.
  - The full unit suite ran in a `git archive` copy under `/tmp`, deleted afterwards.
  - UI behaviour was checked by running the shipped artifact's own app script under Node with a simulated page.

## Prior findings: closure

| Prior | Status | Evidence |
|---|---|---|
| **M-1** Typed values could run commands on the remote host via scp/rsync/ssh | **CLOSED** | Remote destinations must match `[user@]host:/absolute/path` with a restricted character set (`template.html:801-817`). ssh now takes separate username (`-l`) and hostname fields. rsync always passes `-s`. Values such as `;id`, `$(id)`, spaces, `~`, relative paths, `host::module` and IPv6 literals are refused. |
| **M-2** curl/wget labelled "Read only" while writing files | **CLOSED** for those two forms | Both are now yellow and their output field is a write target (`:1673-1690`). Only http(s) URLs are accepted. Writes into directories the system executes (cron, systemd, `/usr/local/bin`, `/opt`) are refused; `/etc/hosts` and `/dev/sda` are red. The same problem survives in pipelines (N-1). |
| **M-3** Runbooks copied hardcoded example values | **CLOSED** | Preflight steps now use your own values (`ps -p 4321`, `git diff -- config/prod.yml`, `id bob`). A new schema rule plus a negative test catch regressions. An unresolved `<previous_group_list>` blocks both Copy Recover and Copy complete plan. |
| **M-4** Pipelines showed "Verified" | **STILL OPEN** (partly) | Complete pipelines now show "Composed — not host-verified" everywhere. Two residuals remain, described below. |
| **m-1** Stale counts in the docs | **STILL OPEN** | Most are fixed. Two remain:<br>• `USER_GUIDE.md:193-196` refers to a "muted blast line" that no longer exists.<br>• `USER_GUIDE.md:319-321` says only `gen-sshd-test-config` prints `Requires: root`; 37 entries do. |
| **m-2** Evidence wording | **CLOSED** | `git diff --check` is clean, and the inaccurate Gitleaks and coverage claims were removed. |
| **m-3** Field types and intents | **CLOSED** | Git paths are literal (`*.py`, `:/config` refused). Shell variable names and PIDs have proper types (`my-var` and PID `0` refused). The kill and ssh intents are corrected. |
| **m-4** Duplicate Git recovery entries rated differently | **CLOSED** | Both are yellow. |
| **m-5** Home "Install a package" card | **CLOSED** | At runtime it opens the yum form on RHEL 7 and the dnf form on RHEL 8, 9 and 10. |
| **m-6** Contrast and live announcements | **CLOSED** for the reported colours | Muted text is now 5.26–5.96:1; the focus ring is 4.35–4.92:1. |
| **m-7** Pipeline UX | **CLOSED** | Incomplete pipelines show "Complete the pipeline"; flags are looked up against their own stage's tool; operators show the text that is actually emitted. |
| **m-8** grep source label | **CLOSED** | Now "GNU grep 2.20-3.11". |
| **m-9** Test strength | **CLOSED** for the listed gaps | Runtime tests now exist for the assembler, runbooks, pipeline trust labels and Home routing. Remaining test-integrity problems are listed under N-6. |

## Open findings, most severe first

### Major

**N-1. Pipelines that write files say "Read only".**
- **Trigger** (confirmed at runtime): `journalctl --no-pager --unit='sshd.service' > '/root/.bashrc'` is rated green, the trust bar says **Read only**, and there is no warning banner. The same happens for `> /root/.ssh/authorized_keys` and `| tee /home/alice/.bash_profile`.
- **Cause:** `/home` and `/root` are treated as scratch space and rated green (`template.html:2108`, `:2187-2195`, `:2302`). The trust bar turns green into "Read only" (`:4968`, `:5143`).
- **Why it matters:** this contradicts `USER_GUIDE.md:183`, the alpha.6 rule that other writes are at least yellow (`SECURITY_REVIEW:20-22`, `CHANGELOG:13-16`), and `curl -o /root/.bashrc`, which is yellow. It is the same class of defect as prior M-2.
- **Fix:** never show "Read only" when a stage writes a file. Treat shell start-up files and `~/.ssh/` as sensitive targets (refuse them or rate them red).

**M-4, still open. Verification labels claim more than was actually run.**
- **(A) Guided-form receipts apply to any values you type.**
  - On the default release (RHEL 8), Home → "Read service logs" with unit `httpd.service` builds `journalctl --no-pager --unit='httpd.service'`. The trust bar and status bar say **Verified**, and the export says *"Verified — verified by Riley Park on 2026-09-18 (defiant-rhel8)"*.
  - The only command that was actually run was `--unit='sshd.service' --priority='err' --since='today' --boot` (`tests/captures/8/gen-journalctl-unit-logs.json`).
  - The prior review recorded this under M-4 as related and pre-existing. It has not been fixed or disclosed.
- **(B) An unfinished pipeline exports the selected entry's receipt.** While the status bar says "Pipeline incomplete", the export says "Verified — Riley Park" and includes `STIG ID: RHEL-08-040101`. The cause is that the selected entry is set aside only when a pipeline result exists (`:3799`). This contradicts `USER_GUIDE.md:241-243`.

**N-2. STIG/control identity still attaches to composed pipelines.**
- **(a) Screen and print.** The Inspector STIG panel and the print-only STIG panel show the selected entry's STIG card, including check text, fix text and captured output, while Copy copies the pipeline (`renderStigPanel`, `:3992-4056`). Confirmed at runtime with firewalld's `RHEL-08-040101`.
- **(b) Export.** A STIG rule opened from search is attached to the pipeline's export (`:3803-3806`). Confirmed at runtime with `RHEL-08-010000`.
- **Why it matters:** this contradicts `SECURITY_REVIEW:26-27` and `CHANGELOG:22-24`.

### Minor

- **m-1 residuals**, as listed in the closure table.
- **N-3. Remote copy destinations are not risk-rated.** scp and rsync targets such as `host:/etc/cron.d/x`, remote `/etc/sudoers`, or `root@host:/` are only yellow. The same writes to a local path are refused or red.
- **N-4. Pipeline flag sources are not shown as claimed.** `SECURITY_REVIEW:28` says each flag names its source stage and tool.
  - The Inspector shows bare flags (`:5284-5290`), and xargs flags carry no source at all (`:2388-2392`).
  - The pipeline export also drops `Requires: root` even though the trust bar shows it (`:2883`).
- **N-5. Accessibility.**
  - **Focus loss:** opening a Home card, a sidebar row, or switching RHEL version re-renders the page and drops keyboard focus to `<body>` (`renderAll`, `:5722-5737`).
  - **Noisy live region:** the live region on `#gen-result` is fully re-rendered on every keystroke (`:5231`, `:5840-5863`). This is likely too chatty for screen readers, but I did not test with one.
  - **Contrast:** the light theme's "Verified" badge colour `#059669` is 3.54–3.77:1 at 11px, below the 4.5:1 minimum, and no test covers it.
- **N-6. Release evidence and docs are inaccurate in places.**
  - `RELEASE_REPORT:11-13` says every prior finding is closed.
  - `QA_REPORT:25` says standalone `file://` delivery passed. The final RC audit ran over `http://127.0.0.1`; the only `file://` evidence is for an earlier artifact (`1b5419d6…`).
  - `TEST_PLAN:32` says 19,732 hostile checks; the gate now reports 23,032.
  - `USER_GUIDE:219` and `:372` say there are eight Git guided forms; there are 11.
  - `USER_GUIDE:328-331` says the fingerprint covers only the `mcr-data` block; it covers every embedded data block.
  - The closure test reports `checks:23` but only 20 run.
  - The browser check TC-DOCS-002 passes without checking any real values.
- **N-7. Small runbook text errors.**
  - The kill task's verify text still mentions `-HUP`, but the form only sends `-TERM` (`commands.json:5026`).
  - The export task's recovery text hardcodes `export -n VARNAME`, and Copy Recover copies it (`:3188`).

### Observations (not blocking)

- grep in a pipeline always needs a file argument, so `journalctl … | grep` cannot filter the piped logs.
- CI pins its GitHub-style actions by tag rather than commit SHA, and its toolchain (Python 3.12, Node 20) differs from the one recorded in provenance (Python 3.14.6, Node 22.23.2).
- The command-syntax rows for Git on RHEL 7 and 9 cite a generic `man git` rather than a captured page.

## Verification commands actually run

| Command | Result |
|---|---|
| In-memory rebuild through `build.py`'s own functions (nothing written) | **Byte-identical** to the committed artifact; fingerprint `552816ec…`; default release RHEL 8 |
| `PYTHONDONTWRITEBYTECODE=1 python3 qa.py` | **PASS**, Q1–Q26 plus JavaScript check: 145,345 hostile checks, 23,032 pipeline checks, 717 oracle comparisons, 232 one-stage checks, 68 redirect checks, 869 commands against 420 grammar rows |
| `python3 -m unittest discover -s tests` (in the archive copy) | **424 ran**. The 4 failures are all in `test_no_raw_trojan_chars`, which needs `git ls-files`; that module passes 13/13 when run in place, worktree still clean |
| `node tests/test_alpha6_review_closure.js` on the template and on the artifact | Passes; reports 23 checks but runs 20 |
| `tools/generate_release_facts.py --check`; `git diff --check` (from origin/main and from `3816597`) | PASS; exit 0 |
| `shasum -c` on alpha.1–alpha.5 archives and `stig-src` | All OK |
| `gitleaks git` and `gitleaks dir` (8.30.1) | 204 commits scanned; no leaks |
| Node runtime probes of the shipped artifact (~60 assembler inputs; full-app scenarios for pipelines, STIG panel, export, Home, runbooks) | Results as cited in the findings above |

Not re-run: the 873-assertion headless-Chrome audit (I reviewed its script and results instead), screen-reader sessions, real-host execution, and CI.

## Residual limitations accurately disclosed (not blockers)

- The release is unsigned; provenance stays at `TAG_COMMIT_PLACEHOLDER` until the tag is created and the artifact is restamped.
- Host receipts cover RHEL 7/8/9/10 as 0/9/0/9.
- RHEL 7 flags come from a UBI7 container, with only 6 tools parsed.
- The flag dictionaries have no curated explanations; 336 of 348 curated entry flags are explained.
- About 98.7% of the mined reference records are unrated; they are kept separate and copying requires an acknowledgement.
- A structurally safe command can still be operationally wrong.
- No screen-reader or cross-browser testing was done.
- The export is reference material, not proof that a command ran.

## Recommendation

**HOLD — do not tag or publish from `9d8934e`.**

The assembler is sound, but alpha.6's main promise is honest trust labels, and three defects break it: "Read only" on file writes (N-1), "Verified" on commands that were never run (M-4), and STIG identity attached to pipelines (N-2).

To reach PASS:
1. Fix N-1, M-4 (both parts) and N-2, each with a harness test and a browser check.
2. Fix the m-1 residuals and N-3 through N-7.
3. Rebuild, rerun all gates and the browser audit, including a `file://` run on the final bytes.
4. Regenerate the evidence with counts taken from the checks actually executed.
5. Repeat this review on the new HEAD.

The full report and a fix map are in `/Users/benny/.claude/plans/perform-a-comprehensive-read-only-soft-ocean.md`.

Several MCP connectors (including Figma, Google Drive, GitHub and Linear) need authorization in your claude.ai connector settings or via `/mcp`. Separately, a few other connectors failed to connect this session. None of them were needed for this review.
