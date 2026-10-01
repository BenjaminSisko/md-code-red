#!/usr/bin/env python3
"""Execute stateful runbook commands after binding them with the shipped JS binder."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
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
import os, signal, subprocess, sys
script=sys.stdin.read().replace('/var/lib/md-code-red',os.environ['MDCR_TEST_STATE_ROOT'])
if os.environ.get('MDCR_TEST_REMOTE_PID_FILE'):
    def reset_signals():
        for sig in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM):
            signal.signal(sig,signal.SIG_DFL)
    child=subprocess.Popen(sys.argv[1:],stdin=subprocess.PIPE,text=True,
                           preexec_fn=reset_signals)
    open(os.environ['MDCR_TEST_REMOTE_PID_FILE'],'w').write(str(child.pid)+'\\n')
    child.communicate(script)
    statusfile=os.environ.get('MDCR_TEST_REMOTE_STATUS_FILE')
    if statusfile: open(statusfile,'w').write(str(child.returncode)+'\\n')
    raise SystemExit(child.returncode)
result=subprocess.run(sys.argv[1:],input=script,text=True)
raise SystemExit(result.returncode)
""")
        (fakebin/'install').write_text("""#!/usr/bin/env python3
import os, pathlib, sys
target=pathlib.Path(sys.argv[-1])
target.mkdir(parents=True,exist_ok=True)
os.chmod(target.resolve(),0o700)
""")
        (fakebin/'stat').write_text("""#!/usr/bin/env python3
import os, stat, sys, time
fmt=sys.argv[sys.argv.index('-c')+1]
path=os.path.abspath(sys.argv[-1])
st=os.stat(path)
mode=format(stat.S_IMODE(st.st_mode),'o')
uid=1 if os.environ.get('MDCR_TEST_BAD_UID_PATH') and path==os.path.abspath(os.environ['MDCR_TEST_BAD_UID_PATH']) else 0
pause=os.environ.get('MDCR_TEST_SIGNAL_PATH','')
if pause and path==os.path.abspath(pause) and fmt=='%u':
    open(os.environ['MDCR_TEST_SIGNAL_READY'],'w').close()
    while not os.path.exists(os.environ['MDCR_TEST_SIGNAL_RELEASE']): time.sleep(0.01)
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

    def app_plan_custom(self,entry,values):
        proc=subprocess.run(['node',str(BINDER),str(ROOT/'template.html')],
                            input=json.dumps({'plan_entry':entry,'values':values}),text=True,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        return json.loads(proc.stdout)['plan']

    def preflight(self):
        rows=self.instructions['gen-nmcli-static-ipv4']['preflight']
        return next(row['command'] for row in rows
                    if 'MDCR_NMCLI_PREFLIGHT' in (row.get('command') or ''))

    def make_complete_txn(self,mode=0o700):
        self.state_root.mkdir(mode=0o700)
        self.txn.mkdir(mode=mode)
        (self.txn/'before').write_text('before\n')
        (self.txn/'profile_path').write_text(str(self.profile)+'\n')

    def reset_state(self):
        if self.state_root.is_symlink(): self.state_root.unlink()
        else: shutil.rmtree(self.state_root,ignore_errors=True)

    def test_nmcli_space_bearing_name_backs_up_and_restores_actual_profile(self):
        rows=self.instructions['gen-nmcli-static-ipv4']['preflight']
        show=rows[0]['command']
        self.assertEqual(app_bind(show,{'con':'Wired connection 1'}),
                         "PAGER=cat nmcli connection show 'Wired connection 1'")
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

    def test_user_value_cannot_inject_a_runnable_runbook_marker(self):
        injected="printf '%s\\n' '# MDCR_FAKE_RECOVER' 'touch /tmp/owned'"
        entry={'id':'synthetic-plan','verify':'Review <payload> only.','undo':'No recovery command.'}
        plan=self.app_plan_custom(entry,{'payload':injected})
        self.assertIn('MDCR_FAKE_RECOVER',plan['verify'])
        self.assertIsNone(plan['copy']['verify'])
        self.assertIsNone(plan['copy']['recover'])

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

    def test_nmcli_preflight_refuses_symlinked_state_root_before_install_follows_it(self):
        outside=self.tmp/'outside-preflight-state'; outside.mkdir(mode=0o755)
        self.state_root.symlink_to(outside,target_is_directory=True)
        _,result=self.run_bound(self.preflight(),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('state root is not root-owned mode 0700',result.stderr)
        self.assertEqual(outside.stat().st_mode & 0o777,0o755,
                         'pre-install symlink guard must prevent chmod through the link')
        self.assertEqual(list(outside.iterdir()),[])

    def test_nmcli_recover_and_finalize_refuse_mode_0755_state_root(self):
        for action in ('undo','verify'):
            with self.subTest(action=action):
                self.reset_state(); self.make_complete_txn(); self.profile.write_text('after\n')
                self.state_root.chmod(0o755)
                _,result=self.run_bound(self.entries['gen-nmcli-static-ipv4'][action],check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('state root is not root-owned mode 0700',result.stderr)
                self.assertTrue(self.txn.exists())
                self.assertEqual(self.profile.read_text(),'after\n')

    def test_nmcli_finalize_clears_complete_transaction_and_allows_next_preflight(self):
        self.run_bound(self.preflight())
        self.assertTrue(self.txn.exists())
        _,result=self.run_bound(self.entries['gen-nmcli-static-ipv4']['verify'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.txn.exists())
        self.run_bound(self.preflight())
        self.assertTrue(self.txn.exists())

    def test_nmcli_recover_refuses_symlinked_or_different_resolved_profile(self):
        for mode in ('symlink','different'):
            with self.subTest(mode=mode):
                self.reset_state(); self.make_complete_txn(); self.profile.write_text('after\n')
                if mode=='symlink':
                    actual=self.profile_dir/'actual.nmconnection'; actual.write_text('outside\n')
                    self.profile.unlink(); self.profile.symlink_to(actual.name)
                    expected='expected one regular NetworkManager profile file'
                else:
                    other=self.profile_dir/'Other.nmconnection'; other.write_text('other\n')
                    self.env['MDCR_TEST_PROFILE']=str(other)
                    expected='connection now resolves to a different profile file'
                _,result=self.run_bound(self.entries['gen-nmcli-static-ipv4']['undo'],check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(expected,result.stderr)
                self.assertTrue(self.txn.exists())
                self.env['MDCR_TEST_PROFILE']=str(self.profile)
                if self.profile.is_symlink():
                    self.profile.unlink(); self.profile.write_text('before\n')

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

    def test_nmcli_preflight_refuses_each_forged_owner_path(self):
        for name,path,diagnostic in (
                ('state_root',self.state_root,'state root is not root-owned mode 0700'),
                ('transaction',self.txn,'no trusted complete NetworkManager transaction'),
                ('before',self.txn/'before','no trusted complete NetworkManager transaction'),
                ('profile_path',self.txn/'profile_path','no trusted complete NetworkManager transaction')):
            with self.subTest(path=name):
                self.reset_state()
                if name=='state_root': self.state_root.mkdir(mode=0o700)
                self.env['MDCR_TEST_BAD_UID_PATH']=str(path)
                _,result=self.run_bound(self.preflight(),check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(diagnostic,result.stderr)
                self.env.pop('MDCR_TEST_BAD_UID_PATH',None)

    def test_nmcli_recover_and_finalize_refuse_each_forged_owner_path(self):
        for action in ('undo','verify'):
            for name,path,diagnostic in (
                    ('state_root',self.state_root,'state root is not root-owned mode 0700'),
                    ('transaction',self.txn,'no trusted complete NetworkManager transaction'),
                    ('before',self.txn/'before','no trusted complete NetworkManager transaction'),
                    ('profile_path',self.txn/'profile_path','no trusted complete NetworkManager transaction')):
                with self.subTest(action=action,path=name):
                    self.reset_state(); self.make_complete_txn(); self.profile.write_text('after\n')
                    self.env['MDCR_TEST_BAD_UID_PATH']=str(path)
                    _,result=self.run_bound(self.entries['gen-nmcli-static-ipv4'][action],check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(diagnostic,result.stderr)
                    self.assertTrue(self.txn.exists())
                    self.assertEqual(self.profile.read_text(),'after\n')
                    self.env.pop('MDCR_TEST_BAD_UID_PATH',None)

    def test_nmcli_recover_and_finalize_refuse_each_missing_state_file(self):
        for action in ('undo','verify'):
            for missing in ('before','profile_path'):
                with self.subTest(action=action,missing=missing):
                    self.reset_state(); self.make_complete_txn(); self.profile.write_text('after\n')
                    (self.txn/missing).unlink()
                    _,result=self.run_bound(self.entries['gen-nmcli-static-ipv4'][action],check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('no trusted complete NetworkManager transaction',result.stderr)
                    self.assertTrue(self.txn.exists())
                    self.assertEqual(self.profile.read_text(),'after\n')

    def test_each_signal_cleans_nmcli_transaction_and_fails_pipeline(self):
        for sig in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM):
            with self.subTest(signal=sig.name):
                self.reset_state()
                ready=self.tmp/f'nmcli-{sig.name}.ready'
                release=self.tmp/f'nmcli-{sig.name}.release'
                pidfile=self.tmp/f'nmcli-{sig.name}.pid'
                statusfile=self.tmp/f'nmcli-{sig.name}.status'
                self.env.update({
                    'MDCR_TEST_SIGNAL_PATH':str(self.txn/'profile_path'),
                    'MDCR_TEST_SIGNAL_READY':str(ready),
                    'MDCR_TEST_SIGNAL_RELEASE':str(release),
                    'MDCR_TEST_REMOTE_PID_FILE':str(pidfile),
                    'MDCR_TEST_REMOTE_STATUS_FILE':str(statusfile),
                })
                command=app_bind(self.preflight(),{'con':'Wired connection 1'})
                self.assertIn("'trap '\"'\"'exit 1'\"'\"' HUP INT TERM'",command)
                self.assertIn('trap cleanup EXIT',command)
                proc=subprocess.Popen(command,shell=True,executable='/bin/sh',env=self.env,
                                      text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                deadline=time.monotonic()+5
                while (not ready.exists() or not pidfile.exists()) and proc.poll() is None and time.monotonic()<deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(),'preflight never reached final profile_path validation')
                self.assertTrue(pidfile.exists(),'sudo wrapper did not record the generated shell pid')
                os.kill(int(pidfile.read_text().strip()),sig)
                release.touch()
                _out,err=proc.communicate(timeout=5)
                self.assertEqual(proc.returncode,1,err)
                self.assertEqual(statusfile.read_text().strip(),'1')
                self.assertFalse(self.txn.exists())
                for key in ('MDCR_TEST_SIGNAL_PATH','MDCR_TEST_SIGNAL_READY','MDCR_TEST_SIGNAL_RELEASE','MDCR_TEST_REMOTE_PID_FILE','MDCR_TEST_REMOTE_STATUS_FILE'):
                    self.env.pop(key,None)


if __name__=='__main__':
    unittest.main()
