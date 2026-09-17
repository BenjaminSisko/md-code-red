# Architecture Bible — MD CODE RED

Comprehensive system design document. All sections TODO until after initial design review.

---

## 1. Executive Summary

**TODO:** One-page overview of system goals, key design decisions, and release targets.

---

## 2. System Architecture

**TODO:** High-level diagram (or ASCII) showing: content sources → extraction → JSON schema → build script → single HTML file → browser UI → localStorage state.

---

## 3. File-by-File Breakdown

**TODO:** Document each source file (content/*.json, template.html, build.py, qa.py), its purpose, format, and size limits.

---

## 4. Data Models

**TODO:** Full schema definitions for: command entries, STIG/control mappings, source citations, version metadata.

---

## 5. Command Builder Engine

**TODO:** How guided forms assemble commands from templates, validate required fields, and render live output.

---

## 6. STIG/NIST Tagging System

**TODO:** Cross-reference schema linking commands to DISA STIG IDs, NIST 800-53 controls, and expected compliant output.

---

## 7. Visualization & Rendering

**TODO:** DOM structure for command display, explanation panel, STIG badge, dangerous-operation warning, and print view.

---

## 8. Export as Evidence

**TODO:** How SCTM-ready output is formatted, what fields it contains, and how copy-to-clipboard works without server.

---

## 9. Search & Indexing

**TODO:** Full-text search implementation (static index vs. runtime trie) across tools, flags, STIG IDs, and source URLs.

---

## 10. Version Management

**TODO:** How version-specific flags are shown/hidden, greyed tooltips for unavailable RHEL versions, and metadata display.

---

## 11. Browser State Management

**TODO:** localStorage schema for favorites, recent commands, print settings, dark/light mode preference.

---

## 12. Keyboard & Accessibility

**TODO:** Keyboard shortcuts, no-mouse operation path, screen reader tagging, and high-contrast mode support.

---

## 13. Ansible Generators

**TODO:** Playbook, inventory, and ansible.cfg builders; template structures; validation before copy.

---

## 14. Git Command Generator

**TODO:** Guided builder for clone, branch, merge, rebase, tag, log, bisect recovery scenarios; validation and safety checks.

---

## 15. Event System & Form Handling

**TODO:** Event delegation, form validation, input sanitization, and change propagation to preview panels.

---

## 16. Feature Specs & User Journeys

**TODO:** Detailed specs for each of the three core journeys (command, evidence, playbook) with wireframes or prototypes.

---

## 17. Algorithms & Logic

**TODO:** Sort orders (tool alphabetical, RHEL version priority, frequency), search ranking, and dangerous-operation detection.

---

## 18. Error Handling & Logging

**TODO:** What errors can occur (missing fields, unsupported version), user-facing messages, console logging for debugging.

---

## 19. Performance & Limits

**TODO:** File size target (<X MB), load time target (< X sec on offline jump box), search response time, localStorage quota.

---

## 20. Security & Input Validation

**TODO:** Input validation at every form boundary, output encoding (esc() functions), no inline event handlers, XSS/injection prevention.

---

## 21. Design Patterns & Code Structure

**TODO:** Module architecture, function naming conventions, CSS organization, and template reuse patterns.

---

## 22. External Dependencies & Vendor Code

**TODO:** List any embedded libraries (highlight: none for air-gap goal), how they're vendored, version pins.

---

## 23. Hidden Assumptions & Gotchas

**TODO:** Assumptions about user environment (RHEL only, Firefox/Chromium only, localhost file:// only, no screen readers assumed — list and justify).

---

## 24. Rebuild & Modernization Path

**TODO:** How to upgrade to a new RHEL version, add new tools, support a web version, or refactor the build pipeline without breaking content.

---

## 25. Glossary

**TODO:** Shared terms (CAT I/II, SCTM, body of evidence, STIG compliance, RHEL SRG, jump box, air-gapped network, control mapping).

---

## Appendix: Known Unknowns

- **Build tool choice:** Node.js script vs. Python build.py (see WORKFLOW.md)
- **Content versioning:** Store STIG release date in metadata or filename?
- **Multi-language support:** English only for v1.0.0; i18n path TBD
- **Mobile support:** RHEL jump boxes are desktop-only; mobile UI out of scope for now
- **Cloud/satellite integration:** Offline-only for v1.0.0; SaaS connector roadmap TBD

**TODO:** Resolve unknowns during design review (Week 1 of Phase 1).
