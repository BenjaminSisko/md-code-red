---
type: user-guide
status: current
last_verified: 2026-09-22
---

# MD CODE RED User Guide

MD CODE RED is one HTML file. Double-click it (or open it from your browser's File
menu) and it runs -- no install, no server, no network call of any kind. This guide
describes what the development build (`dist/md-code-red_v1.0.0-alpha.6-dev.html`, 199 curated
command entries, 102 tools, and 14,439 mined reference commands) actually does,
verified against the running artifact and the QA
gates, not against the original product brief. Where the brief promised something
this build does not yet do, that is called out plainly rather than described as if
it worked.

## Core Workflows

### Journey 1: Generate a command with a guided form

The catalog includes 43 **guided form generators** -- you fill in
a small set of fields and watch the exact command assemble as you type. Walkthrough,
using the real `journalctl` entry:

1. Open the file. The **Command Builder** rail item is selected by default
   (`Ctrl+Alt+1`), and RHEL 9 is the starting version.
2. In the sidebar's **Tools** list, click **journalctl / systemd-journald**. Its one
   catalogued command, "Read the systemd journal, filtered by unit, minimum priority
   and time window," appears underneath, tagged **guided form**.
3. Click it. The editor splits into a **Fields** panel and the assembled-command
   panel below it. All four fields on this entry (`unit`, `priority`, `since`,
   `thisboot`) are optional, so a command renders immediately with nothing typed:
   `journalctl --no-pager`, blast **green**.
4. Type into the fields -- `unit: sshd.service`, choose `priority: err` from its
   dropdown (the field is a closed set: emerg/alert/crit/err/warning/notice/info/
   debug), `since: today`, and choose `thisboot: yes`. The command panel updates on
   every keystroke, never the field inputs themselves, so you never lose your place
   mid-word:
   `journalctl --no-pager --unit='sshd.service' --priority='err' --since='today' --boot`
5. The **Inspector** panel on the right lists every flag the command actually shows,
   in order, each with its explanation or the honest `unverified -- see man page`
   line when no curated explanation exists yet (see Known Limitations -- for this
   build, that is every flag on every generator entry).
6. Click **Copy** to put the plain command on the clipboard, or **Copy with
   comment** (`Ctrl+Shift+C`) to prepend a `#`-prefixed header (tool/version,
   intent, any STIG/CCI rows, blast level) -- see "Copy vs. Copy with comment"
   below. A field left invalid (wrong shape for its type) is refused with a plain-
   English reason under **Fill in the required fields**; nothing partial is ever
   rendered as if it were complete.

A further 156 entries are **static** checks, including
`firewalld-service-active`, `ctrl-alt-del-target-masked`, and
`journald-service-active`. Static checks have no form: pick the tool, pick the
command, and the version-specific command renders directly.

### Journey 1b: Build a pipeline

Real work is rarely one command. The **Pipeline** panel, under the assembled
command, joins several of them into one shell line -- and it does it without ever
letting you type an operator.

**Why there is no text box for the `|`.** A pipe, a `&&`, a `>` are exactly the
characters this tool refuses everywhere else: every field you fill in is
single-quoted before it reaches a command, precisely so that a `|` you type stays
a literal `|` and never becomes a pipe. If the composer let you type an operator,
that guarantee would be gone the moment anything stripped the quotes. So the
operator is not something you supply. You pick one from a fixed list of ten, and
the tool writes it:

| You pick | It writes | It means |
|---|---|---|
| pipe | `\|` | send this command's output into the next one |
| and | `&&` | run the next one only if this one succeeds |
| or | `\|\|` | run the next one only if this one fails |
| then | `;` | run the next one either way |
| write to a file | `>` | write output to a file, replacing it |
| append to a file | `>>` | add output to the end of a file |
| write errors to a file | `2>` | send error output to a file |
| errors with output | `2>&1` | send errors wherever output is going |
| tee | `\| tee` | write output to a file AND keep it flowing |
| tee (append) | `\| tee -a` | add to a file AND keep it flowing |

**Walkthrough.**

1. Build a first command the ordinary way (Journey 1). With the `journalctl`
   generator and `unit: sshd.service`, that is
   `journalctl --no-pager --unit='sshd.service'`.
