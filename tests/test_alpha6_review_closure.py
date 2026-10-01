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
        for broken in (
            {'name':'output','type':'path','required':True,'write_target':'yes'},
            {'name':'output','type':'comment','required':True,'write_target':True},
        ):
            errors=schema.spec_fields_errors('spec',[broken],set())
            self.assertTrue(any('write_target' in e for e in errors),errors)

if __name__=='__main__':
    unittest.main()
