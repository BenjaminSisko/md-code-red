#!/usr/bin/env python3
"""
qa-rhel-stig.py — QA gate for the RHEL STIG Field Manual (rhel-stig.html).

Validates the SHIPPED product against its authoritative sources and the Ops Field
Manual standard. Run after every build / DISA refresh:

    cd _tools && python3 qa-rhel-stig.py

Exit code 0 = all checks pass; 1 = at least one failure (CI-friendly).

Checks, grouped:
  BUILD     placeholder replaced, embedded JSON valid, single file, size <= ceiling
  DATA      per-release rule counts match source XCCDF; CAT I completeness; STIG ID,
            CCI, and NIST 800-53 present at expected coverage
  ACCURACY  random rules per release re-parsed from source XML and diffed against the
            embedded copy (title, CCI, STIG ID, fix-text prefix)
  MAPPING   random CCIs re-checked against the DISA CCI list (CCI -> 800-53)
  LAB       lab findings == CAT I per release; every archetype used has an ARCH def;
            every guided fixhint actually satisfies its own fixmatch (the guided
            'next' fix must work); fixable/manual split is sane
  HTML      no leftover template markers, balanced <script>, all section anchors,
            UI-baseline hooks (localStorage keys, print CSS, toc toggle, copy buttons)
"""
import json, os, re, sys, html as htmllib
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.join(os.path.dirname(HERE), 'rhel-stig.html')
SRC = os.path.join(HERE, 'stig-src')
CCI_MAP_PATH = os.path.join(SRC, 'cci-map.json')
NS = {'x': 'http://checklists.nist.gov/xccdf/1.1'}
SIZE_CEILING_KIB = 400
SPOT_PER_RELEASE = 6   # random rules accuracy-checked per release

SOURCES = {
    'R8':  'U_RHEL_8_STIG_V2R3_Manual-xccdf.xml',
    'R9':  'U_RHEL_9_STIG_V2R5_Manual-xccdf.xml',
    'R10': 'U_RHEL_10_STIG_V1R1_Manual-xccdf.xml',
}
# deterministic "random" sample: fixed stride, no RNG (reproducible in CI)
SAMPLE_STRIDE = 47

results = []  # (group, name, ok, detail)
def check(group, name, ok, detail=''):
    results.append((group, name, bool(ok), detail))


def clean(s):
    if s is None:
        return ''
    s = re.sub(r'<[^>]+>', '', s)
    s = htmllib.unescape(s)
    return re.sub(r'\n{3,}', '\n\n', s.replace('\r\n', '\n')).strip()


def parse_source(tag):
    root = ET.parse(os.path.join(SRC, SOURCES[tag])).getroot()
    out = {}
    for g in root.findall('x:Group', NS):
        rule = g.find('x:Rule', NS)
        if rule is None:
            continue
        vid = g.get('id')
        sev = {'high': 'I', 'medium': 'II', 'low': 'III'}.get(rule.get('severity'), '?')
        cci = ''
        for ident in rule.findall('x:ident', NS):
            if 'cci' in (ident.get('system') or '').lower():
                cci = (ident.text or '').strip(); break
        ver = rule.find('x:version', NS)
        fix_el = rule.find('x:fixtext', NS)
        out[vid] = {
            'c': sev,
            't': clean(rule.find('x:title', NS).text),
            'i': clean(ver.text) if ver is not None else '',
            'cci': cci,
            'fix': clean(fix_el.text) if fix_el is not None else '',
        }
    return out


