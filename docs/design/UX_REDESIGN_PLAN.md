# MD CODE RED UX/UI Revamp Plan

**Status:** Proposed design direction for alpha.6 and the post-alpha.6 implementation sequence  
**Date:** 2026-09-30  
**Product:** MD CODE RED, offline RHEL command and operational-reference toolkit  
**Primary audiences:** Linux administrators, instructors, automation engineers, and compliance staff  
**Companion artifacts:** [Interactive concept board](UX_REDESIGN_CONCEPT.html) and [review presentation](UX_REDESIGN_REVIEW_DECK.html)

## Executive decision

MD CODE RED should keep its deterministic command assembly, offline operation, RHEL 7–10 awareness, validation, risk classification, sources, verification guidance, recovery guidance, and evidence model. Those features make it more trustworthy for real operations than lightweight command generators.

The interface should be reorganized around an operator's task. The current shell places the activity rail, command catalog, command workspace, inspector, and status bar on screen together. At a 1280-pixel viewport, the fixed 160-pixel rail, 240-pixel sidebar, and 320-pixel inspector reserve 720 pixels before the command workspace receives space. Forms then repeat meaning, examples, discovery commands, and consequences under every field. The result is a capable product whose main command feels compressed and whose proof competes with the action it is meant to support.

The proposed direction is a **calm operational field manual**:

1. Start from the task in plain language.
2. Show only the fields needed to configure it.
3. Keep the exact command and its essential trust signals visible.
4. Reveal the runbook, explanations, compliance mapping, release differences, and evidence on demand.

PR #17 remains useful as an interim responsive improvement. It should not be treated as the completed UX revamp because the information architecture, modal and palette behavior, focus stability, accessible command semantics, contrast, and mobile reading order still need deeper changes.

## Evidence used

This plan combines five evidence streams:

- Live task testing on Cmd Generator and MarkdownMe's Linux Command Generator on 2026-09-30.
- Static and interactive inspection of the alpha.6 development branch and generated single-file artifact.
- A UX architecture review of the 199 curated entries, 102 tools, 43 guided generators, 156 static entries, 14,439 mined references, learning content, STIG content, evidence functions, and current shell.
- An accessibility review of keyboard flow, focus, semantics, announcements, contrast, reflow, scrolling, and responsive behavior.
- SALM UX/UI designer and user-researcher analysis, using the operator workflow, friction, trust, skip-pattern, adoption-risk, and decision-point frameworks.

The external tools are reference points, not templates to copy. Their strengths are focus and speed. MD CODE RED's differentiator is reviewed, deterministic, release-aware, explainable output that works without a network.

## Competitive task benchmark

### Task 1: show `sshd.service` errors since today without a pager

| Product | Workflow | Result | Operational context |
|---|---|---|---|
| Cmd Generator | Select `journalctl`, enter the unit, choose error priority, add `Since`, disable pager | `journalctl --no-pager -u sshd.service -p err --since today` | Immediate preview and compact Basic/Advanced controls; no RHEL release, privilege, provenance, verification, or recovery context |
| MarkdownMe | Describe the task and choose Generate | `journalctl -u sshd.service -p err --since today --no-pager` | Lowest interaction cost; summary and flag explanations; server-side AI output, network dependence, no deterministic release ledger or provenance |
| MD CODE RED | Find the task or binary, configure unit, priority, and starting time | `journalctl --no-pager --unit='sshd.service' --priority='err' --since='today'` | Deterministic quoting, RHEL selection, risk, validation, source, verification, recovery, and evidence; supporting material crowds the primary command |

### Task 2: create `alice` with a home directory, Bash, and `wheel`

