---
type: qa-report
status: current
last_verified: 2026-09-20
---

# QA Report -- v1.0.0-alpha.2

**Reviewed source revision:** `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a`

**Tagged merge revision retested:**
`8186e104fdc3ebbe08a037442787ae5d2c7b01d7`

**Result:** PASS for exact-tag automated acceptance and the required 10% content
sample; **HOLD** for browser/pilot acceptance. The interactive receiving-host
browser matrix, About-panel readback, live zero-network observation, and named
human operational use remain pending. A blocking keyboard defect was also found
in the tagged artifact: About advertises `Ctrl+Alt+6`, but the shipped key map
binds only rails 1 through 5.

| Check | Result | Evidence |
|---|---|---|
| Build identity | PASS | Exact tag `8186e104...b01d7`; 8,797,475-byte artifact; SHA-256 `692a8a3c...21486a` |
| QA gates | PASS | Fresh detached-tag run: Q1-Q25 and JS |
| Unit suite | PASS | Fresh detached-tag run: 333 tests, 0 failures |
| Hostile harness | PASS | Fresh detached-tag run: 101,297 checks, 0 failures |
| Reference citations | PASS | 23,447/23,447 re-resolved |
| Content receipt sample | PASS | 2/18 verified entry/version receipts (10%, rounded up), fixed stride 9; fresh read-only host reruns matched both stored receipts; 0 red-blast receipts in the denominator |
| About version/fingerprint, static gate | PASS | Q1 matched version `v1.0.0-alpha.2` and recomputed fingerprint `f6ea94b2...62e83` from all five shipped data islands |
| Browser-facing structure | PASS WITH LIMITATION | JavaScript syntax plus 15 pipeline UI wiring tests and 14 negative controls; these did not catch the six-rail/five-key binding defect |
| Interactive `file://` walkthrough | BLOCKED BY TOOL POLICY | Browser provider rejected the local URL and explicitly prohibited alternate-browser or indirect workarounds; no bypass attempted |
| Approved host/browser matrix | NOT READY | Defiant has Firefox ESR 140.14.0; Saratoga and `rhel9-stig-test` have no Firefox/Chromium package; no RHEL Chromium cell or approved Windows jump-box host exists |
| About-panel visual readback | NOT EXECUTED | Static value checks passed, but no approved-host browser displayed the panel |
| Live zero-network observation | NOT EXECUTED | Q2 static air-gap gate passed; this is not represented as a live browser network receipt |
| Keyboard-only acceptance | FAIL | Six rail buttons ship, but `KEYMAP` accepts only `1`-`5`; About's `Ctrl+Alt+6` tooltip has no matching binding |

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

## Exact-tag content sample -- 2026-09-20

The denominator is the 18 verified entry/version receipts that Q16 found in the
tagged artifact. Following the company test plan's 10% rule, the sample size is
`ceil(18 * 0.10) = 2`. Sorting the receipts by numeric RHEL version then entry ID
and taking fixed stride 9 selected the following two records. This is a
reproducible sample, not an after-the-fact convenience sample.

| Sample | Fresh host observation | Result |
|---|---|---|
| RHEL 8 / `ctrl-alt-del-target-masked` | Defiant, RHEL 8.10, kernel `4.18.0-553.163.1.el8_10.x86_64`; `systemctl status ctrl-alt-del.target` returned exit 3 with `Loaded: masked` and `Active: inactive (dead)` | PASS -- matches the stored receipt and its documented LSB inactive status |
| RHEL 10 / `ctrl-alt-del-target-masked` | Saratoga, RHEL 10.2, kernel `6.12.0-211.53.1.el10_2.x86_64`; the same command returned exit 3 with `Loaded: masked` and `Active: inactive (dead)` | PASS -- matches the stored receipt and its documented LSB inactive status |

All 18 verified receipts are green-blast. The plan's 100% red-blast review rule
therefore had a denominator of zero and was not applicable. These two reruns were
read-only and did not alter either host. They are content evidence, not a browser
or human operational-acceptance receipt.

## Defects and acceptance verdict

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| `MCR-A2-ACC-001` | Blocking | The available interactive-browser provider blocks `file://` and prohibits workaround through another surface. | Named human must execute the matrix on approved hosts. |
| `MCR-A2-ACC-002` | Blocking | The approved RHEL browser matrix is not provisioned: only Defiant has Firefox; Saratoga and `rhel9-stig-test` have neither Firefox nor Chromium; no RHEL Chromium package was observed. | Avery Quinn to name/prepare the approved cells under existing installation authority. |
| `MCR-A2-ACC-003` | Blocking | ADR-001 records that no approved Windows jump-box browser-check host exists. | Avery/Founder decision required before B-5/B-6 can run. |
| `MCR-A2-KEY-001` | Blocking | The artifact renders six rails and labels About `Ctrl+Alt+6`, but `KEYMAP` binds only keys `1`-`5`; the documented About shortcuts are also stale/conflicting. | Engineering fix plus exact-revision regression and doc reconciliation required. |

**Exact-revision verdict:** automated acceptance and sampled content validation
PASS for the released bytes; browser/pilot promotion is **HOLD**. Do not claim the
About-panel visual readback, live zero-network result, full browser matrix,
keyboard-only acceptance, deployment, or named human operational acceptance on
this evidence.