2. In the **Pipeline** panel, click **Add to pipeline**. It becomes **Stage 1**,
   marked *editing* -- the fields above still belong to it, so typing keeps
   editing that stage.
3. Pick the next command from the sidebar as usual, fill its fields, and click
   **Add current command as a stage**. It arrives as **Stage 2**, joined by a
   pipe. Change the join with the **joined by** dropdown on that stage.
4. Or click **Add a redirection** for a stage that is a file rather than a
   command: choose `>`, `>>`, `2>`, `| tee` or `| tee -a` and type the path in
   the **file** box. The path is validated like any other field -- it is not
   free text, and it is quoted in the command.
5. The assembled line above updates as you go:
   `journalctl --no-pager --unit='sshd.service' | tee '/srv/audit/sshd.log'`.
   **Copy**, **Copy with comment** and **Export command and control reference** all now act on the
   WHOLE pipeline; the comment header and the evidence export name every stage,
   its operator, its rating and its citation.

**When nothing assembles, read the stage.** A pipeline that is not finished
produces no command at all -- nothing partial is ever shown as if it were
complete. The panel names the ONE stage that is wrong and why: *"stage 2: the
file to write: no value"*, *"stage 3: still needed: unit"*. Fix that stage and
the line appears.

**What the composer will not build, and why.**

* **Only a guided form can be a stage.** A reference command is a quoted vendor
  string. Joining two of those produces a command the vendor never published
  while the citation still says they did -- so a reference entry is refused as a
  stage by construction, and the panel says so rather than hiding the button.
* **No stage may hand its argument to another interpreter.** `su -c`, `sh -c`,
  `sudo`, `timeout`, `find -exec` and the rest re-parse what you give them,
  which is a second set of quoting rules this tool does not claim to know. It
  refuses those shapes outright instead of guessing at them.
* **No pipeline ends in a shell.** `| sh`, `| bash`, `| python`, an `xargs`
  whose child is one of those, and a write into a directory the system later
  executes (`> /etc/cron.d/...`, `| tee /etc/profile.d/...`) are all refused.
  They all mean the same thing: a command whose text only exists at run time,
  which cannot be read, rated, cited or undone. A red banner over something
  unreviewable would just teach you to click through red.
* **Eight stages, maximum.** Not a technical limit -- a refusal to render
  something nobody will read before running it as root.

**Ratings, when a pipeline writes.** A pipeline is not rated as the worst of its
stages. A write outside a scratch path (`/tmp`, `/var/tmp`, `/home`, `/root`) is
a write and rates at least **yellow**; a target under `/etc`, `/boot`, `/dev`,
`/usr`, `/var/lib`, `/sys` or `/proc` is **red**; `| xargs rm` and friends are
**red** whatever the arguments say. A target in none of those lists shows as
**unrated** -- not green. Green in this tool means a person curated that entry
and said so; a path nobody has ever classified is unclassified, not safe, and
you are entitled to see the difference.

### Journey 2: Build STIG evidence for an audit package

1. Press `/` (when focus is not already in a text field) or `Ctrl+K` / `Cmd+K`
   (works from anywhere, including while typing) to open the command palette, and
   type a STIG ID (`RHEL-08-010000`), a CCI (`CCI-000366`), or a NIST control
   (`AC-6`). Results are grouped, in this order: Tool, Command, STIG, Flag, CCI,
   NIST -- each group capped so one large family cannot crowd the others off
   screen.
2. Press `Enter` or click a result. A **STIG** hit opens the rule directly: if a
   command in this build's catalog is linked to it, the command assembles and the
   Inspector shows the full panel; otherwise the rule opens on its own -- the panel
   still renders in full, and the editor says plainly that no command is catalogued
   for it yet. A **CCI** or **NIST** hit resolves to the first embedded rule that
   cites it, current RHEL version searched first, then the other three.
