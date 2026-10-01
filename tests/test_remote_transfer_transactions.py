#!/usr/bin/env python3
"""Execute the shipped SCP/rsync transaction runbooks through OpenSSH-style argv joining."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def shell_quote(value):
    return "'"+value.replace("'", "'\\''")+"'"


def bind(text, values):
    for key, value in values.items():
        text=text.replace('<'+key+'>', value).replace('{{'+key+'}}', value)
    return text


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
        ssh.write_text("""#!/bin/sh
set -eu
host=$1
shift
[ "$1" = "--" ]
shift
# OpenSSH joins the remaining argv with spaces and the remote login shell
# parses the result. Keep stdin intact so `sh -s` receives the heredoc.
exec /bin/sh -c "$*"
""")
        ssh.chmod(0o755)
        self.env=os.environ.copy()
        self.env['PATH']=str(fakebin)+os.pathsep+self.env.get('PATH','')

    def tearDown(self):
        shutil.rmtree(self.tmp,ignore_errors=True)

    def values(self, target, basename='config.yml'):
        return {
            'remote_identity':'operator@example.test',
            'remote_destination_path':shell_quote(str(target)),
            'remote_source_basename':shell_quote(basename),
            'con':shell_quote('Wired connection 1'),
        }

    def command(self, entry_id, kind, target, basename='config.yml'):
        if kind=='preflight':
            row=next(x for x in self.instructions[entry_id]['preflight'] if x.get('command'))
            raw=row['command']
        elif kind=='recover':
            raw=self.entries[entry_id]['undo']
        elif kind=='finalize':
            verify=self.entries[entry_id]['verify']
            raw=verify[verify.index("printf "):]
        else:
            raise AssertionError(kind)
        return bind(raw,self.values(target,basename))

    def run_command(self, command, check=True):
        return subprocess.run(command,shell=True,executable='/bin/sh',env=self.env,
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              check=check)

    def test_scp_existing_file_is_restored_and_transaction_removed(self):
        target=self.tmp/'config.yml'; target.write_text('before\n')
        self.run_command(self.command('scp-secure-copy','preflight',target))
        self.assertEqual((self.tmp/'config.yml.mdcr-scp.txn/state').read_text(),'present\n')
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

    def test_finalize_discards_backup_and_allows_next_preflight(self):
        target=self.tmp/'tree'; target.mkdir(); (target/'old').write_text('before\n')
        preflight=self.command('rsync-sync-files','preflight',target)
        self.run_command(preflight)
        self.run_command(self.command('rsync-sync-files','finalize',target))
        self.assertFalse(self.tmp.joinpath('tree.mdcr-rsync.txn').exists())
        self.run_command(preflight)


if __name__=='__main__':
    unittest.main()
