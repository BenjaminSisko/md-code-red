/*
 * Full rendered-UI audit for MD CODE RED v1.0.0-alpha.6.
 *
 * Prerequisites:
 *   python3 -m http.server 8878 --bind 127.0.0.1
 *   open -na "Google Chrome" --args --headless=new --remote-debugging-port=9232 about:blank
 *
 * Run from any directory:
 *   node tools/qa/mdcr_functional_ui_audit.mjs <repo> <app-url> <cdp-port>
 *
 * The machine-readable result is written to
 * /tmp/mdcr_functional_audit_results.json.
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const repo = process.argv[2] || process.cwd();
const baseUrl = process.argv[3] || 'http://127.0.0.1:8878/dist/md-code-red_v1.0.0-alpha.6.html';
const cdpPort = Number(process.argv[4] || 9232);
const artifactPath=path.join(repo,'dist','md-code-red_v1.0.0-alpha.6.html');
const artifactBytes=fs.readFileSync(artifactPath);
const artifactText=artifactBytes.toString('utf8');
const artifactSha256=crypto.createHash('sha256').update(artifactBytes).digest('hex');
const fingerprintMatch=/var CONTENT_FINGERPRINT="([0-9a-f]{64})"/.exec(artifactText);
const contentFingerprint=fingerprintMatch?fingerprintMatch[1]:'';
const commandsDoc = JSON.parse(fs.readFileSync(path.join(repo,'content/commands.json'),'utf8'));
const toolsDoc = JSON.parse(fs.readFileSync(path.join(repo,'content/tools.json'),'utf8'));
const golden = JSON.parse(fs.readFileSync(path.join(repo,'tests/fixtures/golden-commands.json'),'utf8'));
const tools = new Map(toolsDoc.tools.map(t=>[t.id,t]));
const entries = commandsDoc.entries;

const pages = await (await fetch(`http://127.0.0.1:${cdpPort}/json/list`)).json();
const page = pages.find(p=>p.type==='page');
if (!page) throw new Error('No CDP page target');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let nextId=1;
const pending=new Map();
const exceptions=[];
const consoleErrors=[];
ws.onmessage=(event)=>{
  const msg=JSON.parse(event.data);
  if(msg.id&&pending.has(msg.id)){
    const p=pending.get(msg.id);pending.delete(msg.id);
    if(msg.error)p.reject(new Error(JSON.stringify(msg.error))); else p.resolve(msg.result);
    return;
  }
  if(msg.method==='Runtime.exceptionThrown') exceptions.push(msg.params.exceptionDetails?.exception?.description||msg.params.exceptionDetails?.text||'exception');
  if(msg.method==='Runtime.consoleAPICalled'&&['error','assert'].includes(msg.params.type)) consoleErrors.push(msg.params.args?.map(a=>a.value||a.description).join(' ')||msg.params.type);
};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
function send(method,params={}){
  const id=nextId++;
  ws.send(JSON.stringify({id,method,params}));
  return new Promise((resolve,reject)=>pending.set(id,{resolve,reject}));
}
async function evaluate(expression){
  const out=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(out.exceptionDetails) throw new Error(out.exceptionDetails.exception?.description||out.exceptionDetails.text);
  return out.result?.value;
}
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function typeCharacters(selector,text){
  const focused=await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return false;e.focus();return document.activeElement===e})()`);
  if(!focused)return {value:'',active:'',focused:false};
  for(const character of text){
    await send('Input.dispatchKeyEvent',{type:'keyDown',text:character,unmodifiedText:character,key:character});
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:character});
  }
  await delay(30);
  return evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});return {value:e?.value||'',active:document.activeElement?.id||document.activeElement?.getAttribute('data-pipe-field')||document.activeElement?.getAttribute('data-field')||document.activeElement?.tagName||'',focused:document.activeElement===e,paletteHidden:document.querySelector('#palette')?.hidden}})()`);
}
async function pressKey(key,code=key){
  await send('Input.dispatchKeyEvent',{type:'keyDown',key,code});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key,code});
}
async function realClick(selector){
  const point=await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;e.scrollIntoView({block:'center',inline:'center'});const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
  if(!point)return false;
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:point.x,y:point.y});
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:point.x,y:point.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:point.x,y:point.y,button:'left',clickCount:1});
  await delay(30);
  return true;
}
const results=[];
function record(id,area,description,status,expected,actual,severity=''){
  results.push({id,area,description,status,expected:String(expected??''),actual:String(actual??''),severity});
}
function pass(id,area,description,actual=''){record(id,area,description,'PASS','',actual)}
function fail(id,area,description,expected,actual,severity='Major'){record(id,area,description,'FAIL',expected,actual,severity)}

await send('Page.enable');
await send('Runtime.enable');
await send('Log.enable');
try{await send('Browser.grantPermissions',{origin:new URL(baseUrl).origin,permissions:['clipboardReadWrite','clipboardSanitizedWrite']});}catch{}
try{await send('Storage.clearDataForOrigin',{origin:new URL(baseUrl).origin,storageTypes:'all'});}catch{}
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false,screenWidth:1440,screenHeight:1000});
const navStart=Date.now();
await send('Page.navigate',{url:baseUrl});
await delay(1200);
const navMs=Date.now()-navStart;
await evaluate(`(()=>{window.__qa={
  click(sel){const e=document.querySelector(sel);if(!e)return false;e.click();return true},
  set(sel,value){const e=document.querySelector(sel);if(!e)return {ok:false,reason:'missing'};if(e.disabled)return {ok:false,reason:'disabled'};if(e.type==='checkbox'){e.checked=value==='yes'||value===true}else{e.value=String(value)}e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return {ok:true}},
  open(rail,tool,id,version,intent){
    const vb=document.querySelector('[data-version="'+CSS.escape(version)+'"]');if(!vb)return {ok:false,step:'version'};vb.click();
    const rb=document.querySelector('[data-rail="'+CSS.escape(rail)+'"]');if(!rb)return {ok:false,step:'rail'};rb.click();
    const tb=document.querySelector('[data-tool="'+CSS.escape(tool)+'"]');if(!tb)return {ok:false,step:'tool'};if(tb.getAttribute('aria-current')!=='true')tb.click();
    const eb=document.querySelector('[data-entry="'+CSS.escape(id)+'"]');
    if(!eb){const gated=[...document.querySelectorAll('#sidebar-body button[disabled]')].find(x=>x.textContent.trim().startsWith(intent));return {ok:false,step:gated?'gated':'entry',gated:!!gated}}
    eb.click();return {ok:true}
  },
  command(){return [...document.querySelectorAll('#editor-card .codeline .lc')].map(x=>x.textContent).join('\\n')},
  state(){return {title:document.querySelector('#editor-card h2')?.textContent||'',rail:document.querySelector('#rail [aria-current="true"]')?.getAttribute('data-rail')||'',copy:!!document.querySelector('[data-action="copy"]'),copyDisabled:!!document.querySelector('[data-action="copy"]')?.disabled,fields:document.querySelectorAll('[data-field]').length,toast:document.querySelector('.toast')?.textContent||'',theme:document.documentElement.getAttribute('data-theme')||'',sidebar:document.body.getAttribute('data-sidebar'),inspector:document.body.getAttribute('data-inspector'),selection:document.body.getAttribute('data-selection-open')}}
};return true})()`);

const boot=await evaluate(`(()=>({title:document.title,h1:document.querySelectorAll('h1').length,home:document.querySelector('#editor-card h2')?.textContent,rail:document.querySelector('#rail [aria-current="true"]')?.getAttribute('data-rail'),scripts:document.scripts.length,islands:document.querySelectorAll('script[type="application/json"]').length,scrollWidth:document.documentElement.scrollWidth,innerWidth}))()`);
if(boot.title.includes('alpha.6')&&boot.home==='What do you need to do?'&&boot.rail==='favorites') pass('TC-BOOT-001','Boot','App opens to task-centered Home',JSON.stringify(boot)); else fail('TC-BOOT-001','Boot','App opens to task-centered Home','alpha.6 Home/favorites',JSON.stringify(boot),'Blocker');
if(boot.h1===1) pass('TC-A11Y-001','Accessibility','Exactly one h1 is exposed',boot.h1); else fail('TC-A11Y-001','Accessibility','Exactly one h1 is exposed',1,boot.h1,'Major');
if(boot.scrollWidth<=boot.innerWidth) pass('TC-LAYOUT-001','Layout','Desktop boot has no horizontal overflow',`${boot.scrollWidth}/${boot.innerWidth}`); else fail('TC-LAYOUT-001','Layout','Desktop boot has no horizontal overflow',`<=${boot.innerWidth}`,boot.scrollWidth,'Major');
record('TC-PERF-001','Performance','Initial page navigation and render','PASS','informational',`${navMs} ms`);

// Primary rails and empty/catalog states.
const railExpect={favorites:'What do you need to do?',builder:'No command selected',ansible:'No command selected',git:'No command selected',reference:'No command selected',about:'About MD CODE RED'};
for(const [rail,title] of Object.entries(railExpect)){
  const got=await evaluate(`(()=>{document.querySelector('[data-rail="${rail}"]').click();return {current:document.querySelector('[data-rail="${rail}"]').getAttribute('aria-current'),title:document.querySelector('#editor-card h2')?.textContent||'',sidebar:document.querySelector('#sidebar-body')?.textContent||''}})()`);
  if(got.current==='true'&&got.title===title)pass(`TC-RAIL-${rail.toUpperCase()}`,'Navigation',`${rail} rail opens the expected workspace`,got.title);else fail(`TC-RAIL-${rail.toUpperCase()}`,'Navigation',`${rail} rail opens the expected workspace`,title,JSON.stringify(got),'Major');
}
const compliance=await evaluate(`(()=>{document.querySelector('[data-rail="stig"]').click();return {open:!document.querySelector('#palette').hidden,value:document.querySelector('#palette-input').value,expanded:document.querySelector('#palette-input').getAttribute('aria-expanded')}})()`);
if(compliance.open&&compliance.value==='STIG'&&compliance.expanded==='true')pass('TC-RAIL-STIG','Navigation','Compliance opens a STIG-filtered search dialog',JSON.stringify(compliance));else fail('TC-RAIL-STIG','Navigation','Compliance opens a STIG-filtered search dialog','open STIG search',JSON.stringify(compliance),'Major');
await evaluate(`document.querySelector('#palette [data-action]')?true:(document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})),true)`);
await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);

function resolveSlot(entry,version,seen=new Set()){
  const slot=entry.rhel_versions?.[version];
  if(!slot||slot.unavailable)return null;
  if(slot.command!==undefined)return slot.command;
  if(slot.same_as!==undefined){if(seen.has(version))throw new Error('same_as cycle');seen.add(version);return resolveSlot(entry,String(slot.same_as),seen)}
  return null;
}
function railFor(entry){const cat=tools.get(entry.tool)?.category;return cat==='ansible'?'ansible':cat==='git'?'git':'builder'}
let matrixIndex=0;
for(const entry of entries){
  const rail=railFor(entry);
  for(const version of ['7','8','9','10']){
    matrixIndex++;
    const isGen=Object.hasOwn(entry,'template');
    const expected=isGen?(golden.generators[entry.id]?.commands?.[version]??null):resolveSlot(entry,version);
    const open=await evaluate(`__qa.open(${JSON.stringify(rail)},${JSON.stringify(entry.tool)},${JSON.stringify(entry.id)},${JSON.stringify(version)},${JSON.stringify(entry.intent)})`);
    const id=`TC-MATRIX-${String(matrixIndex).padStart(3,'0')}`;
    if(expected===null){
      if(!open.ok&&open.step==='gated') pass(id,'Entry matrix',`${entry.id} is visibly gated on RHEL ${version}`,'disabled row');
      else if(!open.ok&&open.step==='tool'&&tools.get(entry.tool)?.availability?.[version]?.available===false) pass(id,'Entry matrix',`${entry.id} is visibly gated with its tool on RHEL ${version}`,'disabled tool row');
      else if(!open.ok) fail(id,'Entry matrix',`${entry.id} is visibly gated on RHEL ${version}`,'disabled row',JSON.stringify(open),'Major');
      else fail(id,'Entry matrix',`${entry.id} is visibly gated on RHEL ${version}`,'no selectable entry','selectable entry','Critical');
      continue;
    }
    if(!open.ok){fail(id,'Entry matrix',`${entry.id} opens on RHEL ${version}`,'selectable entry',JSON.stringify(open),'Critical');continue}
    if(isGen){
      const pre=await evaluate(`__qa.state()`);
      const hasRequired=(entry.fields||[]).some(f=>f.required&&(!f.versions||f.versions.includes(version)));
      if(hasRequired&&pre.copy){fail(id,'Entry matrix',`${entry.id} withholds Copy until required fields are complete on RHEL ${version}`,'Copy absent before valid input',JSON.stringify(pre),'Critical');continue}
      const vals=golden.generators[entry.id]?.values||{};
      let fillError='';
      for(const [name,value] of Object.entries(vals)){
        const set=await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(name)})+'"]',${JSON.stringify(value)})`);
        if(!set.ok)fillError=`${name}:${set.reason}`;
      }
      const state=await evaluate(`(()=>({...__qa.state(),command:__qa.command(),ack:!!document.querySelector('[data-action="ack"]')}))()`);
      if(fillError){fail(id,'Entry matrix',`${entry.id} fields accept golden values on RHEL ${version}`,'all fields editable',fillError,'Critical');continue}
      if(state.command!==expected){fail(id,'Entry matrix',`${entry.id} renders the golden command on RHEL ${version}`,expected,state.command,'Critical');continue}
      const expectedFields=(entry.fields||[]).length;
      if(state.fields!==expectedFields){fail(id,'Entry matrix',`${entry.id} renders every declared field on RHEL ${version}`,expectedFields,state.fields,'Major');continue}
      if(!state.copy){fail(id,'Entry matrix',`${entry.id} exposes Copy after valid input on RHEL ${version}`,'Copy command present',JSON.stringify(state),'Critical');continue}
      if(entry.blast==='red'){
        if(!state.ack||!state.copyDisabled){fail(id,'Entry matrix',`${entry.id} blocks red-copy pending review on RHEL ${version}`,'ack present and copy disabled',JSON.stringify(state),'Critical');continue}
        const unlocked=await evaluate(`(()=>{document.querySelector('[data-action="ack"]').click();return !document.querySelector('[data-action="copy"]').disabled})()`);
        if(!unlocked){fail(id,'Entry matrix',`${entry.id} unlocks after explicit red review on RHEL ${version}`,'copy enabled',unlocked,'Critical');continue}
      }
      pass(id,'Entry matrix',`${entry.id} renders through its UI on RHEL ${version}`,expected);
    }else{
      const state=await evaluate(`(()=>({...__qa.state(),command:__qa.command(),ack:!!document.querySelector('[data-action="ack"]')}))()`);
      if(state.command!==expected){fail(id,'Entry matrix',`${entry.id} renders its reviewed command on RHEL ${version}`,expected,state.command,'Critical');continue}
      if(!state.copy){fail(id,'Entry matrix',`${entry.id} exposes Copy on RHEL ${version}`,'Copy command present',JSON.stringify(state),'Critical');continue}
      if(entry.blast==='red'&&(!state.ack||!state.copyDisabled)){fail(id,'Entry matrix',`${entry.id} gates red copy on RHEL ${version}`,'ack present and copy disabled',JSON.stringify(state),'Critical');continue}
      pass(id,'Entry matrix',`${entry.id} renders through its UI on RHEL ${version}`,expected);
    }
  }
}

// Guard the operator-facing meaning of risk labels. The fourth release-candidate
// review found state-changing file and Git commands presented as green/read-only.
// The catalogue checks cover every corrected ID; this browser sample proves the
// rendered UI exposes the corrected rating and no longer calls green "Read only."
const cpRisk=await evaluate(`(()=>{__qa.open('builder','cp','cp-copy','8','Duplicate a file or directory tree to a new location, leaving the original in place');const bar=document.querySelector('#editor-card .trustbar');return {text:bar?.textContent||'',yellow:!!bar?.querySelector('.risk-yellow')}})()`);
const lsRisk=await evaluate(`(()=>{__qa.open('builder','ls','ls-listing','8','See what is in a directory before touching anything in it');const bar=document.querySelector('#editor-card .trustbar');return {text:bar?.textContent||'',green:!!bar?.querySelector('.risk-green')}})()`);
if(cpRisk.yellow&&cpRisk.text.includes('Changes system')&&lsRisk.green&&lsRisk.text.includes('Low impact')&&!lsRisk.text.includes('Read only'))pass('TC-RISK-LABEL-001','Safety','Rendered risk labels distinguish state-changing commands from low-impact commands',JSON.stringify({cpRisk,lsRisk}));else fail('TC-RISK-LABEL-001','Safety','Rendered risk labels distinguish state-changing commands from low-impact commands','cp-copy: yellow/Changes system; ls-listing: green/Low impact; no Read only claim',JSON.stringify({cpRisk,lsRisk}),'Critical');

// The value matrix above drives DOM events directly so it can cover every
// release quickly. Exercise every guided text control with actual CDP key
// events once as well: this catches focus loss when an input handler replaces
// the node that is receiving the user's next character.
const typingMatrixExceptionStart=exceptions.length;
let typedGuidedFields=0;
const typingMatrixFailures=[];
for(const entry of entries.filter(e=>Object.hasOwn(e,'template'))){
  const version=['8','9','10','7'].find(v=>golden.generators[entry.id]?.commands?.[v]!==null&&golden.generators[entry.id]?.commands?.[v]!==undefined);
  if(!version)continue;
  const open=await evaluate(`__qa.open(${JSON.stringify(railFor(entry))},${JSON.stringify(entry.tool)},${JSON.stringify(entry.id)},${JSON.stringify(version)},${JSON.stringify(entry.intent)})`);
  if(!open.ok){typingMatrixFailures.push(`${entry.id}:open:${JSON.stringify(open)}`);continue}
  const textFields=await evaluate(`(()=>[...document.querySelectorAll('input[data-field]:not([type="checkbox"]),textarea[data-field]')].map(x=>x.getAttribute('data-field')))()`);
  for(const name of textFields){
    const goldenValue=golden.generators[entry.id]?.values?.[name];
    if(goldenValue===undefined){typingMatrixFailures.push(`${entry.id}.${name}:missing golden value`);continue}
    const selector=`[data-field="${name}"]`;
    await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return false;e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);
    const typed=await typeCharacters(selector,String(goldenValue));
    typedGuidedFields++;
    if(typed.value!==String(goldenValue)||!typed.focused){
      typingMatrixFailures.push(`${entry.id}.${name}:${JSON.stringify(typed)}`);
    }
  }
}
if(typedGuidedFields>0&&typingMatrixFailures.length===0&&exceptions.length===typingMatrixExceptionStart)pass('TC-INPUT-KEYBOARD-MATRIX','Input','Every guided text control accepts character-by-character CDP input while retaining focus',`${typedGuidedFields} controls; zero exceptions`);else fail('TC-INPUT-KEYBOARD-MATRIX','Input','Every guided text control accepts character-by-character CDP input while retaining focus','all guided text controls retain their complete value and focus; zero exceptions',JSON.stringify({typedGuidedFields,typingMatrixFailures,exceptions:exceptions.slice(typingMatrixExceptionStart)}),'Critical');

// Reproduce the grep task discovered by the user.
const grepEntry=entries.find(e=>e.id==='grep-search-text');
await evaluate(`__qa.open('builder','grep','grep-search-text','8',${JSON.stringify(grepEntry.intent)})`);
const grepValues=golden.generators['grep-search-text'].values;
for(const [name,value] of Object.entries(grepValues))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(name)})+'"]',${JSON.stringify(value)})`);
const grepExpected=golden.generators['grep-search-text'].commands['8'];
const grepState=await evaluate(`(()=>({command:__qa.command(),fields:document.querySelectorAll('[data-field]').length,flagControls:document.querySelectorAll('select[data-field],input[data-field]').length}))()`);
if(grepState.command===grepExpected&&grepState.fields===grepEntry.fields.length&&grepState.flagControls>=3) pass('TC-TASK-GREP-001','Task completion','Build a flagged grep search for “laundry”',JSON.stringify(grepState)); else fail('TC-TASK-GREP-001','Task completion','Build a flagged grep search for “laundry”',grepExpected+' with editable pattern, target, and flags',JSON.stringify(grepState),'Major');
const gutterStart=await evaluate(`(()=>{const e=document.querySelector('#editor-card [data-line]');if(!e)return null;e.focus();return e.getAttribute('data-line')})()`);
await pressKey('Enter','Enter');
const gutterEnd=await evaluate(`document.activeElement?.getAttribute('data-line')||null`);
if(gutterStart!==null&&gutterEnd===gutterStart)pass('TC-A11Y-FOCUS-003','Accessibility','Keyboard line selection retains focus after the command review re-renders',`line ${gutterEnd}`);else fail('TC-A11Y-FOCUS-003','Accessibility','Keyboard line selection retains focus after the command review re-renders','same focused command line',JSON.stringify({gutterStart,gutterEnd}),'Major');

// Clipboard and evidence workflow on the completed safe grep generator.
await evaluate(`__qa.open('builder','grep','grep-search-text','8',${JSON.stringify(grepEntry.intent)})`);
for(const [name,value] of Object.entries(grepValues))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(name)})+'"]',${JSON.stringify(value)})`);
await evaluate(`(()=>{window.__copied='';document.execCommand=(name)=>{if(name==='copy'){window.__copied=document.querySelector('textarea')?.value||'';return true}return false};return true})()`);
await evaluate(`document.querySelector('[data-action="copy"]').click()`);
await delay(20);
let clipboard=await evaluate(`window.__copied`);
if(clipboard===grepExpected)pass('TC-COPY-001','Clipboard','Copy command writes the exact rendered command',clipboard);else fail('TC-COPY-001','Clipboard','Copy command writes the exact rendered command',grepExpected,clipboard,'Critical');
await evaluate(`document.querySelector('[data-action="copy-comment"]').click()`);await delay(20);
clipboard=await evaluate(`window.__copied`);
if(clipboard.includes('# intent:')&&clipboard.trim().endsWith(grepExpected))pass('TC-COPY-002','Clipboard','Copy with comment includes metadata and the exact command',clipboard.slice(0,180));else fail('TC-COPY-002','Clipboard','Copy with comment includes metadata and the exact command','comment header + exact command',clipboard.slice(0,300),'Critical');
// A field blur fires change between pointer down and pointer up. This must be
// idempotent so the first real click reaches the same button node and the old
// success toast cannot describe a changed command.
await evaluate(`(()=>{const e=document.querySelector('[data-field="pattern"]');e.focus();e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);
await typeCharacters('[data-field="pattern"]','laundry-new');
const editedBeforeClick=await evaluate(`(()=>({command:__qa.command(),toast:document.querySelector('.toast')?.textContent||''}))()`);
await realClick('[data-action="copy"]');
const pointerCopy=await evaluate(`(()=>({clipboard:window.__copied,command:__qa.command(),toast:document.querySelector('.toast')?.textContent||''}))()`);
if(!editedBeforeClick.toast&&pointerCopy.clipboard===pointerCopy.command&&pointerCopy.command.includes('laundry-new')&&pointerCopy.toast.includes('Copied'))pass('TC-COPY-POINTER-001','Clipboard','One real pointer click after typing copies the newly displayed command and refreshes status',JSON.stringify(pointerCopy));else fail('TC-COPY-POINTER-001','Clipboard','One real pointer click after typing copies the newly displayed command and refreshes status','empty stale toast, clipboard equals edited command, success status',JSON.stringify({editedBeforeClick,pointerCopy}),'Critical');
await evaluate(`(()=>{const e=document.querySelector('[data-field="target"]');e.focus();e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);
await typeCharacters('[data-field="target"]','/etc');
await pressKey('Tab','Tab');
const tabAfterEdit=await evaluate(`(()=>({body:document.activeElement===document.body,tag:document.activeElement?.tagName||'',action:document.activeElement?.getAttribute('data-action')||'',field:document.activeElement?.getAttribute('data-field')||''}))()`);
if(!tabAfterEdit.body&&tabAfterEdit.field!=='target')pass('TC-A11Y-FOCUS-004','Accessibility','Tab after typing in the last field advances to the next control',JSON.stringify(tabAfterEdit));else fail('TC-A11Y-FOCUS-004','Accessibility','Tab after typing in the last field advances to the next control','focus advances and never falls to body',JSON.stringify(tabAfterEdit),'Major');
const evidence=await evaluate(`(()=>{const opener=document.querySelector('[data-action="export-evidence"]');opener.focus();opener.click();return {open:!document.querySelector('#evidence-modal').hidden,focus:document.activeElement?.textContent?.trim(),inert:[...document.body.children].filter(x=>x!==document.querySelector('#evidence-modal')&&x.inert).length}})()`);
if(evidence.open&&evidence.inert>0&&evidence.focus)pass('TC-EVIDENCE-001','Evidence','Evidence modal opens, contains focus, and inerts the background',JSON.stringify(evidence));else fail('TC-EVIDENCE-001','Evidence','Evidence modal opens, contains focus, and inerts the background','open/focused/inert',JSON.stringify(evidence),'Critical');
const evidenceClose=await evaluate(`(()=>{document.querySelector('[data-action="evidence-close"]').click();return {closed:document.querySelector('#evidence-modal').hidden,focus:document.activeElement?.getAttribute('data-action'),inert:[...document.body.children].filter(x=>x.inert).length}})()`);
if(evidenceClose.closed&&evidenceClose.focus==='export-evidence'&&evidenceClose.inert===0)pass('TC-EVIDENCE-002','Evidence','Closing evidence restores the opener and background',JSON.stringify(evidenceClose));else fail('TC-EVIDENCE-002','Evidence','Closing evidence restores the opener and background','closed, opener focused, zero inert',JSON.stringify(evidenceClose),'Critical');

// Favorites/recent persistence and storage corruption tolerance.
const fav=await evaluate(`(()=>{const b=document.querySelector('[data-action="fav-toggle"]');b.focus();b.click();const favFocus=document.activeElement?.getAttribute('data-action')==='fav-toggle'&&document.activeElement?.getAttribute('data-favid')===${JSON.stringify(grepEntry.id)};document.querySelector('[data-rail="favorites"]').click();return {home:document.querySelector('#editor-card h2')?.textContent,fav:document.querySelector('#sidebar-body').textContent.includes(${JSON.stringify(grepEntry.intent)}),recent:document.querySelector('#sidebar-body').textContent.includes(${JSON.stringify(grepEntry.intent)}),stored:localStorage.getItem('mdcr.v1.favorites'),favFocus}})()`);
if(fav.home==='What do you need to do?'&&fav.fav&&fav.recent&&fav.stored&&fav.favFocus)pass('TC-STATE-001','State','Favorite persists by ID and its partial re-render retains focus',JSON.stringify(fav));else fail('TC-STATE-001','State','Favorite persists by ID and its partial re-render retains focus','favorite+recent+stored+favorite focus',JSON.stringify(fav),'Major');
await evaluate(`localStorage.setItem('mdcr.v1.favorites','{bad json');sessionStorage.setItem('mdcr.v1.version','bad');location.reload()`);await delay(1100);
const corrupt=await evaluate(`(()=>({home:document.querySelector('#editor-card h2')?.textContent||'',version:document.querySelector('#version-seg [aria-pressed="true"]')?.getAttribute('data-version')||document.querySelector('#version-seg [aria-current="true"]')?.getAttribute('data-version')||document.querySelector('#version-seg input:checked')?.getAttribute('data-version')||'',body:!!document.body}))()`);
if(corrupt.body&&corrupt.home==='What do you need to do?')pass('TC-STATE-002','State','Corrupt storage fails closed without crashing boot',JSON.stringify(corrupt));else fail('TC-STATE-002','State','Corrupt storage fails closed without crashing boot','Home renders',JSON.stringify(corrupt),'Critical');
await evaluate(`(()=>{window.__qa={
  set(sel,value){const e=document.querySelector(sel);if(!e)return {ok:false,reason:'missing'};if(e.disabled)return {ok:false,reason:'disabled'};if(e.type==='checkbox'){e.checked=value==='yes'||value===true}else{e.value=String(value)}e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return {ok:true}},
  open(rail,tool,id,version,intent){
    const vb=document.querySelector('[data-version="'+CSS.escape(version)+'"]');if(!vb)return {ok:false,step:'version'};vb.click();
    const rb=document.querySelector('[data-rail="'+CSS.escape(rail)+'"]');if(!rb)return {ok:false,step:'rail'};rb.click();
    const tb=document.querySelector('[data-tool="'+CSS.escape(tool)+'"]');if(!tb)return {ok:false,step:'tool'};if(tb.getAttribute('aria-current')!=='true')tb.click();
    const eb=document.querySelector('[data-entry="'+CSS.escape(id)+'"]');if(!eb)return {ok:false,step:'entry'};eb.click();return {ok:true}
  },
  command(){return [...document.querySelectorAll('#editor-card .codeline .lc')].map(x=>x.textContent).join('\\n')},
  state(){return {title:document.querySelector('#editor-card h2')?.textContent||'',copy:!!document.querySelector('[data-action="copy"]'),theme:document.documentElement.getAttribute('data-theme')||'',sidebar:document.body.getAttribute('data-sidebar'),inspector:document.body.getAttribute('data-inspector')}}
};return true})()`);

// Rendered contrast checks use computed styles rather than restating tokens.
const baseContrast=await evaluate(`(()=>{function rgba(s){const m=s.match(/[\\d.]+/g).map(Number);return [m[0],m[1],m[2],m.length>3?m[3]:1]}function over(t,b){const a=t[3]+b[3]*(1-t[3]);return [(t[0]*t[3]+b[0]*b[3]*(1-t[3]))/a,(t[1]*t[3]+b[1]*b[3]*(1-t[3]))/a,(t[2]*t[3]+b[2]*b[3]*(1-t[3]))/a,a]}function bg(e){const layers=[];for(let n=e;n;n=n.parentElement)layers.unshift(rgba(getComputedStyle(n).backgroundColor));let out=[255,255,255,1];for(const layer of layers)out=over(layer,out);return out}function lin(v){v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}function lum(v){return .2126*lin(v[0])+.7152*lin(v[1])+.0722*lin(v[2])}function ratio(e,b=e){const a=lum(rgba(getComputedStyle(e).color)),z=lum(bg(b));return (Math.max(a,z)+.05)/(Math.min(a,z)+.05)}document.documentElement.setAttribute('data-theme','dark');const primary=ratio(document.querySelector('.primaryaction'));document.documentElement.setAttribute('data-theme','light');const pressed=ratio(document.querySelector('.panelbtn[aria-pressed="true"]'));return {primary,pressed}})()`);
if(baseContrast.primary>=4.5&&baseContrast.pressed>=4.5)pass('TC-A11Y-CONTRAST-001','Accessibility','Rendered primary and pressed controls meet normal-text contrast',JSON.stringify(baseContrast));else fail('TC-A11Y-CONTRAST-001','Accessibility','Rendered primary and pressed controls meet normal-text contrast','both ratios >= 4.5',JSON.stringify(baseContrast),'Major');
await evaluate(`__qa.open('builder','grep','grep-search-text','8',${JSON.stringify(grepEntry.intent)})`);
const placeholderContrast=await evaluate(`(()=>{function rgb(s){return s.match(/[\\d.]+/g).slice(0,3).map(Number)}function lin(v){v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}function lum(v){return .2126*lin(v[0])+.7152*lin(v[1])+.0722*lin(v[2])}function ratio(a,b){a=lum(a);b=lum(b);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)}const values=[];for(const theme of ['light','dark']){document.documentElement.setAttribute('data-theme',theme);for(const e of [...document.querySelectorAll('#palette-input,input[data-field][placeholder],textarea[data-field][placeholder]')]){const p=getComputedStyle(e,'::placeholder');const c=getComputedStyle(e);values.push({theme,id:e.id||e.getAttribute('data-field'),ratio:ratio(rgb(p.color),rgb(c.backgroundColor)),color:p.color,background:c.backgroundColor})}}return values})()`);
if(placeholderContrast.every(x=>x.ratio>=4.5))pass('TC-A11Y-CONTRAST-003','Accessibility','Rendered placeholder text meets normal-text contrast in both themes',JSON.stringify(placeholderContrast));else fail('TC-A11Y-CONTRAST-003','Accessibility','Rendered placeholder text meets normal-text contrast in both themes','all ratios >= 4.5',JSON.stringify(placeholderContrast),'Major');

// Panel/theme controls and keyboard routes.
const controls=await evaluate(`(()=>{let e=document.querySelector('[data-action="theme"]');e.focus();e.click();const themeFocus=document.activeElement===document.querySelector('[data-action="theme"]');e=document.querySelector('[data-action="panel-sidebar"]');e.focus();e.click();const sideFocus=document.activeElement===document.querySelector('[data-action="panel-sidebar"]');e=document.querySelector('[data-action="panel-inspector"]');e.focus();e.click();const inspFocus=document.activeElement===document.querySelector('[data-action="panel-inspector"]');return {...__qa.state(),themeFocus,sideFocus,inspFocus}})()`);
if(controls.theme&&controls.themeFocus&&controls.sideFocus&&controls.inspFocus)pass('TC-CONTROLS-001','Controls','Theme, Navigator, and Inspector update while preserving focus',JSON.stringify(controls));else fail('TC-CONTROLS-001','Controls','Theme, Navigator, and Inspector update while preserving focus','state changes and focus retained',JSON.stringify(controls),'Major');
const keys=await evaluate(`(()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'2',ctrlKey:true,altKey:true,bubbles:true}));const build=document.querySelector('[data-rail="builder"]').getAttribute('aria-current');document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}));const palette=!document.querySelector('#palette').hidden;document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));const closed=document.querySelector('#palette').hidden;return {build,palette,closed}})()`);
if(keys.build==='true'&&keys.palette&&keys.closed)pass('TC-KEYS-001','Keyboard','Rail jump, search shortcut, and Escape work',JSON.stringify(keys));else fail('TC-KEYS-001','Keyboard','Rail jump, search shortcut, and Escape work','build=true palette opens/closes',JSON.stringify(keys),'Major');
const paletteCommandSetup=await evaluate(`(()=>{document.querySelector('[data-action="palette"]').click();const i=document.querySelector('#palette-input');i.value='journalctl';i.dispatchEvent(new Event('input',{bubbles:true}));i.focus();const options=[...document.querySelectorAll('#palette-results [role="option"]')];return {ready:options.length>1&&(options[1].querySelector('.why')?.textContent||'').includes('Command'),options:options.slice(0,12).map(x=>x.textContent.trim())}})()`);
await pressKey('ArrowDown','ArrowDown');
await pressKey('Enter','Enter');
const paletteFocus=await evaluate(`(()=>{const heading=document.querySelector('#editor-card .tasktitle, #editor-card h2');return {hit:${JSON.stringify(true)},hidden:document.querySelector('#palette').hidden,focused:document.activeElement===heading,active:document.activeElement?.className||document.activeElement?.tagName||'',title:heading?.textContent||''}})()`);
paletteFocus.hit=paletteCommandSetup.ready;paletteFocus.options=paletteCommandSetup.options;
if(paletteFocus.hit&&paletteFocus.hidden&&paletteFocus.focused&&paletteFocus.title!=='No command selected')pass('TC-A11Y-FOCUS-002','Accessibility','Activating a palette command moves focus to the opened task heading',JSON.stringify(paletteFocus));else fail('TC-A11Y-FOCUS-002','Accessibility','Activating a palette command moves focus to the opened task heading','command hit, hidden palette, and opened heading focused',JSON.stringify(paletteFocus),'Major');

// Search semantics and category coverage.
await evaluate(`document.querySelector('[data-action="palette"]').click()`);
for(const [query,label,expectKinds] of [
  ['journalctl','tool/command',['Tool','Command']],
  ['010000','STIG',['STIG']],
  ['CCI-000366','CCI',['CCI']],
  ['AC-2','NIST',['NIST']],
  ['--no-pager','Flag',['Flag']],
  ['subscription-manager','Reference',['Reference']]
]){
  const refreshed=await evaluate(`(()=>{const i=document.querySelector('#palette-input');i.value=${JSON.stringify(query)};i.dispatchEvent(new Event('input',{bubbles:true}));return [...document.querySelectorAll('#palette-results [role="option"]')].slice(0,80).map(x=>({text:x.textContent.trim(),kind:(x.querySelector('.why')?.textContent||'').split(' · ')[0]}))})()`);
  const ok=expectKinds.some(k=>refreshed.some(x=>x.kind===k));
  if(ok)pass(`TC-SEARCH-${label.replace(/\W/g,'').toUpperCase()}`,'Search',`${label} query returns a relevant result`,refreshed.slice(0,4).map(x=>x.text).join(' | '));else fail(`TC-SEARCH-${label.replace(/\W/g,'').toUpperCase()}`,'Search',`${label} query returns a relevant result`,expectKinds.join('/'),refreshed.slice(0,8).map(x=>`${x.kind}:${x.text}`).join(' | '),'Major');
}
await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);

// Reference family hydration and acknowledgement friction.
await evaluate(`document.querySelector('[data-rail="reference"]').click()`);
for(const family of ['stig_rules','raw_captures','redhat_guides']){
  const familyState=await evaluate(`(()=>{const b=document.querySelector('[data-reffam="${family}"]');if(!b)return {button:false,tools:0,records:0};b.click();const tool=document.querySelector('[data-reftool]');if(tool&&tool.getAttribute('aria-current')!=='true')tool.click();return {button:true,tools:document.querySelectorAll('[data-reftool]').length,records:document.querySelectorAll('[data-ref]').length}})()`);
  if(familyState.button&&familyState.tools>0&&familyState.records>0)pass(`TC-REF-FAMILY-${family.toUpperCase()}`,'Reference',`${family} hydrates into browsable tools and records`,JSON.stringify(familyState));else fail(`TC-REF-FAMILY-${family.toUpperCase()}`,'Reference',`${family} hydrates into browsable tools and records`,'button, tools, and records',JSON.stringify(familyState),'Critical');
}
const ref=await evaluate(`(()=>{document.querySelector('[data-rail="reference"]').click();const fam=document.querySelector('[data-reffam]');const before=document.querySelectorAll('[data-ref]').length;if(fam)fam.click();const tool=document.querySelector('[data-reftool]');if(tool&&tool.getAttribute('aria-current')!=='true')tool.click();const rec=document.querySelector('[data-ref]');if(rec)rec.click();return {family:!!fam,tool:!!tool,record:!!rec,before,title:document.querySelector('#editor-card h2')?.textContent||'',ack:!!document.querySelector('[data-action="ref-ack"]'),copyDisabled:!!document.querySelector('[data-action="ref-copy"]')?.disabled,evidence:!!document.querySelector('[data-action="ref-evidence"]')}})()`);
if(ref.family&&ref.tool&&ref.record&&ref.ack&&ref.copyDisabled)pass('TC-REF-001','Reference','Reference family hydrates and unrated copy is gated by acknowledgement',JSON.stringify(ref));else fail('TC-REF-001','Reference','Reference family hydrates and unrated copy is gated by acknowledgement','family/tool/record/ack/disabled copy',JSON.stringify(ref),'Critical');
if(ref.record){
 const ack=await evaluate(`(()=>{const a=document.querySelector('[data-action="ref-ack"]');a.focus();a.click();return {enabled:!document.querySelector('[data-action="ref-copy"]').disabled,evidence:!!document.querySelector('[data-action="ref-evidence"]'),focused:document.activeElement?.getAttribute('data-action')==='ref-ack'}})()`);
 await realClick('[data-action="ref-copy"]');await delay(30);
 const copied=await evaluate(`document.querySelector('.toast')?.textContent||''`);
 await realClick('[data-action="ref-ack"]');
 const cleared=await evaluate(`(()=>({toast:document.querySelector('.toast')?.textContent||'',disabled:!!document.querySelector('[data-action="ref-copy"]')?.disabled,checked:!!document.querySelector('[data-action="ref-ack"]')?.checked}))()`);
 if(ack.enabled&&ack.focused&&copied.includes('Copied')&&!cleared.toast&&cleared.disabled&&!cleared.checked)pass('TC-REF-002','Reference','Reference acknowledgement unlocks copy, and revocation clears stale success state',JSON.stringify({ack,copied,cleared}));else fail('TC-REF-002','Reference','Reference acknowledgement unlocks copy, and revocation clears stale success state','copy enabled; copied status; then unchecked, disabled, and empty status',JSON.stringify({ack,copied,cleared}),'Critical');
}
const governing=await evaluate(`(()=>{document.querySelector('[data-action="palette"]').click();const input=document.querySelector('#palette-input');input.value='aide';input.dispatchEvent(new Event('input',{bubbles:true}));const hit=[...document.querySelectorAll('#palette-results [role="option"]')].find(x=>x.textContent.includes('sudo /usr/sbin/aide --check'));if(hit)hit.click();return {hit:!!hit,title:document.querySelector('#editor-card h2')?.textContent||'',evidence:!!document.querySelector('[data-action="ref-evidence"]')}})()`);
if(governing.evidence)pass('TC-REF-003','Reference','Eligible governing text exposes byte-exact evidence copy',JSON.stringify(governing));else fail('TC-REF-003','Reference','Eligible governing text exposes byte-exact evidence copy','at least one evidence-eligible STIG record',JSON.stringify(governing),'Major');

// Pipeline workflow with a read-only first stage and a root-requiring second
// stage. This proves the composed result retains the strongest privilege and
// does not inherit a receipt or control identity from either catalog entry.
const pipelineExceptionStart=exceptions.length;
const j=entries.find(e=>e.id==='gen-journalctl-unit-logs');
await evaluate(`__qa.open('builder','journalctl','gen-journalctl-unit-logs','8',${JSON.stringify(j.intent)})`);
for(const [n,v] of Object.entries(golden.generators['gen-journalctl-unit-logs'].values))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(n)})+'"]',${JSON.stringify(v)})`);
const pipelineTypedBeforeAdd=await typeCharacters('[data-field="unit"]','x');
await realClick('[data-pipe-action="add"]');
let pipe=await evaluate(`document.querySelector('#pipeline-panel')?.textContent||''`);
if(pipelineTypedBeforeAdd.focused&&(pipe.includes('Stage 1')||pipe.includes('journalctl')))pass('TC-PIPE-001','Pipeline','The first real Add-to-pipeline click after typing creates stage 1',JSON.stringify({typed:pipelineTypedBeforeAdd,panel:pipe.slice(0,220)}));else fail('TC-PIPE-001','Pipeline','The first real Add-to-pipeline click after typing creates stage 1','focused typed field and Stage 1/journalctl after one pointer click',JSON.stringify({typed:pipelineTypedBeforeAdd,panel:pipe.slice(0,300)}),'Major');
const q=entries.find(e=>e.id==='gen-systemctl-manage');
await evaluate(`__qa.open('builder','systemctl','gen-systemctl-manage','8',${JSON.stringify(q.intent)})`);
for(const [n,v] of Object.entries(golden.generators['gen-systemctl-manage'].values))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(n)})+'"]',${JSON.stringify(v)})`);
pipe=await evaluate(`(()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'P',ctrlKey:true,shiftKey:true,bubbles:true}));return document.querySelector('#pipeline-panel')?.textContent||''})()`);
if(pipe.includes('Stage 2')||((pipe.match(/Stage/g)||[]).length>=2))pass('TC-PIPE-002','Pipeline','A second guided command can be added and composed',pipe.slice(0,300));else fail('TC-PIPE-002','Pipeline','A second guided command can be added and composed','two stages',pipe.slice(0,400),'Major');
const pipelineTrust=await evaluate(`(()=>{const edit=document.querySelector('[data-pipe-action="edit"][data-pipe-index="0"]');if(edit)edit.click();const trust=[...document.querySelectorAll('#editor-card .trustfact')].map(x=>x.textContent.trim());const status=document.querySelector('#statusbar')?.textContent||'';const inspector=document.querySelector('#inspector-body')?.textContent||'';const editor=document.querySelector('#editor-card')?.textContent||'';const evidenceButton=document.querySelector('[data-action="export-evidence"]');if(evidenceButton)evidenceButton.click();const evidence=document.querySelector('#evidence-modal-body .evidencepre')?.textContent||'';document.querySelector('[data-action="evidence-close"]')?.click();return {edit:!!edit,trust,status,inspector,editor,evidence}})()`);
const pipelineTrustOk=pipelineTrust.edit&&pipelineTrust.trust.includes('Composed — not host-verified')&&pipelineTrust.status.includes('Composed — not host-verified')&&pipelineTrust.inspector.includes('Pipeline verification')&&pipelineTrust.inspector.includes('Stage 1')&&pipelineTrust.inspector.includes('Stage 2')&&pipelineTrust.inspector.includes('Stage 1 · journalctl')&&pipelineTrust.evidence.includes('Verification (RHEL 8): Composed — not host-verified')&&pipelineTrust.evidence.includes('Requires: root')&&pipelineTrust.evidence.includes('Pipeline STIG/control identity: none')&&!pipelineTrust.evidence.includes('verified by')&&!pipelineTrust.evidence.includes('STIG ID:')&&!pipelineTrust.editor.includes(' · reviewed task');
if(pipelineTrustOk)pass('TC-PIPE-TRUST-001','Pipeline','Pipeline trust signals and evidence remain composed and unverified',JSON.stringify({trust:pipelineTrust.trust,status:pipelineTrust.status.slice(0,180),evidence:pipelineTrust.evidence.slice(0,220)}));else fail('TC-PIPE-TRUST-001','Pipeline','Pipeline trust signals and evidence remain composed and unverified','exact composed status in preview/status/export; per-stage inspector; no borrowed receipt',JSON.stringify(pipelineTrust),'Critical');
const incompletePipeline=await evaluate(`(()=>{document.querySelector('[data-pipe-action="redirect"]')?.click();document.dispatchEvent(new KeyboardEvent('keydown',{key:'e',ctrlKey:true,bubbles:true}));return {editor:document.querySelector('#editor-card')?.textContent||'',result:document.querySelector('#gen-result')?.textContent||'',panel:document.querySelector('#pipeline-panel')?.textContent||'',modalHidden:document.querySelector('#evidence-modal')?.hidden,toast:document.querySelector('.toast')?.textContent||'',stig:(document.querySelector('#stig-panel')?.textContent||'')+(document.querySelector('#print-stig-panel')?.textContent||'')}})()`);
if((incompletePipeline.editor.includes('Complete the pipeline')||incompletePipeline.result.includes('Complete the pipeline'))&&incompletePipeline.panel.includes('Stage 3')&&incompletePipeline.modalHidden&&incompletePipeline.toast.includes('Nothing to export')&&!incompletePipeline.stig.trim())pass('TC-PIPE-INCOMPLETE-001','Pipeline','Incomplete pipeline refuses evidence and exposes no borrowed trust context',JSON.stringify(incompletePipeline).slice(0,500));else fail('TC-PIPE-INCOMPLETE-001','Pipeline','Incomplete pipeline refuses evidence and exposes no borrowed trust context','Complete the pipeline, Stage 3, hidden modal, no STIG, and Nothing to export',JSON.stringify(incompletePipeline),'Critical');
const typedTarget=await typeCharacters('[data-pipe-field="target"][data-pipe-index="2"]','/tmp/x.log');
const typedTargetState=await evaluate(`(()=>({status:document.querySelector('#statusbar')?.textContent||'',command:[...document.querySelectorAll('#editor-card .codeline .lc')].map(x=>x.textContent).join('\\n'),paletteHidden:document.querySelector('#palette').hidden}))()`);
if(typedTarget.value==='/tmp/x.log'&&typedTarget.focused&&typedTarget.paletteHidden&&typedTargetState.status.includes('Composed — not host-verified')&&typedTargetState.command.includes("'/tmp/x.log'")&&exceptions.length===pipelineExceptionStart)pass('TC-PIPE-KEYBOARD-001','Pipeline','Pipeline path accepts character-by-character CDP input without losing focus or throwing',JSON.stringify({typedTarget,typedTargetState}));else fail('TC-PIPE-KEYBOARD-001','Pipeline','Pipeline path accepts character-by-character CDP input without losing focus or throwing','full value, retained focus, composed status, zero exceptions',JSON.stringify({typedTarget,typedTargetState,exceptions:exceptions.slice(pipelineExceptionStart)}),'Critical');
const sensitiveWrite=await evaluate(`(()=>{__qa.set('[data-pipe-field="target"][data-pipe-index="2"]','/root/.bashrc');const trust=[...document.querySelectorAll('#editor-card .trustfact')].map(x=>x.textContent.trim());const banner=document.querySelector('#blast-banner')?.textContent||'';const status=document.querySelector('#statusbar')?.textContent||'';const target=document.querySelector('[data-pipe-field="target"][data-pipe-index="2"]');const row=target?.closest('.stagerow')?.textContent||'';document.dispatchEvent(new KeyboardEvent('keydown',{key:'e',ctrlKey:true,bubbles:true}));const evidence=document.querySelector('#evidence-modal-body .evidencepre')?.textContent||'';document.querySelector('[data-action="evidence-close"]')?.click();return {trust,banner,status,row,evidence}})()`);
if(sensitiveWrite.trust.includes('Destructive')&&sensitiveWrite.banner.includes('File write target')&&!sensitiveWrite.banner.includes('catalogued as blast radius red')&&sensitiveWrite.status.includes('Composed — not host-verified')&&!sensitiveWrite.status.includes('Pipeline incomplete')&&sensitiveWrite.row.includes('red')&&sensitiveWrite.evidence.includes('blast red')&&sensitiveWrite.evidence.includes('Requires: root'))pass('TC-PIPE-WRITE-001','Pipeline','A sensitive shell-startup write is visibly red, explains the target, refreshes status, and keeps root privilege',JSON.stringify({trust:sensitiveWrite.trust,banner:sensitiveWrite.banner,status:sensitiveWrite.status,row:sensitiveWrite.row,evidence:sensitiveWrite.evidence.slice(0,260)}));else fail('TC-PIPE-WRITE-001','Pipeline','A sensitive shell-startup write is visibly red, explains the target, refreshes status, and keeps root privilege','target reason, composed status, red stage, blast red, Requires root',JSON.stringify(sensitiveWrite),'Critical');
const stigEntry=entries.find(e=>e.id==='firewalld-service-active');
const pipelineStig=await evaluate(`(()=>{__qa.open('builder','firewall-cmd','firewalld-service-active','8',${JSON.stringify(stigEntry.intent)});const screen=document.querySelector('#stig-panel')?.textContent||'';const print=document.querySelector('#print-stig-panel')?.textContent||'';document.dispatchEvent(new KeyboardEvent('keydown',{key:'e',ctrlKey:true,bubbles:true}));const evidence=document.querySelector('#evidence-modal-body .evidencepre')?.textContent||'';document.querySelector('[data-action="evidence-close"]')?.click();return {screen,print,evidence}})()`);
if(!pipelineStig.screen.trim()&&!pipelineStig.print.trim()&&pipelineStig.evidence.includes('Pipeline STIG/control identity: none')&&!pipelineStig.evidence.includes('STIG ID:')&&!pipelineStig.evidence.includes('CCI:')&&!pipelineStig.evidence.includes('NIST SP 800-53 controls:'))pass('TC-PIPE-CONTROL-001','Pipeline','Active pipelines suppress selected-entry control identity on screen, print, and export',pipelineStig.evidence.slice(0,280));else fail('TC-PIPE-CONTROL-001','Pipeline','Active pipelines suppress selected-entry control identity on screen, print, and export','empty screen/print STIG panels and explicit none in export',JSON.stringify(pipelineStig),'Critical');
const standaloneStig=await evaluate(`(()=>{document.querySelector('[data-action="palette"]').click();const input=document.querySelector('#palette-input');input.value='010000';input.dispatchEvent(new Event('input',{bubbles:true}));const options=[...document.querySelectorAll('#palette-results [role="option"]')];const hit=options.find(x=>(x.querySelector('.why')?.textContent||'').includes('STIG'));const hitText=hit?.textContent||'';if(hit)hit.click();const panel=document.querySelector('#stig-panel');const rect=panel?.getBoundingClientRect();const style=panel?getComputedStyle(panel):null;const visible=!!(panel&&rect&&rect.width>0&&rect.height>0&&rect.bottom>0&&rect.top<innerHeight&&style.display!=='none'&&style.visibility!=='hidden'&&document.body.getAttribute('data-inspector')==='on');const screen=panel?.textContent||'';const editor=document.querySelector('#editor-card')?.textContent||'';document.dispatchEvent(new KeyboardEvent('keydown',{key:'e',ctrlKey:true,bubbles:true}));const evidence=document.querySelector('#evidence-modal-body .evidencepre')?.textContent||'';document.querySelector('[data-action="evidence-close"]')?.click();return {hit:!!hit,hitText,options:options.slice(0,12).map(x=>x.textContent.trim()),screen,visible,inspector:document.body.getAttribute('data-inspector'),rect:rect?{top:rect.top,bottom:rect.bottom,width:rect.width,height:rect.height}:null,editor,evidence}})()`);
if(standaloneStig.hit&&standaloneStig.visible&&standaloneStig.screen.trim()&&standaloneStig.editor.includes('Inspector panel')&&standaloneStig.evidence.includes('Pipeline STIG/control identity: none')&&!standaloneStig.evidence.includes('STIG ID:'))pass('TC-PIPE-CONTROL-002','Pipeline','A standalone searched STIG is visibly on-screen while pipeline export stays identity-free',JSON.stringify({hit:standaloneStig.hitText,screen:standaloneStig.screen.slice(0,220),visible:standaloneStig.visible,rect:standaloneStig.rect,evidence:standaloneStig.evidence.slice(0,220)}));else fail('TC-PIPE-CONTROL-002','Pipeline','A standalone searched STIG is visibly on-screen while pipeline export stays identity-free','on-screen searched rule and identity-free export',JSON.stringify(standaloneStig),'Major');
const xargsSetup=await evaluate(`(()=>{const s=document.querySelector('#pipekind-1');s.value='xargs';s.dispatchEvent(new Event('change',{bubbles:true}));const c=document.querySelector('[data-pipe-field="replace"][data-pipe-index="1"]');c.focus();c.click();const kept=document.activeElement?.getAttribute('data-pipe-field')==='replace';document.querySelector('[data-pipe-field="replace"][data-pipe-index="1"]').click();return {kept,field:!!document.querySelector('#pipen-1')}})()`);
const typedMax=await typeCharacters('#pipen-1','25');
if(xargsSetup.kept&&xargsSetup.field&&typedMax.value==='25'&&typedMax.focused&&exceptions.length===pipelineExceptionStart)pass('TC-PIPE-KEYBOARD-002','Pipeline','xargs controls retain focus and accept character-by-character batch size input',JSON.stringify({xargsSetup,typedMax}));else fail('TC-PIPE-KEYBOARD-002','Pipeline','xargs controls retain focus and accept character-by-character batch size input','checkbox focus retained, value 25, zero exceptions',JSON.stringify({xargsSetup,typedMax,exceptions:exceptions.slice(pipelineExceptionStart)}),'Critical');
const cleared=await evaluate(`(()=>{const b=document.querySelector('[data-pipe-action="clear"]');if(b)b.click();return document.querySelector('#pipeline-panel')?.textContent||''})()`);
if(!cleared.includes('Stage 1'))pass('TC-PIPE-003','Pipeline','Pipeline Clear action removes all stages',cleared.slice(0,180));else fail('TC-PIPE-003','Pipeline','Pipeline Clear action removes all stages','no stages',cleared.slice(0,300),'Major');
const linkedStigRow=entries.flatMap(e=>(e.stig||[]).map(row=>({entry:e.id,...row}))).find(row=>String(row.rhel_version)==='8');
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
const linkedStig=await evaluate(`(()=>{const id=${JSON.stringify(linkedStigRow?.stig_id||'')};const palette=document.querySelector('#palette');if(palette?.hidden)document.querySelector('[data-action="palette"]').click();const input=document.querySelector('#palette-input');input.value=id.slice(-6);input.dispatchEvent(new Event('input',{bubbles:true}));const hit=[...document.querySelectorAll('#palette-results [role="option"]')].find(x=>(x.querySelector('.why')?.textContent||'').includes('STIG'));if(hit)hit.click();const panel=document.querySelector('#stig-panel');const rect=panel?.getBoundingClientRect();return {found:!!hit,id,inspector:document.body.getAttribute('data-inspector'),visible:!!(panel&&rect&&rect.width>0&&rect.height>0&&rect.top>=0&&rect.top<innerHeight&&getComputedStyle(panel).display!=='none'),focused:document.activeElement===panel,text:panel?.textContent||'',title:document.querySelector('#editor-card h2')?.textContent||'',rect:rect?{top:rect.top,bottom:rect.bottom}:null,innerHeight}})()`);
await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
if(linkedStig.found&&linkedStig.inspector==='on'&&linkedStig.visible&&linkedStig.focused&&linkedStig.text.includes(linkedStig.id)&&linkedStig.title!=='No command selected')pass('TC-STIG-SELECT-001','Accessibility','A searched STIG linked to a command opens visibly and focused at 390px',JSON.stringify(linkedStig));else fail('TC-STIG-SELECT-001','Accessibility','A searched STIG linked to a command opens visibly and focused at 390px','linked command, Inspector on, focused in-viewport STIG panel',JSON.stringify(linkedStig),'Major');
if(exceptions.length===pipelineExceptionStart)pass('TC-PIPE-004','Pipeline','Pipeline composition does not raise a runtime exception','0');else fail('TC-PIPE-004','Pipeline','Pipeline composition does not raise a runtime exception','0',exceptions.slice(pipelineExceptionStart).join('\n\n'),'Critical');

// Isolate later workflows from any pipeline state left by a failure.
await send('Page.navigate',{url:baseUrl});await delay(800);
await evaluate(`(()=>{window.__qa={
  set(sel,value){const e=document.querySelector(sel);if(!e)return {ok:false,reason:'missing'};if(e.disabled)return {ok:false,reason:'disabled'};if(e.type==='checkbox'){e.checked=value==='yes'||value===true}else{e.value=String(value)}e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return {ok:true}},
  open(rail,tool,id,version,intent){const vb=document.querySelector('[data-version="'+CSS.escape(version)+'"]');if(!vb)return {ok:false,step:'version'};vb.click();const rb=document.querySelector('[data-rail="'+CSS.escape(rail)+'"]');if(!rb)return {ok:false,step:'rail'};rb.click();const tb=document.querySelector('[data-tool="'+CSS.escape(tool)+'"]');if(!tb)return {ok:false,step:'tool'};if(tb.getAttribute('aria-current')!=='true')tb.click();const eb=document.querySelector('[data-entry="'+CSS.escape(id)+'"]');if(!eb)return {ok:false,step:'entry'};eb.click();return {ok:true}},
  command(){return [...document.querySelectorAll('#editor-card .codeline .lc')].map(x=>x.textContent).join('\\n')}
};return true})()`);

// A generator receipt applies only to the byte-exact captured command. The
// same form with one changed value must immediately lose the Verified label.
const receiptEntry=entries.find(e=>e.id==='gen-journalctl-unit-logs');
await evaluate(`__qa.open('builder','journalctl','gen-journalctl-unit-logs','8',${JSON.stringify(receiptEntry.intent)})`);
for(const [n,v] of Object.entries(golden.generators['gen-journalctl-unit-logs'].values))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(n)})+'"]',${JSON.stringify(v)})`);
const receiptExact=await evaluate(`(()=>({status:document.querySelector('#statusbar')?.textContent||'',inspector:document.querySelector('#inspector-body')?.textContent||'',live:document.querySelector('#gen-announcement')?.getAttribute('aria-live')||'',atomic:document.querySelector('#gen-announcement')?.getAttribute('aria-atomic')||'',resultLive:document.querySelector('#gen-result')?.getAttribute('aria-live')}))()`);
await evaluate(`__qa.set('[data-field="unit"]','httpd.service')`);
const receiptChanged=await evaluate(`(()=>({status:document.querySelector('#statusbar')?.textContent||'',inspector:document.querySelector('#inspector-body')?.textContent||''}))()`);
if(receiptExact.status.includes('Verified')&&receiptExact.inspector.includes('this exact command was verified by')&&receiptChanged.status.includes('Not host-verified')&&receiptChanged.inspector.includes('current command differs')&&!receiptChanged.inspector.includes('this exact command was verified by'))pass('TC-RECEIPT-001','Verification','A receipt is bound to the exact captured generator command',JSON.stringify({exact:receiptExact.status,changed:receiptChanged.status}));else fail('TC-RECEIPT-001','Verification','A receipt is bound to the exact captured generator command','golden values Verified; changed unit Not host-verified',JSON.stringify({receiptExact,receiptChanged}),'Critical');
if(receiptExact.live==='polite'&&receiptExact.atomic==='true'&&receiptExact.resultLive===null)pass('TC-A11Y-LIVE-001','Accessibility','Command completion uses a concise dedicated live region',JSON.stringify(receiptExact));else fail('TC-A11Y-LIVE-001','Accessibility','Command completion uses a concise dedicated live region','polite atomic announcement; command review is not live',JSON.stringify(receiptExact),'Major');

// Document generator copy contract.
const cfg=entries.find(e=>e.id==='gen-ansible-cfg');
await evaluate(`__qa.open('ansible','ansible-config','gen-ansible-cfg','8',${JSON.stringify(cfg.intent)})`);
for(const [n,v] of Object.entries(golden.generators['gen-ansible-cfg'].values))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(n)})+'"]',${JSON.stringify(v)})`);
const docState=await evaluate(`(()=>({command:__qa.command(),preview:document.querySelector('[aria-label="Generated file preview"]')?.textContent||'',copyDoc:document.querySelector('[data-action="copy-doc"]')?.textContent||''}))()`);
if(docState.command===golden.generators['gen-ansible-cfg'].commands['8']&&docState.preview&&docState.copyDoc)pass('TC-DOC-001','Generated files','Document generator renders command, file preview, and copy action',JSON.stringify({command:docState.command,copyDoc:docState.copyDoc,preview:docState.preview.slice(0,100)}));else fail('TC-DOC-001','Generated files','Document generator renders command, file preview, and copy action','golden command + preview + copy',JSON.stringify(docState),'Critical');

// Invalid input must remain visibly refused in the rendered workflow.
const useradd=entries.find(e=>e.id==='gen-useradd-create');
await evaluate(`__qa.open('builder','useradd','gen-useradd-create','8',${JSON.stringify(useradd.intent)})`);
await evaluate(`__qa.set('[data-field="username"]','<script>')`);
const invalid=await evaluate(`(()=>({command:__qa.command(),copy:!!document.querySelector('[data-action="copy"]'),text:document.querySelector('#gen-result')?.textContent||''}))()`);
if(!invalid.command&&!invalid.copy&&invalid.text.includes('username'))pass('TC-INPUT-001','Validation','Invalid generator input is refused with a field-specific explanation',invalid.text.slice(0,220));else fail('TC-INPUT-001','Validation','Invalid generator input is refused with a field-specific explanation','no command/copy and username error',JSON.stringify(invalid),'Critical');

// Runbook binding uses deliberately non-golden values so copied guidance
// cannot accidentally pass while still naming the example PID/path/account.
const killEntry=entries.find(e=>e.id==='kill-send-signal');
await evaluate(`__qa.open('builder','kill','kill-send-signal','8',${JSON.stringify(killEntry.intent)})`);
const killExceptionStart=exceptions.length;
const killTyped=await typeCharacters('[data-field="pid"]','54321');
const killReady=await evaluate(`(()=>({plan:document.querySelector('#gen-result .opplan')?.textContent||'',announcement:document.querySelector('#gen-announcement')?.textContent||''}))()`);
if(killReady.plan.includes('54321')&&!killReady.plan.includes('12345')&&killTyped.value==='54321'&&killTyped.focused)pass('TC-RUNBOOK-001','Runbook','Process preflight binds a PID entered with real keystrokes',JSON.stringify({typed:killTyped,plan:killReady.plan.slice(0,220)}));else fail('TC-RUNBOOK-001','Runbook','Process preflight binds a PID entered with real keystrokes','54321, focused input, and no golden 12345',JSON.stringify({killTyped,killReady}),'Critical');
if(killReady.announcement.includes('Command ready')&&exceptions.length===killExceptionStart)pass('TC-A11Y-LIVE-002','Accessibility','The first completion of a single-field form announces that the command is ready',killReady.announcement);else fail('TC-A11Y-LIVE-002','Accessibility','The first completion of a single-field form announces that the command is ready','Command ready announcement and zero exceptions',JSON.stringify({killReady,exceptions:exceptions.slice(killExceptionStart)}),'Major');
const gitDiscard=entries.find(e=>e.id==='git-checkout-discard-changes');
await evaluate(`__qa.open('git','git','git-checkout-discard-changes','8',${JSON.stringify(gitDiscard.intent)})`);
await evaluate(`__qa.set('[data-field="path"]','config/prod.yml')`);
const gitPlan=await evaluate(`document.querySelector('#gen-result .opplan')?.textContent||''`);
if(gitPlan.includes('git diff -- config/prod.yml')&&!gitPlan.includes('src/app.py'))pass('TC-RUNBOOK-002','Runbook','Destructive Git preflight binds the current path',gitPlan.slice(0,240));else fail('TC-RUNBOOK-002','Runbook','Destructive Git preflight binds the current path','config/prod.yml and no golden src/app.py',gitPlan.slice(0,300),'Critical');
const gitTypedBeforeAck=await typeCharacters('[data-field="path"]','x');
await realClick('[data-action="ack"]');
const gitAck=await evaluate(`(()=>({enabled:!document.querySelector('[data-action="copy"]').disabled,focused:document.activeElement?.getAttribute('data-action')==='ack',checked:!!document.querySelector('[data-action="ack"]')?.checked,toast:document.querySelector('.toast')?.textContent||''}))()`);
await realClick('[data-action="copy"]');await delay(30);
const gitCopiedToast=await evaluate(`document.querySelector('.toast')?.textContent||''`);
await realClick('[data-action="ack"]');
const gitUnacked=await evaluate(`(()=>({checked:!!document.querySelector('[data-action="ack"]')?.checked,copyDisabled:!!document.querySelector('[data-action="copy"]')?.disabled,toast:document.querySelector('.toast')?.textContent||''}))()`);
await realClick('[data-action="ack"]');
const gitEdited=await typeCharacters('[data-field="path"]','y');
const gitAckAfterEdit=await evaluate(`(()=>({checked:!!document.querySelector('[data-action="ack"]')?.checked,copyDisabled:!!document.querySelector('[data-action="copy"]')?.disabled,toast:document.querySelector('.toast')?.textContent||'',command:__qa.command()}))()`);
if(gitTypedBeforeAck.value==='config/prod.ymlx'&&gitAck.enabled&&gitAck.focused&&gitAck.checked&&!gitAck.toast&&gitCopiedToast.includes('Copied')&&!gitUnacked.checked&&gitUnacked.copyDisabled&&!gitUnacked.toast&&gitEdited.value==='config/prod.ymlxy'&&gitEdited.focused&&!gitAckAfterEdit.checked&&gitAckAfterEdit.copyDisabled&&!gitAckAfterEdit.toast&&gitAckAfterEdit.command.includes('config/prod.ymlxy'))pass('TC-BLAST-ACK-001','Safety','Acknowledgement revocation and later edits clear real copy-success state',JSON.stringify({gitTypedBeforeAck,gitAck,gitCopiedToast,gitUnacked,gitEdited,gitAckAfterEdit}));else fail('TC-BLAST-ACK-001','Safety','Acknowledgement revocation and later edits clear real copy-success state','copy creates success; uncheck and later edit each clear it and disable copy',JSON.stringify({gitTypedBeforeAck,gitAck,gitCopiedToast,gitUnacked,gitEdited,gitAckAfterEdit}),'Critical');
const dangerContrast=await evaluate(`(()=>{function rgba(s){const m=s.match(/[\\d.]+/g).map(Number);return [m[0],m[1],m[2],m.length>3?m[3]:1]}function over(t,b){const a=t[3]+b[3]*(1-t[3]);return [(t[0]*t[3]+b[0]*b[3]*(1-t[3]))/a,(t[1]*t[3]+b[1]*b[3]*(1-t[3]))/a,(t[2]*t[3]+b[2]*b[3]*(1-t[3]))/a,a]}function bg(e){const layers=[];for(let n=e;n;n=n.parentElement)layers.unshift(rgba(getComputedStyle(n).backgroundColor));let out=[255,255,255,1];for(const layer of layers)out=over(layer,out);return out}function lin(v){v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}function lum(v){return .2126*lin(v[0])+.7152*lin(v[1])+.0722*lin(v[2])}document.documentElement.setAttribute('data-theme','light');const h=document.querySelector('#blast-banner .blast h2'),box=h?.closest('.blast');if(!h||!box)return 0;const a=lum(rgba(getComputedStyle(h).color)),b=lum(bg(box));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)})()`);
if(dangerContrast>=4.5)pass('TC-A11Y-CONTRAST-002','Accessibility','The light-theme destructive warning heading meets normal-text contrast',dangerContrast);else fail('TC-A11Y-CONTRAST-002','Accessibility','The light-theme destructive warning heading meets normal-text contrast','ratio >= 4.5',dangerContrast,'Major');
const curlEntry=entries.find(e=>e.id==='curl-transfer-url');
await evaluate(`__qa.open('builder','curl','curl-transfer-url','8',${JSON.stringify(curlEntry.intent)});__qa.set('[data-field="url"]','https://example.invalid/pkg.rpm');__qa.set('[data-field="output"]','/tmp/pkg.rpm')`);
const downloadPlan=await evaluate(`document.querySelector('#gen-result .opplan')?.textContent||''`);
if(downloadPlan.includes('/tmp/pkg.rpm.mdcr-before-download')&&downloadPlan.includes('did not exist before')&&!downloadPlan.includes('Remove the downloaded file if it is not needed'))pass('TC-RUNBOOK-DOWNLOAD-001','Runbook','Download recovery preserves a pre-existing output before offering removal',downloadPlan.slice(0,500));else fail('TC-RUNBOOK-DOWNLOAD-001','Runbook','Download recovery preserves a pre-existing output before offering removal','bound backup path and removal only for a newly created file',downloadPlan.slice(0,800),'Critical');
const scpEntry=entries.find(e=>e.id==='scp-secure-copy');
await evaluate(`__qa.open('builder','scp','scp-secure-copy','8',${JSON.stringify(scpEntry.intent)});__qa.set('[data-field="source"]','/etc/app/config.yml');__qa.set('[data-field="destination"]','alice@server.example.test:/tmp/config.yml')`);
const scpPlan=await evaluate(`document.querySelector('#gen-result .opplan')?.textContent||''`);
if(scpPlan.includes('sh -s --')&&scpPlan.includes('MDCR_SCP_PREFLIGHT')&&scpPlan.includes('txn=$target.mdcr-scp.txn')&&scpPlan.includes('symlinked SCP')&&scpPlan.includes('MDCR_SCP_RECOVER')&&scpPlan.includes('MDCR_SCP_FINALIZE')&&!scpPlan.includes('<remote_'))pass('TC-RUNBOOK-REMOTE-001','Runbook','SCP renders a bound transaction with symlink refusal, recovery, and finalization',scpPlan.slice(0,700));else fail('TC-RUNBOOK-REMOTE-001','Runbook','SCP renders a bound transaction with symlink refusal, recovery, and finalization','sh -s script, transaction state, symlink refusal, recover/finalize, no placeholders',scpPlan.slice(0,1600),'Critical');
const rsyncEntry=entries.find(e=>e.id==='rsync-sync-files');
await evaluate(`__qa.open('builder','rsync','rsync-sync-files','8',${JSON.stringify(rsyncEntry.intent)});__qa.set('[data-field="source"]','/srv/dotfiles/.config');__qa.set('[data-field="destination"]','alice@server.example.test:/home/alice/.config')`);
const rsyncPlan=await evaluate(`(()=>({text:document.querySelector('#gen-result .opplan')?.textContent||'',risk:document.querySelector('#gen-result .risk-red')?.textContent||''}))()`);
if(rsyncPlan.text.includes('sh -s --')&&rsyncPlan.text.includes('MDCR_RSYNC_PREFLIGHT')&&rsyncPlan.text.includes('txn=$target.mdcr-rsync.txn')&&rsyncPlan.text.includes('symlinked rsync')&&rsyncPlan.text.includes('insufficient free space')&&rsyncPlan.text.includes('MDCR_RSYNC_RECOVER')&&rsyncPlan.text.includes('MDCR_RSYNC_FINALIZE')&&!rsyncPlan.text.includes('<remote_')&&rsyncPlan.risk.includes('Destructive'))pass('TC-RUNBOOK-REMOTE-002','Runbook','Rsync renders a symlink-refusing, capacity-checked transaction and an ambiguous source is red',JSON.stringify({risk:rsyncPlan.risk,text:rsyncPlan.text.slice(0,700)}));else fail('TC-RUNBOOK-REMOTE-002','Runbook','Rsync renders a symlink-refusing, capacity-checked transaction and an ambiguous source is red','bound transaction protocol, symlink/capacity refusal, recover/finalize, red risk',JSON.stringify({risk:rsyncPlan.risk,text:rsyncPlan.text.slice(0,1600)}),'Critical');
const nmcliEntry=entries.find(e=>e.id==='gen-nmcli-static-ipv4');
await evaluate(`__qa.open('builder','nmcli','gen-nmcli-static-ipv4','8',${JSON.stringify(nmcliEntry.intent)});__qa.set('[data-field="con"]','Wired connection 1');__qa.set('[data-field="ifname"]','eth0');__qa.set('[data-field="address"]','192.168.1.50/24');__qa.set('[data-field="gateway"]','192.168.1.1')`);
const nmcliPlan=await evaluate(`document.querySelector('#gen-result .opplan')?.textContent||''`);
if(nmcliPlan.includes("nmcli connection show 'Wired connection 1'")&&nmcliPlan.includes("sudo sh -s -- 'Wired connection 1'")&&nmcliPlan.includes('FILENAME,NAME,UUID')&&nmcliPlan.includes('/var/tmp/mdcr-nmcli-static-ipv4.txn')&&nmcliPlan.includes('MDCR_NMCLI_RECOVER')&&nmcliPlan.includes('MDCR_NMCLI_FINALIZE')&&!nmcliPlan.includes('connection show Wired connection 1'))pass('TC-RUNBOOK-NMCLI-001','Runbook','NetworkManager runbook quotes a space-bearing name and uses an external profile transaction',nmcliPlan.slice(0,900));else fail('TC-RUNBOOK-NMCLI-001','Runbook','NetworkManager runbook quotes a space-bearing name and uses an external profile transaction','quoted name, documented list fields, external transaction, recover/finalize',nmcliPlan.slice(0,1800),'Critical');
const usermod=entries.find(e=>e.id==='r-usermod-ag');
await evaluate(`__qa.open('builder','usermod','r-usermod-ag','8',${JSON.stringify(usermod.intent)})`);
await evaluate(`__qa.set('[data-field="groups"]','docker');__qa.set('[data-field="username"]','bob')`);
const userPlan=await evaluate(`(()=>{const p=document.querySelector('#gen-result .opplan');const recover=[...document.querySelectorAll('[data-plan-step]')].find(x=>x.getAttribute('data-plan-step')==='recover');return {text:p?.textContent||'',recoverDisabled:!!recover?.disabled}})()`);
if(userPlan.text.includes('id bob')&&userPlan.text.includes('docker')&&!userPlan.text.includes('id alice')&&userPlan.recoverDisabled)pass('TC-RUNBOOK-003','Runbook','User/group guidance binds current values and blocks unresolved recovery',JSON.stringify(userPlan));else fail('TC-RUNBOOK-003','Runbook','User/group guidance binds current values and blocks unresolved recovery','bob/docker, no alice, disabled unresolved recovery',JSON.stringify(userPlan),'Critical');

// Home task cards are direct, functioning routes into reviewed work.
await send('Page.navigate',{url:baseUrl});await delay(650);
const homeCards=await evaluate(`(()=>{const cards=[...document.querySelectorAll('.homepanel [data-entry]')];const ids=cards.map(x=>x.getAttribute('data-entry'));const outcomes=[];for(const id of ids){document.querySelector('[data-rail="favorites"]').click();const card=document.querySelector('.homepanel [data-entry="'+CSS.escape(id)+'"]');if(!card){outcomes.push(false);continue}card.click();outcomes.push(document.body.getAttribute('data-selection-open')==='true'&&!!document.querySelector('#editor-card h2'))}return {ids,outcomes}})()`);
if(homeCards.ids.length===6&&homeCards.outcomes.every(Boolean))pass('TC-HOME-001','Home','All six common-task cards open reviewed work',JSON.stringify(homeCards));else fail('TC-HOME-001','Home','All six common-task cards open reviewed work','6 successful task routes',JSON.stringify(homeCards),'Major');
const homePackageRoutes=await evaluate(`(()=>{document.querySelector('[data-rail="favorites"]').click();document.querySelector('[data-version="7"]').click();const r7=document.querySelector('.homepanel [data-entry="gen-yum-package"]')?.getAttribute('data-entry')||'';document.querySelector('[data-version="8"]').click();const r8=document.querySelector('.homepanel [data-entry="gen-dnf-package"]')?.getAttribute('data-entry')||'';return {r7,r8}})()`);
if(homePackageRoutes.r7==='gen-yum-package'&&homePackageRoutes.r8==='gen-dnf-package')pass('TC-HOME-002','Home','Package task routes to a guided form for each release family',JSON.stringify(homePackageRoutes));else fail('TC-HOME-002','Home','Package task routes to a guided form for each release family','RHEL 7 yum generator and RHEL 8 dnf generator',JSON.stringify(homePackageRoutes),'Major');
const focusRoutes=await evaluate(`(()=>{document.querySelector('[data-rail="favorites"]').click();const card=document.querySelector('.homepanel [data-entry]');card.focus();card.click();const afterHome={tag:document.activeElement?.tagName||'',body:document.activeElement===document.body};const sidebar=document.querySelector('#sidebar-body [data-entry]');sidebar.focus();sidebar.click();const afterSidebar={tag:document.activeElement?.tagName||'',body:document.activeElement===document.body};const version=document.querySelector('[data-version="9"]');version.focus();version.click();const afterVersion={tag:document.activeElement?.tagName||'',body:document.activeElement===document.body,value:document.activeElement?.getAttribute('data-version')||''};return {afterHome,afterSidebar,afterVersion}})()`);
if(!focusRoutes.afterHome.body&&!focusRoutes.afterSidebar.body&&!focusRoutes.afterVersion.body&&focusRoutes.afterVersion.value==='9')pass('TC-A11Y-FOCUS-001','Accessibility','Home, sidebar, and release re-renders preserve a useful focus target',JSON.stringify(focusRoutes));else fail('TC-A11Y-FOCUS-001','Accessibility','Home, sidebar, and release re-renders preserve a useful focus target','focus never falls to body; release 9 remains focused',JSON.stringify(focusRoutes),'Major');

// Responsive viewport matrix. Reload Home for each width, then selected command layout.
for(const width of [320,390,768,1024,1440]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<=440,screenWidth:width,screenHeight:900});
  await send('Page.navigate',{url:baseUrl});await delay(650);
  const homeSize=await evaluate(`(()=>({innerWidth,doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,allVersions:[...document.querySelectorAll('[data-version]')].every(x=>x.getBoundingClientRect().right<=innerWidth+1)}))()`);
  if(homeSize.doc<=homeSize.innerWidth&&homeSize.body<=homeSize.innerWidth&&homeSize.allVersions)pass(`TC-RESP-${width}-HOME`,'Responsive',`Home fits ${width}px without horizontal overflow`,JSON.stringify(homeSize));else fail(`TC-RESP-${width}-HOME`,'Responsive',`Home fits ${width}px without horizontal overflow`,`scrollWidth<=${width}; versions visible`,JSON.stringify(homeSize),'Major');
  await evaluate(`document.querySelector('[data-entry="gen-lsblk-inspect-storage"]')?.click()`);
  const selected=await evaluate(`(()=>({doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,innerWidth,editorY:document.querySelector('#editor')?.getBoundingClientRect().y,sidebarY:document.querySelector('#sidebar')?.getBoundingClientRect().y,selection:document.body.getAttribute('data-selection-open')}))()`);
  const orderOk=width>720||selected.editorY<=selected.sidebarY;
  if(selected.doc<=selected.innerWidth&&selected.body<=selected.innerWidth&&orderOk)pass(`TC-RESP-${width}-SELECTED`,'Responsive',`Selected task fits ${width}px and uses expected reading order`,JSON.stringify(selected));else fail(`TC-RESP-${width}-SELECTED`,'Responsive',`Selected task fits ${width}px and uses expected reading order`,'no overflow; editor first on narrow view',JSON.stringify(selected),'Major');
}

// High-confidence non-editable placeholder inventory.
const placeholderChecks=[
  ['grep-search-text','pattern'],['kill-send-signal','12345'],['curl-transfer-url','example.invalid'],['wget-download-url','example.invalid'],
  ['ssh-remote-shell','user@host'],['scp-secure-copy','user@host'],['rsync-sync-files','user@host'],['git-checkout-discard-changes','path/to/file'],
  ['git-recovery-wrong-branch','<hash>'],['git-recovery-lost-commit','<hash>'],['r-id','alice'],['r-usermod-ag','alice'],
  ['export-shell-variable','/opt/tool/bin'],['tr-translate-characters','dos.txt']
];
for(const [id,token] of placeholderChecks){
 const e=entries.find(x=>x.id===id);if(!e)continue;
 if(Object.hasOwn(e,'template')&&(e.fields||[]).length) pass(`TC-PARAM-${id}`,'Task completion',`${id} represents user-specific data as editable fields`,`${e.fields.length} guided field(s)`); else fail(`TC-PARAM-${id}`,'Task completion',`${id} represents user-specific data as editable fields`,`guided fields replacing ${token}`,'static Copy command with zero fields','Major');
}

const testPlan=fs.readFileSync(path.join(repo,'docs/TEST_PLAN.md'),'utf8');
const architecture=fs.readFileSync(path.join(repo,'docs/ARCHITECTURE_BIBLE.md'),'utf8');
const redCount=entries.filter(e=>e.blast==='red').length;
if(redCount>0&&testPlan.includes('no entry in this shipped build is rated\nred'))fail('TC-DOCS-001','Documentation','Test plan accurately describes observable red-rated content',`${redCount} red-rated entries and current generator counts`,'Claims no entry is red; also retains pre-alpha.6 generator/check counts','Major');else pass('TC-DOCS-001','Documentation','Test plan accurately describes observable red-rated content',`${redCount} red entries`);
const auditUnit=Number(process.env.AUDIT_UNIT_TESTS||0);
const auditHostile=Number(process.env.AUDIT_HOSTILE_CHECKS||0);
const auditPipeline=Number(process.env.AUDIT_PIPELINE_CHECKS||0);
const fmt=n=>n.toLocaleString('en-US');
const docsCountsOk=auditUnit>0&&auditHostile>0&&auditPipeline>0&&architecture.includes(`${fmt(auditUnit)} unittest cases and ${fmt(auditHostile)} harness checks`)&&testPlan.includes(`${fmt(auditPipeline)} hostile-vector checks`);
if(docsCountsOk)pass('TC-DOCS-002','Documentation','Architecture and test-plan counts match the suite values supplied to this audit',`${fmt(auditUnit)} unit; ${fmt(auditHostile)} hostile; ${fmt(auditPipeline)} pipeline`);else fail('TC-DOCS-002','Documentation','Architecture and test-plan counts match the suite values supplied to this audit','AUDIT_* counts present and exact values in docs',JSON.stringify({auditUnit,auditHostile,auditPipeline,architectureHas:auditUnit>0&&auditHostile>0?architecture.includes(`${fmt(auditUnit)} unittest cases and ${fmt(auditHostile)} harness checks`):false,testPlanHas:auditPipeline>0?testPlan.includes(`${fmt(auditPipeline)} hostile-vector checks`):false}),'Minor');

// Console/runtime health and memory/performance observations.
const perf=await evaluate(`(()=>({heap:performance.memory?performance.memory.usedJSHeapSize:null,resources:performance.getEntriesByType('resource').length,nav:performance.getEntriesByType('navigation')[0]?{dom:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,load:performance.getEntriesByType('navigation')[0].loadEventEnd}:null}))()`);
record('TC-PERF-002','Performance','Browser performance observation','PASS','informational',JSON.stringify(perf));
if(exceptions.length===0&&consoleErrors.length===0)pass('TC-CONSOLE-001','Reliability','No runtime exceptions or console errors occurred during the audit','0');else fail('TC-CONSOLE-001','Reliability','No runtime exceptions or console errors occurred during the audit','0',JSON.stringify({exceptions,consoleErrors}),'Critical');

const summary={total:results.length,pass:results.filter(x=>x.status==='PASS').length,fail:results.filter(x=>x.status==='FAIL').length,bySeverity:{}};
for(const r of results.filter(x=>x.status==='FAIL'))summary.bySeverity[r.severity]=(summary.bySeverity[r.severity]||0)+1;
const output={meta:{tool:'MD CODE RED',version:'v1.0.0-alpha.6',date:'2026-10-01',browser:'Google Chrome headless via CDP',url:baseUrl,commit:process.env.AUDIT_COMMIT||'',artifactBytes:artifactBytes.length,artifactSha256,contentFingerprint,entries:entries.length,generators:entries.filter(e=>Object.hasOwn(e,'template')).length,staticEntries:entries.filter(e=>!Object.hasOwn(e,'template')).length},summary,exceptions,consoleErrors,results};
fs.writeFileSync('/tmp/mdcr_functional_audit_results.json',JSON.stringify(output,null,2));
console.log(JSON.stringify(summary));
ws.close();
