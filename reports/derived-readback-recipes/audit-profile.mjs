// Original retained-evidence audit, with an independently fixed three-sample
// statistic and the previous public DTO/input as a cross-revision reference.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {hashProfileDTO} from '../../scripts/profile-derived-mesh.mjs';
const root=fileURLToPath(new URL('../../',import.meta.url));
const directory=path.resolve(process.argv[2]);
assert.ok([path.join(root,'build','derived-readback-root'),path.join(root,'reports','derived-readback-profile')].includes(path.dirname(directory)));
const read=async name=>JSON.parse(await readFile(path.join(directory,name),'utf8'));
const report=await read('report.json'),environment=await read('environment.json'),inputs=await read('case-inputs.json');
const sha=b=>createHash('sha256').update(b).digest('hex');
const modes=['singleBaseline','singleInstrumented','batchBaseline','batchInstrumented'];
function decode(x){
 if(x.type==='null')return null;
 if(x.type==='number'){const b=Buffer.from(x.bits,'hex');assert.equal(b.length,8);return b.readDoubleBE();}
 if(x.type==='Array')return x.items.map(decode);
 if(x.type==='Object')return Object.fromEntries(x.entries.map(([k,v])=>[k,decode(v)]));
 if(['string','boolean'].includes(x.type))return x.value;
 const Type={Float32Array,Uint32Array}[x.type];assert.ok(Type);const b=Buffer.from(x.bytesHex,'hex'),copy=new Uint8Array(b.length);copy.set(b);const result=new Type(copy.buffer);assert.equal(result.length,x.length);return result;
}
assert.equal(report.status,'PASS');assert.equal(report.queryCount,60);assert.equal(report.separateNativeModules,4);assert.equal(report.cases.length,3);
assert.equal(environment.sdkSourceHashes.length,53);assert.equal(environment.runtimeNotices.length,7);assert.equal(environment.sdkArtifacts.length,2);
for(const names of Object.values(report.nativeExports)){assert.equal(names.length,66);assert.ok(names.includes('_pp_sim_derived_mesh_records'));}
for(const k of ['nativeExportsUnchanged','runtimeMethodsUnchanged','prototypeUnchanged','sourceUnchanged','inputsUnchanged','oldDTOMutationSeparatedFromLaterDTOsAndInputs'])assert.equal(report[k],true);
let numbers=0;
for(const [i,item]of report.cases.entries()){
 const old=JSON.parse(await readFile(path.join(root,'reports','derived-gpu-public-'+[4,64,512][i]+'.json'),'utf8'));
 assert.deepEqual(inputs.cases[i].input,old.input);assert.deepEqual(inputs.cases[i].settings,old.settings);
 const first=await read(item.initialSnapshot.path),expected=hashProfileDTO(decode(old.firstPair.baseline));
 for(const mode of modes){assert.deepEqual(first[mode],old.firstPair.baseline);assert.deepEqual(hashProfileDTO(decode(first[mode])),expected);}
 assert.equal(item.trials.length,5);assert.deepEqual(item.trials.map(t=>t.phase),['initial','warmup','measure','measure','measure']);
 const records=[item.vertices,item.triangles,item.triangles,item.triangles];
 for(const [pair,trial]of item.trials.entries()){
  assert.deepEqual(trial.order,pair%2?[...modes].reverse():modes);assert.equal(trial.pair,pair);
  assert.equal(trial.comparedNumericValues,3*(expected.counts.numbers+expected.counts.typedElements));numbers+=trial.comparedNumericValues;
  assert.deepEqual(await read(item.name+'-pair-'+pair+'.json'),trial);
  for(const mode of modes){
   const o=trial.outcomes[mode];assert.equal(o.error,null);assert.equal(o.clockError,null);assert.deepEqual(o.resultHash,expected);assert.ok(Number.isFinite(o.timing.elapsedMs)&&o.timing.elapsedMs>=0);
   if(mode.endsWith('Instrumented')){
    const calls=mode.startsWith('single')?records:records.map((n,j)=>Math.ceil(n/[20,20,3,2][j]));
    assert.deepEqual(o.timing.getterKinds,calls);assert.deepEqual(o.timing.getterRecords,records);
    const s=o.timing.stages;assert.equal(s.cppGetter.calls,calls.reduce((a,b)=>a+b,0));assert.equal(s.outputCopy.calls,1+s.cppGetter.calls);
    for(const k of ['f64Exchange','u32Exchange','cppQuery'])assert.equal(s[k].calls,1);
    for(const value of Object.values(s))assert.ok(Number.isFinite(value.elapsedMs)&&value.elapsedMs>=0);
    assert.equal(o.timing.unassignedMs,o.timing.elapsedMs-Object.values(s).reduce((a,b)=>a+b.elapsedMs,0));assert.ok(o.timing.unassignedMs>=0);
   }
  }
 }
 for(const mode of modes){
  const measured=item.trials.slice(2).map(t=>t.outcomes[mode].timing),statistics=values=>{assert.equal(values.length,3);const s=[...values].sort((a,b)=>a-b);return {samples:3,medianMs:s[1],p95Ms:s[2],maxMs:s[2]};};
  assert.deepEqual(item.measureSummary[mode].elapsed,statistics(measured.map(t=>t.elapsedMs)));
  if(mode.endsWith('Instrumented')){for(const stage of Object.keys(measured[0].stages))assert.deepEqual(item.measureSummary[mode].stages[stage],statistics(measured.map(t=>t.stages[stage].elapsedMs)));assert.deepEqual(item.measureSummary[mode].unassigned,statistics(measured.map(t=>t.unassignedMs)));}
 }
}
assert.equal(numbers,406410);assert.equal(report.totalComparedNumericValues,numbers);
for(const file of report.files){const b=await readFile(path.join(directory,file.path));assert.equal(b.length,file.bytes);assert.equal(sha(b),file.sha256);}
const result={status:'PASS',queryCount:60,numericComparisons:406410,priorPublicFirstDTOsMatched:3,transports:4,actualDerivedQueriesAdded:0,statistics:'Independent fixed three-sample median/max/nearest-rank-p95 and direct stage residual',scope:'Retained evidence consistency; not GPU readback or clock authenticity.',files:report.files};
try{assert.deepEqual(JSON.parse(await readFile(path.join(directory,'parent-audit.json'),'utf8')),result);}
catch(error){if(error.code!=='ENOENT')throw error;await writeFile(path.join(directory,'parent-audit.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});}
console.log(JSON.stringify({...result,files:result.files.length}));
