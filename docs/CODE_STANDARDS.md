# Code Standards & Security Patterns

The patterns actually enforced in this repo, by a QA gate, a test, or a
consistent practice visible in the commit history -- not an aspirational list.
Where a rule is mechanically enforced, the gate that enforces it is named; where
it is a practice without a bot behind it, that is said plainly too.

---

## 1. Output Encoding: `esc()` / `escapeAttr()` at Every Render Boundary

**Mandatory, mechanically enforced (`qa.py` Q17 + Q19).** Every value written into
an `innerHTML` sink must cross exactly one of the two real functions
`template.html` ships:

```javascript
function esc(s){
  return String(s==null?"":s).replace(/[&<>"']/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
  });
}
function escapeAttr(s){
  return esc(s).replace(/`/g,"&#96;").replace(/=/g,"&#61;");
}
```

(`escapeRegex()` is a third escaper, for building a dynamic `RegExp()` --
unrelated to HTML context, listed here because Q19 tests all three the same
way.) There is no `escapeHtml()` alias and no separate URL sanitizer in this
product -- do not invent one without a reason; use `esc()`/`escapeAttr()` for
every DOM-bound value.

**Two gates prove two different things, and neither is sufficient alone.** Q17
statically proves the escapers are *called* at every sink -- every `innerHTML`
assignment (never `+=`), every `setAttribute()` with a readable, non-dangerous
literal attribute name, no `insertAdjacentHTML`/`outerHTML`/`document.write`/
`createContextualFragment`/`srcdoc`, and every segment reaching a sink or a
derived accumulator is a string literal or one of the three escaper calls --
**never a bare call to another render function**, whose returned markup the gate
cannot see inside. This is why every renderer in `template.html` uses exactly
one accumulator variable filled only by literals and escaper calls, and why a
renderer that shares a screen region with another (the STIG panel inside the
Inspector, for instance) writes its own sink as its own separate statement
rather than being spliced into the caller's string.

Q19 proves the *other* half: the three escapers, lifted verbatim out of the
shipped artifact and run live under Node against ~95 hostile vectors, actually
neutralize what they claim to -- `esc()` must leave no raw `< > " '` and no bare
`&`, and must round-trip exactly through a strict entity decoder (an escaper
that *deletes* the dangerous character instead of encoding it fails this, even
though it would also pass a naive "no `<` survived" check). A gate proving
"called" without a gate proving "correct" -- or the reverse -- is not proof of
render safety; this repo carries both because one review found the first alone
insufficient.

**`esc()` is not a sanitizer.** It neutralizes HTML metacharacters and nothing
else -- a bidi override, a NUL byte, or a zero-width character survives `esc()`
unchanged. Anywhere text crosses into a plain-text artifact outside the DOM (the
evidence export, the clipboard comment header), a *second*, separate treatment
strips that class of character (`headerSafe()`, `evidenceHeaderSafe()`/
`evidenceLineSafe()`) -- see `docs/ARCHITECTURE_BIBLE.md` Section 8. Do not
assume `esc()` alone makes a value safe to paste into a shell comment or a
compliance document; it only makes it safe to place inside HTML.

**Properties are written by name, never computed from pieces.**
`el.innerHTML = ...`, never `el["inner"+"HTML"] = ...` and never a bracketed
name assembled at runtime. A computed member assignment is allowed only where
Q17 can read the property expression as an identifier, a number, or a
dotted/indexed chain (`out[fields[i].name] = ...` is real, audited code in this
file). A property name built at runtime from data the gate cannot read as a
literal is invisible to it -- stated as a residual in `docs/QA_GATES.md`, not
hidden.

---

## 2. Input Validation: Closed Grammars, Not Filters

**Mandatory, mechanically enforced (the assembler's `FIELD_TYPES` table +
`extract/schema.py`'s matching build-time checks; fuzzed by
`tests/hostile_harness.js`, 81,577 checks on this build).** Every user-supplied
value is checked against a full-string regex, a hand-written validator, or an
enum -- never trimmed, transliterated, or "cleaned up" into something the
operator did not type. A value that fails validation is refused with a specific,
human-readable reason; it never silently becomes a different, "safe" value. RHEL
version is always one of `"7"`/`"8"`/`"9"`/`"10"` -- a literal string set, checked
with `inList()`, never a numeric range test. See
`docs/ARCHITECTURE_BIBLE.md` Section 5 for the full field-type and token model.

