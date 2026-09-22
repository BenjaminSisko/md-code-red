---
type: release-evidence
status: candidate
last_verified: 2026-09-22
---

# QA Report -- v1.0.0-alpha.5

The complete candidate verification sequence passed on 2026-09-22.

| Check | Result |
|---|---|
| Build-time schema validation | PASS |
| QA gates | PASS; Q1-Q26 plus JavaScript syntax |
| Python unit suite | PASS; 399 tests |
| Hostile-input harness | PASS; 122,313 checks, zero failures |
| Generator golden commands | PASS; 172 release-specific comparisons |
| Command syntax oracle | PASS; 865 simple invocations, 420 release-specific grammar rows |
| Real reference-export snapshot | PASS after deliberate alpha.5 version/fingerprint/name refresh |
| Generated release facts | PASS; current against source data |
| Validation-matrix drift check | PASS; receipt counts match `content/commands.json` |
| Gitleaks | PASS; 189 commits and approximately 69 MB scanned, no leaks |
| `git diff --check` | PASS |

The candidate contains 199 curated entries across 102 tools: 43 guided
generators and 156 static entries. All 43 generators and all 106 current fields
have schema-validated instructional metadata. The browser still shows missing
host receipts and missing flag explanations honestly rather than manufacturing
evidence.

One read-only RHEL 8 matrix observation was completed in this session. It is not
counted as a new receipt because it has no independent reviewer. The documented
RHEL 9 target timed out and the RHEL 10 target was down; no command ran on those
targets.
