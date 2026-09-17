# Vendor ingestion provenance log

| Date | Source | Method | Feeds | Notes |
|---|---|---|---|---|
| 2026-08-23 | ansible-core 2.21.1 venv (`~/HomeLab/tools/ansible-venv`) | `extract_ansible_doc.py` — `ansible-doc --json` per module, `<cli> --help` parsed | `content/modules.json` (24 modules), `content/flags.json` (9 CLIs) | Regenerable; version recorded in `_meta.core_version`. Re-run with `ANSIBLE_VENV_BIN=<path>` against another core version. |
| 2026-08-23 | RHEL 9 man pages / Red Hat RHEL Security Hardening + Using SELinux guides (local PDFs, COMPASS tree) | manual curation, paraphrased | `content/rhel_flags.json`, RHEL entries in `content/commands.json` | Each entry carries its `source` field. No verbatim vendor passages. |
| 2026-08-23 | ansible-documentation concepts (config precedence, variable precedence, behavior of implicit localhost, pipelining, remote_tmp, become) | paraphrased into entries/trees/glossary | `commands.json`, `trees.json`, `glossary.json`, `errors.json`, precedence ladder in `template.html` | Upstream repo snapshot available on the Crucial X9 (`ANVIL-Corpus-Exports/.../ansible-source-docs/ansible-documentation`) for deeper future ingestion. |
| 2026-08-21 | Benny's control-node migration incident | first-hand | `scars.json` SCAR-001/002, drill d-hang, d-raw-vs-ping | The founding scars. |

Rules: paraphrase only; every emitted entry names its source; unknown = say unknown.
