import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {loadSimulationRuntime} from '../engine/simulation.mjs';

const [file,reportFile,outputsFile,oracleFile]=process.argv.slice(2);
if(!file)throw new Error('Usage: node scripts/verify-motion-wasm.mjs native.json|executable [report.json] [outputs.json] [oracle.csv]');
const names=('rest two-link permuted-tree shear linear-start linear-quarter linear-mid '+
  'linear-terminal clamp-after loop-duration loop-multiple loop-offset loop-huge-clock '+
  'hold-before hold-after exact-first-key single-key step-before step-boundary step-after '+
  'antipodal-mid antipodal-terminal huge-quaternion subnormal-quaternion subnormal-duration '+
  'missing-track-rest maximum-id duplicate-id zero-id unsafe-id missing-parent multiple-roots '+
  'disconnected-cycle self-cycle unknown-track duplicate-track empty-track duplicate-time '+
  'descending-time outside-time zero-quaternion negative-scale zero-scale outside-position '+
  'outside-quaternion zero-duration negative-sample invalid-mode invalid-interpolation '+
  'invalid-budget bone-budget track-budget key-budget empty-tree world-overflow branching-order').split(' ');
const text=file.endsWith('.json')?await readFile(file,'utf8'):execFileSync(path.resolve(file),['--fixtures'],{encoding:'utf8',timeout:60000,maxBuffer:16*1024*1024});
const source=JSON.parse(text.replace(/^\uFEFF/,''));
assert.equal(source.schema,1);assert.deepEqual(source.fixtures.map(f=>f.name),names);
const bytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:bytes});
const statuses=['completed','invalid_input','budget_exceeded','numerical_failure'];
const bits=n=>{assert.ok(Number.isFinite(n),'finite binary64 expected');const d=new DataView(new ArrayBuffer(8));d.setFloat64(0,n);return d.getBigUint64(0).toString(16).padStart(16,'0');};
const counters={fixtures:0,recovery:0,oracle:0};
function compare(actual,expected,label,kind='fixtures'){
  assert.equal(typeof actual,typeof expected,label);
  if(typeof actual==='number'){assert.equal(bits(actual),bits(expected),label);++counters[kind];}
  else if(actual&&typeof actual==='object'){
    assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort(),label);
    for(const key of Object.keys(actual))compare(actual[key],expected[key],label+'.'+key,kind);
  }else assert.equal(actual,expected,label);
}
function binary64(value){
  if(typeof value==='number')return bits(value);
  if(Array.isArray(value))return value.map(binary64);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,binary64(v)]));
  return value;
}
function projected(result){
  assert.ok(statuses.includes(result.status),'known C++ motion status');
  if(result.status!=='completed'){
    assert.deepEqual(result.bones,[]);assert.deepEqual(result.evaluationOrder,[]);assert.equal(result.sampledTime,null);
    return {status:statuses.indexOf(result.status),pose:null};
  }
  for(const bone of result.bones){
    assert.deepEqual(bone.worldPosition.map(bits),bone.worldMatrix.slice(12,15).map(bits),'joint position copies matrix');
    assert.equal(result.evaluationOrder[bone.evaluationRank],bone.id,'evaluation rank/ID');
  }
  return {status:0,pose:{requestedTime:result.requestedTime,sampledTime:result.sampledTime,evaluationOrder:result.evaluationOrder,
    bones:result.bones.map(b=>({id:b.id,parentId:b.parentId,local:b.local,localMatrix:b.localMatrix,worldMatrix:b.worldMatrix}))}};
}
function inputOf(x){return {bones:x.bones,clip:{duration:x.duration,tracks:x.tracks.map(t=>({boneId:t.boneId,interpolation:t.interpolation===0?'linear':t.interpolation===1?'step':'invalid:'+t.interpolation,keys:t.keys.map(k=>({time:k.time,...k.pose}))}))}};}
function settingsOf(x){return {loop:x.mode===0?false:x.mode===1?true:x.mode,maximumBones:x.settings[0],maximumTracks:x.settings[1],maximumKeys:x.settings[2]};}
const rejected=new Map([
  ['zero-id',{layer:'JS exact positive numeric ID',pattern:/Body ID/}],
  ['unsafe-id',{layer:'JS exact positive numeric ID',pattern:/Body ID/}],
  ['invalid-mode',{layer:'JS explicit boolean playback exchange',pattern:/explicit loop boolean/}],
  ['invalid-interpolation',{layer:'JS interpolation enum exchange',pattern:/linear\/step interpolation/}],
  ['invalid-budget',{layer:'C ABI bounded integer settings exchange',pattern:/integer/i}],
]);
const outputs=[];let modelFixtures=0,exchangeRejections=0,recoveryChecks=0;
const recovery=source.fixtures.find(f=>f.name==='linear-mid');
for(const fixture of source.fixtures){
  const input=inputOf(fixture.input),settings=settingsOf(fixture.input),seconds=fixture.input.time;
  if(rejected.has(fixture.name)){
    assert.equal(fixture.result.status,1,'core reference also invalid');assert.equal(fixture.result.pose,null);
    let error;try{runtime.sampleMotion(input,seconds,settings);}catch(cause){error=cause;}
    assert.ok(error instanceof Error,fixture.name+': expected explicit exchange rejection');
    const policy=rejected.get(fixture.name);assert.match(error.message,policy.pattern,fixture.name+': rejection cause');
    ++exchangeRejections;
    const recovered=runtime.sampleMotion(inputOf(recovery.input),recovery.input.time,settingsOf(recovery.input));
    const core=projected(recovered);compare(core,recovery.result,fixture.name+'.recovery','recovery');++recoveryChecks;
    outputs.push({name:fixture.name,input,settings,expectedExchangeRejection:true,layer:policy.layer,error:{name:error.name,code:error.code??null,message:error.message},recovery:recovered,recoveryBinary64:binary64(core)});
    continue;
  }
  const result=runtime.sampleMotion(input,seconds,settings);
  assert.equal(bits(result.requestedTime),bits(seconds),'summary requested time');
  assert.equal(bits(result.duration),bits(fixture.input.duration),'summary source duration');
  assert.equal(result.playback,fixture.input.mode===1?'loop':'clamp','summary playback');
  const core=projected(result);compare(core,fixture.result,fixture.name);++modelFixtures;
  outputs.push({name:fixture.name,input,settings,result,core,binary64:binary64(core)});
}
assert.equal(modelFixtures,51);assert.equal(exchangeRejections,5);assert.equal(recoveryChecks,5);