---

## 3. No Inline Event Handlers -- One Delegated Listener Per Event Type

**Mandatory, mechanically enforced (Q17).** No `onclick=""`/`onchange=""` etc.
anywhere in `template.html`. The entire click surface is one `click` listener on
`document`, dispatching by walking a fixed, ordered list of `data-*` attribute
selectors (`data-version`, `data-rail`, `data-tool`, `data-entry`, `data-hit`,
`data-line`, then `data-action`) via `Element.closest()`:

```javascript
document.addEventListener("click", function(ev){
  var t = ev.target;
  var v = t.closest("[data-version]");
  if (v) { setVersion(v.getAttribute("data-version")); return; }
  var a = t.closest("[data-action]");
  if (!a) return;
  var action = a.getAttribute("data-action");
  if (action === "copy") { doCopy(false); return; }
  // ...
});
```

Adding a new clickable control means adding a `data-*` attribute to the markup
and a branch to the existing router -- never a second `addEventListener` call.
The same rule applies to generator field input (one shared `input`/`change`
listener, dispatching on `data-field`) and to the keyboard surface (one
`keydown` listener reading one table, `KEYMAP` -- see
`docs/ARCHITECTURE_BIBLE.md` Section 12).

---

## 4. Store Raw, Render Safe

**Mandatory.** Content is stored in the data island exactly as authored;
escaping happens only at the render call site, never before. The `esc()` calls
in this file are the *only* place HTML entities are introduced -- a curated
`content/commands.json` string never carries `&lt;` or `&amp;` pre-escaped,
because that would corrupt the plain-text evidence export and the search index,
both of which read the same raw field.

---

## 5. Air-Gap Rules

**Mandatory, mechanically enforced (Q2, and the file's own CSP meta tag).** No
`fetch()`, `XMLHttpRequest`, `WebSocket`, `sendBeacon`, or dynamic `import()`
anywhere in the app script; no external `<link>`/`<script src>`; no CDN literal
(`cdnjs`, `googleapis`, `unpkg`, `jsdelivr`, `gstatic`, or a bare `cdn.`
substring). The Content-Security-Policy meta tag
(`connect-src 'none'; object-src 'none'; form-action 'none'; ...`) makes this a
browser-enforced guarantee, not merely a code-review convention -- even a defect
that slipped past Q2 would still be blocked at request time by the CSP the
shipped file itself carries.

Q2 also closes the obvious workaround: a network-capable API reached by a
bracketed name, a name fused from string literals, or an alias assigned but
never called on the same line is caught the same way Q17 catches the equivalent
render-sink bypass. The shared residual (stated once, in
`docs/QA_GATES.md`, not repeated as a separate claim per gate): a name
constructed at *runtime* from something that is not a string literal is
invisible to a static scan. This is accident prevention for code
`CODEOWNERS` reviews before merge, not a sandbox against a determined author
with commit rights.

URLs in comments, string literals never executed, and internal anchors
(`#stig-panel`) are fine -- the rule is about what the running code *does*, not
what characters appear in the file.

---

## 6. Version and Build Identity

**Mandatory, mechanically enforced (Q1).** Five places must agree on the same
version string on every build: the HTML header comment, the `APP_VERSION`
constant, the embedded data island's `meta.version`, the `dist/` filename, and
`build.py`'s own `APP_VERSION` literal. `build.py` is the only place any of
these five is set -- never hand-edit a built file to "fix" a mismatched version;
if the five disagree, the build (not the artifact) is wrong, and Section 8 below
applies.

The identity block at the top of every built file:

```html
<!--
  Tool:               MD CODE RED -- RHEL Admin Toolkit
  Version:            v1.0.0-dev
  Last modified:      2026-09-17
  Classification:     UNCLASSIFIED
  Content fingerprint (SHA-256 of the data island): <sha256>
  Air-gap certified:  YES -- zero network calls, zero external assets, one file.
-->
```

`CONTENT_FINGERPRINT` is a sixth identity value with its own independent
cross-check: `build.py` computes it from the payload *before* substitution
(never a hash of a string containing itself) and `qa.py`'s Q1 gate re-hashes the
shipped island and compares. See `docs/ARCHITECTURE_BIBLE.md` Section 8.

---

## 7. Constants at Top Level

**Mandatory.** Identity and content-family constants live at the top of the
app-script IIFE, not buried inside a function -- `APP_NAME`, `APP_VERSION`,
`APP_BUILD_DATE`, `APP_CLASSIFICATION`, `CONTENT_FINGERPRINT`, `RHEL_VERSIONS`,
`ATTRIBUTION_BLOCK`, `UNVERIFIED_FLAG_COPY`. There is no `FEATURE_FLAGS` object
in this product -- every shipped feature is simply present in the code; there is
no runtime toggle for the Ansible/git generators because they do not exist yet
(`docs/ARCHITECTURE_BIBLE.md` Sections 13-14), not because a flag disables them.

---

## 8. Content Schema Validation

**Mandatory, mechanically enforced (`extract/schema.py`, imported by both
`build.py` and `tests/test_schema.py` so there is exactly one statement of what
a valid entry is).** The real minimum shape for a static command entry and a
generator entry are documented in full in `docs/ARCHITECTURE_BIBLE.md` Section
4 -- not restated here, and noticeably different from an earlier draft of this
document's example schema (no `optional[]`/`expectedOutput` fields; `verified`
is a per-version object, not a boolean; a generator entry has `fields[]`/
`template[]` instead of `rhel_versions`). Read Section 4, not memory of an
earlier draft.

