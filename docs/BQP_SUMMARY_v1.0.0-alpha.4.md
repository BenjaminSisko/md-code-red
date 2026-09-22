---
type: build-quality-summary
status: candidate
last_verified: 2026-09-22
---

# Build Quality Protocol Summary -- v1.0.0-alpha.4

**Current-main base:** `3f3b2c36ceb45b5f04865e10af92c469ea675d25`

**Decision:** PASS for the source-controlled automated build-quality scope and
READY FOR independent exact-head review after the candidate changes are
committed. This document does not claim exact-head approval, publication,
deployment, receiving-browser validation, or pilot acceptance.

## Candidate scope

Alpha.4 rolls the feature work completed after alpha.3 into one release
candidate:

- guided `pvcreate` and `vgcreate` coverage for the P0 RHEL command matrix;
- a dedicated Git activity with eight guided workflows and closed Git ref and
  revision grammars;
- completed Ansible task-selection controls for generated playbooks;
- six configuration-file generators for sshd, chrony, rsyslog, sudoers,
  systemd units, and cron, including the closed token-line document grammar;
- a source-cited command-syntax oracle, Q26, which validates static release
  commands and the independent golden generator corpus; and
- release-readiness corrections that derive provenance evidence names from the
  current version and reconcile stale POA&M statements with repository facts.

## Gate 1 -- build and artifact integrity: PASS

- `APP_VERSION` is `v1.0.0-alpha.4`; `APP_BUILD_DATE` is pinned to
  `2026-09-22`.
- Two clean build/provenance cycles produced byte-identical HTML, SHA-256
  sidecar, and placeholder provenance manifest.
- Candidate artifact: `dist/md-code-red_v1.0.0-alpha.4.html`
  (8,830,936 bytes).
- Artifact SHA-256:
  `cb2763dc7927aeee23773abc6872fa4e1e3e87f6df39b9075d9791d72231c4ee`.
- Ordered five-island content fingerprint:
  `d11292cc1df80a3689a568e53558427f6fcb7df656ac963f4f7b19fc73eead3e`.
- Q1 independently matched the artifact name, version, pinned build date,
  sidecar, five-island order, and recomputed content fingerprint.
- The provenance manifest deliberately carries `TAG_COMMIT_PLACEHOLDER`. The
  publisher must regenerate it with `--commit <exact-merge-sha>` only after the
  reviewed candidate is merged.
- Historical alpha.1, alpha.2, and alpha.3 release assets remain in their
  versioned archive directories. This preparation did not move a tag or mutate
  a published release.

## Gate 2 -- automated verification: PASS

- `python3 qa.py`: Q1-Q26 and JavaScript syntax PASS.
- `python3 -m unittest discover -s tests`: 377 tests PASS.
- `node tests/hostile_harness.js`: 121,873 checks, 0 failures.
- Q18 parsed and compared 320 YAML, 72 INI, and 44 token-line generated-file
  cases; it also checked all 43 real generator entries.
- Q26 validated 620 resolved static commands and 169 applicable golden
  generator commands as 865 simple invocations against 420 independently
  loaded, release-specific grammar rows; 221 forms carry explicit operand
  bounds. Eight invalid-command, one quoted-operator, and five unmodeled-shell
  controls proved that malformed or unsupported structures fail closed.
- Q25 re-resolved 23,447 of 23,447 stored citations.
- The repository-configured Gitleaks scan reported no leaks before the
  candidate commit. Review of the superseded first candidate also found no
  leaks at exact head; the replacement exact-head reviewer must repeat the
  scan against the frozen replacement SHA.
- `git diff --check` is clean.

## Gate 3 -- release controls: READY FOR REVIEW, NOT RELEASED

- Proposed tag: `v1.0.0-alpha.4`.
- The candidate evidence is based on the current working tree. Once the changes
  are committed, independent reviewers must record their results against that
  exact commit. A later content-changing edit invalidates the review and the
  recorded artifact hashes.
- The final tag target is not known yet. The publisher must rebuild and repeat
  the release gates at the selected merge commit, stamp provenance with that
  full commit ID, and compare the resulting hashes with this candidate packet.
- Browser walkthrough, About-panel visual readback, live zero-network
  observation, deployment, publication, and pilot acceptance were not
  executed and are not inferred from the automated results.
