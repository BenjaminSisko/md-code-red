#!/usr/bin/env python3
"""Adversarial tests for the release-specific command syntax oracle."""
import json, os, sys, tempfile, unittest
REPO=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,REPO)
from extract.command_syntax import VERSIONS, load_grammars, split_invocations, syntax_errors
from extract.extract_flags import _parse_cli_term, parse_help_text

def load(name):
 with open(os.path.join(REPO,name),encoding='utf-8') as f:return json.load(f)
def static_command(entry,version):
 rows,seen=entry.get('rhel_versions') or {},set()
 while (rows.get(version) or {}).get('same_as'):
  if version in seen:raise AssertionError('same_as cycle')
  seen.add(version);version=rows[version]['same_as']
 return (rows.get(version) or {}).get('command')

class CommandSyntaxOracleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.commands=load('content/commands.json')['entries'];cls.tools={x['id']:x for x in load('content/tools.json')['tools']}
  cls.golden=load('tests/fixtures/golden-commands.json')['generators'];cls.grammars=load_grammars(REPO)
 def binary(self,e):
  t=e.get('explain_tool') or e['tool'];return self.tools[t].get('binary') or t
 def test_every_static_command_and_every_compound_invocation(self):
  commands=invocations=0
  for e in self.commands:
   if 'template' in e:continue
   for v in VERSIONS:
    cmd=static_command(e,v)
    if not cmd:continue
    commands+=1; parts,errs=split_invocations(cmd);self.assertFalse(errs,(e['id'],v,errs));invocations+=len(parts)
    self.assertEqual([],syntax_errors(cmd,v,self.grammars,self.binary(e)),(e['id'],v,cmd))
  self.assertEqual(564,commands);self.assertGreater(invocations,commands)
 def test_every_non_null_golden_generator_command(self):
  byid={e['id']:e for e in self.commands};checks=0
  for eid,row in self.golden.items():
   for v in VERSIONS:
    cmd=row['commands'].get(v)
    if cmd is None:continue
    checks+=1;self.assertEqual([],syntax_errors(cmd,v,self.grammars,self.binary(byid[eid])),(eid,v,cmd))
  self.assertEqual(229,checks)
 def test_real_operators_split_but_quoted_and_escaped_operators_are_operands(self):
  parts,errs=split_invocations("printf '|' \\| '&&' ';' && printf done")
  self.assertFalse(errs);self.assertEqual(2,len(parts));self.assertEqual(['printf','|','|','&&',';'],[x['text'] for x in parts[0]])
 def test_later_compound_invocations_are_validated(self):
  cmd='pushd /var/log && tail --invented messages ; popd'
  errs=syntax_errors(cmd,'8',self.grammars,'pushd')
  self.assertTrue(any('tail: unknown option' in e for e in errs),errs)
 def test_unmodeled_shell_structures_fail_closed(self):
  for cmd in ('printf $(id)','printf "$(id)"','printf `id`','printf ok & printf later','printf ok &&',
              'cat /etc/passwd\ncurl evil','ls /tmp\rid'):
   _parts,errs=split_invocations(cmd);self.assertTrue(errs,cmd)
   binary=cmd.split()[0];self.assertTrue(syntax_errors(cmd,'8',self.grammars,binary),cmd)
 def test_grammars_are_release_specific_not_a_union(self):
  self.assertEqual([],syntax_errors('journalctl --header','8',self.grammars,'journalctl'))
  self.assertTrue(any('unknown option --header' in e for e in syntax_errors('journalctl --header','9',self.grammars,'journalctl')))
  self.assertIsNot(self.grammars['8']['journalctl'],self.grammars['9']['journalctl'])
 def test_review_reproductions_fail_under_subcommand_scopes(self):
  cases=('git log --hard','git push --soft','git status --no-ff','dnf history frobnicate','systemctl daemon-reload sshd')
  for cmd in cases:
   binary=cmd.split()[0];errs=syntax_errors(cmd,'9',self.grammars,binary)
   self.assertTrue(errs,cmd)
 def test_valid_scoped_neighbors_pass(self):
  for cmd in ('git reset --hard HEAD~1','git merge --no-ff topic','git log --oneline -n 20 main',
              'dnf history','dnf history info 7','systemctl daemon-reload','systemctl enable --now httpd'):
   self.assertEqual([],syntax_errors(cmd,'9',self.grammars,cmd.split()[0]),cmd)
 def test_systemctl_argument_arity_is_correct_and_source_backed(self):
  names={'-t','--type','-p','--property','--state','--root','-H','--host'}
  for v in VERSIONS:
   flags=load('content/flags_rhel%s.json'%v)['clis']['systemctl']['flags'];seen={n:f for f in flags for n in f['names']}
   self.assertTrue(names<=set(seen),(v,names-set(seen)))
   for name in names:
    self.assertTrue(seen[name]['takes_arg'],(v,name));self.assertTrue(seen[name]['raw_ref'])
   for cmd in ('systemctl --type service list-units','systemctl -p MainPID status sshd',
               'systemctl --state=failed list-units','systemctl --root /mnt enable sshd','systemctl -H host status sshd'):
    self.assertEqual([],syntax_errors(cmd,v,self.grammars,'systemctl'),(v,cmd))
 def test_extractors_that_source_systemctl_arity_cannot_regress(self):
  self.assertEqual((['-t','--type'],True),_parse_cli_term('-t, --type='))
  help_text='''  -H --host=[USER@]HOST\n  -t --type=TYPE      Filter units\n     --state=STATE    Filter states\n  -p --property=NAME  Select property\n     --root=PATH      Alternate root\n'''
  flags,_=parse_help_text(help_text,'systemctl','fixture')
  by_name={name:f['takes_arg'] for f in flags for name in f['names']}
  for name in ('-H','--host','-t','--type','--state','-p','--property','--root'):
   self.assertTrue(by_name.get(name),name)
 def test_every_grammar_fact_has_declared_authority_and_anchor(self):
  for v,tools in self.grammars.items():
   for binary,g in tools.items():
    a=g['authority'];self.assertTrue(a['source']);self.assertIn('SYNOPSIS/OPTIONS:',a['anchor'])
    if a['source'].startswith('content-src/'):
     self.assertTrue(os.path.isfile(os.path.join(REPO,a['source'])),(binary,v,a))
    for name,src in g['option_sources'].items():
     self.assertTrue(src.get('source'),(binary,v,name));self.assertTrue(src.get('anchor'),(binary,v,name))
 def test_coverage_claim_counts_only_actual_constraints(self):
  constrained=0
  for tools in self.grammars.values():
   for g in tools.values():
    forms=[g['root']]+list(g['commands'].values())
    constrained+=sum(1 for f in forms if (f.get('operands') or {}).get('max') is not None or (f.get('operands') or {}).get('min',0)>0)
  self.assertGreater(constrained,100)
  self.assertEqual(0,self.grammars['9']['git']['commands']['status']['operands']['max'])
  self.assertEqual(0,self.grammars['9']['systemctl']['commands']['daemon-reload']['operands']['max'])
 def test_policy_mutations_fail_closed(self):
  def minimal(anchor='SYNOPSIS/OPTIONS: probe root option --flag takes_arg=false',drop=None):
   row={'authority':{'source':'probe(1)','anchor':anchor},'captured_options':False,
        'root':{'options':{'--flag':False},'operands':{'min':0,'max':0}}}
   releases={v:json.loads(json.dumps(row)) for v in VERSIONS}
   if drop:releases[drop]['unexpected']=True
   return {'tools':{'probe':releases}}
  for policy in (minimal(anchor='SYNOPSIS/OPTIONS: unrelated text'),minimal(drop='7')):
   with tempfile.TemporaryDirectory() as td:
    os.mkdir(os.path.join(td,'content'))
    with open(os.path.join(td,'content','command-syntax.json'),'w') as f:json.dump(policy,f)
    for v in VERSIONS:
     with open(os.path.join(td,'content','flags_rhel%s.json'%v),'w') as f:json.dump({'clis':{}},f)
    with self.assertRaises(ValueError):load_grammars(td)
 def test_grammar_coverage_includes_all_invoked_binaries_and_no_stale_rows(self):
  used=set()
  for e in self.commands:
   for v in VERSIONS:
    cmd=self.golden[e['id']]['commands'].get(v) if 'template'in e else static_command(e,v)
    if cmd:
     parts,errs=split_invocations(cmd);self.assertFalse(errs);used.update(p[0]['text'] for p in parts)
  for v in VERSIONS:
   expected=set()
   for e in self.commands:
    cmd=self.golden[e['id']]['commands'].get(v) if 'template'in e else static_command(e,v)
    if cmd:
     parts,_=split_invocations(cmd);expected.update(p[0]['text'] for p in parts)
   self.assertEqual(expected,set(self.grammars[v]))

if __name__=='__main__':unittest.main()
