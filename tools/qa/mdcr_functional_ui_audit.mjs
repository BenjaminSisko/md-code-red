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

const repo = process.argv[2] || process.cwd();
const baseUrl = process.argv[3] || 'http://127.0.0.1:8878/dist/md-code-red_v1.0.0-alpha.6.html';
const cdpPort = Number(process.argv[4] || 9232);
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

// Reproduce the grep task discovered by the user.
const grepEntry=entries.find(e=>e.id==='grep-search-text');
await evaluate(`__qa.open('builder','grep','grep-search-text','8',${JSON.stringify(grepEntry.intent)})`);
const grepValues=golden.generators['grep-search-text'].values;
for(const [name,value] of Object.entries(grepValues))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(name)})+'"]',${JSON.stringify(value)})`);
const grepExpected=golden.generators['grep-search-text'].commands['8'];
const grepState=await evaluate(`(()=>({command:__qa.command(),fields:document.querySelectorAll('[data-field]').length,flagControls:document.querySelectorAll('select[data-field],input[data-field]').length}))()`);
if(grepState.command===grepExpected&&grepState.fields===grepEntry.fields.length&&grepState.flagControls>=3) pass('TC-TASK-GREP-001','Task completion','Build a flagged grep search for “laundry”',JSON.stringify(grepState)); else fail('TC-TASK-GREP-001','Task completion','Build a flagged grep search for “laundry”',grepExpected+' with editable pattern, target, and flags',JSON.stringify(grepState),'Major');

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
const evidence=await evaluate(`(()=>{const opener=document.querySelector('[data-action="export-evidence"]');opener.focus();opener.click();return {open:!document.querySelector('#evidence-modal').hidden,focus:document.activeElement?.textContent?.trim(),inert:[...document.body.children].filter(x=>x!==document.querySelector('#evidence-modal')&&x.inert).length}})()`);
if(evidence.open&&evidence.inert>0&&evidence.focus)pass('TC-EVIDENCE-001','Evidence','Evidence modal opens, contains focus, and inerts the background',JSON.stringify(evidence));else fail('TC-EVIDENCE-001','Evidence','Evidence modal opens, contains focus, and inerts the background','open/focused/inert',JSON.stringify(evidence),'Critical');
const evidenceClose=await evaluate(`(()=>{document.querySelector('[data-action="evidence-close"]').click();return {closed:document.querySelector('#evidence-modal').hidden,focus:document.activeElement?.getAttribute('data-action'),inert:[...document.body.children].filter(x=>x.inert).length}})()`);
if(evidenceClose.closed&&evidenceClose.focus==='export-evidence'&&evidenceClose.inert===0)pass('TC-EVIDENCE-002','Evidence','Closing evidence restores the opener and background',JSON.stringify(evidenceClose));else fail('TC-EVIDENCE-002','Evidence','Closing evidence restores the opener and background','closed, opener focused, zero inert',JSON.stringify(evidenceClose),'Critical');

// Favorites/recent persistence and storage corruption tolerance.
const fav=await evaluate(`(()=>{const b=document.querySelector('[data-action="fav-toggle"]');b.click();document.querySelector('[data-rail="favorites"]').click();return {home:document.querySelector('#editor-card h2')?.textContent,fav:document.querySelector('#sidebar-body').textContent.includes(${JSON.stringify(grepEntry.intent)}),recent:document.querySelector('#sidebar-body').textContent.includes(${JSON.stringify(grepEntry.intent)}),stored:localStorage.getItem('mdcr.v1.favorites')}})()`);
if(fav.home==='What do you need to do?'&&fav.fav&&fav.recent&&fav.stored)pass('TC-STATE-001','State','Favorite and recent work appear on Home and persist by ID',JSON.stringify(fav));else fail('TC-STATE-001','State','Favorite and recent work appear on Home and persist by ID','favorite+recent+stored',JSON.stringify(fav),'Major');
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

// Panel/theme controls and keyboard routes.
const controls=await evaluate(`(()=>{let e=document.querySelector('[data-action="theme"]');e.focus();e.click();const themeFocus=document.activeElement===document.querySelector('[data-action="theme"]');e=document.querySelector('[data-action="panel-sidebar"]');e.focus();e.click();const sideFocus=document.activeElement===document.querySelector('[data-action="panel-sidebar"]');e=document.querySelector('[data-action="panel-inspector"]');e.focus();e.click();const inspFocus=document.activeElement===document.querySelector('[data-action="panel-inspector"]');return {...__qa.state(),themeFocus,sideFocus,inspFocus}})()`);
if(controls.theme&&controls.themeFocus&&controls.sideFocus&&controls.inspFocus)pass('TC-CONTROLS-001','Controls','Theme, Navigator, and Inspector update while preserving focus',JSON.stringify(controls));else fail('TC-CONTROLS-001','Controls','Theme, Navigator, and Inspector update while preserving focus','state changes and focus retained',JSON.stringify(controls),'Major');
const keys=await evaluate(`(()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'2',ctrlKey:true,altKey:true,bubbles:true}));const build=document.querySelector('[data-rail="builder"]').getAttribute('aria-current');document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}));const palette=!document.querySelector('#palette').hidden;document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));const closed=document.querySelector('#palette').hidden;return {build,palette,closed}})()`);
if(keys.build==='true'&&keys.palette&&keys.closed)pass('TC-KEYS-001','Keyboard','Rail jump, search shortcut, and Escape work',JSON.stringify(keys));else fail('TC-KEYS-001','Keyboard','Rail jump, search shortcut, and Escape work','build=true palette opens/closes',JSON.stringify(keys),'Major');

// Search semantics and category coverage.
await evaluate(`document.querySelector('[data-action="palette"]').click()`);
for(const [query,label,expectKinds] of [
  ['journalctl','tool/command',['Tool','Command']],
  ['STIG','STIG',['STIG']],
  ['CCI-000366','CCI',['CCI']],
  ['AC-2','NIST',['NIST']],
  ['--no-pager','Flag',['Flag']],
  ['subscription-manager','Reference',['Reference']]
]){
  const got=await evaluate(`(()=>{const i=document.querySelector('#palette-input');i.value=${JSON.stringify(query)};i.dispatchEvent(new Event('input',{bubbles:true}));return [...document.querySelectorAll('#palette-results [role="option"]')].slice(0,80).map(x=>x.textContent.trim())})()`);
  const ok=expectKinds.some(k=>got.some(x=>x.startsWith(k)||x.includes(k)));
  if(ok)pass(`TC-SEARCH-${label.replace(/\W/g,'').toUpperCase()}`,'Search',`${label} query returns a relevant result`,got.slice(0,4).join(' | '));else fail(`TC-SEARCH-${label.replace(/\W/g,'').toUpperCase()}`,'Search',`${label} query returns a relevant result`,expectKinds.join('/'),got.slice(0,8).join(' | '),'Major');
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
 const ack=await evaluate(`(()=>{document.querySelector('[data-action="ref-ack"]').click();return {enabled:!document.querySelector('[data-action="ref-copy"]').disabled,evidence:!!document.querySelector('[data-action="ref-evidence"]')}})()`);
 if(ack.enabled)pass('TC-REF-002','Reference','Reference acknowledgement unlocks copy',JSON.stringify(ack));else fail('TC-REF-002','Reference','Reference acknowledgement unlocks copy','copy enabled',JSON.stringify(ack),'Critical');
}
const governing=await evaluate(`(()=>{document.querySelector('[data-action="palette"]').click();const input=document.querySelector('#palette-input');input.value='aide';input.dispatchEvent(new Event('input',{bubbles:true}));const hit=[...document.querySelectorAll('#palette-results [role="option"]')].find(x=>x.textContent.includes('sudo /usr/sbin/aide --check'));if(hit)hit.click();return {hit:!!hit,title:document.querySelector('#editor-card h2')?.textContent||'',evidence:!!document.querySelector('[data-action="ref-evidence"]')}})()`);
if(governing.evidence)pass('TC-REF-003','Reference','Eligible governing text exposes byte-exact evidence copy',JSON.stringify(governing));else fail('TC-REF-003','Reference','Eligible governing text exposes byte-exact evidence copy','at least one evidence-eligible STIG record',JSON.stringify(governing),'Major');

// Pipeline workflow with two safe generators.
const pipelineExceptionStart=exceptions.length;
const j=entries.find(e=>e.id==='gen-journalctl-unit-logs');
await evaluate(`__qa.open('builder','journalctl','gen-journalctl-unit-logs','8',${JSON.stringify(j.intent)})`);
for(const [n,v] of Object.entries(golden.generators['gen-journalctl-unit-logs'].values))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(n)})+'"]',${JSON.stringify(v)})`);
let pipe=await evaluate(`(()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'P',ctrlKey:true,shiftKey:true,bubbles:true}));return document.querySelector('#pipeline-panel')?.textContent||''})()`);
if(pipe.includes('Stage 1')||pipe.includes('journalctl'))pass('TC-PIPE-001','Pipeline','A guided command can be added as stage 1',pipe.slice(0,220));else fail('TC-PIPE-001','Pipeline','A guided command can be added as stage 1','Stage 1/journalctl',pipe.slice(0,300),'Major');
const q=entries.find(e=>e.id==='gen-systemctl-query');
await evaluate(`__qa.open('builder','systemctl','gen-systemctl-query','8',${JSON.stringify(q.intent)})`);
for(const [n,v] of Object.entries(golden.generators['gen-systemctl-query'].values))await evaluate(`__qa.set('[data-field="'+CSS.escape(${JSON.stringify(n)})+'"]',${JSON.stringify(v)})`);
pipe=await evaluate(`(()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'P',ctrlKey:true,shiftKey:true,bubbles:true}));return document.querySelector('#pipeline-panel')?.textContent||''})()`);
if(pipe.includes('Stage 2')||((pipe.match(/Stage/g)||[]).length>=2))pass('TC-PIPE-002','Pipeline','A second guided command can be added and composed',pipe.slice(0,300));else fail('TC-PIPE-002','Pipeline','A second guided command can be added and composed','two stages',pipe.slice(0,400),'Major');
const pipelineTrust=await evaluate(`(()=>{const edit=document.querySelector('[data-pipe-action="edit"][data-pipe-index="0"]');if(edit)edit.click();const trust=[...document.querySelectorAll('#editor-card .trustfact')].map(x=>x.textContent.trim());const status=document.querySelector('#statusbar')?.textContent||'';const inspector=document.querySelector('#inspector-body')?.textContent||'';const editor=document.querySelector('#editor-card')?.textContent||'';const evidenceButton=document.querySelector('[data-action="export-evidence"]');if(evidenceButton)evidenceButton.click();const evidence=document.querySelector('#evidence-modal-body .evidencepre')?.textContent||'';document.querySelector('[data-action="evidence-close"]')?.click();return {edit:!!edit,trust,status,inspector,editor,evidence}})()`);
const pipelineTrustOk=pipelineTrust.edit&&pipelineTrust.trust.includes('Composed — not host-verified')&&pipelineTrust.status.includes('Composed — not host-verified')&&pipelineTrust.inspector.includes('Pipeline verification')&&pipelineTrust.inspector.includes('Stage 1')&&pipelineTrust.inspector.includes('Stage 2')&&pipelineTrust.evidence.includes('Verification (RHEL 8): Composed — not host-verified')&&!pipelineTrust.evidence.includes('verified by')&&!pipelineTrust.editor.includes(' · reviewed task');
if(pipelineTrustOk)pass('TC-PIPE-TRUST-001','Pipeline','Pipeline trust signals and evidence remain composed and unverified',JSON.stringify({trust:pipelineTrust.trust,status:pipelineTrust.status.slice(0,180),evidence:pipelineTrust.evidence.slice(0,220)}));else fail('TC-PIPE-TRUST-001','Pipeline','Pipeline trust signals and evidence remain composed and unverified','exact composed status in preview/status/export; per-stage inspector; no borrowed receipt',JSON.stringify(pipelineTrust),'Critical');
const incompletePipeline=await evaluate(`(()=>{document.querySelector('[data-pipe-action="redirect"]')?.click();return {editor:document.querySelector('#editor-card')?.textContent||'',result:document.querySelector('#gen-result')?.textContent||'',panel:document.querySelector('#pipeline-panel')?.textContent||''}})()`);
if((incompletePipeline.editor.includes('Complete the pipeline')||incompletePipeline.result.includes('Complete the pipeline'))&&incompletePipeline.panel.includes('Stage 3'))pass('TC-PIPE-INCOMPLETE-001','Pipeline','Incomplete pipeline names the pipeline problem instead of blaming the selected entry',JSON.stringify(incompletePipeline).slice(0,500));else fail('TC-PIPE-INCOMPLETE-001','Pipeline','Incomplete pipeline names the pipeline problem instead of blaming the selected entry','Complete the pipeline and Stage 3',JSON.stringify(incompletePipeline),'Major');
const cleared=await evaluate(`(()=>{const b=document.querySelector('[data-pipe-action="clear"]');if(b)b.click();return document.querySelector('#pipeline-panel')?.textContent||''})()`);
if(!cleared.includes('Stage 1'))pass('TC-PIPE-003','Pipeline','Pipeline Clear action removes all stages',cleared.slice(0,180));else fail('TC-PIPE-003','Pipeline','Pipeline Clear action removes all stages','no stages',cleared.slice(0,300),'Major');
if(exceptions.length===pipelineExceptionStart)pass('TC-PIPE-004','Pipeline','Pipeline composition does not raise a runtime exception','0');else fail('TC-PIPE-004','Pipeline','Pipeline composition does not raise a runtime exception','0',exceptions.slice(pipelineExceptionStart).join('\n\n'),'Critical');

