import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {createLensSpotProfile,evaluateLensSpotProfile} from '../engine/optical-camera.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {initializeLensSpotLab,lensSpotDisplayData,drawLensSpot} from '../tools/lens-spot-lab.mjs';
const htmlUrl=new URL('../tools/lens-spot-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const copy=x=>JSON.parse(JSON.stringify(x));
const encloses=(a,x)=>assert.ok(a[0]<=x&&x<=a[1],`${a} does not enclose ${x}`);

// Scripted DTO fixture checks UI contracts; it is not an optics calculation.
function fixtureResult(profile,{unknown=false,absent=false}={}){
  const count=profile.radialSamples*profile.angularSamples,nodes=Array.from({length:count},(_,i)=>({position:[i*1e-4,0,-.01],weight:1/count}));
  const position=[[.000001,.000003],[-.000004,-.000002],[profile.sensorZ,profile.sensorZ]];
  const records=nodes.map((node,sampleIndex)=>({sampleIndex,weight:node.weight,status:unknown&&sampleIndex===0?'not_examined':'accepted',route:{status:'completed'},sensor:unknown&&sampleIndex===0?null:{status:'hit',hit:{position}}}));
  const stats=unknown?null:{totalWeight:[1,1],acceptedWeight:[1,1],moments:{centroid:[[.000001,.000003],[-.000004,-.000002],[profile.sensorZ,profile.sensorZ]],meanSquaredRadius:[2e-12,8e-12],hull:position}};
  return {profile:copy(profile),geometry:{frontRadius:.05,backRadius:-.05,thickness:.005},nodes,samples:nodes.map(n=>({ray:{origin:n.position,direction:[0,0,1]},weight:n.weight})),channels:profile.wavelengths.map(wavelength=>({wavelength,index:absent?null:[1.5,1.5],dispersion:{status:absent?'unresolved':'resolved'},result:absent?null:{status:unknown?'budget_exceeded':'completed',records:copy(records),stats:copy(stats)}})),diagnostics:{backend:'scripted DTO fixture, not physics'},timing:{totalMilliseconds:12}};
}
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[],saves=[];
  const ctx=new Proxy({}, {get:(_t,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const create=tag=>({tag,textContent:'',style:{},children:[],value:'',appendChild(c){this.children.push(c);},replaceChildren(...c){this.children=c;}});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{...create(id),hidden:false,disabled:false,width:800,height:600,files:[],getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,saves,doc:{getElementById:get,createElement:create},saveJson:(name,text)=>saves.push({name,text}),fire:(id,type='input')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,'missing listener '+id+':'+type);return fn();}};
}
const runtimeFixture={diagnostics:{backend:'fixture API, not physics'}};
const init=(ui,extra={})=>initializeLensSpotLab({doc:ui.doc,loadRuntime:async()=>runtimeFixture,evaluate:async(_runtime,p,options)=>{options.onProgress({completed:1,total:1,phase:'channel',wavelength:450e-9});return fixtureResult(p);},yieldControl:async()=>{},saveJson:ui.saveJson,...extra});

test('UI waits for explicit calculation, forwards canonical profile and keeps kernel intervals',async()=>{
  const ui=harness(),calls=[];const lab=await init(ui,{evaluate:async(r,p,o)=>{calls.push(copy(p));o.onProgress({completed:3,total:3,phase:'channel'});return fixtureResult(p);}});
  assert.equal(calls.length,0);assert.equal(lab.getState().output,null);assert.equal(ui.get('spot-controls').disabled,false);assert.equal(ui.saves.length,0);
  ui.get('spot-aperture').value='5';ui.fire('spot-aperture');ui.get('spot-sensor-z').value='60';ui.fire('spot-sensor-z');assert.equal(calls.length,0);
  const result=await lab.calculate();assert.equal(calls.length,1);assert.equal(calls[0].apertureRadius,.005);assert.equal(calls[0].sensorZ,.06);assert.equal(result.nodes.length,64);
  assert.equal(ui.get('spot-table').children.length,3);assert.match(ui.get('spot-table').children[0].children[3].textContent,/RMS² \[0\.000002000000, 0\.000008000000\] mm²/);
  assert.match(ui.get('spot-table').children[0].children[3].textContent,/重心X \[0\.001000000, 0\.003000000\]/);assert.ok(ui.draws.some(x=>x[0]==='strokeRect'));
  assert.match(ui.get('spot-elapsed').textContent,/ms/);assert.equal(ui.get('spot-progress').value,3);assert.equal(ui.saves.length,0);
  assert.deepEqual(JSON.parse(ui.get('spot-result-json').textContent).channels[0].result.stats,result.channels[0].result.stats);
  ui.get('spot-aperture').value='4';ui.fire('spot-aperture');assert.equal(lab.getState().output,null);assert.equal(ui.get('spot-table').children.length,0);assert.equal(ui.get('spot-save-result').disabled,true);assert.equal(calls.length,1);
});

test('unknown and unexecuted retain original weights and suppress final moments, never fake origin dots',async()=>{
  const p=createLensSpotProfile(),out=fixtureResult(p,{unknown:true}),rows=lensSpotDisplayData(out);
  assert.equal(rows[0].counts.notExamined,1);assert.equal(rows[0].weights.notExamined,1/64);assert.equal(rows[0].points.length,63);assert.equal(rows[0].stats,null);
  const ui=harness(),lab=await init(ui,{evaluate:async()=>out});await lab.calculate();assert.match(ui.get('spot-table').children[0].children[3].textContent,/最終統計なし/);assert.match(ui.get('spot-table').children[0].children[2].textContent,/未実行 Σw≈0\.01562500/);
  const absent=lensSpotDisplayData(fixtureResult(p,{absent:true}));assert.equal(absent[0].counts.unknown,64);assert.equal(absent[0].points.length,0);assert.equal(absent[0].stats,null);
  const corrupt=fixtureResult(p,{unknown:true});corrupt.channels[0].result.stats=fixtureResult(p).channels[0].result.stats;assert.throws(()=>lensSpotDisplayData(corrupt),/最終統計/);
  const missing=fixtureResult(p);missing.channels[0].result.records.pop();assert.throws(()=>lensSpotDisplayData(missing),/不足/);
  const noPosition=fixtureResult(p);noPosition.channels[0].result.records[0].sensor=null;assert.throws(()=>lensSpotDisplayData(noPosition),/包含/);
  const noStats=fixtureResult(p);noStats.channels[0].result.stats.moments=null;assert.equal(lensSpotDisplayData(noStats)[0].stats.moments,null);
  const mixed=fixtureResult(p);for(const channel of mixed.channels){['route_miss','branch_unavailable','sensor_miss'].forEach((status,i)=>{channel.result.records[i].status=status;channel.result.records[i].sensor=null;});channel.result.stats.acceptedWeight=[61/64,61/64];}
  const display=lensSpotDisplayData(mixed)[0];assert.equal(display.points.length,61);for(const key of ['routeMiss','branchUnavailable','sensorMiss']){assert.equal(display.counts[key],1);assert.equal(display.weights[key],1/64);}assert.deepEqual(display.stats.acceptedWeight,[61/64,61/64]);
});

test('profile roundtrip preserves non-UI source scale, material, wavelengths, settings and binary64 inputs',async()=>{
  const ui=harness(),received=[],lab=await init(ui,{evaluate:async(_r,p)=>{received.push(copy(p));return fixtureResult(p);}});
  const p=createLensSpotProfile({apertureRadius:.01234567890123456,sensorZ:.0567890123456789,radialSamples:3,angularSamples:10,source:{kind:'parallel',direction:[.25,-.5,2]},wavelengths:[500e-9],material:{coefficients:[1.49,2e-15,0]},settings:{maximumSampleEvaluations:17}});
  assert.equal(await lab.loadProfile(JSON.stringify(p)),true);assert.equal(received.length,0);await lab.calculate();assert.deepEqual(received[0],p);
  ui.get('spot-aperture').value='9';ui.fire('spot-aperture');await lab.calculate();assert.deepEqual(received[1],{...p,apertureRadius:.009});
  ui.get('spot-tan-x').value='.2';ui.fire('spot-tan-x');await lab.calculate();assert.deepEqual(received[2].source,{kind:'parallel',direction:[.2,-.25,1]});
  assert.equal(ui.saves.length,0);ui.fire('spot-save-profile','click');assert.equal(ui.saves.length,1);assert.deepEqual(JSON.parse(ui.saves[0].text),received[2]);
  ui.fire('spot-save-result','click');assert.equal(ui.saves.length,2);assert.deepEqual(JSON.parse(ui.saves[1].text).profile,received[2]);
});

test('finite source, invalid input and invalid profile clear stale output without automatic calculation',async()=>{
  const ui=harness();let calls=0;const lab=await init(ui,{evaluate:async(_r,p)=>{++calls;return fixtureResult(p);}});await lab.calculate();
  ui.get('spot-source-mode').value='finite';ui.fire('spot-source-mode','change');assert.equal(ui.get('spot-finite-controls').hidden,false);assert.equal(calls,1);await lab.calculate();assert.deepEqual(lab.getState().output.profile.source,{kind:'finite',position:[0,0,-1]});
  ui.get('spot-source-z').value='';ui.fire('spot-source-z');assert.equal(lab.getState().output,null);assert.equal(await lab.calculate(),null);assert.equal(calls,2);assert.match(ui.get('spot-error').textContent,/有限/);
  ui.get('spot-source-z').value='-2';ui.fire('spot-source-z');await lab.calculate();assert.equal(calls,3);
  assert.equal(await lab.loadProfile('{broken'),false);assert.equal(lab.getState().output,null);assert.equal(calls,3);assert.equal(ui.get('spot-result-json').textContent,'結果なし');
  assert.equal(await lab.loadProfile(JSON.stringify({...createLensSpotProfile(),unrecognized:true})),false);assert.equal(calls,3);
  ui.fire('spot-reset','click');assert.deepEqual(lab.getState().profile,createLensSpotProfile());assert.equal(calls,3);
});

test('busy calculation locks editing/retry/save, reports real progress and does not interleave a second run',async()=>{
  const ui=harness();let finish,calls=0,clock=0;const lab=await init(ui,{now:()=>clock,evaluate:async(_r,p,o)=>{++calls;o.onProgress({completed:16,total:67,phase:'launch'});await new Promise(resolve=>{finish=resolve;});return fixtureResult(p);}});
  const pending=lab.calculate();await Promise.resolve();await Promise.resolve();assert.equal(lab.getState().busy,true);assert.equal(ui.get('spot-controls').disabled,true);assert.equal(ui.get('spot-retry').disabled,true);assert.equal(ui.get('spot-progress').value,16);
  assert.equal(await lab.calculate(),null);assert.equal(await lab.loadProfile('{}'),false);await lab.retry();ui.fire('spot-save-profile','click');assert.equal(ui.saves.length,0);assert.equal(calls,1);
  clock=125;finish();await pending;assert.equal(lab.getState().busy,false);assert.equal(ui.get('spot-controls').disabled,false);assert.match(ui.get('spot-elapsed').textContent,/125\.0000 ms/);
});

test('runtime failure, legacy WASM and calculation failure retain no old result and recover on explicit retry',async()=>{
  const ui=harness();let offline=true,legacy=true;const lab=await init(ui,{loadRuntime:async()=>{if(offline)throw new Error('offline');return runtimeFixture;},evaluate:async(_r,p)=>{if(legacy)throw new Error('Lens spot C++ API unavailable');return fixtureResult(p);}});
  assert.equal(ui.get('spot-controls').disabled,true);assert.equal(lab.getState().output,null);assert.equal(await lab.calculate(),null);
  offline=false;await lab.retry();assert.equal(ui.get('spot-controls').disabled,false);assert.equal(lab.getState().output,null);await lab.calculate();assert.equal(lab.getState().output,null);assert.match(ui.get('spot-error').textContent,/同梱WASM/);
  legacy=false;await lab.retry();assert.equal(lab.getState().output,null);await lab.calculate();assert.ok(lab.getState().output);assert.equal(ui.get('spot-error').hidden,true);
  offline=true;await lab.retry();assert.equal(lab.getState().output,null);assert.equal(ui.get('spot-table').children.length,0);assert.equal(ui.get('spot-controls').disabled,true);
});

test('file loading and saving are user actions and oversize or malformed files erase stale output',async()=>{
  const ui=harness(),lab=await init(ui);await lab.calculate();const p=createLensSpotProfile({sensorZ:.065});
  ui.get('spot-load-profile').files=[{size:100,text:async()=>JSON.stringify(p)}];await ui.fire('spot-load-profile','change');assert.deepEqual(lab.getState().profile,p);assert.equal(lab.getState().output,null);assert.equal(ui.saves.length,0);
  await lab.calculate();ui.get('spot-load-profile').files=[{size:3*1024*1024,text:async()=>{throw new Error('must not read');}}];await ui.fire('spot-load-profile','change');assert.equal(lab.getState().output,null);assert.match(ui.get('spot-error').textContent,/2MiB/);assert.equal(ui.saves.length,0);
});

test('static Japanese lesson, original vector diagram and exactly one build registration are available',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);
  for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));
  for(const term of ['輝度画像','波動PSF','中央値','未実行','HTTP/HTTPS','保存ボタン'])assert.ok(html.includes(term),term);
  assert.match(html,/src="lens-spot-lab\.mjs(?:\?[^\"]*)?"/);assert.doesNotMatch(html,/<script[^>]+src="https?:/);
  const index=await readFile(new URL('../docs/learn/index.html',import.meta.url),'utf8');assert.equal([...index.matchAll(/<article\s/g)].length,23);assert.match(index,/id="lens-spot"/);
  const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.equal((build.match(/\['tools\/lens-spot-lab.html','\.\.\/','lens-spot-lab.mjs'\]/g)??[]).length,1);
  const svg=await readFile(new URL('../docs/learn/diagrams/lens-spot.svg',import.meta.url),'utf8');assert.match(svg,/<svg /);assert.doesNotMatch(svg,/<image|https?:\/\/(?!www.w3.org)/);
  const ui=harness();drawLensSpot(ui.get('spot-view'),lensSpotDisplayData(fixtureResult(createLensSpotProfile(),{absent:true})));assert.equal(ui.draws.filter(d=>d[0]==='arc').length,0);
});

