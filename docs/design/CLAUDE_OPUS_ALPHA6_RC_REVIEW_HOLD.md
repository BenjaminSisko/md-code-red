# MD CODE RED v1.0.0-alpha.6: independent release-candidate review

## 1. What was reviewed

| Item | Value |
|---|---|
| Exact HEAD | `3816597906dd087772188073bb7e1ee452fb500d` (`codex/alpha6-responsive-ux`), working tree clean |
| Compared with | `origin/main` = merge base = `78ac717` (alpha.5 provenance stamp) |
| Range | 8 commits (`510c9a0` → `3816597`), 56 files, +34,145 / −710 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`, 8,895,469 bytes, SHA-256 `e25e88a7…c12c1e9` |
| Artifact source | `271fc9f`. `3816597` adds only docs and QA evidence; no build inputs changed after `271fc9f`. |

**Method.** Strictly read-only. I ran:
- the repository QA gate against the committed artifact;
- git, hash and archive checks;
- a static review of `template.html`, `content/*.json`, the tests, the QA evidence and the release docs.

**Limits.** I did not modify, build, commit or contact anything. The session's permission policy blocked several things:
- inline Python, direct `node`, `unittest`, `gitleaks`, and `tools/generate_release_facts.py --check`;
- `build.py`, because it writes to `dist/`.

I also chose not to run the full unit suite, because `tests/test_provenance_manifest.py` temporarily rewrites `dist/*.provenance.json`.

## 2. Findings

### Blocker — None

### Critical — None

### Major

**M-1. The new `scp` and `rsync` forms let a typed value run as a command on the remote host.**

- **Where:**
  - `content/commands.json:5786-5790`: the `scp` destination is a free-text `comment` field.
  - `content/commands.json:5842-5851`: the `rsync` source and destination are both `comment` fields.
  - `content/commands.json:5727-5731`: the `ssh` destination is also `comment`.
  - The release claim is at `docs/SECURITY_REVIEW_v1.0.0-alpha.6.md:17-18`.
  - The product's own rule (TM2-F8, `template.html:1829-1853`) refuses any stage whose argument is re-read by another interpreter.
- **Trigger:**
  - On RHEL 8 (the default release), destination `alice@host:/tmp/x;id>/tmp/p` produces `scp '/etc/app/config.yml' 'alice@host:/tmp/x;id>/tmp/p'`.
  - OpenSSH's legacy SCP protocol, the default on RHEL 7 and 8, passes the remote path to the remote login shell, so `id` runs remotely.
  - `rsync` older than 3.2.4 (RHEL 7, 8 and 9 ship 3.1.2, 3.1.3 and 3.2.3) does the same with remote paths unless `-s`/`--protect-args` is given. For example, `rsync -a -v -h '/src/' 'alice@host:/dst/$(id)'`.
  - Even harmless values containing spaces get split on the remote side, even though the UI shows them as one quoted word.
  - These are documented upstream behaviours; I did not run them on a host.
- **Impact:**
  - The security review says user values "cannot become operators", which is false for these forms.
  - The hostile-input harness reports the values as "provably confined", but it only models the local shell.
  - The forms emit identical commands on RHEL 7–10, although remote parsing differs by release.
- **Fix:**
  - Replace free text with a closed grammar: `[user@]host:/absolute/path`, built from the existing `username`, `hostname` and `path` validators.
  - Refuse shell-active characters in remote paths, and emit `-s` for `rsync` on RHEL 7–9.
  - Add hostile vectors that model the remote shell.
  - Correct the security-review statement.

**M-2. `curl` and `wget` are labelled green ("Read only") but can write downloaded content to any absolute path.**

- **Where:**
  - `curl`: green at `content/commands.json:5598`, writable output path at `5614-5643`.
  - `wget`: green at `content/commands.json:5653`, writable output path at `5669-5694`.
  - Green is rendered as "Read only" at `template.html:4885` and `template.html:5046`.
  - The single-command rating only checks dangerous patterns (`template.html:1629`).
- **Trigger:** output `/etc/cron.d/job` produces `curl -s -S -o '/etc/cron.d/job' 'https://…'`.
  - It shows as "Read only", with no banner and no acknowledgement.
  - It also composes as a green pipeline stage, while the equivalent `> /etc/cron.d/job` is refused outright (`template.html:2037-2055`, `2234-2244`).
  - The URL is free text, so `file:///etc/shadow` with an output under `/tmp` is also "Read only".
- **Impact:**
  - This contradicts the product's own definition (green means read-only, `docs/USER_GUIDE.md:183-185`).
  - It contradicts the field help: "An existing file at this path can be replaced" (`content/instructional.json:1707`, `:1738`).
  - It contradicts the pipeline rule that writes into executed directories are refused.
- **Fix:**
  - Raise the rating to at least yellow.
  - Apply the redirect-target rating and execution-sink refusal to write-destination `path` fields.
  - Restrict the URL field to http(s).

**M-3. Runbooks for the converted tasks contain hardcoded example values that can be copied.**

- **Where:**
  - `content/commands.json:9094-9095`, `r-usermod-ag`:
    - Verify: "id alice shows wheel plus all previous groups."
    - Recover: `gpasswd -d alice wheel`
  - Preflight commands in `content/instructional.json`:

    | Line | Hardcoded preflight |
    |---|---|
    | `:1688` | `ps -p 12345` |
    | `:1719`, `:1750` | `test ! -e /tmp/output.bin` |
    | `:1781` | `ssh-keygen -F server.example.test` |
    | `:1881` | `git diff -- src/app.py` |
    | `:1909` | `git show --stat a1b2c3d` |
    | `:1995` | `id alice` |
- **Trigger:**
  - Username `bob` with group `docker` produces the correct Run step (`usermod -a -G 'docker' 'bob'`). But the enabled "Copy Recover" button copies `gpasswd -d alice wheel`.
  - On the red `git checkout --` task with path `config/prod.yml`, the Preflight step reviews `src/app.py` instead.
  - `instructionIsBound()` (`template.html:3065-3070`) cannot detect literal example values, so copy stays enabled. I confirmed these strings ship in `dist/` (line 459).
- **Impact:**
  - The recovery step can remove a different, possibly privileged, account from `wheel`.
  - The safeguard before a destructive discard reviews the wrong file.
- **Fix:**
  - Use `<field>` placeholders.
  - Add a schema or test rule that generator runbook text may reference declared fields only, never golden example literals.
  - Assert runbook content in the browser audit using non-golden values.

**M-4. In pipeline mode, the new trust bar shows a "Verified" badge for a pipeline that was never verified.**

- **Where:**
  - New code: `template.html:5047-5050` and `4886-4888` read verification from the *selected entry*. Lines `5053` and `4892` label the pipeline a "reviewed task".
  - A pipeline result always replaces the selected entry's result (`3522-3526`), and selecting a different entry keeps the pipeline (`5550-5570`).
  - The inspector meanwhile says "the composed line has no single catalog receipt" (`5160`).
  - Pre-existing, same cause: the status bar (`5308-5314`) and the evidence export's `Verified (RHEL N)` line (`3786`).
- **Trigger:** on RHEL 8, add the journalctl task, add grep as stage 2, then click Edit on stage 1.
  - The preview shows `journalctl … | grep …` with "Verified".
  - Alternatively, open the static `firewalld-service-active` entry while a pipeline exists. You see the firewalld title, Verify and Undo text, and a "Verified" badge, but Copy copies the journalctl pipeline.
- **Impact:**
  - False assurance of host verification.
  - The export can carry "Verified (RHEL 8): verified by Riley Park…" into an assessment package.
  - It contradicts `docs/USER_GUIDE.md:237-239`, which says the verification displays "can never disagree".
- **Related, pre-existing:** generator badges are entry-level, while receipts cover only the golden values.
- **Fix:**
  - When a pipeline is active, render a pipeline-specific trust bar ("Composed — not host-verified", with per-stage status).
  - Take verification status from the result, not the selected entry, in the status bar and the export.
  - Add a browser assertion.

### Minor

| # | Where | Trigger and impact | Fix |
|---|---|---|---|
| m-1 | **Stale counts.** `docs/ARCHITECTURE_BIBLE.md:144` ("156 of 200"; should be 142) and `:161` ("44 of 200"; should be 58). `docs/USER_GUIDE.md:63` ("156 static"), `:469-471` ("Two guided entries are rated red"; it is three), `:185` (the muted blast line no longer exists). Pre-existing: `USER_GUIDE.md:245`, `:315`, `:461-465` (says 4 curated flags; 336 per `TEST_PLAN.md:76-77`), `:506` (default "RHEL 9"; actually 8). `docs/QA_GATES.md:102`, the named authority, still says 17,092 / 108 / 44 against the gate's 19,732 / 232 / 68. `docs/TEST_PLAN.md:93-94` ("7 other rows"; the table has 15). | The docs contradict themselves and the artifact. `CHANGELOG.md:23-25` claims these were corrected. `:52` says shortcuts were unchanged, but Ctrl+Alt+1–6 were all remapped. | Correct these and add a doc-count consistency test. |
| m-2 | **Evidence wording.** `QA_REPORT_v1.0.0-alpha.6.md:31` says `git diff --check` passed. `RELEASE_REPORT_v1.0.0-alpha.6.md:35` claims "complete pipeline regression coverage". | `git diff --check origin/main...HEAD` exits 2: trailing whitespace in `docs/design/CLAUDE_OPUS_REVIEW.md:3-8` and `UX_REDESIGN_PLAN.md:3-6`. Gitleaks' "200 commits" matches `271fc9f` (HEAD has 201 non-merge commits). The pipeline browser checks only look for substrings (`tools/qa/mdcr_functional_ui_audit.mjs:249,254`). | State the exact range checked, re-scan at HEAD, and soften the claim. |
| m-3 | **Field types.** Git path at `commands.json:6256-6262`. `export` variable typed as `service` at `:3208`. `kill` PID typed `integer` at `:5044-5050`. Stale intents at `:5025` and `:5702`. | Git pathspec magic or globs (`'*.py'`, `':/'`) widen a red discard. `export` accepts invalid names (`my-var`) and its error says "firewalld service name". `kill` accepts PID `0` (signals the whole process group). The `kill` intent still promises `-9`, and the `ssh` intent says it can "run one command", which it cannot. | Use `--literal-pathspecs`, add identifier and PID types, and update the intents. |
| m-4 | `git-recovery-lost-commit` is green (`commands.json:7350`); `gen-git-recovery` is yellow (`:7795`). | The same `git branch '<n>' '<r>'` command gets two different risk labels. | Align or remove the duplicate. |
| m-5 | Home card "Install a package" (`template.html:4080-4081`). | It routes to the static fixed `dnf install httpd` recipe — the class of defect alpha.6 set out to remove. On RHEL 7 it is an enabled button that silently does nothing (`template.html:5558`, `commands.json:9444-9448`). | Route to `gen-dnf-package` / `gen-yum-package`, and gate or disable the card. |
| m-6 | **Contrast.** Muted text `#8494ab` (`template.html:27`, `157`); dark muted `#71717a` (`template.html:44`, `53`); light focus ring `#f59e0b` (`template.html:31`). | Muted text is about 3.1:1 on white and 2.9:1 on the editor background; dark muted is about 3.7:1; the light focus ring is about 2.1:1. All are below WCAG AA. The project's own plan already measured this (`docs/design/UX_REDESIGN_PLAN.md:285`). The contrast test skips the muted color (`tests/test_responsive_controls.py:90-98`). `aria-live` was removed from `#editor-card`. | Raise the tokens, test the muted pair, and disclose it as a known limitation. |
| m-7 | **Pre-existing pipeline UX.** `template.html:3522-3525` and `4869-4879`; latent issues at `5182-5189` and `5167`. | An incomplete pipeline makes available entries show "Not available in RHEL N". Latent only: flag-explanation fallback can borrow another stage's tool dictionary (no dictionary explanations exist today), and standalone operators are shown by internal key rather than the emitted text. | Scope the result to the active selection and fix the stage attribution. |
| m-8 | `commands.json:3235`. | The grep source is labelled "coreutils 8.32-git"; grep is a separate GNU package. The inspector shows this. | Correct the metadata. |
| m-9 | **Test strength.** | The new tests are mostly string checks against the source (`tests/test_task_first_shell.py`). Nothing exercises runbook binding, pipeline trust signals, field-type suitability, or the converted forms with only some options selected (the golden fixtures cover all options on). `TC-PARAM` only checks that fields exist. | Add runtime tests for these. |

## 3. Evidence verified and commands run

**The four areas you asked about:**
- **Pipeline inspector crash: fixed.**
  - The original `TypeError … reading 'rhel_versions'` is recorded in `docs/qa/evidence/alpha6-pipeline-render-crash.json`.
  - The pipeline branch (`template.html:5158-5206`) now returns before the only `entryById(res.id)` call (`:5207`).
  - The record fields it reads match what `assemblePipeline` returns (`:2223-2358`).
  - The shipped artifact contains the branch, and the regression audit has a negative control.
  - The release-candidate browser run recorded zero exceptions in the pipeline and console checks.
- **The 14 converted recipes:** grep, kill, curl, wget, ssh, scp, rsync, git checkout, cherry-pick, branch recovery, id, usermod, export, tr.
  - All are templates with golden commands for all four releases.
  - Q26 checked 229 non-null golden commands; the 3 gated cases are null.
  - Leading-dash values are refused for every field type (`template.html:884`).
  - Defects in these forms are listed in M-1 to M-3 and m-3/m-4.
- **The grep task:** the template (`commands.json:3284-3306`) emits `-r`, `-n` and `-i` as checkbox-gated option literals before the quoted pattern and path.
  - The golden fixture gives `grep -r -n -i 'laundry' '/etc'` on all four releases.
  - The evidence (`TC-COPY-001`, `alpha6-rc-grep.png`) and the artifact's data agree. **Verified exact.**
- **Counts and metadata:** I counted 200 entries: 58 generators and 142 static.
  - Of the 58 generators, 22 are green, 33 yellow and 3 red; 7 entries are red overall.
  - Of the 348 curated flag rows, 336 have explanations; the flag dictionaries contain 0 explanations.
  - There are 18 receipts on 9 entries (3 static + 6 generators) and 419 test methods.
  - These match the generated release facts, `TEST_PLAN` and `USER_GUIDE` Known Limitations. The stale exceptions are listed in m-1.

**Commands run:**
- `git rev-parse` / `status` / `log` / `diff --stat` / `diff --name-status -M`.
- `git show --stat` on all 7 alpha.6 commits.
- `git diff --stat 271fc9f HEAD -- <build inputs>`: empty.
- `PYTHONDONTWRITEBYTECODE=1 python3 qa.py`: **PASS**, Q1–Q26 plus the JavaScript syntax check.
  - 128,449 hostile checks and 19,732 pipeline checks.
  - 232 single-stage pipeline checks and 68 redirect-target checks.
  - 869 command invocations against 420 grammar rows.
  - 18 receipts.
- `shasum -a 256` on `dist/*`:
  - Artifact `e25e88a7…`, sidecar `e896ed43…`, provenance `74f00e8b…`.
  - These match the sidecar, provenance manifest, build-quality (BQP) summary, release report and RC QA JSON.
- `shasum -c stig-src/SHA256SUMS`: all OK.
- Archive checks:
  - Release hashes for alpha.1–alpha.5 match their sidecars.
  - The alpha.5 HTML and sidecar are identical to the `v1.0.0-alpha.5` tag.
  - The archived alpha.5 provenance equals `main`'s stamped copy, which names the tag commit `e299102`.
- `git diff --check origin/main...HEAD`: exits 2 (m-2).
- `git rev-list --count --no-merges HEAD`: 201.

**Not independently verified:**
- the unit-suite run (I statically counted 419 test methods);
- Gitleaks;
- the reproducible-build claim;
- the `generate_release_facts --check` command (I recomputed the facts by hand instead);
- the browser audit (I reviewed its script and results only).

## 4. Release constraints (not defects)

- **Signing and provenance:**
  - The release is unsigned.
  - The provenance manifest carries `TAG_COMMIT_PLACEHOLDER` until the reviewed merge is tagged, rebuilt, retested and stamped.
- **Host verification is partial:**
  - Receipts: RHEL 7 / 8 / 9 / 10 = 0 / 9 / 0 / 9.
  - All 15 new generators are `verified:false`.
  - RHEL 7 flags come from a UBI7 container.
- **Reference material:** no flag-dictionary row carries an explanation, and about 98.7% of mined reference records are unrated.
- **Browser and host coverage:** browser evidence is headless Chrome over localhost HTTP. The `file://` result is a supplemental manual entry. There was no assistive-technology, cross-browser or real-host execution testing.

## 5. Verdict: **HOLD**

There are four Major findings (M-1 to M-4) and no Blockers or Criticals. Artifact integrity, provenance handling, archive preservation, the QA gate, the pipeline crash fix and the exact grep output are all sound.

To reach PASS:
1. Fix M-1 to M-4 and add tests for each.
2. Correct the m-1 and m-2 documentation and evidence claims.
3. Rebuild, rerun the full gates and browser audit, re-scan with Gitleaks at the new HEAD, and repeat the exact-head review.
