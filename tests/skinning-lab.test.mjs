import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {initializeSkinningLab,makeSkinningCase,runSkinningCase} from '../tools/skinning-lab.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const htmlUrl=new URL('../tools/skinning-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8'),ids=new Set([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
const near=(a,b)=>assert.ok(Math.abs(a-b)<2e-12,`${a} != ${b}`);
function harness(){
 const calls=[],listeners=new Map(),elements=new Map(),saves=[],draws=[],canvasDraws=new Map();
 const context=id=>{if(!canvasDraws.has(id))canvasDraws.set(id,[]);return Object.fromEntries(['fillRect','fillText','setLineDash','beginPath','moveTo','lineTo','closePath','stroke','arc','fill'].map(k=>[k,(...args)=>{draws.push([k,...args]);canvasDraws.get(id).push([k,...args]);}]));};
 const element=tag=>({tag,value:'',hidden:false,disabled:false,textContent:'',children:[],appendChild(child){this.children.push(child);},replaceChildren(){this.children=[];}});
 const get=id=>{assert.ok(ids.has(id),id);if(!elements.has(id))elements.set(id,{...element(id),width:800,height:390,getContext:()=>context(id),addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};get('sk-example').value='arm';
 return {doc:{getElementById:get,createElement:element},get,calls,saves,draws,canvasDraws,saveJson:(name,text)=>saves.push({name,text}),fire:(id,type='input')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,id+':'+type);return fn();}};
}
function fake(){
 const calls=[],matrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
 const runtime={calls,diagnostics:{backend:'fixture'},sampleMotion(source,time){calls.push({method:'motion',source:structuredClone(source),time});return {status:'completed',bones:source.bones.map(b=>({id:b.id,worldMatrix:[...matrix]}))};},bindSkin(rest,settings){calls.push({method:'bind',rest:structuredClone(rest),settings});return {status:'completed',joints:rest.map(b=>({id:b.id,restWorld:b.matrix,inverseBind:[...matrix]})),positions:null,diagnostics:[],weightResiduals:[]};},deformSkin(input,settings){calls.push({method:'deform',input:structuredClone(input),settings});return runtime.respond?runtime.respond(input):{status:'completed',joints:null,positions:input.vertices.map(v=>v.position.map(x=>x+.5)),diagnostics:[],weightResiduals:input.vertices.map(()=>0)};}};return runtime;
}
const initialize=(ui,runtime,extra={})=>initializeSkinningLab({doc:ui.doc,loadRuntime:async()=>runtime,saveJson:ui.saveJson,...extra});

test('skinning preview obtains FK inverse binding and positions only from runtime calls',async()=>{
 const ui=harness(),runtime=fake(),lab=await initialize(ui,runtime);assert.deepEqual(runtime.calls.map(x=>x.method),['motion','motion','bind','deform']);assert.equal(runtime.calls[0].time,0);assert.equal(runtime.calls[0].source.clip.tracks.length,0);assert.equal(runtime.calls[1].time,1);assert.equal(ui.get('sk-rows').children.length,6);assert.equal(lab.getState().packet.deformation.positions[0][0],.5);assert.ok(ui.draws.some(x=>x[0]==='lineTo'));assert.equal(ui.saves.length,0);
 const snapshot=lab.getState();snapshot.packet.source.vertices[0].position[0]=999;assert.equal(lab.getState().packet.source.vertices[0].position[0],0);
 const xy=ui.canvasDraws.get('sk-xy'),xz=ui.canvasDraws.get('sk-xz');assert.ok(xz.some(x=>x[0]==='fillText'&&x[1].startsWith('XZ')));assert.equal(new Set(xz.filter(x=>x[0]==='arc').map(x=>x[2])).size,2,'flat source z0 and translated z0.5 form two horizontal rows');assert.ok(new Set(xy.filter(x=>x[0]==='arc').map(x=>x[2])).size>2,'XY retains varying Y');
});

