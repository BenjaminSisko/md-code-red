# Ideas & Backlog

Every idea in this file carries a timestamp, title, description, status, and control relevance. Entries feed into the roadmap and quarterly planning.

**Entry Format:**
```
## [ID: YYMMDD-N]

**Date:** 2026-MM-DD | **Title:** [Feature or decision title]
**Status:** Proposed | Approved | In Design | In Build | Shipped | Deferred
**Iteration:** [Roadmap phase or milestone] | **Effort:** [Low | Medium | High]
**Controls relevance:** [NIST 800-53 controls or "N/A"]
**Description:** [One paragraph explaining the idea]
**Decision log:** [Dates, who decided, why — fill as proposal progresses]
```

---

## [ID: 260917-001]

**Date:** 2026-09-17 | **Title:** Concept Brief — RHEL Admin Toolkit for air-gapped admins
**Status:** Approved
**Iteration:** Blueprint (Stage 01) | **Effort:** N/A
**Controls relevance:** CM-6, CM-7, AC-2, AC-17, AU-2, AU-12, SC-7, SI-2
**Description:** Single-file, offline HTML toolkit generating version-correct Linux commands, Ansible playbooks, and STIG evidence from vendor sources. Reduces time-to-evidence for STIG/RMF packages and escalations from junior to senior admins. Founder's one-pager, filed 2026-09-17 per Frame_RHEL_Admin_Toolkit_2026-09-17.md.
**Decision log:**
- 2026-09-17: Founder (Benny) filed concept brief. Status: Proposed.
- 2026-09-17: Eli Cross (CEO) accepted for Stage 01 Spark and assigned to Zee (Engineering).

---

## [ID: 260917-002]

**Date:** 2026-09-17 | **Title:** Git Command Generator (P1 backlog)
**Status:** Proposed
**Iteration:** Phase 2 (Weeks 7–12) | **Effort:** Medium
**Controls relevance:** N/A
**Description:** Guided builder for clone, branch, merge, rebase, tag, log, bisect, and recovery scenarios. Helps junior admins and automation engineers avoid common git mistakes in isolated repos. Feeds into Phase 2 roadmap pending Phase 1 pilot feedback.
**Decision log:** None yet.

---

## [ID: 260917-003]

**Date:** 2026-09-17 | **Title:** Ansible Playbook, Inventory, and Config Generators (P1 backlog)
**Status:** Proposed
**Iteration:** Phase 2 (Weeks 7–12) | **Effort:** High
**Controls relevance:** CM-6, CM-7, AC-17
**Description:** Answer-driven builders: user selects target group and tasks (checkboxes), generator produces valid YAML playbooks, inventories, and ansible.cfg files with commented options. Enables junior admins to automate without learning YAML from scratch.
**Decision log:** None yet.

---

## [ID: 260917-004]

**Date:** 2026-09-17 | **Title:** Config file generators: sshd, chrony, rsyslog, sudoers, systemd, cron (P2 backlog)
**Status:** Proposed
**Iteration:** Phase 3 (Weeks 13–20) | **Effort:** Medium
**Controls relevance:** AC-17, AU-2, AU-12, SC-7
**Description:** Form-driven generators for common hardening and compliance configs. Each output includes source citations (Red Hat docs, STIG), flags explained, and NIST control mappings. Reduces time to build compliant configurations.
**Decision log:** None yet.

---

## [ID: 260917-005]

**Date:** 2026-09-17 | **Title:** Per-tool syntax oracle, generalized from the golden-command table
**Status:** Proposed
**Iteration:** Not yet scheduled | **Effort:** Medium
**Controls relevance:** N/A
**Description:** `tests/fixtures/golden-commands.json` is a hand-authored VALIDITY
oracle -- the exact command every generator must emit, per release -- added
after MCR-SEC-021/MCR-SEC-015 (condition E1/E6) exposed that the hostile-input
harness proved only containment (every value stays inside one quoted shell
token) and never validity (the benign command is a correct invocation of its
tool). It closed the gap it was built for, but it is a per-generator table that
grows by one hand-typed row every time a 25th generator ships, and it says
nothing about the 3 static entries or about a future non-generator addition.
Proposed: extract the getopt(3) join/argument rules `optionSyntaxErrors()`
already encodes (long options take `=`, short options take a space, never
`-X=value`) into a reusable, per-tool grammar description -- a small table
naming each tool's own option shapes once -- so a new generator or static
entry gets syntax-validity checking derived from its tool's own grammar rather
than requiring a second hand-authored oracle row before it can ship. Raised as
a natural next step from the golden-command table's own docstring, which
already states it exists because "a table regenerated from the code it tests
is a transcript, not an oracle" -- the same principle argues for deriving
syntax rules from tool grammar rather than re-authoring them per generator.
**Decision log:** None yet.

