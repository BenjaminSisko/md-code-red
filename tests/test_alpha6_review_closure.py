#!/usr/bin/env python3
"""Runtime closure checks for findings from the independent alpha.6 review."""
import json
import os
import shutil
import subprocess
import unittest
from extract import schema

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Alpha6ReviewClosureTests(unittest.TestCase):
    def test_runtime_remote_write_and_optional_subset_contracts(self):
        node=shutil.which('node')
        self.assertIsNotNone(node,'Node is required to execute the shipped assembler')
        proc=subprocess.run([node,os.path.join(ROOT,'tests','test_alpha6_review_closure.js'),os.path.join(ROOT,'template.html')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            report=json.loads(proc.stdout.decode('utf-8'))
        except ValueError:
            self.fail(proc.stderr.decode('utf-8','replace'))
        self.assertGreaterEqual(report['checks'],23)
        self.assertEqual(report['failures'],[],report['failures'])
        self.assertEqual(proc.returncode,0)

    def test_write_target_schema_is_closed(self):
        names=set()
        valid={'name':'output','type':'path','required':True,'write_target':True}
        self.assertEqual(schema.spec_fields_errors('spec',[valid],names),[])
        remote={'name':'destination','type':'remote_path','required':True,'write_target':True}
        self.assertEqual(schema.spec_fields_errors('spec',[remote],set()),[])
        for broken in (
            {'name':'output','type':'path','required':True,'write_target':'yes'},
            {'name':'output','type':'comment','required':True,'write_target':True},
        ):
            errors=schema.spec_fields_errors('spec',[broken],set())
            self.assertTrue(any('write_target' in e for e in errors),errors)

    def test_state_changing_entries_are_not_green(self):
        with open(os.path.join(ROOT,'content','commands.json'),encoding='utf-8') as fh:
            entries={e['id']:e for e in json.load(fh)['entries']}
        state_changing={
            'cp-copy','mkdir-create-directory','ln-links','git-clone','gen-git-clone',
            'git-add','git-commit','git-switch-branch','git-stash','git-tag','git-bisect','a-fetch',
        }
        self.assertEqual({eid:entries[eid]['blast'] for eid in state_changing},
                         {eid:'yellow' for eid in state_changing})

        with open(os.path.join(ROOT,'content','instructional.json'),encoding='utf-8') as fh:
            instructions=json.load(fh)['entries']
        for eid,entry in entries.items():
            if entry['blast']=='green':
                continue
            for name,field in instructions.get(eid,{}).get('fields',{}).items():
                self.assertNotIn('read-only',field.get('consequence','').lower(),(eid,name))

    def test_purpose_specific_field_types_replace_firewalld_service_errors(self):
        with open(os.path.join(ROOT,'content','commands.json'),encoding='utf-8') as fh:
            entries={e['id']:e for e in json.load(fh)['entries']}
        expected={
            ('gen-nmcli-static-ipv4','con'):'connection_name',
            ('gen-vgcreate-new-vg','name'):'lvm_name',
            ('gen-lvcreate-new-lv','name'):'lvm_name',
            ('gen-lvcreate-new-lv','vg'):'lvm_name',
            ('gen-podman-stop','container'):'container_name',
            ('gen-git-clone','repository'):'git_repository',
            ('gen-git-clone','directory'):'directory_name',
            ('gen-systemd-unit','description'):'unit_description',
            ('gen-chronyd-one-shot-check','directive'):'chrony_directive',
        }
        for (eid,name),want in expected.items():
            field=next(f for f in entries[eid]['fields'] if f['name']==name)
            self.assertEqual(field['type'],want,(eid,name))

if __name__=='__main__':
    unittest.main()
