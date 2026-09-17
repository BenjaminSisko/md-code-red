# Deliberately broken content fixtures

Each file here is a complete, syntactically valid `commands.json` that violates exactly one
rule `build.py`'s `validate()` is supposed to catch. `tests/test_build_fails_on_broken.py`
copies the real `content/` into a scratch tree, overlays one of these files, runs `build.py`
there, and asserts the build **fails** with the matching message.

A gate that has never been seen to fail is not a gate. Do not "fix" these files.

| File | The one thing wrong with it |
|---|---|
| `commands_missing_rhel_key.json` | `rhel_versions` omits `"7"` — all four keys are mandatory, "not available" is a value, never an absence |
| `commands_dangling_stig.json` | cites `RHEL-09-999999`, which resolves to no record in `rules_rhel9.json` |
| `commands_missing_provenance.json` | `source` has no `url_or_man`, `retrieved_on`, or `license_class` |
| `commands_verified_without_receipt.json` | `verified` is set with a `by` but no `on` or `host` — a verification claim with no capture receipt |
| `commands_unavailable_empty_reason.json` | `{unavailable: {reason: ""}}` — the UI would render a disabled control with nothing to say |
| `commands_same_as_cycle.json` | `same_as` points 7 → 8 → 7, a cycle the assembler must refuse rather than loop on |
| `commands_multiline_intent.json` | `intent` carries a CRLF — it renders as one `<h2>` on screen and pastes as two lines into a root shell, the second never displayed (MCR-SEC-003) |
| `commands_spec_flag_injection.json` | a generator spec's `template[].flag` carries `; rm -rf /etc; #` — flag tokens reach the command line unquoted (MCR-SEC-006) |
| `commands_spec_lit_injection.json` | a generator spec's `template[].lit` is a whole second command (MCR-SEC-006) |
