# Changelog

All notable changes to MD CODE RED are documented here. This project adheres to [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Fixed — re-review conditions D1/D2: MCR-SEC-013, MCR-SEC-014 (2026-09-17, branch `salm/milo/sec-013-014`)

Marcus Reed's re-review of `ac087c3` returned **APPROVE WITH CONDITIONS**: all three HIGH findings
closed, `block_flag` cleared, two new findings — one LOW, one INFORMATIONAL — carried as conditions
D1 and D2. Both are addressed here. The fixtures were committed FIRST, in a commit that fails the
gates (`93a0cbf`), and the fix follows in the commit that turns them green: D1 asks for the gate to
be shown to fail before it is shown to pass, which is the standard the CR-T-08 harness set.

**MCR-SEC-013 (LOW) — a conditional positional literal still shifted arguments.** The MCR-SEC-002
fix reasons about argument slots through `isPositionalToken(tok)`, which was `tok.field && !tok.flag`
— so a `lit` was never positional. A literal made conditional with `requires` could therefore vanish
without the later-positional check that every field token gets:

```js
fields:  [{name:"mode",type:"integer",required:false},{name:"p",type:"path",required:true}]
template:[{lit:"chmod"},{lit:"0644",requires:"mode"},{field:"p"}]
```

with `mode` absent assembled `chmod '/etc/foo'` — the path promoted into the mode slot — and
`spec_errors()` accepted the spec. Both halves now count a `requires`-carrying literal as positional.
At run time `tokenPresent()` answers the presence question for `requires` as well as for `field`, and
one shared `laterPositionalSurvives()` states the shift rule once for both callers. At build time
`positional_indexes()` and `shift_unsafe_after()` do the same, and `spec_template_errors()` refuses
a conditional literal that has a surviving positional after it. An *unconditional* literal stays out
of the positional set deliberately: it can never vanish, so it can never shift anything, and counting
it would refuse correct templates. The legal shape MCR-SEC-002 shipped — `{lit:"…toaddr=",
requires:"toaddr"}` followed by `{field:"toaddr", optional:true}`, both gated on the same field so
they leave together — is still accepted, and `tests/fixtures/schema/valid/` now holds it there so a
future tightening cannot quietly take it away.

**MCR-SEC-014 (INFORMATIONAL) — computed member access reached a render sink.** `el("x")["inner"+
"HTML"] = raw` was rated safe with `audited = 0`: every Q17 rule reads the dotted spelling, and the
spliced name never appears in the source for a regex to find. Marcus accepted either closing it or
recording it, provided the gate was not described as unbypassable. **Closed**, because the check is
mechanical and has no false positive on the code it guards. Q17 now reads the property expression of
every computed member assignment and refuses three things: a bracketed render-sink name
(`obj["innerHTML"]`), a property expression it cannot read (built from literals or operators), and a
sink name fused out of string literals — inline, through a variable, or across two statements
(`k = "inner"; k += "HTML"`). Identifiers, numbers and dotted/indexed chains are allowed, which is
what `out[fields[i].name] = …` in `fieldTypeMap()` and `out.resolved[f.name] = …` in
`validateSpec()` are; a gate with a false positive on the code it guards is a gate somebody switches
off, so a safe control fixture holds that line. The residual the rule genuinely cannot see — a
property name produced at run time from data rather than from string literals — is printed in Q17's
own PASS output instead of being left for the next reviewer to discover, and written into
`docs/CODE_STANDARDS.md` §1.

**Tests.** Four new render-bypass fixtures (`bypass_12`..`bypass_15`) plus
`safe_control_computed_index.js`; an invalid and a valid schema fixture for the conditional literal;
four new never-half-formed harness vectors across all four releases (60 → 76 checks). Gates after the
fix: `python3 qa.py` **QA GATE: PASS**, `python3 -m unittest discover -s tests` **51 tests OK**,
`node tests/hostile_harness.js` **63,536 checks, 0 FAILED**, byte-identical rebuild
(`5fb9b7adfd8b60fe…`).

### Fixed — security review MCR-SEC-001..012 (2026-09-17, branch `salm/milo/shell-assembler`)

Marcus Reed's security review of `4184ea8` returned **DENY with `block_flag`** — 3 HIGH, 5 MEDIUM,
2 LOW, 2 INFORMATIONAL. Every finding is addressed here. None of them was reachable from the shipped
UI (the form renderer is CR-T-25), and that is the reason they close now rather than later: the
assembler is the contract fourteen P0 tool categories of templates will be written against, and a
gate that clears a contract because nothing calls it yet is not a gate.

**MCR-SEC-001 (HIGH) — rich-rule grammar injection.** `composeRichRule()` carried a comment asserting
that no validated value could contain a double quote "because no field type's allow-list admits a
quote character". Two types did: `comment` (every printable character) and `enum` (whatever a content
author lists). A `comment`-typed field in a rich-rule slot could close an attribute and open new
elements — the review's reproduction installed an `accept` clause and a logging clause past the
`drop` the operator had selected, with shell quoting fully intact, so the hostile-input harness rated
it QUOTED-SAFE. Fixed structurally: `RICHRULE_SLOT_TYPES` lists the closed-grammar field types each
slot accepts and `comment`/`enum` are deliberately absent, because rich-rule attribute syntax has no
escape sequence for a quote inside an attribute value — there is no correct encoding, so there is no
free-text path into a rich rule at all. A character-level re-check at composition time is the second
layer. The false comment is replaced with the reasoning.

