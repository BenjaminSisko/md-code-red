# CR-T-34 — Content validation captures, run 1 (GREEN-blast, standing lab hosts)

Run by Caleb Stone, 2026-09-17, under Founder delegation (DECISION_LOG 2026-09-18 item 8)
for GREEN-blast entries only, per the content validation protocol
(`/Users/benny/Documents/SALM LLC/07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md`, Part B
§7-§11). Yellow/red entries are deferred to a throwaway VM per §8-9 of that protocol and are
**not** run here. No `sudo` was used on either host tonight, in line with
`feedback_stig_sudo_no_heredoc.md` and this run's own safety rules. No entry was set
`verified: true` — that flip is Riley's step, after her spot-check (protocol §11).

Hosts: `defiant` (RHEL 8.10, STIG'd) and `saratoga` (RHEL 10.2, STIG'd), both reached over
`ssh` as `adm-linux`. Login banners printed on both connections and were ignored per
instructions.

## Classification of all 27 content/commands.json entries

| Class | Count | Meaning |
|---|---|---|
| GREEN — captured tonight | 9 | Read-only, no privilege needed, ran clean on both hosts |
| GREEN-but-privileged — deferred | 1 | Read-only in intent, but needs root to read the target file |
| GREEN-label-but-state-changing — deferred, flagged | 3 | `blast: "green"` in content, but the command itself changes host state; not run regardless of label |
| YELLOW — deferred to VM | 14 | Reversible state change; out of scope tonight per the CEO's authorization |
| RED | 0 | None of the 27 entries carry `blast: "red"` |

**9 + 1 + 3 + 14 = 27.**

### GREEN — captured on both defiant (RHEL 8) and saratoga (RHEL 10)

| entry_id | command run | notes |
|---|---|---|
| `firewalld-service-active` | `systemctl is-active firewalld` | STIG-sourced |
| `ctrl-alt-del-target-masked` | `systemctl status ctrl-alt-del.target` | STIG-sourced |
| `journald-service-active` | `systemctl is-active systemd-journald` | STIG-sourced; no RHEL 8 STIG mapping exists (see below) |
| `gen-journalctl-unit-logs` | `journalctl --no-pager --unit='sshd.service' --priority='err' --since='today' --boot` | golden-table command, real unit `sshd.service` |
| `gen-systemctl-query` | `systemctl 'status' 'sshd.service'` | golden-table command |
| `gen-chage-list` | `chage -l 'adm-linux'` | golden table used `svcacct`, which does not exist on either host and would need root to read for a user other than yourself; substituted the logged-in account `adm-linux` (substitution recorded in each capture file) |
| `gen-ausearch-by-key` | `ausearch -k 'identity' -ts 'today'` | golden-table command; partial-privilege note below |
| `gen-rsyslogd-test-config` | `rsyslogd -N1 -f '/etc/rsyslog.conf'` | golden-table command |
| `gen-podman-ps` | `podman ps -a` | golden-table command |

18 capture files total (9 entries x 2 RHEL versions), under `tests/captures/8/` and
`tests/captures/10/`.

**`gen-ausearch-by-key` partial-privilege note:** `ausearch` printed `Error opening config
file (Permission denied)` for `/etc/audit/auditd.conf` on both hosts, then fell back to its
built-in defaults and successfully read `/var/log/audit/audit.log` directly (no privilege
needed for the log itself), returning `<no matches>` (exit 1 — documented as the normal
no-match outcome for `ausearch`, not a failure). Because the command's core function (search
the audit log for a key) completed and returned a defined result without `sudo`, this was
captured as GREEN rather than deferred as GREEN-but-privileged; the config-file permission
note is recorded in the capture file for transparency.

### GREEN-but-privileged — deferred

| entry_id | command attempted | result |
|---|---|---|
| `gen-sshd-test-config` | `sshd -T -f '/etc/ssh/sshd_config'` | `/etc/ssh/sshd_config: Permission denied` (exit 1) on **both** hosts — `sshd_config` is not world-readable on either STIG'd host. Recorded as "requires privilege — deferred" per the safety rule; no capture file written (no undo/verify to record against a failed read, and re-running with `sudo` is prohibited tonight). |

### GREEN-label-but-state-changing — deferred, flagged as a content-authoring issue

