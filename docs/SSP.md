# System Security Plan (SSP) -- MD CODE RED

**Status:** In Draft
**Owner:** Noor Patel (ISSO / security engineer, content) with Alex Okafor
(Compliance Officer, control and evidence mapping)
**Last Updated:** 2026-09-17

This document outlines the security controls, risk posture, and compliance
baseline for MD CODE RED. It stays a pointer/stub document owned by Noor
Patel and Alex Okafor -- this pass (Sam Kim, technical writer) fills in only
what is directly checkable from the running system and its gates, and leaves
the control-assessment work itself to its owners.

---

## 1. System Overview

MD CODE RED is a single-file, offline HTML application: one `.html` file, no
server, no database, no network dependency of any kind, opened directly by a
browser (`file://` or a network share) on a RHEL or Windows jump box. It
generates RHEL 7/8/9/10 administration commands, DISA STIG/NIST SP 800-53
crosswalks, and plain-text SCTM-ready evidence exports. All state (favorites,
recent, theme, RHEL version choice) lives in the browser's own
`localStorage`/`sessionStorage`, scoped to that browser profile, and never
leaves it. See `docs/ARCHITECTURE_BIBLE.md` Section 1 for the full technical
summary.

## 2. System Boundary

**In scope:** the single HTML artifact (`dist/md-code-red_<version>.html`) and
the browser process that renders it. Nothing else executes.

**Out of scope, by design:** any network, any server, any database, any
credential store, any file the browser does not itself write (the app never
writes a file to disk -- clipboard and in-browser storage only). The file's own
Content-Security-Policy meta tag (`connect-src 'none'`, `object-src 'none'`,
`form-action 'none'`, `base-uri 'none'`) enforces the network half of this
boundary at the browser level, not merely by omission -- see
`docs/CODE_STANDARDS.md` Section 5.

**Build-time boundary (separate from the runtime boundary above):** the build
pipeline (`build.py`, `extract/`, `content/`, `content-src/`) executes on a
developer or CI host with read access to pinned vendor sources and, for the
flag extractors, read-only SSH access to lab hosts. None of that access, or
those hosts' identities beyond what is cited as provenance, ships in the
artifact.

## 3. Information Types & Classification

| Type | Classification | Notes |
|---|---|---|
| Command entries, flag dictionaries, tool metadata | Unclassified | Derived from public vendor documentation and man pages; see `NOTICE`. |
| DISA STIG rule text, CCI/NIST mappings | Unclassified, public domain (U.S. Government work) | Embedded verbatim, attributed by release -- `NOTICE`. |
| Captured command output (`tests/captures/`, `content/expected_output.json`) | Unclassified | The content validation protocol requires secrets to be redacted from captured `stdout`/`stderr` before a record is committed (`docs/WORKFLOW.md` Section 2a); this repo's own standing rule is that secrets never go in the vault, tickets, logs, or chat, and captures are held to the same bar. |
| User form input at runtime (field values typed into a guided form) | Unclassified, ephemeral | Never transmitted; held only in page memory (`STATE.formValues`) and, for favorites/recent, as **ID references only** in `localStorage` -- never the typed values themselves (`docs/ARCHITECTURE_BIBLE.md` Section 11). |
| Evidence exports | Depends on the destination package | The export itself carries only what the entry/rule/capture content already carries -- unclassified in this repo's content, but an ISSM assembling an SCTM/ATO package decides its own package classification; this tool does not classify content on its behalf. |

## 4. Security Requirements (NIST 800-53)

**Not yet formally mapped in this repo.** No control-by-control implementation
narrative exists here. What *is* directly checkable, mapped informally against
the controls `docs/IDEAS.md`'s original concept brief already named as relevant
(CM-6, CM-7, AC-2, AC-17, AU-2, AU-12, SC-7, SI-2):

- **CM-6/CM-7 (Configuration Settings / Least Functionality):** the content
  schema (`extract/schema.py`) and 22 QA gates constrain what can ship; the
  build fails loud on a schema violation rather than shipping a partial or
  malformed configuration (`docs/ARCHITECTURE_BIBLE.md` Section 18's
  never-half-formed rule).
- **AC-17 (Remote Access):** not applicable -- the tool has no remote access
  surface; it is a local, offline artifact.
