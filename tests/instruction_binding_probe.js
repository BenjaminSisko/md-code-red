#!/usr/bin/env node
"use strict";
const fs=require('fs'),path=require('path');
const repo=path.resolve(__dirname,'..');
const target=process.argv[2]||path.join(repo,'template.html');
const src=fs.readFileSync(target,'utf8');
function marked(begin,end){
  const a=src.indexOf(begin),from=src.indexOf('*/',a)+2,b=src.indexOf(end,from),to=src.lastIndexOf('/*',b);
  if(a<0||from<2||b<0||to<from)throw new Error(`missing ${begin}/${end}`);
  return src.slice(from,to);
}
const sh=/function shQuote\(s\)\{[\s\S]*?\n\}/.exec(src);
if(!sh)throw new Error('missing shQuote');
const binding=marked('MCR-INSTRUCTION-BINDING-BEGIN','MCR-INSTRUCTION-BINDING-END');
const bind=new Function('"use strict";\n'+sh[0]+'\n'+binding+'\nreturn bindInstructionCommand;')();
let input='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>input+=x);process.stdin.on('end',()=>{
  const request=JSON.parse(input);
  process.stdout.write(JSON.stringify({bound:bind(request.text,request.values)})+'\n');
});
