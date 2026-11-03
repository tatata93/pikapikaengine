import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {SELECTION_DEFAULTS,SELECTION_PRESETS,opticalSelectionCase,evaluateOpticalSelectionCase,initializeOpticalSelectionLab} from '../tools/optical-selection-lab.mjs';
const htmlUrl=new URL('../tools/optical-selection-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const clone=x=>JSON.parse(JSON.stringify(x));
const encloses=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${a} does not enclose ${x}`);

test('selection presets preserve full X/Z families, explicit domains and sphere versus cap geometry',()=>{
  assert.equal(Object.keys(SELECTION_PRESETS).length,9);
  for(const preset of Object.keys(SELECTION_PRESETS)){const source=opticalSelectionCase({preset});assert.equal(source.records.length,2);assert.equal(source.ray.minimumParameter,source.parameters.minimumParameter);assert.equal(source.ray.maximumParameter,10);assert.equal(source.settings.maximumQueries,512);}
  assert.deepEqual(opticalSelectionCase({preset:'partial'}).ray.origin[0],[.4,.6]);
  assert.deepEqual(opticalSelectionCase({preset:'order'}).ray.origin[2],[-2,-1]);
  assert.equal(opticalSelectionCase({preset:'self'}).ray.minimumParameter,0);assert.equal(opticalSelectionCase({preset:'cutoff'}).ray.minimumParameter,.01);
  assert.deepEqual(opticalSelectionCase({preset:'sphere'}).records.map(r=>r.surface.kind),['cap','sphere']);
  const cap=opticalSelectionCase({preset:'cap'});assert.equal(cap.records[1].surface.signedRadius,1);assert.deepEqual(cap.ray.direction,[0,0,-1]);
  const original=opticalSelectionCase();original.records[0].surface.center[2]=999;assert.equal(opticalSelectionCase().records[0].surface.center[2],2);
});
test('blank nonfinite reverse domain and fractional budgets reject without a stale call',()=>{
  for(const input of [{preset:'missing'},{originX:''},{originZHalfWidth:-1},{directionScale:0},{originX:Infinity},{minimumParameter:2,maximumParameter:1},{maximumParameter:1001},{maximumQueries:1.5},{maxSqrtRefinements:0},{maximumTotalSqrtRefinements:1000001},{allowPrefixExclusion:1}])assert.throws(()=>opticalSelectionCase(input));
  let calls=0;assert.throws(()=>evaluateOpticalSelectionCase({queryNearestOpticalSurface(){++calls;}},{originX:''}));assert.equal(calls,0);
});
const hit=(t=1,z=0)=>({parameter:[t,t],physicalDistance:[t,t],position:[[0,0],[0,0],[z,z]],geometricNormal:[[0,0],[0,0],[-1,-1]],incidentNormal:[[0,0],[0,0],[-1,-1]],frontFace:true});
const geometry=(status='hit',t=1,z=0)=>({status,reason:status==='hit'?'none':status==='miss'?'parameter_boundary':'aperture_boundary',hit:status==='hit'?hit(t,z):null,candidates:status==='unresolved'?[{parameter:[t,t],state:'unresolved',reason:'aperture_boundary'}]:[],sqrtRefinements:0,refinementLimited:false});
function result(status='hit',{prefix=false,budget=false}={}){
  return {status,geometryQueries:budget?1:prefix?3:2,prefixQueries:prefix?1:0,sqrtRefinements:0,refinementLimited:false,surfaceCount:2,
    nearest:status==='hit'?{id:10,hit:hit()}:null,surfaces:[{id:10,geometry:geometry(),prefix:null,excludedByPrefix:false},{id:20,geometry:budget?null:geometry(prefix?'unresolved':'hit',3,2),prefix:prefix?geometry('miss'):null,excludedByPrefix:prefix}]};
}
// Scripted DTO fixture: tests dispatch/render/error contracts, NOT geometry.
function fixtureRuntime(){const calls=[];return {calls,diagnostics:{backend:'fixture API, not physics',wasmBytes:0},respond:()=>result(),queryNearestOpticalSurface(ray,records,settings){calls.push(clone({ray,records,settings}));return clone(this.respond(ray,records,settings));}};}
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[];
  const defaults={'selection-preset':'front','selection-x':'0','selection-x-width':'0','selection-z':'-1','selection-z-width':'0','selection-scale':'1','selection-min':'0','selection-max':'10','selection-query-budget':'512','selection-sqrt-budget':'128','selection-total-sqrt':'16384'};
  const context=new Proxy({}, {get:(_t,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const create=tag=>({tag,textContent:'',children:[],appendChild(child){this.children.push(child);},replaceChildren(...children){this.children=children;}});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{...create(id),value:defaults[id]??'',checked:id==='selection-prefix',hidden:false,disabled:false,width:900,height:430,getContext:()=>context,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,doc:{getElementById:get,createElement:create},fire:(id,type='change')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,`missing listener ${id}:${type}`);return fn();}};
}
test('UI forwards complete family inputs, canonical table rows and kernel-only nearest selection',async()=>{
  const ui=harness(),runtime=fixtureRuntime(),lab=await initializeOpticalSelectionLab({doc:ui.doc,loadRuntime:async()=>runtime});
  assert.equal(lab.getState().result.nearest.id,10);assert.equal(ui.get('selection-controls').disabled,false);assert.match(ui.get('selection-nearest').textContent,/#10/);assert.equal(ui.get('selection-table').children.length,2);
  ui.get('selection-x-width').value='.1';ui.fire('selection-x-width','input');assert.deepEqual(runtime.calls.at(-1).ray.origin[0],[-.1,.1]);assert.equal(runtime.calls.at(-1).settings.maximumQueries,512);
  const json=JSON.parse(ui.get('selection-json').textContent);assert.deepEqual(json.source.ray.origin[0],[-.1,.1]);assert.equal(json.result.nearest.id,10);assert.ok(ui.draws.some(d=>d[0]==='strokeRect'));
});
test('UI toggles prefix and budgets on the same scene and retains every unqueried ID',async()=>{
  const ui=harness(),runtime=fixtureRuntime();runtime.respond=(_ray,_records,s)=>s.maximumQueries===1?result('budget_exceeded',{budget:true}):s.allowPrefixExclusion?result('hit',{prefix:true}):result('unresolved');
  const lab=await initializeOpticalSelectionLab({doc:ui.doc,loadRuntime:async()=>runtime});lab.preset('prefix');assert.equal(lab.getState().result.status,'hit');
  const source=clone(lab.getState().source);ui.get('selection-prefix').checked=false;ui.fire('selection-prefix');assert.equal(lab.getState().result.status,'unresolved');assert.equal(ui.get('selection-nearest').textContent,'—');assert.deepEqual(lab.getState().source.ray,source.ray);assert.deepEqual(lab.getState().source.records,source.records);
  ui.get('selection-prefix').checked=true;ui.fire('selection-prefix');assert.equal(lab.getState().result.status,'hit');assert.match(ui.get('selection-table').children[1].children[3].textContent,/閉prefix全体がmiss/);
  ui.get('selection-query-budget').value='1';ui.fire('selection-query-budget','input');assert.equal(lab.getState().result.status,'budget_exceeded');assert.equal(ui.get('selection-table').children.length,2);assert.equal(ui.get('selection-table').children[1].children[1].textContent,'未照会');assert.equal(ui.get('selection-nearest').textContent,'—');
  ui.fire('selection-budget-restore','click');assert.equal(lab.getState().result.status,'hit');assert.equal(ui.get('selection-query-budget').value,'512');
});
test('invalid input and corrupt uncertain winner clear prior selections and table data',async()=>{
  const ui=harness(),runtime=fixtureRuntime(),lab=await initializeOpticalSelectionLab({doc:ui.doc,loadRuntime:async()=>runtime});
  ui.get('selection-x').value='';ui.fire('selection-x','input');assert.equal(lab.getState(),null);assert.equal(ui.get('selection-nearest').textContent,'—');assert.equal(ui.get('selection-table').children.length,0);assert.equal(ui.get('selection-json').textContent,'結果なし');
  ui.get('selection-x').value='0';ui.fire('selection-x');assert.equal(lab.getState().result.status,'hit');
  runtime.respond=()=>({...result('unresolved'),nearest:{id:10,hit:hit()}});lab.recalculate();assert.equal(lab.getState(),null);assert.match(ui.get('selection-error').textContent,/未確定/);
});
test('load failure, legacy kernel error and retry never call a replacement selector',async()=>{
  const ui=harness(),runtime=fixtureRuntime();let fail=true;
  const lab=await initializeOpticalSelectionLab({doc:ui.doc,loadRuntime:async()=>{if(fail)throw new Error('offline');return runtime;}});assert.equal(lab.getState(),null);assert.equal(ui.get('selection-controls').disabled,true);assert.equal(runtime.calls.length,0);
  fail=false;await lab.retry();assert.equal(lab.getState().result.status,'hit');
  runtime.respond=()=>{throw new Error('Optical selection WASM API unavailable; rebuild the common C++ runtime');};lab.recalculate();assert.equal(lab.getState(),null);assert.match(ui.get('selection-error').textContent,/同梱WASM.*再読込/);assert.equal(ui.get('selection-table').children.length,0);
  assert.throws(()=>evaluateOpticalSelectionCase({queryBoundedSurface(){throw new Error('must never be used as fallback');}}),/未対応/);
});
test('HTML static contract, original SVG, 18th lesson and single build registration are present',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
  for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));
  assert.match(html,/XZ断面/);assert.match(html,/閉じたprefix/);assert.match(html,/t\|D\|/);assert.match(html,/不確定な面を無視/);assert.match(html,/src="optical-selection-lab\.mjs(?:\?[^\"]*)?"/);
  const index=await readFile(new URL('../docs/learn/index.html',import.meta.url),'utf8');assert.equal([...index.matchAll(/<article\s/g)].length,23);assert.match(index,/id="optical-selection"/);
  const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.equal((build.match(/\['tools\/optical-selection-lab.html','\.\.\/','optical-selection-lab.mjs'\]/g)??[]).length,1);
  const svg=await readFile(new URL('../docs/learn/diagrams/optical-selection.svg',import.meta.url),'utf8');assert.match(svg,/<svg /);assert.doesNotMatch(svg,/<image|https?:\/\/(?!www.w3.org)/);
});

let runtime;
async function actualRuntime(){if(!runtime)runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});return runtime;}
test('actual existing bounded primitives verify family ingredients without substituting nearest selection',async()=>{
  const r=await actualRuntime();
  for(const [preset,states]of [['front',['hit','hit']],['partial',['hit','unresolved']],['prefix',['unresolved','hit']],['simultaneous',['hit','hit']],['order',['hit','hit']],['self',['hit','hit']],['cutoff',['hit','miss']],['sphere',['hit','hit']],['cap',['hit','hit']]]){
    const s=opticalSelectionCase({preset}),results=s.records.map(record=>r.queryBoundedSurface(s.ray,record.surface,s.settings));assert.deepEqual(results.map(g=>g.status),states,preset);
    if(preset==='order'){const a=results[0].hit.parameter,b=results[1].hit.parameter;assert.ok(a[0]<=b[1]&&b[0]<=a[1]);encloses(a,1.25);encloses(b,1);}
    if(preset==='self')encloses(results[1].hit.parameter,0);
    if(preset==='sphere'){encloses(results[0].hit.parameter,3);encloses(results[1].hit.parameter,1);}
    if(preset==='cap'){encloses(results[0].hit.parameter,4);encloses(results[1].hit.parameter,3);}
    if(preset==='prefix'){const prefix=r.queryBoundedSurface({...s.ray,maximumParameter:results[1].hit.parameter[1]},s.records[0].surface,s.settings);assert.equal(prefix.status,'miss');}
  }
});

test('actual WASM selection chooses geometry and distinguishes parameter from distance and domain cutoff',async()=>{
  const r=await actualRuntime();for(const [preset,id,t]of [['front',10,1],['self',10,0],['cutoff',20,1],['sphere',10,1],['cap',10,3]]){
    const s=evaluateOpticalSelectionCase(r,{preset});assert.equal(s.result.status,'hit',preset);assert.equal(s.result.nearest.id,id,preset);encloses(s.result.nearest.hit.parameter,t);encloses(s.result.nearest.hit.physicalDistance,t);assert.deepEqual(s.result.surfaces.map(d=>d.id),[10,20]);
  }
  const scaled=evaluateOpticalSelectionCase(r,{directionScale:2});encloses(scaled.result.nearest.hit.parameter,.5);encloses(scaled.result.nearest.hit.physicalDistance,1);
  const source=opticalSelectionCase(),before=JSON.stringify(source),a=r.queryNearestOpticalSurface(source.ray,source.records,source.settings),b=r.queryNearestOpticalSurface(source.ray,[...source.records].reverse(),source.settings);assert.deepEqual(a,b);assert.equal(JSON.stringify(source),before);
  const miss=evaluateOpticalSelectionCase(r,{originX:3});assert.equal(miss.result.status,'miss');assert.equal(miss.result.nearest,null);
});
test('actual WASM selection retains partial aperture, simultaneous and correlated-order uncertainty',async()=>{
  const r=await actualRuntime();for(const preset of ['partial','simultaneous','order']){const s=evaluateOpticalSelectionCase(r,{preset});assert.equal(s.result.status,'unresolved',preset);assert.equal(s.result.nearest,null);assert.equal(s.result.surfaces.length,2);}
  const source=opticalSelectionCase({preset:'order'}),answer=r.queryNearestOpticalSurface(source.ray,source.records,source.settings);assert.ok(answer.surfaces.every(d=>d.geometry.status==='hit'));
  const [a,b]=answer.surfaces.map(d=>d.geometry.hit.parameter);assert.ok(a[1]>=b[0]&&b[1]>=a[0]);
});
test('actual WASM and UI prove prefix exclusion, preserve unqueried rows and recover without changing geometry',async()=>{
  const r=await actualRuntime(),ui=harness(),lab=await initializeOpticalSelectionLab({doc:ui.doc,loadRuntime:async()=>r});
  lab.preset('prefix');const original=clone(lab.getState().source);assert.equal(lab.getState().result.status,'hit');assert.equal(lab.getState().result.geometryQueries,3);assert.equal(lab.getState().result.prefixQueries,1);
  const rival=lab.getState().result.surfaces.find(s=>s.id===20);assert.equal(rival.geometry.status,'unresolved');assert.equal(rival.prefix.status,'miss');assert.equal(rival.excludedByPrefix,true);assert.match(ui.get('selection-table').children[1].children[3].textContent,/閉prefix全体がmiss/);
  ui.get('selection-prefix').checked=false;ui.fire('selection-prefix');assert.equal(lab.getState().result.status,'unresolved');assert.equal(ui.get('selection-nearest').textContent,'—');assert.deepEqual(lab.getState().source.ray,original.ray);assert.deepEqual(lab.getState().source.records,original.records);
  ui.get('selection-prefix').checked=true;ui.fire('selection-prefix');assert.equal(lab.getState().result.status,'hit');
  ui.get('selection-query-budget').value='2';ui.fire('selection-query-budget','input');assert.equal(lab.getState().result.status,'budget_exceeded');assert.equal(lab.getState().result.geometryQueries,2);assert.equal(lab.getState().result.nearest,null);assert.equal(ui.get('selection-table').children.length,2);
  ui.get('selection-query-budget').value='1';ui.fire('selection-query-budget','input');assert.equal(lab.getState().result.status,'budget_exceeded');assert.equal(ui.get('selection-table').children[1].children[1].textContent,'未照会');
  ui.fire('selection-budget-restore','click');assert.equal(lab.getState().result.status,'hit');assert.deepEqual(lab.getState().source.ray,original.ray);assert.deepEqual(lab.getState().source.records,original.records);
  const json=JSON.parse(ui.get('selection-json').textContent);assert.equal(json.diagnostics.backend,'C++ WebAssembly');assert.equal(json.result.nearest.id,10);
  ui.get('selection-x').value='';ui.fire('selection-x','input');assert.equal(lab.getState(),null);assert.equal(ui.get('selection-table').children.length,0);assert.equal(ui.get('selection-json').textContent,'結果なし');
  ui.get('selection-x').value=String(original.parameters.originX);ui.fire('selection-x');assert.equal(lab.getState().result.status,'hit');
});