| Product | Result | Finding |
|---|---|---|
| Cmd Generator | `adduser --shell /bin/bash alice`, then a separate page for `usermod -a -G wheel alice` | Two pages and two copies; generic Linux orientation; no clear RHEL or privilege context |
| MarkdownMe | `sudo useradd -m -s /bin/bash -G wheel alice` | One coherent answer with flag explanations; generation is opaque and variable |
| MD CODE RED | `useradd -m -G 'wheel' -s '/bin/bash' 'alice'` | One deterministic command with root, risk, verification, and recovery context; too many panels compete for attention |

### Task 3: permanently allow HTTPS and apply the change now

| Product | Result | Finding |
|---|---|---|
| Cmd Generator | Copy `firewall-cmd --permanent --add-service https`, then replace it with and separately copy `firewall-cmd --reload` | The required operation is split and the first command disappears when the second is selected |
| MarkdownMe | Returns both commands in one block | Coherent multi-step result, but no cited RHEL release or deterministic safety model |
| MD CODE RED | Existing recipe: `firewall-cmd --add-service=https --permanent && firewall-cmd --reload` | Stronger operational guidance, but the fixed recipe and flexible rich-rule builder are disconnected |

### Task 4: inspect block devices with hierarchy, filesystem, size, and mount points

| Product | Result | Finding |
|---|---|---|
| Cmd Generator | `lsblk -T -o "NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS"` | Compact, editable controls |
| MarkdownMe | `lsblk --tree -o NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS` | Fast natural-language generation |
| MD CODE RED | Closest current recipe: `lsblk -f` | A real coverage gap: content knows `-o`, but no guided columns workflow exposes it |

## What to adapt and what to reject

### Adapt

- A prominent **What do you need to do?** task input above the fold.
- Immediate, persistent command output near the fields that control it.
- Essentials and Advanced disclosure.
- Short examples beside inputs, with deeper teaching opened only when requested.
- Task suggestions for common work: service logs, user creation, firewall access, storage inspection, package installation, and service management.
- One coherent result for multi-command operations.
- Plain-language descriptions and per-flag explanations.

### Reject

- Remote AI generation, prompt retention, daily quotas, or any dependency that breaks air-gapped use.
- Requiring operators to know the binary before they can begin.
- Uncited commands without release, risk, privilege, or verification context.
- Replacing an earlier command while constructing a required second step.
- Ads, sponsor panels, newsletters, or gamified usage counters in the operational workspace.
- Hiding the trust model. The redesign compresses and stages proof; it does not remove it.

## Operator behavior and adoption risks

### Linux administrator

The administrator wants a copy-ready command, honest prerequisites, a clear statement of what changes, and a recovery path that works. Experienced administrators will skip beginner prose and may use their own verification habits. They will still need verification and rollback when a change behaves unexpectedly.

**Design response:** put the command and trust bar first; keep Verify and Recover one action away; allow experts to stay in the compact path without suppressing safety checks.

### Instructor

The instructor needs a sequence that can be revealed and explained without the full catalog surrounding it. They need examples, field consequences, expected output, and release comparison at teaching speed.

**Design response:** provide a focused Learn workspace and presentation view with larger text, progressive reveals, and printable lesson cards.

### Automation engineer

The automation engineer needs stable structured inputs, predictable quoting, explicit joins, output-path risk, and a way to compose stages without losing validation context.

**Design response:** make Command, Pipeline, Ansible, Git, and Configuration file first-class task types within Build. Give pipeline composition a dedicated canvas.

### Compliance staff

The compliance user needs traceability. They must distinguish a requirement from an implementation command, a source from captured output, and a capture from verified execution.

**Design response:** provide a dedicated Compliance workspace with visible evidence state, control mappings, linked reviewed commands, and exportable references.

### Predicted skip patterns

