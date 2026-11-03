import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {defaultSkinBindingSource,parseSkinBindingSource,serializeSkinBindingSource,parseSkinBindingPortable,serializeSkinBindingPortable} from '../engine/skin-binding.mjs';
import {initializeSkinBindingLab} from '../tools/skin-binding-lab.mjs';
import {Scene,meshEntity} from '../engine/scene.mjs';
const htmlUrl=new URL('../tools/skin-binding-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8'),ids=new Set([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const fresh=()=>defaultSkinBindingSource(runtime),close=(a,b)=>assert.ok(Math.abs(a-b)<2e-12,`${a} != ${b}`);
function harness(){
 const elements=new Map(),listeners=new Map(),saves=[],draws=[];
 const element=()=>({value:'',textContent:'',hidden:false,disabled:false,checked:false,children:[],files:[],appendChild(e){this.children.push(e);},replaceChildren(){this.children=[];}});
 const get=id=>{const full='sb-'+id;assert.ok(ids.has(full),full);if(!elements.has(id)){const context=Object.fromEntries(['fillRect','fillText','setLineDash','beginPath','moveTo','lineTo','closePath','stroke','arc','fill'].map(k=>[k,(...args)=>draws.push([id,k,...args])]));elements.set(id,{...element(),width:800,height:390,getContext:()=>context,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});}return elements.get(id);};
 for(const id of ['time','vertex','bone','weight'])get(id).value=({time:'1',vertex:'1',bone:'19',weight:'1'})[id];
 return {get,draws,saves,doc:{getElementById:id=>get(id.slice(3)),createElement:()=>element()},fire:(id,type='click')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,id+':'+type);return fn();},saveFile:(name,text,type)=>saves.push({name,text,type})};
}
async function initialize(ui,extra={}){return initializeSkinBindingLab({doc:ui.doc,loadRuntime:async()=>runtime,saveFile:ui.saveFile,...extra});}
const file=text=>{const bytes=new TextEncoder().encode(text);return {size:bytes.byteLength,arrayBuffer:async()=>bytes.buffer};};

function previewHarness(){
 const instances=[];let rejectCreate=false,rejectDraw=false;
 const createRenderer=async(canvas,onError)=>{
  if(rejectCreate)throw new Error('GPU unavailable');
  const own={draws:[],clears:0,disposed:0,onError,render(items){assert.deepEqual(items,[]);this.clears++;},async renderChecked(items,camera){if(rejectDraw)throw new Error('GPU validation');this.draws.push({items,camera});},dispose(){this.disposed++;}};
  instances.push(own);return own;
 };
 return {instances,createRenderer,setCreateFailure:value=>{rejectCreate=value;},setDrawFailure:value=>{rejectDraw=value;}};
}

test('binding 3D uses owned successful geometry and camera updates never repeat C++ queries',async()=>{
 const ui=harness(),gpu=previewHarness(),counted=Object.create(runtime);let samples=0,prepares=0;
 counted.sampleMotion=(...args)=>{samples++;return runtime.sampleMotion(...args);};counted.prepareDerivedMesh=(...args)=>{prepares++;return runtime.prepareDerivedMesh(...args);};
 const lab=await initialize(ui,{loadRuntime:async()=>counted,createRenderer:gpu.createRenderer});
 assert.equal(ui.get('3d').hidden,true);assert.equal(ui.get('show-3d').disabled,true);assert.equal(await lab.show3D(),false);
 lab.prepare();const before=lab.getState(),calls=[samples,prepares];assert.equal(await lab.show3D(),true);assert.equal(gpu.instances.length,1);
 const draw=gpu.instances[0].draws[0],entity=draw.items[0];assert.equal(entity.type,'derived-mesh');assert.equal(entity.mesh.vertexCount,6);assert.equal(entity.mesh.triangleCount,4);assert.equal(entity.mesh.floatCount,72);assert.deepEqual(entity.position,[0,0,0]);assert.deepEqual(entity.scale,[1,1,1]);assert.deepEqual(draw.camera,{eye:[3,2,4],target:[1,.35,0]});
 ui.get('view').value='back';assert.equal(await lab.show3D(),true);assert.deepEqual(gpu.instances[0].draws.at(-1).camera.eye,[1,.35,-4]);assert.deepEqual([samples,prepares],calls);
 assert.deepEqual(lab.getState().packet,before.packet);assert.deepEqual(lab.getState().derived,before.derived);assert.deepEqual(lab.getState().source,before.source);
 assert.equal(ui.get('3d').hidden,false);assert.match(ui.get('gpu-status').textContent,/4面 \/ 288 bytes/);lab.dispose();lab.dispose();assert.equal(gpu.instances[0].disposed,1);assert.equal(ui.get('3d').hidden,true);
});

