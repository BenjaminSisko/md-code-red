---
type: qa-report
status: candidate
last_verified: 2026-09-20
---

# QA Report -- v1.0.0-alpha.3

**Original task base:** `46507926500ea92aa8904c6a9d69698e2d3ba705`

**Reconciled current-main base:**
`f5a29549a7b68b11ccdf20ac39bde834954c112f`, including required ancestor
`b9906e460625fa7b63406854646e4666459e9450`.

**Result:** PASS for the complete source-controlled automated acceptance scope;
READY FOR Riley exact-head regression review. Browser/pilot acceptance remains
HOLD and was not executed or inferred.

| Check | Result | Evidence |
|---|---|---|
| Build identity | PASS | 8,797,479-byte alpha.3 artifact; SHA-256 `62c80e950d82ed55086f383ce1918b76ed1425cea9c064d791e9a2e5c7283818` |
| QA gates | PASS | Q1-Q25 and JS; Q1 selected only the alpha.3 artifact and independently verified its sidecar and fingerprint |
| Unit suite | PASS | 336 tests, 0 failures |
| Hostile harness | PASS | 101,297 checks, 0 failures |
| Rail-keyboard regression | PASS | 3 Python contract tests plus Node execution against source and built artifact; all six rails uniquely mapped, advertised, selected, and focused |
| Reference citations | PASS | 23,447/23,447 re-resolved |
| Deterministic build | PASS | Two clean build/provenance cycles produced byte-identical HTML, sidecar, and provenance files |
| Content corpus parity | PASS WITH EXPLAINED METADATA CHANGE | Four reference islands are byte-identical to alpha.2; the first island is equal after normalizing only `meta.version`; all non-metadata keys are equal |
| Source/secret review | PASS | Clean whitespace/error review, exact alpha.2 blob and tag lineage checks, no alpha.3 tag, and Gitleaks 8.30.1 full-tree scan with no leaks |
| Interactive `file://` walkthrough | NOT EXECUTED | Requires approved receiving-host browser and named operator/witness evidence after integration |
| About-panel visual readback | NOT EXECUTED | Static Q1 identity checks passed; no visual claim is made |
| Live zero-network observation | NOT EXECUTED | Q2 static air-gap gate passed; no live browser network receipt is claimed |
| Deployment/pilot acceptance | NOT EXECUTED | Candidate remains local/PR-only and has not been deployed |

## MCR-A2-KEY-001 regression

The alpha.2 defect was a cross-layer mismatch: six rail buttons and an About
tooltip advertising `Ctrl+Alt+6`, but a runtime `KEYMAP` containing only keys
`1` through `5`. The correction adds key `6` to the one rail-jump binding and a
contract test that derives its expected mapping from the rendered button order.
It executes the shipped `KEYMAP`, modifier matcher, and `railAt()` implementation,
then cross-checks the current user-guide table. The source template and built
alpha.3 artifact both report:

| Shortcut | Rail |
|---|---|
| `Ctrl+Alt+1` | Command Builder |
| `Ctrl+Alt+2` | STIG and Evidence Search |
| `Ctrl+Alt+3` | Ansible Generator |
| `Ctrl+Alt+4` | Favorites and Recent |
| `Ctrl+Alt+5` | Reference Commands |
| `Ctrl+Alt+6` | About |

## Acceptance boundary

The prior content-sample evidence remains unchanged because no curated command,
receipt, capture, rule, flag dictionary, or reference record changed. This run
does not reuse alpha.2's browser or pilot state as acceptance for alpha.3. Riley
must review the exact candidate head, and a named operator/witness must later
perform the receiving-host browser procedure before any browser/pilot acceptance
claim.