let runtime;
async function actualRuntime(){if(!runtime)runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});return runtime;}

test('actual C++ WASM: axial small-aperture spot keeps shared pupil weights and sensor enclosures',async()=>{
  const r=await actualRuntime(),p=createLensSpotProfile({apertureRadius:.0001,radialSamples:2,angularSamples:8}),progress=[];
  const out=await evaluateLensSpotProfile(r,p,{onProgress:p=>progress.push(p),yieldControl:async()=>{}});const rows=lensSpotDisplayData(out);
  assert.equal(rows.length,3);assert.equal(out.nodes.length,16);assert.equal(out.samples.length,16);assert.equal(progress.at(-1).completed,progress.at(-1).total);assert.match(out.diagnostics.backend,/C\+\+ WebAssembly/);
  for(const row of rows){assert.equal(row.channel.result.status,'completed');assert.equal(row.counts.accepted,16);assert.ok(row.stats?.moments);encloses(row.stats.totalWeight,1);encloses(row.stats.acceptedWeight,1);encloses(row.stats.moments.centroid[0],0);encloses(row.stats.moments.centroid[1],0);assert.ok(row.stats.moments.meanSquaredRadius[0]>=0);
    for(const point of row.points){encloses(point.position[2],p.sensorZ);assert.equal(point.weight,1/16);}
  }
  // Every wavelength is supplied the same geometric rays and original weights.
  assert.equal(out.channels.length,3);assert.deepEqual(out.samples.map(s=>s.weight),Array(16).fill(1/16));
});

