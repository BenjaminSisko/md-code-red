# QA Gates — what each one proves, how it was watched failing, and what it does not cover

`python3 qa.py` runs **Q1–Q20 plus one unnumbered `JS` gate**: 21 rows in `GATES`,
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

---

## The table

| Gate | Proves | Negative control | Residual |
|---|---|---|---|
| **Q1** | Build integrity: DOCTYPE/`<html>`/`<head>`/`<body>` present, exactly two `<script>` elements (one JSON island, one inline app script), the island parses, the version string matches in five places, the build date matches, the `.sha256` sidecar matches the artifact, and no raw `<` or `>` survives into the data island. | **Partial.** `tests/test_island_escaping.py` (7) drives `island_escape_failures()` with `<!--<script`, with the pre-MCR-SEC-007 `</`-only escaping, and end to end through a real build with the hostile sequence planted in a rule title. The DOCTYPE / script-count / five-way version match / sha256-sidecar checks have **no fixture** — nothing has ever broken the script count or corrupted a version string and asserted Q1 catches it. | The island-escaping half is the only half that has been watched fail. |
| **Q2** | Air-gap law: no external script, stylesheet, link, image or media element; no `@import`/`@font-face`; no non-`data:` `url()`; no `http(s)` `src`/`href`; no network-capable API reached from the app script by any of four routes (written out, bracketed, fused from string literals, or aliased without being called); no CDN literal, written out or assembled. | **Yes**, `tests/test_airgap_and_markers.py` (19): nine routes to a network API, ten "stays clean" controls covering every computed-member shape `template.html` writes, and an end-to-end planted `window["fe"+"tch"]` through `gate_q2` on the real artifact. | A name produced at **run time** from something that is not a string literal — a code-point array, a value out of the content island — is invisible to any scan of the source. Same residual Q17 states; same reason. |
| **Q3** | Provenance law: every command entry, tool, flag dictionary, rules dataset, the CCI map and the destructive-pattern table carry all five `source` fields, with a `license_class` from the allowed set. The field list and the class list are **read out of `extract/schema.py`'s text**, never restated here. | **Yes**, `tests/test_provenance_fields.py` (8): one field dropped at a time, the superset assertion against `schema.PROVENANCE_FIELDS`, an assertion that `qa.py` reads the tuple rather than restating something that happens to match, and unreadable/empty schema tuples. Empty-set case in `tests/test_empty_set_gates.py`. | The **check** is deliberately independent of `extract/schema.py` (that is the point of Q3) — only the constant is shared. So the two can still disagree about what "missing" means, just not about which fields are required. |
| **Q4** | Every command entry carries `verify`, `undo`, and a `blast` of `green`/`yellow`/`red`. | **Yes**, `tests/test_empty_set_gates.py` (6) for the empty case. The per-field checks have no fixture. | Proves the fields are **present and well-typed**, never that a `verify` command verifies anything or that an `undo` undoes it. Content validation is CR-T-34. |
| **Q5** | Every feature marker is present, in the place its kind requires: `code` markers (`function …(`, `var …=`, `document.…`) in live app-script code, `html` markers (`id="…"`) in the static markup outside every `<script>` and HTML comment, `text` markers (user-visible copy, a CSS at-rule, the assembler's comment marker) anywhere in the file. A marker for a module this build does not have yet reports PENDING, never PASS. | **Yes**, `tests/test_airgap_and_markers.py`: a code marker planted in a block comment, in a line comment and in a string literal; a region id planted in a JS string and in an HTML comment; the copy marker that must stay legal inside a string; and an end-to-end demotion of `function renderRail(` to an HTML comment through `gate_q5`. | A marker is a **name**, not behaviour. `function renderRail(` existing in live code says the rail renderer exists; it says nothing about what it renders. |
| **Q6** | No `TODO`/`FIXME`/`XXX`/`lorem ipsum`/`example.com`/`CHANGEME` in the shell. | **None.** | A plain text scan, by design. Low stakes by design too: the blast radius of a miss is cosmetic. Unlike Q5, it is not standing in for a structural claim. |
| **Q7** | Every `localStorage`/`sessionStorage` identifier in the app script sits inside a `try{…}catch` block, and storage records are schema-versioned. Braces are counted over a **lexically masked** copy. | **Yes**, `tests/test_storage_guard.py` (10): the AL-GATE3-003 desync driven five ways (a brace in a string, a template literal, a regex literal, a `//` comment and a `/* */` comment), the closing-brace half that would shorten a span and produce a false FAIL, guarded/unguarded controls, and masking-is-lossless assertions. | Proves the access is **wrapped**, not that the `catch` does anything sensible with the exception. |
| **Q8** | Embedded record counts reconcile with `_meta` for all four RULES datasets, the command entries and the CCI map; no dataset declares `partial`; every dataset names a generator Q15 re-runs. | **Yes**, `tests/test_empty_set_gates.py` for the empty case. The count-mismatch path has no fixture. | Reconciles counts. Q10 reconciles content. |
| **Q9** | Every embedded rule has a STIG ID and a CAT of I/II/III; every CAT I rule carries both check and fix text; CCI present wherever the source has one; NIST present wherever the CCI maps; **and at least one CAT I rule exists per release**. | Indirect. The zero-CAT-I guard is pinned by `tests/test_empty_set_gates.py`. | — |
| **Q10** | Every embedded STIG ID is present in the pinned XCCDF and vice versa (full ID-set parity), and a deterministic stride sample is re-parsed and compared on title, rule id, CCI, CAT, and full check and fix text. | **Yes**, and it is the best-covered gate after Q17: `tests/test_accuracy_gate.py` (9) — control, mutated text, dropped rule, renamed rule, duplicate ID, determinism. | The sample layer alone **would** be fail-open on zero embedded rules; the ID-set **parity** layer closes it, and that layer was added for a different stated reason (drift outside the stride). It is not redundant. Do not remove it. |
| **Q11** | A stride sample of CCI→800-53 mappings matches a fresh parse of the DISA CCI list; every CCI referenced by an embedded rule resolves; the map carries nothing no rule cites; an empty map is refused. | **Yes** for the empty-map guard (`tests/test_empty_set_gates.py`). No dedicated fixture file the way Q10 has one. | Sampled, not exhaustive, on the value comparison. |
| **Q12** | Every entry carries all four RHEL keys with an explicit value in each (a command, an `unavailable` with a reason, or a resolved `same_as`), and every tool declares availability for all four. | **Yes**, `tests/test_empty_set_gates.py` for the empty case. | — |
| **Q13** | Every entry's tool and category resolve; every `stig_id`/`rule_id` pair resolves in the right RULES dataset and carries its reverse link; every `source_ref` resolves. | **Yes**, `tests/test_empty_set_gates.py` for the empty case, including empty tool-id and category **target** sets. | — |
| **Q14** | No curated string on a `paraphrase-only` entry shares an 8-gram with any staged raw source; **and** every release whose flag dictionary ships populated has its raw man/`--help` text staged under `content-src/raw/rhel<N>/`. | **Yes**, `tests/test_paraphrase.py` (15) — the file ADR-001 §7.3 promised and Al's review found missing. A sentence lifted at run time out of a real staged source, in notes and in a flag explanation; honest paraphrase passing; the same sentence on a `verbatim-ok` entry passing; the 7-vs-8 word boundary in both directions; corpus-coverage refusals including an empty directory. | 8-gram shingles catch **lifting**, not close paraphrase, and not a lifted run of seven words or fewer. That is the documented rule, not a defect — but it is a floor, not a guarantee of licence compliance. |
| **Q15** | Re-running each extractor with `--check` reproduces the committed content byte for byte, and every generated dataset names a generator this gate actually re-ran. | **None** directly. `tests/test_build_fails_on_broken.py` (2) exercises the adjacent build-time schema path. | Trusts each extractor's own `--check` mode to be honest. A bug in a `--check` path is inherited whole. |
| **Q16** | Every `expected_output` block has a capture record carrying all nine required fields, and no entry claims `verified` without a `{by, on, host}` receipt. | **Yes**, `tests/test_empty_set_gates.py` for the empty case. | Proves a receipt **exists and is shaped right**. Whether the capture was really taken on that host is a process control, not a gate. |
| **Q17** | Render safety: zero inline `on*=` handlers, no `eval`/`new Function`, `esc()`/`escapeAttr()` defined, no trojan-source characters in the shell **or the data island**, no forbidden sink (`insertAdjacentHTML`, `outerHTML`, `document.write`, `createContextualFragment`, `srcdoc`), `.innerHTML` only ever an assignment target, `setAttribute` only with a readable and non-dangerous literal name, every segment reaching a sink or a derived accumulator is a literal or an escaper call, and no computed member assignment reaches a sink by a bracketed or fused name. | **Yes**, the best-covered gate in the file: `tests/test_render_audit.py` (10) drives 15 committed bypass fixtures plus safe/unsafe controls and the shipped shell. | **Q17 proves the escapers are CALLED. It cannot prove they escape** — that is Q19's job, and the two are only meaningful together. A property name produced at run time from data is invisible to it (MCR-SEC-014, condition D2, recorded in `docs/CODE_STANDARDS.md` §1). |
| **Q18** | Command-assembly safety: the three escaping domains never nest; the assembler lifted out of the **shipped artifact** rejects or provably single-quotes every hostile vector across every field type, release and argument shape; positive controls prove it is not passing by rejecting everything; and the harness's JSON report is checked for shape before it is believed. | **Yes**, twice over: `tests/test_hostile_inputs.py` (10) drives the harness against `template.html`, the harness carries its own positive and negative controls, and `tests/test_q18_report.py` (15) drives the report consumer with an empty body, a truncated body, a renamed field, wrong types, a non-object body, zero checks and a non-zero exit. | Proves **shell-token** containment plus a firewalld rich-rule oracle. There is no YAML sink in this build; if one returns it ships a YAML-parsing oracle in the same commit or the harness refuses to run (MCR-SEC-010). |
| **Q19** | Escaper behaviour: `esc()`, `escapeAttr()` and `escapeRegex()` are lifted verbatim out of the **shipped artifact** and RUN under node against 92 declared and 3 generated hostile vectors. `esc()` leaves no raw `< > " '` and no bare `&`, and round-trips exactly through a strict entity decoder. `escapeAttr()` adds `` ` `` and `=`. `escapeRegex()` escapes every metacharacter present, leaves none bare, compiles, matches its own input, and does not match what only the unescaped pattern would. | **Yes**, three ways: `tests/test_escaper_behaviour.py` (11) mutates the shipped escapers four ways (identity, drop-the-character, half-escaped, `escapeRegex` alone) and asserts each fails; the probe runs its own battery against three known-broken escapers **before reporting anything** and refuses to report a PASS unless it just failed all of them; and `TheRenderAuditCannotSeeThis` keeps Al's original transcript executable. | Proves what the functions do **to strings**, not that every render path calls the right one for its context — that is Q17. Neither gate is sufficient alone. |
| **Q20** | Flag-dictionary coverage and citation honesty (MCR-SEC-020 / MCR-SEC-019, condition E5 of Marcus Reed's D4 review). Half one: distinct long options in each committed raw capture under `content-src/raw/<rel>/` against the long option names `content/flags_rhel<rel>.json` carries, for all 44 tool/release pairs, compared to the dated acceptance in `content-src/flag_coverage_baseline.json` — a shortfall that GROWS fails, one that shrinks reports and asks for the baseline to be tightened. Half two: a generator citing a raw capture line must cite a line that shows the option it actually emits, and the option that counts is the one bound to a value or a composed rich rule, not a decoration. | **Yes**, both halves, before the gate was committed: tightening one baseline row gives *"RHEL 8 / auditctl: the flag dictionary now misses 2 long options documented in the raw capture, up from the accepted 0"*, and reverting `gen-fw-allow-service`'s citation to `#L310` gives *"the eight lines around it show none of the options it actually emits (--add-rich-rule)"* — the defect MCR-SEC-019 reported. | Counts **long options only**, and says so rather than implying more: short options in man-page prose cannot be counted honestly. The raw count is an upper bound (prose, per-subcommand options), which is why this is a regression gate against recorded numbers and not a coverage percentage with a threshold invented on the spot. It does not close the shortfall — that is CR-T-09/10's, accepted with a date in `docs/POAM.md`. |
| **JS** | `node --check` parses the extracted app script. | None; informational by design. Node absent correctly downgrades to PENDING. | Syntax only. |

Node is **required** by Q18 and Q19 and optional for the `JS` gate (Q20 needs neither: it reads files). The asymmetry
is deliberate and stated in both gate docstrings: a missing syntax check is an
inconvenience, and a missing injection or escaping check is a fail-open wearing a
politer word.

---

## Gates with no negative control

Named here rather than left to be discovered by the next reviewer:

1. **Q1**, except its island-escaping half. Nothing has ever broken the script
   count, corrupted one of the five version strings, or mismatched the sha256
   sidecar and asserted Q1 catches it.
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
| MCR-SEC-010 | Dead YAML quoter made Q18 pass on a domain that did not exist | Quoter removed; harness refuses a quoter with no oracle |
| MCR-SEC-013 (D1) | Conditional positional literal shifted arguments | `isPositionalToken()` / `spec_template_errors()`, merged at `9cf092d` |
| MCR-SEC-014 (D2) | Computed member access reached a render sink | `computed_sink_failures()`; residual note in `docs/CODE_STANDARDS.md` §1 |
| AL-GATE3-001 | Q17 proves the escapers are called, never that they escape | **Q19** + `tests/escaper_probe.js` + `tests/test_escaper_behaviour.py` |
| AL-GATE3-002 | D2's `CODE_STANDARDS.md` note was missing | Present at `9cf092d`; verified, no action needed |
| AL-GATE3-003 | Q7's brace counter desynced on a literal | `mask_js_literals()` + `tests/test_storage_guard.py` |
| AL-GATE3-004 | Six gates passed on an empty bundle | `empty_set_failure()` + `tests/test_empty_set_gates.py` |
| AL-GATE3-005 | Q3's provenance list had drifted weaker than `schema.py`'s | `parse_schema_tuple()` + `tests/test_provenance_fields.py` |
| AL-GATE3-006 | Malformed harness report crashed Q18 with a `KeyError` | `harness_report_failures()` + `tests/test_q18_report.py` |
| AL-GATE3-008 | MCR-SEC-013's fix appeared absent | Present at `9cf092d`; verified, no action needed |
| MCR-SEC-015 (E1) | 20 short-option tokens joined with `=`, which getopt does not accept | `flagJoin()` derives the join from the flag's shape; `flag_join_errors()` at build time; the golden-command table and the getopt syntax oracle in the harness |
| MCR-SEC-016 (E4) | Four fields with closed grammars typed as free text | `lvm_size` / `group_list` field types; 31 closed-grammar harness checks |
| MCR-SEC-018 (E3) | The D1 rule over-refused option-shaped conditional literals | The derived discriminator + `tests/test_positional_crosscheck.py` (3,258 shapes / 104,256 runs / 0 violations) |
| MCR-SEC-019 (E5) | A generator cited a man-page line for an option it does not emit | Citation repointed; **Q20** half two |
| MCR-SEC-020 (E5) | Q15 cannot see a systematically incomplete flag dictionary | **Q20** half one + `content-src/flag_coverage_baseline.json`; shortfall accepted with a date |
| MCR-SEC-021 (E6) | The harness was a containment oracle with no validity oracle | `tests/fixtures/golden-commands.json`, `optionSyntaxErrors()`, the enum-branch sweep, `benignFor(field, rot)` |
| MCR-SEC-022 (E7) | `flag` beside `lit` was an unchecked off-switch for the D1 rule | Dual-key token refused in both halves; the discriminator is derived from the literal |
| MCR-SEC-023 | An option emitted as a `lit` was never explained in the inspector | Option-shaped lits pushed into `flags[]`; 248 inspector flag-list checks |

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
2. **§7.3 numbers the gates Q1–Q17.** The file now runs **Q1–Q20 plus `JS`**.
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
