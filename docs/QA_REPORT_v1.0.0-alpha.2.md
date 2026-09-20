---
type: qa-report
status: current
last_verified: 2026-09-20
---

# QA Report -- v1.0.0-alpha.2

**Reviewed source revision:** `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a`

**Tagged merge revision retested:**
`8186e104fdc3ebbe08a037442787ae5d2c7b01d7`

**Result:** PASS for exact-tag automated acceptance, the required 10% verified-
receipt sample, and the Defiant/Firefox ESR `file://` cell; **HOLD** for full
browser/pilot acceptance. The browser run visually confirmed the About identity,
zero external network requests, zero console errors, and the three core user
journeys. The remaining browser cells and named-human operational use are still
pending. A blocking keyboard defect is reproducible in the tagged artifact:
About advertises `Ctrl+Alt+6`, but the shipped key map binds only rails 1 through
5. Fixed-stride reference-corpus review also found two Medium content defects.

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
| Interactive `file://` walkthrough | PASS WITH LIMITATIONS | Exact bytes were opened as `file:///tmp/mcr-qa.ILFLD3/md-code-red_v1.0.0-alpha.2.html` in Firefox ESR 140.14.0 on Defiant/RHEL 8.10 through a temporary loopback-only remote graphical session; core builder, STIG, evidence-export, reference acknowledgement/copy, version-selector, and dark-theme paths worked |
| Approved host/browser matrix | PARTIAL -- 1/6 CELLS | B-1 Defiant/Firefox ESR PASS; B-2 RHEL 9/Firefox, B-3 Saratoga/Firefox, B-4 RHEL/Chromium, B-5 Windows/Chromium, and B-6 Windows/Edge are not runnable with the currently approved hosts/packages. B-6 is added-value rather than blocking by the test plan, but B-2 through B-5 are required coverage |
| Defiant deployment readback | PASS WITH LIMITATION | Released artifact, sidecar, provenance, and alpha.1 rollback are staged read-only under `/home/adm-linux/MD-CODE-RED/`; independent SHA-256/provenance readback passed. Browser QA used a separately re-hashed exact-byte temporary copy, not the staged path, so staging is still not operational acceptance |
| About-panel visual readback | PASS -- B-1 | Firefox displayed `Version v1.0.0-alpha.2 · built 2026-09-20 · UNCLASSIFIED` and fingerprint `f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83` |
| Live zero-network observation | PASS WITH LIMITATION -- B-1 | Firefox Network monitoring across reload showed one expected local-file document row, status 200, blank domain, 0 B transferred, and no external requests; console remained empty. The remote QA session required networking, so this does not satisfy the test plan's stricter OS-network-disabled condition |
| Keyboard-only acceptance | FAIL | Six rail buttons ship, but `KEYMAP` accepts only `1`-`5`; `Ctrl+Alt+6` produced no About transition in Firefox and About's tooltip has no matching binding |
| Reference-corpus content sample | FAIL -- 2 MEDIUM DEFECTS | Fixed stride reviewed 59/23,447 stored positive citations and 55/19,413 residue rows across every populated family/release cell; see the reproducible denominator and findings below |

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

## Reference-corpus fixed-stride sample -- 2026-09-20

This review is separate from the 2/18 verified-receipt sample above. It tests the
new reference-corpus classification itself. The positive denominator is the
23,447 stored citation occurrences (`sum(commands[].o)`), not the closure
ledger's pre-deduplication count of 45,281 classified candidate occurrences.
The residue denominator is 19,413 rows. Together they form a 42,860-row review
population.

For each populated source-family/RHEL cell, the review preserved file order and
selected the first, approximately 25%, 50%, 75%, and last rows using
`round(i * (n - 1) / (k - 1))`; the four-row RHEL 7 raw-capture cell was reviewed
in full. That produces 59 positive citations across 12 cells and 55 residue rows
across 11 cells: **114/42,860 (0.266%)** overall.

| Family | RHEL | Positive denominator / sampled positions | Residue denominator / sampled positions | Result |
|---|---:|---|---|---|
| Raw captures | 7 | 4 / 1,2,3,4 | 0 / not applicable | PASS |
| Raw captures | 8 | 104 / 1,27,53,78,104 | 326 / 1,82,163,245,326 | PASS |
| Raw captures | 9 | 102 / 1,26,51,77,102 | 326 / 1,82,163,245,326 | PASS |
| Raw captures | 10 | 104 / 1,27,53,78,104 | 332 / 1,84,167,249,332 | PASS |
| Red Hat guides | 7 | 3,637 / 1,910,1819,2728,3637 | 2,446 / 1,612,1223,1835,2446 | FAIL -- runnable `lstopo-no-graphics` classified as residue |
| Red Hat guides | 8 | 8,242 / 1,2061,4121,6182,8242 | 1,253 / 1,314,627,940,1253 | NEEDS SME -- complete `su -c` candidate with placeholder is residue |
| Red Hat guides | 9 | 5,523 / 1,1381,2762,4143,5523 | 1,362 / 1,341,681,1022,1362 | FAIL -- runnable `systemd-delta` classified as residue |
| Red Hat guides | 10 | 2,649 / 1,663,1325,1987,2649 | 1,227 / 1,307,614,921,1227 | NEEDS SME -- complete `su -c` candidate with placeholder is residue |
| STIG rules | 7 | 491 / 1,123,246,369,491 | 2,360 / 1,591,1181,1770,2360 | PASS |
| STIG rules | 8 | 719 / 1,181,360,539,719 | 3,210 / 1,803,1605,2408,3210 | PASS |
| STIG rules | 9 | 905 / 1,227,453,679,905 | 3,219 / 1,805,1610,2415,3219 | FAIL -- complete first positive falsely marked truncated |
| STIG rules | 10 | 967 / 1,243,484,725,967 | 3,352 / 1,839,1677,2514,3352 | FAIL -- same shared record falsely marked truncated |

