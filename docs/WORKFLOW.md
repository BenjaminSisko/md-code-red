# Content Pipeline & Refresh Workflow

## Source-to-Build Pipeline

Exact workflow for content review, assembly, and release.

### 1. Sources & Extraction

**TODO:** Define exact source documents (Red Hat docs URLs, DISA STIG release PDFs, man page URLs). Capture in a sources inventory spreadsheet.

Content originates from:
- Red Hat Enterprise Linux 7/8/9/10 documentation (portal.redhat.com)
- DISA STIG release PDFs and SCAP content
- Linux man pages (man-pages package)
- Ansible documentation (ansible-doc --json output)

### 2. Content JSON Schema

**TODO:** Finalize entry schema after SME review. Minimum fields:
- Tool name, RHEL versions supported
- Command template with required/optional parameters
- Flag-by-flag explanations
- STIG ID(s), NIST control(s), expected compliant output
- Source citation (URL/title, date verified, SME who verified)

### 2a. Content Validation Protocol — capture records and per-version `verified`

The full protocol (who runs what, on which host, under what safety rules) is
Riley Park's and Caleb Stone's company record, not a repo file:
`07_QA_Test/MD_CODE_RED/test-plan-skeleton-v1.md` Part B, §7-§11. This section
is a pointer into it plus the two rules that changed inside this repo.

- **Canonical capture path** (Eli Cross ruling, closing the CR-T-34 path
  mismatch): `tests/captures/<rhel_version>/<entry_id>.json`, one JSON file per
  entry per RHEL version, read by `extract/import_captures.py` and enforced by
  `qa.py`'s Q16 gate. This is the only storage location — the protocol
  document's own Appendix is a pointer to this path, not a second tree.
- **`verify_result` is a mandatory capture-record field**, not optional
  narrative. `extract/import_captures.py`'s `REQUIRED_FIELDS` and `qa.py`'s
  `CAPTURE_REQUIRED_FIELDS` both refuse a capture record missing it, alongside
  `command_hash_at_capture`. Riley Park's clarification (capture-review-run1-
  2026-09-18.md §7, protocol clarification request #1): the WRITTEN protocol
  document's §7 field table does not currently list either field explicitly,
  even though the code has gated on both since CR-T-34 — that is a documentation
  gap in the company-record file, not a difference in what is actually
  enforced. **Note for Riley/Caleb, not made here:** `test-plan-skeleton-v1.md`
  §7's table should add `command_hash_at_capture` and `verify_result`
  explicitly so a future SME reading only the written protocol does not
  under-scope what a capture record needs. That edit belongs to the
  company-record file and its own owners; this repo does not carry a copy of
  it to edit.
- **`verified` is per RHEL version, not per entry** (CEO ruling closing Riley
  Park's first capture review, capture-review-run1-2026-09-18.md RILEY-F1: a
  single whole-entry `verified` flag could not be set for any of the batch's 9
  entries without overclaiming a version nobody captured). `content/
  commands.json`'s `verified` field is an object keyed `"7"`/`"8"`/`"9"`/
  `"10"`, each value `false` or a `{by, on, host, capture}` receipt naming the
  QA reviewer, the date, the host, and the capture file that backs it. A
  version whose row is `unavailable` or a `same_as` pointer can never carry a
  receipt of its own — it was never independently run — and a `same_as`
  target's receipt never propagates onto the version pointing at it. See
  `extract/schema.py`'s `verified_errors()`/`resolved_command()` and `qa.py`'s
  `gate_q16()` for the enforced rules, and `tests/captures/README.md` for the
  end-to-end SME-captures/QA-verifies flow.

### 3. Content Review Board

**TODO:** Assign reviewer roles. Review gate MUST pass before build.

- RHEL SME: Validates command syntax and completeness
- ISSO: Validates STIG/NIST mappings and control relevance
- Tech Writer: Validates explanations are plain-English and accurate

### 4. Build Assembly

**TODO:** Document build tool (Node.js script, templating engine). Include BQP gate list.

Build script reads content JSON, template HTML, and generates single air-gap-clean HTML file.

### 5. QA Gate

**TODO:** Cross-reference with TEST_PLAN.md. Gate includes air-gap scan, syntax check, feature marker verification, data integrity spot-check.

### 6. Release & Distribution

**TODO:** Define distribution channels (file share, USB, email, NFS share).

---

## Quarterly STIG Refresh Cycle

Timed to DISA STIG release schedules.

### Timeline

**Week 1: STIG Release & Diff Analysis**
- TODO: Monitor DISA site for new STIG releases
- TODO: Extract new/changed check IDs
- TODO: Map changes to toolkit content

**Week 2: Content Updates**
- TODO: RHEL SME writes new command entries
- TODO: ISSO maps to NIST controls
- TODO: Tech Writer drafts explanations

**Week 3: Review & Build**
- TODO: Content Review Board validates all new entries
- TODO: Build new version
- TODO: QA gate verification

**Week 4: Release & Notify**
- TODO: Deploy to all enclaves
- TODO: Notify admins via email/Slack of what changed
- TODO: Update CHANGELOG

---

## File Organization (TBD)

```
docs/               (this folder)
content/
  rhel-commands/
    tools.json     (command entries by tool)
    stig-map.json  (STIG ID → command cross-reference)
  sources.json     (source citation inventory)
template.html      (UI template)
build.py           (assembly script)
qa.py              (QA validation gates)
```

**TODO:** Confirm folder structure with Zee (Engineering) after initial design review.
