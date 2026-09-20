---
type: deploy-receipt
status: pending-human-acceptance
last_verified: 2026-09-20
---

# Pilot Receipt -- v1.0.0-alpha.2

This is a real candidate handoff record for the recovery build. It is not a human
operational-acceptance claim. The receiving admin completes the remaining named
fields after opening the exact artifact on the pilot host.

| Field | Recorded value |
|---|---|
| Version | v1.0.0-alpha.2 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.2.html` |
| Artifact SHA-256 | `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a` |
| Sidecar verified during build acceptance | Yes |
| Content fingerprint | `f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83` |
| Signature status | UNSIGNED -- SHA-256 integrity only |
| Candidate source revision | `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a` |
| Tagged merge revision | `8186e104fdc3ebbe08a037442787ae5d2c7b01d7` |
| Post-tag provenance revision | `5f66c99f712e373f34f0e15331fd3a1920d86792` |
| Built on | Mac control workstation recovery worktree |
| Built on date | 2026-09-20 |
| Automated post-build check | Fresh exact-tag run on 2026-09-20: Q1-Q25 + JS PASS; 333 unit tests PASS; 101,297 hostile checks PASS |
| Content sample | PASS: deterministic 2/18 verified receipts (10%, rounded up), fresh read-only reruns on Defiant RHEL 8 and Saratoga RHEL 10; 0 red-blast receipts |
| Known limitations | `docs/CHANGELOG.md`, v1.0.0-alpha.2; `docs/QA_REPORT_v1.0.0-alpha.2.md` |
| Rollback artifact | Repository: `releases/v1.0.0-alpha.1/md-code-red_v1.0.0-alpha.1.html`; Defiant staging: `/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.1/md-code-red_v1.0.0-alpha.1.html`, SHA-256 `65de40be58477d3bb1b781d7e2188b2d78329616732971a8bf37fbc7e7b2c665` |
| Receiving host census ID | Defiant / `01 Devices/Defiant RHEL 8.md` |
| Host OS / patch level | Red Hat Enterprise Linux 8.10 (Ootpa), kernel `4.18.0-553.163.1.el8_10.x86_64` |
| Browser / version | Mozilla Firefox `140.14.0esr`; installed before this change; existing xrdp session path active |
| Deployed path | `/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/md-code-red_v1.0.0-alpha.2.html` (read-only file deployment; not yet browser-opened) |
| Deployment method | Existing Mac-to-Defiant SSH/SCP path as `adm-linux`; new temporary tree; on-host verification before atomic rename; no overwrite, package, service, account, listener, firewall, route, DNS, or exposure change |
| Deployment readback | PASS at `2026-09-20T08:53:09-04:00`: file is 8,797,475 bytes, mode `0440`, owner `adm-linux:adm-linux`; sidecar check passed; provenance reports the exact tag, artifact SHA-256, and fingerprint |
| Deployed by / on | Avery Quinn accountable task `MCR-REC-20260920-09`, `2026-09-20T08:53:09-04:00`; **named human operator use/time acknowledgment pending** |
| Independent verifier | Riley-accountable task `MCR-REC-20260920-06` independently re-read the deployed path, sidecar, SHA-256 and provenance after deployment; **Riley Park human browser witness/signature pending** |
| Browser/About/network check | **Pending: local `file://` automation was blocked by provider policy; static Q1/Q2 checks are not a visual About readback or live network receipt** |
| Approved matrix readiness | **Blocked: Defiant has Firefox ESR 140.14.0; no Firefox/Chromium package was observed on Saratoga or `rhel9-stig-test`; no RHEL Chromium cell or approved Windows jump-box host is named** |
| Browser defects | **Blocking: six rails ship, About advertises `Ctrl+Alt+6`, but the key map binds only `1`-`5`; user/pilot shortcut documentation conflicts** |
| Operational pilot acceptance | **Pending named human use; not inferred from automated QA** |

## Evidence boundary and current verdict

The exact released bytes passed automated acceptance and the required content
sample. No approved-host browser was opened in this review, so the About-panel
version/fingerprint were not visually read back and zero network activity was not
observed live. The browser provider rejected the local URL and explicitly barred
alternate-surface workarounds; no bypass was attempted.

**Pilot verdict: HOLD.** The tagged artifact has a blocking keyboard defect and
the approved host/browser matrix is not ready. The exact bytes are deployed
read-only on Defiant and independently re-hashed, but the file has not been opened
in Firefox. Leave named human operator/time, Riley Park's human witness,
browser/network check, and operational acceptance pending until actual evidence
exists.

## Exact deployment procedure executed

1. Confirmed the code repository was at post-tag provenance revision
   `5f66c99f712e373f34f0e15331fd3a1920d86792` and that tag
   `v1.0.0-alpha.2` resolves to
   `8186e104fdc3ebbe08a037442787ae5d2c7b01d7`.
2. Verified the alpha.2 SHA-256 locally and ran its sidecar check from `dist/`.
   Verified the archived alpha.1 sidecar from `releases/v1.0.0-alpha.1/`.
