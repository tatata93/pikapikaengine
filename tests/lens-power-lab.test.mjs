import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {createLensPowerProfile,createLensPowerNodes,evaluateLensPowerProfile} from '../engine/polarized-camera.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {initializeLensPowerLab,lensPowerDisplayData,drawLensPower} from '../tools/lens-power-lab.mjs';
const htmlUrl=new URL('../tools/lens-power-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8'),copy=x=>JSON.parse(JSON.stringify(x));
// Scripted DTO fixture: presentation and dispatch contract only, not physics.
function fixtureOutput(profile,{unknown=false,absent=false,preflight=false}={}){
  const nodes=createLensPowerNodes(profile),packets=nodes.map(node=>({ray:{origin:node.position.map(x=>[x,x]),direction:profile.source.direction.map(x=>[x,x]),minimumParameter:0,maximumParameter:1e6},power:[...node.power],transverseReference:[...profile.source.transverseReference]}));
  const position=[[.001,.0011],[-.002,-.0019],[profile.sensor.center[2],profile.sensor.center[2]]],sensorPower=[.001,.002];
  const record=(packet,packetIndex)=>({packetIndex,power:[...packet.power],status:unknown&&packetIndex===0?'not_examined':'accepted',route:unknown&&packetIndex===0?null:{status:'completed',completion:{state:{power:sensorPower,coherency:{diagonal:[[.0005,.001],[.0005,.001],[0,0]],upper:[{real:[0,0],imag:[0,0]},{real:[0,0],imag:[0,0]},{real:[0,0],imag:[0,0]}]}}}},sensor:unknown&&packetIndex===0?null:{status:'hit',hit:{position}},sensorPower:unknown&&packetIndex===0?null:sensorPower});
  return {profile:copy(profile),nodes,packets,sensor:{kind:'disk',center:profile.sensor.center,apertureRadius:profile.sensor.apertureRadius},channels:profile.wavelengths.map(wavelength=>({wavelength,index:absent?null:[1.5,1.5],dispersion:{status:absent?'unresolved':'resolved'},paths:['primary','ghost'].map(id=>({id,steps:[],result:absent?null:{status:unknown||preflight?'budget_exceeded':'completed',records:preflight?[]:packets.map(record),stats:unknown||preflight?null:{totalSourcePower:[profile.powerWatts,profile.powerWatts],acceptedSourcePower:[profile.powerWatts,profile.powerWatts],detectedPower:[.1,.2]}}}))})),diagnostics:{backend:'scripted DTO fixture, not physics'},timing:{totalMilliseconds:5}};
}
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[],saves=[];
  const ctx=new Proxy({}, {get:(_t,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const create=tag=>({tag,value:'',textContent:'',style:{},children:[],appendChild(c){this.children.push(c);},replaceChildren(...c){this.children=c;}});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{...create(id),hidden:false,disabled:false,width:800,height:420,files:[],getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,saves,doc:{getElementById:get,createElement:create},saveJson:(name,text)=>saves.push({name,text}),fire:(id,type='input')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,'missing listener '+id+':'+type);return fn();}};
}
const initialize=(ui,extra={})=>initializeLensPowerLab({doc:ui.doc,loadRuntime:async()=>({diagnostics:{backend:'fixture, not physics'}}),evaluate:async(_r,p,o)=>{o.onProgress({completed:1,total:1,phase:'path',wavelength:550e-9,path:'primary'});return fixtureOutput(p);},yieldControl:async()=>{},saveJson:ui.saveJson,...extra});

