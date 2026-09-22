---
type: release-evidence
status: released
last_verified: 2026-09-22
---

# Release Report -- v1.0.0-alpha.5

This release incorporates the Linux administrator and instructor review of
alpha.4. It corrects unsafe or incomplete recovery guidance and adds the
instructional and evidence controls needed to use the catalog as a supervised
learning and change-preparation tool.

| Release fact | Released value |
|---|---|
| Version / date | `v1.0.0-alpha.5` / 2026-09-22 |
| Artifact | `dist/md-code-red_v1.0.0-alpha.5.html`; 8,892,535 bytes |
| Artifact SHA-256 | `c64337a2aee3c494171bc9b6f7bb89a0b1006992fc26c7fbe8793579cd8ada7a` |
| Content fingerprint | `41fb7c1e59cc32805fa06a240aca2913e16acb496689c2de0ec9dff598b34c91` |
| Tag target | `e2991029e2f6db6c60db57626f4f6bf24b950d27` (reviewed PR #16 merge) |
| Provenance | Stamped with the tag target; SHA-256 `309739bd1e4767e8a33e9ff25b17cfe991c50f1cd1f2ff6fbf68a04d1056430f` |
| Signing | Unsigned; no authorized publisher key is provisioned |
| Verification | Q1-Q26 + JS; 402 unit tests; 122,313 hostile checks; Gitleaks clean |

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