3. Reconciled the active Pilot SOP, QA browser matrix and Home Lab census. Defiant
   is matrix cell B-1 and the only currently viable named approved host: the
   RHEL 9 VM has no browser/graphical target, and Saratoga has no pilot browser.
4. Read the live Defiant release, kernel, Firefox version, available home space,
   xrdp state and destination absence. The final and temporary paths were both
   absent; more than 32 GiB was available in `/home`.
5. Created a new private temporary tree under `adm-linux`, copied alpha.2 HTML,
   sidecar and provenance plus the alpha.1 rollback set over the existing SSH/SCP
   path, and set the directories to `0750` and files to `0440`.
6. On Defiant, ran both sidecar checks and asserted alpha.2 provenance fields for
   tag revision, artifact hash and content fingerprint. Only after those checks
   passed was the temporary tree renamed atomically to
   `/home/adm-linux/MD-CODE-RED`.
7. `MCR-REC-20260920-06` independently repeated the deployed-file and provenance
   readback. This proves the placed bytes, not browser or operational acceptance.

## Required named-human browser procedure

These steps are intentionally unclaimed. A named operator and Riley Park must
perform and sign them in an authorized Defiant xrdp session after the blocking
keyboard defect has an accepted disposition and the exact artifact under test is
confirmed.

1. Record operator name, Riley witness, start time and end time. Log in through
   the existing Defiant xrdp path; do not create a new listener or bypass.
2. In a terminal, run:

   ```bash
   cd /home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2
   sha256sum -c md-code-red_v1.0.0-alpha.2.html.sha256
   ```

   Stop if the result is not `OK`.
3. Open the exact local file in the installed browser:

   ```bash
   firefox --new-window 'file:///home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/md-code-red_v1.0.0-alpha.2.html'
   ```

4. Open About with the rail control and with `?`. Read back version
   `v1.0.0-alpha.2` and fingerprint
   `f6ea94b2256a5c4645bfef8e2d12d97d8b9b7f7ff9f9816795d3b2363a062e83`.
5. Open Firefox Developer Tools Network, clear it, reload the local file, and
   exercise the operator workflow. Record every request. A pass requires no
   HTTP(S), fetch/XHR, WebSocket, beacon or other remote application request;
   the local `file://` document is not a network request.
6. Record actual operator checks and outcomes: select RHEL 8, search and open a
   verified entry, inspect its verification/undo and STIG evidence, compose and
   copy one green command without executing it, exercise keyboard navigation,
   and test every displayed rail shortcut. Capture console errors and defects.
7. Do not sign operational acceptance while `MCR-A2-KEY-001` remains blocking or
   if version, fingerprint, network, console, operator or witness evidence fails.

## Rollback procedure and verified rollback artifact

The prior version is already placed beside alpha.2 at:

`/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.1/md-code-red_v1.0.0-alpha.1.html`

Its on-host sidecar passed, and its SHA-256 is
`65de40be58477d3bb1b781d7e2188b2d78329616732971a8bf37fbc7e7b2c665`.
Its provenance manifest records content fingerprint
`bb878a8fbe792ef10ddc5f5364054203eb404c1c2df1c123bdcc49f2c63179b1`.

1. Close every alpha.2 browser tab; no daemon or service needs stopping.
2. Verify alpha.1 before use:

   ```bash
   cd /home/adm-linux/MD-CODE-RED/v1.0.0-alpha.1
   sha256sum -c md-code-red_v1.0.0-alpha.1.html.sha256
   ```

3. Open the versioned alpha.1 `file://` path and read back its About version and
   fingerprint. Record why rollback occurred, operator, witness, time and any
   retained alpha.2 defect evidence.
4. Keep alpha.2 closed and read-only for investigation. Do not overwrite either
   version. Removing the receipt-owned `/home/adm-linux/MD-CODE-RED` tree is a
   separate cleanup action and is not required to roll browser use back.

## Jordan product handoff

| Required field | Current state |
|---|---|
| Task ID | `MCR-REC-20260920-09` |
| Artifact revision | v1.0.0-alpha.2 tag target `8186e104fdc3ebbe08a037442787ae5d2c7b01d7`; post-tag provenance commit `5f66c99f712e373f34f0e15331fd3a1920d86792` |
| Checks | Local and on-host sidecars PASS; deployed provenance/hash/fingerprint PASS; independent deployed-byte readback PASS; MCR-06 Q1-Q25+JS, 333 tests, 101,297 hostile checks and 2/18 content sample PASS |
| Reviewer state | Riley-accountable exact-revision verdict **HOLD**; deployed-byte readback complete; Riley Park human browser witness and operator signature pending |
| Deployment state | Exact files deployed read-only on approved Defiant host; browser opening, zero-network observation and named human operational acceptance pending |
| Defects | Blocking `MCR-A2-KEY-001`: About advertises a sixth rail shortcut that the shipped key map does not bind; approved browser matrix gaps remain |
| Forecast impact | File deployment completed on 2026-09-20, ahead of the 2026-09-28 evidence target. Overall receipt remains AMBER/at risk because MCR-06 is HOLD and the keyboard defect plus human browser/witness gates are open. Pilot training/adoption cannot start from this receipt. |
