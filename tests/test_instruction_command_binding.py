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
NM_TXN=Path('/var/tmp/mdcr-nmcli-static-ipv4.txn')
NM_PREPARING=Path(str(NM_TXN)+'.preparing')


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
        if NM_TXN.exists() or NM_TXN.is_symlink() or NM_PREPARING.exists() or NM_PREPARING.is_symlink():
            self.fail('the real NetworkManager transaction path is already in use; refusing to overwrite it')
        self.tmp=Path(tempfile.mkdtemp(prefix='mdcr-nmcli-bind-'))
        self.profile_dir=self.tmp/'system-connections'; self.profile_dir.mkdir()
        self.profile=self.profile_dir/'Wired connection 1.nmconnection'
        self.profile.write_text('before\n')
        fakebin=self.tmp/'bin'; fakebin.mkdir()
        (fakebin/'sudo').write_text('#!/bin/sh\nexec "$@"\n')
        (fakebin/'restorecon').write_text('#!/bin/sh\nexit 0\n')
        (fakebin/'nmcli').write_text("""#!/bin/sh
set -eu
if [ "$1" = "-g" ] && [ "$2" = "FILENAME,NAME,UUID" ]; then
  printf '%s:%s:%s\\n' "$MDCR_TEST_PROFILE" 'Wired connection 1' '11111111-2222-3333-4444-555555555555'
elif [ "$1" = "connection" ] && [ "$2" = "reload" ]; then
  exit 0
else
  printf '%s\\n' "unexpected nmcli argv: $*" >&2
  exit 64
fi
""")
        for name in ('sudo','restorecon','nmcli'):(fakebin/name).chmod(0o755)
        self.env=os.environ.copy()
        self.env['PATH']=str(fakebin)+os.pathsep+self.env.get('PATH','')
        self.env['MDCR_TEST_PROFILE']=str(self.profile)

    def tearDown(self):
        # Remove only a transaction that proves it belongs to this test profile.
        try:
            marker=NM_TXN/'profile_path'
            if marker.is_file() and marker.read_text().strip()==str(self.profile):
                shutil.rmtree(NM_TXN,ignore_errors=True)
            if NM_PREPARING.exists(): shutil.rmtree(NM_PREPARING,ignore_errors=True)
        finally:
            shutil.rmtree(self.tmp,ignore_errors=True)

    def run_bound(self,text,check=True):
        command=app_bind(text,{'con':'Wired connection 1'})
        result=subprocess.run(command,shell=True,executable='/bin/sh',env=self.env,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=check)
        return command,result

    def test_nmcli_space_bearing_name_backs_up_and_restores_actual_profile(self):
        rows=self.instructions['gen-nmcli-static-ipv4']['preflight']
        show=rows[0]['command']
        self.assertEqual(app_bind(show,{'con':'Wired connection 1'}),
                         "nmcli connection show 'Wired connection 1'")
        preflight=next(row['command'] for row in rows if 'MDCR_NMCLI_PREFLIGHT' in (row.get('command') or ''))
        bound,_=self.run_bound(preflight)
        self.assertTrue(bound.endswith("sudo sh -s -- 'Wired connection 1'"),bound)
        self.assertEqual((NM_TXN/'before').read_text(),'before\n')
        self.assertEqual((NM_TXN/'profile_path').read_text(),str(self.profile)+'\n')
        self.assertNotEqual(NM_TXN.parent,self.profile_dir)
        self.profile.write_text('after\n')
        recover=self.entries['gen-nmcli-static-ipv4']['undo']
        recover_bound,_=self.run_bound(recover)
        self.assertTrue(recover_bound.endswith("sudo sh -s -- 'Wired connection 1'"),recover_bound)
        self.assertEqual(self.profile.read_text(),'before\n')
        self.assertFalse(NM_TXN.exists())


if __name__=='__main__':
    unittest.main()
