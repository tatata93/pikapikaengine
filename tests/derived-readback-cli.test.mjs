import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,readdir,stat} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {randomBytes,createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseReadbackArgs,exactReadbackDTO,expectedReadbackCounts} from '../scripts/profile-derived-readback.mjs';
import * as cliModule from '../scripts/profile-derived-readback.mjs';
import {hashProfileDTO,profileStatistics} from '../scripts/profile-derived-mesh.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url)),cli=path.join(ROOT,'scripts/profile-derived-readback.mjs');
const run=args=>spawnSync(process.execPath,[cli,...args],{cwd:ROOT,encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:1024*1024});
const json=async name=>JSON.parse(await readFile(name,'utf8'));

test('readback CLI parser exposes only fixed bounded output/help and keeps runner private',()=>{
 assert.equal(Object.hasOwn(cliModule,'run'),false);assert.deepEqual(parseReadbackArgs(['--help']),{help:true});
 assert.deepEqual(parseReadbackArgs(['--output','build/derived-readback-unit']),{output:'build/derived-readback-unit',totalQueries:60});
 for(const args of [[],['--output'],['--quick'],['--help','--output','x'],['--output','--help'],['--output','x','--output','y'],['--output','x','--repeats','1'],['--output','x','--warmup','0'],['--help=false']])assert.throws(()=>parseReadbackArgs(args),/Usage/);
 const help=run(['--help']);assert.equal(help.status,0);assert.match(help.stdout,/derived-readback/);
});

test('readback exact encoding preserves signed zero, typed byte views and ordered object keys',()=>{
 const values=[-0,Number.MIN_VALUE,1],before=structuredClone(values),encoded=exactReadbackDTO(values);assert.deepEqual(values,before);assert.equal(encoded.items[0].bits,'8000000000000000');assert.equal(encoded.items[1].bits,'0000000000000001');
 assert.notDeepEqual(exactReadbackDTO(0),exactReadbackDTO(-0));assert.notDeepEqual(exactReadbackDTO(new Float32Array([0])),exactReadbackDTO(new Float32Array([-0])));
 assert.notDeepEqual(exactReadbackDTO(new Float32Array([0])),exactReadbackDTO(new Uint32Array([0])));assert.notDeepEqual(exactReadbackDTO({a:1,b:2}),exactReadbackDTO({b:2,a:1}));
 const view=new Float32Array([99,-0,Number.MIN_VALUE,88]);assert.deepEqual(exactReadbackDTO(view.subarray(1,3)),exactReadbackDTO(new Float32Array([-0,Number.MIN_VALUE])));
 for(const value of [NaN,Infinity,undefined,Array(1),new DataView(new ArrayBuffer(1))])assert.throws(()=>exactReadbackDTO(value));
 assert.notEqual(hashProfileDTO({a:-0}).sha256,hashProfileDTO({a:0}).sha256);
});

test('readback accounting distinguishes batch calls from record totals and covers empty failure prefixes',()=>{
 const result=(vertices,faces,audits=faces)=>({geometry:vertices?{positions:Array(vertices),triangles:Array(faces)}:null,audits:Array(audits)});
 for(const [vertices,faces,getters]of [[6,4,6],[192,64,68],[512,512,479]]){const r=result(vertices,faces);assert.deepEqual(expectedReadbackCounts(r,'single'),{records:[vertices,faces,faces,faces],calls:[vertices,faces,faces,faces],getters:vertices+3*faces});assert.equal(expectedReadbackCounts(r,'batch').getters,getters);}
 assert.deepEqual(expectedReadbackCounts(result(0,0,3),'batch'),{records:[0,0,0,3],calls:[0,0,0,2],getters:2});assert.deepEqual(expectedReadbackCounts(result(0,0,0),'batch'),{records:[0,0,0,0],calls:[0,0,0,0],getters:0});assert.throws(()=>expectedReadbackCounts(result(3,1),'auto'));
});

test('readback CLI guard preserves preexisting files and rejects external or unrelated output roots',async()=>{
 const suffix=randomBytes(5).toString('hex'),blocked=path.join(ROOT,'build','derived-readback-blocked-'+suffix);await mkdir(path.dirname(blocked),{recursive:true});await writeFile(blocked,'immutable evidence',{flag:'wx'});
 for(const output of [blocked,ROOT,path.join(ROOT,'build','not-readback-'+suffix),path.join(ROOT,'build','derived-readback','nested'),path.join(ROOT,'build','derived-readback','..','outside-'+suffix)]){const result=run(['--output',output]);assert.equal(result.status,1,result.stderr);assert.match(result.stderr,/Output|directory/);}
 assert.equal(await readFile(blocked,'utf8'),'immutable evidence');
});

