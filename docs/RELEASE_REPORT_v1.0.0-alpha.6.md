---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Release Report -- v1.0.0-alpha.6

Verification totals: 470 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser assertions in each delivery mode.

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It closes the complete
functional audit and addresses the findings recorded by ten independent
Claude Opus release reviews, including real-input, risk-label, validation,
safety-reason, focus, contrast, and recovery findings. The final exact-head
review remains a separate gate.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.6` / 2026-10-01 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,791 bytes |
| Artifact SHA-256 | `198ae5904b2c7d45112b0cc950d4108cd002d2288e940e819fcd107585c4dacb` |
| Content fingerprint | `871abbeab5aa6256de70ee84d7d215c07738f489cfbd1f2af166be3d132e113a` |
| Provenance | `TAG_COMMIT_PLACEHOLDER` until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 470 unit tests; 168,697 hostile checks; 898 browser assertions in each of standalone and HTTP modes |
| Implementation source | `05b96e5c74c7de5b3795df5e1ee9fa87b28583b8` |

The release adds or changes:

- Task-centered Home, common outcomes, working modes, learning paths, favorites,
  recent work, and an explicit reviewed-catalog/reference-library boundary.
- Guided Configure, Review, and Verify workflows with a prominent exact command,
  trust signals, field teaching, value-bound runbooks, release comparison, and
  responsive command-first mobile reading order.
- Fifty-eight guided generators, including editable grep, signaling, transfer,
  remote-shell, synchronization, Git recovery, account, environment, stream,
  and storage workflows.
- Purpose-specific remote, URL, Git repository, Git path, shell-variable, PID, and write-target
  validation with exact golden-command and hostile-input coverage.
- A stage-oriented pipeline inspector whose composed result has an independent
  verification state and evidence context, plus 27,652 hostile pipeline checks,
  741 token-position oracle comparisons, and 232 one-stage invariants.
- Search, keyboard, focus, dialog, live-announcement, pressed-state, landmark,
  contrast, mobile, evidence, and reference-library improvements from the UX
  and independent review packages.
- Key-down/key-up coverage for every guided text field, including the pipeline
  redirect and xargs controls, plus real first-click coverage for Copy,
  acknowledgement, and Add to pipeline after a field edit.
- Red acknowledgements tied to current command bytes; expanded write-target
  classification and preserved composition reasons; atomic owner-validated SCP
  and rsync recovery state that refuses unsafe shared parents.
- Root-owned, mode-0700 NetworkManager rollback state with atomic creation,
  strict Recover/Finalize validation, and saved-connection reactivation.
- Step-by-step runbooks that expose Copy only for authored runnable commands,
  keep Recover separate, gate red evidence copying, and retain focus after
  deterministic keyboard clipboard activation.

The final candidate passed 898 of 898 rendered-browser assertions in both its
standalone `file://` delivery mode and a local HTTP delivery, with no exceptions
or console errors. Two consecutive builds produced the same 8,944,791-byte
artifact, SHA-256 sidecar, and provenance manifest byte for byte. The first
through tenth independent Opus review records are preserved in
`docs/design/`, including the eighth-review PASS, the ninth-review HOLD, and
the tenth-review HOLD whose transaction, signal, trust-check, native-keyboard,
and evidence findings this candidate closes. Exact-head independent review runs
only after this evidence is committed.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