| Content or control | Likely behavior | Risk | Design response |
|---|---|---|---|
| Long help under every field | Experts scan past it; juniors lose the task among the prose | High comprehension friction | One-line hint plus `Why this field?` disclosure |
| Recovery guidance below a long page | Ignored until a failure occurs | High operational risk | Keep Recover beside Verify in the runbook and destructive review state |
| Source citations in the main flow | Most admins skip them; assessors need them | Low if always recoverable | Compact source state in trust bar; full provenance in Evidence |
| Generic verification prose | Administrators substitute their own check | Medium trust risk | Exact verification command and expected result |
| Tool-first catalog | Goal-oriented users guess a binary or leave | High discovery friction | Task search and outcome categories; binary browser remains secondary |
| Unverified reference results mixed with reviewed commands | Users may copy a mined command with false confidence | Critical trust risk | Separate Reviewed tasks from Reference library and label every boundary |

## Information architecture

| Destination | Operator question | Existing material used |
|---|---|---|
| **Home** | What should I do next? | Recent work, favorites, role/task starts, common RHEL tasks |
| **Build** | How do I configure and review this operation? | Guided generators, static recipes, pipelines, Ansible, Git, configuration files |
| **Troubleshoot** | How do I diagnose this safely? | Nine existing RHEL troubleshooting trees and read-only checks |
| **Compliance** | What rule, control, capture, or evidence applies? | STIGs, CCIs, NIST mappings, capture state, evidence export |
| **Learn** | How do I understand or teach this? | Learning paths, drills, checklists, glossary, explanations, release comparisons |
| **Library** | What reviewed and reference material exists? | Curated commands, tools, and mined references with explicit trust boundaries |

Favorites and recent work belong on Home and in search. Version, fingerprint, licensing, and build details belong in Help/About. Git and Ansible become task types within Build rather than permanent peer applications.

The selected RHEL release remains global and follows the user. If changing the release alters or removes the current task, the application must state the effect before silently changing the output.

## Primary workflow

```text
Find the task  →  Configure essentials  →  Review command and trust  →  Use or open runbook
                      ↓                         ↓                            ↓
                Advanced options       Risk · root · RHEL · source    Verify · Recover · Evidence
```

Use four disclosure layers consistently:

1. **Act:** task name, exact command, primary copy action.
2. **Assess:** RHEL release, state-change class, privilege, verification, validation errors.
3. **Operate:** preflight, run, verify, recover.
4. **Understand:** flags, source, release comparison, STIG details, and teaching notes.

## Screen specifications

### Home

- Header: product identity, global RHEL selector, task search, theme, Help/About.
- Main prompt: **What do you need to do?**
- Offline suggestion chips: Read service logs, Manage a service, Create a user, Open a firewall service, Inspect storage, Install a package.
- Recent work and favorites.
- Role/task starts: Operate a host, Teach Linux, Automate a change, Assess controls.
- A short explanation of Reviewed commands and Reference library.

### Build catalog

- Search reviewed tasks by intent, tool, synonym, and outcome.
- Category filters: Logs, Services, Users and access, Firewall, Storage and LVM, Packages, Networking, Security.
- Filters: RHEL availability, state-change class, guided/static, host-verified, compliance mapped.
- Task cards show intent first, binary second, plus trust state and RHEL availability.
- Reference results are linked separately and never rendered as equivalent peers.

### Command builder

- Breadcrumb and task title.
- Three visible stages: Configure, Review, Verify. `Use` is represented by the command actions, not a fourth navigation burden.
- Essential fields first. Advanced fields collapsed.
- Each field includes a label, required/optional state, control, one short example, inline validation, and `Why this field?` disclosure.
- Sticky command card on wide screens; command card immediately after the title on narrow screens.
- Primary action: **Copy command**.
- Secondary action: **Review runbook**.
- Overflow: Copy with context, Copy generated file, Add to pipeline, Save, Print, Export reference.
- Tabs: Runbook, Explain, Compliance, Versions. Render a tab only when meaningful content exists.

### Multi-step operation bundle

Represent real operations as an ordered bundle:

1. **Run** — the command or commands that perform the task.
2. **Verify** — exact confirmation commands and expected evidence.
3. **Recover** — rollback commands, limitations, and prerequisites.

