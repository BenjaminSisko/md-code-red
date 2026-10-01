---
type: release-evidence
status: candidate
last_verified: 2026-09-30
---

# Security Review -- v1.0.0-alpha.6

The candidate preserves the offline single-file architecture, deny-network CSP,
closed generator grammars, output escaping, dangerous-pattern detection, and
explicit acknowledgement for red operations. Q2, Q17-Q19, Q21-Q26, the full
unit suite, the hostile-input harness, Gitleaks, and the rendered-browser
runtime audit passed against the final artifact.

This candidate adds or strengthens the following security properties:

- Fourteen formerly fixed examples are typed, validated generators. User values
  remain shell-quoted operands and cannot become operators or option seams.
- Pipeline inspection handles structural pipeline results before catalog-entry
  lookup, eliminating the null dereference while preserving stage-level source,
  flag, verification, and risk context.
- The hostile-input harness executes 128,449 checks over every generator field,
  multi-stage pipelines, redirect targets, file generators, quoting domains,
  and positive controls; zero failed.
- The final rendered-browser audit produced zero exceptions and zero console
  errors across 867 assertions.
- The standalone file artifact loaded zero network resources. Q2 found no
  external script, stylesheet, image, media, font, fetch, XHR, WebSocket,
  beacon, dynamic import, or CDN path.
- Gitleaks 8.30.1 scanned all 200 reachable commits and 97.90 MB using the
  repository policy; no leaks were found.

The candidate remains unsigned because no authorized publisher identity is
provisioned. SHA-256 detects changed bytes but does not authenticate a publisher.
RHEL host-verification coverage remains partial, mined reference records remain
separate and mostly unrated, and a structurally safe command or pipeline can
still be operationally inappropriate. These boundaries remain visible in the
interface and documentation.

Independent exact-head review is required after the candidate evidence commit.
Any subsequent source or artifact change invalidates that review.
