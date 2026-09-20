---
type: security-review
status: current
last_verified: 2026-09-20
---

# Security Review -- v1.0.0-alpha.2

**Code revision reviewed:** `9d7d08a8fe50c10d3f87ca7ecbd4499aef05565a`

**Disposition:** APPROVE for lab-only unsigned alpha use.

The review covered command and pipeline assembly, operator selection, redirects,
`xargs`, nested interpreter refusal, DOM sinks, data-island escaping, offline
behavior, evidence export, provenance generation, corpus shape separation, and
anchor re-resolution.

Closed findings:

- **PIPE-003:** NUL mode is accepted only when the producer is exclusively
  NUL-delimited; mixed `find -print -o -print0` is refused.
- **PIPE-004:** `xargs -I` emits one replacement argument in a fixed child argv;
  oracle tests compare the exact structure.
- **PIPE-F1:** exact descriptor sinks are green while other `/dev/**` targets,
  including `/dev/zero`, remain red.
- **PF6:** `pipelineBlastBadge()` executes green, yellow, red, and unrated paths;
  an unknown value fails closed.
- **MCR-SEC-020:** the dated waiver is retired with evidence for
  `--add-rich-rule` on RHEL 8, 9, and 10. Q20 remains active as a regression
  ratchet over 70 tool/release pairs.
- **Release lineage:** provenance now hashes all five data islands in declaration
  order, closing the prior reference-island blind spot.

Residuals accepted for this alpha:

- Static scans cannot prove the behavior of a property name built entirely from
  runtime data. Q17 therefore remains an accident-prevention gate backed by code
  review rather than a sandbox claim.
- Mined reference commands are discovery content, not curated or host-verified.
  Q24 prevents them from taking curated fields or entering the assembler.
- The artifact is unsigned. Its SHA-256 and Git lineage prove integrity and
  reproducibility, not publisher identity.
- Receiving-host interactive browser acceptance remains required because the
  available automation provider blocked the local `file://` URL.