Each step has an individual Copy action. A separate action copies the complete reviewed plan. Never replace the Run command when the user selects Verify or Recover.

### Compliance rule

- Rule identity, severity, and RHEL applicability.
- NIST/CCI mappings.
- Evidence state: Reference only, Captured, Host-verified, Stale, or Missing.
- Linked reviewed command.
- Separate disclosures for Check, Fix, expected output, capture, and provenance.
- Export reference with an honest distinction between documentation and proof of execution.

### Troubleshoot

- Start from a symptom.
- Present one diagnostic decision at a time.
- Keep all default diagnostic steps read-only.
- Stop before a state-changing repair and hand off to a reviewed Build task.
- Render the nine existing content trees instead of leaving them unexposed.

### Learn

- Topic and learning-path browser.
- Focused lesson canvas with larger text.
- Progressive flag and field explanations.
- Release comparison.
- Knowledge checks, drills, and printable instructor view.

## Wireframe and mockup coverage

The interactive concept board supplies low-fidelity desktop and mobile wireframes plus high-fidelity desktop and mobile command-builder mockups. Production design work should expand the set to these required states:

- Viewports: 1440, 1024, 768, 390, 320 CSS pixels, and 400% zoom.
- Themes: light, dark, and forced/high-contrast review.
- States: empty, search, no result, incomplete form, validation error, read-only, state-changing, destructive, unverified reference, long command, STIG, pipeline, evidence dialog.
- Each frame annotates focus order, announced status, and the owner of scrolling.

## Visual system

### Direction

Use an operational field-manual aesthetic. The current product's monospace and dark command surface can remain, but ordinary reading text should use a highly legible sans-serif stack. Monospace is reserved for commands, identifiers, flags, evidence hashes, and compact labels.

The automated design-system search recommended a generic AI purple/pink palette. That recommendation is rejected because it conflicts with the existing product identity and with safety semantics. Project tokens and operator clarity take precedence.

### Semantic tokens

| Token | Light intent | Dark intent | Use |
|---|---|---|---|
| Canvas | warm neutral | graphite | Application background |
| Surface | white | elevated charcoal | Reading and form surfaces |
| Text | near-black | near-white | Primary content |
| Muted text | AA-compliant slate | AA-compliant light slate | Secondary content; never below contrast target |
| Brand | deep code red | bright restrained red | Product identity and selected brand details |
| Informational | blue/slate | lighter blue | Links, selected neutral navigation, help |
| Caution | amber | warm amber | Review needed, unresolved, or state-changing |
| Success | forest green | clear green | Verified evidence or successful validation |
| Destructive | red with icon and text | red with icon and text | Destructive operation only |
| Focus | high-contrast blue or amber | high-contrast light blue | 3-pixel visible focus ring |

Do not use color alone. Replace Green/Yellow/Red as primary labels with **Read-only**, **Changes system**, and **Destructive**. Color supports the words.

### Layout and type

- 4/8/12/16/24/32/48 spacing scale.
- 16-pixel minimum main-workspace body text.
- 44 by 44 pixel minimum interaction target.
- 65–78 character reading measure.
- One primary document scroll; drawers, dialogs, and tables own their scroll explicitly.
- No permanent 160 + 240 + 320 pixel panel reservation.
- Reduced motion support; use motion only to explain state change or focus transition.
- No external fonts, CDN assets, runtime libraries, or telemetry in the production artifact.

## Accessibility requirements

The following are release requirements for the redesigned shell, not polish items.

### P0 interaction and semantics

1. Implement the evidence panel as a real modal dialog: move focus into it, constrain Tab and Shift+Tab, make the background inert, close with Escape, and restore focus to the invoking control.
2. Implement search as an accessible combobox/listbox with correct `aria-expanded`, `aria-controls`, `aria-activedescendant`, option selection, and stable keyboard behavior.
3. Restore focus to the search control that opened the palette, not an arbitrary editor button.
4. Preserve focus across theme changes, panel toggles, favorites, destructive acknowledgment, and pipeline updates; avoid replacing focused nodes unnecessarily.
5. Expose command text through semantic `<pre><code>`. Give copy controls their own descriptive names. Do not label a command line only as `Line 1`.
6. Replace the full-editor `aria-live` region with a small stable `role="status"` region for command-ready, copy, validation, and refusal messages.