**MCR-SEC-002 (HIGH) — never-half-formed, per template rather than per field.** An optional field
that was not supplied made its token vanish and the command still assembled: `chown 'apache'
'/var/www'` became `chown '/var/www'` (the path promoted into the owner argument), and a literal that
owned a value could be left dangling as `--add-forward-port=port=443:proto=tcp:toaddr=` — the exact
artefact threat-model-v1 §3.4 names as its reason for existing. Token dropping is now declared:
`optional:true` is mandatory, a positional token may only drop if every later positional drops with
it, `{lit:"...", requires:"field"}` binds a literal to its value, and a version-gated field takes the
same path so one template cannot be well-formed on RHEL 9 and mis-positioned on RHEL 8.

**MCR-SEC-003 (HIGH) — the clipboard header.** "Copy with comment" built `"# label: " + raw content`
and copied it; none of the header is rendered, so a newline in `intent` put a second, never-displayed
line into a root shell — the reproduction copied `rm -rf /var/log/audit` off a screen showing one
title line, with blast green, because `blastFor()` only looked at `res.command`. Four independent
layers now: `headerSafe()` flattens every value to single-line printable text; `commentPayload()`
splits on CR/LF/CRLF anyway and prefixes **every** line with `# `, refusing to compose at all if the
command is not single-line; `blastFor()` runs over the whole payload so the banner fires before the
click and the acknowledgement covers what the clipboard receives; and `extract/schema.py` rejects any
control character in `intent`, `verify`, `undo` and every `stig[]` string, failing the build instead
of the clipboard. The header is also rendered as a read-only preview of exactly what gets copied
(threat-model-v1 §9).

**MCR-SEC-004 (MEDIUM) — the Q17 render audit had five mechanical bypasses** (`innerHTML +=`,
`html = html + x`, an intermediate accumulator under another name, `insertAdjacentHTML`,
`outerHTML`), all rated PASS. Now: forbidden sinks are refused outright (those two plus
`document.write`/`writeln`, `createContextualFragment`, `srcdoc=`), `.innerHTML` may only be an
assignment target, `setAttribute()` must name its attribute with a readable literal and may not name
`href`/`src`/`srcdoc`/`style`/`action`/`formaction`/`xlink:href`/`on*`, the accumulator set is
derived from the source and closed transitively, `=` and `+=` are audited alike, and `is_literal()`
parses the literal instead of comparing first and last characters. 13 negative fixtures under
`tests/fixtures/render-bypass/` prove each construct now fails; audited expressions 24 -> 85.

