# Schema fixtures (CR-T-06)

Each file here is a **complete content bundle** in the shape `build.py`'s
`load_content()` produces — `commands`, `tools`, `rules{7,8,9,10}`,
`flags{7,8,9,10}`, `cci_nist`, `expected_output` — small enough to read in one
screen and self-describing:

| Key | Meaning |
|---|---|
| `_case` | What this bundle is, in one sentence. |
| `_expect` | For an invalid bundle, the substring that must appear in one of the errors `extract/schema.py` returns. `null` for a valid bundle. |

`tests/test_schema.py` strips those two keys before validating, so they never
reach `extract/schema.py`.

`valid/` must produce **zero** errors. `invalid/` must produce **at least one**
error, and that error must be the one named in `_expect` — a fixture that fails
for the wrong reason is as useless as one that passes. Every invalid bundle
breaks exactly one rule; nothing else about it is wrong.

Adding a schema rule means adding a fixture here in the same commit. A rule with
no fixture has never been seen to fire.