let oracleRows=0;const oracleOutputs=[];
if(oracleFile){
  const lines=(await readFile(oracleFile,'utf8')).replace(/^\uFEFF/,'').trim().split(/\r?\n/);
  assert.equal(lines.shift(),['id','time',...Array.from({length:16},(_,i)=>'world'+i)].join(','));assert.equal(lines.length,128);
  const hex=text=>{
    const m=/^(-?)0x([01])(?:\.([0-9a-f]{1,13}))?p([+-]?\d+)$/.exec(text);assert.ok(m,'exact binary64 hex literal');
    const fraction=m[3]??'',exponent=Number(m[4]);assert.ok(Number.isInteger(exponent)&&exponent>=-1022&&exponent<=1023,'normal corpus exponent');
    const value=(m[1]?-1:1)*(Number.parseInt(m[2]+fraction,16)*2**(-4*fraction.length))*2**exponent;assert.ok(Number.isFinite(value));return value;
  };
  const input={bones:[{id:10,parentId:0,rest:{position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}},{id:20,parentId:10,rest:{position:[1,2,0],rotation:[0,0,1,2],scale:[2,.5,1]}}],
    clip:{duration:2,tracks:[{boneId:10,interpolation:'linear',keys:[{time:0,position:[0,0,0],rotation:[0,0,0,4],scale:[1,1,1]},{time:2,position:[4,2,-2],rotation:[0,0,3,4],scale:[3,2,1]}]}]}};
  for(const [j,line] of lines.entries()){
    const fields=line.split(',');assert.equal(fields.length,18);assert.equal(fields[0],String(j));const time=hex(fields[1]);assert.equal(bits(time),bits(j/64));
    const result=runtime.sampleMotion(input,time);assert.equal(result.status,'completed');assert.deepEqual(result.evaluationOrder,[10,20]);
    const expected=fields.slice(2).map(hex);compare(result.bones[1].worldMatrix,expected,'oracle.'+j,'oracle');++oracleRows;
    oracleOutputs.push({id:j,time,result,binary64:binary64(projected(result))});
  }
}
const report={status:'PASS',fixtures:source.fixtures.length,modelFixtures,exchangeRejections,recoveryChecks,
  fixtureNumbers:counters.fixtures,recoveryNumbers:counters.recovery,oracleRows,oracleMatrixBits:counters.oracle,
  bitEqualNumbers:counters.fixtures+counters.recovery+counters.oracle,maximumAbsoluteParityError:0,
  wasmBytes:bytes.length,wasmSha256:createHash('sha256').update(bytes).digest('hex'),
  limits:'Observed finite point-binary64 parity on shipped JS/C ABI. Five narrower exchange-domain rejections are counted explicitly. Not interval containment, events, IK, control, skinning or arbitrary-input precision/fps proof.'};
console.log(JSON.stringify(report,null,2));
if(reportFile)await writeFile(reportFile,JSON.stringify(report,null,2)+'\n');
if(outputsFile)await writeFile(outputsFile,JSON.stringify({schema:1,outputs,oracleOutputs})+'\n');
