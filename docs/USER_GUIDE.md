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

No mouse is required. Every binding below comes from one table in the app script (`KEYMAP`) read by
one delegated `keydown` listener, so what this page says and what the tool does cannot drift apart
without the table changing.

| Action | Binding | Notes |
|---|---|---|
| Open the command palette | `/` | Only when the focus is not already in a text field, so typing a slash into a form still types a slash. |
| Open the command palette from anywhere | `Ctrl+K` / `Cmd+K` | Works while typing. |
| Close the palette | `Esc` | |
| Move through palette results | `↑` / `↓` | Wraps at both ends. |
| Open the selected palette result | `Enter` | A tool opens its command list; a command loads into the editor. |
| Toggle the sidebar | `Ctrl+B` | |
| Toggle the inspector | `Ctrl+I` | |
| Toggle dark / light theme | `Ctrl+Shift+L` | Also the **Theme** button at the right of the status bar. The choice is kept for the session only. |
| Jump to a rail section | `Ctrl+Alt+1` … `Ctrl+Alt+5` | Command Builder, STIG Search, Ansible, Favorites, About — in rail order, top to bottom. Focus moves to the rail button. |
| Copy the command with its comment header | `Ctrl+Shift+C` | Blocked while a red-blast command is unreviewed, exactly as the button is. |
| Move within any list (tools, commands, palette) | `↑` / `↓` | |
| Activate the focused control | `Enter` or `Space` | Standard control behaviour; nothing is rebound. |
| Focus an editor line and pin its explanation | `Enter` or `Space` on a gutter line | Gutter lines are `role="button"`, `tabindex="0"`. |
| Move anywhere else | `Tab` / `Shift+Tab` | Focus order: rail → sidebar (version selector first) → editor toolbar → gutter lines → inspector → status-bar theme button. The palette traps focus until `Esc`. |
| Print | `Ctrl+P` / `Cmd+P` | Browser-native. The print stylesheet drops the rail, sidebar, inspector and status bar. |

Every focusable control shows a visible focus ring; no rule in the stylesheet removes an outline
without replacing it. The rail buttons are icon-only by design, and each reveals its text label on
focus as well as on hover, so a keyboard user reads the same word a mouse user does.

**Not yet bound.** `Ctrl+E` (Export as Evidence) is reserved and deliberately unbound until the
evidence exporter ships (CR-T-28) — a key that appears to work and does nothing is worse than a key
that is documented as not landing yet.

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