test('UI waits for explicit calculation, displays two separate paths per wavelength and preserves kernel watts',async()=>{
  const ui=harness(),calls=[],lab=await initialize(ui,{evaluate:async(_r,p,o)=>{calls.push(copy(p));o.onProgress({completed:1,total:1,phase:'path'});return fixtureOutput(p);}});assert.equal(calls.length,0);assert.equal(lab.getState().output,null);
  ui.get('lp-power').value='2';ui.fire('lp-power');ui.get('lp-aperture').value='3';ui.fire('lp-aperture');assert.equal(calls.length,0);await lab.calculate();assert.equal(calls.length,1);assert.equal(calls[0].powerWatts,2);assert.equal(calls[0].apertureRadius,.003);
  assert.equal(ui.get('lp-table').children.length,6);assert.match(ui.get('lp-table').children[0].children[3].textContent,/検出 \[0\.10000000, 0\.20000000\] W/);assert.match(ui.get('lp-table').children[1].children[0].textContent,/内部反射/);assert.match(ui.get('lp-summary').textContent,/合計なし/);assert.ok(ui.draws.some(d=>d[0]==='strokeRect'));assert.equal(ui.saves.length,0);
  const out=JSON.parse(ui.get('lp-result-json').textContent);assert.deepEqual(out.channels[0].paths[0].result.stats,lab.getState().output.channels[0].paths[0].result.stats);
  ui.get('lp-sensor-radius').value='1';ui.fire('lp-sensor-radius');assert.equal(lab.getState().output,null);assert.equal(ui.get('lp-table').children.length,0);assert.equal(ui.get('lp-save-result').disabled,true);assert.equal(calls.length,1);
});

test('unknown or unadmitted packets retain source watts and never become a zero detected tally',async()=>{
  const profile=createLensPowerProfile(),unknown=fixtureOutput(profile,{unknown:true}),rows=lensPowerDisplayData(unknown);assert.equal(rows[0].counts.notExamined,1);assert.equal(rows[0].watts.notExamined,1/64);assert.equal(rows[0].points.length,63);assert.equal(rows[0].stats,null);
  const preflight=lensPowerDisplayData(fixtureOutput(profile,{preflight:true}));assert.equal(preflight[0].counts.unadmitted,64);assert.equal(preflight[0].watts.unadmitted,1);assert.equal(preflight[0].stats,null);assert.equal(preflight[0].points.length,0);
  const absent=lensPowerDisplayData(fixtureOutput(profile,{absent:true}));assert.equal(absent[0].counts.unadmitted,64);assert.equal(absent[0].stats,null);
  const corrupt=fixtureOutput(profile,{unknown:true});corrupt.channels[0].paths[0].result.stats=fixtureOutput(profile).channels[0].paths[0].result.stats;assert.throws(()=>lensPowerDisplayData(corrupt),/不完全/);
  const falseZero=fixtureOutput(profile,{unknown:true});falseZero.channels[0].paths[0].result.records[0].sensorPower=[0,0];assert.throws(()=>lensPowerDisplayData(falseZero),/0W/);
  const ui=harness(),lab=await initialize(ui,{evaluate:async()=>unknown});await lab.calculate();assert.equal(ui.get('lp-table').children[0].children[3].textContent,'—（最終集計なし）');ui.get('lp-packet').value='0';ui.fire('lp-packet');assert.match(ui.get('lp-record-status').textContent,/sensorPower — W/);assert.equal(JSON.parse(ui.get('lp-inspection').textContent).record.status,'not_examined');
});

test('profile JSON load preserves exact untouched source sensor material wavelength and optional budgets',async()=>{
  const ui=harness(),calls=[],lab=await initialize(ui,{evaluate:async(_r,p)=>{calls.push(copy(p));return fixtureOutput(p);}});
  const p=createLensPowerProfile({powerWatts:.12345678912345678,apertureRadius:.00345678912345678,radialSamples:2,angularSamples:4,source:{direction:[.25,-.5,2],transverseReference:[0,1,0]},sensor:{center:[.01234567891234567,-.02,.07345678912345678],apertureRadius:.02345678912345678},material:{coefficients:[1.49,2e-15,0]},wavelengths:[500e-9],settings:{maximumPackets:17,maximumRouteSqrtRefinements:123}});
  assert.equal(await lab.loadProfile(JSON.stringify(p)),true);assert.equal(calls.length,0);await lab.calculate();assert.deepEqual(calls[0],p);
  ui.get('lp-power').value='3';ui.fire('lp-power');await lab.calculate();assert.deepEqual(calls[1],{...p,powerWatts:3});assert.equal(ui.saves.length,0);
  ui.fire('lp-save-profile','click');ui.fire('lp-save-result','click');assert.equal(ui.saves.length,2);assert.deepEqual(JSON.parse(ui.saves[0].text),calls[1]);assert.deepEqual(JSON.parse(ui.saves[1].text).profile,calls[1]);assert.match(ui.get('lp-legend').children[0].textContent,/500\.00000 nm/);
});

