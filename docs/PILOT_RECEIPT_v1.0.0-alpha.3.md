---
type: deploy-receipt
status: release-complete-browser-check-waived
last_verified: 2026-09-20
---

# Pilot Receipt -- v1.0.0-alpha.3

This receipt records the exact published alpha.3 release assets deployed
read-only on Defiant. A later read-only survey found that the other RHEL 8
systems are headless. Benny then waived the separate attended host/browser
check as redundant: the delivered file is a self-contained HTML application for
modern browsers, and the exact release bytes already passed the automated
browser, keyboard, integrity and hostile-input suites. No replacement host is
required. No browser was opened and no named-human browser acceptance is
claimed.

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
| Deployment host / census | Defiant / `01 Devices/Defiant RHEL 8.md`; `defiant.home.arpa` |
| Separate attended-acceptance target | NOT REQUIRED — owner waived the redundant host-specific browser check on 2026-09-20 |
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
| Pilot verdict | TECHNICAL RELEASE AND DEPLOYMENT COMPLETE; separate named-human host/browser check WAIVED by owner and not executed |

## Superseded replacement RHEL 8 target assessment — 2026-09-20

Benny initially directed that final alpha.3 attended acceptance use a RHEL 8
host other than Defiant. Caleb performed a read-only assessment in the requested
order and then checked the remaining active RHEL 8 guests. No host met the
complete browser, graphical-access, operator-path and Wazuh requirements
without a package, service, power-state, firewall, listener or authentication
change. This assessment is retained as historical evidence; its setup blocker
and proposed follow-up were superseded when Benny waived the separate
host-specific browser check as unnecessary.

| Candidate | Live state | RHEL / space | Browser and graphical path | Wazuh / operator path | Disposition |
|---|---|---|---|---|---|
| `lab-rhel01` / `10.44.50.31` | Shut off | Offline inspection: RHEL 8.10; about 60 GiB free on root | No Firefox/Chromium, GNOME, GDM, xrdp, xorgxrdp or guest VNC server. Libvirt has an existing localhost-only VNC device, but there is no guest desktop/browser to present | `wazuh-agent` installed; `/home/adm-linux` exists; live service/login state cannot be claimed while off | Best dedicated-role candidate, but not ready. Starting it and adding a browser/desktop requires separate explicit approval |
| `wade-ci` / `10.44.50.10` | Running | RHEL 8.10; 23,827,376 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Wazuh active/enabled; existing `adm-linux` SSH path works | Not ready; CI role should not gain desktop packages for this acceptance |
| `orbit-control` / `10.44.50.20` | Running | RHEL 8.10; 97,959,764 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Wazuh active/enabled; existing jump-host `adm-linux` SSH path works | Not ready; staging control-plane boundary would require new software/services |
| `mcp-control` / `10.44.50.40` | Running | RHEL 8.10; 4,698,636 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Wazuh active/enabled; existing jump-host `adm-linux` SSH path works | Not ready; limited free space and no graphical/browser path |
| `repo01-defiant` / `192.168.1.131` | Running | RHEL 8.10; 79,658,892 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Wazuh active/enabled; existing direct `adm-linux` SSH path works | Not ready; authoritative repository role should remain minimal/headless |
| `siem` / `192.168.1.132` | Running | RHEL 8.10; 163,082,852 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Local Wazuh manager rather than an agent; existing Defiant-jump `adm-linux` SSH path works | Not ready; SIEM role is not an appropriate desktop acceptance host |
| `media-bot` / `192.168.1.102` | Running | RHEL 8.10; 60,763,620 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Wazuh active/enabled; existing direct `adm-linux` SSH path works | Not ready; active media workload should remain minimal/headless |
| `hermes01` / `10.44.50.50` | Running | RHEL 8.10; 4,380,392 KiB free | Headless `multi-user.target`; no supported browser or graphical packages/services | Wazuh active/enabled; existing jump-host `adm-linux` SSH path works | Not ready; agent role, low headroom and no graphical/browser path |

Defiant was deliberately excluded from replacement selection. The other
running guests reported by Defiant's QEMU guest agent were RHEL 9.8, RHEL 10.2
or the OPNsense firewall and were not eligible for this RHEL 8 acceptance gate.

No published alpha.3 asset was copied to a replacement host. No VM was started,
and no package, service, listener, firewall, route, DNS, authentication or Wazuh
configuration changed. Existing SSH and QEMU guest-agent paths were used only
for read-only evidence. PPS and maintained topology therefore have no changed
flow or state.

No replacement setup is authorized or required. `lab-rhel01` remained shut off,
no alternate host received release files, and the candidate matrix requires no
follow-up for alpha.3.

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

## Optional future browser spot-check

A manual browser walkthrough is not an alpha.3 release gate. It may be run later
if an operator reports a browser-specific regression. Any such run should record
the browser version, verify the sidecar before opening the local file, confirm
the About version/fingerprint, exercise `Ctrl+Alt+1` through `Ctrl+Alt+6`, and
observe the console and network panel. This receipt does not claim that optional
work occurred.

## Rollback

Alpha.2 remains intact on Defiant at
`/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/`. Close every alpha.3 browser tab,
verify the alpha.2 sidecar, and open the versioned alpha.2 local file. No daemon
or service needs stopping, and neither version should be overwritten or deleted.

## Jordan handoff state

| Required field | Current state |
|---|---|
| Correction / release | `MCR-A2-KEY-001` corrected in separately versioned, published alpha.3 |
| Release evidence | Tag `e72c235f...`; provenance/main `3f38e8c...`; published asset hashes above |
| Reviewer state | Riley exact-head technical review APPROVE; separate human browser witness waived by owner |
| Deployment state | Complete and integrity-verified on Defiant at `2026-09-20T12:07:53-04:00`; no replacement deployment required |
| Browser/pilot state | Host-specific manual browser run WAIVED; not executed and not claimed |
| Forecast impact | None from acceptance infrastructure; alpha.3 remains published and deployed with automated evidence complete |

`WADE_CLEAR: alpha.3 is published, integrity-verified and deployed. Benny waived the redundant host-specific manual browser check; it was not executed or claimed. No alternate-host setup or follow-up is required.`
