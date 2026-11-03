import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,readdir,stat} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {createHash,randomBytes} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseProfileArgs,hashProfileDTO,profileStatistics} from '../scripts/profile-derived-mesh.mjs';
import * as profileModule from '../scripts/profile-derived-mesh.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url)),cli=path.join(ROOT,'scripts/profile-derived-mesh.mjs');
const run=args=>spawnSync(process.execPath,[cli,...args],{cwd:ROOT,encoding:'utf8',windowsHide:true,timeout:60000,maxBuffer:4*1024*1024});
const json=async file=>JSON.parse(await readFile(file,'utf8'));

test('profile CLI has bounded explicit options and rejects duplicates, unknown arguments and malformed counts',()=>{
 assert.equal(Object.hasOwn(profileModule,'runDerivedMeshProfile'),false,'Filesystem/query runner is private and reachable only after CLI option parsing');
 assert.deepEqual(parseProfileArgs(['--help']),{help:true});
 const defaults=parseProfileArgs(['--output','build/derived-profile-test']);assert.equal(defaults.repeats,3);assert.equal(defaults.warmup,1);assert.equal(defaults.totalQueries,100);
 assert.equal(parseProfileArgs(['--output','build/derived-profile-test','--repeats','9','--warmup','3']).totalQueries,260);
 assert.equal(parseProfileArgs(['--output','build/derived-profile-test','--quick','--repeats','1','--warmup','0']).totalQueries,32);
 for(const args of [[],['--output'],['--unknown'],['--output','x','--quick','--quick'],['--output','x','--output','y'],['--help','--quick'],['--output','x','--repeats','0'],['--output','x','--repeats','10'],['--output','x','--repeats','01'],['--output','x','--repeats','1.5'],['--output','x','--warmup','4'],['--output','x','--warmup','-1'],['--output','x','--quick=false']])assert.throws(()=>parseProfileArgs(args));
});

test('profile DTO hash retains number signs, typed bytes and types, view offsets and ordered keys',()=>{
 assert.notEqual(hashProfileDTO(0).sha256,hashProfileDTO(-0).sha256);
 assert.notEqual(hashProfileDTO(new Float32Array([0])).sha256,hashProfileDTO(new Float32Array([-0])).sha256);
 assert.notEqual(hashProfileDTO(new Float32Array([0])).sha256,hashProfileDTO(new Uint32Array([0])).sha256);
 assert.notEqual(hashProfileDTO({a:1,b:2}).sha256,hashProfileDTO({b:2,a:1}).sha256);
 const a=new Float32Array([99,1,-0,88]),b=new Float32Array([1,-0]);assert.deepEqual(hashProfileDTO(a.subarray(1,3)),hashProfileDTO(b));
 const value={a:[Number.MIN_VALUE,-0,1],b:new Uint32Array([0,0xffffffff])},before=structuredClone(value);hashProfileDTO(value);assert.deepEqual(value,before);
 assert.equal(hashProfileDTO(value).counts.numbers,3);assert.equal(hashProfileDTO(value).counts.typedElements,2);assert.throws(()=>hashProfileDTO(Array(1)),/Sparse/);
 assert.deepEqual(profileStatistics([9,1,4,2]),{samples:4,medianMs:3,p95Ms:9,maxMs:9});
 assert.deepEqual(profileStatistics(Array.from({length:20},(_,j)=>j+1)),{samples:20,medianMs:10.5,p95Ms:19,maxMs:20});
 assert.deepEqual(profileStatistics([7]),{samples:1,medianMs:7,p95Ms:7,maxMs:7});
 for(const values of [[],[NaN],[-1],[Infinity]])assert.throws(()=>profileStatistics(values));
});

test('profile CLI output guard rejects external/nonprofile roots and existing files without changing evidence',async()=>{
 const suffix=randomBytes(5).toString('hex'),blocked=path.join(ROOT,'build','derived-profile-blocked-'+suffix);
 await mkdir(path.join(ROOT,'build'),{recursive:true});await writeFile(blocked,'existing evidence',{flag:'wx'});
 for(const output of [blocked,path.join(ROOT,'build','wrong-profile-'+suffix),ROOT,path.join(ROOT,'build','derived-profile','..','outside-'+suffix)]){const r=run(['--quick','--output',output]);assert.equal(r.status,1);assert.match(r.stderr,/Output|directory/);}
 assert.equal(await readFile(blocked,'utf8'),'existing evidence');
 const r=run(['--output',blocked,'--wat']);assert.equal(r.status,1);assert.match(r.stderr,/Unknown argument/);assert.equal(await readFile(blocked,'utf8'),'existing evidence');
});

