import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {loadSimulationRuntime} from '../engine/simulation.mjs';

const [fixtureFile,oracleFile,reportFile,outputsFile,replayFile,replayOracleFile]=process.argv.slice(2);
if(![fixtureFile,oracleFile,reportFile,outputsFile,replayFile,replayOracleFile].every(Boolean))throw new Error('Usage: node scripts/verify-skinning-wasm.mjs native.json native-oracle.csv report.json outputs.json replay.json replay-oracle.csv');
const python=process.env.PIKAPIKA_PYTHON??(process.platform==='win32'?'python':'python3');
const checker=fileURLToPath(new URL('./verify-skinning.py',import.meta.url));
const runReference=args=>JSON.parse(execFileSync(python,[checker,...args],{encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:4*1024*1024}));
// The independent checker validates duplicate keys, finite binary64, schema,
// fixed 65 names and fixed input fingerprints before JSON.parse is used here.
const nativeReference=runReference([fixtureFile,'--oracle',oracleFile]);
const source=JSON.parse((await readFile(fixtureFile,'utf8')).replace(/^\uFEFF/,''));
const bytes=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:bytes});
const statuses=['completed','invalid_input','budget_exceeded','ill_conditioned','numerical_failure'];
const dataView=new DataView(new ArrayBuffer(8));
const bits=n=>{assert.ok(Number.isFinite(n),'finite binary64 required');dataView.setFloat64(0,n);return dataView.getBigUint64(0).toString(16).padStart(16,'0');};
const bitsTree=x=>typeof x==='number'?bits(x):Array.isArray(x)?x.map(bitsTree):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,bitsTree(v)])):x;
const counts={model:0,classifiedHost:0,recovery:0,oracle:0};
function compare(a,b,label,kind='model'){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);++counts[kind];}
 else if(a&&typeof a==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k,kind);}
 else assert.equal(a,b,label);
}
// Native/WASM have different decimal/hex formatting. All persisted numbers
// retain -0, while the separate hex tree also records every binary64 bit.
function signedJSON(x){
 if(typeof x==='number'){assert.ok(Number.isFinite(x));return Object.is(x,-0)?'-0':JSON.stringify(x);}
 if(Array.isArray(x))return '['+x.map(signedJSON).join(',')+']';
 if(x&&typeof x==='object')return '{'+Object.entries(x).map(([k,v])=>JSON.stringify(k)+':'+signedJSON(v)).join(',')+'}';
 return JSON.stringify(x);
}
const settingsOf=a=>({maximumBones:a[0],maximumVertices:a[1],maximumInfluences:a[2],maximumCondition:a[3],maximumInverseResidual:a[4]});
const projected=r=>{assert.ok(statuses.includes(r.status));return {...r,status:statuses.indexOf(r.status)};};
const query=q=>q.operation==='bind'?runtime.bindSkin(q.rest,settingsOf(q.settings)):runtime.deformSkin({joints:q.joints,pose:q.pose,vertices:q.vertices},settingsOf(q.settings));
const rejects=new Map([
 ['bind-zero-id',{layer:'JS exact positive numeric ID',pattern:/Body ID/}],
 ['bind-unsafe-id',{layer:'JS exact positive numeric ID',pattern:/Body ID/}],
 ['bind-invalid-budget',{layer:'C ABI integer Settings budget',pattern:/integer/i}],
 ['bind-invalid-vertex-budget',{layer:'C ABI integer Settings budget',pattern:/integer/i}],
 ['bind-invalid-influence-budget',{layer:'C ABI integer Settings budget',pattern:/integer/i}],
]);
const recovery=source.fixtures.find(f=>f.name==='bind-identity');
const outputs=[],replay=[];
let modelFixtures=0,exchangeRejections=0;
for(const fixture of source.fixtures){
 const q=fixture.input;
 if(rejects.has(fixture.name)){
  const policy=rejects.get(fixture.name);let error;
  try{query(q);}catch(cause){error=cause;}
  assert.ok(error instanceof Error,fixture.name+': explicit rejection required');assert.match(error.message,policy.pattern);
  // A normalized *host rejection*, not a fabricated C++ result. All five have
  // no model outputs in Native too; the sidecar preserves that distinction.
  const classified={status:1,joints:null,positions:null,diagnostics:[],weightResiduals:[]};
  compare(classified,fixture.result,fixture.name,'classifiedHost');
  const recovered=query(recovery.input);compare(projected(recovered),recovery.result,fixture.name+'.retry','recovery');
  outputs.push({name:fixture.name,input:q,classification:'exchange_rejected',layer:policy.layer,
   error:{name:error.name,code:error.code??null,message:error.message},classifiedResult:classified,recovery:recovered,binary64:bitsTree(recovered)});
  replay.push({...fixture,result:classified});++exchangeRejections;continue;
 }
 const result=query(q),core=projected(result);compare(core,fixture.result,fixture.name);
 outputs.push({name:fixture.name,input:q,classification:'C++ model result',result,binary64:bitsTree(result)});
 replay.push({...fixture,result:core});++modelFixtures;
}
assert.equal(modelFixtures,60);assert.equal(exchangeRejections,5);

