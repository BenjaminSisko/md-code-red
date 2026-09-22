---
type: release-report
status: candidate
last_verified: 2026-09-22
---

# Release Report -- v1.0.0-alpha.4

**Current-main base:** `3f3b2c36ceb45b5f04865e10af92c469ea675d25`

This is a prepared release candidate report. Alpha.4 has not been committed as
a reviewed candidate, tagged, published, deployed, or accepted in a browser or
pilot. Fields that depend on the final merge and tag target remain explicitly
pending.

| Required field | Candidate state |
|---|---|
| Version and build date | `v1.0.0-alpha.4`; `2026-09-22` |
| Artifact | `dist/md-code-red_v1.0.0-alpha.4.html` (8,830,936 bytes) |
| Candidate SHA-256 | `cb2763dc7927aeee23773abc6872fa4e1e3e87f6df39b9075d9791d72231c4ee` |
| SHA-256 sidecar | `dist/md-code-red_v1.0.0-alpha.4.html.sha256`; verified by Q1 |
| Five-island content fingerprint | `d11292cc1df80a3689a568e53558427f6fcb7df656ac963f4f7b19fc73eead3e` |
| Provenance | `dist/md-code-red_v1.0.0-alpha.4.provenance.json`; currently contains `TAG_COMMIT_PLACEHOLDER` by design |
| Determinism | Two clean build/provenance cycles reproduced HTML, sidecar, and placeholder provenance byte for byte |
| Automated verification | Q1-Q26+JS PASS; 377 tests PASS; 121,873 hostile checks PASS; pre-commit Gitleaks PASS, with replacement exact-head repetition pending independent review |
| Proposed tag | `v1.0.0-alpha.4`; not created by candidate preparation |
| Exact-head independent review | PENDING after the candidate changes are committed |
| Final merge/tag target | PENDING; must be supplied to `extract/make_provenance.py --commit` after review and merge |
| Deployment state | NOT DEPLOYED; no host, service, package, account, listener, firewall, DNS, route, or exposure change was made |
| Browser/pilot state | NOT EXECUTED / NOT ACCEPTED; no visual, live-network, operator, or witness evidence is claimed |

## Release contents

Alpha.4 adds the generalized command syntax oracle and the completed Phase 3
feature set: P0 LVM generators, a dedicated Git activity with eight guided
workflows, Ansible task-selection controls, and six configuration-file
generators. It also updates release-readiness automation and reconciles stale
governance statements with the current repository evidence.

The catalog contains 199 curated entries across 102 tools, split into 43 guided
generators and 156 static entries. The separate reference tier contains 14,439
commands across 805 tools, including 1,627 evidence-eligible verbatim spans.
The artifact embeds 1,492 STIG rules and 200 CCI mappings.

## Required exact-head closeout

1. Commit the complete candidate and record its full SHA.
2. Obtain independent regression, security, and content review against that
   exact SHA. Record findings or approval without changing the reviewed commit.
3. Merge the reviewed candidate according to the repository workflow.
4. From the selected merge/tag target, clean `dist/`, rebuild, run Q1-Q26 plus
   JavaScript, the full unit suite, hostile harness, and secret scan.
5. Confirm the merge build reproduces the candidate HTML hash and content
   fingerprint. If it does not, stop and reconcile the difference.
6. Regenerate provenance with `python3 extract/make_provenance.py --commit
   <full-merge-sha>` and verify that only the expected commit field changes
   relative to the placeholder candidate manifest.
7. Create and publish `v1.0.0-alpha.4` only after the required review evidence
   and release checks are complete. Preserve all historical tags and archived
   assets.

## Rollback boundary

The latest preserved release is alpha.3 under
`releases/v1.0.0-alpha.3/` and its immutable tag. A release rollback is a
file-level return to that archived artifact after verifying its sidecar. No
service needs stopping because MD CODE RED is a static local HTML artifact.