test('skinning input changes clear old geometry and require explicit query; exports retain all input weights',async()=>{
 const ui=harness(),runtime=fake(),lab=await initialize(ui,runtime);ui.get('sk-child').value='3';ui.fire('sk-child');assert.equal(lab.getState().packet,null);assert.equal(ui.get('sk-rows').children.length,0);assert.equal(ui.get('sk-save').disabled,true);assert.equal(runtime.calls.length,4);ui.fire('sk-run','click');const packet=lab.getState().packet;assert.deepEqual(packet.source.vertices[1].influences,[{id:19,weight:3},{id:7,weight:1}]);assert.deepEqual(packet.source.vertices[0].influences,[{id:7,weight:1}]);ui.fire('sk-save','click');assert.equal(ui.saves.length,1);assert.deepEqual(JSON.parse(ui.saves[0].text),packet);assert.equal(ui.get('sk-save').disabled,false);
});

test('skinning model failure keeps diagnostic packet exportable and draws no stale positions',async()=>{
 const ui=harness(),runtime=fake(),lab=await initialize(ui,runtime);runtime.respond=()=>({status:'numerical_failure',joints:null,positions:null,diagnostics:[{id:7,condition:1,residual:0,pivotFailure:false}],weightResiduals:[]});const failed=lab.query();assert.equal(failed.deformation.positions,null);assert.equal(ui.get('sk-rows').children.length,0);assert.equal(ui.get('sk-stats').textContent,'変形位置なし');assert.match(ui.get('sk-status').textContent,/numerical_failure/);ui.fire('sk-save','click');assert.equal(JSON.parse(ui.saves[0].text).deformation.status,'numerical_failure');runtime.respond=null;assert.equal(lab.query().deformation.status,'completed');
});

test('skinning rejects blank and parse-underflow fields and malformed completed output',async()=>{
 const ui=harness(),runtime=fake(),lab=await initialize(ui,runtime);for(const value of ['', '1e-999']){ui.get('sk-child').value=value;ui.fire('sk-child');assert.equal(lab.query(),null);assert.equal(lab.getState().packet,null);assert.equal(ui.get('sk-save').disabled,true);}ui.get('sk-child').value='1';runtime.respond=()=>({status:'completed',positions:[[NaN,0,0]]});assert.equal(lab.query(),null);assert.match(ui.get('sk-error').textContent,/欠損\/非有限/);
});

test('skinning retry preserves edited controls and old SDK never substitutes JavaScript calculations',async()=>{
 const ui=harness(),runtime=fake();let offline=true;const lab=await initialize(ui,runtime,{loadRuntime:async()=>{if(offline)throw new Error('offline');return runtime;}});assert.equal(lab.getState().available,false);assert.equal(ui.get('sk-run').disabled,true);ui.get('sk-child').value='2';offline=false;await lab.retry();assert.equal(lab.getState().packet.source.vertices[1].influences[0].weight,2);
 const old=fake();old.bindSkin=()=>{throw new Error('Skinning WASM API unavailable');};const missing=await initialize(harness(),old);assert.equal(missing.getState().packet,null);assert.equal(old.calls.filter(c=>c.method==='deform').length,0);assert.throws(()=>runSkinningCase({},makeSkinningCase('arm')),/同梱/);
});

test('skinning static cases skip FK and preserve exact opposing translations and tiny author weights',()=>{
 const runtime=fake(),input=makeSkinningCase('cancellation',0,1,1),before=structuredClone(input),packet=runSkinningCase(runtime,input);assert.deepEqual(input,before);assert.deepEqual(runtime.calls.map(x=>x.method),['bind','deform']);assert.equal(packet.input.pose[0].matrix[12],-(2**53));assert.equal(packet.input.pose[1].matrix[12],2**53);const tiny=makeSkinningCase('underflow',0,Number.MIN_VALUE,Number.MAX_VALUE);assert.equal(tiny.vertices[0].influences[1].weight,Number.MIN_VALUE);assert.equal(tiny.vertices[0].influences[0].weight,Number.MAX_VALUE);
});

