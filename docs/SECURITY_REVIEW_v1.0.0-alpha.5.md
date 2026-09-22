---
type: release-evidence
status: candidate
last_verified: 2026-09-22
---

# Security Review -- v1.0.0-alpha.5

The release keeps the offline single-file architecture, deny-network CSP,
closed generator grammars, output escaping, dangerous-pattern detection, and
red-operation copy acknowledgement. Q2, Q17-Q19, Q21, Q22, Q24-Q26, the full
unit suite, hostile-input harness, and Gitleaks all pass.

This candidate strengthens operational safety:

- Firewalld recovery removes the exact original rich rule in the explicit zone
  and verifies permanent and runtime state.
- NetworkManager, packages, systemd, cron, LVM, and generated configuration
  recover from recorded pre-state instead of a guessed opposite action.
- Storage and management-network workflows require stronger device, backup,
  recovery-access, and review checks.
- Instructional copy fails closed when a plan contains an unresolved
  placeholder.
- Execution receipts bind actual output and operator/target metadata to the
  exact command, artifact hash, and content fingerprint.
- Release-signing tooling refuses to choose a key and requires the complete
  approved fingerprint, a valid detached signature, and matching file hashes.

Known limits remain visible. The candidate is unsigned because no authorized
publisher signing identity is provisioned. RHEL 7 has no real-host evidence;
RHEL 9 has zero independently reviewed command receipts; RHEL 8 and 10 remain
partial at nine receipts each. The browser command/control reference is not an
execution receipt. These limits prevent claims of publisher authentication or
unsupervised production validation.

Independent exact-head review is required after the candidate commit. Any
change to that head invalidates the review and requires it to be repeated.