function fromHex(text){
 const m=/^(-?)0x([0-9a-f]+)(?:\.([0-9a-f]*))?p([+-]?\d+)$/.exec(text);assert.ok(m,'hexadecimal binary64 literal');
 const fraction=m[3]??'',mantissa=BigInt('0x'+m[2]+fraction),power=Number(m[4])-4*fraction.length;
 assert.ok(Number.isSafeInteger(power));let raw=m[1]?1n<<63n:0n;
 if(mantissa){
  const width=mantissa.toString(2).length,exponent=power+width-1;assert.ok(exponent<=1023&&exponent>=-1074);
  if(exponent>=-1022){const shift=53-width;let full;
   if(shift>=0)full=mantissa<<BigInt(shift);else{const mask=(1n<<BigInt(-shift))-1n;assert.equal(mantissa&mask,0n,'hex rounds instead of encoding exact binary64');full=mantissa>>BigInt(-shift);}
   raw|=BigInt(exponent+1023)<<52n;raw|=full-(1n<<52n);
  }else{const shift=power+1074;let sub;
   if(shift>=0)sub=mantissa<<BigInt(shift);else{const mask=(1n<<BigInt(-shift))-1n;assert.equal(mantissa&mask,0n);sub=mantissa>>BigInt(-shift);}
   assert.ok(sub>0n&&sub<(1n<<52n));raw|=sub;
  }
 }
 dataView.setBigUint64(0,raw);const result=dataView.getFloat64(0);assert.ok(Number.isFinite(result));return result;
}
function toHex(n){
 const raw=BigInt('0x'+bits(n)),negative=raw>>63n,exponent=Number((raw>>52n)&2047n),fraction=(raw&((1n<<52n)-1n)).toString(16).padStart(13,'0');
 return (negative?'-':'')+(exponent?'0x1.'+fraction+'p'+(exponent-1023):'0x0.'+fraction+'p-1022');
}
// Exact encoding sanity checks cover zeros, subnormal/normal boundaries and
// maximal finite values; no float hex parsing through underflowing 2**powers.
for(const n of [0,-0,Number.MIN_VALUE,-Number.MIN_VALUE,2**-1022,1,1.5,Number.MAX_VALUE])assert.equal(bits(fromHex(toHex(n))),bits(n));
const lines=(await readFile(oracleFile,'utf8')).replace(/^\uFEFF/,'').trim().split(/\r?\n/),header=lines.shift();
assert.equal(lines.length,128);const oracleReplay=[header],oracleOutputs=[];
for(const [j,line] of lines.entries()){
 const fields=line.split(',');assert.equal(fields.length,105);assert.equal(fields[0],String(j));
 const values=[j,...fields.slice(1).map(fromHex)],matrices=Array.from({length:4},(_,k)=>values.slice(1+16*k,17+16*k));
 const bound=runtime.bindSkin([{id:7,matrix:matrices[0]},{id:19,matrix:matrices[1]}]);assert.equal(bound.status,'completed');
 const expectedInverses=[values.slice(70,86),values.slice(86,102)];
 bound.joints.forEach((joint,k)=>compare(joint.inverseBind,expectedInverses[k],`oracle.${j}.inverse.${k}`,'oracle'));
 const input={joints:bound.joints,pose:[{id:19,matrix:matrices[3]},{id:7,matrix:matrices[2]}],
  vertices:[{position:values.slice(65,68),influences:[{id:19,weight:values[69]},{id:7,weight:values[68]}]}]};
 const deformed=runtime.deformSkin(input);assert.equal(deformed.status,'completed');compare(deformed.positions[0],values.slice(102,105),`oracle.${j}.position`,'oracle');
 oracleOutputs.push({id:j,input,bind:bound,deform:deformed,binary64:bitsTree({bind:bound,deform:deformed})});
 oracleReplay.push([...fields.slice(0,70),...bound.joints.flatMap(joint=>joint.inverseBind.map(toHex)),...deformed.positions[0].map(toHex)].join(','));
}
await writeFile(replayFile,signedJSON({schema:1,fixtures:replay})+'\n');
await writeFile(replayOracleFile,oracleReplay.join('\n')+'\n');
const mainReference=runReference([fixtureFile,replayFile,'--oracle',oracleFile,'--wasm-oracle',replayOracleFile]);
const report={status:'PASS',fixtures:65,modelFixtures,exchangeRejections,exchangeRejectedNames:[...rejects.keys()],sdkRangeExcludedFixtures:0,
 classification:'Replay JSON includes 60 actual C++ model results and five explicitly classified host exchange failures with no C++ result. Not all 65 are accepted WASM model queries.',
 fixtureResultNumbers:counts.model,classifiedHostStatusNumbers:counts.classifiedHost,recoveryNumbers:counts.recovery,
 oracleRows:128,oracleResultNumbers:counts.oracle,actualResultBitsCompared:counts.model+counts.recovery+counts.oracle,
 nativeReference,mainReference,wasmBytes:bytes.length,wasmSHA256:createHash('sha256').update(bytes).digest('hex'),
 sdkActualLimits:{bones:128,vertices:2048,influences:8192},nativeSettingsLimits:{bones:128,vertices:65536,influences:262144},
 scope:'Original finite inputs and copied snapshots only; point-binary64 parity and fixed-corpus rational point tests, not arbitrary-input precision, intervals, GPU skinning or normals.'};
await writeFile(outputsFile,signedJSON({schema:1,outputs,oracleOutputs})+'\n');
await writeFile(reportFile,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