**MCR-SEC-005 (MEDIUM) — the rich-rule test's hostile-type parameter was dead.**
`richRuleSpec(hostileField, hostileType)` was only ever called as `richRuleSpec(null, null)`, which
is why MCR-SEC-001 survived 15,392 checks. It is now driven with every field type in every slot of
two rich-rule shapes, and the harness gained the second oracle the finding asked for: a rich-rule
parser that asserts the composed rule's element count, element order, attributes and ACTION equal the
operator's intent. Both oracles carry negative controls — the injected rule from the review and an
action-only swap must be caught — so the oracle has been seen to fail before it is believed.

**MCR-SEC-006 (MEDIUM) — `template[].flag` and `template[].lit` are trusted content, not unchecked
content.** `extract/schema.py` had no `template`/`fields`/`richRule` shape at all. It has one now —
field names and types, enum options, version subsets, token shapes, both allow-lists
(`^-{1,2}[A-Za-z0-9][A-Za-z0-9-]*$` for flags, `^[A-Za-z0-9_./=:,+-]+$` for lits), `requires:`
resolution, rich-rule slot types, MCR-SEC-002's droppability rules, and declared-but-unused fields.
The same two allow-lists are enforced at run time, where a bad token makes the whole template `null`.
`tests/test_schema.py` asserts the field-type list, the rich-rule slot table and both regexes are
identical on both sides, so the mirrored tables cannot drift silently.

**MCR-SEC-007 (MEDIUM) — the data island's `</` escaping.** It closed `</script>` and nothing else:
`<!--` followed by `<script` puts the HTML tokeniser into script-data-double-escaped state, where
`</script>` stops terminating the element and the island's closing tag, the app script and its own
"Not built yet" fallback are swallowed as text — a silent denial of use on a jump box, with
verbatim-embedded DISA fix text as the delivery vehicle. `build.py` now escapes every `<` and `>` as
`\u003c`/`\u003e`: valid JSON, reversible, one rule instead of a list of sequences. Q1 asserts no raw
`<` or `>` survives; `qa.py` parses the island without repairing it first.

**MCR-SEC-008 (MEDIUM) — a destructive pattern could not match across a value boundary.** `shQuote()`
inserts a quote at every literal-to-value boundary, so the first reviewer to add `rm -rf /` to
`dangerous.json` would have silently disabled that row. `blastFor()` now matches both the raw command
and its unquoted projection. `rm -rf /` is in the table (8 -> 9 patterns), the constraint is
documented in `_meta` where a reviewer authors, and the harness asserts every row fires on a
synthetic assembled command — a pattern that can never fire fails the build.

**MCR-SEC-009 (LOW)** — U+2028, U+2029 and U+2065 added to `INVISIBLE_RE`, to Q17's trojan-source
ranges, and to the fixture's `invisible character` class (52 -> 55 vectors).

**MCR-SEC-010 (LOW) — DECISION: `yamlQuote()` removed, not wired.** It was correct, used the right
YAML `''` idiom, and had no call site: `assembleCommand()` has no YAML output path, so Q18's
quoting-domain gate was passing on a domain that did not exist. A dead escaper reads as "Ansible YAML
output is proven safe", which the CR-T-25 review would have inherited as a false clean bill. The
gate is now explicitly **shell-only** until the Ansible generators land (CR-T-17+), the Q5 marker
reports PENDING rather than PASS, and two gates hold the door for its return: `qa.py` fails if a YAML
quoter appears in the shipped shell, and the harness refuses to run if one appears in the assembler
block without a YAML-parsing oracle beside it.

**MCR-SEC-012 (INFORMATIONAL) — one rendered-state object.** `currentResult()` was called
independently by `renderEditor()`, `renderBlastBanner()`, `renderInspector()` and `doCopy()`. `RESULT`
is now computed once per interaction, keyed on the state assembly reads and dropped at the top of
`renderAll()`; the gutter, the banner, the inspector, the clipboard preview, `doCopy()` and the
CR-T-28 exporter read it (threat-model-v1 §9).

**MCR-SEC-011 (INFORMATIONAL)** needed no code change: it records that no user-supplied value reaches
the assembler in the shipped UI. Condition **C10** is also closed — Q17's trojan-source scan now
covers the data island as well as the hand-written shell, because DISA fix text is rendered *and*
copied into evidence.