### P1 form, contrast, and reflow

7. Associate hints and errors with inputs using `aria-describedby`; set `aria-invalid` when appropriate.
8. Meet WCAG 2.2 AA contrast in both themes. The review measured failures around 2.90–3.09:1 for light muted text, 3.67–4.00:1 for dark muted text, 3.54–3.77:1 for light success text, 2.06–2.15:1 for the light focus ring, and approximately 1.2–1.5:1 for key form boundaries.
9. Give every status a text label or icon plus accessible text.
10. Add one page-level `h1`, clear main/navigation/complementary landmarks, and a skip target that receives focus without being hidden by sticky UI.
11. Remove the abrupt 1025-pixel state that can leave roughly 305 pixels for the editor before the 1024-pixel layout expands it.
12. Eliminate horizontally scrolling primary navigation on mobile.
13. Validate comparison tables, fixed bars, and dialogs at 200% and 400% zoom and with text-spacing overrides.
14. Test representative workflows with VoiceOver and NVDA, not only static rules.

## Independent review gate for PR #17

Claude Code 2.1.233 ran a read-only review with the verified `claude-opus-5-5` model at maximum effort. Its verdict is **REQUEST CHANGES**. The review confirmed that the layout-state cascade, archive handling, generated artifact, action routing, and air-gap/security boundary are sound. It identified three changes that should land before PR #17 merges:

1. Preserve focus on the Navigator, Inspector, and Theme buttons when their pressed state changes. The current `renderStatusBar()` replacement deletes the focused node.
2. Raise the contrast and size of the new shortcut/tagline text. The `Ctrl K` hint is approximately 2.9:1 in light mode and 4.0:1 in dark mode at 10 pixels.
3. Add minimum regression coverage for action routing, `aria-pressed` synchronization, focus retention, skip-target semantics, and layout-state row integrity.

The review also recommends fixing the sticky-header skip offset, returning palette focus to its opener, separating brand red from the destructive token, giving pressed states a non-color cue, adding a page-level heading, reconciling landmark names, improving the mobile rail, correcting the dark-mode selected tint, and reconciling release/documentation dates before the alpha.6 tag. The complete report is preserved in [CLAUDE_OPUS_REVIEW.md](CLAUDE_OPUS_REVIEW.md).

## Content and capability changes

### Add

- Offline intent-to-reviewed-task search with transparent matching.
- Guided `lsblk` storage inspection with presets: Filesystems, Capacity, Topology, LVM relationships, and Advanced columns.
- Editable firewall task templates: Allow service, Open port, and Rich rule.
- Multi-step operation bundles with persistent Run, Verify, and Recover commands.
- Dedicated Troubleshoot UI for existing trees.
- Dedicated Compliance browse and evidence-state UI.
- Focused instructor presentation and print view.
- Visible token-change highlighting when an input changes the generated command.

### Reconcile

- The user guide says RHEL 9 is the starting release in an early journey while the built alpha.6 development artifact derives RHEL 8 as the default. The documentation and artifact must state one source-controlled behavior consistently.
- Static recipes and guided builders should share the same task and form model so a recipe can become editable without switching entries.
- The flag inspector should show curated explanations when available and a concise `man` path otherwise. Repeated unverified rows do not justify a permanent inspector.

## Implementation roadmap

### Phase 0 — Validate the architecture

- Build clickable prototypes for Home, Build, command review, pipeline, Compliance, and mobile review.
- Test terminology and navigation with two representatives from each audience.
- Map every current action and content family to a destination.
- Confirm the selected RHEL context and trust boundaries remain understandable.

