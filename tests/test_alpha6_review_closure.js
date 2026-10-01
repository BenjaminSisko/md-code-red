#!/usr/bin/env node
"use strict";
const fs=require('fs'),path=require('path');
const repo=path.resolve(__dirname,'..');
const target=process.argv[2]||path.join(repo,'template.html');
const src=fs.readFileSync(target,'utf8');
function block(begin,end){
  const a=src.indexOf(begin),from=src.indexOf('*/',a)+2,b=src.indexOf(end,from),to=src.lastIndexOf('/*',b);
  if(a<0||from<2||b<0||to<from)throw new Error('missing assembler markers');
  return src.slice(from,to);
}
const code=block('MCR-ASSEMBLER-BEGIN','MCR-ASSEMBLER-END');
const mod=new Function('"use strict";\n'+code+'\nreturn {assembleCommand,validateField,assemblePipeline,redirectTargetBlast};')();
const entries=JSON.parse(fs.readFileSync(path.join(repo,'content','commands.json'),'utf8')).entries;
const tools=JSON.parse(fs.readFileSync(path.join(repo,'content','tools.json'),'utf8')).tools;
const by=Object.fromEntries(entries.map(e=>[e.id,e]));
const patterns=JSON.parse(fs.readFileSync(path.join(repo,'content','dangerous.json'),'utf8')).patterns;
const failures=[];
let checks=0;
function check(ok,msg){checks++;if(!ok)failures.push(msg)}
function assemble(id,values){return mod.assembleCommand(by[id],'8',values,{patterns});}

// A remote operand gets a second parser on older scp/rsync. The validator must
// refuse values local shell quoting would otherwise make look safe.
check(assemble('scp-secure-copy',{preserve:'yes',source:'/etc/app/config.yml',destination:'alice@host:/tmp/x;id'})===null,'scp accepted remote-shell separator');
check(assemble('rsync-sync-files',{dry_run:'yes',source:'/etc/app/',destination:'alice@host:/tmp/$(id)'})===null,'rsync accepted remote command substitution');
const rsync=assemble('rsync-sync-files',{dry_run:'yes',source:'/etc/app/',destination:'alice@host:/tmp/app/'});
check(rsync&&rsync.command.includes(' -s '),'rsync omitted --protect-args/-s');
const remoteScratch=assemble('scp-secure-copy',{source:'/etc/app/config.yml',destination:'alice@host:/tmp/config.yml'});
check(remoteScratch&&remoteScratch.blast==='yellow','remote scratch destination was not rated as a write');
const remoteSystem=assemble('scp-secure-copy',{source:'/etc/app/config.yml',destination:'root@host:/etc/hosts'});
check(remoteSystem&&remoteSystem.blast==='red','remote protected destination was not raised to red');
const remoteRoot=assemble('rsync-sync-files',{source:'/etc/app/',destination:'root@host:/'});
check(remoteRoot&&remoteRoot.blast==='red','remote filesystem root was not raised to red');
check(assemble('scp-secure-copy',{source:'/etc/app/config.yml',destination:'root@host:/etc/cron.d/job'})===null,
      'remote execution sink was not refused');

// A pipeline write is never read-only. Ordinary files are yellow, sensitive
// login/startup files are red, and delayed-execution sinks are refused.
const journalValues={unit:'sshd.service',priority:'err',since:'today',thisboot:'yes'};
function redirected(target){return mod.assemblePipeline([
  {spec:by['gen-journalctl-unit-logs'],values:journalValues},
  {op:'redirect',target}
],'8',{patterns,tools});}
const pipelineScratch=redirected('/tmp/log.txt');
check(pipelineScratch&&pipelineScratch.blast==='yellow','pipeline file write was labelled read-only');
const pipelineStartup=redirected('/root/.bashrc');
check(pipelineStartup&&pipelineStartup.blast==='red','pipeline shell-startup write was not red');
check(redirected('/root/.ssh/authorized_keys')?.blast==='red','pipeline SSH trust write was not red');
check(redirected('/etc/cron.d/job')===null,'pipeline execution sink was not refused');
const attributedFlags=mod.assemblePipeline([
  {spec:by['gen-journalctl-unit-logs'],values:journalValues},
  {op:'pipe',spec:by['gen-systemctl-manage'],values:{action:'start',unit:'sshd.service'}}
],'8',{patterns,tools});
check(attributedFlags&&attributedFlags.flags.length>0&&
      attributedFlags.flags.every(f=>Number.isInteger(f.stage_index)&&typeof f.tool==='string'&&f.tool),
      'pipeline flag metadata omitted its stage/tool source');