test('binding 3D hides and releases old geometry on time/source/Scene/budget edits and model failures',async()=>{
 const ui=harness(),gpu=previewHarness(),lab=await initialize(ui,{createRenderer:gpu.createRenderer});
 for(const [id,event]of [['time','input'],['input','input'],['scene','input'],['derived-budget','input']]){
  lab.reset();lab.prepare();assert.equal(await lab.show3D(),true);const previous=gpu.instances[0].clears;
  ui.fire(id,event);assert.equal(ui.get('3d').hidden,true);assert.equal(lab.getState().derived,null);assert.ok(gpu.instances[0].clears>previous);assert.equal(ui.get('show-3d').disabled,true);
 }
 lab.reset();lab.prepare();await lab.show3D();const source=fresh();source.influences=source.mesh.positions.map(()=>[{boneId:7,weight:1},{boneId:19,weight:1}]);source.motion.clip.tracks[0].keys[1].rotation=[0,0,1,0];
 lab.readText(serializeSkinBindingSource(source));assert.equal(lab.prepare().status,'degenerate');assert.equal(ui.get('3d').hidden,true);assert.equal(await lab.show3D(),false);assert.equal(ui.get('save-json').disabled,false);
 lab.reset();lab.prepare();assert.equal(await lab.show3D(),true);lab.dispose();
});

test('binding GPU unavailable, draw rejection, and late device errors preserve numeric/source results and allow retry',async()=>{
 const ui=harness(),gpu=previewHarness(),lab=await initialize(ui,{createRenderer:gpu.createRenderer});lab.prepare();const before=lab.getState();gpu.setCreateFailure(true);
 assert.equal(await lab.show3D(),false);assert.equal(ui.get('3d').hidden,true);assert.match(ui.get('gpu-status').textContent,/GPU unavailable/);
 assert.deepEqual(lab.getState().source,before.source);assert.deepEqual(lab.getState().packet,before.packet);assert.deepEqual(lab.getState().derived,before.derived);assert.equal(ui.get('save-json').disabled,false);
 gpu.setCreateFailure(false);gpu.setDrawFailure(true);assert.equal(await lab.show3D(),false);assert.equal(gpu.instances[0].disposed,1);assert.equal(ui.get('3d').hidden,true);
 gpu.setDrawFailure(false);assert.equal(await lab.show3D(),true);const current=gpu.instances.at(-1);gpu.instances[0].onError('late old device');assert.equal(ui.get('3d').hidden,false);
 current.onError('device lost');assert.equal(ui.get('3d').hidden,true);assert.equal(current.disposed,1);assert.deepEqual(lab.getState().derived,before.derived);assert.equal(ui.get('save-portable').disabled,false);
 assert.equal(await lab.show3D(),true);lab.dispose();
});

test('binding async GPU initialization and validation cannot resurrect geometry after newer edits',async()=>{
 const ui=harness();let completeCreate,completeDraw;const make=()=>({clears:0,disposed:0,render(){this.clears++;},renderChecked:()=>new Promise(resolve=>{completeDraw=resolve;}),dispose(){this.disposed++;}}),own=make(),newer=make();
 let delayed=true;const lab=await initialize(ui,{createRenderer:()=>delayed?new Promise(resolve=>{completeCreate=resolve;}):Promise.resolve(newer)});lab.prepare();const pending=lab.show3D();assert.equal(ui.get('show-3d').disabled,true);ui.fire('time','input');completeCreate(own);assert.equal(await pending,false);assert.equal(own.disposed,1);assert.equal(ui.get('3d').hidden,true);
 delayed=false;lab.reset();lab.prepare();const drawing=lab.show3D();await Promise.resolve();assert.equal(typeof completeDraw,'function');ui.fire('input','input');completeDraw();assert.equal(await drawing,false);assert.equal(ui.get('3d').hidden,true);assert.equal(lab.getState().derived,null);assert.ok(newer.clears>0);lab.dispose();
});

