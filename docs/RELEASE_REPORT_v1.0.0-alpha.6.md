---
type: release-evidence
status: candidate
last_verified: 2026-09-30
---

# Release Report -- v1.0.0-alpha.6

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It also closes every defect
found by the complete alpha.6 functional audit.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.6` / 2026-09-30 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.6.html`; 8,895,469 bytes |
| Artifact SHA-256 | `e25e88a7ced014aa45273bd865a27d8860aa56126b03e1867ca7d0cadd12c1e9` |
| Content fingerprint | `327324da688bf7c04bad4952832671958f16d64824c7e5839166397422a4557e` |
| Provenance | `TAG_COMMIT_PLACEHOLDER` until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 419 unit tests; 128,449 hostile checks; 867 browser assertions; Gitleaks clean |
| Candidate source | `271fc9f08d048d9f3da038f6dc487d8187480b0b` |

The release adds or changes:

- Task-centered Home, common outcomes, working modes, learning paths, favorites,
  recent work, and an explicit reviewed-catalog/reference-library boundary.
- Guided Configure, Review, and Verify workflows with a prominent exact command,
  trust signals, field teaching, runbooks, release comparison, and responsive
  command-first mobile reading order.
- Fifty-eight guided generators, including repaired grep, signaling, transfer,
  remote-shell, synchronization, Git recovery, account, environment, and stream
  workflows, plus the all-release `lsblk` storage inspector.
- A stable stage-oriented pipeline inspector and complete pipeline regression
  coverage.
- Search, keyboard, focus, modal, pressed-state, landmark, contrast, mobile,
  evidence, and reference-library improvements from the UX and independent
  review package.

All four functional-audit defect families are closed. The final candidate passed
867 of 867 rendered-browser assertions with no exceptions or console errors.
The functional and repository release-candidate gates are clear for exact-head
review.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
