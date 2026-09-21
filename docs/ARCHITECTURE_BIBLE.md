# Architecture Bible -- MD CODE RED

Written from the code that ships (`build.py`, `extract/schema.py`, `template.html`,
`qa.py`, `docs/QA_GATES.md`) against the artifact `git clean -fdx dist && python3
build.py` actually produces (never `rm -rf dist` -- `dist/` has carried tracked
release artifacts since v1.0.0-alpha.1 was tagged, and `build.py` does not
regenerate all of them; `docs/QA_GATES.md`'s "Clean rebuild" section says why),
not from the PRD or from ADR-001. Where this document and
ADR-001 disagree, this document is describing what exists today; ADR-001 is the
design record of how the team got there and is not restated here. A skilled
engineer with this file, `docs/QA_GATES.md`, and the source should be able to
rebuild the tool from scratch.

---

## 1. Executive Summary

MD CODE RED is a single static HTML file. Opening it in a browser -- no server, no
network, no install -- gives a RHEL 7/8/9/10 admin a guided way to assemble exact,
version-correct shell commands, see the DISA STIG rule and NIST SP 800-53 controls
a command satisfies, and export a plain-text evidence block for an SCTM/ATO
package. Nothing the page does ever leaves the browser: there is no `fetch`, no
`XMLHttpRequest`, no cookie, and the page's own Content-Security-Policy meta tag
enforces that at the browser level (`connect-src 'none'`), not just by omission.

The file is **built, never hand-edited**: `python3 build.py` reads curated and
generated JSON under `content/`, validates it against `extract/schema.py`, and
substitutes it into `template.html` to produce `dist/md-code-red_<version>.html`.
`python3 qa.py` then runs 25 independent gates (plus an optional Node syntax
check) against the built artifact and fails the build loud on any defect a gate
can see; `docs/QA_GATES.md` states what each gate proves and, as important, what
it does not.

As built (`v1.0.0-alpha.4-dev`, 2026-09-21): 185 curated command
entries across 102 tools (29 guided-form generators and 156 static checks), 14,439
distinct mined reference commands, 1,492 embedded STIG rules across all four RHEL
releases, 200 CCI-to-NIST mappings, and a content fingerprint identifying this
exact data payload. `docs/USER_GUIDE.md` states the remaining evidence and
explanation gaps without treating mined reference material as curated content.

---

## 2. System Architecture

```
  Pinned vendor sources                  Read-only host/container reads
  (stig-src/*.zip, hashed)               (defiant RHEL 8, saratoga RHEL 10,
        |                                 a UBI7 container standing in for
        v                                 RHEL 7 -- see docs/WORKFLOW.md)
  extract/parse_xccdf.py                        |
        |                                        v
        v                                 extract/extract_flags.py
  content/rules_rhel{7,8,9,10}.json              |
  content/cci_nist.json                          v
                                          content/flags_rhel{7,8,9,10}.json
  Hand-authored curated content
  (content/commands.json, tools.json,     tests/captures/<rhel>/<entry>.json
   dangerous.json, glossary.json)         (SME-run captures)
        |                                        |
        |                                        v
        |                                 extract/import_captures.py
        |                                        |
        |                                        v
        |                                 content/expected_output.json
        |                                        |
        +--------------------+-------------------+
                              v
                         build.py
                  (load -> validate -> assemble ->
                   inject into template.html ->
                   escape_island() -> write dist/)
                              |
                              v
              dist/md-code-red_<version>.html
              (one file: static shell + five
               JSON data islands + one app script)
                              |
                              v
                          qa.py
              (25 gates + JS syntax check against
               the SHIPPED artifact, independent
               of build.py's own validation)
                              |
                              v
                    browser, file:// or a share
              (runtime state: sessionStorage for
               RHEL version/theme, localStorage
               for favorites/recent -- both
               schema-versioned, both optional)
```

The build-time half (`build.py`, `extract/schema.py`) and the run-time half
(`template.html`'s app script) share almost no code: the one exception is the
content **schema**, which `extract/schema.py` states once and both `build.py` and
`tests/test_schema.py` import, and the field **validation/assembly rules**, which
`extract/schema.py`'s build-time checks and `template.html`'s run-time assembler
independently re-implement the same decisions (documented together in Section 5)
so that a defect has to be present in both copies to reach the browser.

---

## 3. File-by-File Breakdown

| Path | Role | Notes |
|---|---|---|
| `template.html` | The shell: static markup, inline `<style>`, an empty `<script id="mcr-data">` placeholder, and one `<script>` containing the entire app (~124 KB unminified, ES5). Never opened as the deliverable itself -- it has no data until built. | |
| `build.py` | Loads `content/`, validates via `extract/schema.py`, resolves `same_as` chains and joins captures, injects the JSON data island and five `__TOKEN__` substitutions into `template.html`, writes `dist/md-code-red_<version>.html` and its `.sha256` sidecar. Stdlib only. | See Section 2 above and the docstring at the top of the file, which states the "never patched by hand" rule this whole pipeline exists to enforce. |
| `qa.py` | 25 independent gates (Q1-Q25) plus an optional `node --check`, run against the **shipped artifact**, not against `content/`. Fully documented gate by gate in `docs/QA_GATES.md` -- not duplicated here. | |
| `extract/schema.py` | The one statement of the content schema: `VERSIONS`, `BLASTS`, `LICENSE_CLASSES`, `PRIVILEGES`, `PROVENANCE_FIELDS`, and every `*_errors()` function `build.py`'s `validate()` and `tests/test_schema.py` both call. | No I/O; pure functions over already-loaded JSON. |
| `extract/parse_xccdf.py` | Regenerates `content/rules_rhel{7,8,9,10}.json` and `content/cci_nist.json` from the pinned DISA XCCDF sources in `stig-src/`, after verifying `stig-src/SHA256SUMS`. Deterministic: same pins in, byte-identical files out (no wall clock). `--check` re-runs and diffs, which is what `qa.py`'s Q15 gate calls. | |
| `extract/extract_flags.py` | Regenerates `content/flags_rhel<N>.json` by SSHing (read-only, no sudo) to a real host and parsing `man -P cat` / `--help` output, or by re-parsing already-staged raw text under `content-src/raw/rhel<N>/` in `--check` mode. Never writes prose: every flag's `explain` comes out `null` until a human curates it, and a re-run never clobbers a curated value. | All four release dictionaries currently cover 22 tools; RHEL 7 uses a container. |
| `extract/extract_ansible_doc.py` | Regenerates `content/modules.json` and `content/flags.json` from `ansible-doc --json`. **Not consumed by `build.py`'s `CONTENT` map** -- leftover from the Grey Beard Ansible fork this product started from. See Section 23. | |
| `extract/import_captures.py` | Walks `tests/captures/<rhel_version>/<entry_id>.json`, validates every record against the content validation protocol's field set, verifies `command_hash_at_capture`, and folds STIG-mapped captures into `content/expected_output.json`. `--check` re-runs into a temp dir and diffs (Q15). | The canonical capture path, per Eli Cross's ruling -- see `docs/WORKFLOW.md`. |
| `extract/make_pending_skeletons.py` | Writes empty, honestly-`pending` skeletons for content that has no source yet. | |
| `content/commands.json` | The 185 command entries -- the core curated catalog. Hand-authored; schema in Section 4. | 29 generators and 156 static checks. |
| `content/tools.json` | The 102 tools, their labels, and per-RHEL-version availability (`available`, `reason`, `alternative`). | |
| `content/dangerous.json` | The 15-row destructive-pattern table `blastFor()` matches against every assembled command, both quoted and unquoted. | |
| `content/glossary.json` | Loaded into the data island (`DATASETS.GLOSSARY`) but **never read by any renderer in `template.html`**. Inherited from the Grey Beard Ansible fork; its terms (implicit localhost, delegation, pipelining) are Ansible concepts, not RHEL ones. See Section 23. | |
| `content/rules_rhel{7,8,9,10}.json` | Generated. Every rule in the pinned benchmark for that release: STIG ID, rule ID, CAT, every CCI, verbatim check/fix text, `_meta` (benchmark version, date, sunset flag, rule count). | Never hand-edited (ADR-001 section 6.3, restated in `build.py`'s own header comment). |
| `content/flags_rhel{7,8,9,10}.json` | Generated. Per-tool flag/option name lists with `explain: null` until curated, plus `_meta` naming the host or container that was read. | |
| `content/cci_nist.json` | Generated. CCI -> NIST SP 800-53 Rev 5 control list, filtered to the CCIs the four embedded benchmarks actually cite (200 of the DISA CCI list's ~5,100). | |
| `content/expected_output.json` | Generated, solely by `extract/import_captures.py`. Keyed `entry_id\|stig_id\|rhel_version`; joined onto `commands.json`'s `stig[]` rows by `build.py`'s `assemble()`. | 5 keys in this build. |
| `content-src/roster.json` | The closed SME/QA roster `qa.py`'s Q16 gate checks a capture receipt's `by`/`captured_by` against. | Not shipped in the artifact -- a build-time-only fact. |
| `content-src/flag_coverage_baseline.json` | The dated, ratcheting acceptance baseline Q20 measures flag-dictionary completeness against. Expires 2026-09-25 (`docs/POAM.md`). | |
| `content-src/raw/rhel<N>/*.man.txt` | Staged, git-ignored raw `man`/`--help` captures -- the source of record for licensing review and for Q14's paraphrase-collision check. Never read by `build.py`. | |
| `content/checklists.json`, `dossier.json`, `drills.json`, `errors.json`, `letter.md`, `modules.json`, `rhel_flags.json`, `scars.json`, `snippets.json`, `trees.json`, `flags.json` | Present under `content/` but **absent from `build.py`'s `CONTENT` map** -- none of these reach the shipped artifact. Leftover from the Grey Beard Ansible fork (`modules.json`/`flags.json` are `extract_ansible_doc.py`'s own output). | See Section 23. |
| `tests/` | `tests/hostile_harness.js` (the pure assembler, lifted and fuzzed under Node), `tests/test_*.py` (unittest, run via `python3 -m unittest discover -s tests`), `tests/fixtures/golden-commands.json` (the hand-authored validity oracle), `tests/captures/` (real SME capture records). | 339 unittest cases and 101,957 harness checks pass on this build. |
| `stig-src/` | The pinned DISA STIG/CCI zip sources and their SHA-256 sums -- the source of record `extract/parse_xccdf.py` reads from. | |
| `NOTICE` | The per-family licensing derivation statement (public-domain vs. paraphrase-only, and where each family's raw source is staged). | |

---

## 4. Data Models

All shapes below are enforced by `extract/schema.py` at build time and, for the
shell's own read of the assembled island, implicitly by how `template.html`
indexes into them (a field the schema allows but the renderer never reads is
dead weight, not a defect -- see Section 23 for `glossary.json`, the one real
example).

**Command entry** (`content/commands.json`, one of two shapes):

*Static (fixed per-RHEL-version command)* -- 156 of 185 entries:
```
{
  id, tool, explain_tool?, category, intent,
  rhel_versions: { "7": slot, "8": slot, "9": slot, "10": slot },
  flags: [ {flag, explain, source_ref, license_class} ],
  verify, undo, blast: "green"|"yellow"|"red",
  privilege?: "root",
  source: {title, url_or_man, version, retrieved_on, license_class},
  verified: { "7": false|receipt, "8": ..., "9": ..., "10": ... },
  stig?: [ {stig_id, rhel_version, cci?, nist?} ]
}
```
A `slot` is one of: `{command, notes?, changed_in_note?}`, `{same_as: "<version>",
changed_in_note?}`, or `{unavailable: {reason, alternative?}}`. A `receipt` is
`{by, on, host, capture}` -- see Section 6.

*Generator (guided form)* -- 29 of 185 entries:
```
{
  id, tool, category, intent,
  fields: [ {name, type, required, options?, versions?} ],
  template: [ token, token, ... ],
  versions?: ["7","8","9","10"],   // omitted means offered on all four
  blast, verify, undo, source, privilege?
}
```
A `token` is one of a literal (`{lit}`), a flag/value pair (`{flag, field,
optional?, eq?, join?}`), a conditional literal (`{lit, requires}`), or a rich
rule (`{richRule: {family, source?, destination?, service?, port?, protocol?,
action}, flag?}`). Section 5 covers assembly in full.

**Tool** (`content/tools.json`):
```
{ id, label, binary, availability: { "7": {available, reason?, alternative?},
  "8": ..., "9": ..., "10": ... } }
```

**Rule** (`content/rules_rhel<N>.json`, per release):
```
{ i: stig_id, r: rule_id, t: title, c: "I"|"II"|"III",
  cci: [ "CCI-XXXXXX", ... ], n: [ "NIST control", ... ],
  chk: check_text, fix: fix_text, cmds: [entry_id, ...] }
```
`cmds` is a reverse link `build.py`'s `assemble()` computes from every entry's
`stig[]` rows -- it does not exist in the raw XCCDF parse.
`_meta`: `{version, benchmark_date, sha256, rule_count, cat_counts, sunset,
partial: false}`.

**Flag dictionary** (`content/flags_rhel<N>.json`):
```
{ _meta: {rhel_version, host, redhat_release, kernel, captured_on, source, ...},
  clis: { "<tool>": { available: true, flags: [ {names: [...], takes_arg,
          explain: null|string} ], unparsed: [...] } | {available: false, reason} } }
```

**CCI/NIST map** (`content/cci_nist.json`): `{ cci: { "CCI-XXXXXX": {nist:
["AC-6", ...]} } }`.

**Destructive pattern** (`content/dangerous.json`): `{id, match, label, why,
blast_floor}` -- `match` is a case-insensitive literal substring checked against
both the fully assembled command and its unquoted projection (Section 5).

**Capture record** (`tests/captures/<rhel_version>/<entry_id>.json`): the content
validation protocol's field set -- `entry_id`, `rhel_version`, `host`,
`redhat_release`, `kernel`, `pkg_versions`, `command_as_run`, `exit_code`,
`stdout`, `stderr`, `captured_on`, `captured_by`, `blast_confirmed`,
`undo_executed`, `command_hash_at_capture`, `verify_result` -- see
`docs/WORKFLOW.md` for the full capture-to-receipt flow and `qa.py`'s
`CAPTURE_REQUIRED_FIELDS`.

---

## 5. Command Builder Engine

The assembler (`assembleCommand()`, fenced by `MCR-ASSEMBLER-BEGIN`/`-END` markers
in `template.html`) is deliberately **pure**: no `document`, `window`, storage, or
data-island reference inside the fence. `tests/hostile_harness.js` and `qa.py`'s
Q18 gate both lift the block verbatim out of the shipped artifact and run it under
Node, so the code proved safe by CI is the exact code the browser runs.

**Field types** (`FIELD_TYPES`, ~24 entries) are an allow-list, never a filter: a
value is checked with a full-string regex, a hand-written validator function
(`isIpv4`, `isPath`, ...), or an enum, capped in length, and rejected outright
rather than trimmed or transliterated. Every type but one (`comment`) is
ASCII-only and rejects a leading dash (which the target tool would read as an
option). `comment` is the single free-text type in the product and is still
POSIX-single-quoted (`shQuote()`) before it reaches a command line.

**Assembly walks `template[]` once**, producing `null` -- never a partially built
string -- the instant anything is wrong:

- A **literal** (`{lit}`) is emitted verbatim if it matches a closed character
  class; if it is *option-shaped* (matches `FLAG_TOKEN_RE`, e.g. `-T`, `--permanent`)
  it is also pushed into the flags list so the Inspector explains it, even though
  it carries no separate value.
- A **conditional literal** (`{lit, requires: "<field>"}`) drops only if the field
  it names is absent -- and, if it is *positional* (an argument, not an
  option-shaped word), only if every *later* positional token also drops, so
  argument N+1 can never silently shift into argument N's place.
- A **flag/value token** (`{flag, field}`) is dropped only when `optional: true`
  is declared, subject to the same positional-shift rule. The join between the
  flag and its value is **derived from the flag's own shape**, not authored per
  token: a `--long` flag joins with `=`; a single-dash flag joins with a space,
  because GNU `getopt()` hands a `-X=value`'s `=` straight through as the first
  character of the value rather than treating it as a separator. Two narrow
  escape hatches (`eq:false` on a long flag, `join:"glued"` on a short one) exist
  for the tools that genuinely need them; a token declaring a join its own shape
  already derives is refused as a disagreement, not resolved by guessing.
- A **rich rule** (`{richRule}`, used only by the three `firewall-cmd` generators)
  is composed from independently validated sub-fields against a fixed slot table
  (`RICHRULE_SLOT_TYPES`) -- `comment` and `enum` are deliberately excluded as
  rich-rule sub-field types, because firewalld's rich-rule attribute syntax has no
  escape for a quote inside a value, so there is no free-text path into a rich
  rule at all, by construction.

Every resolved value is **shell-quoted uniformly** (`shQuote()`, POSIX single
quotes, `'` escaped as `'\''`) -- there is no "this value looks safe, leave it
bare" branch. The **blast rating** is computed over the fully assembled,
already-quoted command *and* its unquoted projection (`unquoteCommand()`), against
`content/dangerous.json`'s pattern table, so a pattern like `rm -rf /` still fires
against `rm -rf '/etc/pki'` even though the quoting inserts a `'` at the boundary.
An entry's own declared `blast` is a floor, never lowered by the pattern scan.

One rendered-state object (`RESULT`, keyed on RHEL version + entry id + a stable
serialization of the live form values) is computed once per interaction and read
by the gutter, the blast banner, the Inspector, the clipboard payloads, and the
evidence exporter -- none of them re-assemble the command independently, so what
an ISSM signs off on and what the operator's clipboard holds cannot diverge.

---

## 6. STIG/NIST Tagging System

A command entry cites zero or more STIG rows (`stig[]`, one row per STIG ID per
RHEL version it applies to: `{stig_id, rhel_version, cci?, nist?}`). At render
time, `ruleFor(stigId, version)` looks the row up in that version's embedded rule
set for title, CAT, verbatim check/fix text, and its own CCI list (a row can
override the rule's CCIs, though none currently do); `nistForCci()` walks the
CCI-to-NIST map to produce the crosswalk. The STIG panel (`renderStigPanel()`)
renders this for both a selected command entry and a **standalone** rule reached
via search with no linked command (Section 9) -- the same function, the same
markup, in either case, plus a sunset banner when the release's `_meta.sunset` is
true and a "changed in RHEL X" note when the current entry's slot carries one.

**Verification is per RHEL version, not per entry** (a CEO ruling closing a real
review finding: a single whole-entry flag could not be set without overclaiming a
version nobody independently ran). `entry.verified[version]` is either `false` or
a receipt `{by, on, host, capture}`. `verificationStatusForVersion()` is the one
function that turns that plus a joined capture into the three UI states
documented in `docs/USER_GUIDE.md` (Verified / Captured / Not host-verified) --
read by the Inspector, the status bar, and the evidence exporter, so the three
places cannot disagree. A `same_as` or `unavailable` version can never carry its
own receipt (`extract/schema.py`'s `verified_errors()` refuses it at build time):
it was never independently run, even when its command text is identical to a
version that was.

---

## 7. Visualization & Rendering

There is no virtual DOM and no templating library: every renderer builds one HTML
string by concatenation and assigns it to exactly one element's `innerHTML`, or
(for the storage-guard, the assembler, and other pure blocks) returns data that a
caller renders. This is deliberately auditable rather than merely convenient:
`qa.py`'s Q17 gate statically proves every segment reaching an `innerHTML` sink,
or a derived string accumulator, is either a literal or a call to `esc()` /
`escapeAttr()` / `escapeRegex()` -- never a bare call to another render function,
whose returned markup the gate cannot see the inside of. Every renderer in
`template.html` follows the same shape for exactly this reason: one accumulator
variable per function, filled by string-literal `+=` and escaper calls only, with
any other renderer that shares a screen region (e.g. `renderStigPanel()` inside
`renderInspector()`) called as its own separate statement writing its own sink,
never spliced into the caller's accumulator.

Regions and their owning renderer: rail (`renderRail`), version selector
(`renderVersionSelector`), sidebar/tool list (`renderToolList`,
`renderFavoritesSidebar`), editor (`renderEditor`, `renderGeneratorEditor` +
`renderGeneratorForm` + `renderGeneratorResult` for generators, `renderAbout` for
the About rail), blast banner (`renderBlastBanner`), inspector
(`renderInspector`), STIG panel (`renderStigPanel`, writing both the on-screen
`#stig-panel` and the print-only `#print-stig-panel` from one accumulator),
status bar (`renderStatusBar`), palette (`renderPalette`), evidence modal
(`renderEvidenceModal`). `renderAll()` is the top-level re-render, called after
every state-changing action; a generator's field keystrokes instead call the
narrower `renderGeneratorResult()`/`onFieldChange()` path so a text input never
loses focus mid-word (Section 15).

---

## 8. Export as Evidence

`exportEvidence()` gathers the current rendered result plus the matched STIG row
and rule (never recomputing the command) and hands them to `formatEvidenceText()`
-- a pure function, lifted and tested the same way the assembler is
(`tests/test_evidence_export.js`/`.py`, `tests/test_evidence_export_real.js`/`.py`
snapshot the REAL evidence text for a real entry against a committed fixture, so
the documented sample and the shipped artifact cannot drift apart). The full
field list is documented for the reader in `docs/USER_GUIDE.md`'s "Export as
Evidence" section and is not repeated here.

Two things make this export trustworthy on an air-gapped host with nothing to
compare it against: the **content fingerprint** (sha256 of the exact bytes inside
`<script id="mcr-data">`, computed by `build.py` *before* the payload is
substituted into the template so it is never a hash of a string containing
itself, embedded as a plain constant, and independently re-checked by `qa.py`'s
Q1 gate against a fresh hash of the shipped island), and **line safety**
(`evidenceHeaderSafe()`/`evidenceLineSafe()`, sharing `MCR-ASSEMBLER`'s
`INVISIBLE_RE_G` table rather than a second hand-rolled copy, after that second
copy was found to have already drifted once). A bidi override or a raw NUL
character in DISA fix text is stripped from this plain-text export the same way
it is stripped from the clipboard comment header -- the export crosses into an
SCTM/ATO package, a trust boundary `esc()`'s HTML-entity encoding does not by
itself protect.

---

## 9. Search & Indexing

`buildIndex(datasets)` (pure, `MCR-INDEX-BEGIN`/`-END`) walks the whole content
island once -- tools, command intents, curated per-entry flags, all four
per-release flag dictionaries, all four releases' STIG rules, and the CCI/NIST
map -- into one flat array of `{kind, id, tool, version, cat, label, hay}`
records, `hay` being the lowercase haystack a query matches against. It is built
**lazily**, on the first palette keystroke (not at page load), and cached for the
rest of the page's life (`SEARCH_INDEX`, outside the pure block).
`tests/test_search_index.js` lifts the block out of the shipped artifact and
times it against this exact embedded dataset -- both build and query measure well
under 100 ms, as a number the test suite prints, not a claim this document makes.

`queryIndex(index, q)` requires every whitespace-separated term to match somewhere
in a record's haystack (AND, not OR), scores a word-start match higher than a
mid-word substring match, sorts by score, and groups the results by `kind` in a
fixed order (Tool, Command, STIG, Flag, CCI, NIST), each group capped at 8. A CCI
or NIST hit has no command of its own to open -- `activateCrosswalkHit()` resolves
it to the first embedded rule that cites it, current RHEL version searched
first, then the other three in order.

---

## 10. Version Management

`RHEL_VERSIONS = ["7","8","9","10"]` is the single source of truth for which
releases exist; every gating decision reads it or the entry/tool's own
per-version data, never a second hard-coded list. A tool unavailable on the
selected release, or a command entry whose slot for that release is
`unavailable`, stays on screen **disabled**, carrying its reason and (when one is
declared) its alternative in a `.why` line and a tooltip -- `entryGateInfo()` /
`toolAvailability()` are the two functions that answer "is this offered here, and
why not if it isn't" for a static entry and a generator spec respectively, and
both return a reason string rather than a boolean, so the sidebar never merely
hides a row. Switching versions (`setVersion()`) resets the red-blast
acknowledgement (a new version is a new command to review) and persists the
choice to `sessionStorage` only -- it does not survive a fresh open of the file.

---

## 11. Browser State Management

One guarded module (`STORE`, `MCR`-namespaced `mdcr.v1.`) is the only path to
`localStorage`/`sessionStorage` in the file -- every accessor is its own
try/catch (so a `file://` page whose browser blocks storage degrades to "nothing
persisted" rather than throwing) and every stored value is wrapped
`{schema, data}`; a schema mismatch on read is discarded silently rather than
trusted. `qa.py`'s Q7 gate proves every storage identifier sits inside a
try/catch by counting braces over a **lexically masked** copy of the source (so a
brace inside a string or regex literal cannot desynchronize the count).

What is actually stored: RHEL version and theme choice in `sessionStorage`
(session-only, by design); the last-opened tool id, and favorites/recent **entry
ID lists only** in `localStorage`. `sanitizeIdList()` (`MCR-FAVORITES-BEGIN/-END`,
also lifted and fuzzed by `tests/test_favorites_store.js`) is the one choke point
a value read back out of storage passes through: not a string, too long, a
duplicate, or an ID that does not resolve against the *live* content island (an
older build's favorite) is dropped silently rather than rendered blank or as raw
stored text. Nothing but an ID ever round-trips through storage -- there is no
path from `localStorage` back into `innerHTML`.

---

## 12. Keyboard & Accessibility

One delegated `keydown` listener and one binding table (`KEYMAP`) implement the
entire keyboard surface -- `docs/USER_GUIDE.md`'s keyboard table is checked
against this exact array, which is the only place a binding can be added or
changed. Palette-local navigation (arrow keys, Enter, a `Tab` focus trap) and
gutter-line activation are handled ahead of the table because they are contextual
to an open overlay or a specific element, not a global shortcut. Every focusable
control shows a visible focus ring (`:focus`/`:focus-visible`, never removed
without a replacement); the icon-only rail buttons reveal their text label on
both focus and hover so a keyboard user reads the same word a mouse user does.
ARIA is used structurally throughout (`role="navigation"/"complementary"/
"main"/"contentinfo"/"dialog"/"alert"/"listbox"/"option"`, `aria-current`,
`aria-pressed`, `aria-disabled`, `aria-modal`) rather than decoratively. No
screen-reader testing is claimed or has been recorded; the ARIA roles and focus
management are the extent of the accessibility work done, documented honestly
rather than inflated (Section 23).

---

## 13. Ansible Generators

The activity rail's **Ansible** item (`Ctrl+Alt+3`) is live. It uses the same
generator registry and renderer as the Command Builder, filtered to the Ansible
tool category. Three entries generate a playbook plus its invocation, an
inventory plus `ansible-inventory --graph`, and an `ansible.cfg` plus
`ansible-config dump --only-changed`. Generated YAML and INI are composed by
`composeDoc()` from typed fields and are covered by the hostile harness's
structure and round-trip oracles.

---

## 14. Git Command Generator

**Not implemented in this build**, and not represented anywhere in the current UI
(no rail item, no placeholder). Phase 2 backlog (`docs/IDEAS.md` 260917-002).

---

## 15. Event System & Form Handling

Two delegated listeners on `document` (`click`, and a shared `input`/`change`
handler for generator fields) are the entire event surface -- there is no inline
`onclick`/`onchange` anywhere in the shell (`qa.py`'s Q17 gate would fail the
build if there were). The click router matches the event target against a fixed
set of `closest("[data-*]")` selectors in priority order (`data-version`,
`data-rail`, `data-tool`, `data-entry`, `data-hit`, `data-line`, the palette/
evidence-modal backdrops, then `data-action`) and dispatches once it finds the
nearest match -- adding a new clickable region means adding a `data-*` attribute
and a branch here, never a second listener.

Generator field input is split from the rest of the editor on purpose:
`onFieldChange()` writes into `STATE.formValues` and calls only
`renderGeneratorResult()` + `renderInspector()`, never the full `renderEditor()`
that would rebuild the field `<input>` elements themselves and drop focus/cursor
position mid-keystroke. `renderGeneratorForm()` (the field frame) is rebuilt only
on entry selection or a RHEL version change.

Validation happens in one place regardless of caller: `validateSpec()` (used by
the UI to explain *which* field is wrong and why) and `assembleCommand()`'s own
internal checks (used to actually build or refuse the command) are both reads of
the same `FIELD_TYPES` table and the same per-field `required`/`versions`
declarations -- there is no second, looser validation path a generator can fall
through.

---

## 16. Feature Specs & User Journeys

The three journeys this build actually supports -- guided-form command
generation, STIG evidence lookup and export, and reviewing a command's blast
level before copying it -- are specified step by step, with real UI labels and
keys, in `docs/USER_GUIDE.md`. That document is the feature spec; this section
exists only to point at it rather than duplicate it, per the same rule Section 6
of `docs/QA_GATES.md` follows for gate detail.

---

## 17. Algorithms & Logic

**Search scoring**: term-AND matching with a word-start bonus (score +3) over a
mid-word substring match (score +1), summed per term, sorted descending, grouped
by kind (Section 9). No stemming, no fuzzy matching, no synonym table.

**The positional-shift rule** (`isPositionalToken()` / `laterPositionalSurvives()`,
Section 5): the same question -- "does any later argument-slot token survive if
this one is dropped" -- answers whether a droppable field token *or* a droppable
option-shaped-but-conditional literal is allowed to vanish. An option-shaped
literal (matches `FLAG_TOKEN_RE`) is never positional regardless of whether it is
conditional, because dropping an option can never shift an argument into its
place.

**Blast escalation** (`blastFor()`, Section 5): an entry's declared `blast` is a
floor; the destructive-pattern table can only raise it, never lower it, and is
checked against both the assembled command and its unquoted projection so
quoting cannot hide a match. `content/dangerous.json`'s 11 rows are each proved
to fire against a synthetic assembled command by `tests/hostile_harness.js` --
a pattern that can never match fails the build, not just a code review.

**Version gating**: read directly from the entry/tool's own declared
availability (Section 10) -- there is no derived "is this version older/newer"
logic anywhere; RHEL 9 is not assumed to inherit RHEL 8's behavior except where
an entry's own `same_as` explicitly says so.

---

## 18. Error Handling & Logging

There is no logging framework and no server to log to. The product's error
philosophy is stated once and applied everywhere: **a wrong or incomplete result
is `null`, never a partially built one.** `assembleCommand()` returns `null` on
any missing required field, invalid value, gated field, or malformed template
token -- there is no second return shape carrying a half-formed string for the
caller to patch up or explain. The UI surfaces this as either a specific,
plain-English reason per field (`validateSpec()`'s `missing`/`invalid` lists,
shown under "Fill in the required fields") or a short status-bar toast for a
user action with nothing to act on yet (`"Nothing to copy -- no complete command
is assembled."`, `"Nothing to export -- select a command or a STIG rule first."`,
`"No embedded STIG rule cites <id> in this build."`). A copy or clipboard
failure -- the comment header could not be rendered as safe single-line text, or
`document.execCommand("copy")` itself failed -- is reported the same way, with a
concrete next step (`"select the text ... and use your browser's copy"`), never a
silent no-op.

---

## 19. Performance & Limits

**Size**: reported, never enforced -- the Founder ruled the ceiling unlimited on
2026-09-17. This build's artifact is 2.36 MB (2,471,136 bytes): 2.22 MB data
island, 0.14 MB shell. `qa.py` prints this on every run; it cannot fail a build
over it.

**Search**: index build and query both measure well under 100 ms against this
build's full ~4,000-record index (`tests/test_search_index.js`, timed, not
estimated).

**Storage**: `localStorage` favorites are capped at 200 entries, recent at 20;
both are silently truncated (oldest dropped) past the cap rather than growing
without bound or erroring.

**Load time and localStorage quota** under real air-gapped browser conditions
(an old Firefox ESR or Chromium on a RHEL or Windows jump box, opening a 2.36 MB
`file://` document) have not been benchmarked and are not claimed here --
`docs/USER_GUIDE.md`'s Troubleshooting section covers what happens if storage is
blocked outright, which is the condition that has actually been designed for and
tested (Section 11), as distinct from how fast it loads, which has not.

---

## 20. Security & Input Validation

The full rule set -- escaping, storage guards, air-gap enforcement, the
never-half-formed rule, and every gate that proves each of them against the
shipped artifact -- is `docs/CODE_STANDARDS.md` and `docs/QA_GATES.md`; this
section is a map into them, not a third copy. In outline: every value a user
supplies is validated against a closed field-type grammar before it can reach a
command (Section 5); every value rendered into the DOM crosses `esc()` or
`escapeAttr()` at the render call site, checked mechanically by `qa.py`'s Q17
(the escapers are *called*) and Q19 (the escapers *actually escape*, run live
under Node against ~95 hostile vectors); the file's own CSP meta tag makes the
air-gap guarantee enforceable rather than merely a stated intent (Section 1); and
`qa.py`'s Q21 gate scans every tracked source file, not just the shipped
artifact, for raw invisible/bidi/zero-width characters, so a hostile character
cannot even enter the repository undetected. The one residual stated everywhere
it applies, not hidden: a property or API name assembled at *run time* from
something that is not a string literal is invisible to a static scan -- this is
an accident-prevention design for code reviewed by `CODEOWNERS`, not a sandbox
against a determined author with commit rights, and was never claimed to be one.

---

## 21. Design Patterns & Code Structure

**One file, two `<script>` elements, ES5, an IIFE.** The entire app script is one
`(function(){ "use strict"; ... })()`, targeting engines old enough to still be
running on an air-gapped jump box (the shell polyfills `NodeList.prototype.forEach`
and `Element.prototype.matches`/`closest` for exactly this reason). No `let`/
`const`/arrow functions/template literals/classes in the shipped app script --
`var` and `function` throughout.

**Marked, liftable blocks.** Five regions are fenced with `MCR-<NAME>-BEGIN`/
`-END` comment markers and are each pure (no `document`/`window`/storage/data
island inside the fence): the assembler (`MCR-ASSEMBLER`), the search index
(`MCR-INDEX`), the evidence formatter (`MCR-EVIDENCE`), the favorites ID
sanitizer (`MCR-FAVORITES`). Tests lift each block verbatim out of the *shipped*
artifact by these markers and exercise it under Node, so what CI proves safe is
provably the code the browser runs, not a hand-copied approximation of it.

**One accumulator per renderer**, enforced by Q17's static audit (Section 7) --
this is the load-bearing convention that makes the render-safety gate possible at
all, and every new renderer has to follow it or the gate stops being able to see
inside it.

**Content over code.** A generator is not a second registry: it *is* a
`commands.json` entry whose shape happens to carry `fields[]`/`template[]`
instead of `rhel_versions` (`isGeneratorEntry()` is the one-line test everywhere
this distinction matters). Adding a 25th tool to the catalog is a content change,
not a code change, unless it needs a field type or a rich-rule slot type that
does not exist yet.

**Naming**: `render*()` for a function that writes a DOM sink; `*Errors()` (in
`extract/schema.py`) for a function returning a list of human-readable problem
strings, empty meaning clean; `*For()` (`blastFor`, `ruleFor`, `nistForCci`,
`ratesFor`-style helpers) for a pure lookup; `is*()`/`has*()` for a boolean
predicate. CSS classes are BEM-adjacent but not strict BEM (`.railbtn .lbl`,
`.codeline .ln`/`.lc`, `.vbadge.v-verified`) -- component-scoped, not a formal
methodology.

---

## 22. External Dependencies & Vendor Code

**None, by design.** No embedded library, no vendored JS, no font file, no image
asset beyond what CSS alone provides. The CSP meta tag (`script-src
'unsafe-inline'`, everything else `'none'` or `data:`) makes adding an external
dependency a build-breaking change, not a style violation -- Q2 additionally
scans for any network-capable API reached by a bracketed, fused, or aliased name,
so the restriction cannot be routed around at the JavaScript level either
(residual stated in Section 20). Vendor **content** (DISA STIG/CCI text, RHEL
documentation, man pages, Ansible's own documentation tooling output) is
embedded as data, cited by `source`, and staged raw under `content-src/raw/` for
audit -- see `NOTICE` for the full per-family licensing statement and README.md's
Attribution section for the required verbatim block.

---

## 23. Hidden Assumptions & Gotchas

- **`content/glossary.json` is dead weight.** It is loaded into the data island
  (`DATASETS.GLOSSARY = DATA.glossary`) but no renderer in `template.html` ever
  reads it, and its content (Ansible concepts: implicit localhost, delegation,
  pipelining) is inherited from the Grey Beard Ansible fork this product started
  from -- it is not even about the right subject. It inflates the artifact for no
  UI benefit. Either wire a glossary view to it (Section 25 covers what a RHEL/
  STIG-specific glossary would need instead) or drop it from `build.py`'s
  `CONTENT` map.
- **Ten files under `content/`** (`checklists.json`, `dossier.json`, `drills.json`,
  `errors.json`, `letter.md`, `modules.json`, `rhel_flags.json`, `scars.json`,
  `snippets.json`, `trees.json`) **and `content/flags.json`** are present on disk
  but absent from `build.py`'s `CONTENT` map -- also fork leftovers. They do not
  reach the artifact and do not affect the build, but a future engineer grepping
  `content/` for "what does this tool ship" will find them and reasonably wonder;
  worth a cleanup pass.
- **RHEL 7 has no real host in the lab.** Its flag dictionary is extracted from a
  UBI7 *container* standing in for a RHEL 7 host, which means kernel- and
  systemd-manager-dependent behavior (real unit activation, live journald state)
  was never observed for RHEL 7 -- only each tool's own `--help`/man text as
  shipped in the container's packages. `content/flags_rhel7.json`'s own `_meta`
  states this caveat (`kernel_caveat`); it is easy to miss if you only read the
  UI.
- **RHEL 9 is the default version on load** (`STATE.version = "9"`) despite
  having the least populated content of the four releases (no flag dictionary,
  no captures). A first-time operator's first impression is the release with the
  most "unverified -- see man page" text in the build.
- **`file://` storage is not guaranteed.** Every `localStorage`/`sessionStorage`
  access degrades silently (Section 11); this is correct behavior, but it means
  "my favorites disappeared" is an expected outcome on some hardened browser
  profiles, not a bug to chase.
- **No screen-reader testing is recorded.** ARIA roles and focus management are
  implemented carefully (Section 12), but "keyboard-operable" and "screen-reader
  tested" are not the same claim, and only the first has evidence behind it.
- **English and desktop only**, by omission rather than by an explicit design
  decision recorded anywhere in code -- there is no i18n scaffolding and no
  mobile layout beyond the 1024px responsive breakpoint that stacks the
  inspector under the sidebar.

---

## 24. Rebuild & Modernization Path

**Add a tool or a command entry**: author a `content/commands.json` entry
(static or generator shape, Section 4), add or update its `content/tools.json`
availability row, run `python3 build.py && python3 qa.py`. No template or build
code changes for a tool whose fields fit the existing `FIELD_TYPES` table and
whose rich-rule needs (if any) fit `RICHRULE_SLOT_TYPES`.

**Add a field type**: extend `FIELD_TYPES` in `template.html` (the run-time
half) and the matching validator in `extract/schema.py` (the build-time half) --
both, or the two halves disagree about what a valid value is, which is exactly
the drift the schema's existence is meant to prevent.

**Populate RHEL 9's flag dictionary, or a real RHEL 7 host's**: run
`extract/extract_flags.py --host <alias> --rhel <N>` against a reachable,
read-only-permitted host; commit the raw captures under `content-src/raw/rhel<N>/`
and the parsed `content/flags_rhel<N>.json`. Curating `explain` text for any
dictionary is a separate, human, paraphrase-only step (`docs/CODE_STANDARDS.md`)
that a re-run of the extractor never overwrites.

**Refresh a STIG release**: re-pin `stig-src/` (new zip, new SHA-256, both
committed together per `stig-src/SOURCES.md`'s own rule), re-run
`extract/parse_xccdf.py`, rebuild. See `docs/WORKFLOW.md`'s quarterly refresh
cycle.

**Add a fifth RHEL release**: touches more than content -- `VERSIONS` in
`extract/schema.py`, `RHEL_VERSIONS` in `template.html`, every per-version object
shape in Section 4, and the STIG/flags/rules content triad. Budget this as a
cross-cutting change, not a content-only one.

**A web-hosted (non-file://) version, or a second output format (Markdown,
PDF)**: out of scope for this architecture as it stands -- the single-file,
zero-network design is load-bearing for the air-gap guarantee (Section 1), not
an artifact of the current build tooling. Either would need its own design
review, not a `build.py` flag.

---

## 25. Glossary

This is documentation prose, not shipped content. `content/glossary.json`
(the Ansible-fork glossary this section's own note points at) is present in
the repo but not shipped in the alpha: `build.py`'s `CONTENT` map dropped it
for v1.0.0-alpha.1 (AL-GATE3-011, CEO decision, Gate 3 review
ENG-2026-09-18-002 section 8.1 item 2) because it shipped embedded and
unreachable -- no Glossary kind in the search index, no rail, no panel, no
renderer. The file stays committed for a later tranche that wires a real
RHEL/STIG glossary view, at which point this section becomes the design
reference for that view rather than a description of dead weight.

- **Air-gapped network**: a network with no physical or logical connection to the
  public internet or any external network -- the deployment context this tool is
  built for.
- **ATO**: Authorization to Operate -- the formal DoD/federal risk-acceptance
  decision that follows a completed body of evidence.
- **Blast radius / blast level**: this product's own term (not a DISA/NIST term)
  for how disruptive a command is if run: green (read-only), yellow (a
  reversible state change), red (destructive, gated behind a review checkbox).
- **CAT I/II/III**: DISA's severity categories for a STIG finding -- CAT I is the
  most severe (a control that, if violated, directly and immediately risks
  compromise).
- **CCI**: Control Correlation Identifier -- DISA's fine-grained identifier
  linking a specific, testable requirement to one or more NIST SP 800-53
  controls. One STIG rule typically cites several.
- **Content fingerprint**: this product's own term for the sha256 hash of the
  exact bytes inside the shipped file's embedded JSON data island -- see
  Section 8.
- **Data island**: the `<script id="mcr-data" type="application/json">` element
  holding the entire content payload as JSON text, read once at page load via
  `JSON.parse`.
- **Jump box**: an isolated, often air-gapped administrative host used to reach
  or manage other systems inside a restricted enclave.
- **NIST SP 800-53**: the NIST Special Publication defining the security and
  privacy control catalog federal/DoD systems are assessed against.
- **Same_as chain**: this product's mechanism for one RHEL version's command slot
  to point at another version's identical command rather than repeating it --
  resolved at build time, cycle-guarded, and explicitly barred from ever carrying
  its own verification receipt (Section 6).
- **SCTM**: Security Control Traceability Matrix -- the artifact this tool's
  evidence export is formatted to feed directly into.
- **STIG**: Security Technical Implementation Guide -- DISA's configuration
  standard for a given product or platform, published as an XCCDF benchmark.
- **XCCDF**: the Extensible Configuration Checklist Description Format DISA
  publishes STIG benchmarks in -- the source format `extract/parse_xccdf.py`
  parses.

---

## Appendix: Rebuild Verification Checklist

Run in order from a clean checkout; every step should be green before trusting a
change. Use `git clean -fdx dist`, never `rm -rf dist`: `dist/` has carried
tracked release artifacts since v1.0.0-alpha.1 was tagged, `build.py` does not
regenerate all of them, and `git clean -fdx dist` removes only what git does
not track (`docs/QA_GATES.md`'s "Clean rebuild" section says why):

1. `git clean -fdx dist && python3 build.py` -- clean build, no schema errors,
   prints a sha256 and a content fingerprint.
2. `python3 qa.py` -- all 25 gates plus `JS` PASS (Node required for Q18/Q19;
   `JS` correctly downgrades to PENDING without it).
3. `python3 -m unittest discover -s tests` -- 204 tests OK on this build.
4. `node tests/hostile_harness.js` -- 81,577 checks, 0 FAILED.
5. Build twice from the same sources (`git clean -fdx dist && python3 build.py`
   a second time on the same day) and diff the two artifacts -- they should be
   byte-identical (`build.py` has no wall-clock dependency beyond the build date,
   which is stable within a day).
6. Open the built file in a real browser and drive it by hand for the three
   journeys in `docs/USER_GUIDE.md` -- the automated gates prove structure and
   safety, not that the UI is usable; nothing here substitutes for actually
   looking at it.

## Appendix: Known Unknowns

- **Web-hosted or multi-format delivery** (a server-hosted version, a PDF/
  Markdown export): out of scope as designed -- see Section 24.
- **Mobile support**: out of scope by omission, not a stated decision -- see
  Section 23.
- **i18n / non-English content**: not started; no scaffolding exists.
- **`content/glossary.json`'s fate**: either wire a real RHEL/STIG glossary view
  to it, or remove it from `build.py`'s `CONTENT` map -- see Section 23.
- **The ten unreferenced `content/*.json`/`.md` files** left over from the fork:
  candidates for a cleanup pass, not a functional gap -- see Section 23.
