#!/usr/bin/env python3
"""Execute stateful runbook commands after binding them with the shipped JS binder."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
BINDER=ROOT/'tests'/'instruction_binding_probe.js'


def app_bind(text,values):
    proc=subprocess.run(['node',str(BINDER),str(ROOT/'template.html')],
                        input=json.dumps({'text':text,'values':values}),text=True,
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return json.loads(proc.stdout)['bound']


class InstructionCommandBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        commands=json.loads((ROOT/'content/commands.json').read_text())['entries']
        cls.entries={e['id']:e for e in commands}
        cls.instructions=json.loads((ROOT/'content/instructional.json').read_text())['entries']

    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='mdcr-nmcli-bind-'))
        self.profile_dir=self.tmp/'system-connections'; self.profile_dir.mkdir()
        self.profile=self.profile_dir/'Wired connection 1.nmconnection'
        self.profile.write_text('before\n')
        self.state_root=self.tmp/'state-root'
        self.txn=self.state_root/'nmcli-static-ipv4.txn'
        self.nmcli_log=self.tmp/'nmcli.log'
        fakebin=self.tmp/'bin'; fakebin.mkdir()
        (fakebin/'sudo').write_text("""#!/usr/bin/env python3
import os, subprocess, sys
script=sys.stdin.read().replace('/var/lib/md-code-red',os.environ['MDCR_TEST_STATE_ROOT'])
result=subprocess.run(sys.argv[1:],input=script,text=True)
raise SystemExit(result.returncode)
""")
        (fakebin/'install').write_text("""#!/usr/bin/env python3
import os, pathlib, sys
target=pathlib.Path(sys.argv[-1])
if target.is_symlink(): raise SystemExit(1)
target.mkdir(parents=True,exist_ok=True)
os.chmod(target,0o700)
""")
        (fakebin/'stat').write_text("""#!/usr/bin/env python3
import os, stat, sys
fmt=sys.argv[sys.argv.index('-c')+1]
path=os.path.abspath(sys.argv[-1])
st=os.stat(path)
mode=format(stat.S_IMODE(st.st_mode),'o')
uid=1 if os.environ.get('MDCR_TEST_BAD_UID_PATH') and path.startswith(os.path.abspath(os.environ['MDCR_TEST_BAD_UID_PATH'])) else 0
if fmt=='%u:%a': print(str(uid)+':'+mode)
elif fmt=='%u': print(uid)
else: raise SystemExit(64)
""")
        (fakebin/'restorecon').write_text('#!/bin/sh\nexit 0\n')
        (fakebin/'nmcli').write_text("""#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "$MDCR_TEST_NMCLI_LOG"
if [ "$1" = "-g" ] && [ "$2" = "FILENAME,NAME,UUID" ]; then
  if [ "${MDCR_TEST_RACE_CREATE_TXN:-}" = yes ]; then
    mkdir -m 0700 -- "$MDCR_TEST_STATE_ROOT/nmcli-static-ipv4.txn"
  fi
  case "${MDCR_TEST_NMCLI_MODE:-single}" in
    missing) exit 0 ;;
    duplicate)
      printf '%s:%s:%s\\n' "$MDCR_TEST_PROFILE" 'Wired connection 1' '11111111-2222-3333-4444-555555555555'
      printf '%s:%s:%s\\n' "$MDCR_TEST_PROFILE" 'Wired connection 1' 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' ;;
    numeric)
      printf '%s:%s:%s\\n' "$MDCR_TEST_PROFILE" '10' '11111111-2222-3333-4444-555555555555'
      printf '%s:%s:%s\\n' "$MDCR_TEST_PROFILE" '1e1' 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' ;;
    *) printf '%s:%s:%s\\n' "$MDCR_TEST_PROFILE" 'Wired connection 1' '11111111-2222-3333-4444-555555555555' ;;
  esac
elif [ "$1" = "connection" ] && [ "$2" = "reload" ]; then
  exit 0
elif [ "$1" = "connection" ] && [ "$2" = "up" ] && [ "$3" = "Wired connection 1" ]; then
  exit 0
else
  printf '%s\\n' "unexpected nmcli argv: $*" >&2
  exit 64
