#!/usr/bin/env python3
"""Regression coverage for the guided Linux-instruction layer."""
import copy
import json
import os
import re
import sys
import unittest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'extract'))
import schema


def load(name):
    with open(os.path.join(ROOT,'content',name),encoding='utf-8') as fh:
        return json.load(fh)


class InstructionalSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.commands=load('commands.json')['entries']
        cls.data=load('instructional.json')
        with open(os.path.join(ROOT,'template.html'),encoding='utf-8') as fh:
            cls.template=fh.read()

    def test_every_generator_and_field_has_instructional_metadata(self):
        generators={e['id']:e for e in self.commands if 'template' in e}
        self.assertEqual(set(generators),set(self.data['entries']))
        self.assertEqual(sum(len(e['fields']) for e in generators.values()),
                         sum(len(r['fields']) for r in self.data['entries'].values()))
        self.assertEqual([],schema.instructional_errors(self.data,self.commands))

    def test_missing_metadata_fails_closed(self):
        broken=copy.deepcopy(self.data)
        eid=sorted(broken['entries'])[0]
        name=sorted(broken['entries'][eid]['fields'])[0]
        del broken['entries'][eid]['fields'][name]['meaning']
        errors=schema.instructional_errors(broken,self.commands)
        self.assertTrue(any('missing meaning' in e for e in errors),errors)

    def test_null_discovery_is_explicit_not_omitted(self):
        for eid,row in self.data['entries'].items():
            for name,meta in row['fields'].items():
                self.assertIn('discovery_command',meta,(eid,name))
                self.assertTrue(meta['discovery_command'] is None or isinstance(meta['discovery_command'],str))

    def test_learning_paths_resolve_and_have_checks(self):
        ids={e['id'] for e in self.commands if 'template' in e}
        for path in self.data['learning_paths']:
            self.assertTrue(path['entry_ids'])
            self.assertTrue(set(path['entry_ids'])<=ids)
            self.assertTrue(path['check']['question'])
            self.assertTrue(path['check']['answer'])

    def test_template_has_instructional_workflows(self):
        markers=(
            'function operationalPlan(', 'data-plan-step=', 'Preflight', 'Recover',
            'function bindInstruction(', 'RHEL release comparison', 'Read next:',
            'Man section ', 'data-learn-entry=', 'Comprehension check',
            'if(name==="stig")', 'Recovery not proven', 'State-changing operation.'
        )
        for marker in markers:
            self.assertIn(marker,self.template,marker)

    def test_stig_rail_no_longer_uses_placeholder_copy(self):
        self.assertNotIn('This rail lands with its own task: STIG search',self.template)
        self.assertIn('el("palette-input").value="STIG"',self.template)

    def assert_keyboard_contract(self,template):
        event_literals=list(re.finditer(
            r'([\'\"`])(keydown|keyup|keypress)\1',template))
        self.assertEqual([match.group(2) for match in event_literals],['keydown'],
                         'the complete shell must have one literal keydown registration and no keyup/keypress registration')
        self.assertEqual(template.count('document.addEventListener("keydown"'),1)
        self.assertNotRegex(template,r'\.onkey(?:down|up|press)\s*=')
        self.assertNotRegex(template,r'\[\s*([\'\"`])onkey(?:down|up|press)\1\s*\]\s*=')
        self.assertNotRegex(
            template,
            r'addEventListener(?:\.|\[\s*([\'\"`]))(?:call|apply)',
            'keyboard handlers may not be registered through Function.call/apply',
        )
        start=template.index('document.addEventListener("keydown"')
        end=template.index('/* ============ boot ============ */',start)
        handler=template[start:end]
        for forbidden in (
            'data-action','data-plan-step','doCopyPlanStep(','doCopy(',
            'copyText(','dispatchEvent','MouseEvent','.click(',
            '["click"]',"['click']",
        ):
            self.assertNotIn(forbidden,handler,
                             'native buttons must keep browser Enter/Space semantics: '+forbidden)
        keymap=template[
            template.index('var KEYMAP=['):template.index('];',template.index('var KEYMAP=['))+2
        ]
        key_values=[]
        for match in re.finditer(r'keys:\[([^\]]*)\]',keymap):
            key_values.extend(value for _quote,value in re.findall(r'([\'\"])(.*?)\1',match.group(1)))
        self.assertNotIn('Enter',key_values,'Enter must remain native outside contextual overlay handling')
        self.assertNotIn(' ',key_values,'Space must remain native outside contextual gutter handling')

    def test_native_copy_buttons_have_no_keyboard_retrigger_handler(self):
        self.assert_keyboard_contract(self.template)
        boot='/* ============ boot ============ */'
        listener='document.addEventListener("keydown",function(ev){'
        keymap='var KEYMAP=['
        mutants={
            'late keypress':self.template.replace(
                boot,'window.addEventListener("keypress",function(e){e.target.dispatchEvent(new MouseEvent("click"));});\n'+boot),
            'template-literal keyup':self.template.replace(
                boot,'window.addEventListener(`keyup`,function(e){e.target.click();});\n'+boot),
            'computed listener':self.template.replace(
                boot,'window["addEventListener"]("keyup",function(e){e.target.click();});\n'+boot),
            'Function.apply listener':self.template.replace(
                boot,'window.addEventListener.apply(window,["keyup",function(e){e.target.click();}]);\n'+boot),
            'dispatch in approved handler':self.template.replace(
                listener,listener+'\n  ev.target.dispatchEvent(new MouseEvent("click"));',1),
            'Enter in KEYMAP':self.template.replace(
                keymap,keymap+'\n  {id:"bad-enter",keys:["Enter"],mods:"none",whenTyping:true,run:function(e){e.target.dispatchEvent(new MouseEvent("click"));}},',1),
        }
        for name,mutant in mutants.items():
            with self.subTest(mutant=name),self.assertRaises(AssertionError):
                self.assert_keyboard_contract(mutant)

    def test_generator_plan_placeholders_are_bindable_and_broadly_detected(self):
        placeholder=re.compile(r'<[A-Za-z][A-Za-z0-9_-]*(?: [A-Za-z][A-Za-z0-9_-]*)*>|\{\{[^{}\n]+\}\}')
        special={'generated_rule_arg','previous_group_list','remote_identity',
                 'remote_destination_path','remote_source_basename'}
        for entry in (e for e in self.commands if 'template' in e):
            names={f['name'] for f in entry['fields']}|special
            for field in ('verify','undo'):
                for token in placeholder.findall(entry[field]):
                    name=token.strip('<>{}')
                    self.assertIn(name,names,(entry['id'],field,token))
        self.assertNotIn('<exact generated rule>',json.dumps(self.commands))
        self.assertIn("values.generated_rule_arg=match[1]",self.template)
        self.assertIn("(?: [A-Za-z][A-Za-z0-9_-]*)*>",self.template)

    def test_golden_examples_cannot_leak_into_runnable_guidance(self):
        broken=copy.deepcopy(self.data)
        broken['entries']['kill-send-signal']['preflight'][0]['command']='ps -p 12345'
        errors=schema.instructional_errors(broken,self.commands)
        self.assertTrue(any("hardcodes field 'pid' example '12345'" in e for e in errors),errors)

    def test_converted_runbooks_bind_non_golden_values(self):
        expected={
            'kill-send-signal':'<pid>',
            'curl-transfer-url':'<output>',
            'wget-download-url':'<output>',
            'ssh-remote-shell':'<hostname>',
            'git-checkout-discard-changes':'<path>',
            'git-recovery-wrong-branch':'<revision>',
            'r-usermod-ag':'<username>',
        }
        for eid,token in expected.items():
            commands='\n'.join((item.get('command') or '') for item in self.data['entries'][eid]['preflight'])
            self.assertIn(token,commands,(eid,commands))
        usermod=next(e for e in self.commands if e['id']=='r-usermod-ag')
        self.assertIn('<username>',usermod['verify'])
        self.assertIn('<groups>',usermod['verify'])
        self.assertIn('<previous_group_list>',usermod['undo'])

    def test_known_field_guidance_is_domain_correct(self):
        git_source=self.data['entries']['gen-git-merge']['fields']['source']
        self.assertIn('branch, tag, or commit',git_source['meaning'])
        self.assertEqual(git_source['discovery_command'],'git branch --all')
        rsyslog_target=self.data['entries']['gen-rsyslog-config']['fields']['target']
        self.assertIn('remote system',rsyslog_target['meaning'])
        self.assertEqual(rsyslog_target['discovery_command'],'getent ahosts <target>')

    def test_recovery_and_verification_guidance_matches_the_generated_action(self):
        by_id={entry['id']:entry for entry in self.commands}
        export=by_id['export-shell-variable']
        self.assertIn('export -n <variable>',export['undo'])
        self.assertNotIn('VARNAME',export['undo'])
        kill=by_id['kill-send-signal']
        self.assertIn('SIGTERM',kill['verify'])
        self.assertNotIn('SIGHUP',kill['verify'])
        for eid in ('curl-transfer-url','wget-download-url'):
            download=by_id[eid]
            self.assertIn('<output>.mdcr-before-download',download['undo'])
            self.assertIn('restore',download['undo'].lower())
            self.assertNotIn('simply be deleted',download['undo'].lower())
            preflight='\n'.join((item.get('command') or '') for item in self.data['entries'][eid]['preflight'])
            self.assertIn('cp -a -- <output> <output>.mdcr-before-download',preflight)
        self.assertEqual(
            by_id['scp-secure-copy']['intent'],
            'Copy a local file to a remote host over the same encrypted channel ssh uses',
        )
        self.assertNotIn('--delete',by_id['rsync-sync-files']['undo'])
        for eid,suffix in (('scp-secure-copy','scp'),('rsync-sync-files','rsync')):
            preflight='\n'.join((item.get('command') or '') for item in self.data['entries'][eid]['preflight'])
            self.assertIn('<remote_identity>',preflight)
            self.assertIn('<remote_destination_path>',preflight)
            self.assertIn('sh -s --',preflight)
            self.assertIn('.mdcr-'+suffix+'.txn',preflight)
            self.assertIn('mkdir -m 0700 -- "$txn"',preflight)
            self.assertIn('stat -c',preflight)
            self.assertNotIn('preparing=$txn.preparing',preflight)
            self.assertIn('present',preflight)
            self.assertIn('absent',preflight)
            self.assertIn('.mdcr-'+suffix+'.txn',by_id[eid]['undo'])
            self.assertIn('MDCR_'+suffix.upper()+'_RECOVER',by_id[eid]['undo'])
            self.assertIn('MDCR_'+suffix.upper()+'_FINALIZE',by_id[eid]['verify'])
        rsync_preflight='\n'.join((item.get('command') or '') for item in self.data['entries']['rsync-sync-files']['preflight'])
        self.assertIn('insufficient free space',rsync_preflight)

        nmcli=by_id['gen-nmcli-static-ipv4']
        nmcli_preflight='\n'.join((item.get('command') or '') for item in self.data['entries']['gen-nmcli-static-ipv4']['preflight'])
        self.assertIn('FILENAME,NAME,UUID',nmcli_preflight)
        self.assertIn('cp -a',nmcli_preflight)
        self.assertIn('/var/lib/md-code-red',nmcli_preflight)
        self.assertIn('install -d -m 0700 -o 0 -g 0',nmcli_preflight)
        self.assertIn('stat -c',nmcli_preflight)
        self.assertIn('mkdir -m 0700 -- "$txn"',nmcli_preflight)
        self.assertNotIn('/var/tmp/mdcr-nmcli-static-ipv4.txn',nmcli_preflight)
        self.assertNotIn('connection export',nmcli_preflight+'\n'+nmcli['notes'])
        self.assertIn('MDCR_NMCLI_RECOVER',nmcli['undo'])
        self.assertIn('profile_path',nmcli['undo'])


if __name__=='__main__':
    unittest.main()
