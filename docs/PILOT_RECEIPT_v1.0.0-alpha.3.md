---
type: deploy-receipt
status: pending-human-acceptance
last_verified: 2026-09-20
---

# Pilot Receipt -- v1.0.0-alpha.3

This receipt records the exact published alpha.3 release assets deployed
read-only on the approved Defiant pilot host. It is deployment and integrity
evidence only. No browser was opened, no named human used the artifact, and no
pilot or operational acceptance is claimed.

| Field | Recorded value |
|---|---|
| Task / event | `MCR-REC-20260920-09`; `MCR-HANDOFF-MCR-A3-DEPLOY-20260920T120753-0400` |
| Version | `v1.0.0-alpha.3` |
| GitHub release | `https://github.com/BenjaminSisko/md-code-red/releases/tag/v1.0.0-alpha.3` |
| Annotated tag target | `e72c235fbb8e58c72c7ebf861696efeef5e4a27b` |
| Post-tag provenance / main revision | `3f38e8c9816ebd96e95364183ca90e73c3606ef2` |
| Artifact | `md-code-red_v1.0.0-alpha.3.html`, 8,797,479 bytes |
| Artifact SHA-256 | `62c80e950d82ed55086f383ce1918b76ed1425cea9c064d791e9a2e5c7283818` |
| Sidecar-file SHA-256 | `39906bcf34c95c6d5d379a56bc9d4af7963481505d0eee9dc58845eb84bce83a` |
| Provenance-file SHA-256 | `2ec6f0c21fffe10d10d0c194c5c326685228520ce60425672a0d20b1a28de301` |
| Content fingerprint | `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea` |
| Signature status | UNSIGNED -- SHA-256 integrity plus Git/release lineage only |
| Automated release checks | Q1-Q25+JS PASS; 336 unit tests PASS; 101,297 hostile checks PASS; rail-keyboard source and built-artifact contracts PASS; deterministic double-build PASS; Gitleaks full-tree scan PASS |
| Riley exact-head review | APPROVE at reviewed candidate `3f68ac1da3dac3bbb29fab6a07363ee0da1d5015`; no blocker, high, medium or low findings |
| Receiving host / census | Defiant / `01 Devices/Defiant RHEL 8.md`; `defiant.home.arpa` |
| Host OS / patch level | RHEL 8.10; kernel `4.18.0-553.163.1.el8_10.x86_64` |
| Installed browser | Firefox ESR `140.14.0-1.el8_10`; not opened by this deployment |
| Deployed path | `/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.3/` |
| Deployment method | Existing Mac-to-Defiant SSH/SCP path as `adm-linux`; private mode-0700 staging directory; all three assets verified before atomic rename |
| Deployed by / time | Avery Quinn / Caleb Stone task; `2026-09-20T12:07:53-04:00` |
| On-host controls | Directory `0750`; three files `0440`; owner/group `adm-linux:adm-linux` |
| On-host integrity | All three published file hashes PASS; HTML sidecar check PASS; provenance version, tag target, artifact size/hash and fingerprint PASS |
| Wazuh state / impact | `wazuh-agent` active after deployment; no agent, syslog, allowlist or logging configuration changed |
| PPS / network / topology impact | None: existing SSH carried a bounded file copy; no address, route, DNS, protocol, port, listener, firewall rule, approved-client scope, exposure or topology changed |
| Rollback artifact | Preserved alpha.2 path `/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/`; HTML SHA-256 `692a8a3cfc443fd3960b022530e1af52214236d8aa35d9c33aae1ba40821486a` re-read after deployment |
| Independent receiving verifier | PENDING; the deployment task performed a final-path readback, but no separate human/QA verifier is claimed here |
| About version/fingerprint readback | NOT EXECUTED |
| Keyboard-only walkthrough | NOT EXECUTED in an approved receiving-host browser |
| Live zero-network / console observation | NOT EXECUTED |
| Named human operational use | NOT EXECUTED |
| Deployment state | COMPLETE AND INTEGRITY-VERIFIED on Defiant |
| Pilot verdict | HOLD pending named-human browser use and Riley's attended acceptance witness |