3. The Inspector's STIG panel (also mirrored below the command for printing) shows
   the STIG ID and Category badge, every cited CCI as its own badge, the CCI to
   NIST SP 800-53 crosswalk, the rule title, and **Check text** / **Fix text** as
   expandable `<details>` sections carrying the verbatim DISA text. A RHEL 7 rule
   also carries a sunset banner ("RHEL 7 STIG V3R15 is SUNSET at DISA -- a terminal
   release, no further updates expected"); an entry whose command changed between
   releases carries its own "Changed in RHEL X: ..." note above the panel.
4. If a capture has been recorded for that exact STIG ID / RHEL version pair, the
   panel shows **Expected compliant output (captured)**, open by default. Until
   then it says so honestly -- **No capture yet** -- rather than inventing one. In
   this build only 5 STIG ID/version pairs carry a capture at all (see Known
   Limitations).
5. Click **Export command and control reference** (or `Ctrl+E`) for a deterministic **command and
   control reference**. It contains expected content, not proof of execution.
   To bind an actual run, target, operator, exit code and observed output to the
   artifact, use the separate receipt format in `docs/EXECUTION_EVIDENCE.md`.

### Journey 3: Review a state-changing command before you copy it

Every assembled command carries a blast rating -- **green** (read-only), **yellow**
(a reversible state change), or **red** (destructive, confirmation required) -- shown
in the muted line under the command's title (`tool . RHEL N . blast <level>`).
Of the 43 guided entries, 28 are yellow (add a user, merge or rebase Git history,
extend a logical volume, write a privileged configuration, and so on), 13 are green, and two
are red. The red `pvcreate` and `vgcreate` forms write LVM metadata to a selected
block device, so the confirmation flow below is visible for real catalog content.

1. A yellow rating is informational only: it does not block **Copy** or **Copy with
   comment**, and there is no checkbox to tick. Read the muted blast line and the
   entry's own **Verify** / **Undo** lines (printed under the command) before you
   run anything that changes host state.
2. A red rating (from an entry's own content, or from the destructive-pattern table
   matching the assembled command -- `rm -rf`, `wipefs`, `lvremove`, `pvcreate`,
   `vgcreate`, `dnf remove`, and the rest of `content/dangerous.json`'s fifteen
   rows) opens a red bordered
   banner above the command: **"Destructive operation -- review before running,"**
   naming which pattern matched and why. **Copy** and **Copy with comment** are
   both disabled (`aria-disabled`, with a tooltip saying so) until you tick **"I
   have reviewed this command."** The banner is evaluated over the *entire*
   clipboard payload, including the comment header, not just the command line --
   so a destructive word hidden only in a comment header still trips it.
3. **Favorite** the entry (toolbar button, or from the Favorites rail once opened)
   if you expect to come back to it; see "Favorites & Recent" below.

**Ansible and Git generators.** The **Ansible** rail (`Ctrl+Alt+3`) contains
guided playbook, inventory, and `ansible.cfg` builders. The playbook form always
creates the requested package task and provides two optional task checkboxes:
**Refresh DNF package metadata first** and **Start and enable the same-named
service**. The service checkbox deliberately uses the package name as the unit
name; leave it unchecked when those names differ. Every typed YAML scalar is
quoted, the two checkbox choices only add complete curated YAML blocks, and the
offered `ansible-playbook` invocation keeps `--check --diff` so it reports the
proposed changes without applying them. The **Git** rail
(`Ctrl+Alt+4`) contains the curated Git reference entries plus eight guided
forms: clone, create a branch, merge, rebase, create an annotated tag, inspect a
bounded log, start a bisect, and recover a lost commit by creating a branch at
its revision. Branch and tag fields reject invalid ref shapes; revision fields
accept conservative commit expressions such as `main`, `origin/main`, `HEAD~1`,
and `HEAD@{1}`. Git values remain single shell-quoted operands in the assembled
command.

## UI Reference

### RHEL Version Selector and verification status

The sidebar's version segmented control (RHEL 7 / 8 / 9 / 10) switches the whole
app's context. A tool or command not offered on the selected release stays on
screen, disabled, with its reason and (when one exists) its alternative shown in a
`.why` line -- gated, never hidden, so you always know a tool exists even when this
release cannot offer it (RHEL 7 has no `dnf` or `podman`, for example; the entries
say so and point at `yum` as the alternative for package management).

Every command entry's per-version verification is one of three states, shown as a
badge in the Inspector, the status bar, and the evidence export -- read from one
function (`verificationStatusForVersion()`) so the three places can never disagree:

| Badge | Meaning | What backs it |
|---|---|---|
| **Verified** (green badge) | "verified by NAME on DATE (HOST)" | A real `{by, on, host, capture}` receipt sits on this exact RHEL version. QA (Riley Park, in this build) independently reviewed the SME's capture and wrote the receipt. Never inherited from a `same_as` target -- a version whose row only points at another version was never independently run, and can never carry its own receipt. |
| **Captured** (amber badge) | "captured, awaiting QA" | A capture exists for this exact STIG ID/version pair but no QA receipt has been written yet. **No entry in this shipped build is currently in this state** -- every capture Caleb Stone ran was already cleared by Riley Park's review, so this badge is implemented and tested but not currently observable in the UI. |
| **Not host-verified** (grey badge) | "not host-verified" | Neither of the above. This is the default and the honest majority case: only 18 guided-entry/release pairs carry verified receipts in this build; the newly added Git forms are documented and test-covered but have no host-verification receipt. |

A version whose command is a `same_as` pointer at another version (for example RHEL
9 often reuses RHEL 8's command text) shows **Not host-verified** even when the text
is identical to a verified version's -- the command was never independently run on
that release.

### Search

The command palette (`/` or `Ctrl+K`/`Cmd+K`) searches a lazily built, typed index
over tools, command intents, curated flags, the per-release flag dictionaries, every
embedded STIG rule ID and title, every cited CCI, and every mapped NIST SP 800-53
control -- built once, on the first keystroke that reaches the palette (never at
boot), and reused for the rest of the session. Results are grouped by kind (Tool,
Command, STIG, Flag, CCI, NIST) in that order, each group capped at 8 so one large
family cannot crowd the others off screen. A query with no possible match says so
explicitly -- "No matches for *x*. Try a tool name such as ..." -- rather than
showing an empty list with no explanation. On this build's full embedded dataset
(roughly 4,000 indexed records), both building the index and answering a query
measure well under 100 ms (`tests/test_search_index.js`, run in CI via
`tests/test_search_index.py`).

### Copy vs. Copy with comment

**Copy** puts the assembled command on the clipboard exactly as shown, nothing
else. **Copy with comment** (`Ctrl+Shift+C`) prepends a `#`-prefixed header, one
line per fact, rendered on screen in a read-only preview directly above the button
row (labeled "Copy with comment -- exactly what reaches the clipboard") so what you
see is byte-for-byte what lands on the clipboard:

```
# MD CODE RED v1.0.0-alpha.6-dev -- RHEL 8
# intent: <the entry's one-line intent text>
# STIG: RHEL-08-XXXXXX (CAT II)  NIST: AC-6, CM-6
# blast: yellow
<the assembled command, not comment-prefixed>
```

Every header line is rendered, escaped, and forced single-line before it is
assembled -- a newline embedded in curated `intent`/`verify`/`undo` text cannot put
an unrendered second command on the clipboard. The command is the only line in the
payload that is not `#`-prefixed; if the command itself cannot be rendered as safe
single-line text, the whole copy is refused rather than silently dropping the
comment.

### Export command and control reference

`Ctrl+E`, or the **Export command and control reference** button in the command toolbar, opens a
plain-text command and control reference in a modal. The preview shown is
byte-for-byte what
**Copy evidence text** puts on the clipboard -- nothing is recomputed between the
two. The block, in order:

This reference can support preparation of an SCTM or assessment package, but it
does not contain actual execution output, an exit code or operator attestation
and therefore is not proof that the command ran. Use
`docs/EXECUTION_EVIDENCE.md` for a bound execution receipt.

1. Header line, tool version and build date.
2. **Content fingerprint** (see below).
3. **Verified (RHEL N): <status text>** -- the same three-state text described
   above, for the exported version only.
4. When a STIG row applies: STIG ID; STIG version and benchmark date; rule title;
   CAT; every cited CCI; the mapped NIST SP 800-53 controls; Check text and Fix
   text verbatim; then either the captured output, compliance result (yes/no/not
   recorded), capture host, release, kernel and capture date, or the honest line
   "Expected output: not captured yet -- no capture record exists for this STIG
   ID/RHEL version pair."
5. The assembled command for the exported RHEL version and its blast level, a
   `Requires: root` line when the entry declares one (currently only
   `gen-sshd-test-config`), and every flag the command shows with its explanation
   or `unverified -- see man page`.
6. The source citation (title, version, retrieval date), or "Source citation: not
   recorded on this entry."
7. The operator's own date line (today's date, taken from the browser clock at
   export time -- there is no server to disagree with it).

**Content fingerprint, and how to check it offline.** The fingerprint is the sha256
hash of the exact bytes inside this file's own `<script id="mcr-data">` element (the
embedded JSON data island), computed by `build.py` at build time and printed both
in the file's own header comment and in the About panel. It exists because the tool
is air-gapped: there is nowhere to look the content up to compare it against. What
it actually proves is narrower than "this content is correct" -- it proves **this
evidence export came from this exact file**. To check it: open the same file's
**About** panel (`Ctrl+Alt+7`) and compare its "Content fingerprint" line,
character for character, against the one printed at the top of the evidence export.
They are read from one constant (`CONTENT_FINGERPRINT`), so inside one file they can
never disagree. **If they do not match**, the evidence text did not come from the
copy of the file you have open -- it may have been exported from an older or newer
build, or edited after export. Re-open the evidence from the file you actually have
in hand and re-export it; do not attach an evidence block whose fingerprint you
cannot match to the file that produced it.

