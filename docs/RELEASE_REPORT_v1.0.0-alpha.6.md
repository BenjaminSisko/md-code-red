---
type: release-evidence
status: candidate
last_verified: 2026-10-01
---

# Release Report -- v1.0.0-alpha.6

Verification totals: 480 unit tests; 168,697 hostile-input checks; 27,652 pipeline checks; 898 rendered-browser records in each delivery mode (896 pass/fail assertions and 2 performance observations).

This candidate replaces the dense tool-first interface with a task-centered
Home and guided Configure, Review, and Verify workflow while retaining the
offline, provenance-backed RHEL command catalog. It closes the complete
functional audit and addresses the findings recorded by thirteen independent
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
| Verification | Q1-Q26 + JS; 480 unit tests; 168,697 hostile checks; 896 pass/fail browser assertions plus 2 performance observations in each of standalone and HTTP modes |
| Implementation source | `3e5c95402e7349a9ad7f6be233673728e301410d` |

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
  and rsync recovery state that refuses unsafe shared parents, bounds a
  persistent symlink-replant attack, fails with exact status 1, preserves the
  full transaction, and does not follow the attacker link.
- Root-owned, mode-0700 NetworkManager rollback state with atomic creation,
  pre-install symlink refusal, strict Recover/Finalize mode validation,
  positive finalization coverage, and saved-connection reactivation.
- Step-by-step runbooks that expose Copy only for authored runnable commands,
  keep Recover separate, gate red evidence copying, and retain focus after
  deterministic keyboard clipboard activation. The browser gate compares the
  copied Recover script byte for byte with the instruction-binding probe.
- Complete artifact-backed test discovery in Forgejo CI, release gating for
  uncommitted protected edits and extraction/CI changes, exact-version artifact
  selection, and recovery-refusal guidance that tells operators to preserve the
  rollback transaction while resolving its trust failure.
- Fail-closed transfer coverage for an unremovable raced link, a planted
  non-link directory, and exhaustion after three replants. Each SCP/rsync case
  requires exact status 1, retained trusted rollback state, and an outside
  directory containing only its original sentinel; targeted mutants prove the
  guarded success and transaction-retention paths cannot silently regress.
- CI preserves the committed candidate provenance while building the HTML
  before unit discovery. Full-shell source-shape coverage rejects the named
  late listener, inline/property handler, synthetic activation, and `KEYMAP`
  mutation forms without claiming arbitrary call-graph analysis. The browser auditor retains distinct standalone
  and HTTP result files while proving the browser's main-document bytes equal
  the audited artifact.
- The post-merge provenance stamp is release-safe: readiness normalizes only
  `git_commit`, requires canonical JSON and a commit SHA at or after the reviewed
  implementation in the release tree's ancestry, compares every other manifest
  field with the reviewed implementation, and refuses an uncommitted stamp.
  This keeps the documented post-stamp CI run green without
  weakening protection for HTML, sidecar, tests, extraction, or workflow files.

The final candidate passed all 896 pass/fail rendered-browser assertions and
recorded two informational performance observations in both its standalone
`file://` delivery mode and a local HTTP delivery, with no exceptions or console
errors. Two consecutive builds produced the same 8,944,791-byte
artifact, SHA-256 sidecar, and provenance manifest byte for byte. The first
through thirteenth independent Opus review records are preserved in
`docs/design/`, including the eighth-review PASS, the ninth-review HOLD, and
the tenth-, eleventh-, twelfth-, and thirteenth-review HOLDs. This candidate closes their
transaction, signal, trust-check, native-keyboard, bounded-failure, exact
clipboard, CI toolchain, write-through-link, fail-closed recovery,
release-integrity, and operator-guidance findings. Exact-head independent
review runs only after this evidence is committed.

A separate post-merge simulation stamped this candidate SHA into the manifest,
changed the release report to released state, committed both files, rebuilt the
same HTML, and passed 480 of 480 unit tests plus Q1-Q26 + JS from the resulting
tree. The stamped manifest retained the reviewed release-workstation toolchain
and every semantic field other than `git_commit`.

Publication does not establish deployment, receiving-host acceptance, or command
execution. The release must remain labeled lab-only and unsigned. After merge,
the tag must target the reviewed merge exactly, the full gates must be rerun on
that tag target, and the later provenance stamp must name that SHA.