## Deployment procedure executed

1. Read the published GitHub release metadata and verified that the annotated
   `v1.0.0-alpha.3` tag peels to
   `e72c235fbb8e58c72c7ebf861696efeef5e4a27b`. GitHub and Forgejo `main`
   were observed at post-tag provenance revision
   `3f38e8c9816ebd96e95364183ca90e73c3606ef2`.
2. Downloaded the three published release assets into a private local temporary
   directory. Their SHA-256 values matched the release digests above, and the
   HTML sidecar returned `OK`.
3. Read Defiant's release, kernel, installed Firefox, Wazuh state, `/home`
   capacity, existing version directories and rollback hash. The alpha.3 final
   path was absent, more than 32 GiB was free, Wazuh was active, and alpha.2's
   rollback hash matched.
4. Created private staging directory
   `/home/adm-linux/.md-code-red-alpha3-stage-MCR-DEPLOY-20260920T120706-0400`,
   copied only the three published assets over the existing SSH/SCP path, and
   set the directory to `0750` and files to `0440` with
   `adm-linux:adm-linux` ownership.
5. In the staging directory, verified each published file hash, ran the HTML
   sidecar, and asserted provenance version, release commit, filename, byte
   count, artifact hash and content fingerprint. Only after every assertion
   passed was the directory atomically renamed to the final alpha.3 path.
6. Re-read the final path, all three hashes, sidecar result, ownership/modes,
   preserved alpha.2 hash and active Wazuh state. No browser process was
   started and no host configuration was changed.

## Required named-human acceptance procedure

These steps remain deliberately unclaimed.

1. Record the named operator, Riley witness, approved host/browser, start time
   and end time.
2. Re-run the exact alpha.3 sidecar check from the final Defiant directory and
   stop unless it returns `OK`.
3. Open the exact local alpha.3 `file://` path in the approved Firefox session.
4. Confirm About shows `v1.0.0-alpha.3` and fingerprint
   `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea`.
5. Exercise `Ctrl+Alt+1` through `Ctrl+Alt+6`, confirming each shortcut selects
   and focuses its advertised rail, especially `Ctrl+Alt+6` for About.
6. Complete the Pilot SOP's command, search, evidence-export,
   favorites/recent, theme, print and keyboard-only smoke paths without
   executing a generated system command.
7. Record the browser console and DevTools Network results. Acceptance requires
   zero remote application requests from the local-file workflow.
8. If any identity, sidecar, keyboard, console, network or workflow check
   fails, close alpha.3 and return to the verified alpha.2 rollback artifact.

## Rollback

Alpha.2 remains intact at
`/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/`. Close every alpha.3 browser tab,
verify the alpha.2 sidecar, and open the versioned alpha.2 local file. No daemon
or service needs stopping, and neither version should be overwritten or deleted.

## Jordan handoff state

| Required field | Current state |
|---|---|
| Correction / release | `MCR-A2-KEY-001` corrected in separately versioned, published alpha.3 |
| Release evidence | Tag `e72c235f...`; provenance/main `3f38e8c...`; published asset hashes above |
| Reviewer state | Riley exact-head technical review APPROVE; receiving-host human witness pending |
| Deployment state | Complete and integrity-verified on Defiant at `2026-09-20T12:07:53-04:00` |
| Browser/pilot state | HOLD; no browser, named-human or operational acceptance claimed |
| Forecast impact | The corrected release and deployment gates are complete; the remaining gate is named-human browser/pilot evidence and Riley's attended witness |

`WADE_BLOCKED: alpha.3 is published, deployed and integrity-verified on Defiant, but named-human browser use, About identity readback, live zero-network/console evidence, operator checks and Riley Park's attended acceptance witness remain pending.`
