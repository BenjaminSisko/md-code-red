---
type: qa-report
status: candidate
last_verified: 2026-09-22
---

# QA Report -- v1.0.0-alpha.4

**Current-main base:** `3f3b2c36ceb45b5f04865e10af92c469ea675d25`

**Result:** PASS for the complete source-controlled automated acceptance scope.
The candidate still requires independent review at its exact committed head.
Receiving-browser, deployment, and pilot acceptance were not executed.

| Check | Result | Evidence |
|---|---|---|
| Build identity | PASS | 8,830,936-byte alpha.4 artifact; SHA-256 `cb2763dc7927aeee23773abc6872fa4e1e3e87f6df39b9075d9791d72231c4ee` |
| Content identity | PASS | Five-island fingerprint `d11292cc1df80a3689a568e53558427f6fcb7df656ac963f4f7b19fc73eead3e` |
| QA gates | PASS | Q1-Q26 plus JavaScript syntax; Q1 selected only the alpha.4 artifact and verified its sidecar and fingerprint |
| Unit suite | PASS | 377 tests, 0 failures |
| Hostile-input harness | PASS | 121,873 checks, 0 failures |
| Generated documents | PASS | 320 YAML, 72 INI, and 44 token-line round-trip oracle checks; 43 real generators exercised |
| Command syntax oracle | PASS | 789 release commands expanded to 865 simple invocations and checked against 420 release-specific grammar rows; 221 forms have operand bounds and 14 adversarial controls fired |
| Reference citations | PASS | 23,447/23,447 re-resolved |
| Deterministic build | PASS | Two clean build/provenance cycles produced byte-identical HTML, sidecar, and placeholder provenance files |
| Secret review | PENDING AT REPLACEMENT HEAD | Pre-commit and superseded-candidate exact-head Gitleaks scans found no leaks; the replacement exact-head reviewer must repeat the repository-configured scan |
| Source hygiene | PASS | `git diff --check` clean |
| Exact-head independent review | PENDING | Must be recorded after the candidate changes are committed; no reviewer or approval is invented here |
| Interactive `file://` walkthrough | NOT EXECUTED | Requires an approved receiving-host browser and recorded operator evidence |
| About-panel visual readback | NOT EXECUTED | Static identity checks passed; no visual claim is made |
| Live zero-network observation | NOT EXECUTED | Q2 static air-gap gate passed; no live browser network receipt is claimed |
| Deployment/pilot acceptance | NOT EXECUTED | Candidate is local and has not been published or deployed |

## Functional coverage added since alpha.3

The 199-entry curated catalog contains 102 tools, 43 guided generators, and 156
static entries. Alpha.4 adds or completes LVM, Git, Ansible, and configuration
file generation. The generated-file safety model now has three independent
parsers: YAML, INI, and token-line. The command syntax model adds a second,
source-cited structural check while retaining the hand-authored golden command
table as an independent regression oracle.

Q26 is intentionally broader than the generator table: it validates every
resolved static command for every applicable RHEL release and the applicable
per-release golden generator commands. The fourteen adversarial controls ensure
the new oracle cannot pass by accepting arbitrary tokens or unsupported shell
structure.

## Acceptance boundary

This report records repeatable checks performed against the candidate working
tree. A reviewer must assess the exact committed candidate head, including the
new tool grammar corpus, release evidence, POA&M reconciliation, generator
content, and Q26 integration. After merge, the publisher must rebuild from the
selected tag target and regenerate provenance with its full commit SHA. No
historical alpha.3 review, deployment state, or pilot result is carried forward
as acceptance for alpha.4.