test('profile quick CLI uses actual WASM, retains all warmups, separates expected failures and recovers without changing old runs',async()=>{
 const output=path.join(ROOT,'build','derived-profile-cli-'+randomBytes(5).toString('hex'));
 const first=run(['--quick','--repeats','1','--warmup','1','--output',output]);assert.equal(first.status,0,first.stderr);
 const summary=JSON.parse(first.stdout),dir=summary.runDirectory,report=await json(path.join(dir,'report.json')),env=await json(path.join(dir,'environment.json')),inputs=await json(path.join(dir,'case-inputs.json'));
 assert.equal(report.status,'PASS');assert.equal(report.mode,'quick');assert.equal(report.queryCount,48);assert.equal(report.cases.length,8);assert.equal(env.sdkSourceHashes.length,53);assert.equal(env.runtimeNotices.length,7);assert.equal(env.sdkArtifacts.length,2);assert.equal(report.nativeExportCount,66);assert.equal(report.nativeExportsUnchanged,true);assert.equal(report.sourceUnchanged,true);
 assert.deepEqual(report.cases.slice(0,3).map(c=>c.triangles),[4,64,512]);assert.equal(inputs.cases.length,8);assert.equal(inputs.cases.find(c=>c.name==='expected-host-2049').input.positions.length,2049);
 assert.equal(report.sourcePreparation.sourceUnchanged,true);assert.equal(report.sourcePreparation.deformationStatus,'completed');assert.match(report.timingContract,/uncalibrated/);assert.match(report.timingContract,/not pure JavaScript/);assert.match(report.scope,/No GPU/);
 let total=0;
 for(const c of report.cases){assert.equal(c.trials.length,3);assert.deepEqual(c.trials.map(t=>t.phase),['initial','warmup','measure']);assert.equal(c.measureSummary.sampleCount,1);assert.equal(c.measureSummary.baseline.elapsed.medianMs,c.trials[2].baseline.timing.elapsedMs);assert.equal(c.measureSummary.instrumented.elapsed.p95Ms,c.trials[2].instrumented.timing.elapsedMs);assert.deepEqual(c.measureSummary.classification,c.expectation);
  const snapshot=await json(path.join(dir,c.initialSnapshot.path));assert.equal(snapshot.encoding,'tagged-exact-v1');assert.deepEqual(snapshot.baseline,snapshot.instrumented);
  for(const [j,t] of c.trials.entries()){assert.deepEqual(t.order,j%2===0?['baseline','instrumented']:['instrumented','baseline']);assert.deepEqual(t.baseline.resultHash,t.instrumented.resultHash);assert.equal(t.instrumented.clockError,null);assert.ok(t.baseline.timing.elapsedMs>=0);assert.ok(t.instrumented.timing.unassignedMs>=0);total+=t.comparedNumericValues;
   if(c.expectation.kind==='host_rejection'){assert.ok(t.baseline.error&&t.instrumented.error);assert.equal(t.instrumented.timing.stages.cppQuery.calls,0);assert.deepEqual(t.instrumented.timing.getterKinds,[0,0,0,0]);}
   else{assert.equal(t.baseline.error,null);assert.equal(t.instrumented.error,null);assert.equal(t.instrumented.timing.stages.cppQuery.calls,1);}
   if(c.expectation.kind==='completed'){assert.deepEqual(t.instrumented.timing.getterKinds,[c.vertices,c.triangles,c.triangles,c.triangles]);assert.equal(t.instrumented.timing.stages.cppGetter.calls,c.vertices+3*c.triangles);assert.equal(t.instrumented.timing.stages.outputCopy.calls,1+c.vertices+3*c.triangles);assert.equal(t.instrumented.renderDataFactory.calls,1);}
   else assert.equal(t.instrumented.renderDataFactory,null);
  }
 }
 assert.equal(total,report.totalComparedNumericValues);assert.equal(report.cases.at(-1).name,'recovery-unit');assert.equal(report.cases.at(-1).expectation.kind,'completed');
 const files=await readdir(dir),sizes=await Promise.all(files.map(name=>stat(path.join(dir,name))));assert.ok(sizes.reduce((sum,s)=>sum+s.size,0)<10*1024*1024);assert.equal(sizes.reduce((sum,s)=>sum+s.size,0),summary.retainedBytes);
 const retained=await readFile(path.join(dir,'report.json')),oldHash=createHash('sha256').update(retained).digest('hex');
 const second=run(['--quick','--repeats','1','--warmup','0','--output',output]);assert.equal(second.status,0,second.stderr);assert.notEqual(JSON.parse(second.stdout).runDirectory,dir);assert.equal(createHash('sha256').update(await readFile(path.join(dir,'report.json'))).digest('hex'),oldHash);
});
