# QA Gates — what each one proves, how it was watched failing, and what it does not cover

`python3 qa.py` runs **Q1–Q22 plus one unnumbered `JS` gate**: 23 rows in `GATES`,
one PASS/FAIL line each, non-zero exit on any FAIL. This file is the map.

It exists because of a sentence in Al Kowalski's BQP Gate 3 review of `qa.py`
(2026-09-18, PASS WITH ISSUES):

> A gate with no negative control is not disproven — it is simply a gate nobody
> has watched fail, which is the exact posture Marcus's own commit messages
> argue against ("a checker that has never been seen to fail proves nothing").

Three columns matter for every row below, and the third is the one that is
usually missing from documents like this:

| Column | Question it answers |
|---|---|
| **Proves** | What is true of the artifact when this gate says PASS. Stated narrowly. |
| **Negative control** | Where somebody has watched this gate FAIL on input engineered to break it. A gate with none is not accused of anything; it is simply unwatched. |
| **Residual** | What a PASS explicitly does **not** mean. A gate described as unbypassable stops being questioned, which is worse than one whose limits are written down. |

`qa.py` is itself trust-path code — it is the merge gate — so its own defects are
tracked with IDs (`MCR-SEC-*` from Marcus Reed's security reviews, `AL-GATE3-*`
from Al's Gate 3 diff review) and referenced in the rows they belong to.

## Clean rebuild: `git clean -fdx dist`, never `rm -rf dist`

`dist/` has carried tracked release artifacts since v1.0.0-alpha.1 was tagged:
`md-code-red_v1.0.0-alpha.1.html`, its `.sha256` sidecar, and its
`.provenance.json` manifest are all committed to this repo, not merely
build output. `rm -rf dist` deletes tracked content that `build.py` does not
regenerate (only `extract/make_provenance.py` writes the provenance manifest,
and it is not part of a normal `build.py` run) -- so the "clean, then rebuild"
step the integrator checklist and `docs/WORKFLOW.md`/`docs/CODE_STANDARDS.md`
document as standing practice quietly breaks the working tree every time it is
followed literally, leaving a committed file gone until someone notices and
restores it. `git clean -fdx dist` removes only what git does NOT track --
exactly the stale artifacts and stray sidecars this file's Q1 section and
`dist_integrity_failures()` exist to refuse -- and leaves the release
artifacts alone. Use `git clean -fdx dist && python3 build.py` everywhere the
old `rm -rf dist && python3 build.py` recipe is written down.

---

## The table

| Gate | Proves | Negative control | Residual |
|---|---|---|---|
| **Q1** | Build integrity: DOCTYPE/`<html>`/`<head>`/`<body>` present, exactly two `<script>` elements (one JSON island, one inline app script), the island parses, the version string matches in five places, the build date matches, the `.sha256` sidecar matches the artifact, no raw `<` or `>` survives into the data island, **and (CR-T-28) the embedded `CONTENT_FINGERPRINT` constant equals a fresh sha256 of the shipped island**. The fingerprint is defined as the sha256 of exactly the bytes inside `<script id="mcr-data">...</script>` -- computed by `build.py` before that payload is substituted into the template (never a hash of a string containing itself) and embedded as a plain constant, never inside the island. **Preflight, before any of the above runs:** `find_artifact()` no longer globs `dist/` and takes whatever sorts last -- it derives the ONE filename `build.py`'s own `APP_VERSION` names and gates exactly that file, nothing else. `dist_integrity_failures()` then refuses to proceed at all (hard `FAIL`, non-zero exit, before Q1's own checks run) if `dist/` holds any other `md-code-red_*.html`/`.sha256`/`.provenance.json`, naming every offender, or if the correctly-named artifact is older than `build.py`, `template.html`, or anything in `content/` -- a stale file cannot pass by having the right name and an unchecked clock. | **Partial**, now **Yes** for artifact selection. `tests/test_island_escaping.py` (7) as before for the escaping half. **New:** `tests/test_dist_integrity.py` (5) closes AL-GATE3-001's post-release finding (DECISION_LOG 2026-09-17, three dist/ incidents) -- a stale sidecar named to sort after the real artifact and carrying the CURRENT version string (the `*.main.html` shape of the actual incident) is proven NOT selected; a stray `.html`/`.sha256` in `dist/` is proven refused, named; a correctly-named artifact predating a `content/` edit is proven refused by mtime. The DOCTYPE / script-count / five-way version match / sha256-sidecar / fingerprint checks still have **no fixture** -- nothing has ever broken the script count, corrupted a version string, or planted a stale fingerprint and asserted Q1 catches it. | The island-escaping half and the artifact-selection half are the only halves that have been watched fail. Selection is now name-derived rather than defensive pattern-matching: it cannot be fooled by sort order, but a `dist/` holding a file with the exact expected name that was hand-edited in place (never rebuilt, `touch`ed to a fresh mtime) is a residual this gate does not close -- CONTENT_FINGERPRINT and the sha256 sidecar (both above) are what catch that instead. |
| **Q2** | Air-gap law: no external script, stylesheet, link, image or media element; no `@import`/`@font-face`; no non-`data:` `url()`; no `http(s)` `src`/`href`; no network-capable API reached from the app script by any of four routes (written out, bracketed, fused from string literals, or aliased without being called); no CDN literal, written out or assembled. | **Yes**, `tests/test_airgap_and_markers.py` (19): nine routes to a network API, ten "stays clean" controls covering every computed-member shape `template.html` writes, and an end-to-end planted `window["fe"+"tch"]` through `gate_q2` on the real artifact. | A name produced at **run time** from something that is not a string literal — a code-point array, a value out of the content island — is invisible to any scan of the source. Same residual Q17 states; same reason. |
| **Q3** | Provenance law: every command entry, tool, flag dictionary, rules dataset, the CCI map and the destructive-pattern table carry all five `source` fields, with a `license_class` from the allowed set. The field list and the class list are **read out of `extract/schema.py`'s text**, never restated here. | **Yes**, `tests/test_provenance_fields.py` (8): one field dropped at a time, the superset assertion against `schema.PROVENANCE_FIELDS`, an assertion that `qa.py` reads the tuple rather than restating something that happens to match, and unreadable/empty schema tuples. Empty-set case in `tests/test_empty_set_gates.py`. | The **check** is deliberately independent of `extract/schema.py` (that is the point of Q3) — only the constant is shared. So the two can still disagree about what "missing" means, just not about which fields are required. |
| **Q4** | Every command entry carries `verify`, `undo`, and a `blast` of `green`/`yellow`/`red`. | **Yes**, `tests/test_empty_set_gates.py` (6) for the empty case. The per-field checks have no fixture. | Proves the fields are **present and well-typed**, never that a `verify` command verifies anything or that an `undo` undoes it. Content validation is CR-T-34. |
| **Q5** | Every feature marker is present, in the place its kind requires: `code` markers (`function …(`, `var …=`, `document.…`) in live app-script code, `html` markers (`id="…"`) in the static markup outside every `<script>` and HTML comment, `text` markers (user-visible copy, a CSS at-rule, the assembler's comment marker) anywhere in the file. A marker for a module this build does not have yet reports PENDING, never PASS. | **Yes**, `tests/test_airgap_and_markers.py`: a code marker planted in a block comment, in a line comment and in a string literal; a region id planted in a JS string and in an HTML comment; the copy marker that must stay legal inside a string; and an end-to-end demotion of `function renderRail(` to an HTML comment through `gate_q5`. | A marker is a **name**, not behaviour. `function renderRail(` existing in live code says the rail renderer exists; it says nothing about what it renders. The `yamlQuote(` marker was PENDING for exactly that reason -- a name with no sink behind it -- and is live only now that Q18 checks the sink and the oracle beside it. |
| **Q6** | No `TODO`/`FIXME`/`XXX`/`lorem ipsum`/`example.com`/`CHANGEME` in the shell. | **None.** | A plain text scan, by design. Low stakes by design too: the blast radius of a miss is cosmetic. Unlike Q5, it is not standing in for a structural claim. |
| **Q7** | Every `localStorage`/`sessionStorage` identifier in the app script sits inside a `try{…}catch` block, and storage records are schema-versioned. Braces are counted over a **lexically masked** copy. | **Yes**, `tests/test_storage_guard.py` (10): the AL-GATE3-003 desync driven five ways (a brace in a string, a template literal, a regex literal, a `//` comment and a `/* */` comment), the closing-brace half that would shorten a span and produce a false FAIL, guarded/unguarded controls, and masking-is-lossless assertions. | Proves the access is **wrapped**, not that the `catch` does anything sensible with the exception. |
| **Q8** | Embedded record counts reconcile with `_meta` for all four RULES datasets, the command entries and the CCI map; no dataset declares `partial`; every dataset names a generator Q15 re-runs. | **Yes**, `tests/test_empty_set_gates.py` for the empty case. The count-mismatch path has no fixture. | Reconciles counts. Q10 reconciles content. |
| **Q9** | Every embedded rule has a STIG ID and a CAT of I/II/III; every CAT I rule carries both check and fix text; CCI present wherever the source has one; NIST present wherever the CCI maps; **and at least one CAT I rule exists per release**. | Indirect. The zero-CAT-I guard is pinned by `tests/test_empty_set_gates.py`. | — |
| **Q10** | Every embedded STIG ID is present in the pinned XCCDF and vice versa (full ID-set parity), and a deterministic stride sample is re-parsed and compared on title, rule id, CCI, CAT, and full check and fix text. | **Yes**, and it is the best-covered gate after Q17: `tests/test_accuracy_gate.py` (9) — control, mutated text, dropped rule, renamed rule, duplicate ID, determinism. | The sample layer alone **would** be fail-open on zero embedded rules; the ID-set **parity** layer closes it, and that layer was added for a different stated reason (drift outside the stride). It is not redundant. Do not remove it. |
| **Q11** | A stride sample of CCI→800-53 mappings matches a fresh parse of the DISA CCI list; every CCI referenced by an embedded rule resolves; the map carries nothing no rule cites; an empty map is refused. | **Yes** for the empty-map guard (`tests/test_empty_set_gates.py`). No dedicated fixture file the way Q10 has one. | Sampled, not exhaustive, on the value comparison. |
| **Q12** | Every entry carries all four RHEL keys with an explicit value in each (a command, an `unavailable` with a reason, or a resolved `same_as`), and every tool declares availability for all four. | **Yes**, `tests/test_empty_set_gates.py` for the empty case. | — |
| **Q13** | Every entry's tool and category resolve; every `stig_id`/`rule_id` pair resolves in the right RULES dataset and carries its reverse link; every `source_ref` resolves. | **Yes**, `tests/test_empty_set_gates.py` for the empty case, including empty tool-id and category **target** sets. | — |
| **Q14** | No curated string on a `paraphrase-only` FIELD shares an 8-gram with any staged raw source, checked per field — `intent`, `verify`, `undo`, `rhel_versions[].notes`, `.changed_in_note.what`, `flags[].explain`, a generator's `fields[].label`/`.help`, and `stig[].notes` — with a `flags[]` item's own `license_class` overriding its entry's when present; every release whose flag dictionary ships populated has its raw man/`--help` text staged under `content-src/raw/rhel<N>/`; **and** a paraphrase-only entry whose source is not a staged man page or `content-src/raw/` path (i.e. cites a Red Hat guide, which this repo does not stage) carries a `source.paraphrase_attested_by {by, on}` receipt naming a QA-role reviewer from `content-src/roster.json`. | **Yes**, `tests/test_paraphrase.py` (33) — the file ADR-001 §7.3 promised and Al's review found missing, widened this tranche (Milo Vance, self-flagged H1 gap: the gate scanned `notes`/`changed_in_note`/`flags[].explain` and nothing else, and filtered by license_class once per entry, so a flag with its own `license_class: paraphrase-only` under a verbatim-ok entry — firewalld-service-active's `status`/`is-active` — was never checked). Coverage: a sentence lifted at run time out of a real staged source, in every one of the newly-covered fields (`TheWidenedFieldsAreCaught`) and in `notes`/a flag explanation (`ThePlantedSentenceIsCaught`); the flag-level license_class override in both directions (`TheFlagLicenseClassOverride`); the H1 incident re-created deterministically from `content-src/raw/rhel8/chronyd.man.txt`, plus a check that the real `gen-chronyd-one-shot-check` entry is clean (`TheChronydNearMiss`); the guide-citation attestation receipt — missing, valid, off-roster, wrong-role, not-required-for-a-man-page, and the real 27 entries needing none (`TheGuideAttestationReceipt`); honest paraphrase passing in every field; the same sentence on a `verbatim-ok` field passing; the 7-vs-8 word boundary in both directions; corpus-coverage refusals including an empty directory. All 27 shipped entries audited under the widened gate: **0 collisions, 0 entries require a paraphrase_attested_by receipt.** | 8-gram shingles catch **lifting**, not close paraphrase, and not a lifted run of seven words or fewer. That is the documented rule, not a defect — but it is a floor, not a guarantee of licence compliance. The guide-attestation receipt is a **human** control, not a re-derivation of Q14's own offline check — Q14 cannot verify a paraphrase against text it does not have, on principle (see `qa.source_is_offline_checkable`'s docstring for why this repo does not stage guide prose to close that gap instead). |
| **Q15** | Re-running each extractor with `--check` reproduces the committed content byte for byte, and every generated dataset names a generator this gate actually re-ran. | **None** directly. `tests/test_build_fails_on_broken.py` (2) exercises the adjacent build-time schema path. | Trusts each extractor's own `--check` mode to be honest. A bug in a `--check` path is inherited whole. |
| **Q16** | Capture backing (Marcus Reed's Verified-per-version review, VER-001/002/003, conditions J1/J2/J3). Every `expected_output` block has a capture record carrying all nine required fields. Every per-version `verified` receipt is backed by its own capture file for that exact (entry, RHEL version) pair, `command_hash_at_capture` matches `sha256(command_as_run)`, and `command_as_run` still matches what this build emits TODAY — a fixed `rhel_versions` command diffs against the shipped, `same_as`-resolved artifact; a **generator** (`template` present, MCR-SEC-006 — no single "current" command exists to diff without one) diffs against the hand-authored validity oracle in `tests/fixtures/golden-commands.json` (**J1**). The two-person rule: `by` and `captured_by` are normalised (casefold, collapsed whitespace incl. NBSP, one stripped trailing parenthetical — `normalize_person_name()`) and BOTH must resolve against the closed roster in `content-src/roster.json`, `by` holding the QA role and `captured_by` holding the SME role (**J2**). Closed grammars on `host` (`RECEIPT_HOST_RE`, cross-checked against the capture's own `host`) and `capture` (`RECEIPT_CAPTURE_PATH_RE` — no traversal, no other shape); `by`'s grammar is the roster itself (**J3**). | **Yes**, `tests/test_empty_set_gates.py` for the empty case, and — new in this tranche — `tests/test_q16_receipts.py` (21 cases) exercising `gate_q16()` directly: J1's golden-table bind shown failing on a missing table, a missing row, and Marcus's own repro (a generator's template changing what it emits while the golden row and receipt still describe the old command); J2's nine variants (eight accidental — case, padding, doubled/NBSP whitespace, a `(SME)` suffix — plus the deliberate alias `"C. Stone"`, which fails for roster non-membership, not equality), an off-roster name on either side, a roster member in the wrong role, and a missing roster file; J3's `<img onerror=>`-shaped `host` and `capture`, a `../` traversal in `capture`, and a `host` that disagrees with its own capture's `host`. | Proves a receipt **exists, is shaped right, and is bound to what the product emits today** — for both the fixed-command and the generator half. The deliberate-alias residual is explicit and stated in the gate's own PASS diagnostics, not implied: normalisation closes only the accidental bypass; a person who deliberately writes a different name is refused because that name is not on the closed roster, never because it is detected as an alias. Whether a capture was really taken on the host it claims remains a process control, not a gate. |
| **Q17** | Render safety: zero inline `on*=` handlers, no `eval`/`new Function`, `esc()`/`escapeAttr()` defined, no trojan-source characters in the shell **or the data island**, no forbidden sink (`insertAdjacentHTML`, `outerHTML`, `document.write`, `createContextualFragment`, `srcdoc`), `.innerHTML` only ever an assignment target, `setAttribute` only with a readable and non-dangerous literal name, every segment reaching a sink or a derived accumulator is a literal or an escaper call, and no computed member assignment reaches a sink by a bracketed or fused name. | **Yes**, the best-covered gate in the file: `tests/test_render_audit.py` (10) drives 15 committed bypass fixtures plus safe/unsafe controls and the shipped shell. | **Q17 proves the escapers are CALLED. It cannot prove they escape** — that is Q19's job, and the two are only meaningful together. A property name produced at run time from data is invisible to it (MCR-SEC-014, condition D2, recorded in `docs/CODE_STANDARDS.md` §1). |
| **Q18** | Command-assembly safety. **Two quoting domains** -- `shQuote()` for a POSIX shell word, `yamlQuote()` for a YAML single-quoted scalar -- plus the DOM escapers, never nested in any direction and never substituted for one another; the YAML **sink** (`composeDoc()`), its quoter and its **parsing oracles** must all three be present, and the report's `yaml_oracle_checks`/`ini_oracle_checks` must both be non-zero; the assembler lifted out of the **shipped artifact** rejects or provably single-quotes every hostile vector across every field type, release and argument shape; every generated playbook, inventory and `ansible.cfg` is PARSED and compared line for line against the operator's intent; positive controls prove it is not passing by rejecting everything; and the harness's JSON report is checked for shape before it is believed. | **Yes**, three ways: `tests/test_hostile_inputs.py` (10) drives the harness against `template.html`; the harness carries its own positive and negative controls, including the **domain-swap control** (a shell-quoted value must NOT parse as a YAML scalar) and an injected-line control; and `tests/test_q18_report.py` (16) drives the report consumer with an empty body, a truncated body, a renamed field, wrong types, a non-object body, zero checks, zero file-oracle checks and a non-zero exit. | Proves **shell-token** containment, a firewalld rich-rule oracle, and **file** containment by parsing. It does not prove the generated playbook does what the operator meant -- that is the golden table's job for the command and a human's for the file. |
| **Q19** | Escaper behaviour: `esc()`, `escapeAttr()` and `escapeRegex()` are lifted verbatim out of the **shipped artifact** and RUN under node against 92 declared and 3 generated hostile vectors. `esc()` leaves no raw `< > " '` and no bare `&`, and round-trips exactly through a strict entity decoder. `escapeAttr()` adds `` ` `` and `=`. `escapeRegex()` escapes every metacharacter present, leaves none bare, compiles, matches its own input, and does not match what only the unescaped pattern would. | **Yes**, three ways: `tests/test_escaper_behaviour.py` (11) mutates the shipped escapers four ways (identity, drop-the-character, half-escaped, `escapeRegex` alone) and asserts each fails; the probe runs its own battery against three known-broken escapers **before reporting anything** and refuses to report a PASS unless it just failed all of them; and `TheRenderAuditCannotSeeThis` keeps Al's original transcript executable. | Proves what the functions do **to strings**, not that every render path calls the right one for its context — that is Q17. Neither gate is sufficient alone. |
| **Q20** | Flag-dictionary coverage and citation honesty (MCR-SEC-020 / MCR-SEC-019). Distinct long options in every committed raw capture are compared with dictionary names for all 70 captured tool/release pairs; a shortfall that grows fails and one that shrinks demands a tighter baseline. A generator citation must also show the option it emits. | **Yes.** Growth and bad-citation controls remain, and `tests/test_coverage_baseline_expiry.py` now exercises both retirement paths: a fully evidenced retirement remains valid after the former deadline, while a retired record with missing authority/evidence fails. | The named wrapped-term defect is retired: `--add-rich-rule` resolves on RHEL 8, 9 and 10. Raw counts remain an upper bound because they include prose and per-subcommand mentions, so the retained baseline is a regression ratchet rather than a fabricated coverage percentage. Retirement ended the dated waiver; it did not disable Q20. |
| **Q21** | No raw control, bidi or zero-width character in any tracked source file. Walks `git ls-files` — **all tracked files, nothing excluded (280 at v1.0.0-alpha.1)** — with one allowance, a U+FEFF byte-order mark at offset 0 (only `stig-src/U_CCI_List.xml` uses it). Applies the same `TROJAN_RANGES` table Q17 applies to the artifact — not a second copy. | **Yes**: `tests/test_no_raw_trojan_chars.py` (9) plants a U+202E and asserts it is caught by codepoint and byte offset, plants all 14 character classes one file each, and asserts the six-ASCII-character escape spelling, ordinary prose and a binary file are NOT caught. The planted files live in a temp directory, never the repo — a committed fixture holding a raw U+202E would be the thing this gate forbids — and the BOM allowance is pinned at offset 0 from both sides: allowed at 0, caught one byte later. | Proves the REPOSITORY is clean; **Q17 proves the shipped artifact is**. Deliberately not folded into Q17: different corpus, and a merged gate's failure would be ambiguous between "the artifact is poisoned" and "an editor rewrote a fixture". It reads bytes only — it cannot tell a deliberate vector from an accident, which is why the allowance is a single byte offset and is itself a test. |
| **Q22** | Declared tool is the invoked binary, and every flag resolves, is curated, or is honestly marked (Marcus Reed's Panels review, PANEL-001 / condition G1). Two checks: (a) **binary agreement** — the first word of every `rhel_versions[version].command` (after stripping one leading `sudo`) must equal the binary `tools.json` records for the entry's `explain_tool` (falling back to `tool`); `firewalld-service-active` declaring tool `firewall-cmd` while every version's command is a `systemctl` invocation is exactly the mis-filing this catches, because the inspector's flag panel would look the binary up in the wrong dictionary. (b) **flag explainability** — every `flags[].flag` either resolves as a name in a POPULATED `flags_rhel<v>.json` (RHEL 7/9 ship empty dictionaries and do not count), carries a curated `explain`, or is honestly marked non-option (not `-`-prefixed, with a `license_class` on record) — a flag that is option-shaped, unresolved, and has neither is the one shape this gate refuses outright. | **No dedicated test file exercises `gate_q22` directly.** The gate's own PASS/FAIL text was watched fail during its authoring (committed failing on `firewalld-service-active` / `journald-service-active`, fixed in `content/commands.json` and `template.html`, per the code comment above `gate_q22`), but that transcript is not pinned by any committed fixture the way Q19's or Q21's negative controls are. | Already applies AL-GATE3-004's rule to itself: zero entries with a `rhel_versions` block, or no populated `flags_rhel*.json` at all, is an explicit failure (`empty_set_failure`), not a vacuous PASS — unlike Q3/Q4/Q8/Q12/Q13/Q16 before that review. It only checks entries carrying a `rhel_versions` block, so a generator spec (`"template" in e`) is silently out of scope, by design — generators compose per release and have no fixed binary to agree with. |
| **JS** | `node --check` parses the extracted app script. | None; informational by design. Node absent correctly downgrades to PENDING. | Syntax only. |

Node is **required** by Q18 and Q19 and optional for the `JS` gate (Q20 needs neither: it reads files). The asymmetry
is deliberate and stated in both gate docstrings: a missing syntax check is an
inconvenience, and a missing injection or escaping check is a fail-open wearing a
politer word.

---

## The pipeline composer (CR-T-31): what proves it, and what a PASS does not mean

`assemblePipeline()` composes several commands into one shell line. That is the
feature most able to undo everything Q18 proves, because the thing being added
between stages -- `|`, `&&`, `>` -- is precisely the metacharacter the hostile
harness rejects tens of thousands of times over. The design answer is one
sentence, and every gate below exists to keep it true:

> **A pipeline is structure the tool owns, never a value the user supplies.**

The user picks a KEY; the key is resolved by `hasOwnProperty` against
`PIPE_OPERATORS`; that table's own string literal is what is emitted. No code
path copies operator text out of a stage. `|` never enters a form field.

### The gates, and what each one holds

| What proves it | Proves | Negative control | Residual |
|---|---|---|---|
| **Q18 (extended)** -- `node tests/hostile_harness.js`, driven through `gate_q18` | Every hostile vector into every field of **every stage** of multi-stage pipelines and into every redirect target (17,092 checks); the operator seam (332 checks driving every vector, every prototype-chain key and the operator TEXT itself into `op`, all refused, with 40 controls proving the ten real keys compose); the interpreter class (100); stage naming (36); one-stage invariants (108); redirect-target ratings (44). The report is shape-checked before it is believed, and Q18 fails closed on a zero in any of those counts. | **Yes.** 11 pipeline-oracle negative controls (an injected bare `\|` in a value, a quote-broken one, an extra / missing / swapped / misplaced operator, a QUOTED operator, a smuggled `$(id)`, an uncomposed redirect, unbalanced quoting) each FAIL the harness if the oracle reports agreement, plus a positive control that fails if it rejects the honest line. `tests/test_q18_report.py` (16) drives the consumer with a missing field, wrong types, a zero count and a non-zero exit. | It proves the emitted line's **structure is the operator's own** and that no value escaped its quoting. It does **not** prove the pipeline is a sensible thing to run, and the blast COMPOSITION rules are policy over a target path and a child binary. |
| **The pipeline oracle** (inside the harness) | Builds the expected word layout from the USER'S composition -- operator keys through the closed table, each stage's word count from `assembleCommand()` -- then tokenises the emitted line under POSIX single-quote rules and asserts every expected operator sits at exactly its expected word INDEX, fully unquoted, with no other word an operator and no word leaving a metacharacter outside its quotes. 589 comparisons. | **Yes**, the 11 above. This is the check that would catch an operator arriving from data, so it is the one that must be shown able to fail. | It compares STRUCTURE. A pipeline whose every operator is exactly where the operator put it can still be a bad idea. |
| **`tests/test_pipeline_ui_wiring.py`** (15 tests, 9 audits) | The PANEL, which the harness cannot see: operator `emit` text is `esc()`d into element TEXT and reaches no `value=` attribute; the `<option>` values are closed-table KEYS through `escapeAttr()`; no rendered control is dead and no routed verb is unreachable (both directions, for actions and fields); the picker, the table and the emission allow-list are the same set of ten; `#pipeline-panel` has exactly one writer and `renderAll()` calls it; the only free-text inputs are a `path` and an `integer`, both validated; every rating the assembler can produce has a badge rule behind it; neither header site heads a pipeline with one stage's tool name. | **Yes**, 14 controls, each mutating the real `template.html` in the way its audit exists to catch, each asserting it actually patched something first so a control cannot rot into a no-op. | It is a STRUCTURAL read of the source, not a DOM test. It proves no control is unwired and no operator text reaches a value; it does not prove the panel is usable, which is what the browser check in the commit record is for. |
| **`tests/test_pipeline_stig_shapes.py`** (ADR-002) | The closed operator set can express the pipelines DISA's own check text uses, re-derived from `content/rules_rhel*.json` so the claim cannot go stale: 462 of 3,086 command lines carry a top-level operator and 457 (98.9%) are fully expressible. Operators are counted at TOP LEVEL only -- `awk`'s `($3>=1000)&&(...)` and `find`'s `-exec ... \;` are not shell operators. | Structural: the fixture's `out_of_scope` list must be non-empty and every entry must carry a reason, so assertion 1 cannot pass by declaring everything out of scope. | A shape the set cannot express is reported as a **finding**, never a reason to widen the set quietly. PIPE-F1 (`/dev/null` is 26 of the 31 absolute redirect targets in the corpus and the rule rates `/dev/**` RED) is recorded, not carved out. |

### The composition rules, and the check that proves each one fires

Blast is **not** the max of the stages. Each rule below is asserted to FIRE --
to produce a rating ABOVE the max of its stages -- because a rule nobody has
watched fire does not exist (the discipline that caught MCR-SEC-008):

| Rule | Proved by |
|---|---|
| A `>`/`>>` to a target outside a scratch path is a WRITE: at least yellow | blast-composition checks; a green command + an unclassified target must not rate green |
| A target under `/etc`, `/boot`, `/dev`, `/usr`, `/var/lib`, `/sys`, `/proc` is RED | the same block, per release |
| A target outside the protected list renders `unrated`, **never green** (PL4) | 44 redirect-target rating checks, including a control that an unclassified and a scratch target do not rate the same |
| An interpreter as final consumer is **REFUSED**, not rated (PL2) | 100 interpreter-class checks: a pipe into one, an `xargs` CHILD that is one (with and without `-0`/`-I`), and an execution sink reached by REDIRECT -- each with a legal neighbour as a control |
| `\| xargs` feeding a destructive tool, or feeding anything that assembles red, is RED | blast-composition checks on the real `XARGS_RED_TOOLS` list |
| `;`, `&&`, `\|\|` carry the max of their stages | blast-composition checks |
| `dangerous.json` fires on the de-quoted projection of the WHOLE pipeline | a pattern (`rm -rf /`) whose text exists ONLY across the operator, matching no stage alone |

### TM2-F8, and why `su -c` is refused rather than escaped

`su -c`, `sh -c`, `find -exec` and every wrapper that takes another command as
its argument RE-PARSE that argument. A value correctly single-quoted for the
outer shell is then re-interpreted by an inner one, so `shQuote()` -- a POSIX
shell quoter and nothing else -- is the wrong escaper for that second domain.
That is exactly the shape the dead YAML quoter was deleted to stop pretending
about (MCR-SEC-010): **a second escaping domain gets its own quoter AND its own
parsing oracle in the same commit, or it does not exist.**

It does not exist here. Every wrapper is REFUSED as a stage binary and `find`'s
`-exec` family is refused as a bare token, so this composer cannot emit a stage
whose argument a child re-parses. `xargs` is the one re-parser present on
purpose: it re-parses its INPUT STREAM, not its argv, and that stream is the
producing stage's output -- filenames on a disk -- never a value from a form.

---

## Gates with no negative control

Named here rather than left to be discovered by the next reviewer:

1. **Q1**, except its island-escaping half and its artifact-selection preflight
   (`tests/test_dist_integrity.py`). Nothing has ever broken the script count,
   corrupted one of the five version strings, mismatched the sha256 sidecar,
   or planted a stale `CONTENT_FINGERPRINT` and asserted Q1 catches it.
2. **Q6.** A text scan doing what it says, with a cosmetic blast radius.
3. **Q15.** The `--check` re-run is exercised end to end on every build and by
   nothing in `tests/`.
4. The **per-item** halves of Q4, Q8, Q12, Q13 and Q16 — their empty-set halves
   are covered, their "this field is wrong" halves are not.

None of these is an accusation. They are the rows where "this gate has been
watched failing" cannot currently be said.

---

## Residuals, collected

* **Run-time name construction defeats Q2 and Q17 alike.** Both read names built
  from *string literals*. A property or API name assembled at run time from a
  code-point array or from island data is invisible to any scan of the source.
  Both gates are accident-prevention over hand-written code `CODEOWNERS` reviews,
  not sandboxes; a determined author with commit rights was never in the threat
  model (MCR-SEC-014, D2).
* **`extract/schema.py`'s `content_errors()` still passes an empty bundle.** The
  AL-GATE3-004 shape one layer down: a fully empty `commands.json` clears
  build-time schema validation. Every one of Q3/Q4/Q8/Q12/Q13/Q16 now catches it
  at the merge gate, which is where the build would be stopped anyway. Not fixed
  here because `extract/schema.py` is being edited on a sibling branch this
  tranche stayed clear of. **Open, and deliberately not silent.**
* **Q10 is sampled on content and exhaustive on IDs.** A text drift outside the
  stride and inside the ID set is the one thing that gets past it.
* **Q14's floor is eight words.** Seven lifted words pass, by the documented rule.
* **Q16 proves receipts exist**, not that the capture happened as described.

---

## Closed, and where the evidence is

| ID | Finding | Closed by |
|---|---|---|
| MCR-SEC-004 | Five mechanical bypasses of the innerHTML audit | `render_sink_failures()` + 15 bypass fixtures |
| MCR-SEC-007 | Data island could break out of its `<script>` | `island_escape_failures()` + `tests/test_island_escaping.py` |
| MCR-SEC-009 | U+2028/2029/2065 missing from the invisible-character set | `TROJAN_RANGES`, fixture vectors |
| MCR-SEC-010 | Dead YAML quoter made Q18 pass on a domain that did not exist | **Closed (CR-T-25).** The quoter was removed and Q18 narrowed to shell-only, under Marcus Reed's standing condition D3: the sink, the quoter and a YAML-parsing oracle ship in ONE commit. They did. `composeDoc()` is the sink (playbook, inventory, `ansible.cfg`), `yamlQuote()` the quoter, `parseYamlSubset()`/`parseIniSubset()` the oracles. Q18 now checks all three are present AND that the oracles ran (a zero count is a FAIL), and `tests/test_doc_spec_schema.py` (20) holds the build-time copy of the rules to the runtime's. |
| MCR-SEC-013 (D1) | Conditional positional literal shifted arguments | `isPositionalToken()` / `spec_template_errors()`, merged at `9cf092d` |
| MCR-SEC-014 (D2) | Computed member access reached a render sink | `computed_sink_failures()`; residual note in `docs/CODE_STANDARDS.md` §1 |
| AL-GATE3-001 | Q17 proves the escapers are called, never that they escape | **Q19** + `tests/escaper_probe.js` + `tests/test_escaper_behaviour.py` |
| AL-GATE3-002 | D2's `CODE_STANDARDS.md` note was missing | Present at `9cf092d`; verified, no action needed |
| AL-GATE3-003 | Q7's brace counter desynced on a literal | `mask_js_literals()` + `tests/test_storage_guard.py` |
| AL-GATE3-004 | Six gates passed on an empty bundle | `empty_set_failure()` + `tests/test_empty_set_gates.py` |
| AL-GATE3-005 | Q3's provenance list had drifted weaker than `schema.py`'s | `parse_schema_tuple()` + `tests/test_provenance_fields.py` |
| AL-GATE3-006 | Malformed harness report crashed Q18 with a `KeyError` | `harness_report_failures()` + `tests/test_q18_report.py` |
| AL-GATE3-008 | MCR-SEC-013's fix appeared absent | Present at `9cf092d`; verified, no action needed |
| (self-inflicted, `dd01ad7`) | A `json.dump(..., ensure_ascii=False)` round-trip turned 8 invisible-character vectors in `tests/fixtures/hostile-inputs.json` into the raw characters they name; no gate could see it | **Q21** + `tests/test_no_raw_trojan_chars.py`; the fixture is now byte-identical to `origin/main` apart from two added field types |
| MCR-SEC-025 (F2) | `chronyd -Q` modelled the chrony directive as the option's value | Pinned capture settles it — directives are OPERANDS (`chronyd [OPTION]... [DIRECTIVE]...`, #L7) and `-Q` takes no argument (#L68); command unchanged, citation repointed, grammar recorded in the entry's notes |
| MCR-SEC-015 (E1) | 20 short-option tokens joined with `=`, which getopt does not accept | `flagJoin()` derives the join from the flag's shape; `flag_join_errors()` at build time; the golden-command table and the getopt syntax oracle in the harness |
| MCR-SEC-016 (E4) | Four fields with closed grammars typed as free text | `lvm_size` / `group_list` field types; 31 closed-grammar harness checks |
| MCR-SEC-018 (E3) | The D1 rule over-refused option-shaped conditional literals | The derived discriminator + `tests/test_positional_crosscheck.py` (3,258 shapes / 104,256 runs / 0 violations) |
| MCR-SEC-019 (E5) | A generator cited a man-page line for an option it does not emit | Citation repointed; **Q20** half two |
| MCR-SEC-020 (E5) | Q15 cannot see a systematically incomplete flag dictionary | **Q20** half one + `content-src/flag_coverage_baseline.json`; shortfall accepted with a date |
| MCR-SEC-021 (E6) | The harness was a containment oracle with no validity oracle | `tests/fixtures/golden-commands.json`, `optionSyntaxErrors()`, the enum-branch sweep, `benignFor(field, rot)` |
| MCR-SEC-022 (E7) | `flag` beside `lit` was an unchecked off-switch for the D1 rule | Dual-key token refused in both halves; the discriminator is derived from the literal |
| MCR-SEC-023 | An option emitted as a `lit` was never explained in the inspector | Option-shaped lits pushed into `flags[]`; 248 inspector flag-list checks |
| VER-001 (J1) | 12 of 18 verified receipts sat on generator entries, exempt from Q16's command-drift check (`if "template" not in e:`) — a template edit could not invalidate the receipts describing its old behaviour | `load_golden_commands()`; generator half of `gate_q16()`'s drift check bound to `tests/fixtures/golden-commands.json`; `tests/test_q16_receipts.py::Q16GoldenTableBinding` |
| VER-002 (J2) | The two-person rule was byte-for-byte string equality; 8 of 9 variants (case, padding, doubled/NBSP whitespace, a `(SME)` suffix) bypassed it, and a deliberate alias cannot be closed by any string comparison at all | `normalize_person_name()` + `load_roster()` + `content-src/roster.json`; `by` must hold the QA role and `captured_by` the SME role; the deliberate-alias residual is stated in the gate's own PASS diagnostics; `tests/test_q16_receipts.py::Q16TwoPersonRoster` |
| VER-003 (J3) | Receipt `by`/`host` had no closed grammar — hostile markup or a path traversal in `host`/`capture` passed the whole gate | `RECEIPT_HOST_RE`, `RECEIPT_CAPTURE_PATH_RE`, receipt-vs-capture `host` cross-check (`by`'s grammar is J2's roster); `tests/test_q16_receipts.py::Q16ClosedGrammars` |

---

## Stale items in ADR-001 §7 — for Al, not edited here

`ADR-001-engine-and-content.md` is Al Kowalski's document and this tranche does
not touch it. These are the places its §7 no longer describes what `qa.py` does,
collected so the next revision has a list rather than a search:

1. **The 8 MB ceiling (AL-GATE3-007, still open).** §7.2, §7.4 item #10, §10's
   CI table, §12 risk R5 and §13 open question Q1 all describe an 8 MB hard
   ceiling as current binding policy. The Founder ruled the ceiling **unlimited
   on 2026-09-17**; `qa.py`'s module docstring, `size_report()` and
   `.forgejo/workflows/ci.yml` all already say so, and the size line cannot fail
   a build. Only the ADR still carries the old figure.
2. **§7.3 numbers the gates Q1–Q17.** The file now runs **Q1–Q21 plus `JS`**.
   Q18 correctly sits outside the BQP Gate 2 ten-check mapping (it is Marcus's CI
   merge-gate #4/#9, as `qa.py`'s docstring says). **Q19 is new in this tranche**
   and sits outside that mapping for the same reason: it answers AL-GATE3-001,
   not an ADR §7 item. If §7.3 is meant to be the complete gate list rather than
   the Gate 2 mapping, both need a row.
3. **§7.3 Q14 promised `tests/test_paraphrase.py`.** It now exists. §7.3 should
   also record the second half Q14 grew here: a populated flag dictionary whose
   raw sources are not staged is a FAIL, because the corpus the gate compares
   against is then not the corpus the content came from.
4. **§7.3 Q10 describes sampling.** Al's experiment 4 established that the
   **ID-set parity** layer — added for a different stated reason — is what closes
   the zero-embedded-rules case the sample alone would miss. Worth stating in the
   ADR so a future cleanup does not remove it as redundant. It is stated in this
   file's Q10 row and in `accuracy_failures()`'s docstring for the same reason.
5. **§7.3 Q3 should say the field list comes from `extract/schema.py`**, not
   from a list in `qa.py` — the drift AL-GATE3-005 found is only mechanically
   prevented as long as that stays true.

---

*Maintained alongside `qa.py`. A new gate lands with its row and its negative
control, or it does not land.*