// Download forms are state-changing write operations, accept HTTP(S) only,
// refuse execution sinks, and raise protected system destinations to red.
for(const id of ['curl-transfer-url','wget-download-url']){
  check(assemble(id,{output:'/tmp/file',url:'file:///etc/shadow'})===null,id+' accepted file: URL');
  check(assemble(id,{output:'/etc/cron.d/job',url:'https://example.test/file'})===null,id+' accepted execution sink');
  const scratch=assemble(id,{output:'/tmp/file',url:'https://example.test/file'});
  check(scratch&&scratch.blast==='yellow',id+' did not rate a scratch write yellow');
  const system=assemble(id,{output:'/etc/hosts',url:'https://example.test/file'});
  check(system&&system.blast==='red',id+' did not raise a protected path write to red');
}

check(assemble('kill-send-signal',{pid:'0'})===null,'kill accepted PID 0');
check(assemble('export-shell-variable',{variable:'my-var'})===null,'export accepted an invalid shell identifier');
check(assemble('git-checkout-discard-changes',{path:'*.py'})===null,'git discard accepted pathspec globbing');
check(assemble('git-checkout-discard-changes',{path:':/config'})===null,'git discard accepted pathspec magic');

// Optional-subset controls exercise shapes the all-options golden fixture does
// not: each omitted field must disappear with its own option and no neighbour.
let res=assemble('grep-search-text',{pattern:'laundry',target:'/etc'});
check(res&&res.command==="grep 'laundry' '/etc'",'grep no-flag subset is wrong');
res=assemble('grep-search-text',{ignore_case:'yes',pattern:'laundry',target:'/etc'});
check(res&&res.command==="grep -i 'laundry' '/etc'",'grep one-flag subset is wrong');
res=assemble('ssh-remote-shell',{hostname:'server.example.test'});
check(res&&res.command==="ssh 'server.example.test'",'ssh optional identity/username subset is wrong');
res=assemble('scp-secure-copy',{source:'/etc/app/config.yml',destination:'alice@server.example.test:/tmp/config.yml'});
check(res&&res.command==="scp '/etc/app/config.yml' 'alice@server.example.test:/tmp/config.yml'",'scp no-preserve subset is wrong');
res=assemble('rsync-sync-files',{source:'/etc/app/',destination:'alice@server.example.test:/tmp/app/'});
check(res&&res.command==="rsync -a -v -h -s '/etc/app/' 'alice@server.example.test:/tmp/app/'",'rsync no-dry-run subset is wrong');

// A host receipt applies only to the byte-exact command that was captured.
function extractFn(name){
  const re=new RegExp('function '+name+'\\([^)]*\\)\\{'),m=re.exec(src);
  if(!m)throw new Error('missing '+name);
  let i=src.indexOf('{',m.index),depth=0;
  for(;i<src.length;i++){
    if(src[i]==='{')depth++;
    else if(src[i]==='}'&&--depth===0)return src.slice(m.index,i+1);
  }
  throw new Error('unbalanced '+name);
}
const verificationStatusForVersion=new Function('"use strict";\n'+extractFn('verificationStatusForVersion')+'\nreturn verificationStatusForVersion;')();
const receipted={verified:{'8':{by:'QA',on:'2026-10-01',host:'rhel8',command_as_run:'exact command'}}};
check(verificationStatusForVersion(receipted,'8','exact command').state==='verified','exact captured command lost its receipt');
check(verificationStatusForVersion(receipted,'8','different command').state==='unverified','changed values inherited a receipt');

const report={checks,failures};
process.stdout.write(JSON.stringify(report)+'\n');
process.exit(failures.length?1:0);
