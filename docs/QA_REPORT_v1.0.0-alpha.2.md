---
type: qa-report
status: current
last_verified: 2026-09-20
---

# QA Report -- v1.0.0-alpha.2

**Revision:** `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a`

**Result:** PASS for automated acceptance; interactive receiving-host browser
acceptance remains pending.

| Check | Result | Evidence |
|---|---|---|
| Build | PASS | 8,797,475-byte artifact; SHA-256 `692a8a3c...21486a` |
| QA gates | PASS | Q1-Q25 and JS |
| Unit suite | PASS | 333 tests, 0 failures |
| Hostile harness | PASS | 101,297 checks, 0 failures |
| Reference citations | PASS | 23,447/23,447 re-resolved |
| Evidence export | PASS | Real RHEL 9 `firewalld-service-active` export matches the alpha.2 snapshot |
| Browser-facing structure | PASS | JavaScript syntax plus 15 pipeline UI wiring tests and 14 negative controls |
| Interactive Chrome `file://` walkthrough | BLOCKED BY TOOL POLICY | Browser automation rejected the local URL; no bypass attempted |

The candidate covers all four RHEL releases. The curated tier has 183 entries
across 100 tools. The reference tier has 14,439 distinct records across three
families and 45,281 citations. Q24 proves reference/curated shape separation and
permits evidence quote export only for byte-exact governing-source spans. Q25
re-resolves every stored citation, so a moved or changed source fails the build.

Known pilot observations remain visible: most flag explanations are uncurated,
only five STIG/release pairs have captured expected output, and the release is
unsigned. The receiving admin must verify the sidecar, open the artifact in the
required browser, compare the About-panel fingerprint, and record the zero-network
  sanity check on the deploy receipt.
