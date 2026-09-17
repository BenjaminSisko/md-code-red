#!/usr/bin/env python3
"""
build-rhel-stig.py — Practical Ops Lab data pipeline for the RHEL STIG guide.

Parses the official DISA Manual XCCDF for RHEL 8, 9, 10 and injects a compact
dataset into rhel-stig.template.html, producing the shippable rhel-stig.html.

Refresh workflow when DISA publishes a new quarterly release:
  1. Download the new U_RHEL_<v>_<rel>_STIG.zip from dl.dod.cyber.mil
  2. Unzip; drop the *Manual-xccdf.xml next to this script (or edit SOURCES)
  3. python3 build-rhel-stig.py
  4. Re-run the QA gate on rhel-stig.html

Datasets produced and injected:
  RULES : every rule (v-id, release, CAT, title, SRG). Full check+fix text for
          all CAT I; fix text for curated high-traffic CAT II. Drives the rule
          browser + checklist tracker.
  LAB   : per-release CAT I findings classified into shell-fixable archetypes or
          honestly-flagged manual/install-time findings. Drives the practice lab.
"""
import xml.etree.ElementTree as ET
import re, html, json, sys, os

NS = {'x': 'http://checklists.nist.gov/xccdf/1.1'}

# (xccdf filename, release tag, human release label). Edit on refresh.
SOURCES = [
    ('U_RHEL_8_STIG_V2R3_Manual-xccdf.xml',  'R8',  'RHEL 8 · STIG V2R3 · 02 Apr 2025'),
    ('U_RHEL_9_STIG_V2R5_Manual-xccdf.xml',  'R9',  'RHEL 9 · STIG V2R5 · 02 Jul 2025'),
    ('U_RHEL_10_STIG_V1R1_Manual-xccdf.xml', 'R10', 'RHEL 10 · STIG V1R1 · 26 Feb 2026'),
]

# curated CAT II titles that get fix text embedded (week-one, high-traffic controls)
CURATED_II = ['permitrootlogin', ' ssh', 'sudo', 'pam_faillock', 'pwquality',
    'password complexity', 'account lock', 'banner', 'umask', 'tmout', 'session lock',
    'usb mass storage', 'autofs', 'core dump', 'grub', 'firewalld', 'audit package',
    'auditd', 'world-writable', 'promiscuous', 'nologin', 'aslr', 'kdump',
    'chrony', 'ntp', 'wireless', 'gpgcheck', 'sysrq']
MAX_II_PER_REL = 18


def clean(s):
    if s is None:
        return ''
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = s.replace('\r\n', '\n')
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def cap(s, n):
    if len(s) <= n:
        return s
    return s[:n].rsplit('\n', 1)[0].rstrip() + \
        '\n\n[trimmed — full text in the official STIG / STIG Viewer]'


def classify(title, tag='R9'):
    """CAT I title -> (mode, archetype, target). mode: 'fix' shell-fixable, 'man' manual."""
    t = title.lower()
    if 'vendor-supported' in t: return ('man', 'support', '')
    if 'partitions must implement cryptographic' in t or ('disk' in t and 'crypto' in t): return ('man', 'disk', '')
    if 'uefi' in t or 'bios' in t or 'single-user' in t or 'maintenance mode' in t or 'superuser' in t or ('boot' in t and 'password' in t): return ('man', 'boot', '')
    if 'ip tunnel' in t or 'bind package' in t: return ('man', 'cryptomisc', '')
    if 'telnet' in t: return ('pkg', 'pkg', 'telnet-server')
    if 'rsh-server' in t: return ('pkg', 'pkg', 'rsh-server')
    if 'tftp' in t: return ('pkg', 'pkg', 'tftp' if tag == 'R10' else 'tftp-server')
    if 'ftp' in t and 'trivial' not in t: return ('pkg', 'pkg', 'vsftpd')
    if 'shosts.equiv' in t: return ('file', 'file', '/etc/ssh/shosts.equiv')
    if '.shosts' in t: return ('file', 'file', '.shosts')
    if 'ctrl-alt-delete' in t and 'burst' in t: return ('svc', 'cadburst', '')
    if 'ctrl-alt-delete' in t: return ('svc', 'cadtarget', '')
    if 'blank' in t or 'null password' in t: return ('cfg', 'nullok', '')
    if 'pluggable authentication module' in t or ('pam' in t and 'sshd' in t): return ('cfg', 'sshdpam', '')
    if 'automatic log' in t or 'automatic login' in t or 'unattended' in t: return ('cfg', 'autologin', '')
    if 'root account must be the only' in t: return ('cfg', 'uid0', '')
    if 'gpg signature' in t or 'gnu privacy guard' in t or 'signature verification' in t or 'digitally signed' in t: return ('cfg', 'gpgcheck', '')
    if 'crypto-policies' in t and 'package' in t: return ('pkgreq', 'pkgreq', 'crypto-policies')
    if 'fips mode' in t or 'fips-validated' in t: return ('fips', 'fips', '')
    if 'cryptographic policy must not be overridden' in t or 'systemwide cryptographic policy' in t: return ('cfg', 'cryptopolicy', '')
    if 'security module' in t: return ('cfg', 'selinux', '')
    if 'privilege escalation' in t: return ('cfg', 'sudopw', '')
    if 'cipher' in t: return ('cfg', 'sshciphers', '')
    if 'message authentication' in t: return ('cfg', 'sshmacs', '')
    if 'hashing algorithms' in t or 'shadow file' in t or 'encrypted representations' in t: return ('cfg', 'pwhash', '')
    if 'new kernel' in t or 'kexec' in t: return ('cfg', 'kexec', '')
    if 'audit tools' in t: return ('cfg', 'audittools', '')
    if 'environment variables' in t: return ('cfg', 'sshenv', '')
    if 'renegotiation' in t: return ('cfg', 'sshrekey', '')
    if 'account administration utilities' in t: return ('cfg', 'useradd', '')
    return ('cfg', 'generic', '')


