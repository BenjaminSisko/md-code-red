I've finished the review and the verdict is **HOLD**. I re-checked at the end that HEAD and every artifact hash are unchanged.

# MD CODE RED v1.0.0-alpha.6: fifth exact-head release review

## 1. Commit and tree state

| Item | Value |
|---|---|
| Reviewed HEAD | `00ecdbfc13af034a87b997712c760f68b3c9fe55` on `codex/alpha6-responsive-ux`, 10 commits ahead of origin |
| Implementation commit | `be95fe8eb990…`. Between `be95fe8` and HEAD, `00ecdbf` changes only the provenance JSON and evidence docs; the HTML, template and content are byte-identical. |
| Tree before and after | `git status` clean both times, no stashes, HEAD unchanged. Ignored files were not listed because the `--ignored` form was blocked. |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`: 8,922,170 bytes, SHA-256 `fa9e08f0…4f54851`. This matches the sidecar, provenance and RELEASE_REPORT. |
| Sidecar / provenance SHA-256 | `12ea46ae…` / `5acb99b9…`; provenance `git_commit` is `TAG_COMMIT_PLACEHOLDER`, as expected |
| Content fingerprint | `ee66dd86…6103a0`, recomputed from the islands; matches the file header, the JS constant and provenance |

**Session limits.** The permission policy allowed only read-only git/grep/ls and `node -e`. Python, `qa.py`, `build.py`, clones, shell execution and a browser were all blocked. Everything below was checked statically or in Node, using the shipped artifact's own code and data.

## 2. Verdict: **HOLD**

There are no Blocker or Critical findings. **Two Major and five Minor findings remain**:
- **F-1 (Major):** the new scp/rsync backup and restore commands can never run.
- **F-2 (Major):** the release evidence contradicts itself and cites test IDs that don't exist.

## 3. The ten review areas

1. **Closed (by code analysis and committed evidence).**
   - A deferred `change` now returns early when the value is already stored (`template.html:6150-6158`), so the first click after typing reaches Copy, acknowledgement and Add to pipeline.
   - Edits clear the acknowledgement and the "Copied" message (`:6156-6157`, `bumpPipeline` `:4678`); pipeline fields are also idempotent (`:4859-4866`).
   - Both browser-audit runs record real CDP input passing `TC-COPY-POINTER-001` (clipboard equals the edited command, stale message cleared first), `TC-BLAST-ACK-001`, `TC-PIPE-001` and `TC-A11Y-FOCUS-004`.
   - I could not repeat these with my own browser session.
2. **Partly closed.** All twelve entries are yellow and green now reads "Low impact" (`:5171`, `:5346`). Residual: F-3.
3. **Closed.** Through the artifact, 13 legitimate forms were accepted and 28 hostile forms refused on all four RHEL releases.
   - Accepted: HTTPS with port or IP, SSH with or without user/port, `~user`, `user@host:path`, absolute paths.
   - Refused include: `ext::`, `fd::`, `file://`, `git://`, `http://`, unknown schemes, `host:path` without a user, leading `-`, `-oProxyCommand` hosts, `;`/`$()`/backticks, `%`, whitespace, credentials, `..`, and `[::1]`.
   - The directory field refuses `..`, `-x`, `.git`, spaces and `/`.
4. **Partly closed.**
   - Refused as intended: `/var/run/systemd/system/*` and `/etc/rc0.d`–`/etc/rc6.d`, for both redirects and scp.
   - The new startup files are red, and scp joins the destination with the source name (`/tmp/.bashrc` → `host:/var/www` is red).
   - Residuals: F-5, F-6, and the `/etc/rc.local` observation.
5. **Not closed.** See F-1.
6. **Closed for the targeted path.** `selectStigRule` turns the Inspector on (`:5909`), and `TC-PIPE-CONTROL-002` checks the panel is on screen at 1440×1000. Observations are in §5.
7. **Closed.** Placeholder text now measures 5.60–5.96:1 in light and 6.91–7.76:1 in dark, on every input background (previously 4.41:1).
8. **Partly closed.** Container names match Podman's own grammar and LVM names are close to lvm(8). Residual: F-4.
9. **Not closed.** See F-2.
   - Correct: 431 test methods (counted, not run), 165,361 / 26,992 / 717 / 232 harness checks and 40 field types (re-run), 893/893 in both modes, 37/18/3 guided split, release facts.
   - Inconsistent: the BQP summary, the HTML closure table, and the overclaims in F-1 and F-5.
10. **Closed.**
    - A single write reason is shown for `/root/.bashrc`.
    - `CATALOGUE-RED` names the stage, both directly and for an xargs child.
    - Messages clear on edits and selections; `change` and pipeline fields no longer re-render needlessly.
    - The completion announcement no longer depends on an existing pipeline.
    - One cosmetic leftover is listed in §5.

## 4. Findings

### F-1 (Major): scp/rsync preflight and Recover commands cannot execute

- **Where:**
  - Preflights: `content/instructional.json:1826` (scp) and `:1868` (rsync).
  - Recover: `content/commands.json:5784` (scp) and `:5846` (rsync).
  - Binding: `template.html:3281-3291`.
