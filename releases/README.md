# Release archive

Published artifacts leave `dist/` when a newer release candidate is built so
the QA artifact selector can prove it is testing exactly one version. Historical
artifacts remain byte-for-byte under this directory and under their signed or
annotated Git tag and release entry.

| Version | Archive | Release lineage |
|---|---|---|
| v1.0.0-alpha.1 | `releases/v1.0.0-alpha.1/` | Tag `v1.0.0-alpha.1`; artifact, SHA-256 sidecar, and provenance manifest preserved unchanged |
| v1.0.0-alpha.2 | Current candidate in `dist/` | Build date 2026-09-20; Q1-Q25 and JS required before tag |