### Keyboard Operation

The activity rail now begins with a visible **Search all** button. It opens the
same typed command palette as `/` or `Ctrl+K` / `Cmd+K`, so mouse and touch users
do not need to discover a shortcut first. The status bar includes **Navigator**
and **Inspector** buttons; their highlighted pressed state means the panel is
open. Below 720 pixels the activity rail stays at the top and scrolls sideways,
while the navigator, command workspace, inspector, and status appear in that
reading order. Keyboard users can press `Tab` once from the top of the document
to reveal **Skip to command workspace**.

No mouse is required. Every binding below comes from one table in the app script
(`KEYMAP`) read by one delegated `keydown` listener, so what this page says and what
the tool does cannot drift apart without the table changing.

| Action | Binding | Notes |
|---|---|---|
| Open the command palette | `/` | Only when focus is not already in a text field, so typing a slash into a form still types a slash. |
| Open the command palette from anywhere | `Ctrl+K` / `Cmd+K` | Works while typing. |
| Close the palette, or the evidence export panel | `Esc` | If the evidence modal is open, `Esc` closes that first. |
| Toggle the sidebar | `Ctrl+B` | |
| Toggle the inspector | `Ctrl+I` | |
| Toggle dark / light theme | `Ctrl+Shift+L` | Also the **Theme** button at the right of the status bar. The choice is kept for the browser session only (`sessionStorage`), not across a fresh open of the file. |
| Command Builder | `Ctrl+Alt+1` | Opens the guided command builder and focuses its rail button. |
| STIG and Evidence Search | `Ctrl+Alt+2` | Opens STIG and evidence search and focuses its rail button. |
| Ansible Generator | `Ctrl+Alt+3` | Opens the Ansible generator and focuses its rail button. |
| Git Command Generator | `Ctrl+Alt+4` | Opens the curated Git catalog and its eight guided scenarios, and focuses its rail button. |
| Favorites and Recent | `Ctrl+Alt+5` | Opens saved and recently used entries and focuses its rail button. |
| Reference Commands | `Ctrl+Alt+6` | Opens the mined reference-command catalog and focuses its rail button. |
| About | `Ctrl+Alt+7` | Opens version, fingerprint, provenance, and licensing details and focuses its rail button. |
| Copy the command with its comment header | `Ctrl+Shift+C` | Blocked while a red-blast command is unreviewed, exactly like the button. |
| Export command and control reference | `Ctrl+E` | Opens the command/control reference preview modal. |
| Move through palette results, or within any list (tools, commands, palette rows) | Arrow Up / Arrow Down | Wraps at both ends inside the palette. |
| Open the selected palette result | `Enter` | A tool opens its command list; a STIG/CCI/NIST hit opens the rule or resolves to one; a command loads into the editor. |
| Focus an editor line and pin its explanation | `Enter` or `Space` on a gutter line | Gutter lines are `role="button"`, `tabindex="0"`. |
| Move anywhere else | `Tab` / `Shift+Tab` | Focus order: rail, sidebar (version selector first), editor toolbar, gutter lines, inspector, status-bar theme button. The palette traps focus until `Esc`. |
| Print | `Ctrl+P` / `Cmd+P` | Browser-native, not in `KEYMAP`. The print stylesheet drops the rail, sidebar, inspector and status bar. |

