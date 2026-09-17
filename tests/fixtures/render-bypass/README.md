# Render-sink bypass fixtures (MCR-SEC-004)

Each `bypass_*.js` here is a small, complete function that renders content text
into the DOM **without** the audited `esc()`-wrapped `innerHTML` path, and that
**passed** qa.py's Q17 audit on revision `4184ea8`. Marcus Reed found five of
them by driving `qa.py`'s own `read_assignment` / `expression_ok` / `segment_ok`
functions directly; the rest are the same families closed at the same time.

`tests/test_render_audit.py` feeds every file to `qa.render_sink_failures()` and
asserts:

| File prefix | Required verdict |
|---|---|
| `safe_control.js` | **zero** failures — the healthy case, checked first |
| `unsafe_control_*.js` | at least one failure — the case that always fired |
| `bypass_*.js` | at least one failure — the case that did not |

None of these constructs exists in `template.html`, and none is allowed to: the
product renders through one sink, through `esc()`/`escapeAttr()`, and Q17 is what
keeps that true for the next render path somebody writes.

Do not "fix" these files. A gate that has never been seen to fail is not a gate.
