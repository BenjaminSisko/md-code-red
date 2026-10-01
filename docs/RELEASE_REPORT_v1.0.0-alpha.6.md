---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Release Report -- v1.0.0-alpha.6

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It closes the complete
functional audit and addresses the findings recorded by three independent
Claude Opus release reviews, including the third review's real-input,
safety-reason, focus, contrast, and recovery findings. The final exact-head
review remains a separate gate.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.6` / 2026-10-01 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,913,823 bytes |
| Artifact SHA-256 | `69ec4e6bcce72fc1ad4c05f632702120b4d983527a93d6c917da372c6568d18c` |
| Content fingerprint | `e377c108f895bf4ca26b476e26f246e0d6b80a2156f1b5a1cea0039019224225` |
| Provenance | `TAG_COMMIT_PLACEHOLDER` until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 429 unit tests; 145,345 hostile checks; 889 browser assertions in each of standalone and HTTP modes |
| Implementation source | `19274c4f99a6a9b73ffd504d2bc2053957453a45` |

The release adds or changes:

- Task-centered Home, common outcomes, working modes, learning paths, favorites,
  recent work, and an explicit reviewed-catalog/reference-library boundary.
- Guided Configure, Review, and Verify workflows with a prominent exact command,
  trust signals, field teaching, value-bound runbooks, release comparison, and
  responsive command-first mobile reading order.
- Fifty-eight guided generators, including editable grep, signaling, transfer,
  remote-shell, synchronization, Git recovery, account, environment, stream,
  and storage workflows.
- Purpose-specific remote, URL, Git path, shell-variable, PID, and write-target
  validation with exact golden-command and hostile-input coverage.
- A stage-oriented pipeline inspector whose composed result has an independent
  verification state and evidence context, plus 23,032 hostile pipeline checks,
  717 token-position oracle comparisons, and 232 one-stage invariants.
- Search, keyboard, focus, dialog, live-announcement, pressed-state, landmark,
  contrast, mobile, evidence, and reference-library improvements from the UX
  and independent review packages.
- Character-by-character coverage for every guided text field, including the
  pipeline redirect and xargs controls that exposed the third-review focus bug.
- Red acknowledgements tied to current command bytes; expanded write-target
  classification and preserved composition reasons; safer transfer recovery.

The final candidate passed 889 of 889 rendered-browser assertions in both its
standalone `file://` delivery mode and a local HTTP delivery, with no exceptions
or console errors. The first, second, and third independent Opus reviews and
their HOLD findings are preserved in `docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD.md` and
`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD_2.md`, and
`docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD_3.md`. Exact-head independent
review runs only after this evidence is committed.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
