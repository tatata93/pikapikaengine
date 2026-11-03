import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {OPTICS_DEFAULTS,opticsPreset,opticsCase,evaluateOpticsCase,initializeOpticsLab} from '../tools/optics-lab.mjs';

const wasmBytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes});
const htmlUrl=new URL('../tools/optics-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8');
const close=(actual,expected,tolerance=2e-13)=>assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} != ${expected}`);

test('real C++ WASM normal incidence returns four-percent power and kernel directions',()=>{
  assert.equal(runtime.diagnostics.backend,'C++ WebAssembly');
  const state=evaluateOpticsCase(runtime,OPTICS_DEFAULTS),{source,result}=state;
  assert.deepEqual(source.query.incident,[0,-1,0]);assert.deepEqual(source.query.normal,[0,1,0]);
  assert.equal(result.kind,'transmission');assert.equal(result.uncertainty,'none');
  assert.deepEqual(result.reflected,[0,1,0]);assert.deepEqual(result.transmitted,[0,-1,0]);
  close(result.power.reflectanceS,1/25);close(result.power.reflectanceP,1/25);
  close(result.power.transmittanceS,24/25);close(result.power.transmittanceP,24/25);
  assert.ok(result.discriminant[0]>0);close(source.query.vacuumWavelength,550e-9,1e-21);
});

test('real Brewster, TIR and homogeneous queries retain distinct direction/power validity',()=>{
  const brewster=evaluateOpticsCase(runtime,opticsPreset('brewster')).result;
  assert.equal(brewster.kind,'transmission');assert.ok(brewster.power.reflectanceP<1e-28);
  close(brewster.power.reflectanceS,25/169);close(brewster.power.transmittanceS,144/169);
  const tir=evaluateOpticsCase(runtime,opticsPreset('tir')).result;
  assert.equal(tir.kind,'total_internal_reflection');assert.equal(tir.transmitted,null);assert.equal(tir.cosineTransmitted,null);
  assert.equal(tir.power.reflectanceS,1);assert.equal(tir.power.transmittanceP,0);assert.ok(tir.discriminant[1]<0);
  const same=evaluateOpticsCase(runtime,opticsPreset('equal')).result;
  assert.equal(same.kind,'transmission');assert.equal(same.power.reflectanceUnpolarized,0);assert.equal(same.power.transmittanceUnpolarized,1);
  assert.deepEqual(same.transmitted,same.incidentUnit);
});

test('exact critical source vector reaches actual C++ interval query without angle reconstruction',()=>{
  const {source,result}=evaluateOpticsCase(runtime,opticsPreset('critical'));
  assert.equal(source.incidentSource,'exact-critical-vector');assert.deepEqual(source.query.incident,[3,-4,0]);
  assert.equal(source.query.indexIncident,5);assert.equal(source.query.indexTransmitted,3);
  assert.equal(result.kind,'uncertain');assert.equal(result.uncertainty,'critical_angle');
  assert.equal(result.power,null);assert.equal(result.transmitted,null);assert.equal(result.cosineTransmitted,null);
  assert.ok(result.discriminant[0]<=0&&result.discriminant[1]>=0);
  const copy=opticsPreset('critical');copy.incidentOverride[0]=99;
  assert.deepEqual(opticsPreset('critical').incidentOverride,[3,-4,0]);
});

test('wavelength conversion is explicit and does not invent dispersion',()=>{
  const blue=evaluateOpticsCase(runtime,{angleDegrees:35,wavelengthNm:450}),red=evaluateOpticsCase(runtime,{angleDegrees:35,wavelengthNm:650});
  close(blue.source.query.vacuumWavelength,450e-9,1e-21);close(red.source.query.vacuumWavelength,650e-9,1e-21);
  assert.equal(blue.source.query.indexIncident,red.source.query.indexIncident);assert.equal(blue.source.query.indexTransmitted,red.source.query.indexTransmitted);
  assert.deepEqual(blue.result.power,red.result.power);assert.deepEqual(blue.result.transmitted,red.result.transmitted);
  close(blue.result.vacuumWavelength,450e-9,1e-21);
});

function documentHarness() {
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1])),listeners=new Map(),elements=new Map(),calls=[];
  const context=new Proxy({}, {get(target,key){return key in target?target[key]:(...args)=>calls.push({method:key,args});},set(target,key,value){target[key]=value;return true;}});
  const defaults={angle:'0','index-incident':'1','index-transmitted':'1.5',wavelength:'550'};
  function get(id) {
    assert.ok(ids.has(id),`unknown HTML element ${id}`);
    if(!elements.has(id))elements.set(id,{value:defaults[id]??'',textContent:'',hidden:false,disabled:true,width:900,height:500,
      setAttribute(name,value){this[name]=value;},getContext(){return context;},addEventListener(type,callback){listeners.set(`${id}:${type}`,callback);}});
    return elements.get(id);
  }
  return {doc:{getElementById:get},get,calls,fire:(id,type='click')=>{const callback=listeners.get(`${id}:${type}`);assert.ok(callback,`missing listener ${id}:${type}`);return callback();}};
}

test('UI submits actual queries and draws the returned directions, retaining exact source until angle edits',async()=>{
  const ui=documentHarness(),submitted=[];
  const instrumented={get diagnostics(){return runtime.diagnostics;},queryDielectricInterface(input){submitted.push(structuredClone(input));return runtime.queryDielectricInterface(input);}};
  const lab=await initializeOpticsLab({doc:ui.doc,loadRuntime:async()=>instrumented});
  assert.equal(ui.get('optics-controls').disabled,false);assert.equal(submitted.length,1);
  assert.match(ui.get('power-ru').textContent,/4\.00000/);assert.match(ui.get('power-tu').textContent,/96\.00000/);
  const initial=lab.getState();
  const tip=[450+initial.result.reflected[0]*190,245-initial.result.reflected[1]*190];
  assert.ok(ui.calls.some(call=>call.method==='lineTo'&&call.args[0]===tip[0]&&call.args[1]===tip[1]),'returned reflection direction is drawn');
  assert.match(ui.get('optics-view')['aria-label'],/無偏光反射4/);
  ui.fire('preset-tir');assert.equal(lab.getState().result.kind,'total_internal_reflection');assert.match(ui.get('result-transmitted').textContent,/なし/);
  ui.fire('preset-critical');assert.equal(lab.getState().result.kind,'uncertain');
  for(const id of ['power-rs','power-ts','power-rp','power-tp','power-ru','power-tu'])assert.equal(ui.get(id).textContent,'—');
  assert.match(ui.get('result-transmitted').textContent,/未確定/);assert.match(ui.get('result-explanation').textContent,/0%に置き換えません/);
  const json=JSON.parse(ui.get('optics-json').textContent);assert.equal(json.result.power,null);assert.deepEqual(json.input.incident,[3,-4,0]);
  ui.get('wavelength').value='450';ui.fire('wavelength','input');assert.deepEqual(submitted.at(-1).incident,[3,-4,0]);assert.equal(lab.getState().result.kind,'uncertain');
  close(submitted.at(-1).vacuumWavelength,450e-9,1e-21);assert.match(ui.get('wavelength-metres').textContent,/分散モデル未導入/);
  ui.get('index-incident').value='4.9';ui.fire('index-incident','input');assert.deepEqual(submitted.at(-1).incident,[3,-4,0]);assert.equal(lab.getState().result.kind,'transmission');
  ui.get('angle').value='60';ui.fire('angle','input');assert.equal(lab.getState().source.incidentSource,'angle');assert.equal(lab.getState().source.parameters.incidentOverride,null);
  close(submitted.at(-1).incident[0],Math.sin(Math.PI/3));close(submitted.at(-1).incident[1],-0.5);assert.notDeepEqual(submitted.at(-1).incident,[3,-4,0]);
  assert.match(ui.get('input-source').textContent,/JavaScript/);
  ui.fire('preset-brewster');assert.ok(lab.getState().result.power.reflectanceP<1e-28);
  ui.fire('preset-equal');assert.equal(lab.getState().result.power.transmittanceUnpolarized,1);assert.match(ui.get('result-explanation').textContent,/解析的/);
  ui.fire('preset-normal');assert.equal(lab.getState().source.parameters.angleDegrees,0);assert.equal(ui.get('optics-error').hidden,true);
});

test('UI clears stale success after input or real C++ rejection and recovers on valid input',async()=>{
  const ui=documentHarness();let rejectNext=false,calls=0;
  const instrumented={get diagnostics(){return runtime.diagnostics;},queryDielectricInterface(input){calls++;return runtime.queryDielectricInterface(rejectNext?(rejectNext=false,{...input,indexIncident:0}):input);}};
  const lab=await initializeOpticsLab({doc:ui.doc,loadRuntime:async()=>instrumented});assert.ok(lab.getState());
  ui.get('index-incident').value='NaN';ui.fire('index-incident','input');assert.equal(lab.getState(),null);assert.equal(ui.get('power-ru').textContent,'—');assert.equal(calls,1);
  assert.match(ui.get('optics-error').textContent,/照会できません/);assert.match(ui.get('optics-view')['aria-label'],/表示していません/);
  ui.fire('preset-normal');assert.equal(lab.getState().result.kind,'transmission');assert.equal(ui.get('optics-error').hidden,true);
  rejectNext=true;lab.recalculate();assert.equal(lab.getState(),null);assert.equal(ui.get('result-kind').textContent,'—');assert.equal(ui.get('power-ts').textContent,'—');
  assert.match(ui.get('optics-error').textContent,/indices|屈折率/);assert.equal(ui.get('optics-controls').disabled,false);
  ui.fire('preset-brewster');assert.equal(lab.getState().result.kind,'transmission');assert.equal(ui.get('optics-error').hidden,true);
});

test('initialization failure has no substitute result; retry obtains real WASM output',async()=>{
  const ui=documentHarness();let attempts=0;
  const lab=await initializeOpticsLab({doc:ui.doc,loadRuntime:async()=>{if(attempts++===0)throw new Error('fixture load failure');return runtime;}});
  assert.equal(lab.getState(),null);assert.equal(ui.get('optics-controls').disabled,true);assert.equal(ui.get('power-ru').textContent,'—');
  assert.match(ui.get('optics-error').textContent,/fixture load failure/);assert.equal(ui.get('optics-retry').disabled,false);
  await ui.fire('optics-retry');assert.equal(lab.getState().result.kind,'transmission');close(lab.getState().result.power.reflectanceUnpolarized,0.04);
  assert.equal(ui.get('optics-controls').disabled,false);assert.equal(ui.get('optics-error').hidden,true);
});

test('HTML and original SVG resources exist, IDs match and numerical scope is explicit',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);assert.equal(new Set(ids).size,ids.length);
  for(const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    const target=new URL(match[1],htmlUrl);if(target.protocol==='file:'){const fragment=target.hash.slice(1);target.hash='';await access(target);if(fragment)assert.ok((await readFile(target,'utf8')).includes(`id="${fragment}"`));}
  }
  assert.match(html,/<script type="module" src="optics-lab\.mjs(?:\?[^"]*)?"><\/script>/);
  for(const text of ['分散モデルは未導入','通常doubleの近似','file://','HTTP/HTTPS','放射輝度','多面レンズ','元ベクトル'])assert.ok(html.includes(text),`missing scope: ${text}`);
  const svg=await readFile(new URL('../docs/learn/diagrams/optical-interface.svg',import.meta.url),'utf8');assert.match(svg,/<title /);assert.match(svg,/<desc /);assert.ok(!/<image\b|https?:\/\//.test(svg.replace('http://www.w3.org/2000/svg','')));
  for(const parameters of [{angleDegrees:NaN},{angleDegrees:90},{indexIncident:0},{indexTransmitted:6},{wavelengthNm:Infinity},{wavelengthNm:300},{incidentOverride:[3,-4,1]}])assert.throws(()=>opticsCase(parameters));
  assert.throws(()=>opticsPreset('lens'));
});