---

## [ID: 260917-006]

**Date:** 2026-09-17 | **Title:** Split `qa.py` into a gates package
**Status:** Proposed
**Iteration:** Not yet scheduled | **Effort:** Medium
**Controls relevance:** N/A
**Description:** `qa.py` is a single ~56 KB file implementing all 22 gates plus
shared helpers (brace masking, trojan-character scanning, provenance checks).
Al Kowalski's BQP Gate 3 review of this file found six real defects, several
caused or worsened by the file's size and the ease of one gate's helper
silently drifting from another's copy of the same rule (AL-GATE3-003's brace
desync, AL-GATE3-005's provenance-field-list drift). `docs/QA_GATES.md`'s own
"Stale items in ADR-001" section already flags that the gate count has grown
past what an earlier design document assumed. Proposed: split `qa.py` into a
small package -- one module per gate or per closely related group of gates,
shared helpers (`mask_js_literals()`, `TROJAN_RANGES`, `PROVENANCE_FIELDS`
readers) in a common module imported once -- so a change to one gate cannot
silently reach into another's assumptions the way the brace-counting and
provenance-list defects did. `qa.py` itself would become a thin runner that
imports and sequences the gate modules, preserving the single `python3 qa.py`
entry point and the Q1-Q22 PASS/FAIL output format. This is a maintainability
proposal, not a behavior change -- every gate's proof, negative control, and
residual should be identical after the split; `docs/QA_GATES.md` would not
need to change except to note the new file layout.
**Decision log:** None yet.

---

## [ID: 260917-007]

**Date:** 2026-09-17 | **Title:** An ELS-entitled RHEL 7 host to replace the UBI7 container stand-in
**Status:** Proposed
**Iteration:** Not yet scheduled | **Effort:** Medium
**Controls relevance:** CM-6, CM-7
**Description:** `content/flags_rhel7.json` is extracted from a rootless UBI7
container on saratoga standing in for a RHEL 7 host, because the lab has none.
The container's own `_meta.kernel_caveat` says plainly that kernel- and
systemd-manager-dependent behavior was never observed, only each tool's own
`--help` text as shipped in the container's public repos -- and UBI7's public
repos ship neither `man`/`man-db` at all nor most of the packages this
product's 19-tool catalog needs (`firewalld`, `NetworkManager`, `lvm2`,
`audit`, `rsyslog`, `chrony`, `policycoreutils-python`, `openssh-server`, `git`
are all `available: false` for exactly this reason), so only 6 of the 19 tools
have any RHEL 7 flag coverage at all. Red Hat's Extended Life Cycle Support
(ELS) program keeps RHEL 7 entitled and patchable past its normal end of full
support, which would give this project a real RHEL 7 host or VM -- full
package repos, real `man` pages, real systemd/kernel behavior -- to extract
from and to run SME captures against, the same way `defiant` (RHEL 8) and
`saratoga` (RHEL 10) are used today. Directly closes `docs/POAM.md`'s
POAM-CONTENT-002. Weigh against RHEL 7's STIG being DISA's stated terminal
release (`docs/WORKFLOW.md`, "The RHEL 7 frozen source") -- an ELS host raises
content *coverage* for RHEL 7, it does not change that RHEL 7's compliance
ceiling is fixed regardless.
**Decision log:** None yet.

---

## [ID: 260917-008]

**Date:** 2026-09-17 | **Title:** A second active RHEL SME to spread the capture workload
**Status:** Proposed
**Iteration:** Not yet scheduled | **Effort:** Low
**Controls relevance:** N/A
**Description:** `content-src/roster.json` names two people with the `SME` role
(Caleb Stone, Renata Osei) and one with `QA` (Riley Park), and `qa.py`'s Q16
two-person rule requires a receipt's SME and QA names to differ and both
resolve against this closed roster. In practice, every capture run and content
fix in this repo's history is attributed to Caleb Stone or Milo Vance
(engineering) -- Renata Osei is on the roster but has not visibly run a
capture campaign yet. This is a bus-factor and throughput risk, not a gate
defect: RHEL 9's empty flag dictionary and the RHEL 7 coverage gap
(`docs/POAM.md` POAM-CONTENT-001/002) both sit behind one person's available
time. Proposed: formally staff Renata Osei onto an active capture campaign (or
recruit a third SME) so RHEL 9/RHEL 7 content work can run in parallel with
Caleb Stone's other assignments rather than serializing behind him. Low effort
because the roster mechanism this needs already exists and is enforced -- this
is a staffing decision, not a code or schema change.
**Decision log:** None yet.
