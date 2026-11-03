import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {resolve,join,relative} from 'node:path';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {defaultSkinBindingSource,createSkinBindingSource,parseSkinBindingSource,serializeSkinBindingSource,
 parseSkinBindingPortable,serializeSkinBindingPortable,evaluateSkinBinding,meshFingerprint} from '../engine/skin-binding.mjs';
import {Scene,meshEntity} from '../engine/scene.mjs';
import {savePortableScene} from '../engine/portable-scene.mjs';

const [cliArg,outputArg='build/skin-binding-proof']=process.argv.slice(2);
if(!cliArg)throw new Error('Usage: node scripts/verify-skin-binding.mjs NativeCLI output-directory');
const root=process.cwd(),cli=resolve(cliArg),output=resolve(outputArg);await mkdir(output,{recursive:true});const run=await mkdtemp(join(output,'run-'));
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));const runtime=await loadSimulationRuntime({wasmBytes:wasm});
const commands=[];function command(args,expectedSuccess=true){const result=spawnSync(cli,args,{encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:8*1024*1024});commands.push({command:[cli,...args],exitCode:result.status,stdout:result.stdout??'',stderr:result.stderr??'',error:result.error?.message??null});if(expectedSuccess)assert.equal(result.status,0,result.stderr??result.error?.message);else assert.notEqual(result.status,0,'expected explicit source/file failure');return result;}
const bits=x=>{assert.ok(Number.isFinite(x));const view=new DataView(new ArrayBuffer(8));view.setFloat64(0,x);return view.getBigUint64(0).toString(16).padStart(16,'0');};
const bitTree=x=>typeof x==='number'?{f64:bits(x)}:Array.isArray(x)?x.map(bitTree):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,bitTree(x[k])])):x;
let matchingSourceNumbers=0,matchingResultNumbers=0;
function compare(actual,expected,kind){assert.deepEqual(bitTree(actual),bitTree(expected));const count=x=>typeof x==='number'?1:x&&typeof x==='object'?Object.values(x).reduce((n,v)=>n+count(v),0):0;if(kind==='source')matchingSourceNumbers+=count(actual);else matchingResultNumbers+=count(actual);}
const base=defaultSkinBindingSource(runtime),fixtures=[{name:'default',source:base}];
const edited=structuredClone(base);edited.influences[1][0].weight=3;edited.motion.clip.tracks.push({boneId:7,interpolation:'step',keys:[{time:0,position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]},{time:2,position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}]});fixtures.push({name:'edited-hidden-track',source:edited});
const permuted=structuredClone(edited);for(const key of ['joints','restBones'])permuted[key].reverse();permuted.motion.bones.reverse();permuted.motion.clip.tracks.reverse();for(const w of permuted.influences)w.reverse();fixtures.push({name:'permuted',source:permuted});
const tiny=structuredClone(base);tiny.name='原本🙂 "quote" \\';tiny.target={objectId:'腕🙂',nativeId:'9007199254740991'};tiny.mesh.positions[0][0]=-0;tiny.influences[0][0].weight=Number.MIN_VALUE;tiny.influences[1][1].weight=-0;tiny.joints[0].inverseBind[2]=-0;tiny.joints[0].restWorld[2]=-0;tiny.restBones[0].rest.rotation[0]=-0;tiny.fingerprint=meshFingerprint(tiny.mesh);fixtures.push({name:'unicode-signedzero-subnormal-max-id',source:tiny});
const underflow=structuredClone(base);underflow.influences[1]=[{boneId:19,weight:Number.MAX_VALUE},{boneId:7,weight:Number.MIN_VALUE}];fixtures.push({name:'author-underflow',source:underflow});
const inverse=structuredClone(base);inverse.joints[0].inverseBind[0]=2;fixtures.push({name:'invalid-inverse-quality',source:inverse});
const mismatch=structuredClone(base);mismatch.joints[0].restWorld[12]+=1;fixtures.push({name:'stored-rest-mismatch',source:mismatch,sourceFailure:true});
const huge=structuredClone(base);const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];huge.motion.bones=Array.from({length:128},(_,i)=>({id:i+1,name:'Overflow '+i,parentId:i,rest:{position:[0,0,0],rotation:[0,0,0,1],scale:[1e6,1e6,1e6]}}));huge.motion.clip.tracks=[];huge.restBones=huge.motion.bones.map(({id,parentId,rest})=>({id,parentId,rest:structuredClone(rest)}));huge.joints=huge.motion.bones.map(b=>({id:b.id,restWorld:[...identity],inverseBind:[...identity]}));huge.influences=huge.mesh.positions.map(()=>[{boneId:1,weight:1}]);fixtures.push({name:'rest-fk-overflow',source:huge,sourceFailure:true});
const records=[],modelStatusCounts={};let modelEvaluations=0,sourceFailureEvaluations=0;
for(const fixture of fixtures){
 const source=createSkinBindingSource(fixture.source),json=serializeSkinBindingSource(source),portable=serializeSkinBindingPortable(source),input=join(run,fixture.name+'.skin'),restoredFile=join(run,fixture.name+'-roundtrip.skin');
 await writeFile(join(run,fixture.name+'.json'),json);await writeFile(input,portable);compare(parseSkinBindingSource(json),source,'source');compare(parseSkinBindingPortable(portable),source,'source');
 command(['roundtrip',input,restoredFile]);const restored=parseSkinBindingPortable(await readFile(restoredFile,'utf8'));compare(restored,source,'source');
 const entity={...meshEntity(source.target.objectId,source.mesh),nativeId:source.target.nativeId},scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[entity]});const sceneFile=join(run,fixture.name+'.scene');await writeFile(sceneFile,savePortableScene(scene));command(['match',restoredFile,sceneFile]);
 const record={name:fixture.name,input:source,roundtrip:restored,inputBits:bitTree(source),roundtripBits:bitTree(restored),samples:[]};
 for(const [seconds,loop] of [[0,false],[.5,false],[1,false],[2,false],[3,true]]){
  if(fixture.sourceFailure){assert.throws(()=>evaluateSkinBinding(runtime,source,seconds,{loop,scene}));const native=command(['sample',restoredFile,String(seconds),...(loop?['loop']:[])],false);record.samples.push({seconds,loop,classification:'source-quality-exception',nativeExit:native.status});++sourceFailureEvaluations;continue;}
  const web=evaluateSkinBinding(runtime,source,seconds,{loop,scene}).deformation,native=parseStrictJson(command(['sample',restoredFile,String(seconds),...(loop?['loop']:[])]).stdout);
  const expected={status:web.status,positions:web.positions,diagnostics:web.diagnostics,weightResiduals:web.weightResiduals};compare(native,expected,'result');record.samples.push({seconds,loop,classification:'actual-cpp-model-result',native,web:expected,nativeBits:bitTree(native),webBits:bitTree(expected)});++modelEvaluations;modelStatusCounts[web.status]=(modelStatusCounts[web.status]??0)+1;
 }
 records.push(record);
}
const original=join(run,'default.skin'),existing=join(run,'preserve.skin');await writeFile(existing,'existing output must remain\n');const before=await readFile(existing);command(['roundtrip',original,existing],false);compare((await readFile(existing)).toString(),before.toString(),'source');
await writeFile(join(run,'outputs.json'),stringifyStrictJson({schema:1,fixtures:records},{maxBytes:32*1024*1024,maxDepth:24,maxNodes:2000000})+'\n');await writeFile(join(run,'commands.json'),JSON.stringify(commands,null,2)+'\n');
const paths=['engine/skin-binding.mjs','engine/strict-json.mjs','core/src/skinning_io.cpp','core/include/pikapika/skinning_io.hpp','tools/skinning_cli.cpp','scripts/verify-skin-binding.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json'];
const hashes=[];for(const path of paths){const data=await readFile(resolve(root,path));hashes.push({path,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')});}
const report={schema:1,status:'PASS',runDirectory:relative(root,run).replaceAll('\\','/'),sourceFixtures:fixtures.length,modelEvaluations,modelStatusCounts,sourceFailureEvaluations,matchingSourceNumbers,matchingResultNumbers,sourceArtifacts:hashes,wasmBytes:wasm.length,wasmSHA256:createHash('sha256').update(wasm).digest('hex'),
 scope:'Actual JSON/portable/Native round trips and Native/main C++ finite-result bit parity. Source-quality exceptions counted separately; no renderer, contact, interval or universal precision claim.'};
await writeFile(join(run,'report.json'),JSON.stringify(report,null,2)+'\n');await writeFile(join(output,'latest.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