---

## 9. Testing & QA Gates

**Mandatory.** The full local sequence before any commit is considered done:

```
git clean -fdx dist && python3 build.py
python3 qa.py
python3 -m unittest discover -s tests
node tests/hostile_harness.js
```

`git clean -fdx dist`, never `rm -rf dist`: `dist/` has carried tracked release
artifacts since v1.0.0-alpha.1 was tagged, and `build.py` does not regenerate
all of them, so `rm -rf dist` deletes committed files a rebuild will not
restore. `git clean -fdx dist` removes only what git does not track.

`docs/QA_GATES.md` is the authority on what each of the 22 gates proves, how it
has been watched fail, and what it explicitly does not cover -- read it, not a
summary of it. Two gates have scope worth knowing precisely, because it is
narrower or wider than it sounds: Q6's leak scan (`TODO`/`FIXME`/`XXX`/
`lorem ipsum`/`example.com`/`CHANGEME`) reads only the extracted app script
(`ctx["shell"]`) -- a `TODO` left in a companion doc does **not** fail Q6. Q21's
raw-character scan, by contrast, reads every file `git ls-files` reports --
all 271 tracked files in this build, documentation included, nothing excluded
-- so a raw invisible/bidi/zero-width character in a companion doc fails Q21
exactly like one in code would, even though a leftover `TODO` in the same file
would not fail anything. Companion docs should still carry neither: Q6's
narrower scope is not permission to leave a `TODO` in `docs/`, only a fact
worth knowing when deciding which gate would actually catch one.

---

## 10. Sources of Record, Never Patch `dist/`

**Mandatory, stated in `build.py`'s own header comment: "Built, never patched: if
this file is wrong, the source or the extractor is wrong."** `dist/*.html` is
git-ignored (a committed artifact embeds its own build date and cannot stay
byte-identical to a rebuild across days) and is never hand-edited, at any size,
for any reason. A defect in the shipped file is a defect in `content/`,
`template.html`, `build.py`, or an extractor -- fix the source, rebuild, and let
the QA sequence prove the fix. This applies equally to companion docs: this
guide is a source, `dist/` never carries documentation of its own to patch.

---

## 11. Fail-First Commits

**Practice, visible throughout the commit history rather than bot-enforced.**
A defect fix in this repo is conventionally committed as two steps: a test that
demonstrates the defect (shown red against the pre-fix code), then the fix
(shown green). `docs/QA_GATES.md`'s "Closed, and where the evidence is" table
and this repo's `README.md` Recent changes entries both cite specific commits
built this way. There is no gate that mechanically enforces two-commit
fail-first delivery -- it is a reviewed convention, and reviewers have held PRs
to it in this repo's history. Follow it for any defect fix; a single commit
that both introduces a regression test and the fix in one diff makes it
impossible for a reviewer to confirm the test would have caught the bug.

---

## 12. Branches, Never `main`

