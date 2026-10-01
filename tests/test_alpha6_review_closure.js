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
const mod=new Function('"use strict";\n'+code+'\nreturn {assembleCommand,validateField};')();
const entries=JSON.parse(fs.readFileSync(path.join(repo,'content','commands.json'),'utf8')).entries;
const by=Object.fromEntries(entries.map(e=>[e.id,e]));
const patterns=JSON.parse(fs.readFileSync(path.join(repo,'content','dangerous.json'),'utf8')).patterns;
const failures=[];
function check(ok,msg){if(!ok)failures.push(msg)}
function assemble(id,values){return mod.assembleCommand(by[id],'8',values,{patterns});}

// A remote operand gets a second parser on older scp/rsync. The validator must
// refuse values local shell quoting would otherwise make look safe.
check(assemble('scp-secure-copy',{preserve:'yes',source:'/etc/app/config.yml',destination:'alice@host:/tmp/x;id'})===null,'scp accepted remote-shell separator');
check(assemble('rsync-sync-files',{dry_run:'yes',source:'/etc/app/',destination:'alice@host:/tmp/$(id)'})===null,'rsync accepted remote command substitution');
const rsync=assemble('rsync-sync-files',{dry_run:'yes',source:'/etc/app/',destination:'alice@host:/tmp/app/'});
check(rsync&&rsync.command.includes(' -s '),'rsync omitted --protect-args/-s');

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

const report={checks:23,failures};
process.stdout.write(JSON.stringify(report)+'\n');
process.exit(failures.length?1:0);
