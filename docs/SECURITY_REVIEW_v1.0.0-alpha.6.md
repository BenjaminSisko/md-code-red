---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Security Review -- v1.0.0-alpha.6

Verification totals: 480 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser records in each delivery mode (896 pass/fail assertions and 2 performance observations).

The candidate preserves the offline single-file architecture, deny-network CSP,
closed generator grammars, output escaping, dangerous-pattern detection, and
explicit acknowledgement for destructive operations. Q2, Q17-Q19, Q21-Q26,
the full unit suite, the hostile-input harness, and the rendered-browser runtime
audit pass against the final artifact.

| Traceability fact | Candidate value |
|---|---|
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,791 bytes |
| Artifact SHA-256 | `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Content fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Implementation source | `5b868f10eec73bf6207113f56c41d42eb6802b1d` |

This candidate adds or strengthens the following security properties:

- SSH, SCP, rsync, URL, Git repository, Git path, shell-variable, and PID values use
  purpose-specific closed grammars. SSH emits the username through `-l`; rsync
  uses `-s` and accepts only a local source plus validated remote destination.
  Git clone accepts only HTTPS, SSH, SCP-like `user@host:path`, or an absolute
  local path; command-running `ext::` transports are refused.
- Curl, wget, SCP, and rsync destination fields are classified as write targets.
  Execution sinks are refused, protected system and sensitive user startup or
  authentication targets are red. SCP rates the validated path plus source
  basename and may remain yellow when only the remote host can reveal directory
  semantics; every rsync remote write is red. Other writes are
  at least yellow. RHEL usrmerge
  aliases (`/bin`, `/sbin`,
  `/lib`, and `/lib64`), `/var/run`, and `/etc/rc0.d` through `/etc/rc6.d`
  classify like their real targets.
- Instructional preflight, verify, and recovery commands bind the operator's
  actual inputs. Schema validation refuses hardcoded non-enum examples, and
  unresolved recovery state stays disabled.
- Composed pipelines have their own not-host-verified state and evidence context.
  They do not borrow one stage's receipt, verification label, or STIG identity;
  each displayed flag names its source stage and tool. Target-specific and
  destructive-child reasons survive composition and appear in the red banner.
- A destructive acknowledgement is bound to the current command. Any field,
  pipeline, operator, or release change clears it and disables Copy again.
- SCP and rsync use single-stdin remote transaction scripts whose app-bound
  strings execute through a fake SSH transport that reproduces OpenSSH's joined
  remote-command semantics. Field validation refuses remote dot segments before
  those scripts run. Preflight refuses symlink targets, unsafe writable parents,
  symlinked transaction parents, foreign-owned or stale transaction state, and
  non-mode-`0700` transaction directories. It atomically creates the final
  protected directory, writes a complete backup or an `absent` record, and
  writes the owner-validated state file last. A preserved backup owner is safe
  because access is controlled by the trusted mode-`0700` parent. Rsync
  checks capacity for two copies plus a margin. Recovery restores through an
  `after` path, uses GNU `mv -T`, and makes a bounded retry after removing a
  raced symlink so a directory backup replaces the link without following it.
  A persistent attacker that replants the link after every removal reaches the
  bounded failure path: execution exits exactly 1 after six removals, retains
  `state`, `before`, and `after`, leaves the link in place, and does not touch a
  sentinel behind it. The tests require the outside directory to contain only
  that sentinel, preventing writes through the link from going unnoticed.
  Additional SCP and rsync cases cover a link that cannot be removed, a planted
  non-link directory, and an attacker that stops after three replants. They
  require exact status 1 and retained rollback state; mutation controls prove
  the link check, removal failure, retry exhaustion, outer failure, and
  transaction-retention guards all fail closed. Recover and Finalize
  independently refuse symlinked
  destinations and unsafe or symlinked transaction parents.
  A created target is removed only when recorded state proves it was absent;
  explicit finalization clears the transaction. SCP remains
  local-to-remote, and rsync recovery does not prescribe `--delete`.
- NetworkManager rollback state is atomically created under root-owned mode-0700
  `/var/lib/md-code-red`. Preflight, Recover, and Finalize reject symlinked,
  non-root-owned, incorrectly permissioned, or incomplete state. Recovery reloads
  and reactivates the saved connection from a required console or out-of-band
  session. The pre-install symlink test begins with a mode-`0755` link target and
  proves refusal occurs before `install` can change it; positive Finalize
  coverage proves trusted state removal.
- Runbook prose is never treated as a runnable clipboard payload. Preflight Copy
  includes only authored command fields; Verify and Recover Copy are enabled
  only for closed transaction scripts carrying an MDCR marker. Red-rated command,
  runbook, generated-file, and evidence-copy controls all share the exact-command
  acknowledgement gate. The rendered audit compares the rsync Recover clipboard
  bytes with the external instruction-binding probe and rejects any payload
  containing a Preflight or Finalize marker.
- Generator receipts include the exact reviewed `command_as_run`. Changing any
  field immediately changes both the Inspector and status bar to Not
  host-verified; the command cannot keep a receipt merely because its entry and
  RHEL release match.
- The hostile-input harness executes 168,697 checks over all 41 field types,
  every generator field, multi-stage pipelines, redirect targets, file
  generators, quoting domains, and positive controls; zero failed. This includes
  27,652 pipeline checks, 741 pipeline-oracle comparisons, and 232 one-stage
  invariants.
- The final standalone and HTTP rendered-browser audits each produced zero
  exceptions and zero console errors across 896 pass/fail assertions and two
  informational performance observations. Their JSON metadata binds each run to
  the artifact byte count, SHA-256, and content fingerprint, and the auditor
  compares the main-document response bytes returned by CDP with that artifact
  before it records results.
  The coverage includes 109 guided text controls entered with real CDP
  key-down/key-up pairs, first-click
  pointer coverage after edits, stale-toast invalidation, pipeline redirect and
  xargs input, composed-command trust, acknowledgement invalidation, incomplete
  pipelines, receipt binding, status refresh, placeholder contrast, focus, visible
  searched STIG rules, runbook binding,
  and Home-route regressions.
- The standalone artifact loaded zero network resources. Q2 found no external
  script, stylesheet, image, media, font, fetch, XHR, WebSocket, beacon,
  dynamic import, or CDN path.
- Forgejo CI builds the deterministic HTML before discovering unit tests, so the
  artifact-backed tests execute on a clean checkout. It leaves the committed
  candidate provenance untouched because that manifest intentionally records
  the release workstation toolchain; regenerating it with runner-specific
  Python or Node versions would dirty the protected evidence before tests run.

The candidate remains unsigned because no authorized publisher identity is
provisioned. SHA-256 detects changed bytes but does not authenticate a publisher.
RHEL host-verification coverage remains partial, mined reference records remain
separate and mostly unrated, and a structurally safe command or pipeline can
still be operationally inappropriate. These boundaries remain visible in the
interface and documentation.

Independent exact-head review remains the last candidate gate. Any subsequent
source, artifact, or evidence change invalidates that review.
