# Release archive

Published artifacts leave `dist/` when a newer release candidate is built so
the QA artifact selector can prove it is testing exactly one version. Historical
artifacts remain byte-for-byte under this directory and under their signed or
annotated Git tag and release entry.

| Version | Archive | Release lineage |
|---|---|---|
| v1.0.0-alpha.1 | `releases/v1.0.0-alpha.1/` | Tag `v1.0.0-alpha.1`; artifact, SHA-256 sidecar, and provenance manifest preserved unchanged |
| v1.0.0-alpha.2 | `releases/v1.0.0-alpha.2/` | Immutable tag `v1.0.0-alpha.2`; current published artifact, SHA-256 sidecar, and post-tag-stamped provenance manifest preserved byte-for-byte from `main` |
| v1.0.0-alpha.3 | `releases/v1.0.0-alpha.3/` | Immutable tag `v1.0.0-alpha.3`; released artifact, SHA-256 sidecar, and provenance manifest preserved byte-for-byte before alpha.4 feature development |
