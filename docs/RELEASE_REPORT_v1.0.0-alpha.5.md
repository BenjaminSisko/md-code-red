---
type: release-evidence
status: candidate
last_verified: 2026-09-22
---

# Release Report -- v1.0.0-alpha.5

This candidate incorporates the Linux administrator and instructor review of
alpha.4. It corrects unsafe or incomplete recovery guidance and adds the
instructional and evidence controls needed to use the catalog as a supervised
learning and change-preparation tool.

| Release fact | Candidate value |
|---|---|
| Version / date | `v1.0.0-alpha.5` / 2026-09-22 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.5.html`; 8,891,476 bytes |
| Artifact SHA-256 | `334dc3f5f094e1e14ef300a519cba273082213b708ed650d3af62f48bd1ae554` |
| Content fingerprint | `f5a709078b6eb96e130937282116e10788825cdb4e3c4ea687d3ffb41b52629a` |
| Provenance | Placeholder until the reviewed merge SHA exists |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 399 unit tests; 122,313 hostile checks; Gitleaks clean |

The release adds or changes:

- Exact, state-aware recovery for firewalld, NetworkManager, package,
  systemd, LVM, cron, and generated-configuration operations.
- Privilege metadata on 37 of 199 entries and explanations for every option or
  subcommand used by a yellow/red static entry.
- Structured prerequisites and value-bound Preflight, Run, Verify, and Recover
  plans for all generators.
- Field-level teaching, Start Here paths, RHEL comparison, man-page guidance,
  a working STIG search action, and nine RHEL troubleshooting trees.
- A clearly named command/control reference export, a separate formal execution
  receipt, a tracked real-host matrix, generated release facts, and fail-closed
  signing support.

Publication does not establish deployment or browser acceptance. RHEL 7 still
needs a product decision or a real host; RHEL 9 needs reviewed receipts; RHEL 8
and 10 remain partially verified. The release must remain labeled lab-only and
unsigned. The tag must target the reviewed merge exactly and the post-merge
provenance stamp must name that target.