- **What the operator copies** (rendered by the shipped artifact):
  `ssh alice@server.example.test -- 'target=$1; [ -d "$target" ] && …; fi' sh '/tmp/config.yml' 'config.yml'`
- **Why it fails:**
  - ssh joins its arguments with spaces, and sshd runs the result as `$SHELL -c "<string>"` with no positional parameters.
  - So `$1` and `$2` are empty, and `… fi sh /tmp/config.yml config.yml` is a shell syntax error. Nothing executes: no backup, no absence marker, no restore.
  - All four commands fail this way on every RHEL release.
  - Basis: OpenSSH's documented behaviour and POSIX grammar; I wasn't permitted to execute it.
- **Further defects once the transport is fixed:**
  - An older `.mdcr-before-*` backup makes the preflight exit 1 silently, and Recover then restores that older copy.
  - An absence marker from an earlier run plus a skipped preflight makes Recover `rm -rf` a target that already existed.
  - A failed `cp -a` leaves a partial backup that Recover would restore.
  - A leftover `.mdcr-after-*` file blocks every later Recover.
  - The rsync preflight copies the whole destination tree, which can fill the filesystem.
- **Tests:** only string-presence checks (`tests/test_instructional_ux.py:136-144`). No browser test exists.
- **Docs claim it works:** SECURITY_REVIEW:38-42, USER_GUIDE:156-158, CHANGELOG:23-26, QA_REPORT:53.
- **Impact:** the claimed closure of the prior scp/rsync recovery finding (R4-7) is ineffective. Operators who continue past the error overwrite remote files with no backup, and the documented Recover also fails, including for red rsync targets.
- **Fix:**
  - Use a working remote form, such as `ssh <id> -- sh -s -- <path> <base> <<'MDCR' … MDCR`, or rsync's own `--backup --backup-dir`.
  - Scope backups and markers to a single operation, and refuse rather than silently skip.
  - Add tests that execute the exact ssh-joined string in a temp directory, covering present, absent and stale cases.

### F-2 (Major): Release evidence is internally inconsistent and cites nonexistent tests

- **Stale BQP summary.** `docs/BQP_SUMMARY_v1.0.0-alpha.6.md:13,17-21,26` is one of the four required release-evidence files, yet it certifies the previous artifact:
  - 8,913,823 bytes, `69ec4e6b…`, fingerprint `e377c108…`;
  - sidecar `4f9e6081…`, provenance `df95b0b4…`;
  - implementation commit `19274c4`.
- **Phantom test IDs.** The HTML closure table (`docs/qa/QA_REPORT_v1.0.0-alpha.6-rc.html:10`) cites `TC-RUNBOOK-REMOTE-001/002` and `TC-STIG-SELECT-001`.
  - None exists in the audit script, either results JSON, or any commit.
  - The STIG property is real but is tested as `TC-PIPE-CONTROL-002`; the transfer claim is untested and false.
- **No gate catches either.** No check ties the BQP identity fields or cited test IDs to the artifact.
- **Fix:**
  - Regenerate the BQP summary for the current artifact and re-run the two-build reproducibility cycle.
  - Correct the cited IDs, and remove the transfer claim or back it with a real test.
  - Add a gate checking document identity fields against the sidecar and provenance, and checking that every cited test ID exists.

### F-3 (Minor): `gen-git-clone` still says "read-only" on screen

- **Where:** `content/instructional.json:651,658`, rendered in "Why this field? → Consequence" (`template.html:5254`).
- **Impact:** a yellow, state-changing clone shows "This value limits what the read-only command inspects." This text is generated from the risk rating and wasn't regenerated when the rating changed.
- **Fix:** regenerate the text, and gate that the wording agrees with the rating.

### F-4 (Minor): New field types misdescribe valid inputs

- **Where:** `template.html:924`, `:928`, and the message at `:987-988`.
- **Impact:** both messages blame valid input instead of the tool's own restriction.
  - "System eth0", "Wired connection 1" and "cloud-init eth0" are rejected as "not a valid NetworkManager connection name", although NetworkManager creates exactly these names. They are what the field's own discovery command, `nmcli connection show`, lists.
  - "OpenSSH server daemon", the real description of `sshd.service`, is rejected as "not a valid systemd unit description". The fixture's benign value `Managed-application-service` shows the workaround.
- **Fix:** accept quoted spaces, or reword the labels honestly, for example "connection name or UUID, no spaces" with the UUID discovery command, and "single-token description".

### F-5 (Minor): rsync directory semantics are partial, and the docs overclaim

- **Where:** `template.html:1745-1768`; claims in USER_GUIDE:154 ("Rsync directory sources are red") and SECURITY_REVIEW:24 ("possible remote-directory destinations are red").
- **Impact:**
  - `rsync -a /srv/dotfiles/.config/systemd alice@h:/home/alice/.config` is yellow, yet it writes `~/.config/systemd/user/*`, a target class the tool itself rates red.
  - The same sync spelled with trailing slashes is red.
  - `scp /tmp/x.conf root@h:/var/www` is yellow, contradicting the SECURITY_REVIEW wording.
