# Changelog

All notable changes to MD CODE RED are documented here. This project adheres to [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Fixed — D4 review MCR-SEC-015..023, conditions E1–E7 (2026-09-17, branch `salm/milo/generators`)

Marcus Reed's D4 review of the generator tranche at `69fb1c2`/`996b504` returned **DENY** — one HIGH
that blocks on its own, plus conditions E1–E7 and two advisories. Everything below lands on the same
branch. E2 (MCR-SEC-017, the rebase onto `origin/main`) was already met at `996b504`; D3 (no YAML
sink without a YAML quoter *and* a YAML-parsing oracle) remains open and untouched, because this
branch has no YAML sink.

#### MCR-SEC-015 — HIGH — condition E1 — short options joined with `=`

The assembler joined **every** flag to its value with `=` unless the token carried `eq:false`, and
`eq:false` was used nowhere in the 24 shipped specs. 20 short-option tokens across 11 of 24
generators emitted `-X=value`, which getopt(3) does not accept — the `=` is passed through as the
first character of `optarg`.

    auditctl -w='/etc/motd' -p='r' -k='identity'      ->  auditctl -w '/etc/motd' -p 'r' -k 'identity'
    chage -M='60' -m='7' -W='14' 'svcacct'            ->  chage -M '60' -m '7' -W '14' 'svcacct'
    useradd -m -c='RFC-1234' -G='wheel' -s='/bin/bash' 'svcacct'
                                                      ->  useradd -m -c 'RFC-1234' -G 'wheel' -s '/bin/bash' 'svcacct'
    lvcreate -L='10G' -n='lv0' 'vg0'                  ->  lvcreate -L '10G' -n 'lv0' 'vg0'

Most fail loudly at the tool, which is the safe direction. Two do not: `auditctl` produces a STIG
control that looks applied and is not, and `useradd` silently sets GECOS to `=RFC-1234` and the login
shell to `=/bin/bash`.

**Fixed at the assembler, not per token.** A new `flagJoin()` inside the `MCR-ASSEMBLER` block
derives the join from the flag's own shape — `--long` joins with `=`, `-X` joins with a space — so
all 20 tokens are correct with **no content edit at all**, and a 25th generator inherits the rule.
Two escape hatches survive, each legal only on the shape it belongs to: `eq:false` on a long option,
`join:"glued"` on a short one for a tool that requires `-Xvalue`. Neither is used in the tranche.

**Deviation from the recommended fix, stated plainly.** MCR-SEC-015 recommended `eq:false` on every
single-dash token plus a schema rule refusing a single-dash flag whose `eq` is not `false`. That is
20 content edits and a rule an author can still defeat by forgetting a key on the twenty-first
generator. The derived rule inverts it: a short option carrying `eq` **at all** is refused, because
the join is derived and a declaration is a disagreement with the rule rather than a restatement of
it. `extract/schema.py`'s new `flag_join_errors()` is the build-time half; the assembler returns
`null` at run time for the same token.

#### MCR-SEC-022 (E7) and MCR-SEC-018 (E3) — the discriminator is now derived

`flag` beside `lit` was an unchecked off-switch for the D1 positional rule. It emits nothing on a lit
token; its only effect was to make `isPositionalToken()` and `positional_indexes()` look away — so
`{lit:"0644", flag:"-P", requires:"m"}` was accepted and reopened MCR-SEC-013 through the key meant
to close it. Marcus's four-row table is now a test, on every release, in both halves:

| template | build time | run time, gate supplied | run time, gate absent |
|---|---|---|---|
| `{lit:"0644",requires:"m"}` | REFUSED | — | — |
| `{lit:"-P",flag:"-P",requires:"m"}` | REFUSED | `null` | `null` |
| `{lit:"0644",flag:"-P",requires:"m"}` | REFUSED | `null` | `null` |
| `{lit:"/etc/shadow",flag:"-x",requires:"m"}` | REFUSED | `null` | `null` |
| `{lit:"-P",requires:"m"}` (derived) | accepted | `chmod -P '/etc/foo'` | `chmod '/etc/foo'` |

A token carrying both `lit` and `flag` is refused **even when they agree**: the branch shipped two
exemplars of the shape, and an author who hits the D1 build error should not have a
documented-looking lever to pull. Whether a literal is an option is derived from the literal — a
`lit` matching `FLAG_TOKEN_RE` is an option and never occupies an argument slot — so a real option
needs no key. `gen-lvextend-grow` and `gen-setsebool-set` lose their `flag` key and keep `requires`,
which is the regression Marcus said to watch for. This also closes MCR-SEC-018's over-refusal without
the dangerous workaround it invited: deleting `requires` to clear the build error would have made
every SELinux boolean change **persistent** when the operator asked for runtime-only.

#### MCR-SEC-023 — advisory — a lit-emitted option is now explained

The lit branch pushed the word and returned, so `sshd -T`, `setsebool -P`, `lvextend -r` and
`journalctl --no-pager --boot` appeared in the command and were absent from the flag-by-flag panel.
The same derived test decides it: an option-shaped literal goes into `flags[]`, in command order.
With no curated `explain` and no dictionary hit the panel renders *"unverified — see man page"* — the
no-guess law, not a guess.

#### MCR-SEC-016 — condition E4 — closed grammars where one exists

    lvm_size    ^([+-]?\d+(\.\d+)?[bBsSkKmMgGtTpPeE]?|\d+%(FREE|VG|PVS|ORIGIN))$
    group_list  ^[a-z_][a-z0-9_-]{0,31}(,[a-z_][a-z0-9_-]{0,31})*$

`gen-lvcreate-new-lv.size`, `gen-lvextend-grow.size`, `gen-useradd-create.groups` and
`gen-usermod-add-group.groups` move off `comment`, the one free-text type. Nothing here was
injectable — every value is `shQuote`d and every wrong one fails closed at the tool — but
`lvextend -L 'ticket RFC-1234' -r '/dev/vg0/lv0'` assembled and rendered Copy on a yellow-blast
storage command. The `lvm_size` label is load-bearing rather than decorative: it is the placeholder
and the refusal reason, and the only place in the UI that distinguishes `10G` (set the volume to) from
`+10G` (grow it by). The four `comment` fields Marcus called defensible stay free text; his unrated
note on `chronyd -Q` is recorded in `docs/POAM.md` instead of being dropped.

#### MCR-SEC-019 and MCR-SEC-020 — condition E5 — gate Q20

`gen-fw-allow-service` cited `firewall-cmd.man.txt#L310` — `--add-service`, an option it does not
emit, since it composes a rich rule. Repointed to `#L538`. **CLOSED.**

The dictionary finding was never "there is a gap": it was that nothing could see one, because Q15
re-runs the extractor and diffs the output against itself. New gate **Q20** has two halves, both
shown able to fail before commit (it is Q20, not Q19: the merge with `origin/main` at `da2ab47`
brought in Q19, the escaper property gate from Al Kowalski's Gate 3 review):

- **Coverage** — distinct long options in each committed raw capture against the dictionary, for all
  44 tool/release pairs, compared to `content-src/flag_coverage_baseline.json`, which records the gap
  with its acceptance date, who accepted it and the ticket that owns closing it (CR-T-09/10). A
  shortfall that **grows** fails; one that shrinks reports and asks for the baseline to be tightened.
  Measured: firewall-cmd 16 of 205 long options on RHEL 8, dnf/yum 61 of 140, nmcli 2 of 20.
- **Citations** — a generator citing a raw capture line must cite a line showing the option it emits,
  and the option that counts is the one bound to a value or a rich rule, not a decoration like
  `--permanent` that half the firewall-cmd man page mentions.

**MCR-SEC-020 is ACCEPTED WITH A DATE** (2026-09-17) in `docs/POAM.md` alongside the `chronyd -Q`
note and a re-confirmed MCR-SEC-014; closing the shortfall belongs to CR-T-09/10.

#### MCR-SEC-021 — condition E6 — the harness gets a validity oracle

The 12,689 content-spec checks were a **containment** oracle only. They assert a hostile value is
rejected or confined to a single-quoted token whose skeleton matches the benign control, and never
assert the benign control is a valid invocation of its tool. That is exactly how 20 malformed joins
passed 76,225 checks with 0 failures.

- `tests/fixtures/golden-commands.json` — one row per generator: stated benign values and the **exact**
  command it must emit on each release (`null` where gated off), the flag list the inspector must show,
  the blast it must rate, and the man-page rule the row pins. Hand-authored from each tool's man page
  and getopt(3), never generated from the assembler: a table regenerated from the code it tests is a
  transcript. Completeness runs both ways — a generator with no row fails, a row naming no generator
  fails.
- `optionSyntaxErrors()` — getopt(3) syntax on every benign command the harness assembles, with three
  negative controls including MCR-SEC-015's own reproduction.
- `benignFor(field, rot)` — no longer pins every enum to `opts[0]`, so a hostile value is fuzzed
  against every branch of its neighbours rather than only the safest one.
- A new enum-branch **control** sweep: every generator × every enum field × every option × every
  release against the real `dangerous.json` — assembles, valid syntax, never below the declared blast,
  and every destructive branch (`remove`/`stop`/`disable`/`off`) at least yellow. Checked in the honest
  direction: a green-declared generator must have a branch **raised** and a branch still **green**, so
  a pattern table that rated everything yellow would fail.

#### Also

- `tests/test_positional_crosscheck.py` + `tests/shift_crosscheck_driver.js` — Marcus's exhaustive
  shift sweep re-run after the discriminator change and extended with option-shaped literals: every
  2-to-4-token template over 8 token kinds containing a literal (4,336 shapes), filtered to the 3,258
  `extract/schema.py` accepts, driven over 4 releases × 8 supplied/absent combinations — **104,256
  runs, 0 shift violations**. The expectation is computed in Python from `schema.positional_indexes()`
  and the answer comes from the assembler lifted through the harness's purity-checked extractor, so
  neither side restates the other's rule. Shown failing against the pre-fix tree.
- Nine new schema fixtures (seven invalid, two valid) covering the join rule and the dual-key token.
- **Fail-first commits**, both hashes recorded: `77a688f` (golden table RED, 44 harness failures) →
  `5315fef` (E1 green); `1389487` (discriminator table RED, 78 harness + 5 unit failures) → `dee9005`
  (E7/E3/MCR-SEC-023 green).

**Functions changed in `template.html`, all inside the `MCR-ASSEMBLER` block, and nothing else in that
file:** `flagJoin()` (new — the derived join rule), `isPositionalToken()` (the derived positional
discriminator), and `assembleCommand()` in three places (the field-flag branch and the richRule branch
call `flagJoin()`; the lit branch refuses a dual-key token and pushes option-shaped literals into
`flags[]`). Two rows were added to the `FIELD_TYPES` table for E4.

**Merged with `origin/main` at `da2ab47`** (the Gate 3 `qa.py` hardening merge). Only `qa.py`,
`README.md` and `docs/CHANGELOG.md` conflicted; both doc conflicts kept both sides, and in `qa.py`
both new gates were kept — theirs stays **Q19** (escaper behaviour, already referenced by
`docs/QA_GATES.md`) and this branch's coverage gate became **Q20**. `template.html`,
`extract/schema.py`, `content/` and every test file auto-merged.

#### Q21 — no tracked source file spells an invisible character

A defect of mine, found after the merge and fixed on the same branch. `dd01ad7` rewrote
`tests/fixtures/hostile-inputs.json` through `json.dump(..., ensure_ascii=False)` while adding the two
new benign values, and **eight** invisible-character vectors the file states as JSON `\u` escapes on
purpose — U+200B, U+200D, U+202E, U+FEFF, U+00AD, U+2028, U+2029, U+2065 — came back out as the raw
characters they name. Q17 could not see it (it scans the built artifact, which this fixture never
reaches) and the harness could not (it reads the file as JSON, where an escape and its character are
one value). The fixture is now byte-identical to `origin/main` apart from the two added field types,
and the harness still rejects all 11,744 invisible-character vectors, so what is tested did not change
— only how it is written. New gate **Q21** walks `git ls-files` with Q17's own `TROJAN_RANGES` table;
`tests/test_no_raw_trojan_chars.py` plants each character class in a temp directory and watches the
scanner fire before believing it. Committed fail-first at `484ec23` (Q21 FAIL, 8 findings).

#### Marcus Reed's D4 re-review — conditions F1, F2, F3

**F1** — the fixture carried **eight** raw characters, not three: U+200B, U+200D, U+202E, U+FEFF,
U+00AD, U+2028, U+2029, U+2065. All eight re-escaped; the file is byte-identical to `origin/main`
apart from the two field types E4 added, all 55 vectors parse identically, and the harness still
rejects 11,744 invisible-character vectors. Q21's character set is `qa.TROJAN_RANGES` — Q17's own
table — which already covers everything the condition lists. The gate was then **widened** on
Marcus's narrower rule: the exclusion list is now **empty**, all 226 tracked files are scanned
(`stig-src/` and `content-src/raw/` included, both measured clean), and the single allowance is a
U+FEFF at offset 0 — allowed at 0, caught one byte later, both halves tested.

**F2 / MCR-SEC-025** — settled from the pinned capture, and the spec **stays**: chronyd(8) SYNOPSIS is
`chronyd [OPTION]... [DIRECTIVE]...` (`content-src/raw/rhel8/chronyd.man.txt#L7`, identical on
RHEL 10) and `-Q` takes no argument (#L68), so configuration directives are **operands** accepted
after the options and `chronyd -Q 'server time.mil iburst'` is correct as emitted. The golden row is
unchanged. What was wrong was the *modelling* — the directive is a separate operand, not `-Q`'s value
— so the citation moves from `man 8 chronyd` to the `-Q` line in the capture, and the operand grammar
is recorded in the entry's `notes`, which the renderer surfaces.

**F3** — the Q20 ratchet gets a retirement plan: **owner Caleb Stone** (extractor fix, CR-T-09
follow-up), **retires 2026-09-25**. Q20 now FAILS from 2026-09-26 unless the baseline is regenerated
against the new dictionaries or re-dated in writing, and `tests/test_coverage_baseline_expiry.py`
watches that fire against an injected date rather than leaving it to be discovered on the day. An
accepted residual does not get to become a permanent one by nobody looking.

**Gates on the merged tree, from a clean `dist/`:** `build.py` OK and reproducible · `qa.py`
**Q1–Q21 PASS** (22 gates with `JS`) · `unittest discover` **159 OK** (135 from the hardening merge,
plus the 24 added here) · `node tests/hostile_harness.js` **81,577 checks, 0 FAILED** (was 76,225) ·
artifact sha256 `9eb3402689e8c4f68f914a8154515aa117b999da646e9fb6c0bb1ce8c40bab2b`.

### Added — CR-T-17..25 guided-form generators (2026-09-17, branch `salm/milo/generators`)

24 generator specs, one `GENERATORS` registry, form renderer and `decodeCmd()` — the P0 generator
tranche Zee assigned after the assembler merged. The assembler itself (`assembleCommand`,
`validateField`/`validateSpec`, `shQuote`, `composeRichRule`, `isPositionalToken`, `blastFor`) is
untouched; everything here is content (`content/commands.json`, `content/tools.json`,
`content/dangerous.json`) plus rendering code that calls the assembler the same way a static entry
does.

- **CR-T-17** — ported six Grey Beard generators: `gen-fw-set-default-zone`, `gen-fw-open-port`,
  `gen-fw-allow-service` (firewall-cmd), `gen-nmcli-static-ipv4`, `gen-journalctl-unit-logs`,
  `gen-lvcreate-new-lv`, `gen-lvextend-grow`, `gen-sshd-test-config`, `gen-useradd-create`,
  `gen-usermod-add-group`.
- **CR-T-18** — `gen-systemctl-query` (status/is-active/is-enabled/is-failed, blast green) and
  `gen-systemctl-manage` (start/stop/restart/reload/enable/disable, blast yellow) — split so a read
  action and a state-changing action never share one blast level.
- **CR-T-19** — `gen-dnf-package` (`versions: ["8","9","10"]`) and `gen-yum-package` (all four). RHEL 7
  never sees a fabricated `dnf` command: the generator is version-gated AND `tools.json`'s `dnf` entry
  is `unavailable` on RHEL 7 with `reason`/`alternative: "yum"`, so the sidebar shows the note twice
  over — once on the tool, once on the (absent) generator.
- **CR-T-20** — `gen-setsebool-set` (`-P` persist is an optional lit bound via `requires:`) and
  `gen-semanage-port-add`.
- **CR-T-21** — `gen-chage-list` (`-l`, read-only) and `gen-chage-set-aging` (`-M`/`-m`/`-W`), both
  man-page-sourced per ADR-001 §2.4 (no RHEL guide covers `chage`'s own flag grammar).
- **CR-T-22** — `gen-auditctl-watch` (`-w`/`-p`/`-k`) and `gen-ausearch-by-key` (`-k`/`-ts`).
- **CR-T-23** — `gen-rsyslogd-test-config` (`-N1 -f`, parses and validates, never starts the daemon).
- **CR-T-24** — `gen-chronyd-one-shot-check` (`-Q`, one correction and exit). The RHEL 7
  chronyd-default/legacy-ntpd note (CR-P0-05 AC3) is carried in the entry's own `notes` field, which
  `assembleCommand()` already surfaces to the renderer, and in `tools.json`'s `chronyd` availability
  notes per version.
- **CR-T-25** — `gen-podman-ps` and `gen-podman-stop` (`versions: ["8","9","10"]`), with `tools.json`'s
  `podman` entry `unavailable` on RHEL 7 (no supported package, base or Extras). RHEL 7 never fabricates
  a podman command (CR-P0-05 AC4): both the generator and the tool are gated, independently.

**Content authoring note.** `flags_rhel8.json`/`flags_rhel10.json` (CR-T-09/10) are the host-verified
source for every `flag`-typed token in these specs, EXCEPT `--add-rich-rule` and `--permanent` on the
two firewall-cmd rich-rule generators: both are real, present in the raw RHEL 8/10 man-page capture
(`content-src/raw/rhel{8,10}/firewall-cmd.man.txt` lines 538/247+), but missing from the generated
dictionary because `extract_flags.py`'s synopsis-line regex captures only the leading `[--permanent]`
token repeated ahead of firewalld's ~90 per-option lines and misses the option that follows it on the
same line (e.g. `--zone=zone`, `--add-service=service`). Cited from the raw capture directly instead of
invented; flagged as an extractor follow-on, not fixed here (extract/ is a different owner's surface).
RHEL 7/9 have no `flags_rhel{7,9}.json` (empty placeholders, no host read yet) — every field on those
releases is either gated off (`field.versions`) or documented from the RHEL 7 System Administrator's
Guide / RHEL 9 guides (source `url_or_man`/`sha256` from the corpus manifest,
`license_class: paraphrase-only`), never captured verbatim.

**Gates.** `qa.py` Q12 and `tests/test_schema.py` learned that `"template" in e` (a generator spec)
keeps the four-version promise via `spec.versions`/`field.versions`, not a `rhel_versions` object —
both would have failed the FIRST real generator spec, a gap `extract/schema.py`'s own `spec_errors()`
already closed at build time but these two had not caught up to. `tests/hostile_harness.js` gained a
content-spec sweep: it loads `content/commands.json` directly and fuzzes every field of every one of
the 24 generator entries with the full hostile-vector set, in that entry's own template rather than a
synthetic analog (12,689 checks; the harness's existing per-field-type sweep stays as-is and still runs
first). `python3 build.py && python3 qa.py && python3 -m unittest discover -s tests && node
tests/hostile_harness.js` all green.
### Fixed — BQP Gate 3 review of `qa.py`: AL-GATE3-001/003/004/005/006, plus Q2/Q5/Q14 (2026-09-17, branch `salm/milo/qa-hardening`)

Al Kowalski's Gate 3 diff review of `qa.py` as trust-path code returned **PASS WITH ISSUES**:
one HIGH, five MEDIUM/LOW, and two rows of the per-gate table marked "fail-open risk found"
with no negative control. `qa.py` is the merge gate — a bug in it fails open and nothing
downstream notices — so every fix below landed as a pair of commits: the gate shown to FAIL
first, then the change that turns it green.

**AL-GATE3-001 (HIGH) — the escapers were never proven to escape.** `segment_ok()` treats any
segment matching `^(esc|escapeAttr|escapeRegex)\s*\(` as safe, full stop, and `gate_q17` checks
that the strings `"function esc("` and `"function escapeAttr("` exist. Together those prove a
function under that name is defined and every render path funnels through a call to it. They
cannot prove the body does anything. Al's reproduction:

```python
qa.render_sink_failures(shell_with_identity_escapers)
# -> ([], 4)   — zero failures, 4 expressions "audited"
```

`function esc(s){return s;}` defeats the product's entire XSS defence with **zero change to any
call site**, and every call site keeps looking exactly as safe as it does today.

**Q19** closes it by running the functions instead of reading them. `extract_js_function()`
brace-matches `esc`, `escapeAttr` and `escapeRegex` out of the SHIPPED artifact over a lexically
masked copy — the same discipline `hostile_harness.js` applies to the assembler block, for the
same reason: the code that clears the gate has to be the code that crosses the air gap. The three
functions go to `tests/escaper_probe.js` under node against 92 declared vectors and 3 generated
ones (100k, 20k and 5k characters). The properties:

* `esc()` — no raw `<`, `>`, `"` or `'` in the output, every `&` opens a well-formed entity, and
  a strict decoder round-trips the output back to **the exact input**. The round trip is not
  decoration: an escaper that *deletes* the dangerous characters is XSS-safe and would silently
  eat every `<` in a DISA fix text, and a no-raw-metacharacter test alone would rate it clean.
* `escapeAttr()` — all of the above plus no raw `` ` `` and no raw `=`, which is the reason it
  exists as a separate function from `esc()`.
* `escapeRegex()` — every metacharacter present is backslash-escaped and none left bare, the
  pattern compiles, matches its own input, and does **not** match what only the unescaped pattern
  would (`a.c` must not match `abc`) — the half an identity function would otherwise pass.

The probe runs its own battery against three known-broken escapers (identity, drop-the-character,
half-escaped) **before reporting anything**, and refuses to report a PASS if any comes back clean.
Node is required, as for Q18: an escaping check that downgrades itself to PENDING on a thin runner
is a fail-open wearing a politer word. Mutation evidence: 76 named failures against the shipped
artifact with `return s;` spliced into `esc()`; 0 against it as it ships.

**AL-GATE3-003 (MEDIUM) — Q7's brace counter desynced on a literal.** `try_block_spans()` counted
raw `{`/`}`. One unbalanced brace inside a string literal inside a `try` body shifted the depth, so
the span ran past its own `catch` and swallowed the sibling code after it — and a genuinely
unguarded `localStorage` call in that sibling code was reported as one of the audited try/catch
references. New `mask_js_literals()` returns a same-length, same-line-breaks copy with comments
blanked entirely and the *contents* of strings, template literals and regex literals blanked, their
delimiters kept. The masking happens inside the span finder, not in its caller: a caller that has
to remember to launder its input is a caller that will one day forget, which is how this arrived.
Driven five ways in `tests/test_storage_guard.py`, including the closing-brace half that would
*shorten* a span and produce a false FAIL — a gate that cries wolf gets switched off.

**AL-GATE3-004 (MEDIUM) — six gates passed on an empty bundle.** Q3, Q4, Q8, Q12, Q13 and Q16 all
reported PASS with no entries, no tools and no rules, because a per-item loop records a failure only
by finding something wrong *with* an item. Q9 has guarded its own empty case since CR-T-07 with the
reasoning written out in a comment; that reasoning was never about CAT I rules. One shared
`empty_set_failure()` helper, and every gate says why *its* empty set is suspicious. Q7 and Q18 grew
the same guard in their own commits. Recorded and not fixed: `extract/schema.py`'s `content_errors()`
has the same shape one layer down, so an empty `commands.json` still clears build-time validation —
out of this branch's scope, caught by all six gates at the merge gate, written down in
`docs/QA_GATES.md`.

**AL-GATE3-005 (MEDIUM) — Q3 had drifted weaker than the check it doubles.** `qa.py` required four
provenance fields; `extract/schema.py` requires five. The missing one was `version`, the field
schema.py's own docstring calls mandatory because "a source that cannot say which version of the
document it came from cannot be re-checked". Masked only because `build.py` runs the stricter check
first. `parse_schema_tuple()` now reads `PROVENANCE_FIELDS` and `LICENSE_CLASSES` out of
`extract/schema.py`'s **text** — the same no-import discipline `load_build_constants()` uses on
`build.py`. The constant is shared; the independent *check* Q3 exists to be is not. An unreadable or
empty tuple is a FAIL, never a fallback.

**AL-GATE3-006 (LOW) — a malformed harness report crashed Q18.** `rep["checks"]` and seven siblings
were read unguarded, so a harness exiting 0 with key-incomplete JSON raised `KeyError('checks')` mid
run, with no `try/except` anywhere in `main()`. It failed closed — Python exits non-zero — so it was
never a silent pass; it was a stack trace that reads identically whether the harness broke or whether
it caught something real. `harness_report_failures()` now trusts nothing about the report's shape:
non-object bodies, a non-list `failures`, missing counts, counts of the wrong type (`True` is an
`int` in Python and is not a count) and zero checks are each one FAIL line naming the reason.

**Q2 — the air gap could be spelled around.** The scan was `re.findall` for `fetch(`,
`XMLHttpRequest`, `WebSocket`, `navigator.sendBeacon`, `import(`. Al placed it in the same
structural class as the Q17 computed-member gap MCR-SEC-014 closed, but undocumented and untested
rather than accepted and recorded. `network_call_failures()` applies D2's rule to the air gap and
adds the shape Q17 never needs: a render sink is always *written*, a network API only has to be
*reached*, so `var f = fetch;` is the whole bypass. Four routes closed — the name in real code
called or not, the name in brackets, the name fused out of string literals (inline, through a
variable, or split across a literal and a variable), and a CDN host assembled the same way — with
ten controls covering every computed-member shape `template.html` writes.

**Q5 — a marker in a comment counted as a feature.** A substring match over the whole file, standing
in for structural claims like "the rail renderer exists". `marker_kind()` derives the kind from the
marker's own text, leaving `MARKERS` a list of 3-tuples so tranches that add markers do not collide
over a schema change: `code` markers must start at a position that survived masking, `html` markers
must be in the markup outside every `<script>` and HTML comment, and `text` markers — user-visible
copy, a CSS at-rule, the assembler's own comment marker — are matched as text **on purpose**,
because copy lives in a string literal and there is nowhere else for it to live.

**Q14 — the gate nobody could drive.** ADR-001 §7.3 promised `tests/test_paraphrase.py`; it did not
exist, and Al's table carried Q14 as the one gate he could not rule out a fail-open for because there
was nothing to run. Q14 is split into pure pieces the way Q10 and Q17 already were, and the test file
plants a sentence lifted at run time out of a real staged source, checks honest paraphrase still
passes, checks the same sentence on a `verbatim-ok` entry still passes, and pins the 7-versus-8 word
boundary in both directions. Q14 also gained a refusal: a release whose flag dictionary ships
populated with no raw sources staged under `content-src/raw/rhel<N>/` is a FAIL, because the
dictionary was extracted *from* those files and without them the gate is comparing curated content
against a corpus it did not come from.

**New: `docs/QA_GATES.md`.** Every gate, what it proves stated narrowly, where it has been watched
failing, and what a PASS explicitly does not mean — including the four rows that still have no
negative control, named rather than left to be found. It also collects the ADR-001 §7 items that are
now stale (the superseded 8 MB ceiling, §7.3 still numbering Q1–Q17, the Q14 promise now met, the
Q10 parity layer that must not be removed as redundant) for Al, whose document it is.

Gates 19 → 20 (Q1–Q19 plus `JS`), all PASS. Unit tests 51 → 135, all OK. Hostile harness 63,536
checks, 0 failed. `template.html` untouched, so the artifact is byte-identical: sha256
`5fb9b7adfd8b60feb90baa96f43b2d622c78158959672d5c60940fcd87bd16ad`, reproducible across rebuilds.

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
