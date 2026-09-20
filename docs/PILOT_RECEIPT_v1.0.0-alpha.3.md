---
type: deploy-receipt
status: pending-human-acceptance
last_verified: 2026-09-20
---

# Pilot Receipt -- v1.0.0-alpha.3

This receipt records the exact published alpha.3 release assets deployed
read-only on Defiant. Benny later directed that final attended acceptance use
a different RHEL 8 host. Defiant is therefore retained as historical deployment
evidence and rollback context, not the active acceptance target. No replacement
host is currently ready, no browser was opened, no named human used the
artifact, and no pilot or operational acceptance is claimed.

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
| Historical deployment host / census | Defiant / `01 Devices/Defiant RHEL 8.md`; `defiant.home.arpa` |
| Active attended-acceptance target | UNASSIGNED — Benny directed use of another RHEL 8 host; the 2026-09-20 live candidate assessment found no ready replacement |
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
| Pilot verdict | HOLD pending an approved replacement RHEL 8 target, deployment there, named-human browser use and Riley's attended acceptance witness |

## Replacement RHEL 8 target assessment — 2026-09-20

Benny directed that final alpha.3 attended acceptance use a RHEL 8 host other
than Defiant. Caleb performed a read-only assessment in the requested order and
then checked the remaining active RHEL 8 guests. No host met the complete
browser, graphical-access, operator-path and Wazuh requirements without a
package, service, power-state, firewall, listener or authentication change.

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

The least-invasive approval-required setup plan is to use `lab-rhel01`: approve
its start, revalidate live RHEL/Wazuh/login/storage state, approve only the
minimum repo01-backed graphical and Firefox packages needed for the existing
localhost-only libvirt VNC console, and avoid xrdp, new listeners, firewall
rules and new authentication paths. Deployment of the published triplet may
proceed only after that prerequisite change is separately approved, executed
and verified.

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
2. Confirm the receiving host is the separately approved replacement RHEL 8
   target. Do not use Defiant for final attended acceptance.
3. Re-run the exact alpha.3 sidecar check from the final replacement-host
   directory and
   stop unless it returns `OK`.
4. Open the exact local alpha.3 `file://` path in the approved browser session.
5. Confirm About shows `v1.0.0-alpha.3` and fingerprint
   `9829c043fb20ef8e2cdf1476a9769f605db19a2161e8fbff7903a226ed6361ea`.
6. Exercise `Ctrl+Alt+1` through `Ctrl+Alt+6`, confirming each shortcut selects
   and focuses its advertised rail, especially `Ctrl+Alt+6` for About.
7. Complete the Pilot SOP's command, search, evidence-export,
   favorites/recent, theme, print and keyboard-only smoke paths without
   executing a generated system command.
8. Record the browser console and DevTools Network results. Acceptance requires
   zero remote application requests from the local-file workflow.
9. If any identity, sidecar, keyboard, console, network or workflow check
   fails, close alpha.3 and return to the verified replacement-host rollback
   artifact. Defiant's alpha.2 remains historical deployment rollback evidence,
   not the active acceptance host.

## Rollback

Defiant's alpha.2 remains intact at
`/home/adm-linux/MD-CODE-RED/v1.0.0-alpha.2/`. Close every alpha.3 browser tab,
verify the alpha.2 sidecar, and open the versioned alpha.2 local file. No daemon
or service needs stopping, and neither version should be overwritten or deleted.
This is historical rollback evidence for Defiant. A replacement host must have
its own versioned rollback-safe placement before attended acceptance begins.

## Jordan handoff state

| Required field | Current state |
|---|---|
| Correction / release | `MCR-A2-KEY-001` corrected in separately versioned, published alpha.3 |
| Release evidence | Tag `e72c235f...`; provenance/main `3f38e8c...`; published asset hashes above |
| Reviewer state | Riley exact-head technical review APPROVE; receiving-host human witness pending |
| Deployment state | Historical deployment complete and integrity-verified on Defiant at `2026-09-20T12:07:53-04:00`; replacement-host deployment not started |
| Browser/pilot state | HOLD; active target unassigned; no browser, named-human or operational acceptance claimed |
| Forecast impact | Replacement-target readiness is now an additional prerequisite before named-human browser evidence and Riley's attended witness |

`WADE_BLOCKED: alpha.3 is published and historically deployed on Defiant, but Benny requires final acceptance on another RHEL 8 host and no assessed replacement is currently browser/graphical ready without separately approved host changes. Replacement deployment, named-human browser use, About identity readback, live zero-network/console evidence, operator checks and Riley Park's attended acceptance witness remain pending.`
