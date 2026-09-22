---
type: release-report
status: released
last_verified: 2026-09-22
---

# Release Report -- v1.0.0-alpha.4

**Reviewed candidate:** `b6c0ad76b020e5c2c2dc36bea025993ef6e0bcfb`

**Tagged merge revision:** `fb0a9451c828301d509e9190d18576ca0422e985`

This report records the approved alpha.4 artifact and its immutable tag target.
Release publication is separate from deployment, receiving-browser validation,
and pilot acceptance; none of those operational acceptance states is inferred.

| Required field | Released state |
|---|---|
| Version and build date | `v1.0.0-alpha.4`; `2026-09-22` |
| Artifact | `dist/md-code-red_v1.0.0-alpha.4.html` (8,830,936 bytes) |
| SHA-256 | `cb2763dc7927aeee23773abc6872fa4e1e3e87f6df39b9075d9791d72231c4ee` |
| SHA-256 sidecar | `dist/md-code-red_v1.0.0-alpha.4.html.sha256`; verified by Q1 and direct digest comparison |
| Five-island content fingerprint | `d11292cc1df80a3689a568e53558427f6fcb7df656ac963f4f7b19fc73eead3e` |
| Provenance | `dist/md-code-red_v1.0.0-alpha.4.provenance.json`; records tag target `fb0a9451c828301d509e9190d18576ca0422e985` |
| Determinism | Two clean candidate build/provenance cycles were byte-identical; the clean merge-target rebuild reproduced the same artifact hash and content fingerprint |
| Automated verification | Q1-Q26+JS PASS; 377 tests PASS; 121,873 hostile checks PASS; exact-head and merge-target repository-configured Gitleaks scans PASS |
| Release tag | `v1.0.0-alpha.4`, explicitly targeting merge `fb0a9451c828301d509e9190d18576ca0422e985` |
| Independent review | APPROVED at exact candidate head `b6c0ad76b020e5c2c2dc36bea025993ef6e0bcfb`; no blocking findings remain |
| Deployment state | NOT DEPLOYED; no host, service, package, account, listener, firewall, DNS, route, or exposure change was made |
| Browser/pilot state | NOT EXECUTED / NOT ACCEPTED; no visual, live-network, operator, or witness evidence is claimed |
| Integrity boundary | Annotated tag and artifact are unsigned; integrity relies on SHA-256 plus Git lineage, not publisher identity |

## Release contents

Alpha.4 adds the generalized command syntax oracle and the completed feature
set: P0 LVM generators, a dedicated Git activity with eight guided workflows,
Ansible task-selection controls, and six configuration-file generators. It
also corrects release-readiness automation and reconciles stale governance
statements with repository evidence.

The catalog contains 199 curated entries across 102 tools, split into 43 guided
generators and 156 static entries. The separate reference tier contains 14,439
commands across 805 tools, including 1,627 evidence-eligible verbatim spans.
The artifact embeds 1,492 STIG rules and 200 CCI mappings.

Q26 expands 620 static and 169 golden generator release commands into 865
simple invocations and checks them against 420 independently loaded,
release-specific grammar rows. The tokenizer preserves quoted and escaped
operator identity, validates every modeled compound stage, and fails closed on
unsupported line breaks and shell structure. Of the 420 declared grammar
authorities, 69 repository capture paths are existence-checked; the other 351
external or manual labels remain documentary citations rather than
mechanically re-resolved evidence.

## Release operation record

1. PR #15 merged the independently reviewed candidate without changing its
   files.
2. A clean rebuild at merge revision
   `fb0a9451c828301d509e9190d18576ca0422e985` reproduced the reviewed artifact
   SHA-256 and content fingerprint.
3. Q1-Q26 plus JavaScript, all 377 unit tests, 121,873 hostile-input checks,
   `git diff --check`, and the repository-configured Gitleaks scan passed at the
   merge revision.
4. Provenance was stamped in this later commit with the selected tag target;
   only the expected `git_commit` field changed from the placeholder manifest.
5. The annotated unsigned tag targets the merge revision rather than this
   later provenance-stamp commit. Historical tags and archived assets remain
   unchanged.

## Rollback boundary

The prior release is alpha.3 under `releases/v1.0.0-alpha.3/` and its immutable
tag. A rollback is a file-level return to that archived artifact after
verifying its sidecar. No service needs stopping because MD CODE RED is a
static local HTML artifact.
