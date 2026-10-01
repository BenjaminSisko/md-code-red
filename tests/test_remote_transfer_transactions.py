#!/usr/bin/env python3
"""Execute the shipped SCP/rsync transaction runbooks through OpenSSH-style argv joining."""
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


class RemoteTransferTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content=json.loads((ROOT/'content/commands.json').read_text())
        cls.entries={e['id']:e for e in content['entries']}
        cls.instructions=json.loads((ROOT/'content/instructional.json').read_text())['entries']

    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='mdcr-remote-txn-'))
        fakebin=self.tmp/'bin'; fakebin.mkdir()
        ssh=fakebin/'ssh'
        ssh.write_text("""#!/usr/bin/env python3
import os, signal, subprocess, sys
assert sys.argv[2]=='--'
# OpenSSH joins the remaining argv with spaces and the remote login shell
# parses the result. Pass the pipe through explicitly; a background process
# launched by a POSIX shell would otherwise inherit /dev/null as stdin.
command=' '.join(sys.argv[3:])
pidfile=os.environ.get('MDCR_TEST_REMOTE_PID_FILE')
if pidfile:
    def reset_signals():
        for sig in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM):
            signal.signal(sig,signal.SIG_DFL)
    child=subprocess.Popen(['/bin/sh','-c',command],stdin=sys.stdin,
                           preexec_fn=reset_signals)
    open(pidfile,'w').write(str(child.pid)+'\\n')
    status=child.wait()
    statusfile=os.environ.get('MDCR_TEST_REMOTE_STATUS_FILE')
    if statusfile: open(statusfile,'w').write(str(status)+'\\n')
    raise SystemExit(status)
os.execv('/bin/sh',['sh','-c',command])
""")
        ssh.chmod(0o755)
        stat_cmd=fakebin/'stat'
        stat_cmd.write_text("""#!/usr/bin/env python3
import os, stat, sys, time
fmt=sys.argv[sys.argv.index('-c')+1]
path=os.path.abspath(sys.argv[-1])
st=os.stat(path)
uid=st.st_uid
bad=os.environ.get('MDCR_TEST_BAD_OWNER_PATH','')
if bad and path==os.path.abspath(bad): uid+=1
mode=format(stat.S_IMODE(st.st_mode),'o')
pause=os.environ.get('MDCR_TEST_SIGNAL_TXN','')
if pause and path==os.path.abspath(pause) and fmt=='%u':
    open(os.environ['MDCR_TEST_SIGNAL_READY'],'w').close()
    release=os.environ['MDCR_TEST_SIGNAL_RELEASE']
    while not os.path.exists(release): time.sleep(0.01)
if fmt=='%u:%a': print(str(uid)+':'+mode)
elif fmt=='%u': print(uid)
elif fmt=='%a': print(mode)
else: raise SystemExit(64)
""")
        stat_cmd.chmod(0o755)
        mkdir_cmd=fakebin/'mkdir'
        mkdir_cmd.write_text("""#!/usr/bin/env python3
import os, subprocess, sys
target=os.path.abspath(sys.argv[-1])
race=os.environ.get('MDCR_TEST_RACE_TXN','')
if race and target==os.path.abspath(race):
    subprocess.run(['/bin/mkdir','-m','0700','--',target],check=True)
    raise SystemExit(1)
os.execv('/bin/mkdir',['mkdir']+sys.argv[1:])
""")
        mkdir_cmd.chmod(0o755)
        mv_cmd=fakebin/'mv'
        mv_cmd.write_text("""#!/usr/bin/env python3
import os, sys
args=sys.argv[1:]
words=[word for word in args if word not in ('-T','--')]
race=os.environ.get('MDCR_TEST_RACE_RECOVERY_TARGET','')
outside=os.environ.get('MDCR_TEST_RACE_RECOVERY_OUTSIDE','')
marker=os.environ.get('MDCR_TEST_RACE_RECOVERY_MV_MARKER','')
if race and marker and not os.path.exists(marker) and len(words)==2 and words[0].endswith('/before') and os.path.abspath(words[1])==os.path.abspath(race):
    open(marker,'w').close()
    if not os.path.lexists(race):
        if os.environ.get('MDCR_TEST_RACE_RECOVERY_PLANT_DIRECTORY')=='yes':
            os.mkdir(race)
            open(os.path.join(race,'sentinel'),'w').write('do not touch\\n')
        else:
            os.symlink(outside,race,target_is_directory=True)
if (os.environ.get('MDCR_TEST_RACE_RECOVERY_MV_FAIL_ON_LINK')=='yes' and
        len(words)==2 and race and os.path.abspath(words[1])==os.path.abspath(race) and
        os.path.islink(race)):
    raise SystemExit(1)
real=os.environ['MDCR_TEST_REAL_MV']
os.execv(real,[real]+args)
""")
        mv_cmd.chmod(0o755)
        rm_cmd=fakebin/'rm'
        rm_cmd.write_text("""#!/usr/bin/env python3
import os, subprocess, sys
args=sys.argv[1:]
words=[word for word in args if word not in ('-f','--')]
fail_target=os.environ.get('MDCR_TEST_RACE_RECOVERY_RM_FAIL_TARGET','')
if len(words)==1 and fail_target and os.path.abspath(words[0])==os.path.abspath(fail_target):
    raise SystemExit(1)
result=subprocess.run(['/bin/rm']+args)
race=os.environ.get('MDCR_TEST_RACE_RECOVERY_TARGET','')
outside=os.environ.get('MDCR_TEST_RACE_RECOVERY_OUTSIDE','')
marker=os.environ.get('MDCR_TEST_RACE_RECOVERY_REPLANT','')
always=os.environ.get('MDCR_TEST_RACE_RECOVERY_REPLANT_ALWAYS')=='yes'
limit=int(os.environ.get('MDCR_TEST_RACE_RECOVERY_REPLANT_LIMIT','0') or '0')
countfile=os.environ.get('MDCR_TEST_RACE_RECOVERY_RM_COUNT','')
if result.returncode==0 and len(words)==1 and race and os.path.abspath(words[0])==os.path.abspath(race):
    count=0
    if countfile:
        count=int(open(countfile).read() or '0') if os.path.exists(countfile) else 0
        open(countfile,'w').write(str(count+1))
        count+=1
    if always or (limit and count<=limit) or (marker and not os.path.exists(marker)):
        if marker: open(marker,'w').close()
        if not os.path.lexists(race): os.symlink(outside,race,target_is_directory=True)
raise SystemExit(result.returncode)
""")
        rm_cmd.chmod(0o755)
        self.env=os.environ.copy()
        self.env['PATH']=str(fakebin)+os.pathsep+self.env.get('PATH','')
        self.env['MDCR_TEST_REAL_MV']=shutil.which('gmv') or '/usr/bin/mv'

    def tearDown(self):
        shutil.rmtree(self.tmp,ignore_errors=True)

    def values(self, target, basename='config.yml'):
        source=str(self.tmp/basename)
        return {'source':source,'destination':'operator@example.test:'+str(target)}

    def app_bind(self, text, values):
        proc=subprocess.run(['node',str(BINDER),str(ROOT/'template.html')],
                            input=json.dumps({'text':text,'values':values}),text=True,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        return json.loads(proc.stdout)['bound']

    def app_plan(self, entry_id, values):
        proc=subprocess.run(['node',str(BINDER),str(ROOT/'template.html')],
                            input=json.dumps({'entry_id':entry_id,'version':'8','values':values}),
                            text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        return json.loads(proc.stdout)['plan']

    def command(self, entry_id, kind, target, basename='config.yml'):
        plan=self.app_plan(entry_id,self.values(target,basename))
        key={'preflight':'preflight','recover':'recover','finalize':'verify'}.get(kind)
        if key is None: raise AssertionError(kind)
        command=plan['copy'][key]
        if not command: raise AssertionError('operationalPlan returned no runnable '+kind)
        return command

    def run_command(self, command, check=True, timeout=None):
        return subprocess.run(command,shell=True,executable='/bin/sh',env=self.env,
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              check=check,timeout=timeout)

    def start_command(self, command):
        return subprocess.Popen(command,shell=True,executable='/bin/sh',env=self.env,
                                text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    def test_scp_existing_file_is_restored_and_transaction_removed(self):
        target=self.tmp/'config.yml'; target.write_text('before\n')
        self.run_command(self.command('scp-secure-copy','preflight',target))
        txn=self.tmp/'config.yml.mdcr-scp.txn'
        self.assertEqual((txn/'state').read_text(),'present\n')
        self.assertEqual(txn.stat().st_mode & 0o777,0o700)
        target.write_text('after\n')
        self.run_command(self.command('scp-secure-copy','recover',target))
        self.assertEqual(target.read_text(),'before\n')
        self.assertFalse(self.tmp.joinpath('config.yml.mdcr-scp.txn').exists())

    def test_scp_directory_destination_resolves_source_basename(self):
        directory=self.tmp/'remote'; directory.mkdir()
        target=directory/'config.yml'; target.write_text('before\n')
        self.run_command(self.command('scp-secure-copy','preflight',directory))
        target.write_text('after\n')
        self.run_command(self.command('scp-secure-copy','recover',directory))
        self.assertEqual(target.read_text(),'before\n')

    def test_absent_scp_target_is_removed_only_with_absent_state(self):
        target=self.tmp/'new.yml'
        self.run_command(self.command('scp-secure-copy','preflight',target))
        self.assertEqual((self.tmp/'new.yml.mdcr-scp.txn/state').read_text(),'absent\n')
        target.write_text('new\n')
        self.run_command(self.command('scp-secure-copy','recover',target))
        self.assertFalse(target.exists())
        self.assertFalse(self.tmp.joinpath('new.yml.mdcr-scp.txn').exists())

    def test_stale_transaction_is_refused_without_replacing_backup(self):
        target=self.tmp/'config.yml'; target.write_text('first\n')
        command=self.command('scp-secure-copy','preflight',target)
        self.run_command(command)
        backup=self.tmp/'config.yml.mdcr-scp.txn/before'
        self.assertEqual(backup.read_text(),'first\n')
        target.write_text('changed-before-second-preflight\n')
        second=self.run_command(command,check=False)
        self.assertNotEqual(second.returncode,0)
        self.assertIn('unfinished SCP transaction',second.stderr)
        self.assertEqual(backup.read_text(),'first\n')

    def test_rsync_tree_is_restored_and_transaction_removed(self):
        target=self.tmp/'tree'; target.mkdir(); (target/'old').write_text('before\n')
        self.run_command(self.command('rsync-sync-files','preflight',target))
        (target/'old').write_text('after\n'); (target/'new').write_text('new\n')
        self.run_command(self.command('rsync-sync-files','recover',target))
        self.assertEqual((target/'old').read_text(),'before\n')
        self.assertFalse((target/'new').exists())
        self.assertFalse(self.tmp.joinpath('tree.mdcr-rsync.txn').exists())

    def test_finalize_discards_each_backup_and_allows_next_preflight(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                target=self.tmp/f'{prefix}-finalize-positive'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                preflight=self.command(entry_id,'preflight',target)
                self.run_command(preflight)
                txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                self.run_command(self.command(entry_id,'finalize',target))
                self.assertFalse(txn.exists())
                self.run_command(preflight)

    def test_scp_symlinked_file_is_refused_before_backup(self):
        real=self.tmp/'real.conf'; real.write_text('before\n')
        target=self.tmp/'link.conf'; target.symlink_to(real.name)
        result=self.run_command(self.command('scp-secure-copy','preflight',target),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('symlinked scp',result.stderr)
        self.assertFalse(self.tmp.joinpath('link.conf.mdcr-scp.txn').exists())
        self.assertEqual(real.read_text(),'before\n')

    def test_rsync_symlinked_directory_is_refused_before_capacity_check(self):
        real=self.tmp/'real-tree'; real.mkdir(); (real/'old').write_text('before\n')
        target=self.tmp/'link-tree'; target.symlink_to(real.name,target_is_directory=True)
        result=self.run_command(self.command('rsync-sync-files','preflight',target),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('symlinked rsync',result.stderr)
        self.assertFalse(self.tmp.joinpath('link-tree.mdcr-rsync.txn').exists())
        self.assertEqual((real/'old').read_text(),'before\n')

    def test_recovery_and_finalize_refuse_each_forged_owner_path(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','SCP',False),('rsync-sync-files','RSYNC',True)):
            for action in ('recover','finalize'):
                for forged,diagnostic in (
                        ('txn',f'no trusted {prefix} transaction for'),
                        ('state',f'no trusted {prefix} transaction state for')):
                    with self.subTest(entry=entry_id,action=action,forged=forged):
                        stem=f'{prefix.lower()}-{action}-{forged}'
                        target=self.tmp/stem
                        if is_dir:
                            target.mkdir(); (target/'old').write_text('before\n')
                        else:
                            target.write_text('before\n')
                        self.run_command(self.command(entry_id,'preflight',target,stem+'.src'))
                        txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                        self.env['MDCR_TEST_BAD_OWNER_PATH']=str(txn if forged=='txn' else txn/'state')
                        result=self.run_command(self.command(entry_id,action,target,stem+'.src'),check=False)
                        self.assertNotEqual(result.returncode,0)
                        self.assertIn(diagnostic,result.stderr)
                        self.assertTrue(txn.exists())
                        self.env.pop('MDCR_TEST_BAD_OWNER_PATH',None)

    def test_preflight_refuses_each_forged_owner_path_with_specific_diagnostic(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','SCP',False),('rsync-sync-files','RSYNC',True)):
            for forged,diagnostic in (
                    ('txn',f'no trusted {prefix} transaction for'),
                    ('state',f'untrusted {prefix} transaction state')):
                with self.subTest(entry=entry_id,forged=forged):
                    stem=f'{prefix.lower()}-preflight-{forged}'
                    target=self.tmp/stem
                    if is_dir:
                        target.mkdir(); (target/'old').write_text('before\n')
                    else:
                        target.write_text('before\n')
                    txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                    self.env['MDCR_TEST_BAD_OWNER_PATH']=str(txn if forged=='txn' else txn/'state')
                    result=self.run_command(self.command(entry_id,'preflight',target,stem+'.src'),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(diagnostic,result.stderr)
                    self.assertFalse(txn.exists(),'EXIT cleanup must remove the rejected transaction')
                    self.env.pop('MDCR_TEST_BAD_OWNER_PATH',None)

    def test_recovery_and_finalize_refuse_mode_0755_transactions(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','SCP',False),('rsync-sync-files','RSYNC',True)):
            for action in ('recover','finalize'):
                with self.subTest(entry=entry_id,action=action):
                    target=self.tmp/f'{prefix.lower()}-{action}-bad-mode'
                    if is_dir:
                        target.mkdir(); (target/'old').write_text('before\n')
                    else:
                        target.write_text('before\n')
                    self.run_command(self.command(entry_id,'preflight',target))
                    txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                    txn.chmod(0o755)
                    result=self.run_command(self.command(entry_id,action,target),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(f'no trusted {prefix} transaction for',result.stderr)
                    self.assertTrue(txn.exists())

    def test_missing_state_and_backup_have_specific_recovery_diagnostics(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','SCP',False),('rsync-sync-files','RSYNC',True)):
            for action in ('recover','finalize'):
                with self.subTest(entry=entry_id,action=action,missing='state'):
                    target=self.tmp/f'{prefix.lower()}-{action}-missing-state'
                    if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                    else: target.write_text('before\n')
                    self.run_command(self.command(entry_id,'preflight',target))
                    txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                    (txn/'state').unlink()
                    result=self.run_command(self.command(entry_id,action,target),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(f'no trusted {prefix} transaction state for',result.stderr)
                    self.assertTrue(txn.exists())
            with self.subTest(entry=entry_id,missing='before'):
                target=self.tmp/f'{prefix.lower()}-missing-before'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                self.run_command(self.command(entry_id,'preflight',target))
                txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                if (txn/'before').is_dir(): shutil.rmtree(txn/'before')
                else: (txn/'before').unlink()
                result=self.run_command(self.command(entry_id,'recover',target),check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('trusted saved',result.stderr)
                self.assertTrue(txn.exists())

    def test_recovery_refuses_each_preexisting_swap_shape(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','SCP',False),('rsync-sync-files','RSYNC',True)):
            for swap_is_dir in (False,True):
                with self.subTest(entry=entry_id,swap='directory' if swap_is_dir else 'file'):
                    target=self.tmp/f'{prefix.lower()}-swap-{int(swap_is_dir)}'
                    if is_dir:
                        target.mkdir(); (target/'old').write_text('before\n')
                    else:
                        target.write_text('before\n')
                    self.run_command(self.command(entry_id,'preflight',target))
                    txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                    after=txn/'after'
                    if swap_is_dir: after.mkdir()
                    else: after.write_text('untrusted\n')
                    result=self.run_command(self.command(entry_id,'recover',target),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('recovery swap already exists',result.stderr)
                    self.assertTrue(target.exists())
                    self.assertTrue((txn/'before').exists())

    def test_foreign_owned_saved_content_inside_trusted_transaction_is_recoverable(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','SCP',False),('rsync-sync-files','RSYNC',True)):
            with self.subTest(entry=entry_id):
                target=self.tmp/f'{prefix.lower()}-foreign-backup'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                txn=Path(str(target)+f'.mdcr-{prefix.lower()}.txn')
                self.env['MDCR_TEST_BAD_OWNER_PATH']=str(txn/'before')
                self.run_command(self.command(entry_id,'preflight',target))
                if is_dir: (target/'old').write_text('after\n')
                else: target.write_text('after\n')
                self.run_command(self.command(entry_id,'recover',target))
                if is_dir: self.assertEqual((target/'old').read_text(),'before\n')
                else: self.assertEqual(target.read_text(),'before\n')
                self.assertFalse(txn.exists())
                self.env.pop('MDCR_TEST_BAD_OWNER_PATH',None)

    def test_atomic_transaction_mkdir_refuses_midflight_race(self):
        target=self.tmp/'config.yml'; target.write_text('before\n')
        txn=self.tmp/'config.yml.mdcr-scp.txn'
        self.env['MDCR_TEST_RACE_TXN']=str(txn)
        result=self.run_command(self.command('scp-secure-copy','preflight',target),check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(txn.is_dir())
        self.assertFalse((txn/'before').exists())

    def test_each_preflight_refuses_writable_parent_without_sticky_bit(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                shared=self.tmp/f'{prefix}-shared'; shared.mkdir(mode=0o777); shared.chmod(0o777)
                target=shared/f'{prefix}-target'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                result=self.run_command(self.command(entry_id,'preflight',target),check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('writable without sticky protection',result.stderr)
                self.assertFalse(Path(str(target)+f'.mdcr-{prefix}.txn').exists())

    def test_each_preflight_refuses_symlinked_parent_explicitly(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                real=self.tmp/f'{prefix}-real-parent'; real.mkdir()
                link=self.tmp/f'{prefix}-linked-parent'; link.symlink_to(real.name,target_is_directory=True)
                target=link/f'{prefix}-target'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                result=self.run_command(self.command(entry_id,'preflight',target),check=False)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('symlinked transaction parent',result.stderr)
                self.assertFalse(Path(str(real/(f'{prefix}-target'))+f'.mdcr-{prefix}.txn').exists())

    def test_recovery_and_finalize_refuse_symlinked_destination_without_touching_outside(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            for action in ('recover','finalize'):
                with self.subTest(entry=entry_id,action=action):
                    target=self.tmp/f'{prefix}-{action}-symlink-target'
                    if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                    else: target.write_text('before\n')
                    self.run_command(self.command(entry_id,'preflight',target))
                    txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                    if target.is_dir(): shutil.rmtree(target)
                    else: target.unlink()
                    outside=self.tmp/f'{prefix}-{action}-outside'; outside.mkdir()
                    sentinel=outside/'sentinel'; sentinel.write_text('do not touch\n')
                    target.symlink_to(outside,target_is_directory=True)
                    result=self.run_command(self.command(entry_id,action,target),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(f'symlinked {prefix}',result.stderr.lower())
                    self.assertEqual(sentinel.read_text(),'do not touch\n')
                    self.assertEqual(sorted(p.name for p in outside.iterdir()),['sentinel'])
                    self.assertTrue(txn.exists())

    def test_recovery_and_finalize_refuse_parent_that_becomes_unsafe(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            for action in ('recover','finalize'):
                with self.subTest(entry=entry_id,action=action):
                    parent=self.tmp/f'{prefix}-{action}-unsafe-parent'; parent.mkdir(mode=0o700)
                    target=parent/'target'
                    if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                    else: target.write_text('before\n')
                    self.run_command(self.command(entry_id,'preflight',target))
                    txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                    parent.chmod(0o777)
                    result=self.run_command(self.command(entry_id,action,target),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('writable without sticky protection',result.stderr)
                    self.assertTrue(txn.exists())

    def test_recovery_and_finalize_refuse_parent_that_becomes_a_symlink(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            for action in ('recover','finalize'):
                with self.subTest(entry=entry_id,action=action):
                    parent=self.tmp/f'{prefix}-{action}-parent'; parent.mkdir(mode=0o700)
                    target=parent/'target'
                    if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                    else: target.write_text('before\n')
                    self.run_command(self.command(entry_id,'preflight',target))
                    moved=self.tmp/f'{prefix}-{action}-moved-parent'
                    parent.rename(moved)
                    parent.symlink_to(moved.name,target_is_directory=True)
                    linked_target=parent/'target'
                    txn=Path(str(linked_target)+f'.mdcr-{prefix}.txn')
                    result=self.run_command(self.command(entry_id,action,linked_target),check=False)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('symlinked transaction parent',result.stderr)
                    self.assertTrue(txn.exists())

    def test_recovery_replaces_a_raced_symlink_instead_of_following_it(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                target=self.tmp/f'{prefix}-race-target'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                self.run_command(self.command(entry_id,'preflight',target))
                if is_dir: (target/'old').write_text('after\n')
                else: target.write_text('after\n')
                outside=self.tmp/f'{prefix}-outside'; outside.mkdir()
                sentinel=outside/'sentinel'; sentinel.write_text('do not touch\n')
                marker=self.tmp/f'{prefix}-mv-race.marker'
                self.env['MDCR_TEST_RACE_RECOVERY_TARGET']=str(target)
                self.env['MDCR_TEST_RACE_RECOVERY_OUTSIDE']=str(outside)
                self.env['MDCR_TEST_RACE_RECOVERY_MV_MARKER']=str(marker)
                result=self.run_command(self.command(entry_id,'recover',target),check=False)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertFalse(target.is_symlink())
                self.assertEqual(sentinel.read_text(),'do not touch\n')
                self.assertEqual(sorted(p.name for p in outside.iterdir()),['sentinel'])
                if is_dir: self.assertEqual((target/'old').read_text(),'before\n')
                else: self.assertEqual(target.read_text(),'before\n')
                self.env.pop('MDCR_TEST_RACE_RECOVERY_TARGET',None)
                self.env.pop('MDCR_TEST_RACE_RECOVERY_OUTSIDE',None)
                self.env.pop('MDCR_TEST_RACE_RECOVERY_MV_MARKER',None)

    def test_rsync_recovery_retries_when_symlink_is_replanted_after_removal(self):
        target=self.tmp/'rsync-replant-target'
        target.mkdir(); (target/'old').write_text('before\n')
        self.run_command(self.command('rsync-sync-files','preflight',target))
        (target/'old').write_text('after\n')
        outside=self.tmp/'rsync-replant-outside'; outside.mkdir()
        sentinel=outside/'sentinel'; sentinel.write_text('do not touch\n')
        marker=self.tmp/'rsync-replant.marker'
        mv_marker=self.tmp/'rsync-replant-mv.marker'
        self.env.update({
            'MDCR_TEST_RACE_RECOVERY_TARGET':str(target),
            'MDCR_TEST_RACE_RECOVERY_OUTSIDE':str(outside),
            'MDCR_TEST_RACE_RECOVERY_REPLANT':str(marker),
            'MDCR_TEST_RACE_RECOVERY_MV_MARKER':str(mv_marker),
        })
        result=self.run_command(self.command('rsync-sync-files','recover',target),check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(marker.exists(),'rm wrapper did not replant the symlink')
        self.assertFalse(target.is_symlink())
        self.assertEqual((target/'old').read_text(),'before\n')
        self.assertEqual(sentinel.read_text(),'do not touch\n')
        self.assertEqual(sorted(p.name for p in outside.iterdir()),['sentinel'])
        for key in ('MDCR_TEST_RACE_RECOVERY_TARGET','MDCR_TEST_RACE_RECOVERY_OUTSIDE','MDCR_TEST_RACE_RECOVERY_REPLANT','MDCR_TEST_RACE_RECOVERY_MV_MARKER'):
            self.env.pop(key,None)

    def test_rsync_recovery_persistent_replant_is_bounded_and_preserves_transaction(self):
        target=self.tmp/'rsync-persistent-replant-target'
        target.mkdir(); (target/'old').write_text('before\n')
        self.run_command(self.command('rsync-sync-files','preflight',target))
        txn=Path(str(target)+'.mdcr-rsync.txn')
        (target/'old').write_text('after\n')
        outside=self.tmp/'rsync-persistent-replant-outside'; outside.mkdir()
        sentinel=outside/'sentinel'; sentinel.write_text('do not touch\n')
        mv_marker=self.tmp/'rsync-persistent-replant-mv.marker'
        countfile=self.tmp/'rsync-persistent-replant-rm.count'
        self.env.update({
            'MDCR_TEST_RACE_RECOVERY_TARGET':str(target),
            'MDCR_TEST_RACE_RECOVERY_OUTSIDE':str(outside),
            'MDCR_TEST_RACE_RECOVERY_REPLANT_ALWAYS':'yes',
            'MDCR_TEST_RACE_RECOVERY_RM_COUNT':str(countfile),
            'MDCR_TEST_RACE_RECOVERY_MV_MARKER':str(mv_marker),
        })
        result=self.run_command(self.command('rsync-sync-files','recover',target),
                                check=False,timeout=5)
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(),outside.resolve())
        self.assertEqual(sentinel.read_text(),'do not touch\n')
        self.assertEqual(sorted(p.name for p in outside.iterdir()),['sentinel'])
        self.assertEqual(int(countfile.read_text()),6)
        self.assertEqual((txn/'state').read_text(),'present\n')
        self.assertTrue((txn/'before').is_dir())
        self.assertTrue((txn/'after').is_dir())
        for key in ('MDCR_TEST_RACE_RECOVERY_TARGET','MDCR_TEST_RACE_RECOVERY_OUTSIDE',
                    'MDCR_TEST_RACE_RECOVERY_REPLANT_ALWAYS','MDCR_TEST_RACE_RECOVERY_RM_COUNT',
                    'MDCR_TEST_RACE_RECOVERY_MV_MARKER'):
            self.env.pop(key,None)

    def test_recovery_fails_closed_when_raced_link_cannot_be_removed(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                parent=self.tmp/f'{prefix}-sticky-parent'; parent.mkdir(mode=0o1777); parent.chmod(0o1777)
                target=parent/'target'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                self.run_command(self.command(entry_id,'preflight',target))
                txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                if is_dir: (target/'old').write_text('after\n')
                else: target.write_text('after\n')
                outside=self.tmp/f'{prefix}-rm-fail-outside'; outside.mkdir()
                sentinel=outside/'sentinel'; sentinel.write_text('do not touch\n')
                marker=self.tmp/f'{prefix}-rm-fail.marker'
                self.env.update({
                    'MDCR_TEST_RACE_RECOVERY_TARGET':str(target),
                    'MDCR_TEST_RACE_RECOVERY_OUTSIDE':str(outside),
                    'MDCR_TEST_RACE_RECOVERY_MV_MARKER':str(marker),
                    'MDCR_TEST_RACE_RECOVERY_MV_FAIL_ON_LINK':'yes',
                    'MDCR_TEST_RACE_RECOVERY_RM_FAIL_TARGET':str(target),
                })
                result=self.run_command(self.command(entry_id,'recover',target),check=False,timeout=5)
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertTrue(marker.exists(),'mv wrapper did not plant the raced link')
                self.assertTrue(target.is_symlink())
                self.assertEqual(target.resolve(),outside.resolve())
                self.assertEqual(sorted(p.name for p in outside.iterdir()),['sentinel'])
                self.assertEqual((txn/'state').read_text(),'present\n')
                self.assertTrue((txn/'before').exists())
                self.assertTrue((txn/'after').exists())
                for key in ('MDCR_TEST_RACE_RECOVERY_TARGET','MDCR_TEST_RACE_RECOVERY_OUTSIDE',
                            'MDCR_TEST_RACE_RECOVERY_MV_MARKER','MDCR_TEST_RACE_RECOVERY_MV_FAIL_ON_LINK',
                            'MDCR_TEST_RACE_RECOVERY_RM_FAIL_TARGET'):
                    self.env.pop(key,None)

    def test_recovery_fails_closed_when_non_link_directory_is_planted(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                target=self.tmp/f'{prefix}-planted-directory-target'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                self.run_command(self.command(entry_id,'preflight',target))
                txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                if is_dir: (target/'old').write_text('after\n')
                else: target.write_text('after\n')
                marker=self.tmp/f'{prefix}-planted-directory.marker'
                self.env.update({
                    'MDCR_TEST_RACE_RECOVERY_TARGET':str(target),
                    'MDCR_TEST_RACE_RECOVERY_OUTSIDE':str(self.tmp/'unused-outside'),
                    'MDCR_TEST_RACE_RECOVERY_MV_MARKER':str(marker),
                    'MDCR_TEST_RACE_RECOVERY_PLANT_DIRECTORY':'yes',
                })
                result=self.run_command(self.command(entry_id,'recover',target),check=False,timeout=5)
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertTrue(marker.exists(),'mv wrapper did not plant the directory')
                self.assertTrue(target.is_dir())
                self.assertFalse(target.is_symlink())
                self.assertEqual(sorted(p.name for p in target.iterdir()),['sentinel'])
                self.assertEqual((txn/'state').read_text(),'present\n')
                self.assertTrue((txn/'before').exists())
                self.assertTrue((txn/'after').exists())
                for key in ('MDCR_TEST_RACE_RECOVERY_TARGET','MDCR_TEST_RACE_RECOVERY_OUTSIDE',
                            'MDCR_TEST_RACE_RECOVERY_MV_MARKER','MDCR_TEST_RACE_RECOVERY_PLANT_DIRECTORY'):
                    self.env.pop(key,None)

    def test_recovery_exhaustion_restores_after_but_preserves_rollback(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            with self.subTest(entry=entry_id):
                target=self.tmp/f'{prefix}-three-replants-target'
                if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                else: target.write_text('before\n')
                self.run_command(self.command(entry_id,'preflight',target))
                txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                if is_dir: (target/'old').write_text('after\n')
                else: target.write_text('after\n')
                outside=self.tmp/f'{prefix}-three-replants-outside'; outside.mkdir()
                (outside/'sentinel').write_text('do not touch\n')
                marker=self.tmp/f'{prefix}-three-replants.marker'
                countfile=self.tmp/f'{prefix}-three-replants.count'
                self.env.update({
                    'MDCR_TEST_RACE_RECOVERY_TARGET':str(target),
                    'MDCR_TEST_RACE_RECOVERY_OUTSIDE':str(outside),
                    'MDCR_TEST_RACE_RECOVERY_MV_MARKER':str(marker),
                    'MDCR_TEST_RACE_RECOVERY_MV_FAIL_ON_LINK':'yes',
                    'MDCR_TEST_RACE_RECOVERY_REPLANT_LIMIT':'3',
                    'MDCR_TEST_RACE_RECOVERY_RM_COUNT':str(countfile),
                })
                result=self.run_command(self.command(entry_id,'recover',target),check=False,timeout=5)
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertEqual(int(countfile.read_text()),4)
                self.assertFalse(target.is_symlink())
                if is_dir: self.assertEqual((target/'old').read_text(),'after\n')
                else: self.assertEqual(target.read_text(),'after\n')
                self.assertEqual(sorted(p.name for p in outside.iterdir()),['sentinel'])
                self.assertEqual((txn/'state').read_text(),'present\n')
                self.assertTrue((txn/'before').exists())
                self.assertFalse((txn/'after').exists(),'current state should have been moved back to the target')
                for key in ('MDCR_TEST_RACE_RECOVERY_TARGET','MDCR_TEST_RACE_RECOVERY_OUTSIDE',
                            'MDCR_TEST_RACE_RECOVERY_MV_MARKER','MDCR_TEST_RACE_RECOVERY_MV_FAIL_ON_LINK',
                            'MDCR_TEST_RACE_RECOVERY_REPLANT_LIMIT','MDCR_TEST_RACE_RECOVERY_RM_COUNT'):
                    self.env.pop(key,None)

    def test_each_signal_cleans_each_remote_transaction_and_fails_pipeline(self):
        for entry_id,prefix,is_dir in (
                ('scp-secure-copy','scp',False),('rsync-sync-files','rsync',True)):
            for sig in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM):
                with self.subTest(entry=entry_id,signal=sig.name):
                    stem=f'{prefix}-{sig.name.lower()}'
                    target=self.tmp/stem
                    if is_dir: target.mkdir(); (target/'old').write_text('before\n')
                    else: target.write_text('before\n')
                    txn=Path(str(target)+f'.mdcr-{prefix}.txn')
                    ready=self.tmp/f'{stem}.ready'; release=self.tmp/f'{stem}.release'; pidfile=self.tmp/f'{stem}.pid'; statusfile=self.tmp/f'{stem}.status'
                    self.env.update({
                        'MDCR_TEST_SIGNAL_TXN':str(txn/'state'),
                        'MDCR_TEST_SIGNAL_READY':str(ready),
                        'MDCR_TEST_SIGNAL_RELEASE':str(release),
                        'MDCR_TEST_REMOTE_PID_FILE':str(pidfile),
                        'MDCR_TEST_REMOTE_STATUS_FILE':str(statusfile),
                    })
                    command=self.command(entry_id,'preflight',target,stem+'.src')
                    self.assertIn("'trap '\"'\"'exit 1'\"'\"' HUP INT TERM'",command)
                    self.assertIn('trap cleanup EXIT',command)
                    proc=self.start_command(command)
                    deadline=time.monotonic()+5
                    while (not ready.exists() or not pidfile.exists()) and proc.poll() is None and time.monotonic()<deadline:
                        time.sleep(0.01)
                    self.assertTrue(ready.exists(),'preflight never reached final state validation')
                    self.assertTrue(pidfile.exists(),'ssh wrapper did not record the remote shell pid')
                    os.kill(int(pidfile.read_text().strip()),sig)
                    release.touch()
                    _out,err=proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode,1,err)
                    self.assertEqual(statusfile.read_text().strip(),'1')
                    self.assertFalse(txn.exists())
                    for key in ('MDCR_TEST_SIGNAL_TXN','MDCR_TEST_SIGNAL_READY','MDCR_TEST_SIGNAL_RELEASE','MDCR_TEST_REMOTE_PID_FILE','MDCR_TEST_REMOTE_STATUS_FILE'):
                        self.env.pop(key,None)


if __name__=='__main__':
    unittest.main()