def find_source(fname):
    """Look for the XCCDF in cwd, script dir, or the stig-src/ source folder."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (fname, os.path.join(here, fname), os.path.join(here, 'stig-src', fname)):
        if os.path.exists(p):
            return p
    return None


def load_cci_map():
    """CCI -> NIST SP 800-53 control, from DISA U_CCI_List (stig-src/cci-map.json)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, 'stig-src', 'cci-map.json'), os.path.join(here, 'cci-map.json')):
        if os.path.exists(p):
            return json.load(open(p, encoding='utf-8'))
    print('WARN: cci-map.json not found - rules will omit NIST mapping', file=sys.stderr)
    return {}


CCI_MAP = load_cci_map()


def parse(fname, tag):
    root = ET.parse(fname).getroot()
    rules, lab, ii_count = [], [], 0
    for g in root.findall('x:Group', NS):
        rule = g.find('x:Rule', NS)
        if rule is None:
            continue
        vid = g.get('id')
        sev = rule.get('severity')
        cat = {'high': 'I', 'medium': 'II', 'low': 'III'}.get(sev, '?')
        title = clean(rule.find('x:title', NS).text)
        ver = rule.find('x:version', NS)
        stig_id = clean(ver.text) if ver is not None else ''   # e.g. RHEL-09-212015
        # CCI (DISA ident) -> NIST SP 800-53 control
        cci = ''
        for ident in rule.findall('x:ident', NS):
            if 'cci' in (ident.get('system') or '').lower():
                cci = (ident.text or '').strip()
                break
        nist = CCI_MAP.get(cci, '') if cci else ''
        chk_el = rule.find('x:check/x:check-content', NS)
        fix_el = rule.find('x:fixtext', NS)
        chk = clean(chk_el.text) if chk_el is not None else ''
        fix = clean(fix_el.text) if fix_el is not None else ''
        entry = {'v': vid, 'r': tag, 'c': cat, 't': title, 'i': stig_id}
        if cci:
            entry['cci'] = cci
        if nist:
            entry['n'] = nist
        if cat == 'I':
            entry['chk'] = cap(chk, 880)
            entry['fix'] = cap(fix, 740)
            mode, arch, target = classify(title, tag)
            lab.append({'v': vid, 'r': tag, 'a': arch, 'g': target, 't': title, 'm': mode})
        elif cat == 'II' and ii_count < MAX_II_PER_REL and any(k in title.lower() for k in CURATED_II):
            entry['fix'] = cap(fix, 440)
            ii_count += 1
        rules.append(entry)
    return rules, lab


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    all_rules, all_lab, releases = [], [], []
    for fname, tag, label in SOURCES:
        path = find_source(fname)
        if not path:
            print('MISSING:', fname, '- put it in _tools/stig-src/ - skipping', file=sys.stderr)
            continue
        rules, lab = parse(path, tag)
        all_rules += rules
        all_lab += lab
        c1 = sum(1 for r in rules if r['c'] == 'I')
        releases.append({'tag': tag, 'label': label, 'n': len(rules), 'c1': c1})
        print(f'{tag}: {len(rules)} rules ({c1} CAT I), {len(lab)} lab findings')

    data = {'releases': releases, 'rules': all_rules, 'lab': all_lab}
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    print(f'dataset: {len(payload)//1024} KB, {len(all_rules)} rules total')

    tpl_path = os.path.join(here, 'rhel-stig.template.html')
    out_path = os.path.join(os.path.dirname(here), 'rhel-stig.html')
    tpl = open(tpl_path, encoding='utf-8').read()
    if '/*__STIG_DATA__*/' not in tpl:
        print('ERROR: placeholder /*__STIG_DATA__*/ not found in template', file=sys.stderr)
        sys.exit(1)
    out = tpl.replace('/*__STIG_DATA__*/', payload)
    open(out_path, 'w', encoding='utf-8').write(out)
    print(f'wrote {out_path}: {os.path.getsize(out_path)//1024} KB')


if __name__ == '__main__':
    main()