**Exit:** At least 80% of participants find the correct workspace for representative tasks without coaching.

### Phase 1 — Shell and accessibility foundation

- Replace the four-region shell with header, one navigation region, and one primary workspace.
- Establish semantic tokens for spacing, type, contrast, risk, focus, surfaces, and elevation.
- Implement correct headings, landmarks, skip target, status region, dialog, combobox, and focus restoration.
- Move inspector content into tabs and disclosures.
- Move build metadata into Help/About.
- Add task-centered Home.

**Exit:** No horizontal page overflow at 320 pixels; complete keyboard navigation; no loss of selection, focus, or RHEL context.

### Phase 2 — Builder redesign

- Add task search, categories, filters, and task-oriented results.
- Implement Configure → Review → Verify.
- Collapse instructional field detail.
- Add sticky command preview and trust bar.
- Consolidate command actions.
- Convert operational plans into bundles and a runbook.
- Separate reviewed tasks from references.

**Exit:** An administrator can find, configure, understand, and copy a known command without documentation or keyboard shortcuts.

### Phase 3 — Troubleshoot and Compliance

- Render all diagnostic trees.
- Build STIG/CCI/NIST browsing and filtering.
- Apply the evidence-state model consistently.
- Preserve read-only diagnostics and explicit handoff into reviewed repairs.

**Exit:** A compliance user can find a rule, identify mapped controls, distinguish reference from verified evidence, and export an honest reference.

### Phase 4 — Automation and teaching

- Move pipelines to a dedicated stage canvas.
- Add focused Ansible, Git, and configuration starts.
- Build Learn from instructional content.
- Add instructor presentation and print modes.

**Exit:** Users can build a two-stage pipeline and instructors can complete a lesson without entering the general catalog.

### Phase 5 — Hardening and release

- Complete light, dark, forced-color, reduced-motion, zoom, text-spacing, keyboard, and screen-reader validation.
- Validate Firefox and Chromium on supported RHEL and Windows jump-host workflows.
- Run exact-output, clipboard-parity, RHEL-gating, destructive-gate, CSP, air-gap, hostile-input, build-integrity, and provenance regressions.
- Produce responsive snapshots at 360, 768, 1024, 1440, and 1920 pixels.

**Exit:** The acceptance criteria below pass on the exact generated candidate artifact.

## Prioritized delivery backlog

| Priority | Work | Acceptance signal |
|---|---|---|
| P0 | Evidence dialog, search combobox, focus restoration, focus stability, command semantics, status announcements | Keyboard and screen-reader journeys complete without focus loss or hidden command meaning |
| P0 | New shell and task-first information architecture | Common task begins above the fold and the command workspace is not compressed by three permanent panels |
| P0 | Trust boundary between reviewed and reference commands | Participants correctly classify the boundary at least 90% of the time |
| P1 | Command builder progressive disclosure and trust bar | Exact command and Copy action remain visible; required proof is reachable in one action |
| P1 | Contrast, text size, target size, and mobile reflow | WCAG 2.2 AA checks pass; no horizontal page scroll at 320 pixels |
| P1 | Operation bundles | Run, Verify, and Recover persist together and copy independently |
| P1 | Guided storage inspection | Exact benchmark task can generate hierarchy, filesystem, size, and mount-point columns |
| P1 | Firewall template unification | HTTPS and custom service/port workflows generate permanent plus apply-now steps coherently |
| P2 | Compliance and troubleshooting workspaces | Existing content is discoverable through outcome-based navigation |
| P2 | Instructor and pipeline workspaces | Representative teaching and automation journeys complete without catalog detours |
| P2 | Documentation/default-version reconciliation | User guide, source, and generated artifact agree on default behavior |

## Usability research plan

Recruit 20–24 participants, with 5–6 from each primary audience. Use paired task testing where competitors support the task. Do not install remote product analytics in the application; capture research observations outside the shipped artifact.