// Explicit opt-in only: performance comparisons must run in isolation after all
// builds/tests, not compete with the normal parallel test runner.
if(process.env.PIKAPIKA_READBACK_FULL_TEST==='1')test('readback actual SDK fixed 60-query comparison retains all four paths, exact first DTOs and raw phases once',async()=>{
 const output=path.join(ROOT,'build','derived-readback-cli-'+randomBytes(5).toString('hex')),old=path.join(output,'run-old');await mkdir(old,{recursive:true});await writeFile(path.join(old,'evidence'),'preserve',{flag:'wx'});
 const result=run(['--output',output]);assert.equal(result.error,undefined,result.error?.message);assert.equal(result.status,0,result.stderr);
 const summary=JSON.parse(result.stdout),directory=summary.runDirectory,report=await json(path.join(directory,'report.json')),environment=await json(path.join(directory,'environment.json')),inputs=await json(path.join(directory,'case-inputs.json'));
 assert.equal(report.status,'PASS');assert.equal(report.queryCount,60);assert.equal(report.separateNativeModules,4);assert.equal(report.cases.length,3);assert.deepEqual(report.cases.map(item=>item.triangles),[4,64,512]);assert.equal(inputs.cases.length,3);assert.equal(report.ownedSnapshotsUnchanged,12);assert.equal(report.oldDTOMutationSeparatedFromLaterDTOsAndInputs,true);
 assert.equal(environment.sdkSourceHashes.length,53);assert.equal(environment.runtimeNotices.length,7);assert.equal(environment.sdkArtifacts.length,2);for(const names of Object.values(report.nativeExports)){assert.equal(names.length,66);assert.ok(names.includes('_pp_sim_derived_mesh_records'));}
 for(const key of ['nativeExportsUnchanged','runtimeMethodsUnchanged','prototypeUnchanged','sourceUnchanged','inputsUnchanged'])assert.equal(report[key],true);
 const keys=['singleBaseline','singleInstrumented','batchBaseline','batchInstrumented'];let compared=0;
 for(const item of report.cases){assert.equal(item.trials.length,5);assert.deepEqual(item.trials.map(trial=>trial.phase),['initial','warmup','measure','measure','measure']);const snapshot=await json(path.join(directory,item.initialSnapshot.path));assert.equal(snapshot.encoding,'tagged-exact-v1');for(const key of keys)assert.deepEqual(snapshot[key],snapshot.singleBaseline);
  for(const [index,trial]of item.trials.entries()){assert.deepEqual(trial.order,index%2===0?keys:[...keys].reverse());compared+=trial.comparedNumericValues;
   for(const key of keys){const outcome=trial.outcomes[key];assert.equal(outcome.error,null);assert.equal(outcome.clockError,null);assert.deepEqual(outcome.resultHash,trial.outcomes.singleBaseline.resultHash);assert.ok(outcome.timing.elapsedMs>=0);
    if(key.endsWith('Instrumented')){const records=[item.vertices,item.triangles,item.triangles,item.triangles],calls=key.startsWith('single')?records:records.map((n,k)=>Math.ceil(n/[20,20,3,2][k]));assert.deepEqual(outcome.timing.getterRecords,records);assert.deepEqual(outcome.timing.getterKinds,calls);assert.equal(outcome.timing.stages.cppGetter.calls,calls.reduce((a,b)=>a+b,0));assert.equal(outcome.timing.stages.outputCopy.calls,1+calls.reduce((a,b)=>a+b,0));}
   }
  }
  for(const key of keys)assert.deepEqual(item.measureSummary[key].elapsed,profileStatistics(item.trials.slice(2).map(trial=>trial.outcomes[key].timing.elapsedMs)));
 }
 assert.equal(compared,report.totalComparedNumericValues);assert.equal(compared,3*135470);assert.match(report.scope,/No GPU/);assert.match(report.timingContract,/uncalibrated/);assert.match(report.timingContract,/not pure JavaScript/);
 for(const file of report.files){const bytes=await readFile(path.join(directory,file.path));assert.equal(bytes.length,file.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),file.sha256);}
 const names=await readdir(directory),sizes=await Promise.all(names.map(name=>stat(path.join(directory,name))));assert.equal(sizes.reduce((sum,item)=>sum+item.size,0),summary.retainedBytes);assert.ok(summary.retainedBytes<10*1024*1024);assert.equal(await readFile(path.join(old,'evidence'),'utf8'),'preserve');assert.notEqual(directory,old);assert.equal((await readdir(output)).length,2);
});
