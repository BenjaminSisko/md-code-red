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
const assembler=marked('MCR-ASSEMBLER-BEGIN','MCR-ASSEMBLER-END');
const binding=marked('MCR-INSTRUCTION-BINDING-BEGIN','MCR-INSTRUCTION-BINDING-END');
const instructionStart=src.indexOf('function instructionFor(');
const instructionEnd=src.indexOf('function fieldInstruction(',instructionStart);
const planStart=src.indexOf('function operationalPlan(');
const planEnd=src.indexOf('function instructionIsBound(',planStart);
if(instructionStart<0||instructionEnd<0||planStart<0||planEnd<0)throw new Error('missing operational plan functions');
const instructionFor=src.slice(instructionStart,instructionEnd);
const operationalPlan=src.slice(planStart,planEnd);
const commands=JSON.parse(fs.readFileSync(path.join(repo,'content','commands.json'),'utf8'));
const instructional=JSON.parse(fs.readFileSync(path.join(repo,'content','instructional.json'),'utf8'));
const patterns=JSON.parse(fs.readFileSync(path.join(repo,'content','dangerous.json'),'utf8')).patterns;
const runtime=new Function('DATASETS','STATE','"use strict";\n'+assembler+'\n'+instructionFor+'\n'+binding+'\n'+operationalPlan+'\nreturn {bindInstructionCommand,assembleCommand,operationalPlan};')({INSTRUCTIONAL:instructional},{formValues:{}});
let input='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>input+=x);process.stdin.on('end',()=>{
  const request=JSON.parse(input);
  if(request.entry_id){
    const entry=commands.entries.find(row=>row.id===request.entry_id);
    if(!entry)throw new Error('unknown entry '+request.entry_id);
    const state={formValues:request.values||{}};
    const scoped=new Function('DATASETS','STATE','"use strict";\n'+assembler+'\n'+instructionFor+'\n'+binding+'\n'+operationalPlan+'\nreturn {assembleCommand,operationalPlan};')({INSTRUCTIONAL:instructional},state);
    const res=scoped.assembleCommand(entry,request.version||'8',state.formValues,{patterns});
    if(!res)throw new Error('entry did not assemble');
    process.stdout.write(JSON.stringify({plan:scoped.operationalPlan(entry,res),command:res.command})+'\n');
  }else{
    process.stdout.write(JSON.stringify({bound:runtime.bindInstructionCommand(request.text,request.values)})+'\n');
  }
});
