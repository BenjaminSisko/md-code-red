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

**Later disposition:** this table records the classifications used during the capture run; it
is not a statement of the current catalogue. `gen-dnf-package` and `gen-yum-package` were
subsequently raised to yellow. A follow-up review of the pinned `chronyd(8)` source corrected
the third interpretation: `-Q` reports the measured offset and does not step the clock, so
`gen-chronyd-one-shot-check` remains green. The current ratings and their regression gate live
in `content/commands.json` and `tests/test_blast_state_change_labels.py`.

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

## Canonical path and the per-version capture -> receipt flow

**Canonical location (Eli Cross ruling, closing the CR-T-34 run's three-way path
mismatch — WADE_BLOCKED, below, was that report; it is resolved):**
`tests/captures/<rhel_version>/<entry_id>.json`, one JSON file per entry per RHEL
version, in THIS directory. `content-src/captures/` (an early extractor-docstring
guess) and `07_QA_Test/MD_CODE_RED/captures/` (the protocol document's original,
superseded proposal) are not used; `test-plan-skeleton-v1.md`'s own Appendix is a
pointer to this path, not a second storage location.

`extract/import_captures.py` (added at `9241f44`, after this README's own first
commit `ed1ccbe`) reads every file here, validates it against the content
validation protocol's §7 field set (`extract/import_captures.py`'s
`REQUIRED_FIELDS`, which also requires `command_hash_at_capture` and
`verify_result` — see `docs/WORKFLOW.md` §2a for why those two are mandatory in
code before the written protocol document's own §7 table lists them explicitly),
and folds the STIG-mapped ones into `content/expected_output.json` — a
**generated** file (ADR-001 §6.3: never hand-edited, only regenerated by
`python3 extract/import_captures.py`). A capture for an entry/version with no
`stig[]` row on this content (most `gen-*` generator entries) is still fully
validated but has nothing to join onto in that index; it is counted in
`_meta.files_validated` and read directly by `qa.py`'s Q16 gate off its own file,
by path, via the entry's `verified[version].capture` field.

**The flow, end to end, per entry per RHEL version (CEO ruling closing Riley
Park's first capture review, capture-review-run1-2026-09-18.md RILEY-F1:
`verified` is per RHEL version, not per whole entry — a single flag could never
be set for a batch like this one without overclaiming a version nobody
captured):**

1. **SME captures.** The RHEL SME (Caleb Stone, or a named delegate) runs the
   entry's command on a real host of the stated version per protocol §8/§9,
   writes the capture record here, and sets nothing in `content/commands.json`
   — a capture record on its own asserts nothing about `verified`.
2. **QA reviews.** Riley Park's spot-check (protocol §11) either independently
   re-runs or re-derives from the capture's own evidence. For each
   (entry, version) pair she clears, she writes a receipt into
   `content/commands.json`'s `verified[version]`:
   `{"by": "Riley Park", "on": "<date>", "host": "<capture's own host>",
   "capture": "tests/captures/<version>/<entry_id>.json"}`.
3. **`qa.py`'s Q16 gate enforces the pairing on every build:** the receipt's
   `capture` path must resolve to a real file for that EXACT (entry, version)
   pair, its `command_hash_at_capture` must match `sha256(command_as_run)`
   (not hand-edited), its `command_as_run` must still match the command this
   build actually assembles for that version today (same_as chains resolved
   the same way `build.py` resolves them — content edited since capture drifts
   this red), and the receipt's `by` must not equal the capture's
   `captured_by` — the SME who ran it is never the same name as the QA
   reviewer who verified it.
4. A version whose `rhel_versions` row is `unavailable` or a `same_as` pointer
   can never carry a receipt of its own (`extract/schema.py`'s
   `verified_errors()`) — it was never independently run on that version, and
   a `same_as` TARGET's receipt never propagates onto the version pointing at
   it. The UI shows "not host-verified" for that version rather than silently
   reusing another version's evidence.

Riley Park's first review (capture-review-run1-2026-09-18.md §4) cleared 9
entries x 2 RHEL versions (8 and 10) from Caleb's CR-T-34 batch above — 18
entry/version pairs, 18 receipts, now written into `content/commands.json`.

### WADE_BLOCKED (CR-T-34 run) — RESOLVED at `9241f44`

The original run that produced the capture files in this directory could not
fold them into `content/expected_output.json`: `extract/import_captures.py` did
not exist yet, and three different documents disagreed on where capture files
should live and which field names a capture record carries. Both are resolved:
the extractor was added at `9241f44`, and Eli Cross's ruling settled the path
(above) and the field-name authority (the content validation protocol's §7
names — `extract/import_captures.py`'s docstring says so explicitly). See
`capture-review-run1-2026-09-18.md` for the review that exercised the resolved
pipeline end to end.
