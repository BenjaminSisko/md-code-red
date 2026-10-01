---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Security Review -- v1.0.0-alpha.6

The candidate preserves the offline single-file architecture, deny-network CSP,
closed generator grammars, output escaping, dangerous-pattern detection, and
explicit acknowledgement for destructive operations. Q2, Q17-Q19, Q21-Q26,
the full unit suite, the hostile-input harness, and the rendered-browser runtime
audit pass against the final artifact.

This candidate adds or strengthens the following security properties:

- SSH, SCP, rsync, URL, Git path, shell-variable, and PID values use
  purpose-specific closed grammars. SSH emits the username through `-l`; rsync
  uses `-s` and accepts only a local source plus validated remote destination.
- Curl, wget, SCP, and rsync destination fields are classified as write targets.
  Execution sinks are refused, protected system and sensitive user startup or
  authentication targets are red, remote directory destinations are red, and
  other writes are at least yellow. RHEL usrmerge aliases (`/bin`, `/sbin`,
  `/lib`, and `/lib64`) classify like their `/usr` targets.
- Instructional preflight, verify, and recovery commands bind the operator's
  actual inputs. Schema validation refuses hardcoded non-enum examples, and
  unresolved recovery state stays disabled.
- Composed pipelines have their own not-host-verified state and evidence context.
  They do not borrow one stage's receipt, verification label, or STIG identity;
  each displayed flag names its source stage and tool. Target-specific and
  destructive-child reasons survive composition and appear in the red banner.
- A destructive acknowledgement is bound to the current command. Any field,
  pipeline, operator, or release change clears it and disables Copy again.
- Download runbooks preserve an existing destination before transfer and only
  recommend removal when the destination was created by that run. SCP is
  explicitly local-to-remote, and rsync recovery does not prescribe `--delete`.
- Generator receipts include the exact reviewed `command_as_run`. Changing any
  field immediately changes both the Inspector and status bar to Not
  host-verified; the command cannot keep a receipt merely because its entry and
  RHEL release match.
- The hostile-input harness executes 145,345 checks over all 34 field types,
  every generator field, multi-stage pipelines, redirect targets, file
  generators, quoting domains, and positive controls; zero failed. This includes
  23,032 pipeline checks, 717 pipeline-oracle comparisons, and 232 one-stage
  invariants.
- The final standalone and HTTP rendered-browser audits each produced zero
  exceptions and zero console errors across 889 assertions, including 109
  guided text controls entered character by character, pipeline redirect and
  xargs input, composed-command trust, acknowledgement invalidation, incomplete
  pipelines, receipt binding, status refresh, contrast, focus, runbook binding,
  and Home-route regressions.
- The standalone artifact loaded zero network resources. Q2 found no external
  script, stylesheet, image, media, font, fetch, XHR, WebSocket, beacon,
  dynamic import, or CDN path.

The candidate remains unsigned because no authorized publisher identity is
provisioned. SHA-256 detects changed bytes but does not authenticate a publisher.
RHEL host-verification coverage remains partial, mined reference records remain
separate and mostly unrated, and a structurally safe command or pipeline can
still be operationally inappropriate. These boundaries remain visible in the
interface and documentation.

Independent exact-head review remains the last candidate gate. Any subsequent
source, artifact, or evidence change invalidates that review.