- **Fix:** classify the destination subtree conservatively, or narrow the docs to the trailing-slash rule.

### F-6 (Minor, needs host confirmation): `~/.bashrc.d/*` is not treated as a startup location

- **Where:** `isSensitiveUserTarget` (`template.html:2283-2298`).
- **Impact:** writes to `/home/alice/.bashrc.d/x.sh` (redirect or scp) are yellow. To my knowledge, the stock RHEL 9 and 10 `/etc/skel/.bashrc` sources `~/.bashrc.d/*`, which would contradict "shell startup files are red". I could not check a host.
- **Confirm:** `grep -n bashrc.d /etc/skel/.bashrc` on a RHEL 9 host.
- **Fix:** add the location, or narrow the claim.

### F-7 (Minor, pre-existing since alpha.5): nmcli recovery relies on a VPN-only command

- **Where:** `content/commands.json:683` (`gen-nmcli-static-ipv4` notes) tells operators to save the profile with `nmcli connection export`. The repo's own RHEL 8/9/10 captures say "Only VPN connections are supported."
- **Impact:** the pre-change backup step fails for the Ethernet profile this lockout-prone generator modifies.
- **Fix:** copy the profile's keyfile/ifcfg file and record `nmcli connection show <con>` instead.

## 5. Observations (non-blocking)

- `/etc/rc.local` is still only red, while its `/etc/rc.d/rc.local` target is refused.
- The standalone STIG text says the rule is "in the Inspector panel on the right" (`:5127`), which is wrong at 1024px and below. The 14 of 1,492 rules that link to a command still open with the Inspector off, despite USER_GUIDE:167-168.
- "Destructive command — tick the review box first." stays in the status bar after the box is ticked (`:6068`).
- Test strength:
  - The green-entry protection is twelve hard-coded IDs, not a general gate.
  - `test_responsive_controls` asserts source text rather than behaviour.
  - The contrast test samples only the palette input.
  - The STIG visibility test runs only at desktop width.
- The free-text `chronyd -Q` directive field was not analysed for file-writing directives.

## 6. Checks run

| Check | Outcome |
|---|---|
| `git rev-parse`, `status`, `stash list`, at start and end | Same HEAD, clean |
| `git show --stat`, `git diff 88b233b..HEAD`, `git diff --stat be95fe8 HEAD` | Changes reviewed; HTML unchanged since `be95fe8` |
| `git diff --check` from `88b233b` and from `main` | Clean |
| Node SHA-256 of artifact, sidecar, provenance, template, at start and end | Unchanged; match the sidecar and provenance |
| Template plus the artifact's islands and tokens, substituted forward | Byte-identical to the shipped artifact |
| Content fingerprint recomputed | Matches |
| Embedded data compared with `content/*.json` (sorted keys) | Identical apart from build-derived fields |
| Release facts recomputed; alpha.1–5 archives; `stig-src` SHA256SUMS | All match |
| `test_alpha6_review_closure.js` on template and artifact | 68/68 each |
| `hostile_harness.js` on artifact | 165,361 checks, 0 failed; 26,992 pipeline |
| Assembler probe matrices (Git, paths, scp/rsync, pipeline reasons, validators) | Results above |
| Runbook rendered from the artifact; contrast computed from CSS tokens | F-1 and area 7 |
| Evidence JSON/HTML cross-check | 893/893 both modes, no divergence; HTML lists all 893 IDs; three cited IDs exist nowhere |
| Network-API scan; island escaping | No network APIs or external references; islands escaped and valid JSON |

**Not performed** (blocked by the session's permission policy): the Python suite, `qa.py` Q1–Q26, the rebuild and reproducibility cycle, `generate_release_facts --check`, browser sessions, Gitleaks, running any shell command, RHEL hosts, and screen readers.

## 7. Acceptable residual limitations for a lab-only, unsigned alpha

- The release is unsigned; provenance stays at the placeholder until the tag exists, then must be rebuilt, retested and stamped.
- Host receipts cover RHEL 7/8/9/10 as 0/9/0/9, and RHEL 7 flags come from a UBI7 container.
- The mined reference tier is mostly unrated but kept separate and gated by acknowledgement.
- Sink lists are enumerated (for example `/etc/systemd/user` and udev rules are red, not refused), and classification is lexical only.
- Only Chrome was tested and screen-reader behaviour is unverified; CI pins actions by tag.

## 8. To reach PASS

1. Fix F-1 and add tests that actually execute the commands.
2. Correct the evidence package (F-2) and add identity and test-ID gates.
3. Fix F-3 to F-6 and correct the overclaiming docs; fix F-7 or disclose it.
4. Rebuild, rerun every gate in both delivery modes, and repeat the exact-head review.

---

*Not used in this review: several connectors (Figma, Google Drive, GitHub and others) need authorization in claude.ai connector settings or via `/mcp`, and a few others failed to connect.*