The positive failure is record `ref-995689356a465fb0`, command
`NetworkManager --print-config`, cited to RHEL-09-252040 and RHEL-10-800300.
Both governing check texts show that exact, complete one-line command followed by
output. The extractor nevertheless sets `trunc: true` because `--print-config`
is absent from its no-value long-option allow-list. The UI therefore makes the
false statement that the vendor cut the command and suppresses the governing
evidence-quote path.

The residue failures are root-prompt candidates `lstopo-no-graphics` and
`systemd-delta`, both complete runnable invocations classified `unparseable`.
A targeted extent check found the same two invocations in other RHEL guide cells,
so engineering must fix the classifier and regenerate the corpus rather than
hand-edit generated JSON. The sampled RHEL 8/RHEL 10 `su - <username> -c ...`
rows are complete-looking vendor commands, but their placeholder/wrapper policy
is not explicit; Caleb Stone and Renata Osei must adjudicate before QA calls
them defects or intentional refusals.

## Defiant Firefox ESR browser receipt -- 2026-09-20

- Host/browser: Defiant, RHEL 8.10, Firefox ESR 140.14.0.
- Operation: true local-file open of a temporary exact-byte artifact copy. The
  Defiant copy re-hashed to
  `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a`.
- Identity: About visually matched `v1.0.0-alpha.2`, build date 2026-09-20,
  `UNCLASSIFIED`, and the full expected content fingerprint.
- Builder journey: assembled `systemctl 'status' 'sshd.service'`; green blast,
  Riley Park/Defiant receipt, source, copy, and evidence preview all rendered.
- STIG journey: `/` palette search for `RHEL-08-040101` opened the rule and
  rendered `systemctl is-active firewalld`, CAT II, CCI-002314, NIST AC-17(1),
  expected output, source, and the STIG evidence preview.
- Reference journey: opened `sudo systemctl enable firewalld`; the panel stayed
  read-only, said it was not host-verified or assembled, withheld verify/undo,
  and kept Copy/citation/evidence controls disabled until acknowledgement.
- UI/runtime: RHEL version selection and dark theme worked; Firefox console was
  empty; Network monitoring found zero external requests.
- Failure: `Ctrl+Alt+6` did not open About. Source inspection confirms that the
  advertised sixth shortcut is absent from `KEYMAP`.
- Cleanup: the temporary browser profile, artifact copy, VNC authentication
  material, Xvnc process, and loopback tunnels were removed after the run.

## Defects and acceptance verdict

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| `MCR-A2-ACC-001` | Closed for B-1 | The direct browser-tab provider could not load `file://`; an approved-host interactive desktop session was used instead, and the exact bytes completed the Defiant/Firefox cell. | Preserve this receipt; no claim beyond B-1. |
| `MCR-A2-ACC-002` | Blocking | The approved RHEL browser matrix is not provisioned: only Defiant has Firefox; Saratoga and `rhel9-stig-test` have neither Firefox nor Chromium; no RHEL Chromium package was observed. | Avery Quinn to name/prepare the approved cells under existing installation authority. |
| `MCR-A2-ACC-003` | Blocking | ADR-001 records that no approved Windows jump-box browser-check host exists. | Avery/Founder decision required before B-5/B-6 can run. |
| `MCR-A2-KEY-001` | Blocking | The artifact renders six rails and labels About `Ctrl+Alt+6`, but `KEYMAP` binds only keys `1`-`5`; the documented About shortcuts are also stale/conflicting. | Engineering fix plus exact-revision regression and doc reconciliation required. |
| `MCR-A2-CONT-001` | Medium | Complete governing command `NetworkManager --print-config` is falsely marked incomplete for both sampled STIG citations, producing an inaccurate warning and suppressing governing evidence quote. | Add the flag to the explicit no-value option policy, add regression coverage, regenerate, and obtain Caleb/Renata adjudication. |
| `MCR-A2-CONT-002` | Medium | Complete root-prompt commands `lstopo-no-graphics` and `systemd-delta` are classified `unparseable` residue; follow-through shows the omissions recur across guide releases. | Fix the strong-head/classification rule, add negative/positive controls, regenerate, and obtain Caleb/Renata adjudication. |
| `MCR-A2-CONT-003` | Unrated -- SME decision | Sampled RHEL 8/10 `su - <username> -c "gsettings ..."` candidates are complete-looking but reside under `unparseable`; intended wrapper/placeholder policy is undocumented. | Caleb Stone and Renata Osei decide eligible vs. intentional refusal, then document and test the policy. |

**Exact-revision verdict:** automated acceptance, verified-receipt sampling, and
the Defiant/Firefox ESR browser cell PASS for the released bytes; reference-
corpus sampling FAILS with two Medium defects; browser/pilot promotion is
**HOLD** because a High keyboard defect and four required matrix cells remain
open. The About-panel visual readback and zero-external-request result may be
claimed for B-1 only. Do not claim the full browser matrix, the stricter
OS-network-disabled test, keyboard-only acceptance, operational deployment
acceptance, or named-human operational acceptance. Read-only staging and an
exact-byte QA copy are not operational deployment acceptance.