test('actual C++ WASM: finite object construction and budget failures retain all original samples',async()=>{
  const r=await actualRuntime(),p=createLensSpotProfile({apertureRadius:.0001,radialSamples:2,angularSamples:8,source:{kind:'finite',position:[0,0,-1]},settings:{maximumSampleEvaluations:1}});
  const out=await evaluateLensSpotProfile(r,p,{yieldControl:async()=>{}}),rows=lensSpotDisplayData(out);
  for(const row of rows){assert.equal(row.channel.result.status,'budget_exceeded');assert.equal(row.channel.result.records.length,16);assert.equal(row.stats,null);assert.ok(row.counts.notExamined>=15);assert.equal(row.weights.notExamined,15/16);}
  for(let k=0;k<3;++k){encloses(out.samples[0].ray.origin[k],p.source.position[k]);encloses(out.samples[0].ray.direction[k],out.nodes[0].position[k]-p.source.position[k]);}
});

test('actual WASM through UI: explicit focus changes produce new raw results, profile reload does not trace',async()=>{
  const ui=harness(),r=await actualRuntime();let calls=0;const lab=await init(ui,{loadRuntime:async()=>r,evaluate:async(...args)=>{++calls;return evaluateLensSpotProfile(...args);}});
  await lab.loadProfile(JSON.stringify(createLensSpotProfile({apertureRadius:.0001,radialSamples:2,angularSamples:8})));assert.equal(calls,0);await lab.calculate();const before=lab.getState().output;assert.ok(before);assert.equal(calls,1);
  ui.get('spot-sensor-z').value='70';ui.fire('spot-sensor-z');assert.equal(lab.getState().output,null);assert.equal(calls,1);await lab.calculate();const after=lab.getState().output;assert.equal(calls,2);assert.equal(after.profile.sensorZ,.07);
  assert.notDeepEqual(after.channels[1].result.stats.moments.meanSquaredRadius,before.channels[1].result.stats.moments.meanSquaredRadius);assert.equal(ui.saves.length,0);
});