- **SC-7 (Boundary Protection):** enforced by the CSP meta tag and Q2's static
  scan (Section 2 above), not by a network device this tool depends on.
- **SI-2 (Flaw Remediation):** the fail-first commit practice and the 22-gate
  regression suite (`docs/CODE_STANDARDS.md` Sections 9/11) are the mechanism;
  there is no formal patch/advisory process documented for this tool
  specifically.
- **AC-2, AU-2, AU-12:** not applicable to the runtime (no accounts, no
  runtime audit logging -- there is nothing to log to, by design). These may
  still apply to the **build/CI environment**, which is out of this
  document's current scope (Noor/Alex to determine).

A full control-by-control SSP narrative against the complete NIST SP 800-53
Rev 5 baseline selected for this system's authorization boundary is Alex
Okafor's work, not something this pass can complete from the code alone.

## 5. System Architecture & Security Controls

Pointer, not a restatement: `docs/ARCHITECTURE_BIBLE.md` Section 20 (Security &
Input Validation) and `docs/CODE_STANDARDS.md` in full are the technical
controls -- input validation via closed field-type grammars, output encoding at
every render sink (mechanically proven two ways, Q17 and Q19), air-gap
enforcement (CSP + Q2), and guarded, schema-versioned, try/catch-wrapped
`localStorage`/`sessionStorage` access that degrades to "nothing persisted"
rather than erroring. The stated residual, in one place rather than restated
per control: a property or API name assembled at *runtime* from something that
is not a string literal is invisible to the static gates -- this is
accident-prevention for code under `CODEOWNERS` review, not a defense against
an author with commit rights and hostile intent, and was never represented as
one.

## 6. Incident Response Plan

**Not yet drafted.** No documented process exists for: reporting a security
finding against this tool, updating a STIG entry found to be incorrect after
release, or a command-replacement SOP if a shipped command is later found
unsafe. Given the tool ships no telemetry and has no update channel (README's
"how to open" is "double-click the file" -- there is no auto-update), an
incorrect command in a shipped `.html` file already in an enclave has no
remote remediation path; this makes an incident response plan for this tool
specifically about **notification and re-distribution**, not patching in
place. Alex Okafor to draft.

## 7. Configuration Management (CM)

What exists and is checkable: version control (Forgejo, `orbit/md-code-red`),
build gates (`docs/QA_GATES.md`), branch protection via `CODEOWNERS` on
`.forgejo/workflows/`, `stig-src/`, `content/`, and `extract/`
(`docs/CODE_STANDARDS.md` Section 12), and a reproducible-build check in CI
(two builds of the same sources must be byte-identical). **Not yet defined:** a
formal content review board with named seats beyond the SME/QA roles
`content-src/roster.json` already enforces mechanically (`docs/WORKFLOW.md`
Section 3), and a release process (`docs/WORKFLOW.md` Section 6 states this
gap plainly rather than asserting a channel that does not exist).

## 8. Contingency & Disaster Recovery

**Not yet drafted.** The content JSON under `content/` is version-controlled
(Forgejo is the recovery path for a corrupted or lost checkout); there is no
documented fallback procedure for an operator whose shipped `.html` file is
corrupted mid-enclave (re-obtain from the distribution channel, once one is
defined per `docs/WORKFLOW.md` Section 6) or for falling back to raw vendor
documentation if the toolkit is unavailable. Alex Okafor to draft.

## 9. Compliance Assessment Summary

**Not yet performed.** No formal security review sign-off covering the whole
system exists as a single event this document can cite; what exists is a
series of named, scoped reviews (Marcus Reed's assembler/panels/generator
reviews, tracked by MCR-SEC finding ID in `docs/QA_GATES.md`'s closed-findings
table, and Al Kowalski's BQP Gate 3 review of `qa.py` itself, tracked as
AL-GATE3-* findings) each closed with specific code changes, not a single
umbrella "APPROVED" event. Noor Patel to determine whether that pattern
constitutes sufficient compliance assessment evidence or whether a
consolidated review is still required before authorization.

---

## Appendix: Crosswalk to RMF Controls

**Not yet mapped.** Benny to confirm scope (Section 4 above lists what this
pass could infer informally; a formal RMF crosswalk is separate work).

---

**Contact:** Noor Patel, Alex Okafor (via Dani Mercer, XO)