// Isolate later workflows from any pipeline state left by a failure.
await send('Page.navigate',{url:baseUrl});await delay(800);
await evaluate(`(()=>{window.__qa={
  set(sel,value){const e=document.querySelector(sel);if(!e)return {ok:false,reason:'missing'};if(e.disabled)return {ok:false,reason:'disabled'};if(e.type==='checkbox'){e.checked=value==='yes'||value===true}else{e.value=String(value)}e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return {ok:true}},
  open(rail,tool,id,version,intent){const vb=document.querySelector('[data-version="'+CSS.escape(version)+'"]');if(!vb)return {ok:false,step:'version'};vb.click();const rb=document.querySelector('[data-rail="'+CSS.escape(rail)+'"]');if(!rb)return {ok:false,step:'rail'};rb.click();const tb=document.querySelector('[data-tool="'+CSS.escape(tool)+'"]');if(!tb)return {ok:false,step:'tool'};if(tb.getAttribute('aria-current')!=='true')tb.click();const eb=document.querySelector('[data-entry="'+CSS.escape(id)+'"]');if(!eb)return {ok:false,step:'entry'};eb.click();return {ok:true}},
  command(){return [...document.querySelectorAll('#editor-card .codeline .lc')].map(x=>x.textContent).join('\\n')}
};return true})()`);

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
await evaluate(`__qa.set('[data-field="pid"]','54321')`);
const killPlan=await evaluate(`document.querySelector('#gen-result .opplan')?.textContent||''`);
if(killPlan.includes('54321')&&!killPlan.includes('12345'))pass('TC-RUNBOOK-001','Runbook','Process preflight binds the current PID',killPlan.slice(0,220));else fail('TC-RUNBOOK-001','Runbook','Process preflight binds the current PID','54321 and no golden 12345',killPlan.slice(0,300),'Critical');
const gitDiscard=entries.find(e=>e.id==='git-checkout-discard-changes');
await evaluate(`__qa.open('git','git','git-checkout-discard-changes','8',${JSON.stringify(gitDiscard.intent)})`);
await evaluate(`__qa.set('[data-field="path"]','config/prod.yml')`);
const gitPlan=await evaluate(`document.querySelector('#gen-result .opplan')?.textContent||''`);
if(gitPlan.includes('git diff -- config/prod.yml')&&!gitPlan.includes('src/app.py'))pass('TC-RUNBOOK-002','Runbook','Destructive Git preflight binds the current path',gitPlan.slice(0,240));else fail('TC-RUNBOOK-002','Runbook','Destructive Git preflight binds the current path','config/prod.yml and no golden src/app.py',gitPlan.slice(0,300),'Critical');
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
if(architecture.includes('339 unittest cases')||architecture.includes('101,957 harness checks'))fail('TC-DOCS-002','Documentation','Architecture validation counts match the current suite','418 unit tests; 122,533 hostile checks','339 unit tests; 101,957 hostile checks','Minor');else pass('TC-DOCS-002','Documentation','Architecture validation counts match the current suite');

