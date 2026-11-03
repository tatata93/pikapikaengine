import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {Scene} from '../engine/scene.mjs';
import {savePortableScene} from '../engine/portable-scene.mjs';
import {createDerivedMeshRenderData,copyDerivedMeshRenderVertices} from '../engine/derived-render.mjs';
import {createSkinBindingSource,parseSkinBindingSource,serializeSkinBindingSource,parseSkinBindingPortable,serializeSkinBindingPortable,validateSkinBindingContext,evaluateSkinBinding} from '../engine/skin-binding.mjs';
import {BACK_COVER_TARGET,BACK_COVER_ROOT,BACK_COVER_HINGE,createRobotBackCoverSource,createRobotBackCoverScene} from '../scripts/create-robot-back-cover.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url)),assetURL=new URL('../assets/robot-back-cover.skin.json',import.meta.url),sceneURL=new URL('../assets/robot-back-cover.scene.json',import.meta.url);
const json=await readFile(assetURL,'utf8'),sceneJSON=await readFile(sceneURL,'utf8'),source=parseSkinBindingSource(json),scene=Scene.load(sceneJSON);
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)),runtime=await loadSimulationRuntime({wasmBytes:wasm});
const near=(a,b)=>assert.ok(Math.abs(a-b)<=256*Number.EPSILON*Math.max(1,Math.abs(b)),`${a} != ${b}`);
const sha=x=>createHash('sha256').update(x).digest('hex');
const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
// Independent closed-form solution for this authored two-bone fixture only.
// Root palette is I; hinge palette Rx(theta); the middle row has exact weights
// 1/2,1/2. The symmetric NLERP midpoint has theta=pi/16. Not general JS skinning.
function expected(t){const theta=t*Math.PI/8,c=Math.cos(theta),s=Math.sin(theta);return [[-.75,.625,0],[.75,.625,0],[-.75,s/16,-(1+c)/16],[.75,s/16,-(1+c)/16],[-.75,-5*c/8,-5*s/8],[.75,-5*c/8,-5*s/8]];}
function verifyPositions(actual,t){const reference=expected(t);assert.equal(actual.length,6);for(let j=0;j<6;++j)for(let k=0;k<3;++k)near(actual[j][k],reference[j][k]);}

