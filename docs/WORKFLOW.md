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