// Console/runtime health and memory/performance observations.
const perf=await evaluate(`(()=>({heap:performance.memory?performance.memory.usedJSHeapSize:null,resources:performance.getEntriesByType('resource').length,nav:performance.getEntriesByType('navigation')[0]?{dom:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,load:performance.getEntriesByType('navigation')[0].loadEventEnd}:null}))()`);
record('TC-PERF-002','Performance','Browser performance observation','PASS','informational',JSON.stringify(perf));
if(exceptions.length===0&&consoleErrors.length===0)pass('TC-CONSOLE-001','Reliability','No runtime exceptions or console errors occurred during the audit','0');else fail('TC-CONSOLE-001','Reliability','No runtime exceptions or console errors occurred during the audit','0',JSON.stringify({exceptions,consoleErrors}),'Critical');

const summary={total:results.length,pass:results.filter(x=>x.status==='PASS').length,fail:results.filter(x=>x.status==='FAIL').length,bySeverity:{}};
for(const r of results.filter(x=>x.status==='FAIL'))summary.bySeverity[r.severity]=(summary.bySeverity[r.severity]||0)+1;
const output={meta:{tool:'MD CODE RED',version:'v1.0.0-alpha.6',date:'2026-10-01',browser:'Google Chrome headless via CDP',url:baseUrl,commit:process.env.AUDIT_COMMIT||'',entries:entries.length,generators:entries.filter(e=>Object.hasOwn(e,'template')).length,staticEntries:entries.filter(e=>!Object.hasOwn(e,'template')).length},summary,exceptions,consoleErrors,results};
fs.writeFileSync('/tmp/mdcr_functional_audit_results.json',JSON.stringify(output,null,2));
console.log(JSON.stringify(summary));
ws.close();
