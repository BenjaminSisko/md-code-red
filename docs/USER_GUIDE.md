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

1. Press `/` (or `Ctrl+K`/`Cmd+K`) and type a STIG ID (e.g. `RHEL-08-010000`), a CCI (`CCI-000366`),
   or a NIST control (`AC-6`). Results are grouped by kind (Tool, Command, STIG, Flag, CCI, NIST).
2. Press `Enter` or click a **STIG** result. If a command in this build's catalog is linked to that
   rule, it opens directly with the command assembled; otherwise the rule opens on its own — the
   Inspector still shows the full panel, and the editor says plainly that no command is catalogued
   for it yet. A CCI or NIST result resolves to the first embedded rule that cites it, current RHEL
   version first.
3. The Inspector's STIG panel shows the STIG ID, Category, every cited CCI, the CCI → NIST SP 800-53
   crosswalk, the rule title, and **Check text** / **Fix text** as expandable sections (verbatim DISA
   text). A RHEL 7 rule also carries the sunset banner; an entry whose command changed between
   releases carries its "changed in RHEL X" note above the panel.
4. If a capture has been recorded for that STIG ID/RHEL version pair, the expected compliant output
   shows under **Expected compliant output (captured)**. Until then the panel says so honestly — "No
   capture yet" — rather than inventing one.
5. Click **Export as Evidence** (or `Ctrl+E`) for the SCTM-ready plain-text block — see below.

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

The command palette (`/` or `Ctrl+K`/`Cmd+K`) searches a lazily built, typed index over tools,
command intents, curated flags, the per-release flag dictionaries, every embedded STIG rule ID and
title, every cited CCI, and every mapped NIST SP 800-53 control — built once, on the first keystroke
(never at boot), and reused for the rest of the session. Results are grouped by kind (Tool, Command,
STIG, Flag, CCI, NIST) in that order, each group capped so one large family cannot crowd the others
off screen. A query with no possible match says so explicitly — "No matches for *x*. Try a tool name
such as …" — rather than showing an empty list with no explanation. On this build's full embedded
dataset (roughly 4,000 indexed records), both building the index and answering a query measure well
under 100 ms (`tests/test_search_index.js`, run in CI via `tests/test_search_index.py`).

### Export as Evidence

`Ctrl+E`, or the **Export as Evidence** button in the command toolbar, opens a plain-text, SCTM-ready
block in a modal: tool version and build date, the content fingerprint (sha256 of the embedded data
island, defined below), STIG ID, STIG version and benchmark date, rule title, CAT, every cited CCI,
the mapped NIST SP 800-53 controls, check text, fix text, expected output (or an honest "not captured
yet" line), the assembled command exactly as rendered with its flags, the source citation, capture
metadata when a capture exists (host, OS release, kernel, capture date), and the operator's own date
line. The preview shown is byte-for-byte what **Copy evidence text** puts on the clipboard — nothing
is recomputed between the two. Two exports of the same entry are identical except that one line
(`tests/test_evidence_export.js`). The command and its flags are read from the same rendered result
the screen and the ordinary Copy button already use — the exporter never re-assembles the command
itself.

**Content fingerprint.** A sha256 hash of the exact bytes inside this file's embedded data island,
computed by `build.py` at build time and printed both in the file's own header comment and in the
About panel, so an operator can quote it offline with no way to compare the file against anything
else. `qa.py`'s Q1 gate independently re-hashes the shipped island and fails the build if it does not
match the embedded constant.

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
| Export as Evidence | `Ctrl+E` | Opens the evidence preview modal; `Esc` closes it (and closes the palette first if both would otherwise apply). |
| Move within any list (tools, commands, palette) | `↑` / `↓` | |
| Activate the focused control | `Enter` or `Space` | Standard control behaviour; nothing is rebound. |
| Focus an editor line and pin its explanation | `Enter` or `Space` on a gutter line | Gutter lines are `role="button"`, `tabindex="0"`. |
| Move anywhere else | `Tab` / `Shift+Tab` | Focus order: rail → sidebar (version selector first) → editor toolbar → gutter lines → inspector → status-bar theme button. The palette traps focus until `Esc`. |
| Print | `Ctrl+P` / `Cmd+P` | Browser-native. The print stylesheet drops the rail, sidebar, inspector and status bar. |

Every focusable control shows a visible focus ring; no rule in the stylesheet removes an outline
without replacing it. The rail buttons are icon-only by design, and each reveals its text label on
focus as well as on hover, so a keyboard user reads the same word a mouse user does.

### Favorites & Recent

Every command entry's toolbar carries a **Favorite** / **Favorited** toggle. The **Favorites** rail
(`Ctrl+Alt+4`) lists favorited entries and, below them, the entries opened most recently this
session, newest first. Selecting either jumps straight back to the Command Builder rail with that
entry loaded.

Only entry IDs are ever written to `localStorage` (namespaced `mdcr.v1.`, schema-versioned like every
other stored value) — never the entry's text. Every ID read back out of storage is checked against
the live content island before it is trusted (`sanitizeIdList()`, `tests/test_favorites_store.js`);
an ID that does not resolve — from an older build, or from anything that is not a plain, short ID
string — is silently dropped rather than rendered blank or as raw stored text. There is no
favorites/recent export to a file; both lists are per-browser and never leave `localStorage`.

### Print View

`Ctrl+P` / `Cmd+P` prints the current command and, when the selection carries one, its full STIG
panel — check text, fix text, CCI/NIST crosswalk, sunset banner and "changed in RHEL X" note included
— with the rail, sidebar, inspector, status bar and any open overlay dropped. Nothing else loads: the
printed page draws from the same single-file, zero-network artifact as the screen.

### Dark/Light Mode

**TODO:** Fill after QA verifies behavior. Toggle in header; persisted per session.

### About Panel

The **About** rail (`Ctrl+Alt+5`) shows the tool's version and build date, the content fingerprint,
every embedded STIG release with its version, benchmark date and rule count (and a sunset marker for
RHEL 7), the embedded source families with their license classes, and the required attribution block
from SALM's Content Licensing Ruling v1, reproduced verbatim.

## Troubleshooting

**TODO:** Fill after QA verifies behavior. Common issues, workarounds, and when to escalate to the RHEL SME.

**Version mismatch:** Confirm RHEL version in header. Commands tagged "Not in RHEL 7" will not render.

**Copy button inactive:** Fill all required fields (marked with red border).

**Dangerous operations warning:** Confirms before copying `rm -rf`, `wipefs`, `lvremove`, `dnf remove` commands.