test('original robot cover keeps fixed asset IDs exact planned geometry and one-time actual C++ binding',()=>{
 assert.deepEqual(source.target,{objectId:'robot/player/back-cover',nativeId:'71000'});assert.deepEqual(source.target,BACK_COVER_TARGET);assert.equal(source.fingerprint,'00fbf40445c59a88');
 assert.deepEqual(source.mesh,{version:1,positions:[[-.75,.625,0],[.75,.625,0],[-.75,0,-.125],[.75,0,-.125],[-.75,-.625,0],[.75,-.625,0]],triangles:[[0,3,2],[0,1,3],[2,5,4],[2,3,5]]});
 assert.deepEqual(source.motion.bones.map(b=>[b.id,b.parentId,b.rest.position]),[[71001,0,[0,.625,0]],[71002,71001,[0,-.625,0]]]);assert.equal(source.motion.clip.duration,1);assert.equal(source.motion.clip.tracks[0].boneId,BACK_COVER_HINGE);assert.deepEqual(source.motion.clip.tracks[0].keys.map(k=>k.time),[0,1]);
 assert.deepEqual(source.influences,[[{boneId:71001,weight:1}],[{boneId:71001,weight:1}],[{boneId:71001,weight:1},{boneId:71002,weight:1}],[{boneId:71001,weight:1},{boneId:71002,weight:1}],[{boneId:71002,weight:1}],[{boneId:71002,weight:1}]]);
 const root=source.joints.find(j=>j.id===BACK_COVER_ROOT),hinge=source.joints.find(j=>j.id===BACK_COVER_HINGE);
 for(let k=0;k<16;++k){near(root.restWorld[k],k===13?.625:identity[k]);near(root.inverseBind[k],k===13?-.625:identity[k]);near(hinge.restWorld[k],identity[k]);near(hinge.inverseBind[k],identity[k]);}
 assert.deepEqual(createRobotBackCoverSource(runtime),source);assert.equal(serializeSkinBindingSource(source),json);assert.equal(createRobotBackCoverScene().save(),sceneJSON);
});
test('actual C++ FK and all vertex LBS agree with independent closed forms at rest midpoint and pi8',()=>{
 for(const t of [0,.5,1]){const state=evaluateSkinBinding(runtime,source,t,{scene});assert.equal(state.rest.status,'completed');assert.equal(state.pose.status,'completed');assert.equal(state.deformation.status,'completed');verifyPositions(state.deformation.positions,t);
  const c=Math.cos(t*Math.PI/8),s=Math.sin(t*Math.PI/8),rx=[1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1];
  for(const bone of state.pose.bones)for(let k=0;k<16;++k)near(bone.worldMatrix[k],bone.id===BACK_COVER_ROOT?(k===13?.625:identity[k]):rx[k]);
 }
 assert.equal(serializeSkinBindingSource(source),json);assert.equal(scene.save(),sceneJSON);
});
test('33 finite authored clip parameters pass local audits with four faces and owned 288 byte tokens',()=>{
 for(let j=0;j<=32;++j){const state=evaluateSkinBinding(runtime,source,j/32);assert.equal(state.deformation.status,'completed');const derived=runtime.prepareDerivedMesh({positions:state.deformation.positions,triangles:source.mesh.triangles});assert.equal(derived.status,'completed');assert.equal(derived.audits.length,4);assert.equal(derived.geometry.interleaved.length,72);assert.equal(derived.geometry.interleaved.byteLength,288);
  for(const audit of derived.audits){assert.ok(audit.squaredCross[0]>1e-24);assert.ok(audit.normalError.every(e=>e<=1e-6));assert.ok(audit.normal[2]<-.8,'Known back-facing fixture orientation');}
  const token=createDerivedMeshRenderData(derived),owned=copyDerivedMeshRenderVertices(token);assert.deepEqual(token,{vertexCount:6,triangleCount:4,floatCount:72});derived.geometry.interleaved.fill(99);assert.deepEqual(copyDerivedMeshRenderVertices(token),owned);
 }
 assert.equal(serializeSkinBindingSource(source),json);
});
test('JSON portable and separate authoring context preserve source; level identity is not inferred',()=>{
 assert.deepEqual(parseSkinBindingPortable(serializeSkinBindingPortable(source)),source);assert.deepEqual(parseSkinBindingSource(serializeSkinBindingSource(source)),source);assert.equal(validateSkinBindingContext(source,scene),true);
 const context=structuredClone(scene.data);context.entities[0].id='level-obstacle';assert.throws(()=>validateSkinBindingContext(source,context));context.entities[0].id=source.target.objectId;context.entities[0].mesh.positions[0][0]+=.01;assert.throws(()=>validateSkinBindingContext(source,context));
 const end=evaluateSkinBinding(runtime,source,1),clamped=evaluateSkinBinding(runtime,source,2);assert.deepEqual(clamped.deformation,end.deformation);assert.deepEqual(evaluateSkinBinding(runtime,source,1.5,{loop:true}).deformation,evaluateSkinBinding(runtime,source,.5).deformation);
});
test('bad authored fields and saved numeric failures are refused without source repair or successful tokens',()=>{
 for(const edit of [s=>s.fingerprint='0'.repeat(16),s=>s.target.nativeId='071000',s=>s.motion.bones[1].parentId=0,s=>s.mesh.triangles[0][1]=99,s=>s.influences[2]=[{boneId:71001,weight:0}],s=>s.motion.clip.tracks[0].keys[1].rotation=[0,0,0,0]]){const bad=structuredClone(source);edit(bad);assert.throws(()=>createSkinBindingSource(bad));}
 const bad=structuredClone(source);bad.joints[0].inverseBind[13]+=.01;createSkinBindingSource(bad);const original=serializeSkinBindingSource(bad),result=evaluateSkinBinding(runtime,bad,.5);assert.equal(result.deformation.status,'ill_conditioned');assert.equal(result.deformation.positions,null);assert.throws(()=>createDerivedMeshRenderData(result.deformation));assert.equal(serializeSkinBindingSource(bad),original);
 const tiny=structuredClone(source);tiny.influences[2]=[{boneId:71001,weight:Number.MIN_VALUE},{boneId:71002,weight:Number.MAX_VALUE}];const failed=evaluateSkinBinding(runtime,tiny,.5);assert.equal(failed.deformation.status,'numerical_failure');assert.equal(failed.deformation.positions,null);assert.equal(tiny.influences[2][0].weight,Number.MIN_VALUE);
 assert.equal(serializeSkinBindingSource(source),json);
});
const cli=process.env.PIKAPIKA_SKIN_CLI??path.join(ROOT,process.platform==='win32'?'build/native/Release/pikapika-skin.exe':'build/ci/pikapika-skin');
test('Native CLI roundtrip carries JSON authored source through portable and matches context plus all known poses',{skip:!existsSync(cli)},async()=>{
 await mkdir(path.join(ROOT,'build'),{recursive:true});const directory=await mkdtemp(path.join(ROOT,'build/robot-cover-source-test-')),input=path.join(directory,'source.skin'),output=path.join(directory,'roundtrip.skin'),context=path.join(directory,'context.scene');
 await writeFile(input,serializeSkinBindingPortable(source),{flag:'wx'});await writeFile(context,savePortableScene(scene),{flag:'wx'});
 const call=args=>{const result=spawnSync(cli,args,{encoding:'utf8',timeout:10000,maxBuffer:1024*1024});assert.equal(result.status,0,result.stderr);return result.stdout;};
 const info=JSON.parse(call(['inspect',input]));assert.equal(info.vertices,6);assert.equal(info.triangles,4);assert.equal(info.nativeId,'71000');call(['roundtrip',input,output]);assert.deepEqual(parseSkinBindingPortable(await readFile(output,'utf8')),source);assert.equal(JSON.parse(call(['match',output,context])).matches,true);
 for(const t of [0,.5,1]){const result=JSON.parse(call(['sample',output,String(t)]));assert.equal(result.status,'completed');verifyPositions(result.positions,t);}
 const before=await readFile(output),refused=spawnSync(cli,['roundtrip',input,output],{encoding:'utf8',timeout:10000});assert.notEqual(refused.status,0);assert.deepEqual(await readFile(output),before);
});
test('one-time generator refuses existing assets and SDK authoring bytes remain immutable',async()=>{
 const before=[await readFile(assetURL),await readFile(sceneURL),await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))].map(sha);
 const result=spawnSync(process.execPath,['scripts/create-robot-back-cover.mjs','--write'],{cwd:ROOT,encoding:'utf8',timeout:10000});assert.notEqual(result.status,0);assert.match(result.stderr,/existing authoring asset/);
 const after=[await readFile(assetURL),await readFile(sceneURL),await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))].map(sha);assert.deepEqual(after,before);assert.equal(after[2],sha(wasm));
});
