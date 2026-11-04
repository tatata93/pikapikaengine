// Actual shared-WASM entry C ABI replay. This does not implement or exercise
// the future public owned JavaScript entry decoder or a JavaScript solver.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const [nativeFile,directory,...extra]=process.argv.slice(2);
if(!nativeFile||!directory||extra.length)throw Error('Usage: node scripts/verify-sphere-triangle-mesh-entry-wasm-wire.mjs native-packets.json fresh-output-directory');
const dir=path.resolve(directory);await mkdir(path.dirname(dir),{recursive:true});await mkdir(dir);
const jsonBudget={maxBytes:67108864,maxDepth:48,maxNodes:2000000};
const nativeBytes=await readFile(nativeFile),native=parseStrictJson(nativeBytes.toString('utf8'),jsonBudget);
assert.equal(native.schema,1);assert.equal(native.kind,'sphere-triangle-mesh-entry-sdk-packets');
assert.equal(native.fixtureCount,65);assert.ok(Array.isArray(native.fixtures));assert.equal(native.fixtures.length,65);
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:wasm}),m=runtime.native;
const prefix='_pp_sim_sphere_triangle_mesh_entry';
for(const suffix of ['_begin','_append','','_record','_last_mesh','_candidate'])assert.equal(typeof m[prefix+suffix],'function','Required raw entry C ABI export '+suffix);
runtime.check(m._pp_sim_reset());
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
function bits(x){assert.equal(typeof x,'number');assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0).toString(16).padStart(16,'0');}
function integer(x,maximum,label){assert.ok(Number.isSafeInteger(x)&&x>=0&&x<=maximum&&!Object.is(x,-0),label);return x;}
function flag(x,label){return integer(x,1,label);}
const packet=()=>Array.from(runtime.output());
const same=(a,b)=>a.length===b.length&&a.every((v,i)=>bits(v)===bits(b[i]));
const getter=(suffix,length,...args)=>{runtime.check(m[prefix+suffix](...args));const p=packet();assert.equal(p.length,length,'exact raw getter length');p.forEach(bits);return p;};
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a!==null&&typeof a==='object'){
  assert.ok(b!==null,label);assert.equal(Array.isArray(a),Array.isArray(b),label);
  assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);
  for(const key of Object.keys(a))compare(a[key],b[key],label+'.'+key);
 }else assert.equal(a,b,label);
}
const records=[];let accepted=0,hostRejected=0;
for(const expected of native.fixtures){
 assert.ok(Array.isArray(expected.input)&&expected.input.length===24);
 assert.ok(Array.isArray(expected.triangles)&&expected.triangles.length<=65);
 for(const triangle of expected.triangles)assert.ok(Array.isArray(triangle)&&triangle.length===10);
 const r={name:expected.name,input:[...expected.input],inputBits:expected.input.map(bits),
  triangles:expected.triangles.map(t=>[...t]),triangleBits:expected.triangles.map(t=>t.map(bits)),
  beginStatus:0,appendStatuses:[],exchangeStatus:0,failedPhase:null,
  summary:null,summaryBits:null,echo:null,echoBits:null,sources:[],sourceBits:[],
  audits:[],auditBits:[],leaves:[],leafBits:[],partition:[],partitionBits:[],frontier:[],frontierBits:[],
  current:null,currentBits:null,initial:null,initialBits:null,bestWitness:null,bestWitnessBits:null,
  window:null,windowBits:null,candidateIds:[],candidateIdBits:[],lastMeshSummary:null,lastMeshSummaryBits:null,lastMeshRows:[],
  outputBefore:packet(),outputBeforeBits:null,outputAfter:null,outputAfterBits:null,hostFailurePreserved:null};
 r.outputBeforeBits=r.outputBefore.map(bits);
 r.beginStatus=m[prefix+'_begin'](r.triangles.length);r.exchangeStatus=r.beginStatus;
 if(r.beginStatus!==0)r.failedPhase='begin';
 for(let offset=0;!r.failedPhase&&offset<r.triangles.length;offset+=6){
  const values=r.triangles.slice(offset,offset+6).flat();runtime.inputF64(values);
  r.exchangeStatus=m[prefix+'_append'](values.length);r.appendStatuses.push(r.exchangeStatus);
  if(r.exchangeStatus!==0)r.failedPhase='append';
 }
 if(!r.failedPhase){runtime.inputF64(r.input);r.exchangeStatus=m[prefix](24);if(r.exchangeStatus!==0)r.failedPhase='query';}
 if(!r.failedPhase){
  accepted++;r.summary=packet();assert.equal(r.summary.length,40);r.summaryBits=r.summary.map(bits);
  for(const i of [3,4,6,7,12,15,16,18,19,20,34])flag(r.summary[i],'entry header flag');
  r.echo=getter('_record',24,0,0);r.echoBits=r.echo.map(bits);
  for(const [key,rawKey,kind,count,maximum,length] of [
   ['sources','sourceBits',1,r.summary[2],64,14],['audits','auditBits',2,r.summary[11],256,64],
   ['leaves','leafBits',3,r.summary[8],128,6],['partition','partitionBits',4,r.summary[9],128,8],
   ['frontier','frontierBits',5,r.summary[10],128,4]]){
   integer(count,maximum,'entry bounded record count');
   for(let i=0;i<count;i++){const p=getter('_record',length,kind,i);r[key].push(p);r[rawKey].push(p.map(bits));}
  }
  for(const [key,kind,present,length] of [['current',6,r.summary[18],4],['initial',7,r.summary[6],6],
   ['bestWitness',8,r.summary[15],18],['window',9,r.summary[16],6]]){
   if(present){r[key]=getter('_record',length,kind,0);r[key+'Bits']=r[key].map(bits);}
  }
  const idCount=integer(r.summary[17],64,'entry conservative ID count');
  for(let i=0;i<idCount;i++){const p=getter('_record',2,10,i);r.candidateIds.push(p);r.candidateIdBits.push(p.map(bits));}
  if(r.summary[19]){
   r.lastMeshSummary=getter('_last_mesh',24,0,0);r.lastMeshSummaryBits=r.lastMeshSummary.map(bits);
   for(const source of r.sources)for(const i of [11,12,13])flag(source[i],'last mesh source flag');
   for(let rowOrdinal=0;rowOrdinal<r.sources.length;rowOrdinal++)if(r.sources[rowOrdinal][11]){
    const row={rowOrdinal,packet:null,bits:null,candidates:[],candidateBits:[]};
    if(r.sources[rowOrdinal][12]){
     row.packet=getter('_last_mesh',58,1,rowOrdinal);row.bits=row.packet.map(bits);
     const count=integer(row.packet[6],7,'last mesh candidate prefix count');
     for(let i=0;i<count;i++){const p=getter('_candidate',13,rowOrdinal,i);row.candidates.push(p);row.candidateBits.push(p.map(bits));}
    }r.lastMeshRows.push(row);
   }
  }
 }else{hostRejected++;r.hostFailurePreserved=same(r.outputBefore,packet());assert.equal(r.hostFailurePreserved,true);}
 r.outputAfter=packet();r.outputAfterBits=r.outputAfter.map(bits);compare(r,expected,r.name);records.push(r);
}
assert.equal(accepted,native.accepted);assert.equal(hostRejected,native.hostRejected);
const captured={schema:1,kind:native.kind,fixtureCount:records.length,accepted,hostRejected,fixtures:records};
const capturedText=stringifyStrictJson(captured,jsonBudget)+'\n';assert.ok(Buffer.byteLength(capturedText)<=jsonBudget.maxBytes,'complete raw stream budget includes final LF');
await writeFile(path.join(dir,'wasm-packets.json'),capturedText,{flag:'wx'});
const sha=x=>createHash('sha256').update(x).digest('hex');
const report={schema:1,status:'PASS',fixtures:records.length,accepted,hostRejected,numericBits,negativeZeroBits,
 sourceNativePackets:{bytes:nativeBytes.length,sha256:sha(nativeBytes)},wasm:{bytes:wasm.length,sha256:sha(wasm)},
 capturedPackets:{bytes:Buffer.byteLength(capturedText),sha256:sha(capturedText)},
 scope:'Actual shared WASM raw entry C ABI replay of all 65 frozen finite Native inputs and every owned record getter, with complete raw-wire numeric bit comparison. Public JavaScript owned entry wrapper is unimplemented; no model DTO reconstruction or mathematical validation is claimed here. Independent pure-result and original 65-input Fraction/negative checks are separate Python steps.'};
await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
