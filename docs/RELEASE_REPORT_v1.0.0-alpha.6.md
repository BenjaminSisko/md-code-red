---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Release Report -- v1.0.0-alpha.6

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It closes the complete
functional audit and addresses the findings recorded by four independent
Claude Opus release reviews, including real-input, risk-label, validation,
safety-reason, focus, contrast, and recovery findings. The final exact-head
review remains a separate gate.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.6` / 2026-10-01 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,922,170 bytes |
| Artifact SHA-256 | `fa9e08f011aee4fe197cae0af55ca6018bdf6f05b219a17655b2c68fc4f54851` |
| Content fingerprint | `ee66dd869084216485f70d1169bcf40c760956fead632589992d5fe8c96103a0` |
| Provenance | `TAG_COMMIT_PLACEHOLDER` until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 431 unit tests; 165,361 hostile checks; 893 browser assertions in each of standalone and HTTP modes |
| Implementation source | Pending exact review-fix commit |

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
  verification state and evidence context, plus 26,992 hostile pipeline checks,
  717 token-position oracle comparisons, and 232 one-stage invariants.
- Search, keyboard, focus, dialog, live-announcement, pressed-state, landmark,
  contrast, mobile, evidence, and reference-library improvements from the UX
  and independent review packages.
- Key-down/key-up coverage for every guided text field, including the pipeline
  redirect and xargs controls, plus real first-click coverage for Copy,
  acknowledgement, and Add to pipeline after a field edit.
- Red acknowledgements tied to current command bytes; expanded write-target
  classification and preserved composition reasons; safer transfer recovery.

The final candidate passed 893 of 893 rendered-browser assertions in both its
standalone `file://` delivery mode and a local HTTP delivery, with no exceptions
or console errors. The first through fourth independent Opus reviews and
their HOLD findings are preserved in `docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD.md` and
`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD_2.md`, and
`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD_3.md`, and
`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD_4.md`. Exact-head independent
review runs only after this evidence is committed.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
