import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,writeFileSync,existsSync,rmSync} from 'node:fs';
import {readFile as readAsync} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve,dirname,basename} from 'node:path';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {validateMesh} from '../engine/mesh.mjs';
import {Scene,meshEntity,box} from '../engine/scene.mjs';
import {createMotionSource,setMotionKey,serializeMotionPortable,parseMotionPortable} from '../engine/motion.mjs';
import {savePortableScene,parsePortableScene} from '../engine/portable-scene.mjs';
import {parseStrictJson,stringifyStrictJson,utf8Length} from '../engine/strict-json.mjs';
import {meshFingerprint,createSkinBindingSource,parseSkinBindingSource,serializeSkinBindingSource,parseSkinBindingPortable,serializeSkinBindingPortable,setSkinInfluences,setSkinWeight,validateSkinBindingContext,evaluateSkinBinding,defaultSkinBindingSource} from '../engine/skin-binding.mjs';

const runtime=await loadSimulationRuntime({wasmBytes:await readAsync(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const fresh=()=>defaultSkinBindingSource(runtime),copy=x=>structuredClone(x);
const near=(a,b)=>assert.ok(Math.abs(a-b)<=256*Number.EPSILON*Math.max(1,Math.abs(b)),`${a} != ${b}`);
const identity=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
function bindMotion(source,motion){
 source.motion=createMotionSource(motion);source.restBones=source.motion.bones.map(({id,parentId,rest})=>({id,parentId,rest:copy(rest)}));
 const rest=runtime.sampleMotion({bones:source.motion.bones,clip:{...source.motion.clip,tracks:[]}},0);assert.equal(rest.status,'completed');
 const binding=runtime.bindSkin(rest.bones.map(b=>({id:b.id,matrix:b.worldMatrix})));assert.equal(binding.status,'completed');source.joints=binding.joints;return createSkinBindingSource(source);
}
function withExtraBone(){
 const source=fresh(),motion=copy(source.motion);motion.bones.push({id:99,name:'Hidden',parentId:7,rest:{position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}});
 motion.clip.tracks.push({boneId:99,interpolation:'step',keys:[{time:0,position:[0,0,0],rotation:[0,0,0,-2],scale:[1,1,1]},{time:1.5,position:[0,2,0],rotation:[0,0,0,-4],scale:[2,1,1]}]});return bindMotion(source,motion);
}
function sceneFor(source){return new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[{...meshEntity(source.target.objectId,source.mesh),nativeId:source.target.nativeId}]});}
const freeze=x=>{if(x&&typeof x==='object'){Object.freeze(x);for(const value of Object.values(x))freeze(value);}return x;};

test('owned default skin binding has known fingerprint and real C++ rest/bend positions',()=>{
 const source=fresh();assert.equal(source.fingerprint,'9da65482c00e78b0');assert.deepEqual(source.motion.bones.map(b=>b.id),[19,7]);assert.deepEqual(source.restBones.map(b=>b.id),[19,7]);assert.deepEqual(source.joints.map(b=>b.id),[19,7]);assert.equal(source.motion.name,'Original arm motion');
 const rest=evaluateSkinBinding(runtime,source,0);assert.equal(rest.deformation.status,'completed');assert.deepEqual(rest.deformation.positions,source.mesh.positions);
 const before=copy(source),bent=evaluateSkinBinding(runtime,source,1);assert.equal(bent.deformation.status,'completed');const expected=[[0,-.2,0],[1.1,-.1,0],[1.2,1,0],[0,.2,0],[.9,.1,0],[.8,1,0]];bent.deformation.positions.forEach((p,j)=>p.forEach((v,k)=>near(v,expected[j][k])));assert.deepEqual(source,before);
 assert.equal(evaluateSkinBinding(runtime,source,3).pose.sampledTime,2);assert.deepEqual(evaluateSkinBinding(runtime,source,2.5,{loop:true}).deformation,evaluateSkinBinding(runtime,source,.5).deformation);assert.throws(()=>evaluateSkinBinding(runtime,source,1,{loop:1}),/loop boolean/);
 const saved=copy(bent);evaluateSkinBinding(runtime,source,.3);assert.deepEqual(bent,saved);assert.throws(()=>defaultSkinBindingSource({}),/runtime unavailable/);
});

test('owned source strict schema rejects wrong fields sparse arrays stale rest and unsafe domains',()=>{
 const edits=[s=>s.extra=1,s=>delete s.space,s=>s.target.extra=1,s=>s.mesh.extra=1,s=>s.influences[0][0].extra=1,s=>s.joints[0].extra=1,s=>s.restBones[0].extra=1,s=>s.restBones[0].rest.extra=1,s=>s.version=2,s=>s.units='cm',s=>s.space='world',s=>s.fingerprint='0'.repeat(16),s=>s.fingerprint=s.fingerprint.toUpperCase(),s=>s.target.nativeId='042',s=>s.target.nativeId=42,s=>s.target.nativeId='9007199254740992',s=>s.target.objectId='',s=>s.target.objectId='x'.repeat(97),s=>s.joints[0].id=0,s=>s.joints[0].id=2**53,s=>s.joints.push(copy(s.joints[0])),s=>s.joints.pop(),s=>s.restBones.pop(),s=>s.restBones[0].parentId=0,s=>s.restBones[0].rest.position[0]=2,s=>s.influences.pop(),s=>s.influences[0]=[],s=>s.influences[0]=[{boneId:7,weight:0}],s=>s.influences[0]=[{boneId:7,weight:-1}],s=>s.influences[0]=[{boneId:99,weight:0},{boneId:7,weight:1}],s=>s.influences[0]=[{boneId:7,weight:0},{boneId:7,weight:1}],s=>s.influences[0]=Array(1),s=>s.influences=Array(6),s=>s.mesh.positions=Array(6),s=>s.joints=Array(2),s=>s.restBones=Array(2),s=>s.joints[0].inverseBind[3]=1e-30,s=>s.joints[0].inverseBind[0]=1e151,s=>s.joints[0].restWorld[0]=Infinity];
 for(const [j,edit] of edits.entries()){const source=fresh();edit(source);assert.throws(()=>createSkinBindingSource(source),'schema mutation '+j);}
 const source=fresh();let called=false;Object.defineProperty(source,'name',{enumerable:true,get(){called=true;return 'getter';}});assert.throws(()=>createSkinBindingSource(source),/accessor/);assert.equal(called,false);
});

test('source JSON and portable retain all authored signed zeros subnormal weights and hidden motion',()=>{
 const source=withExtraBone();source.name='原本 "quotes" \\ path';source.motion.name='日本語 motion end_skin';source.mesh.positions[0][0]=-0;source.influences[1][0].weight=-0;source.influences[1][1].weight=Number.MIN_VALUE;source.joints[0].restWorld[2]=-0;source.joints[0].inverseBind[2]=-0;
 const before=copy(source),json=serializeSkinBindingSource(source),portable=serializeSkinBindingPortable(source);
 assert.match(json,/-0/);assert.equal(json.includes('\n'),false,'JSON is compact');assert.deepEqual(parseSkinBindingSource(json),source);assert.deepEqual(parseSkinBindingPortable(portable),source);assert.deepEqual(source,before);
 const encoded=Number(/\nmotion_bytes (\d+)\n/.exec(portable)[1]),motion=serializeMotionPortable(source.motion);assert.equal(encoded,utf8Length(motion));assert.ok(encoded>motion.length);assert.equal(parseSkinBindingPortable(portable).motion.clip.tracks[1].keys[1].rotation[3],-4);
 assert.equal(meshFingerprint(source.mesh),fresh().fingerprint,'only hash zero is canonical; authored zero is retained');
 const integerZeros=fresh();integerZeros.mesh.triangles[0][0]=-0;integerZeros.restBones.find(b=>b.id===7).parentId=-0;const canonical=createSkinBindingSource(integerZeros);assert.equal(Object.is(canonical.mesh.triangles[0][0],-0),false);assert.equal(Object.is(canonical.restBones.find(b=>b.id===7).parentId,-0),false);assert.equal(Object.is(integerZeros.mesh.triangles[0][0],-0),true);assert.equal(Object.is(integerZeros.restBones.find(b=>b.id===7).parentId,-0),true);
});

test('immutable weight and influence edits preserve every unrelated source field and failed candidates',()=>{
 const source=freeze(withExtraBone()),before=copy(source),edited=setSkinWeight(source,1,19,3);assert.equal(edited.influences[1][0].weight,3);assert.deepEqual(source,before);assert.deepEqual(edited.joints,source.joints);assert.deepEqual(edited.motion,source.motion);assert.deepEqual(edited.mesh,source.mesh);assert.deepEqual(edited.influences.filter((_,j)=>j!==1),source.influences.filter((_,j)=>j!==1));
 const raw=[{boneId:7,weight:1},{boneId:19,weight:-0}],replaced=setSkinInfluences(source,1,raw);assert.equal(Object.is(replaced.influences[1][1].weight,-0),true);raw[0].weight=9;assert.equal(replaced.influences[1][0].weight,1);
 for(const args of [[-1,7,1],[6,7,1],[1,99,1],[1,19,-1]])assert.throws(()=>setSkinWeight(source,...args));assert.throws(()=>setSkinInfluences(source,0,[{boneId:7,weight:0}]));assert.throws(()=>setSkinInfluences(source,0,Array.from({length:5},()=>({boneId:7,weight:1}))));assert.deepEqual(source,before);
});

test('local rest snapshot detects same-world reparenting while names order and keys remain editable',()=>{
 const source=withExtraBone(),changed=copy(source);changed.motion.bones.find(b=>b.id===19).parentId=99;
 const a=runtime.sampleMotion({bones:source.motion.bones,clip:{duration:2,tracks:[]}},0),b=runtime.sampleMotion({bones:changed.motion.bones,clip:{duration:2,tracks:[]}},0);assert.deepEqual(a.bones.find(b=>b.id===19).worldMatrix,b.bones.find(b=>b.id===19).worldMatrix);assert.throws(()=>createSkinBindingSource(changed),/Stale local rest/);
 const keys=copy(source);keys.motion=setMotionKey(keys.motion,{boneId:19,time:.5,position:[1,0,0],rotation:[0,0,-1,1],scale:[1,1,1]});keys.motion.bones.reverse();keys.motion.bones[0].name='Renamed';const result=createSkinBindingSource(keys);assert.deepEqual(result.joints,source.joints);assert.deepEqual(result.restBones,source.restBones);assert.equal(evaluateSkinBinding(runtime,result,.5).deformation.status,'completed');assert.deepEqual(parseSkinBindingPortable(serializeSkinBindingPortable(result)),result);
});

test('structurally saved bad inverse or tiny author weight is never silently repaired into successful positions',()=>{
 const source=fresh();source.joints[0].inverseBind[12]+=.001;assert.deepEqual(parseSkinBindingSource(serializeSkinBindingSource(source)),source);const bad=evaluateSkinBinding(runtime,source,1);assert.equal(bad.deformation.status,'ill_conditioned');assert.equal(bad.deformation.positions,null);assert.equal(source.joints[0].inverseBind[12],-.999);
 const under=fresh();under.influences[1]=[{boneId:7,weight:Number.MIN_VALUE},{boneId:19,weight:Number.MAX_VALUE}];const saved=parseSkinBindingPortable(serializeSkinBindingPortable(under)),r=evaluateSkinBinding(runtime,saved,1);assert.equal(r.deformation.status,'numerical_failure');assert.equal(r.deformation.positions,null);assert.equal(saved.influences[1][0].weight,Number.MIN_VALUE);
 const stale=fresh();stale.joints[0].restWorld[12]+=.25;createSkinBindingSource(stale);assert.throws(()=>evaluateSkinBinding(runtime,stale,1),/Stale C\+\+ rest/);assert.throws(()=>evaluateSkinBinding(runtime,fresh(),-1),/current pose failed/);assert.throws(()=>evaluateSkinBinding({},fresh(),1),/runtime unavailable/);
 const overflow=fresh();overflow.motion={version:1,kind:'skeletal-motion',name:'Editable rest overflow',bones:Array.from({length:54},(_,j)=>({id:j+1,name:'Chain '+j,parentId:j,rest:{position:[1,0,0],rotation:[0,0,0,1],scale:[1e6,1e6,1e6]}})),clip:{name:'Static',duration:2,tracks:[]}};overflow.restBones=overflow.motion.bones.map(({id,parentId,rest})=>({id,parentId,rest:copy(rest)}));overflow.joints=overflow.motion.bones.map(b=>({id:b.id,restWorld:identity(),inverseBind:identity()}));overflow.influences=overflow.mesh.positions.map(()=>[{boneId:1,weight:1}]);assert.deepEqual(parseSkinBindingSource(serializeSkinBindingSource(overflow)),overflow);assert.throws(()=>evaluateSkinBinding(runtime,overflow,0),/rest FK failed: numerical_failure/);
});

test('context checks browser/native IDs and full ordered geometry without mutating or binding object transforms',()=>{
 const source=fresh(),scene=sceneFor(source),before=scene.save();assert.equal(validateSkinBindingContext(source,scene),true);assert.equal(scene.save(),before);
 scene.edit(source.target.objectId,{position:[10,20,30],yaw:1,scale:[2,3,4],color:[1,0,0]});assert.equal(validateSkinBindingContext(source,scene),true);assert.deepEqual(evaluateSkinBinding(runtime,source,1,{scene}).deformation.positions,evaluateSkinBinding(runtime,source,1).deformation.positions);
 for(const edit of [s=>s.entities[0].id='other',s=>s.entities[0].nativeId='43',s=>s.entities[0].mesh.positions[0][0]=.01,s=>s.entities[0].mesh.triangles.reverse()]){const data=copy(scene.data);edit(data);assert.throws(()=>validateSkinBindingContext(source,data));}
 const legacy=new Scene();legacy.add(box('arm-mesh',[0,0,0],[1,1,1]));const old=legacy.save();assert.throws(()=>validateSkinBindingContext(source,legacy));assert.equal(legacy.save(),old);assert.equal(legacy.data.version,1);
 const zero=copy(scene.data);zero.entities[0].mesh.positions[0][0]=-0;assert.equal(validateSkinBindingContext(source,zero),true);
 const collision=copy(scene.data);collision.entities.push({...meshEntity('second',source.mesh),nativeId:'42'});assert.throws(()=>validateSkinBindingContext(source,collision),/collision/i);
});

test('simulated constant fingerprint still rejects changed full geometry in the production validator',()=>{
 // This simulates a hash collision only; it does not claim a real FNV collision.
 // No numerical C++ operation is substituted. No public bypass hook exists.
 let code=readFileSync(new URL('../engine/skin-binding.mjs',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,'');code=code.replace('function meshFingerprint(input)','function unusedRealFingerprint(input)');code+='\nglobalThis.matchSource=validateSkinBindingContext;';
 const sandbox={validateMesh,createMotionSource,serializeMotionPortable,parseMotionPortable,savePortableScene,parsePortableScene,parseStrictJson,utf8Length,stringifyStrictJson:(value,options)=>stringifyStrictJson(copy(value),options),meshFingerprint:()=> '0000000000000000',TextEncoder,TextDecoder,ArrayBuffer,DataView,Uint8Array};
 vm.runInNewContext(code,sandbox,{timeout:1000});const source=fresh();source.fingerprint='0000000000000000';const scene=sceneFor(source);assert.equal(sandbox.matchSource(source,scene),true);const dirty=copy(scene.data);dirty.entities[0].mesh.positions[0][0]=.01;assert.throws(()=>sandbox.matchSource(source,dirty),/full geometry\/order/);
});

test('strict JSON rejects duplicate decoded keys nonfinite underflow invalid Unicode and oversized documents',()=>{
 const json=serializeSkinBindingSource(fresh());for(const text of [json.replace('"version":1','"version":1,"version":1'),json.replace('"version":1','"version":1,"\\u0076ersion":1'),json.replace('"weight":1','"weight":1e999'),json.replace('"weight":1','"weight":1e-999'),json.replace('"weight":1','"weight":NaN'),json.replace('"Original arm binding"','"\\ud800"'),json+'{}'])assert.throws(()=>parseSkinBindingSource(text));
 assert.throws(()=>parseSkinBindingSource(' '.repeat(8*1024*1024+1)),/budget/);assert.throws(()=>parseSkinBindingPortable('é'.repeat(4*1024*1024+1)),/8 MiB/);
 const edge=fresh();edge.name='é'.repeat(128);assert.equal(parseSkinBindingSource(serializeSkinBindingSource(edge)).name,edge.name);edge.name+='a';assert.throws(()=>createSkinBindingSource(edge),/256 bytes/);edge.name='valid';edge.target.objectId='あ'.repeat(96);assert.equal(createSkinBindingSource(edge).target.objectId.length,96);edge.target.objectId='😀'.repeat(49);assert.throws(()=>createSkinBindingSource(edge),/length/);
});

test('portable framing rejects wrong counts lengths escapes extra rows underflow and trailing whitespace',()=>{
 const source=fresh(),text=serializeSkinBindingPortable(source),n=Number(/motion_bytes (\d+)/.exec(text)[1]);
 const invalid=[text.replace('mesh 6 4','mesh 2049 4'),text.replace('mesh 6 4','mesh 6 131073'),text.replace('influences 6','influences 5'),text.replace('weights 1 7 1','weights 0'),text.replace('weights 1 7 1','weights 1 7 1e-999'),text.replace('weights 1 7 1','weights 1 7 0x1'),text.replace('object "arm-mesh" "42"','object "arm-mesh""42"'),text.replace('"Original arm binding"','"\\u0041"'),text.replace('motion_bytes '+n,'motion_bytes '+(n-1)),text.replace('motion_bytes '+n,'motion_bytes '+(n+1)),text.replace('motion_bytes '+n,'motion_bytes 4194305'),text.replace('end_skin\n','end_skin\n\n'),text+' ',text+'unknown\n',text.slice(0,-12),text.replace('name "Original arm binding"','name "'+ 'x'.repeat(4097)+'"')];
 for(const [j,bad] of invalid.entries())assert.throws(()=>parseSkinBindingPortable(bad),'portable mutation '+j);
 assert.deepEqual(parseSkinBindingPortable(text.replace('pikapika_skin 1','pikapika_skin 1.0')),source);assert.deepEqual(parseSkinBindingPortable(text.slice(0,-1)),source);
});

test('owned subset accepts simultaneous source limits and preserves the existing triangle-count ceiling',()=>{
 let source=withExtraBone(),motion=copy(source.motion);motion.bones.push({id:101,name:'Fourth',parentId:7,rest:{position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}});for(let j=0;j<124;++j)motion.bones.push({id:1000+j,name:'Retained '+j,parentId:7,rest:{position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}});source=bindMotion(source,motion);assert.equal(source.joints.length,128);
 source.mesh.positions=Array.from({length:2048},(_,j)=>copy(source.mesh.positions[j%6]));source.influences=source.mesh.positions.map(()=>[7,19,99,101].map(boneId=>({boneId,weight:1})));source.fingerprint=meshFingerprint(source.mesh);const valid=createSkinBindingSource(source);assert.equal(valid.influences.flat().length,8192);assert.equal(evaluateSkinBinding(runtime,valid,0).deformation.positions.length,2048);
 const tooMany=copy(valid);tooMany.mesh.positions.push([0,0,0]);tooMany.influences.push([{boneId:7,weight:1}]);assert.throws(()=>createSkinBindingSource(tooMany),/2048/);
 const extraBone=copy(valid);extraBone.motion.bones.push({id:9999,name:'One over',parentId:7,rest:copy(extraBone.motion.bones[0].rest)});assert.throws(()=>createSkinBindingSource(extraBone),/128 bones/);
 const triangles=fresh();triangles.mesh.triangles=Array.from({length:131072},()=>[0,1,4]);triangles.fingerprint=meshFingerprint(triangles.mesh);assert.equal(createSkinBindingSource(triangles).mesh.triangles.length,131072);triangles.mesh.triangles.push([0,1,4]);assert.throws(()=>createSkinBindingSource(triangles),/triangle count/);
});

const cli=process.env.PIKAPIKA_SKIN_CLI??resolve(process.platform==='win32'?'build/native/Release/pikapika-skin.exe':'build/ci/pikapika-skin');
function tempTask(fn){const directory=mkdtempSync(join(tmpdir(),'pikapika-skin-source-'));try{return fn(directory);}finally{const target=resolve(directory),root=resolve(tmpdir());assert.equal(dirname(target),root);assert.ok(basename(target).startsWith('pikapika-skin-source-'));rmSync(target,{recursive:true,force:true});}}
function command(args,ok=true){assert.ok(existsSync(cli),'Native skin CLI must be built: '+cli);const r=spawnSync(cli,args,{encoding:'utf8',windowsHide:true,timeout:15000,maxBuffer:4*1024*1024});if(ok)assert.equal(r.status,0,(r.stderr??'')+(r.error?.message??''));else assert.notEqual(r.status,0,'expected Native failure');return r;}

test('Native CLI init to Web JSON to portable Native roundtrip preserves every owned field and known FK',()=>tempTask(dir=>{
 const original=join(dir,'init.skin'),fromWeb=join(dir,'web.skin'),round=join(dir,'round.skin');command(['init',original]);const native=parseSkinBindingPortable(readFileSync(original,'utf8'));assert.deepEqual(native,fresh());const web=parseSkinBindingSource(serializeSkinBindingSource(native));writeFileSync(fromWeb,serializeSkinBindingPortable(web));command(['roundtrip',fromWeb,round]);const restored=parseSkinBindingPortable(readFileSync(round,'utf8'));assert.deepEqual(restored,web);
 const sample=JSON.parse(command(['sample',round,'1']).stdout);assert.equal(sample.status,'completed');assert.ok(Array.isArray(sample.positions));sample.positions.forEach((p,j)=>p.forEach((v,k)=>near(v,evaluateSkinBinding(runtime,restored,1).deformation.positions[j][k])));
}));

test('Native CLI weight and scene match retain source context while invalid operations preserve named files',()=>tempTask(dir=>{
 const input=join(dir,'input.skin'),output=join(dir,'edited.skin'),sceneFile=join(dir,'mesh.scene'),source=withExtraBone();source.name='日本語 "quoted" \\ original';source.influences[1][0].weight=Number.MIN_VALUE;source.influences[1][1].weight=-0;source.joints[0].inverseBind[2]=-0;writeFileSync(input,serializeSkinBindingPortable(source));const inputBytes=readFileSync(input);command(['weight',input,output,'1','19','3']);const edited=parseSkinBindingPortable(readFileSync(output,'utf8'));assert.equal(edited.influences[1][0].weight,3);assert.deepEqual(edited.motion,source.motion);assert.deepEqual(edited.joints,source.joints);assert.deepEqual(readFileSync(input),inputBytes);
 const scene=sceneFor(source);writeFileSync(sceneFile,savePortableScene(scene));const sceneBytes=readFileSync(sceneFile);command(['match',output,sceneFile]);assert.deepEqual(readFileSync(sceneFile),sceneBytes);
 const existing=join(dir,'must-stay.skin');writeFileSync(existing,'named output sentinel\n');const sentinel=readFileSync(existing);for(const args of [['roundtrip',input,existing],['roundtrip',input,input],['weight',input,existing,'1','999','1'],['weight',input,existing,'1','19','-1'],['weight',input,existing,'1','19','1e-999']])command(args,false);assert.deepEqual(readFileSync(existing),sentinel);assert.deepEqual(readFileSync(input),inputBytes);
 const dirty=copy(scene.data);dirty.entities[0].mesh.positions[0][0]=.01;writeFileSync(sceneFile,savePortableScene(dirty));command(['match',output,sceneFile],false);
}));

test('portable BOM and non-ASCII motion separators match Native rejection while quoted names retain Unicode whitespace',()=>tempTask(dir=>{
 const source=fresh(),text=serializeSkinBindingPortable(source),motion=serializeMotionPortable(source.motion);
 const embedded=next=>text.replace('motion_bytes '+utf8Length(motion)+'\n'+motion,'motion_bytes '+utf8Length(next)+'\n'+next);
 const invalid=['\ufeff'+text,text.replace('\nname ','\n\ufeffname '),text.replace('\nend_skin','\n\ufeffend_skin'),embedded('\ufeff'+motion),...['\u00a0','\u2028','\ufeff'].map(w=>embedded(motion.replace('pikapika_motion 1','pikapika_motion'+w+'1')))];
 for(const [j,bad]of invalid.entries()){
  assert.notEqual(bad,text);assert.throws(()=>parseSkinBindingPortable(bad),'BOM/Unicode separator '+j);
  const input=join(dir,'bad-'+j+'.skin'),output=join(dir,'rejected-'+j+'.skin');writeFileSync(input,bad);assert.equal(existsSync(output),false);command(['roundtrip',input,output],false);assert.equal(existsSync(output),false,'rejected syntax creates no output');
 }
 const name='名前 \u00a0\u2028\ufeff "quoted" \\ slash';source.name=name;source.motion.name=name;source.motion.clip.name=name;source.motion.bones[0].name=name;
 const portable=serializeSkinBindingPortable(source);assert.deepEqual(parseSkinBindingPortable(portable),source);
 const input=join(dir,'name.skin'),output=join(dir,'name-round.skin');writeFileSync(input,portable);command(['roundtrip',input,output]);assert.deepEqual(parseSkinBindingPortable(readFileSync(output,'utf8')),source);
}));