test('packet inspector shows actual route and sensor records, while invalid input removes stale data',async()=>{
  const ui=harness(),lab=await initialize(ui);await lab.calculate();ui.get('lp-inspect').value='0:1';ui.fire('lp-inspect','change');ui.get('lp-packet').value='5';ui.fire('lp-packet');let data=JSON.parse(ui.get('lp-inspection').textContent);assert.equal(data.path,'ghost');assert.equal(data.record.packetIndex,5);assert.ok(data.record.route.completion.state.coherency);
  ui.get('lp-packet').value='10000';ui.fire('lp-packet');assert.equal(ui.get('lp-inspection').textContent,'結果なし');
  ui.get('lp-power').value='';ui.fire('lp-power');assert.equal(lab.getState().output,null);assert.equal(await lab.calculate(),null);assert.match(ui.get('lp-error').textContent,/有限/);assert.equal(ui.get('lp-result-json').textContent,'結果なし');
  assert.equal(await lab.loadProfile('{broken'),false);assert.equal(lab.getState().output,null);ui.fire('lp-reset','click');assert.deepEqual(lab.getState().profile,createLensPowerProfile());
});

test('busy evaluation locks controls and saving, exposes real progress and prevents overlapping runs',async()=>{
  const ui=harness();let finish,calls=0,clock=0;const lab=await initialize(ui,{now:()=>clock,evaluate:async(_r,p,o)=>{++calls;o.onProgress({completed:16,total:70,phase:'launch'});await new Promise(resolve=>{finish=resolve;});return fixtureOutput(p);}});
  const pending=lab.calculate();await Promise.resolve();await Promise.resolve();assert.equal(ui.get('lp-controls').disabled,true);assert.equal(ui.get('lp-retry').disabled,true);assert.equal(ui.get('lp-progress').value,16);assert.equal(await lab.calculate(),null);assert.equal(await lab.loadProfile('{}'),false);await lab.retry();ui.fire('lp-save-profile','click');assert.equal(ui.saves.length,0);assert.equal(calls,1);
  clock=200;finish();await pending;assert.equal(lab.getState().busy,false);assert.equal(ui.get('lp-controls').disabled,false);assert.match(ui.get('lp-elapsed').textContent,/200\.00000 ms/);
});

test('load failure and legacy kernel error clear old results, retry does not automatically launch packets',async()=>{
  const ui=harness();let offline=true,legacy=true,calls=0;const lab=await initialize(ui,{loadRuntime:async()=>{if(offline)throw new Error('offline');return {};},evaluate:async(_r,p)=>{++calls;if(legacy)throw new Error('Polarized packet WASM API unavailable; rebuild');return fixtureOutput(p);}});
  assert.equal(ui.get('lp-controls').disabled,true);assert.equal(await lab.calculate(),null);assert.equal(calls,0);offline=false;await lab.retry();assert.equal(calls,0);await lab.calculate();assert.equal(lab.getState().output,null);assert.match(ui.get('lp-error').textContent,/同梱WASM/);
  legacy=false;await lab.retry();await lab.calculate();assert.ok(lab.getState().output);offline=true;await lab.retry();assert.equal(lab.getState().output,null);assert.equal(ui.get('lp-table').children.length,0);
});

