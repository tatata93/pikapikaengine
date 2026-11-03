import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp,access} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createMotionSource} from '../engine/motion.mjs';
import {Scene,meshEntity} from '../engine/scene.mjs';
import {savePortableScene} from '../engine/portable-scene.mjs';
import {createDerivedMeshRenderData} from '../engine/derived-render.mjs';
import {createSkinBindingSource,meshFingerprint,parseSkinBindingSource,serializeSkinBindingSource,parseSkinBindingPortable,serializeSkinBindingPortable,validateSkinBindingContext,evaluateSkinBinding} from '../engine/skin-binding.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
export const BACK_COVER_TARGET=Object.freeze({objectId:'robot/player/back-cover',nativeId:'71000'});
export const BACK_COVER_ROOT=71001,BACK_COVER_HINGE=71002;
export function originalBackCoverMesh(){return {version:1,positions:[[-.75,.625,0],[.75,.625,0],[-.75,0,-.125],[.75,0,-.125],[-.75,-.625,0],[.75,-.625,0]],triangles:[[0,3,2],[0,1,3],[2,5,4],[2,3,5]]};}
export function createRobotBackCoverSource(runtime){
 const rest=position=>({position,rotation:[0,0,0,1],scale:[1,1,1]}),hinge=rest([0,-.625,0]);
 // Original authored X+pi/8 endpoint. It is stored in the source as binary64
 // quaternion components; no game-time sin/cos or bind regeneration is needed.
 const opening=[Math.sin(Math.PI/16),0,0,Math.cos(Math.PI/16)];
 const motion=createMotionSource({version:1,kind:'skeletal-motion',name:'Robot back cover hinge motion',bones:[{id:BACK_COVER_ROOT,name:'Upper mount',parentId:0,rest:rest([0,.625,0])},{id:BACK_COVER_HINGE,name:'Lower hinge',parentId:BACK_COVER_ROOT,rest:hinge}],clip:{name:'Open around +X by pi/8',duration:1,tracks:[{boneId:BACK_COVER_HINGE,interpolation:'linear',keys:[{time:0,...hinge},{time:1,...hinge,rotation:opening}]}]}});
 const pose=runtime.sampleMotion({bones:motion.bones,clip:{...motion.clip,tracks:[]}},0);assert.equal(pose.status,'completed');
 const bind=runtime.bindSkin(pose.bones.map(b=>({id:b.id,matrix:b.worldMatrix})));assert.equal(bind.status,'completed');
 const mesh=originalBackCoverMesh();
 return createSkinBindingSource({version:1,kind:'mesh-skin-binding',name:'Original robot back hinge cover',units:'m-s-kg',axes:'right-handed-y-up',space:'mesh-local-is-skeleton',target:{...BACK_COVER_TARGET},fingerprint:meshFingerprint(mesh),mesh,influences:mesh.positions.map((_,j)=>j<2?[{boneId:BACK_COVER_ROOT,weight:1}]:j<4?[{boneId:BACK_COVER_ROOT,weight:1},{boneId:BACK_COVER_HINGE,weight:1}]:[{boneId:BACK_COVER_HINGE,weight:1}]),joints:bind.joints,restBones:motion.bones.map(({id,parentId,rest})=>({id,parentId,rest})),motion});
}
export function createRobotBackCoverScene(){
 // Independently saved authoring context, from this same original recipe. It is
 // not a level collider and not an independent external asset provenance proof.
 return new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[{...meshEntity(BACK_COVER_TARGET.objectId,originalBackCoverMesh(),[0,0,0],[1,1,1],[.22,.48,.62]),nativeId:BACK_COVER_TARGET.nativeId}]});
}
const sha=value=>createHash('sha256').update(value).digest('hex');
const near=(a,b)=>assert.ok(Math.abs(a-b)<=256*Number.EPSILON*Math.max(1,Math.abs(b)),`${a} != ${b}`);
function analytic(seconds){const theta=seconds*Math.PI/8,c=Math.cos(theta),s=Math.sin(theta);return [[-.75,.625,0],[.75,.625,0],[-.75,.0625*s,-.0625*(1+c)],[.75,.0625*s,-.0625*(1+c)],[-.75,-.625*c,-.625*s],[.75,-.625*c,-.625*s]];}
function statistics(values){const s=[...values].sort((a,b)=>a-b);return {samples:s.length,medianMs:s[Math.floor(s.length/2)],p95Ms:s[Math.ceil(.95*s.length)-1],maxMs:s.at(-1)};}
async function run(mode){
 assert.ok(mode==='--write'||mode==='--verify','Use --write once, or --verify without overwriting assets');
 const sdkPaths=['assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json'];
 const hashes=async()=>Object.fromEntries(await Promise.all(sdkPaths.map(async name=>{const data=await readFile(path.join(ROOT,name));return [name,{bytes:data.length,sha256:sha(data)}];})));
 const sdkBefore=await hashes(),begin=performance.now(),runtime=await loadSimulationRuntime({wasmBytes:await readFile(path.join(ROOT,sdkPaths[1]))}),startupMs=performance.now()-begin;
 const source=createRobotBackCoverSource(runtime),scene=createRobotBackCoverScene(),json=serializeSkinBindingSource(source),sceneJSON=scene.save();validateSkinBindingContext(source,scene);
 const asset=path.join(ROOT,'assets/robot-back-cover.skin.json'),context=path.join(ROOT,'assets/robot-back-cover.scene.json');
 if(mode==='--write'){
  for(const filename of [asset,context]){let exists=true;try{await access(filename);}catch{exists=false;}assert.equal(exists,false,'Generator refuses an existing authoring asset');}
  await writeFile(asset,json,{flag:'wx'});await writeFile(context,sceneJSON,{flag:'wx'});
 }else{assert.deepEqual(parseSkinBindingSource(await readFile(asset,'utf8')),source);assert.deepEqual(Scene.load(await readFile(context,'utf8')).data,scene.data);}
 await mkdir(path.join(ROOT,'build'),{recursive:true});const directory=await mkdtemp(path.join(ROOT,'build/robot-cover-source-'));
 const save=async(name,value)=>writeFile(path.join(directory,name),typeof value==='string'?value:JSON.stringify(value,null,2)+'\n',{flag:'wx'});
 const raw=[],known=[],phases=['initial','warmup','measure','measure','measure'];
 // Five observations at each reference time; all stages are wall observations
 // of the real SDK and ownership factory, with no overhead subtraction.
 for(const seconds of [0,.5,1])for(let sample=0;sample<5;++sample){
  const pipelineBegin=performance.now();let t=pipelineBegin;const state=evaluateSkinBinding(runtime,source,seconds),sourceMs=performance.now()-t;assert.equal(state.deformation.status,'completed');
  t=performance.now();const derived=runtime.prepareDerivedMesh({positions:state.deformation.positions,triangles:source.mesh.triangles},{readback:'single'}),derivedMs=performance.now()-t;assert.equal(derived.status,'completed');
  t=performance.now();const token=createDerivedMeshRenderData(derived),tokenMs=performance.now()-t,pipelineMs=performance.now()-pipelineBegin;assert.deepEqual(token,{vertexCount:6,triangleCount:4,floatCount:72});assert.equal(derived.geometry.interleaved.byteLength,288);
  for(let j=0;j<6;++j)for(let axis=0;axis<3;++axis)near(state.deformation.positions[j][axis],analytic(seconds)[j][axis]);
  assert.equal(serializeSkinBindingSource(source),json);assert.equal(scene.save(),sceneJSON);
  raw.push({seconds,sample,phase:phases[sample],sourceMs,derivedMs,tokenMs,totalMs:sourceMs+derivedMs+tokenMs,pipelineMs});
  if(sample===0)known.push({seconds,state,derived,tokenMetadata:{...token}});
 }
 // Finite-range quality acceptance, not a proof of every real clip parameter.
 for(let j=0;j<=32;++j){const state=evaluateSkinBinding(runtime,source,j/32);assert.equal(state.deformation.status,'completed');const d=runtime.prepareDerivedMesh({positions:state.deformation.positions,triangles:source.mesh.triangles});assert.equal(d.status,'completed',`Unchanged authored angle failed at ${j}/32`);assert.equal(d.geometry.interleaved.length,72);}
 const skinPath=path.join(directory,'source.skin'),roundPath=path.join(directory,'native-roundtrip.skin'),scenePath=path.join(directory,'context.scene');await save('source.skin',serializeSkinBindingPortable(source));await save('context.scene',savePortableScene(scene));
 const cli=process.env.PIKAPIKA_SKIN_CLI??path.join(ROOT,process.platform==='win32'?'build/native/Release/pikapika-skin.exe':'build/ci/pikapika-skin'),commands=[];
 function native(args){const value=spawnSync(cli,args,{cwd:ROOT,encoding:'utf8',timeout:10000,maxBuffer:1024*1024});commands.push({command:[cli,...args],exitCode:value.status,error:value.error?.message??null,stdout:value.stdout,stderr:value.stderr});assert.equal(value.status,0,value.stderr??value.error?.message);return value.stdout;}
 native(['inspect',skinPath]);native(['roundtrip',skinPath,roundPath]);native(['match',skinPath,scenePath]);assert.deepEqual(parseSkinBindingPortable(await readFile(roundPath,'utf8')),source);
 for(const seconds of [0,.5,1]){const result=JSON.parse(native(['sample',roundPath,String(seconds)]));assert.equal(result.status,'completed');for(let j=0;j<6;++j)for(let axis=0;axis<3;++axis)near(result.positions[j][axis],analytic(seconds)[j][axis]);}
 assert.equal(await readFile(asset,'utf8'),json);assert.equal(await readFile(context,'utf8'),sceneJSON);assert.equal(serializeSkinBindingSource(source),json);const sdkAfter=await hashes();assert.deepEqual(sdkAfter,sdkBefore);
 const stats=[];for(const seconds of [0,.5,1])for(const stage of ['sourceMs','derivedMs','tokenMs','totalMs','pipelineMs'])stats.push({seconds,stage,...statistics(raw.filter(r=>r.seconds===seconds&&r.phase==='measure').map(r=>r[stage]))});
 await save('measurements.json',{schema:1,raw,statistics:stats,scope:'Node small six-vertex asset only, first/warmup/three measures per pose; Source includes full validation/rest/current FK/LBS, derived is single readback, token includes validation/copy. totalMs sums that trial\'s three observed call durations; pipelineMs is the enclosing wall interval including intervening status checks/clock overhead. These are uncalibrated. No renderer/GPU or general performance claim.'});
 await save('known-results.json',{schema:1,known,finiteClipSamples:33,analyticTolerance:'256*epsilon*max(1,abs(reference)); explicit point comparison to analytic X rotations at 0/pi16/pi8, not interval enclosure or general NLERP constant angular speed'});await save('commands.json',commands);
 const report={schema:1,status:'PASS',directory:path.relative(ROOT,directory).replaceAll('\\','/'),target:source.target,bones:source.motion.bones.map(b=>b.id),fingerprint:source.fingerprint,vertices:6,faces:4,floatCount:72,bytes:288,authoredShapeChangedFromPlan:false,sourceBytes:Buffer.byteLength(json),sourceSHA256:sha(json),sceneBytes:Buffer.byteLength(sceneJSON),sceneSHA256:sha(sceneJSON),startupMs,measurements:stats,sourceUnchanged:true,sdkBefore,sdkAfter,recipe:{path:'scripts/create-robot-back-cover.mjs',sha256:sha(await readFile(fileURLToPath(import.meta.url))),command:[process.execPath,...process.argv.slice(1)],node:process.version,scope:'Original authoring recipe; one-time C++ rest FK/bind. Saved context is the same recipe, not an external independent asset/level.'},nativeCLI:{path:cli,sha256:sha(await readFile(cli)),commands:commands.length},notes:'No source adjustment/angle shrink/face discard/normal fallback. Initial/warmup/raw observations retained. Continuous real parameter quality and game integration are separate acceptance.'};await save('report.json',report);console.log(JSON.stringify(report,null,2));
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url)await run(process.argv.length===3?process.argv[2]:null);