fi
""")
        for name in ('sudo','install','stat','restorecon','nmcli'):(fakebin/name).chmod(0o755)
        self.env=os.environ.copy()
        self.env['PATH']=str(fakebin)+os.pathsep+self.env.get('PATH','')
        self.env['MDCR_TEST_PROFILE']=str(self.profile)
        self.env['MDCR_TEST_STATE_ROOT']=str(self.state_root)
        self.env['MDCR_TEST_NMCLI_LOG']=str(self.nmcli_log)

    def tearDown(self):
        shutil.rmtree(self.tmp,ignore_errors=True)

    def run_bound(self,text,check=True,con='Wired connection 1'):
        command=app_bind(text,{'con':con})
        result=subprocess.run(command,shell=True,executable='/bin/sh',env=self.env,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=check)
        return command,result

    def preflight(self):
        rows=self.instructions['gen-nmcli-static-ipv4']['preflight']
        return next(row['command'] for row in rows
                    if 'MDCR_NMCLI_PREFLIGHT' in (row.get('command') or ''))

    def make_complete_txn(self,mode=0o700):
        self.state_root.mkdir(mode=0o700)
        self.txn.mkdir(mode=mode)
        (self.txn/'before').write_text('before\n')
        (self.txn/'profile_path').write_text(str(self.profile)+'\n')

    def test_nmcli_space_bearing_name_backs_up_and_restores_actual_profile(self):
        rows=self.instructions['gen-nmcli-static-ipv4']['preflight']
        show=rows[0]['command']
        self.assertEqual(app_bind(show,{'con':'Wired connection 1'}),
                         "nmcli connection show 'Wired connection 1'")
        bound,_=self.run_bound(self.preflight())
        self.assertTrue(bound.endswith("sudo sh -s -- 'Wired connection 1'"),bound)
        self.assertIn('state_root=/var/lib/md-code-red',bound)
        self.assertEqual((self.txn/'before').read_text(),'before\n')
        self.assertEqual((self.txn/'profile_path').read_text(),str(self.profile)+'\n')
        self.assertEqual(self.state_root.stat().st_mode & 0o777,0o700)
        self.assertEqual(self.txn.stat().st_mode & 0o777,0o700)
        self.assertNotEqual(self.state_root,self.profile_dir)
        self.profile.write_text('after\n')
        recover=self.entries['gen-nmcli-static-ipv4']['undo']
        recover_bound,_=self.run_bound(recover)
        self.assertTrue(recover_bound.endswith("sudo sh -s -- 'Wired connection 1'"),recover_bound)
        self.assertEqual(self.profile.read_text(),'before\n')
        self.assertFalse(self.txn.exists())
        calls=self.nmcli_log.read_text()
        self.assertIn('connection reload',calls)
        self.assertIn('connection up Wired connection 1',calls)

    def test_instruction_values_are_bound_once(self):
        bound=app_bind('<first> {{second}}',{
            'first':'{{second}}',
            'second':'<first>',
        })
        self.assertEqual(bound,"'{{second}}' '<first>'")

    def test_nmcli_preflight_refuses_preexisting_transaction_directory(self):
        self.state_root.mkdir(mode=0o700)
        self.txn.mkdir(mode=0o700)
        marker=self.txn/'untrusted'; marker.write_text('keep\n')
        _,result=self.run_bound(self.preflight(),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('unfinished NetworkManager transaction',result.stderr)
        self.assertEqual(marker.read_text(),'keep\n')
        self.assertFalse((self.txn/'before').exists())

    def test_nmcli_preflight_refuses_symlinked_transaction(self):
        self.state_root.mkdir(mode=0o700)
        outside=self.tmp/'outside'; outside.mkdir()
        self.txn.symlink_to(outside,target_is_directory=True)
        _,result=self.run_bound(self.preflight(),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('unfinished NetworkManager transaction',result.stderr)
        self.assertTrue(self.txn.is_symlink())
        self.assertEqual(list(outside.iterdir()),[])

    def test_nmcli_preflight_atomic_mkdir_refuses_midflight_transaction(self):
        self.env['MDCR_TEST_RACE_CREATE_TXN']='yes'
        _,result=self.run_bound(self.preflight(),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.txn.is_dir())
        self.assertFalse((self.txn/'before').exists())

    def test_nmcli_recover_and_finalize_refuse_untrusted_mode(self):
        self.make_complete_txn(mode=0o755)
        self.profile.write_text('after\n')
        _,recover=self.run_bound(self.entries['gen-nmcli-static-ipv4']['undo'],check=False)
        self.assertNotEqual(recover.returncode,0)
        self.assertIn('no trusted complete NetworkManager transaction',recover.stderr)
        self.assertEqual(self.profile.read_text(),'after\n')
        _,finalize=self.run_bound(self.entries['gen-nmcli-static-ipv4']['verify'],check=False)
        self.assertNotEqual(finalize.returncode,0)
        self.assertIn('no trusted complete NetworkManager transaction',finalize.stderr)
        self.assertTrue(self.txn.exists())

    def test_nmcli_recover_refuses_symlinked_state_root(self):
        outside=self.tmp/'outside-state'; outside.mkdir(mode=0o700)
        self.state_root.symlink_to(outside,target_is_directory=True)
        _,result=self.run_bound(self.entries['gen-nmcli-static-ipv4']['undo'],check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('state root is not root-owned mode 0700',result.stderr)

    def test_nmcli_preflight_reports_missing_and_duplicate_matches(self):
        for mode in ('missing','duplicate'):
            with self.subTest(mode=mode):
                self.env['MDCR_TEST_NMCLI_MODE']=mode
                _,result=self.run_bound(self.preflight(),check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('did not resolve exactly once',result.stderr)
                self.assertFalse(self.txn.exists())
        self.env.pop('MDCR_TEST_NMCLI_MODE',None)

    def test_nmcli_numeric_looking_name_uses_string_equality(self):
        self.env['MDCR_TEST_NMCLI_MODE']='numeric'
        _,result=self.run_bound(self.preflight(),check=False,con='1e1')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(self.txn.is_dir())

    def test_nmcli_refuses_forged_state_ownership(self):
        self.state_root.mkdir(mode=0o700)
        self.env['MDCR_TEST_BAD_UID_PATH']=str(self.state_root)
        _,result=self.run_bound(self.preflight(),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('state root is not root-owned mode 0700',result.stderr)


if __name__=='__main__':
    unittest.main()
