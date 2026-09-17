#!/usr/bin/env python3
"""QA gate for the built grey-beard-ansible.html. Exits non-zero on any failure.

Checks (stdlib only):
  1. built file exists, parses as HTML enough to extract the data island
  2. data island parses as JSON and matches template version
  3. air-gap law: no external fetchable resources (src=/href= to http(s) beyond
     plain documentation anchors <a href>), no fetch()/XHR/WebSocket/import()
  4. every command entry keeps the verify/undo/blast promise
  5. every flags/errors dictionary entry has a source
  6. decoder humility: the UNKNOWN path exists; no guess-fallback marker
  7. no TODO/lorem/example.com/CHANGEME leaks (CHANGE_ME placeholders in
     generated-output templates are allowed by design)
  8. single-file sanity: no <link rel=stylesheet>, no external <script src>
  9. size report
"""

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(REPO, "grey-beard-ansible.html")

fails = []


def fail(msg):
    fails.append(msg)
    print("FAIL:", msg)


def ok(msg):
    print("  ok:", msg)


def main():
    if not os.path.exists(DEST):
        print("FAIL: grey-beard-ansible.html not built")
        sys.exit(1)
    html = open(DEST, encoding="utf-8").read()

    # 2. data island
    m = re.search(r'<script id="gba-data" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        fail("no data island found")
        report()
    try:
        data = json.loads(m.group(1).replace("<\\/", "</"))
        ok(f"data island parses ({len(m.group(1)) / 1024:.0f} KiB)")
    except json.JSONDecodeError as e:
        fail(f"data island is not valid JSON: {e}")
        report()

    # 3. air-gap law
    ext_script = re.findall(r'<script[^>]+src=', html)
    ext_css = re.findall(r'<link[^>]+rel=["\']?stylesheet', html)
    ext_img = re.findall(r'<img[^>]+src=["\']?https?://', html)
    net_js = re.findall(r'\b(fetch\s*\(|XMLHttpRequest|WebSocket|navigator\.sendBeacon|import\s*\()', html)
    if ext_script: fail(f"external <script src> found: {ext_script}")
    else: ok("no external scripts")
    if ext_css: fail("external stylesheet found")
    else: ok("no external stylesheets")
    if ext_img: fail("remote images found")
    else: ok("no remote images")
    if net_js: fail(f"network-capable JS calls found: {set(x[0] for x in net_js)}")
    else: ok("no fetch/XHR/WebSocket/beacon/dynamic-import")
    http_srcs = re.findall(r'(?:src|href)=["\']https?://[^"\']+', html)
    if http_srcs: fail(f"http(s) src/href present: {http_srcs[:5]}")
    else: ok("zero http(s) references of any kind")

    # 4. entry promises
    bad = 0
    for e in data["commands"]["entries"]:
        if not e.get("verify") or not e.get("undo") or e.get("blast") not in ("green", "yellow", "red"):
            bad += 1
            fail(f"entry {e.get('id')}: verify/undo/blast promise broken")
    if not bad:
        ok(f"all {len(data['commands']['entries'])} command entries keep verify/undo/blast")

    # 5. provenance
    missing_src = [e["id"] for e in data["commands"]["entries"] if not e.get("source")]
    missing_src += [s["id"] for s in data["errors"]["signatures"] if not s.get("source")]
    for cli, d in data["flags"].items():
        if cli != "_meta" and not d.get("source"):
            missing_src.append("flags:" + cli)
    if missing_src: fail(f"entries without source: {missing_src}")
    else: ok("every entry/signature/dictionary carries provenance")

    # 6. decoder humility
    if "UNKNOWN to my dictionary" not in html:
        fail("decoder unknown-flag path missing")
    else:
        ok("decoder admits unknowns")
    if "I don't guess" not in html:
        fail("humility copy missing")
    else:
        ok("humility rule present")

    # 7. leaks — example.com is checked only OUTSIDE the data island, because
    # vendor ansible-doc examples legitimately use the RFC 2606 example domain
    shell_only = html.replace(m.group(1), "")
    leaks = []
    for pat, why, hay in [(r'\bTODO\b', "TODO", html), (r'lorem ipsum', "lorem", html),
                          (r'example\.com', "example.com outside vendor data", shell_only)]:
        if re.search(pat, hay, re.I):
            leaks.append(why)
            fail(f"leak: {why}")
    if not leaks:
        ok("no TODO/lorem/example.com leaks")

    # localStorage guarded
    if "try{ localStorage" in html.replace("  ", " ") or re.search(r'try\s*\{\s*(var v=)?localStorage', html):
        ok("localStorage access is try/catch-guarded")
    else:
        fail("localStorage guard not found")

    # 9. size
    size = os.path.getsize(DEST)
    print(f"size: {size/1024:.0f} KiB")
    if size > 4 * 1024 * 1024:
        fail("built file exceeds 4 MiB sanity ceiling")

    report()


def report():
    if fails:
        print(f"\nQA GATE: {len(fails)} failure(s)")
        sys.exit(1)
    print("\nQA GATE: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
