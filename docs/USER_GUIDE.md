# MD CODE RED User Guide

## Core Workflows

### Journey 1: Generate a Command

**TODO:** Fill after QA verifies behavior.

- Open the HTML file
- Select RHEL version (7/8/9/10)
- Search or browse a tool
- Answer guided questions
- Command renders live with explanation
- STIG/NIST badge shows if applicable
- Copy or Export as Evidence

### Journey 2: Build STIG Evidence

**TODO:** Fill after QA verifies behavior.

- Search by STIG ID (e.g., RHEL-09-xxxxxx)
- Check command, fix command, and control mapping display
- Expected output shows for validation
- Export as Evidence → paste into SCTM narrative

### Journey 3: Generate an Ansible Playbook

**TODO:** Fill after QA verifies behavior.

- Choose Ansible → Playbook
- Answer target group and task checkboxes
- Valid YAML renders with task comments
- Copy to jump box, run, verify

## UI Reference

### Version Selector

**TODO:** Fill after QA verifies behavior. Version-specific flags greyed out with tooltip ("Not available in RHEL 7").

### Search

**TODO:** Fill after QA verifies behavior. Full-text across tools, flags, STIG IDs, control numbers, and source citations.

### Export as Evidence

**TODO:** Fill after QA verifies behavior. Output format: command + control + expected output in SCTM-ready style.

### Keyboard Operation

**TODO:** Fill after QA verifies behavior. No mouse required on locked-down boxes.

### Favorites & Recent

**TODO:** Fill after QA verifies behavior. Browser localStorage only; exportable as JSON; never stored server-side.

### Print View

**TODO:** Fill after QA verifies behavior. Optimized for binders and SOPs.

### Dark/Light Mode

**TODO:** Fill after QA verifies behavior. Toggle in header; persisted per session.

## Troubleshooting

**TODO:** Fill after QA verifies behavior. Common issues, workarounds, and when to escalate to the RHEL SME.

**Version mismatch:** Confirm RHEL version in header. Commands tagged "Not in RHEL 7" will not render.

**Copy button inactive:** Fill all required fields (marked with red border).

**Dangerous operations warning:** Confirms before copying `rm -rf`, `wipefs`, `lvremove`, `dnf remove` commands.
