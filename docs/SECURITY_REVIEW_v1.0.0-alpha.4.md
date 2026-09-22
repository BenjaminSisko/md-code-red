---
type: security-review
status: candidate
last_verified: 2026-09-22
---

# Security Review -- v1.0.0-alpha.4

**Current-main base:** `3f3b2c36ceb45b5f04865e10af92c469ea675d25`

**Disposition:** PASS for automated security controls and READY FOR independent
exact-head security review as a lab-only unsigned candidate. This disposition
does not authorize or claim tagging, publication, deployment, browser
acceptance, or pilot acceptance.

## Security-relevant scope

- Closed grammars were added for Git references and revisions, cron hour and
  minute fields, and token-line configuration documents.
- Six configuration generators produce reviewable files. Their emitted command
  either validates the generated file or, for cron, performs the explicitly
  disclosed replacement action.
- The hostile harness independently parses generated YAML, INI, and token-line
  files and compares recovered values and line structure with operator intent.
- Q26 adds a source-cited per-tool grammar for binary, subcommand, option,
  option-argument, join, and operand structure. It covers static commands and
  applicable golden generator commands without replacing the golden oracle.
- Provenance review pointers are now derived from the current version and do
  not claim that a historical release review approved alpha.4.
- The POA&M was reconciled to distinguish retired findings from active gaps and
  to avoid presenting implemented RHEL 9 extraction or input validation as
  missing work.

## Automated security evidence

- Q2 air-gap law PASS: no external assets or network API path.
- Q17 render-sink audit PASS.
- Q18 command and generated-document assembly PASS: 121,873 hostile-input
  checks, 0 failures; 119,801 hostile values rejected and 2,072 accepted only
  under the tested quoting constraints.
- Q18 parsed and compared 320 YAML, 72 INI, and 44 token-line documents.
- Q19 escaper behavior PASS.
- Q21 raw control, bidirectional, and zero-width scan PASS across 362 tracked
  files.
- Q24 reference/curated shape separation PASS.
- Q25 re-resolved all 23,447 stored citations.
- Q26 checked 620 static commands and 169 applicable golden generator commands
  as 865 simple invocations against 420 independently loaded release-specific
  grammar rows; 221 forms have explicit operand bounds. Eight invalid-command,
  one quoted-operator, and five unmodeled-shell controls were rejected.
- The repository-configured Gitleaks scan reported no leaks before the
  candidate commit, and the superseded first candidate also passed at exact
  head. The replacement exact-head reviewer must repeat the scan.
- `git diff --check` is clean.

## Integrity assessment

The candidate HTML SHA-256 is
`cb2763dc7927aeee23773abc6872fa4e1e3e87f6df39b9075d9791d72231c4ee` and
the ordered five-island fingerprint is
`d11292cc1df80a3689a568e53558427f6fcb7df656ac963f4f7b19fc73eead3e`.
Two clean cycles reproduced the HTML, sidecar, and placeholder provenance
manifest byte for byte. The placeholder is deliberate because the final merge
or tag target does not exist yet; it must be replaced only after exact-head
review and merge.

## Residuals and limits

- The artifact remains unsigned. SHA-256 and Git lineage provide integrity and
  reproducibility evidence, not publisher identity.
- The new command syntax oracle establishes structural conformance to declared
  tool grammars. It does not prove that a syntactically valid command is the
  correct operational choice for a particular system.
- Q26 checks that all 420 grammar rows declare an authority label and syntax
  anchor. It existence-checks 69 repository capture paths; the remaining 351
  external/manual labels are documentary citations and are not mechanically
  re-resolved by this gate.
- Generated configuration files are reviewable artifacts. Validation commands
  do not install most generated files; `crontab cron.generated` does replace
  the current user's crontab and is rated and documented accordingly.
- Static gates do not replace a receiving-host browser walkthrough or live
  zero-network observation.
- No exact-head independent human review has been recorded for alpha.4. Any
  content change after such a review requires a fresh disposition and rebuild.
