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
