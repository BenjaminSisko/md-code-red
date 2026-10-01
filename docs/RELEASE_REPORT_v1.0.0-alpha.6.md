---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Release Report -- v1.0.0-alpha.6

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It closes the complete
functional audit and every major or minor finding from the first independent
Claude Opus release review.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.6` / 2026-10-01 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,902,185 bytes |
| Artifact SHA-256 | `d1949c9e16b6b479167058a38c6bfd3062e480c22ea029386da1e7aca4f65a04` |
| Content fingerprint | `552816ec5cab1416f3463f3b43e247a58e1de9ffd17577916b4600435c0d982a` |
| Provenance | `TAG_COMMIT_PLACEHOLDER` until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 424 unit tests; 145,345 hostile checks; 873 browser assertions |
| Implementation source | `669924a6df0208f7e239985091ff227de9713168` |

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

The final candidate passed 873 of 873 rendered-browser assertions with no
exceptions or console errors. The first independent Opus review and its HOLD
findings are preserved in `docs/design/CLAUDE_OPUS_ALPHA6_RC_REVIEW_HOLD.md`.
Exact-head independent review runs only after this evidence is committed.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
