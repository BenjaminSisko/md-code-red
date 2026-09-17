# Raw source dumps (provenance record, never embedded)

`rhel<N>/<tool>.man.txt` and `.help.txt` are verbatim captures of `man -P cat <tool>` and `<tool> --help`
from a real host of that RHEL version (host, release, kernel and package NVRA are recorded in
`content/flags_rhel<N>.json._meta`). They exist so that:

- `extract/extract_flags.py --check` and `qa.py` Q15 can re-parse them offline and prove the flag
  dictionaries were generated, not hand-edited;
- `qa.py` Q14 can prove no verbatim text from these paraphrase-only sources reaches the artifact.

Licensing: man page text is GPL-2.0-or-later (and per-package licenses); it is reference material
held in this repository and is **never embedded** in the built artifact (content licensing ruling v1,
2026-09-17). Curated `explain` text is authored separately, paraphrased, and cited.