test('file load is a user action with size rejection and no automatic save or calculation',async()=>{
  const ui=harness(),lab=await initialize(ui);await lab.calculate();const p=createLensPowerProfile({powerWatts:4});ui.get('lp-load-profile').files=[{size:100,text:async()=>JSON.stringify(p)}];await ui.fire('lp-load-profile','change');assert.deepEqual(lab.getState().profile,p);assert.equal(lab.getState().output,null);assert.equal(ui.saves.length,0);
  await lab.calculate();ui.get('lp-load-profile').files=[{size:3*1024*1024,text:async()=>{throw new Error('must not read');}}];await ui.fire('lp-load-profile','change');assert.equal(lab.getState().output,null);assert.match(ui.get('lp-error').textContent,/2MiB/);
});

test('static Japanese lesson original SVG and bounded tables distinguish watts from radiance with one build tuple',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));
  for(const term of ['自動加算しません','単色実験','未受理','追加の余弦','HTTP/HTTPS','表示中央値','全ghost'])assert.ok(html.includes(term),term);assert.match(html,/overflow-x:auto/);assert.match(html,/white-space:nowrap/);assert.match(html,/src="lens-power-lab\.mjs(?:\?[^\"]*)?"/);
  const index=await readFile(new URL('../docs/learn/index.html',import.meta.url),'utf8');assert.equal([...index.matchAll(/<article\s/g)].length,24);assert.match(index,/id="lens-power"/);
  const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.equal((build.match(/\['tools\/lens-power-lab.html','\.\.\/','lens-power-lab.mjs'\]/g)??[]).length,1);
  const svg=await readFile(new URL('../docs/learn/diagrams/lens-power.svg',import.meta.url),'utf8');assert.match(svg,/<svg /);assert.doesNotMatch(svg,/<image|https?:\/\/(?!www.w3.org)/);
  const ui=harness();drawLensPower(ui.get('lp-primary'),lensPowerDisplayData(fixtureOutput(createLensPowerProfile(),{absent:true})));assert.equal(ui.draws.filter(d=>d[0]==='arc').length,0);
});

let runtime;async function actual(){if(!runtime)runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});return runtime;}
test('actual WASM through UI distinguishes source and detected watts, sensor rejection and explicit budget recovery',async()=>{
  const ui=harness(),lab=await initialize(ui,{loadRuntime:actual,evaluate:evaluateLensPowerProfile});
  await lab.loadProfile(JSON.stringify(createLensPowerProfile({apertureRadius:.0001,radialSamples:1,angularSamples:4,wavelengths:[550e-9]})));await lab.calculate();let out=lab.getState().output;assert.ok(out);assert.equal(out.channels[0].paths[0].result.status,'completed');assert.equal(ui.get('lp-table').children.length,2);assert.match(ui.get('lp-table').children[0].children[3].textContent,/検出/);
  ui.get('lp-sensor-x').value='900';ui.fire('lp-sensor-x');ui.get('lp-sensor-y').value='900';ui.fire('lp-sensor-y');ui.get('lp-sensor-radius').value='.001';ui.fire('lp-sensor-radius');await lab.calculate();out=lab.getState().output;
  for(const path of out.channels[0].paths){assert.equal(path.result.status,'completed');assert.equal(path.result.counts.sensorMiss,4);assert.ok(path.result.stats.detectedPower[0]<=0&&path.result.stats.detectedPower[1]>=0);assert.equal(path.result.stats.acceptedSourcePower[1],0);}
  ui.get('lp-packet-budget').value='1';ui.fire('lp-packet-budget');await lab.calculate();assert.equal(lab.getState().output.channels[0].paths[0].result.stats,null);assert.equal(ui.get('lp-table').children[0].children[3].textContent,'—（最終集計なし）');ui.get('lp-packet-budget').value='1024';ui.fire('lp-packet-budget');await lab.calculate();assert.equal(lab.getState().output.channels[0].paths[0].result.status,'completed');assert.equal(ui.saves.length,0);
});