test('binding UI explicitly prepares real C++ Float32 positions and normals without editing its source',async()=>{
 const ui=harness(),lab=await initialize(ui),before=serializeSkinBindingSource(lab.getState().source),pose=lab.getState().packet;
 assert.equal(lab.getState().derived,null);assert.equal(ui.get('prepare').disabled,false);
 const result=lab.prepare();assert.equal(result.status,'completed');assert.equal(result.geometry.interleaved.length,72);assert.equal(result.geometry.triangles.length,4);
 assert.deepEqual(Array.from(result.geometry.positions[1]),[Math.fround(1.1),Math.fround(-.1),0]);
 for(const audit of result.audits){assert.ok(audit.normal.every((x,i)=>x===[0,0,1][i]));assert.ok(audit.normalError.every(x=>x<=1e-6));}
 assert.equal(serializeSkinBindingSource(lab.getState().source),before);assert.deepEqual(lab.getState().packet,pose);
 const displayed=parseSkinBindingSource(ui.get('json').textContent);assert.equal(serializeSkinBindingSource(displayed),before);
 const state=lab.getState();state.derived.geometry.positions[0][0]=99;assert.equal(lab.getState().derived.geometry.positions[0][0],0);
 const preview=JSON.parse(ui.get('derived-result').textContent);assert.equal(preview.display.totalFaces,4);assert.equal(preview.result.geometry.interleaved.length,72);
});

test('binding UI clears prepared geometry on budget and source edits and retries an actual normal failure',async()=>{
 const ui=harness(),lab=await initialize(ui);assert.equal(lab.prepare().status,'completed');const pose=lab.getState().packet;
 ui.get('derived-budget').value='1';ui.fire('derived-budget','input');assert.equal(lab.getState().derived,null);assert.deepEqual(lab.getState().packet,pose);
 const failed=lab.prepare();assert.equal(failed.status,'quality_unresolved');assert.equal(failed.geometry,null);assert.equal(ui.get('save-json').disabled,false);
 ui.get('derived-budget').value='128';ui.fire('derived-budget','input');assert.equal(lab.prepare().status,'completed');
 ui.get('time').value='0';ui.fire('time','input');assert.equal(lab.getState().derived,null);assert.equal(ui.get('prepare').disabled,true);ui.fire('run');assert.equal(lab.prepare().status,'completed');
 ui.fire('input','input');assert.equal(lab.getState().derived,null);assert.equal(ui.get('prepare').disabled,true);assert.equal(ui.get('derived-result').textContent,'未実行');
});

test('binding UI sends actual equal-weight half-turn LBS collapse to the C++ derived model',async()=>{
 const ui=harness(),lab=await initialize(ui),source=fresh();source.influences=source.mesh.positions.map(()=>[{boneId:7,weight:1},{boneId:19,weight:1}]);
 source.motion.clip.tracks.find(t=>t.boneId===19).keys.find(k=>k.time===1).rotation=[0,0,1,0];
 const text=serializeSkinBindingSource(source);assert.equal(lab.readText(text),true);assert.equal(lab.getState().packet.deformation.status,'completed');
 assert.ok(lab.getState().packet.deformation.positions.every(p=>p[0]===1&&p[1]===0&&p[2]===0));
 const result=lab.prepare();assert.equal(result.status,'degenerate');assert.equal(result.geometry,null);assert.equal(serializeSkinBindingSource(lab.getState().source),text);assert.equal(ui.get('save-portable').disabled,false);
 ui.fire('default');assert.equal(lab.prepare().status,'completed');
});

test('binding UI never prepares before position success or substitutes for an unavailable derived API',async()=>{
 const ui=harness(),missing=Object.create(runtime);missing.prepareDerivedMesh=undefined;const lab=await initialize(ui,{loadRuntime:async()=>missing});
 assert.equal(lab.prepare(),null);assert.match(ui.get('derived-status').textContent,/対応/);assert.equal(lab.getState().packet.deformation.status,'completed');assert.equal(lab.getState().derived,null);
 const source=fresh();source.influences[1]=[{boneId:19,weight:Number.MAX_VALUE},{boneId:7,weight:Number.MIN_VALUE}];
 assert.equal(lab.readText(serializeSkinBindingSource(source)),true);assert.equal(lab.getState().packet.deformation.status,'numerical_failure');assert.equal(ui.get('prepare').disabled,true);assert.equal(lab.prepare(),null);assert.match(ui.get('derived-status').textContent,/先に位置計算/);assert.equal(ui.get('save-json').disabled,false);
});