test('skinning static page and build entry describe actual SDK and draw-only limitations',async()=>{
 const all=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);assert.equal(all.length,new Set(all).size);for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));for(const text of ['2048','65536','JavaScriptでは逆行列・LBS・FKを再実装しません','原本binding','HTTP/HTTPS','Float32','入力と結果JSONを保存'])assert.ok(html.includes(text),text);const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.equal((build.match(/\['tools\/skinning-lab.html','\.\.\/','skinning-lab.mjs'\]/g)??[]).length,1);
});

let runtime;async function actual(){return runtime??=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});}
test('actual skin SDK preview gives analytic six-vertex ribbon at rest and right-angle key',async()=>{
 const r=await actual(),source=makeSkinningCase('arm',0),rest=runSkinningCase(r,source);assert.equal(rest.deformation.status,'completed');rest.deformation.positions.forEach((p,j)=>p.forEach((x,k)=>near(x,source.vertices[j].position[k])));const moved=runSkinningCase(r,makeSkinningCase('arm',1));const expected=[[0,-.2,0],[1.1,-.1,0],[1.2,1,0],[0,.2,0],[.9,.1,0],[.8,1,0]];moved.deformation.positions.forEach((p,j)=>p.forEach((x,k)=>near(x,expected[j][k])));
});

test('actual skin SDK preview edits middle weight only and exports unchanged source originals',async()=>{
 const ui=harness(),lab=await initialize(ui,await actual()),original=lab.getState().packet.source;ui.get('sk-child').value='3';ui.fire('sk-child');ui.fire('sk-run','click');const packet=lab.getState().packet;near(packet.deformation.positions[1][0],1.15);near(packet.deformation.positions[1][1],-.05);assert.deepEqual(packet.source.vertices[0],original.vertices[0]);assert.deepEqual(packet.source.vertices[2],original.vertices[2]);assert.equal(packet.source.vertices[1].influences[0].weight,3);ui.fire('sk-save','click');assert.deepEqual(JSON.parse(ui.saves[0].text),packet);
});

test('actual skin SDK preview retains shear and handles cancellation underflow failure and retry',async()=>{
 const r=await actual(),shear=runSkinningCase(r,makeSkinningCase('shear',1)),m=shear.input.pose.find(b=>b.id===19).matrix;near(m[0]*m[4]+m[1]*m[5],-36/25);assert.equal(shear.deformation.status,'completed');assert.equal(runSkinningCase(r,makeSkinningCase('cancellation',0)).deformation.positions[0][0],1);
 const ui=harness(),lab=await initialize(ui,r);ui.get('sk-example').value='underflow';ui.fire('sk-example','change');ui.fire('sk-run','click');assert.equal(lab.getState().packet.deformation.status,'numerical_failure');assert.equal(ui.get('sk-rows').children.length,0);assert.equal(lab.getState().packet.source.vertices[0].influences[1].weight,Number.MIN_VALUE);ui.get('sk-root').value='1';ui.get('sk-child').value='1';ui.fire('sk-root');ui.fire('sk-run','click');assert.deepEqual(lab.getState().packet.deformation.positions,[[1,0,0]]);
});

test('actual skin SDK failed inverse binding returns only diagnostics and retries without old geometry',async()=>{
 const ui=harness(),lab=await initialize(ui,await actual());ui.get('sk-example').value='shear';ui.fire('sk-example','change');ui.get('sk-condition').value='1';ui.fire('sk-condition');ui.fire('sk-run','click');const failed=lab.getState().packet;assert.equal(failed.binding.status,'ill_conditioned');assert.equal(failed.binding.joints,null);assert.equal(failed.deformation,null);assert.equal(ui.get('sk-rows').children.length,0);assert.equal(ui.get('sk-save').disabled,false);ui.get('sk-condition').value='1e10';ui.fire('sk-condition');ui.fire('sk-run','click');assert.equal(lab.getState().packet.deformation.status,'completed');assert.equal(ui.get('sk-rows').children.length,6);
});