Gates on this work: `python3 build.py && python3 qa.py` -> Q1-Q18 PASS; `node tests/hostile_harness.js`
-> 63,536 checks, 0 failures, 27 invariants, 276 positive controls;
`python3 -m unittest discover -s tests` -> 51 tests OK; two builds byte-identical; verified in Chrome
with zero console errors.


### Added — runtime shell, keyboard controller and the command assembler (2026-09-17, CR-T-08/13/14/15/16)

**The security-critical tranche.** The command assembler is the surface the threat model ranks as the
product's top risk: a string this code builds is executed by a trusted human as root on a production
host, with no sandbox, no approval step and no rollback behind it.

- **`assembleCommand(specOrEntry, version, values)` (CR-T-15)** — pure, DOM-free, data-free, and
  fenced between `MCR-ASSEMBLER-BEGIN` / `MCR-ASSEMBLER-END` markers so it can be lifted out of the
  *shipped artifact* and executed under Node by the test harness. `null` is the only answer for an
  incomplete or invalid input: there is no second return shape carrying a half-built string
  (threat-model-v1 §3.4). A companion `validateSpec()` tells the UI *which* field is wrong without the
  assembler ever handing out a partial command to explain itself with.
- **A per-field TYPE system with 23 allow-list validators** — hostname, ipv4, ipv6, ipaddr, cidr,
  port, portrange, protocol, family, action, unit, username, groupname, path, zone, service, package,
  selinux_boolean, audit_key, interface, integer, enum and comment. Full match, length-capped, and
  preceded by universal checks that reject control characters (NUL, newline, carriage return, tab),
  invisible and bidirectional-override characters, non-ASCII look-alikes, and any leading dash
  (argument injection). `comment` is the **only** free-text type, the only one that accepts non-ASCII
  text, and it is still single-quoted before it can reach a shell.
- **`shQuote()` and `yamlQuote()` as separate functions** — POSIX `'\''` for the shell, `''` for YAML,
  and `esc()`/`escapeAttr()` for the DOM: three escaping domains, three functions, never nested.
  `shQuote()` deliberately has **no** "this value looks harmless, leave it bare" branch; quoting is
  uniform, which costs `--zone='public'` in the rendered command and buys a rule with no exceptions
  to audit.
- **firewalld rich rules composed from validated sub-fields** (`composeRichRule()`), never from one
  free-text box — the highest-risk field class in threat-model-v1 §3.1.
- **Blast evaluation against `dangerous.json` matched on the fully assembled, post-quoting command**,
  with a content entry's own `blast: "red"` tripping the banner independently (§3.3). The red banner
  is `role="alert"` and holds Copy until the reviewer checkbox is ticked.
- **Version gating that is structural, not cosmetic** — a field or an enum option that a release does
  not carry is dropped from the template before assembly, so it is *impossible* to include in that
  release's command, and the control renders disabled with "Not available in RHEL N" rather than
  disappearing.

- **Runtime shell (CR-T-13)** — the five regions per UI spec §2 with real content: a rail with
  focus-revealed text labels (no images anywhere), the version selector persisted by id through the
  storage guard, the tool list from `tools.json` gated by per-release availability with its reason and
  alternative, an editor rendering the assembled command in a monospace block with a real line-number
  gutter (`role="button"`, focusable), an inspector listing every flag the command actually uses with
  its curated `explain` or the honest "unverified — see man page", and the status bar. Dark and light
  tokens per UI spec §6 with the theme resolved in an inline `<head>` style, so there is no flash of
  the wrong theme. Empty, gated and error states per UI spec §7 — with no tool selected the toolbar is
  *absent*, not merely disabled, so there is no dead control to tab through. Everything renders through
  `esc()`/`escapeAttr()`; interaction is `data-*` delegation; zero inline handlers.