test('binding authoring UI uses real C++ and displays the known strip without changing source fields',async()=>{
 const ui=harness(),lab=await initialize(ui),state=lab.getState();assert.deepEqual(state.source,fresh());assert.equal(state.packet.deformation.status,'completed');close(state.packet.deformation.positions[1][0],1.1);close(state.packet.deformation.positions[1][1],-.1);assert.equal(ui.get('rows').children.length,6);assert.equal(ui.get('save-json').disabled,false);assert.ok(ui.draws.some(r=>r[0]==='xz'&&r[1]==='fillText'&&r[2].startsWith('XZ')));state.source.name='mutated copy';assert.equal(lab.getState().source.name,'Original arm binding');
});
test('binding UI raw weight edit exports JSON and portable sources and rereads the whole original',async()=>{
 const ui=harness(),lab=await initialize(ui),before=lab.getState().source;ui.get('weight').value='3';assert.equal(ui.fire('edit'),true);const after=lab.getState().source;assert.equal(after.influences[1][0].weight,3);assert.deepEqual(after.motion,before.motion);assert.deepEqual(after.joints,before.joints);assert.deepEqual(after.influences[4],before.influences[4]);close(lab.getState().packet.deformation.positions[1][0],1.15);ui.fire('save-json');ui.fire('save-portable');assert.deepEqual(parseSkinBindingSource(ui.saves[0].text),after);assert.deepEqual(parseSkinBindingPortable(ui.saves[1].text),after);assert.equal(lab.readText(ui.saves[1].text),true);assert.deepEqual(lab.getState().source,after);
});
test('binding UI clears old geometry on text or clock edits and rejects duplicate and underflow JSON',async()=>{
 const ui=harness(),lab=await initialize(ui),valid=ui.get('input').value;ui.get('input').value=valid;ui.fire('input','input');assert.equal(lab.getState().packet,null);assert.equal(ui.get('save-json').disabled,true);assert.equal(ui.get('rows').children.length,0);
 for(const bad of ['{"version":1,"version":1}',valid.replace('"weight":1','"weight":1e-999')]){assert.equal(lab.readText(bad),false);assert.equal(lab.getState().packet,null);assert.equal(ui.get('save-portable').disabled,true);}
 assert.equal(lab.readText(valid),true);ui.get('time').value='0';ui.fire('time','input');assert.equal(lab.getState().packet,null);assert.equal(ui.get('save-json').disabled,false);ui.fire('run');assert.deepEqual(lab.getState().packet.deformation.positions,lab.getState().source.mesh.positions);
});
test('binding UI preserves underflowing author weights as editable source and recovers using C++',async()=>{
 const ui=harness(),lab=await initialize(ui),source=fresh();source.influences[1]=[{boneId:19,weight:Number.MAX_VALUE},{boneId:7,weight:Number.MIN_VALUE}];assert.equal(lab.readText(serializeSkinBindingSource(source)),true);assert.equal(lab.getState().packet.deformation.status,'numerical_failure');assert.equal(lab.getState().packet.deformation.positions,null);assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('save-json').disabled,false);ui.fire('save-json');assert.equal(parseSkinBindingSource(ui.saves[0].text).influences[1][1].weight,Number.MIN_VALUE);ui.get('bone').value='7';ui.get('weight').value='1';assert.equal(ui.fire('edit'),true);assert.equal(lab.getState().packet.deformation.status,'completed');assert.equal(ui.get('error').hidden,true);
});
test('binding UI stores finite stale rest-world data but never rebinds or draws it',async()=>{
 const ui=harness(),lab=await initialize(ui),source=fresh();source.joints[0].restWorld[12]+=1;assert.equal(lab.readText(serializeSkinBindingSource(source)),true);assert.equal(lab.getState().packet,null);assert.equal(ui.get('save-json').disabled,false);assert.match(ui.get('error').textContent,/rest/i);assert.equal(lab.getState().source.joints[0].restWorld[12],2);assert.equal(ui.fire('default'),true);assert.equal(lab.getState().packet.deformation.status,'completed');
});
test('binding UI requires an entered Scene to match before querying and keeps Scene input unchanged',async()=>{
 const ui=harness(),lab=await initialize(ui),source=fresh(),entity={...meshEntity('arm-mesh',source.mesh),nativeId:'42'},scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[entity]});ui.get('scene').value=scene.save();ui.fire('scene','input');assert.equal(lab.query(),null);assert.match(ui.get('error').textContent,/Scene/);assert.equal(ui.fire('match'),true);assert.equal(lab.getState().packet.sceneMatched,true);assert.equal(ui.get('scene').value,scene.save());const dirty=structuredClone(scene.data);dirty.entities[0].mesh.positions[0][0]=.01;ui.get('scene').value=JSON.stringify(dirty);ui.fire('scene','input');assert.equal(ui.fire('match'),false);assert.equal(lab.getState().packet,null);assert.equal(ui.get('rows').children.length,0);ui.fire('clear-scene');assert.ok(lab.query());assert.equal(lab.getState().packet.sceneMatched,false);
});
test('binding UI file reader accepts both codecs and rejects invalid UTF8 BOM and oversized metadata',async()=>{
 const ui=harness(),lab=await initialize(ui);for(const text of [serializeSkinBindingSource(fresh()),serializeSkinBindingPortable(fresh())]){ui.get('file').files=[file(text)];assert.equal(await ui.fire('file','change'),true);assert.equal(lab.getState().packet.deformation.status,'completed');}
 ui.get('file').files=[{size:2,arrayBuffer:async()=>new Uint8Array([0xc0,0xaf]).buffer}];assert.equal(await lab.readFile(),false);assert.equal(lab.getState().packet,null);
 ui.get('file').files=[file('\ufeff'+serializeSkinBindingSource(fresh()))];assert.equal(await lab.readFile(),false);assert.equal(ui.get('save-json').disabled,true);
 let read=false;ui.get('file').files=[{size:8388609,arrayBuffer:async()=>{read=true;return new ArrayBuffer(0);}}];assert.equal(await lab.readFile(),false);assert.equal(read,false);assert.equal(lab.reset(),true);
});
test('binding UI ignores an older asynchronous file read after a newer source was applied',async()=>{
 const ui=harness(),lab=await initialize(ui);let finish;const old=serializeSkinBindingSource(fresh());ui.get('file').files=[{size:old.length,arrayBuffer:()=>new Promise(resolve=>{finish=resolve;})}];const pending=lab.readFile();const newer=fresh();newer.influences[1][0].weight=3;assert.equal(lab.readText(serializeSkinBindingSource(newer)),true);finish(new TextEncoder().encode(old).buffer);assert.equal(await pending,false);assert.equal(lab.getState().source.influences[1][0].weight,3);assert.equal(lab.getState().packet.deformation.status,'completed');
});
test('binding UI can preserve source while runtime is offline and retries without JavaScript deformation',async()=>{
 const ui=harness();let offline=true;const lab=await initialize(ui,{loadRuntime:async()=>{if(offline)throw new Error('offline');return runtime;}});assert.equal(lab.getState().available,false);assert.equal(lab.readText(serializeSkinBindingSource(fresh())),true);assert.equal(lab.getState().packet,null);assert.equal(ui.get('save-json').disabled,false);assert.equal(ui.get('run').disabled,true);offline=false;await lab.retry();assert.equal(lab.getState().packet.deformation.status,'completed');
 const broken=Object.create(runtime);broken.deformSkin=()=>({status:'completed',positions:[[NaN,0,0]]});const invalid=await initialize(harness(),{loadRuntime:async()=>broken});assert.equal(invalid.getState().packet,null);
});
test('binding UI rejects decimal-underflow weight edits without changing the prior owned source',async()=>{
 const ui=harness(),lab=await initialize(ui),before=lab.getState().source;ui.get('weight').value='1e-999';assert.equal(ui.fire('edit'),false);assert.deepEqual(lab.getState().source,before);assert.equal(lab.getState().packet,null);assert.equal(ui.get('rows').children.length,0);assert.equal(ui.get('save-json').disabled,false);
});
test('binding page links and labels cover actual source codecs and explicit renderer limitations',async()=>{
 const all=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);assert.equal(all.length,new Set(all).size);for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));for(const text of ['2048','8192','8MiB','author weight','Native','fingerprint','全motion','法線','Float32','HTTP/HTTPS'])assert.ok(html.includes(text),text);const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.ok(build.includes("['tools/skin-binding-lab.html','../','skin-binding-lab.mjs']"));
});