These three entries carry `"blast": "green"` in `content/commands.json` /
`tests/fixtures/golden-commands.json`, but their actual command semantics change host state,
which conflicts with "GREEN (read-only, runnable tonight)." Per the safety rule ("if a
command's semantics are unclear, do not run it") these were **not** run, and are flagged here
for the content owner (Milo) to review the blast rating, independent of the WADE_BLOCKED
finding below:

| entry_id | why it is not read-only |
|---|---|
| `gen-dnf-package` | `action` field is `install`/`remove` — installs or removes a package, i.e. changes package state. Golden value `action=install` would run `dnf 'install' 'firewalld'`. |
| `gen-yum-package` | Same issue, `yum` on RHEL 7/8+. |
| `gen-chronyd-one-shot-check` | `chronyd -Q '<directive>'` does not just test config — per `chronyd(8)`, `-Q` retrieves the offset from the given NTP source(s), **applies it to step the system clock**, and exits. That steps the real system clock on a STIG'd host, which is a state change (affects logs, cron, any time-sensitive service) even though it touches no file. Not run. |

### YELLOW — deferred to a throwaway VM (not run tonight)

`gen-fw-set-default-zone`, `gen-fw-open-port`, `gen-fw-allow-service`, `gen-nmcli-static-ipv4`,
`gen-lvcreate-new-lv`, `gen-lvextend-grow`, `gen-useradd-create`, `gen-usermod-add-group`,
`gen-systemctl-manage`, `gen-setsebool-set`, `gen-semanage-port-add`, `gen-chage-set-aging`,
`gen-auditctl-watch`, `gen-podman-stop` — 14 entries, all `blast: "yellow"` and all genuinely
state-changing (add/remove/start/stop/modify). None were run against `defiant` or `saratoga`.

## STIG check/fix compliance status (protocol §10)

All five STIG-mapped check rows exercised tonight came back **compliant** on the real host —
no "expected, not observed" label is needed for any of them:

| entry_id | STIG ID | host | compliant? | observed |
|---|---|---|---|---|
| `firewalld-service-active` | RHEL-08-040101 | defiant (RHEL 8) | yes | `active` |
| `firewalld-service-active` | RHEL-10-200531 | saratoga (RHEL 10) | yes | `active` |
| `ctrl-alt-del-target-masked` | RHEL-08-040170 | defiant (RHEL 8) | yes | `Loaded: masked`, `Active: inactive (dead)` |
| `ctrl-alt-del-target-masked` | RHEL-10-700960 | saratoga (RHEL 10) | yes | `Loaded: masked`, `Active: inactive (dead)` |
| `journald-service-active` | RHEL-10-500000 | saratoga (RHEL 10) | yes | `active` |

`journald-service-active` carries no RHEL 8 STIG mapping (content/commands.json's own note:
"No rule in the pinned RHEL 8 V2R8 benchmark maps to the journal service"), so the RHEL 8
capture of that entry is a content-validation read only, not a compliance claim.

## WADE_BLOCKED — content/expected_output.json cannot be updated as instructed

`content/expected_output.json` is a **generated** file, not a hand-authored one. Its own
`_meta` says: `"generator": "extract/import_captures.py"`, and
`extract/make_pending_skeletons.py` (which emits the current empty skeleton) states in its own
docstring:

> `content/expected_output.json` the capture index — EMPTY. ADR-001 §6.5: expected output is
> captured, never typed. `extract/import_captures.py` (CR-T-34) folds capture files from
> `content-src/captures/` into this index. None have been captured.
> ...
> ADR-001 §6.3: generated files are never hand-edited. Fix the extractor, re-run.

`extract/import_captures.py` — the extractor this file names as its own generator, and the
one CR-T-34 (this ticket) is supposed to deliver — does not exist anywhere in the repo. The
only two ways to get real capture data into `content/expected_output.json` are: (a) hand-edit
the generated file directly, which the codebase's own Cardinal Rule (ADR-001 §6.3, stated in
the file that owns this exact index) forbids; or (b) write `extract/import_captures.py`, which
is on this run's explicit do-not-edit list (`extract/`). Both paths are closed to me tonight.

A second, independent mismatch compounds this: three different documents name three different
locations for capture files feeding this index —
`content-src/captures/<rhel>/...` (named by `extract/make_pending_skeletons.py`'s own
docstring, the actual generator target),
`07_QA_Test/MD_CODE_RED/captures/<rhel>/<entry_id>.json` (named by the joint protocol,
test-plan-skeleton-v1.md §7 and its Appendix file layout), and
`tests/captures/<rhel_version>/<entry_id>.json` (named by this run's own task instructions,
which is where the files in this directory actually live). None of the three agree, and
resolving that is a design decision, not something I should pick silently by hand-editing the
generated index around whichever path I chose tonight.

A third, smaller mismatch: even setting the generator issue aside, the capture record field
names `qa.py`'s `gate_q16()` requires inside `content/expected_output.json["captures"][key]`
(`host`, `os_release`, `kernel`, `patch_level`, `command_run`, `exit_code`, `stdout`,
`captured_on`, `captured_by`) do not match the field names the protocol document's own §7
schema specifies for a capture record (`host`, `redhat_release`, `kernel`, `pkg_versions`,
`command_as_run`, `exit_code`, `stdout`, `stderr`, `captured_on`, `captured_by`,
`blast_confirmed`, `undo_executed`). This run's capture files (above) follow the protocol's §7
field names, which is the schema this run was told to read first; reconciling that against
`qa.py` is exactly the kind of change this run is not authorized to make unilaterally (`qa.py`
is also on the do-not-edit list).

**Per instruction, this is not bent around — it is reported.** `content/expected_output.json`
was left untouched (still the empty skeleton at HEAD). Gate results below are therefore the
baseline gates against unmodified content, not "Q16 passing with real captures" — that
condition cannot be met without either restoring `extract/import_captures.py` to the
task scope or an explicit ruling on where capture files live and which field-name schema is
authoritative.

## Gate run (baseline, expected_output.json unmodified — see WADE_BLOCKED above)

See the end of this session's report for the actual `rm -rf dist && python3 build.py && python3
qa.py && python3 -m unittest discover -s tests` output.