**Mandatory, and CODEOWNERS-backed for the paths that matter most.** Every
change lands on a branch and is reviewed before merge -- `CODEOWNERS` requires
review on every path (`*`), with `.forgejo/workflows/`, `stig-src/`,
`content/`, and `extract/` called out explicitly so the CI gate itself, the
pinned vendor sources, and the extractors cannot be edited around their own
review requirement. `.forgejo/workflows/ci.yml`'s own header states the same
rule for itself: a change to the CI gate needs the platform owner's review, so
the gate cannot be edited by whoever is trying to get past it. This document's
own authoring branch (`salm/sam/docs-alpha`) follows the same rule -- docs
never land on `main` directly either.

---

## 13. Model-Class Rule: A Change to the Assembler Is a Security-Review Change

**Practice, established by this repo's own history rather than a bot gate.**
Every change that has touched the code between the `MCR-ASSEMBLER-BEGIN` and
`MCR-ASSEMBLER-END` markers in `template.html` -- the pure command-assembly
block `tests/hostile_harness.js` and `qa.py`'s Q18 lift verbatim and fuzz -- has
gone through a named security review before merging, and several were returned
**DENY** or **APPROVE WITH CONDITIONS** rather than waved through (twelve
findings across MCR-SEC-001 through MCR-SEC-012 on the block's first review
alone; further conditions on later tranches, all tracked by ID in
`docs/QA_GATES.md`'s closed-findings table). This repo treats "touches the
assembler" as its own change class for exactly the reason the threat model
gives it top billing: it is the code standing between validated input and a
root shell on a STIG'd host. Treat any change inside those markers -- including
one that looks purely mechanical, like a new field type or a new flag-join rule
-- as requiring the same review weight, whether or not a CI job currently
enforces it. A change outside the markers (a renderer, the search index, the
evidence formatter) does not carry the same automatic weight, but any change
that adds a new sink, a new storage access, or a new network-adjacent surface
should be reviewed with the same posture Section 1's residual and Section 5's
CSP-backed guarantee assume it will be.

---

## 14. Language Target: ES5, One File, Two `<script>` Elements

**Mandatory, mechanically enforced (Q1 for the two-script count; the `JS` gate
for syntax).** The entire app is one `(function(){ "use strict"; ... })()` IIFE
-- `var`/`function` throughout, no `let`/`const`/arrow functions/template
literals/classes, because the deployment target is whatever browser happens to
be on an air-gapped jump box, which may be an old ESR-era Firefox. The shell
polyfills `NodeList.prototype.forEach` and `Element.prototype.matches`/
`closest` for exactly this reason -- do not assume a modern browser feature is
available without checking whether the shell already polyfills it, and if it
does not, add the polyfill rather than raising the minimum supported browser
silently. Exactly two `<script>` elements ship: the JSON data island
(`id="mcr-data"`) and the one app script. A third `<script>` element, or a
`type="module"` script, fails Q1.

---

## 15. ASCII-Only Source Files, Enforced Across the Whole Repository

**Mandatory, mechanically enforced (Q21).** `qa.py`'s Q21 gate walks every file
`git ls-files` reports -- all 271 tracked files in this build, source and
documentation alike, nothing excluded -- and refuses a raw control, bidi, or
zero-width character anywhere in any of them. The one allowance is a single
U+FEFF byte-order mark at byte offset 0, and only because
`stig-src/U_CCI_List.xml` (a pinned, hash-verified vendor file) carries one; a
BOM one byte later, or anywhere else, still fails. Curated prose (an `intent`
string, a companion doc) that needs an em dash or a curly quote writes a plain
hyphen (`--`) or a straight quote instead -- see this very sentence for the
convention in practice. This is stricter than "the shipped artifact is clean"
(which Q17's narrower character scan already covers) precisely so a hostile
character cannot enter the *repository* even in a file the build never touches.

---

## Violations

A gate failure (Q1-Q22, `JS`) blocks the build and, by the CI workflow's own
step order, everything after it -- QA gate, accuracy re-check, gitleaks, size
report, drift check, artifact upload never run on a build that failed earlier.
A practice violation without a gate behind it (fail-first commits, the
assembler's model-class review weight) is a review finding, not a build
failure -- raise it the way this repo's security and architecture reviews
already do, by name and by finding ID, not as an unstated expectation.