- **Keyboard controller (CR-T-14)** — one delegated `keydown` listener over one `KEYMAP` table: `/`
  and `Ctrl/Cmd+K` for the palette, `Esc`, `Ctrl+B`/`Ctrl+I` panel toggles, `Ctrl+Shift+L` theme,
  `Ctrl+Shift+C` copy-with-comment, `Ctrl+Alt+1..5` rail jumps, arrow navigation in every list, a
  focus-trapped palette, and a visible focus ring on every control. Documented in
  `docs/USER_GUIDE.md`, which replaces its keyboard TODO with the table the code actually implements.
- **Shell-level command palette** over the build-time index seed, so the keyboard controller has a
  real palette to drive. The lazy typed index over flags, STIG IDs and control numbers is still
  CR-T-29 and is marked as such on screen.

### Added — gates that can be shown to fail (2026-09-17, CR-T-08/16)
- **`qa.py --accuracy` hardening (CR-T-08).** The Q10 comparison moved into a pure
  `accuracy_failures()` that `gate_q10` and the tests both call, and it grew a second layer: the
  20-per-release stride sample still catches drifted text, and a new **full ID-set parity check**
  catches a rule added, dropped or renamed *outside* the sample, which 20-in-445 would otherwise walk
  straight past.
- **A committed mutated fixture.** `tests/fixtures/accuracy/clean_rules_rhel9.json` is the
  deterministic sample of the shipping RHEL 9 dataset, unmodified; `mutated_rules_rhel9.json` is the
  same file with six planted edits, one per field the gate compares (title, rule id, CCI set, CAT,
  fix text past the 100-character prefix window, check text). `tests/test_accuracy_gate.py` proves the
  gate passes on the clean file and names every planted mutation in its failure output on the other —
  the control case first, because a mutated fixture failing proves nothing if the clean one fails too.
- **Hostile-input harness (CR-T-16), Marcus's CI merge-gate #4.**
  `tests/fixtures/hostile-inputs.json` carries **52 vectors across 18 classes** — command
  substitution, statement separators, redirection, grouping, globbing, newline and CR injection,
  option injection, unicode look-alikes, invisible and bidi characters, path traversal, NUL,
  quote-breaking, over-length, empty. `tests/hostile_harness.js` runs every vector against every field
  type on all four releases in three argument shapes, plus five rich-rule sub-fields: **15,392 checks**
  per run. Each pair has a *required* outcome — every closed-grammar type must reject every vector,
  and the one free-text type's expectation is declared per vector — so a validator that stopped
  enforcing its grammar fails the gate even when the shell quoting still holds.
- **The harness does not execute `/bin/sh`.** Proving the quoting by running it would mean executing
  attacker-controlled text in CI on precisely the build where the quoting is broken. It tokenises the
  assembled command under POSIX rules instead and compares its shell-visible shape against the same
  command built from a benign value.
- **Controls in both directions.** 276 positive controls assert every field type's benign value still
  assembles on every release in every shape, so a gate cannot pass by rejecting everything; two
  negative controls assert the checker itself still fails an unquoted `$(whoami)` and an appended
  `; id`.
- **`qa.py` Q18** runs that harness against the **built artifact**, so the code CI clears is the code
  that crosses the air gap, and adds threat-model §11 gate #9: a static check that `shQuote`,
  `yamlQuote` and `esc` are never nested inside one another.
- **Q17 gained a trojan-source scan** — zero raw C0/C1 control, zero-width or bidirectional-override
  characters in the hand-written shell. This is not theoretical: it caught 29 such characters in this
  very branch (below).

