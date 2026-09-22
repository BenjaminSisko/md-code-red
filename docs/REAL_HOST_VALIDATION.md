# Real-Host Validation Matrix

The machine-readable plan is
`content-src/real-host-validation-matrix.json`. It covers read-only identity,
service, journal, firewalld, NetworkManager, package, LVM, SELinux, time and
rsyslog checks on real RHEL 8, 9 and 10 hosts. A run becomes product evidence
only after a named operator capture and an independent reviewer receipt through
the existing workflow in `docs/WORKFLOW.md` Section 2a.

Current state:

- RHEL 8 has nine independently reviewed receipts, so the matrix is partial.
- RHEL 9 has raw flag captures but zero independently reviewed command receipts;
  it is the first priority.
- RHEL 10 has nine independently reviewed receipts, so the matrix is partial.
- RHEL 7 has no real validation host. Product ownership must either provide one
  or formally classify RHEL 7 as legacy/reference-only. The existing UBI7
  extraction container does not answer that decision.

Run `python3 tools/validation_matrix.py report` for the current matrix. The
unit suite runs `python3 tools/validation_matrix.py check` so the recorded
receipt counts cannot drift from `content/commands.json`. The
`probe-local` action only reads the local operating-system identity. It refuses
to count non-RHEL machines as evidence and does not run the matrix commands.

The control workstation is not RHEL and is not counted as host evidence. An
existing authorized SSH profile reached the documented RHEL 8 Defiant host on
2026-09-22, where all 11 read-only matrix cases were attempted: eight returned
zero; firewalld and LVM exposed non-root access limits; and chrony could not
reach its daemon. This was
an operator observation, not an independently reviewed entry receipt, so the
receipt count remains nine. The documented RHEL 9 target timed out and the RHEL
10 target was down; no command ran on either host. Raw host output was not added
to the public repository. Unknown results remain unknown.