**Note: plain Copy has no keyboard shortcut** -- only Copy *with comment*
(`Ctrl+Shift+C`) does. Use `Tab` to the **Copy** button and press `Enter` or
`Space`, or click it.

Every focusable control shows a visible focus ring; no rule in the stylesheet
removes an outline without replacing it. Each rail button shows both a compact
glyph and its text label, and exposes the same name through its accessible label.

### Favorites & Recent

Every command entry's toolbar carries a **Favorite** / **Favorited** toggle. The
**Favorites** rail (`Ctrl+Alt+5`) lists favorited entries and, below them, the
entries opened most recently this session, newest first (up to 20). Selecting
either opens the entry in its owning rail: Git, Ansible, or Command Builder.

Only entry IDs are ever written to `localStorage` (namespaced `mdcr.v1.`, schema-
versioned like every other stored value) -- never the entry's text. Every ID read
back out of storage is checked against the live content island before it is
trusted; an ID that does not resolve -- from an older build, or from anything that
is not a plain, short ID string -- is silently dropped rather than rendered blank
or as raw stored text. Favorites and recent are **per browser profile** (whatever
browser and profile opened the file -- `localStorage` is scoped to the page's
origin, and a `file://` page's storage is local to that browser installation); there
is no export to a file, and nothing here ever leaves the browser.

### Print View

`Ctrl+P` / `Cmd+P` prints the current command and, when the selection carries one,
its full STIG panel -- check text, fix text, CCI/NIST crosswalk, sunset banner and
"changed in RHEL X" note included -- with the rail, sidebar, inspector, status bar
and any open overlay dropped. Nothing else loads: the printed page draws from the
same single-file, zero-network artifact as the screen.

### Dark/Light Mode

`Ctrl+Shift+L`, or the **Theme** button at the right end of the status bar, toggles
between dark and light. With no explicit choice, the theme follows the browser's
own `prefers-color-scheme` setting, resolved in an inline `<head>` style before the
page paints -- there is no flash of the wrong theme on load. An explicit choice is
kept in `sessionStorage` only: it survives navigating within the same tab for the
rest of the browser session, but a fresh open of the file (a new tab, or the
browser restarted) starts from the system preference again.

### About Panel

The **About** rail (`Ctrl+Alt+7`) shows the tool's version and build date, the
content fingerprint, every embedded STIG release with its version, benchmark date
and rule count (and a sunset marker for RHEL 7), the embedded source families with
their license classes, and the required attribution block from SALM's Content
Licensing Ruling v1, reproduced verbatim -- see README.md's Attribution section for
the same text.

## Known Limitations

This is the honest state of the shipped build, not a roadmap. Current counts,
the receipt-derived default release and per-release flag totals are generated
from build inputs in `docs/generated/RELEASE_FACTS.md`; the unit suite checks
that file with `python3 tools/generate_release_facts.py --check` so these facts do not depend on
hand-maintained prose. The current derived default is RHEL 8: RHEL 8 and 10 tie
with nine receipts each, and the documented algorithm chooses the lower release.

- **199 curated command entries across 102 tools.** 43 are guided-form generators
  and 156 are static checks. The separate mined reference tier contains 14,439
  distinct commands with 45,281 source citations; reference rows are discovery
  material and are never silently promoted into the curated catalog.
- **RHEL 7 flags are extracted from a UBI7 container, not a real RHEL 7 host** --
  the lab has none. Of the tools probed, only 6 have a parsed flag dictionary on
  RHEL 7 (`systemctl`, `journalctl`, `yum`, `useradd`, `usermod`, `chage`), because
  UBI7's public repos ship neither `man`/`man-db` (every tool is `--help`-only) nor
  most of the other packages at all. The remaining tools are honestly marked
  `available: false` for RHEL 7 rather than guessed at.
- **RHEL 9 now has a release-specific flag dictionary and raw captures.** All four
  release dictionaries currently cover 22 command-line tools. A flag is still
  shown as unverified when its own release dictionary lacks that option; the UI
  never borrows a definition from another RHEL release.
- **Only 5 STIG ID/RHEL-version pairs carry a captured expected output**, out of
  the 10 STIG rows the 3 static entries declare across all four releases:
  `firewalld-service-active` (RHEL 8, RHEL 10), `ctrl-alt-del-target-masked`
  (RHEL 8, RHEL 10), and `journald-service-active` (RHEL 10 only -- it has no RHEL
  8 STIG mapping at all). Every other STIG panel in the build honestly shows "No
  capture yet."
- **Flag explanations are almost entirely uncurated.** Across the four release flag
  dictionaries, most entries do not carry a curated
  `explain` -- the extractor writes `explain: null` by design and a human SME
  curates prose in a separate step that has not run yet. Only 4 flags anywhere in
  the build (on the 3 static entries' own hand-curated `flags[]`) carry a curated
  explanation; every other flag panel entry in this build reads `unverified -- see
  man page`. This is the no-guess rule working as intended, not a bug, but it means
  the Inspector is not yet a teaching tool for most flags.
- **The "Captured, awaiting QA" verification badge is implemented and tested but
  never actually shown in this build** -- every capture on record already has a QA
  receipt.
- **Two guided entries are rated blast red:** `pvcreate` and `vgcreate`. Both
  write LVM metadata to a selected block device. The Copy controls stay locked
  until the operator checks **I have reviewed this command**.
- **The STIG Search rail item is a placeholder.** STIG lookup today happens
  through the command palette (Journey 2), not a dedicated browse view. The
  Ansible and Git rails are live. Six configuration generators have shipped:
  sshd, chrony, rsyslog, sudoers, systemd units and cron. Their output is a
  reviewed fragment; deployment still requires site-specific backup, ownership,
  mode, SELinux context, service action and recovery steps.
- **English only, desktop only.** No localization, no mobile layout beyond the
  responsive breakpoint at 1024px that stacks the inspector under the sidebar.

## Troubleshooting

Nine RHEL-first, read-only decision trees for boot/emergency mode, fstab,
DNF/RPM, NetworkManager, firewalld, LVM/filesystems, SELinux AVCs, time sync and
rsyslog are maintained in `content/rhel_troubleshooting.json`. They preserve
unknowns and stop before destructive repair. They are operator data in this
release and are not yet rendered as an in-browser rail.

**The file will not open, or shows "Not built yet."** You have `template.html`
itself, not a built artifact -- it has no data island. Run `python3 build.py` from
a checkout and open the file it writes under `dist/`.

**Opening from `file://` in Firefox ESR or Chromium.** The app needs no network at
all -- its Content-Security-Policy meta tag refuses every network-capable request
(`connect-src 'none'`, `object-src 'none'`, `form-action 'none'`) and the shell
polyfills `NodeList.prototype.forEach` and `Element.prototype.matches`/`closest`
for older ESR-era engines. If nothing renders, check your browser's own local-file
permissions (some hardened configurations restrict `file://` script execution
entirely) rather than looking for a missing server.

**Favorites, recent, theme choice, or the RHEL version do not persist between
opens.** Every `localStorage`/`sessionStorage` access is wrapped in its own
try/catch and degrades to "nothing was saved" rather than erroring -- a hardened
browser profile that blocks storage on `file://` pages will show this. The app
still works; it just starts from defaults (RHEL 9, light/dark by system
preference, no favorites) every time.

**Copy says "Copy failed."** The clipboard write uses a hidden, selected textarea
and `document.execCommand("copy")` rather than an async clipboard-permission API,
specifically so it needs no permission prompt on an air-gapped jump box -- but some
hardened configurations still block it. Select the text in the editor or the
evidence preview and use your browser's own copy command instead.

**The evidence export's content fingerprint does not match the About panel.** See
"Export command and control reference" above -- re-export from the file you actually have open rather
than trusting a fingerprint from elsewhere.

**A tool or command I expect is greyed out.** Check the RHEL version selector
first. A disabled row always carries its reason in a `.why` line and a tooltip
(for example "Not available in RHEL 7 -- use yum" on `dnf`); nothing is hidden
outright.
