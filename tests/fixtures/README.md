# Test fixtures

- `hostile-inputs.json` — the hostile-input fixture for the command assembler (threat-model-v1 §11
  item 4 and §12 item 1, CI merge-gate #4). 52 adversarial vectors across 18 classes, plus a benign
  control value per field type. Each vector declares what the one free-text field type (`comment`)
  must do with it; every other field type is a closed grammar and must reject every vector, which is
  policy in the harness rather than per-row data so a new field type inherits it. Run by
  `tests/hostile_harness.js` (Node) from `tests/test_hostile_inputs.py` against `template.html` and
  from `qa.py` Q18 against the **built artifact**. Regenerating this file by hand is fine; changing a
  vector's expected outcome is a security decision and needs Marcus's review, not just a green run.
- `accuracy/clean_rules_rhel9.json` — the deterministic Q10 sample of `content/rules_rhel9.json`,
  byte-identical to the shipping dataset. The control case: `qa.accuracy_failures()` must report it
  clean against a live re-parse of the pinned RHEL 9 XCCDF. If this one ever fails, the mutated
  fixture failing proves nothing.
- `accuracy/mutated_rules_rhel9.json` — the same 20 rules with six planted edits, one per field the
  gate compares (title, rule id, CCI set, CAT, fix text past the 100-character prefix window, check
  text). `_meta.mutations` names each one, and `tests/test_accuracy_gate.py` asserts the gate reports
  every one of them by field and by STIG ID. A build of `qa.py` that calls this file clean has lost
  its accuracy gate, whatever the rest of its output says.
- `schema/` — valid and invalid content bundles for `tests/test_schema.py` (CR-T-06).
- `broken-content/` — defective bundles proving `build.py` refuses to assemble them.
- Capture files from the content validation protocol land under
  `tests/captures/<rhel_version>/<entry_id>.json` (test plan Part B §7).