### Fixed (2026-09-17, CR-T-15/16)
- **The `unit` field type admitted a backslash.** Its character class was written `[A-Za-z0-9_.@:\\-]`,
  and the escaped backslash put `\` *inside* the class. A backslash is inert once single-quoted, so no
  injection was possible — but it is the one character whose meaning differs between the shell, YAML
  and a systemd unit name, and the allow-list is supposed to be a grammar, not just an injection
  filter. **Found by the hostile-input harness on its first policy-enforcing run**, not by review.
- **29 raw control and invisible characters in `template.html`.** The two regex literals meant to
  *reject* control and bidi characters had been written with real control characters instead of
  escapes — including a NUL and five bidirectional overrides — which broke the regex at load time in
  Chromium (Node's `--check` parsed it happily). Repaired to escapes and now gated by the Q17
  trojan-source scan, which is the control that stops it recurring.

### Changed (2026-09-17, CR-T-16)
- **Node is now REQUIRED in CI** (`actions/setup-node@v4` in `.forgejo/workflows/ci.yml`). The
  assembler is JavaScript and Q18 runs it; a Python re-implementation of the quoting would be a second
  assembler to keep in sync and the shipped one would be the untested one. The older `node --check`
  syntax gate stays optional, because a missing syntax check is an inconvenience and a missing
  injection check is a production RHEL host.
- **Q5 feature markers** now cover the shell, the keyboard controller and every assembler module, and
  the assembler / keyboard markers moved from PENDING to required. The generator registry, flag
  decoder, STIG panel, evidence exporter and lazy typed index stay PENDING against their own tasks.

### Added — content schema module and the real XCCDF pipeline (2026-09-17, CR-T-06/07)
- `extract/schema.py`: the ADR-001 §5 content schema as one pure, importable module — provenance,
  the four mandatory RHEL keys and the three legal version-value shapes, `same_as` chains and cycles,
  `stig[]` referential integrity, `blast` enum, the `{by, on, host}` `verified` receipt, flag shape,
  generated-dataset `_meta`, the tools availability matrix, and the filtered CCI map. `build.py` and
  `tests/test_schema.py` both import it, so the build and the tests cannot enforce different rules.
- `tests/test_schema.py`: 11 tests, stdlib only, no third-party dependency. The shipping `content/`
  is validated first as the control, then 2 valid and 30 invalid bundles under
  `tests/fixtures/schema/`, each declaring the error it expects so a fixture cannot pass by failing
  for the wrong reason.
- `extract/parse_xccdf.py`: the full RULES pipeline. Verifies `stig-src/SHA256SUMS` before reading a
  byte, cross-checks each benchmark's in-XML version against its pinned filename, and emits every
  rule of all four releases — **1,492 total: RHEL 7 V3R15 244, RHEL 8 V2R8 369, RHEL 9 V2R9 445,
  RHEL 10 V1R2 434** — with STIG ID, `SV-…_rule` id, CAT, title, all `ident` CCIs, the mapped NIST
  SP 800-53 controls, and verbatim uncapped check and fix text. `_meta` carries benchmark id,
  release-info version and date, source SHA-256, CAT counts, `partial: false`, and `extracted_on`.
- `build_cci_map` step in the same script rewrites `content/cci_nist.json` from `U_CCI_List.xml`,
  filtered to the 200 CCIs the four benchmarks cite and recording the full list's 5,137 items.
- Determinism: nothing in the extractor reads a clock, so a re-run is byte-identical and two builds
  of the same sources produce the same artifact SHA-256 on any day.

### Changed (2026-09-17, CR-T-06/07)
- `source.version` is mandatory provenance. A source that cannot say which version of the document it
  came from cannot be re-checked.
- A flag's `explain: null` is legal only while `content/flags_rhel*.json` are empty. Once a dictionary
  is curated, a null explain is a schema error rather than a shipped blank.
- Q8 requires exact per-release parity with a live re-parse; `_meta.partial` is now a failure, because
  no extractor in the repo produces a partial dataset any more.
- Q9 reports CAT I check-and-fix completeness per release and fails a release that reports zero CAT I
  rules (which would mean the severity parse dropped them and the gate had nothing to check).
- Q10 compares the full check and fix text, not only a 100-character prefix, and fails if the fixed
  stride cannot yield the 20 samples ADR-001 §7.3 requires.
- Q11 also fails on a CCI map carrying mappings no embedded rule cites — the map is filtered by design.
- Q15 re-runs every extractor and additionally verifies that each generated dataset declares a
  generator this gate actually executes, so a file cannot name an extractor nobody runs and then drift.
- CI runs `python3 -m unittest discover -s tests` instead of one test file by name.

### Removed (2026-09-17, CR-T-07)
- `extract/make_skeleton_content.py`. Its RULES and CCI half is replaced by `extract/parse_xccdf.py`;
  the genuinely sourceless half — empty flag dictionaries and the empty capture index — moved to
  `extract/make_pending_skeletons.py`.

### Added — real FLAGS dictionaries from Defiant and Saratoga (2026-09-17, CR-T-09/10, Milo Vance)
- `extract/extract_flags.py`: SSH (read-only, no sudo) to a RHEL host, run `man -w`/`man -P cat`/
  `<tool> --help`/`rpm -qf --qf '%{NVRA}'`/`cat /etc/redhat-release`/`uname -r` for the 22 P0 tools
  (systemctl, firewall-cmd, nmcli, dnf, yum, semanage, setsebool, useradd, usermod, chage, pvcreate,
  vgcreate, lvcreate, lvextend, sshd + sshd_config(5), journalctl, auditctl, ausearch, rsyslogd +
  rsyslog.conf(5), chronyd + chrony.conf(5) + chronyc, podman, git), save the raw output under
  `content-src/raw/rhel<N>/` (git-ignored — the paraphrase-only source of record for Q14's collision
  check and for licensing review), and parse the OPTIONS-style definition list in each page into
  `content/flags_rhel<N>.json`: `names[]`, `takes_arg`, `explain: null` per flag, `package` (NVRA) and
  `pages[]` (man section, source, `raw_ref`) per tool. The parser never writes prose — man pages are
  GPL-2.0-or-later, paraphrase-only per `content-licensing-ruling-v1.md` — and anything option-shaped
  it cannot confidently resolve into a name/arg boundary is recorded under a tool's `unparsed[]` rather
  than guessed. Re-running is non-destructive: a curated `explain` survives, and a flag no longer seen
  is marked `removed_in` rather than silently dropped.
- `--check` mode (no SSH): re-parses the committed raw dumps under `content-src/raw/rhel<N>/` and
  diffs the result against `content/flags_rhel<N>.json`, so reproducibility can be proven offline and
  in CI without a live dependency on lab hosts.
- Ran against **Defiant (RHEL 8.10)**: 22/22 tools present, package NVRA recorded for each,
  **952 flags parsed, 1 unparsed**. Ran against **Saratoga (RHEL 10.2)**: 22/22 tools present,
  **1,019 flags parsed, 3 unparsed**. `content-src/raw/rhel{8,10}/` hold 27 raw man/help dumps each.
- `qa.py` Q15: `extract/make_pending_skeletons.py` still owns the placeholder empty
  `flags_rhel{7,9}.json` (RHEL 9/7 extraction is CR-T-11/12, still blocked/at-risk), but no longer
  gates `flags_rhel8.json`/`flags_rhel10.json` — those are real data now, so a diff against the empty
  placeholder would always show expected drift. Q15 instead runs `extract_flags.py --check` for RHEL
  8 and 10 directly against the committed raw dumps. Documented inline in `gate_q15`.

### Known conflict — content/commands.json vs. the new explain:null schema rule (CR-T-06 × CR-T-09/10)
- `extract/schema.py`'s `flags_errors()` (added this same day by the concurrent `salm/milo/xccdf-pipeline`
  branch) makes a command entry's `flags[].explain: null` a schema error once *any* `flags_rhel*.json`
  is non-empty — and CR-T-09/10 just made two of them non-empty. `content/commands.json` currently has
  4 such flags across 3 skeleton entries (`firewalld-service-active`: `status`, `is-active`;
  `ctrl-alt-del-target-masked`: `status`; `journald-service-active`: `is-active`), so as of this branch
  **`python3 build.py` FATALs with 4 schema errors** and `tests/test_schema.py`'s
  `test_flag_explain_nulls_are_still_honest` / `test_content_dir_validates` and
  `tests/test_build_fails_on_broken.py`'s `test_00_real_content_builds` fail — all three failures trace
  to the same 4 flags, confirmed with `python3 -m unittest discover -s tests`.
  `content/commands.json` (curated content) and `extract/schema.py` (CR-T-06) are both outside this
  branch's file scope (`extract/extract_flags.py`, `content/flags_rhel{8,10}.json`, `content-src/raw/`,
  docs, and this one `qa.py` addition only), so this is reported rather than worked around, per the
  task brief. Needs one of: (a) curate those 4 flags' `explain` (content authoring, CR-T-33 territory),
  or (b) scope the schema rule to the RHEL version(s) a flags dictionary actually covers rather than
  "any dictionary anywhere is non-empty" (an entry whose `rhel_versions` never reaches 8 or 10 has no
  honest way to satisfy a global rule), or (c) a sequencing call from Zee/Al/Devon on CR-T-09/10 landing
  ahead of CR-T-33. Until resolved, `salm/milo/flags-extract` cannot get a green `build.py`/`qa.py`
  end to end on top of current `main`, though every gate this branch's own files are responsible for
  (Q15's flags check, the extractor's own idempotency) is verified green in isolation — see README.

### Added — v1.0.0-dev engine skeleton (2026-09-17, CR-T-02..05)
- `build.py`: MD CODE RED identity constants, 14-file `CONTENT` map, `validate()` (four mandatory RHEL
  keys, `stig_id` referential integrity, provenance, capture-backed `verified`), `same_as` resolution
  with cycle detection, STIG reverse links, search-index seed, `dist/md-code-red_<version>.html` + `.sha256`.
- `qa.py`: gates Q1-Q17 with a PASS/FAIL line each, the pinned-XCCDF accuracy re-check and CCI
  re-check (`--accuracy`), generated-file integrity, mechanical `innerHTML` audit, and a size
  **report** (`--size`) that can never fail a build.
- `template.html`: five-region shell skeleton (RAIL/SIDEBAR/EDITOR/INSPECTOR/STATUSBAR + PALETTE),
  CSP meta tag, dark/light theme tokens, ES5 IIFE with escaping helpers, guarded storage, theme
  module, data-island loader, and status-bar renderer.
- Skeleton content: 3 STIG-sourced command entries, 3 tools, destructive-pattern table, and generated
  rules/CCI/flags datasets from the pinned DISA sources.
- `tests/test_build_fails_on_broken.py` and six deliberately broken fixtures.
- CI: seven steps — build, QA, accuracy re-check, gitleaks, size report, reproducible-build drift
  check, artifact upload with sha256.

### Planned
- Command Builder engine (P0)
- STIG/NIST tagging and Export as Evidence (P0)
- Git Command Generator (P1)
- Ansible Playbook, Inventory, Config generators (P1)
- Config file generators: sshd_config, chrony.conf, rsyslog.conf, sudoers, systemd units (P2)
- Scenario mode: "Harden a new RHEL 9 host" (P2)
- Bulk evidence export for full STIG checklist (P2)

## v1.0.0 — TBD

### Added
- **Command Builder:** Core toolset (systemctl, firewall-cmd, nmcli, dnf/yum, semanage, useradd, chage, lvm, ssh/sshd, journalctl, auditctl, rsyslog, chronyd, podman) across RHEL 7–10
- **Flag-by-flag explanations** for every generated command
- **STIG/NIST tagging:** CAT I checks with control mappings and expected compliant output
- **Export as Evidence:** SCTM-ready format (command + control + result)
- **Version awareness:** Flags hidden/greyed per RHEL version with "changed in RHEL X" notes
- **Full-text search** across tools, flags, STIG IDs, control numbers
- **Single HTML file:** Zero external dependencies, air-gap clean
- **Source citation:** Every entry cites Red Hat docs, man pages, STIG version/date
- **Dark/light mode** toggle
- **Print-optimized stylesheet**
- **Keyboard operation** for locked-down boxes
- **Favorites & recent** (browser localStorage only)

### Known Issues
- TODO: Backlog items from pilot feedback (add as they surface)

---

## Release Policy

Versioning follows semantic versioning: `MAJOR.MINOR.PATCH`.

- **PATCH:** Bug fixes, source citation updates, single-tool additions
- **MINOR:** New tool or generator, new journey, UI improvements
- **MAJOR:** Architectural change, RHEL version drop, product pivot

Content updates tied to **DISA STIG release cycles** (quarterly).
