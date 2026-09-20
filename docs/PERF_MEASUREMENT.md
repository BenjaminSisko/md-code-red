# Reference corpus: the size measurement, and the ship decision

Owner: Milo Vance, Toolkit Systems Engineer
Measured: 2026-09-17
Ruling this answers: Al Kowalski — "lazy per-family, per-tier hydration becomes
mandatory at 5,000 corpus records, and the inverted search index must be in
place before the second family lands."

This tranche is **14,488 mined records across three families**, so both clocks
had already expired when the corpus was written. The measurement below is what
decided *how* to obey the ruling, not *whether*.

## Method

Built artifact, served over a local HTTP server (`python3 -m http.server`),
loaded in Chromium 152 on an Apple-silicon Mac (10 cores). Every number is a
median of repeated runs; parse timings are the median of 9–12 in-page
`JSON.parse()` calls on the island's own text; first contentful paint is read
from `PerformanceObserver`'s paint entries; heap is `performance.memory
.usedJSHeapSize` after load.

Three artifacts were measured:

| build | what it is |
|---|---|
| `base` | the tracked v1.0.0-alpha.1 release artifact — no corpus at all |
| `eager` | the whole corpus in the single `mcr-data` island (the stopped run's shape) |
| `lazy` | what ships: per-family islands plus a build-time inverted index |

## Numbers

| | base | eager | lazy (shipped) |
|---|---|---|---|
| artifact | 2.46 MB | 8.08 MB | 8.56 MB |
| bytes parsed at boot | 2.32 MB | 7.89 MB | **2.94 MB** |
| island `JSON.parse`, median | 4.2 ms | 10.7 ms | **4.2 ms** |
| DOMContentLoaded, median | 31 ms | 70 ms | **56 ms** |
| first contentful paint, median | 176 ms | 204 ms | **192 ms** |
| JS heap after load | 5–9 MB | 17–20 MB | **5.3 MB** |

Search, measured on the real UI path (typing into the palette and timing the
`input` handler, five runs per query, median and max):

| query | median | max |
|---|---|---|
| `a` (single letter) | 0.4 ms | 0.4 ms |
| `se`, `et` (two letters, very common) | 2.0–2.1 ms | 2.2–2.4 ms |
| `audit` | 1.9 ms | 5.5 ms |
| `config`, `pam`, `ssh`, `faillock`, `sshd_config` | 1.1–1.3 ms | 1.2–1.7 ms |
| `systemctl enable` (two terms) | 2.3 ms | 2.3 ms |

For comparison, the eager build's flat runtime index was 19,137 records and its
worst case was a 9.5 ms scan on a single letter that matched 16,061 of them.

Hydration, measured by clicking the family in the sidebar:

- DISA family (1,656 records, 0.51 MB): **4.1 ms**, heap 5.3 MB → 6.8 MB,
  including the re-render.
- A query for a STIG id hydrates **only** `mcr-ref-stig_rules`; the 4.1 MB Red
  Hat family stays unparsed. Asserted by `tests/test_reference_index.js`, which
  counts island reads rather than trusting a flag.

## The decision

**Ship the whole corpus (option a), with the inverted index and lazy per-family
hydration built.** Not option (b) — no family is staged out.

The reasoning, in order:

1. **The eager build already opened.** 10.7 ms of parse and 204 ms to paint is
   not a jump box refusing to open; it is not even close. Derate an order of
   magnitude for an old x86 laptop and it is ~110 ms of parse and ~2 s to paint.
   So "the corpus is too big to ship" was not true, and staging C2/C3 out would
   have been withholding 12,832 records the operator can use to solve a problem
   they cannot solve otherwise.
2. **But "it measures fine" is not the standard.** Al's ruling is about the
   architecture the *next* family lands into. C4 (the deferred ComplianceAsCode
   remediations, 482 scripts under a fourth licence class) is already named in
   the extractor's own `source_modules` as `deferred`. Landing it on an eager
   loader would repeat this measurement from a worse starting point.
3. **So both were built, and the whole corpus ships.** Boot now parses 2.94 MB —
   the pre-corpus figure — and the corpus costs nothing until an operator asks
   for it. The index makes query cost a function of the query rather than of the
   corpus, which is what has to be true before family four.

## What it cost

The artifact is **0.48 MB larger** than the eager build: the inverted index is
0.47 MB after delta-encoding its posting lists (0.78 MB before). That is the
honest trade — half a megabyte of index to stop parsing five megabytes of
records at boot, and to stop rebuilding a 19,000-entry scan index on the first
keystroke.

Two shapes were measured and rejected:

- **One island holding pre-serialised JSON strings.** Keeps "exactly two script
  elements" true, and costs **32.8% (1.6 MB)** to JSON-escape the inner
  documents. It also hides the families from qa.py, the harnesses and anyone
  reading the shipped file.
- **Raw (undelta'd) posting lists.** 0.78 MB instead of 0.47 MB, for four fewer
  lines of decode.

## What was NOT solved, and is stated rather than claimed away

Lazy hydration does not avoid the HTML tokeniser. In a single-file artifact the
whole 8.56 MB is still read and tokenised by the browser before any script runs,
and that — not `JSON.parse` — is most of the remaining DOMContentLoaded gap
between `base` (31 ms) and `lazy` (56 ms). There is no way around it that keeps
one file, and one file is the product.

Heap numbers move with garbage collection and should be read as a band, not a
point. The stable, repeatable claim is the one the test asserts: after boot, the
reference islands have been read **zero** times.