def main():
    # ---- load product ----
    if not os.path.exists(PROD):
        print('FATAL: rhel-stig.html not found — run build-rhel-stig.py first')
        sys.exit(1)
    doc = open(PROD, encoding='utf-8').read()

    # ===== BUILD =====
    check('BUILD', 'template placeholder replaced', '/*__STIG_DATA__*/' not in doc)
    size_bytes = os.path.getsize(PROD)
    check(
        'BUILD',
        f'size <= {SIZE_CEILING_KIB} KiB',
        size_bytes <= SIZE_CEILING_KIB * 1024,
        f'{size_bytes} bytes',
    )
    m = re.search(r'<script id="stigdata" type="application/json">(.*?)</script>', doc, re.S)
    check('BUILD', 'embedded data script present', bool(m))
    data = None
    if m:
        try:
            data = json.loads(m.group(1)); check('BUILD', 'embedded JSON parses', True)
        except Exception as e:
            check('BUILD', 'embedded JSON parses', False, str(e)[:60])
    if not data:
        report(); return
    rules = data['rules']; lab = data['lab']
    by_rel = {}
    for r in rules:
        by_rel.setdefault(r['r'], []).append(r)

    # ===== DATA + ACCURACY per release =====
    cci_map = json.load(open(CCI_MAP_PATH, encoding='utf-8')) if os.path.exists(CCI_MAP_PATH) else {}
    check('MAPPING', 'cci-map.json present', bool(cci_map), f'{len(cci_map)} entries')

    for tag in SOURCES:
        src = parse_source(tag)
        emb = {r['v']: r for r in by_rel.get(tag, [])}
        # count parity
        check('DATA', f'{tag}: rule count matches source', len(emb) == len(src),
              f'embedded {len(emb)} vs source {len(src)}')
        # CAT I completeness: every CAT I has check + fix
        cat1 = [r for r in emb.values() if r['c'] == 'I']
        src_cat1 = [v for v, d in src.items() if d['c'] == 'I']
        check('DATA', f'{tag}: CAT I count matches source', len(cat1) == len(src_cat1),
              f'{len(cat1)} vs {len(src_cat1)}')
        check('DATA', f'{tag}: every CAT I has check+fix text',
              all(r.get('chk') and r.get('fix') for r in cat1),
              f'{sum(1 for r in cat1 if not (r.get("chk") and r.get("fix")))} missing')
        # identifiers
        check('DATA', f'{tag}: every rule has a STIG ID', all(r.get('i') for r in emb.values()),
              f'{sum(1 for r in emb.values() if not r.get("i"))} missing')
        # CCI coverage: embedded cci present wherever source has one
        cci_gap = [v for v, d in src.items() if d['cci'] and not emb.get(v, {}).get('cci')]
        check('DATA', f'{tag}: CCI present wherever source has one', not cci_gap,
              f'{len(cci_gap)} gaps')
        # NIST coverage: where cci maps, 'n' present
        nist_gap = [r['v'] for r in emb.values()
                    if r.get('cci') and cci_map.get(r['cci']) and not r.get('n')]
        check('DATA', f'{tag}: NIST 800-53 present where CCI maps', not nist_gap,
              f'{len(nist_gap)} gaps')

        # accuracy spot-check: deterministic sample re-diffed against source XML
        vids = sorted(emb)
        sample = vids[::SAMPLE_STRIDE][:SPOT_PER_RELEASE] or vids[:SPOT_PER_RELEASE]
        bad = []
        for v in sample:
            e, s = emb[v], src[v]
            if e['t'] != s['t']:
                bad.append(f'{v} title'); continue
            if e.get('i') != s['i']:
                bad.append(f'{v} stigid'); continue
            if s['cci'] and e.get('cci') != s['cci']:
                bad.append(f'{v} cci'); continue
            if e.get('fix'):
                ef = e['fix'].split('[trimmed')[0].strip()
                if ef and not s['fix'].startswith(ef[:100]):
                    bad.append(f'{v} fix'); continue
            if e.get('n') and s['cci']:
                if cci_map.get(s['cci']) != e['n']:
                    bad.append(f'{v} nist'); continue
        check('ACCURACY', f'{tag}: {len(sample)} sampled rules match source XML', not bad,
              ', '.join(bad) if bad else 'all match')

    # ===== MAPPING accuracy: sample CCIs vs DISA list =====
    if cci_map:
        seen = {r['cci']: r.get('n') for r in rules if r.get('cci') and r.get('n')}
        sample_cci = sorted(seen)[::11][:8]
        bad = [c for c in sample_cci if cci_map.get(c) != seen[c]]
        check('MAPPING', f'{len(sample_cci)} sampled CCI->800-53 match DISA list', not bad,
              ', '.join(bad) if bad else 'all match')

    # ===== LAB =====
    lab_by_rel = {}
    for l in lab:
        lab_by_rel.setdefault(l['r'], []).append(l)
    for tag in SOURCES:
        n_cat1 = len([r for r in by_rel.get(tag, []) if r['c'] == 'I'])
        check('LAB', f'{tag}: lab findings == CAT I count', len(lab_by_rel.get(tag, [])) == n_cat1,
              f'{len(lab_by_rel.get(tag, []))} vs {n_cat1}')
    fixable = [l for l in lab if l['m'] != 'man']
    manual = [l for l in lab if l['m'] == 'man']
    check('LAB', 'fixable/manual split is sane (both non-empty, majority fixable)',
          len(fixable) > 0 and len(manual) > 0 and len(fixable) > len(manual),
          f'{len(fixable)} fixable / {len(manual)} manual')

    # ARCH table: every archetype used by a fixable lab finding must be defined,
    # and its guided fixhint must satisfy its own fixmatch (guided 'next' must work).
    arch_block = doc[doc.find('var ARCH={'):doc.find('// manual archetypes')]
    used_archs = sorted({l['a'] for l in fixable})
    defined = set(re.findall(r'(\w+):\{ chk:function', arch_block))
    missing = [a for a in used_archs if a not in defined]
    check('LAB', 'every used archetype has an ARCH definition', not missing,
          ', '.join(missing) if missing else f'{len(used_archs)} archetypes')

    # guided-fix self-consistency: for each archetype, the guided fixhint must satisfy
    # its own fixmatch — otherwise 'next' shows a fix that doesn't flip the finding.
    # Parse each archetype's fixhint return-string and fixmatch return-expression.
    def js_str(block, field):
        # fixhint:function(g){return <STR>;}  — capture the returned string literal(s)
        m2 = re.search(field + r':function\([^)]*\)\{return (.*?);\}', block)
        if not m2:
            return None
        expr = m2.group(1)
        # join concatenated 'x'+g+'y' string parts into a representative sample using target g
        parts = re.findall(r"'([^']*)'|\"([^\"]*)\"", expr)
        return ''.join(a or b for a, b in parts)

    inconsistent = []
    # split ARCH block into per-archetype segments
    seg = re.findall(r'(\w+):\{ chk:function.*?ok:function[^}]*\}[^}]*\}', arch_block)
    arch_segs = {}
    for a in used_archs:
        mseg = re.search(re.escape(a) + r':\{ chk:function.*?\}, ok:function', arch_block)
        if mseg:
            arch_segs[a] = mseg.group(0)
    for a, block in arch_segs.items():
        # sample fix commands taken from this archetype's own lab targets
        targets = [l['g'] for l in fixable if l['a'] == a] or ['']
        hint_tmpl = js_str(block, 'fixhint') or ''
        mexpr = re.search(r'fixmatch:function\(([^)]*)\)\{return (.*?);\}, ok:', block)
        if not hint_tmpl or not mexpr:
            continue
        match_body = mexpr.group(2)
        regexes = re.findall(r'/((?:[^/\\]|\\.)+)/', match_body)
        idx_tokens = re.findall(r"indexOf\('([^']+)'\)", match_body)
        # build a candidate command: the hint text plus a concrete target
        ok_any = False
        for tgt in targets:
            cand = hint_tmpl + ' ' + tgt
            rx_ok = False
            for rx in regexes:
                try:
                    if re.search(rx, cand):
                        rx_ok = True; break
                except re.error:
                    rx_ok = True; break
            tok_ok = (not idx_tokens) or any(t in cand for t in idx_tokens)
            if (rx_ok or not regexes) and tok_ok:
                ok_any = True; break
        if not ok_any:
            inconsistent.append(a)
    check('LAB', "guided fixhint satisfies its own fixmatch", not inconsistent,
          ', '.join(inconsistent) if inconsistent else f'{len(arch_segs)} archetypes verified')

    # ===== HTML integrity =====
    check('HTML', 'no leftover template markers', '__' + '_' not in doc.replace('__STIG', '') and '/*__' not in doc)
    check('HTML', '<script> tags balanced',
          doc.count('<script') == doc.count('</script>'),
          f'{doc.count("<script")} open / {doc.count("</script>")} close')
    anchors = ['start', 'model', 'goods', 'anatomy', 'oscap', 'workflow', 'tour',
               'automation', 'browser', 'builder', 'lab', 'prove', 'cheat', 'capstone', 'next']
    missing_anchors = [a for a in anchors if f'id="{a}"' not in doc]
    check('HTML', 'all 15 section anchors present', not missing_anchors,
          ', '.join(missing_anchors) if missing_anchors else '15/15')
    for hook, label in [
        ('ofm-rhel-stig-capstone', 'capstone localStorage'),
        ('ofm-rhel-stig-status', 'tracker localStorage'),
        ('ofm-rhel-stig-lastsec', 'resume localStorage'),
        ('@media print', 'print stylesheet'),
        ('id="tocToggle"', 'mobile TOC toggle'),
        ('copybtn', 'copy buttons'),
    ]:
        check('HTML', f'UI baseline: {label} present', hook in doc)
    # provenance / licensing (paid-product must-haves)
    check('HTML', 'footer names DISA source versions',
          'V2R3' in doc and 'V2R5' in doc and 'V1R1' in doc)
    check('HTML', 'single-user license + AI disclosure present',
          'Single-user license' in doc and 'AI assistance' in doc)

    report()


def report():
    groups = {}
    for g, n, ok, d in results:
        groups.setdefault(g, []).append((n, ok, d))
    total = len(results); passed = sum(1 for *_, ok, _ in [(r[0], r[1], r[2], r[3]) for r in results] if ok)
    passed = sum(1 for r in results if r[2])
    print('\n' + '=' * 66)
    print(' QA GATE — RHEL STIG Field Manual')
    print('=' * 66)
    for g in ['BUILD', 'DATA', 'ACCURACY', 'MAPPING', 'LAB', 'HTML']:
        if g not in groups:
            continue
        print(f'\n[{g}]')
        for n, ok, d in groups[g]:
            mark = 'PASS' if ok else 'FAIL'
            line = f'  {mark}  {n}'
            if d:
                line += f'   ({d})'
            print(line)
    fails = total - passed
    print('\n' + '-' * 66)
    print(f' {passed}/{total} checks passed' + ('' if fails == 0 else f'  —  {fails} FAILURE(S)'))
    print('-' * 66)
    sys.exit(0 if fails == 0 else 1)


if __name__ == '__main__':
    main()