Representative tasks:

1. Generate a command to show `sshd.service` errors since today without a pager.
2. Determine whether `firewalld` is active on RHEL 9.
3. Create a user with a home directory, Bash shell, and wheel membership.
4. Permanently allow HTTPS and apply it now.
5. Inspect storage hierarchy, filesystem, size, and mount points.
6. Build a two-stage journal-to-tee pipeline and identify output-path risk.
7. Generate an Ansible package task and find the dry-run invocation.
8. Locate a STIG, map its NIST controls, determine evidence state, and export the reference.
9. Attempt a destructive LVM command and explain why copy is blocked.
10. Teach the journal command and compare release behavior.

Record completion, correctness, time, wrong turns, navigation reversals, controls used, trust interpretation, whether Verify and Recover are found, and confidence. Test keyboard-only use, VoiceOver, NVDA, 200%/400% zoom, reduced motion, forced colors, text spacing, and narrow landscape.

## Success measures

- At least 85% unassisted completion across all four audiences.
- Median time to first valid common command below 45 seconds for experienced administrators and below 3 minutes for new learners.
- No more than two navigation reversals before selecting the intended task.
- At least 90% correct interpretation of reviewed versus reference, read-only versus state-changing, and captured versus verified.
- Every participant notices the destructive-command gate before attempting copy.
- At least 90% find Verify and Recover without coaching.
- Zero page-level horizontal scrolling on mobile.
- Every primary target is at least 44 by 44 pixels.
- System Usability Scale target of 80 or better.
- No regression in command output, quoting, validation, risk classification, RHEL gating, clipboard parity, CSP, air-gap operation, evidence integrity, or hostile-input handling.

## Definition of done

The revamp is complete when:

- The primary workflows work from intent search through copy, verification, and recovery.
- The single-file artifact makes no network request and contains no runtime external dependency.
- The generated command remains deterministic and matches golden tests.
- All safety and evidence states are accurate, visible, and programmatically conveyed.
- Keyboard, VoiceOver, and NVDA users can complete representative workflows without focus loss.
- Light, dark, forced-color, reduced-motion, zoom, and text-spacing checks pass.
- The exact release candidate passes the existing QA, unit, hostile-input, CSP, build-integrity, provenance, and distribution gates.
- User documentation matches the shipped default release behavior and navigation.
- Product, engineering, QA, accessibility, and Linux-administrator reviewers accept the same generated candidate.

## Open decisions for implementation planning

These questions do not block review of the design direction. They should be resolved during Phase 0:

1. Whether the new shell lands in alpha.6 or becomes the principal alpha.7 scope.
2. Whether mobile Review is a distinct route/state or an in-document transition while keeping a single history entry.
3. Which current static recipes are promoted first into editable task templates.
4. Whether instructor presentation is included in the same single-file artifact or generated as a separate offline artifact.
5. Which RHEL release is the source-controlled default after the documentation drift is reconciled.

## External references

- [Cmd Generator](https://cmdgenerator.org/)
- [Cmd Generator journalctl builder](https://cmdgenerator.org/cmd-generators/journalctl/)
- [Cmd Generator adduser builder](https://cmdgenerator.org/cmd-generators/adduser/)
- [Cmd Generator usermod builder](https://cmdgenerator.org/cmd-generators/usermod/)
- [Cmd Generator firewall-cmd builder](https://cmdgenerator.org/cmd-generators/firewall-cmd/)
- [Cmd Generator lsblk builder](https://cmdgenerator.org/cmd-generators/lsblk/)
- [MarkdownMe Linux Command Generator](https://markdownme.com/tools/linux-command-generator)
- [Awesome HTML Slide Skills](https://github.com/ToseaAI/awesome-html-slide-skills)
- [visual-explainer](https://github.com/nicobailon/visual-explainer), used as the presentation workflow under its MIT license
