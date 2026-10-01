---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Release Report -- v1.0.0-alpha.6

Verification totals: 465 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser assertions in each delivery mode.

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It closes the complete
functional audit and addresses the findings recorded by nine independent
Claude Opus release reviews, including real-input, risk-label, validation,
safety-reason, focus, contrast, and recovery findings. The final exact-head
review remains a separate gate.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.6` / 2026-10-01 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,944,842 bytes |
| Artifact SHA-256 | `bd419fffba2e2c1c7a2218c0a550bf6eda368619315b7f54d6a91207887a06aa` |
| Content fingerprint | `98974cb6efa8bf67c42e4869c03c3d9e5ae35b5d6631500cdeda1a35b418c358` |
| Provenance | `TAG_COMMIT_PLACEHOLDER` until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 465 unit tests; 168,697 hostile checks; 898 browser assertions in each of standalone and HTTP modes |
| Implementation source | `4d61c901001f631690954d4bdb8f345d9c33742a` |

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
or console errors. Two consecutive builds produced the same 8,944,842-byte
artifact, SHA-256 sidecar, and provenance manifest byte for byte. The first
through ninth independent Opus review records are preserved in `docs/design/`,
including the eighth-review PASS and the ninth-review HOLD whose blockers this
candidate closes. Exact-head independent review runs only after this evidence is
committed.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
