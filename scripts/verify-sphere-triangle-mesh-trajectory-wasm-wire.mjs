import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const [nativeFile,directory]=process.argv.slice(2);
if(!nativeFile||!directory)throw Error('Usage: node scripts/verify-sphere-triangle-mesh-trajectory-wasm-wire.mjs native-packets.json fresh-output-directory');
const dir=path.resolve(directory);await mkdir(dir,{recursive:true});
const jsonBudget={maxBytes:16777216,maxDepth:32,maxNodes:2000000};
const native=parseStrictJson(await readFile(nativeFile,'utf8'),jsonBudget);
assert.equal(native.schema,1);assert.equal(native.kind,'sphere-triangle-mesh-trajectory-sdk-packets');assert.equal(native.fixtureCount,62);assert.equal(native.fixtures.length,62);
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:wasm}),m=runtime.native;
const prefix='_pp_sim_sphere_triangle_mesh_trajectory';
const exports=['_begin','_append','','_record','_last_mesh','_candidate'];
for(const suffix of exports)assert.equal(typeof m[prefix+suffix],'function','Required new raw C ABI export '+suffix);
runtime.check(m._pp_sim_reset());
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0).toString(16).padStart(16,'0');};
const packet=()=>Array.from(runtime.output());
const same=(a,b)=>a.length===b.length&&a.every((v,i)=>bits(v)===bits(b[i]));
const getter=(suffix,...args)=>{runtime.check(m[prefix+suffix](...args));return packet();};
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
 else assert.equal(a,b,label);
}
const records=[];let accepted=0,hostRejected=0;
for(const expected of native.fixtures){
 const r={name:expected.name,input:[...expected.input],inputBits:expected.input.map(bits),triangles:expected.triangles.map(t=>[...t]),triangleBits:expected.triangles.map(t=>t.map(bits)),
  beginStatus:0,appendStatuses:[],exchangeStatus:0,failedPhase:null,summary:null,summaryBits:null,echo:null,echoBits:null,
  sources:[],sourceBits:[],audits:[],auditBits:[],leaves:[],leafBits:[],frontier:[],frontierBits:[],current:null,currentBits:null,witness:null,witnessBits:null,
  lastMeshSummary:null,lastMeshSummaryBits:null,lastMeshRows:[],outputBefore:packet(),outputBeforeBits:null,outputAfter:null,outputAfterBits:null,hostFailurePreserved:null};
 r.outputBeforeBits=r.outputBefore.map(bits);
 r.beginStatus=m[prefix+'_begin'](r.triangles.length);r.exchangeStatus=r.beginStatus;
 if(r.beginStatus!==0)r.failedPhase='begin';
 for(let offset=0;!r.failedPhase&&offset<r.triangles.length;offset+=6){
  const values=r.triangles.slice(offset,offset+6).flat();runtime.inputF64(values);
  r.exchangeStatus=m[prefix+'_append'](values.length);r.appendStatuses.push(r.exchangeStatus);if(r.exchangeStatus!==0)r.failedPhase='append';
 }
 if(!r.failedPhase){runtime.inputF64(r.input);r.exchangeStatus=m[prefix](24);if(r.exchangeStatus!==0)r.failedPhase='query';}
 if(!r.failedPhase){
  accepted++;r.summary=packet();r.summaryBits=r.summary.map(bits);assert.equal(r.summary.length,32);
  for(const index of [3,4,9,12,13,14,15,29])assert.ok(r.summary[index]===0||r.summary[index]===1,'header flag');
  r.echo=getter('_record',0,0);r.echoBits=r.echo.map(bits);
  for(const [field,bitField,kind,count,maximum]of [['sources','sourceBits',1,r.summary[2],64],['audits','auditBits',2,r.summary[8],255],['leaves','leafBits',3,r.summary[6],128],['frontier','frontierBits',4,r.summary[7],33]]){
   assert.ok(Number.isInteger(count)&&count>=0&&count<=maximum);
   for(let j=0;j<count;j++){const p=getter('_record',kind,j);r[field].push(p);r[bitField].push(p.map(bits));}
  }
  if(r.summary[13]){r.current=getter('_record',5,0);r.currentBits=r.current.map(bits);}
  if(r.summary[12]){r.witness=getter('_record',6,0);r.witnessBits=r.witness.map(bits);}
  if(r.summary[14]){
   r.lastMeshSummary=getter('_last_mesh',0,0);r.lastMeshSummaryBits=r.lastMeshSummary.map(bits);
   for(const source of r.sources)for(const index of [11,12,13])assert.ok(source[index]===0||source[index]===1,'last mesh source flag');
   for(let j=0;j<r.sources.length;j++)if(r.sources[j][11]){
    const row={rowOrdinal:j,packet:null,bits:null,candidates:[],candidateBits:[]};
    if(r.sources[j][12]){
     row.packet=getter('_last_mesh',1,j);row.bits=row.packet.map(bits);assert.equal(row.packet.length,58);
     assert.ok(Number.isInteger(row.packet[6])&&row.packet[6]>=0&&row.packet[6]<=7,'candidate count');
     for(let k=0;k<row.packet[6];k++){const p=getter('_candidate',j,k);row.candidates.push(p);row.candidateBits.push(p.map(bits));}
    }r.lastMeshRows.push(row);
   }
  }
 }else{hostRejected++;r.hostFailurePreserved=same(r.outputBefore,packet());assert.equal(r.hostFailurePreserved,true);}
 r.outputAfter=packet();r.outputAfterBits=r.outputAfter.map(bits);compare(r,expected,r.name);records.push(r);
}
const result={schema:1,kind:native.kind,fixtureCount:records.length,accepted,hostRejected,fixtures:records};
assert.equal(accepted,native.accepted);assert.equal(hostRejected,native.hostRejected);
await writeFile(path.join(dir,'wasm-packets.json'),stringifyStrictJson(result,jsonBudget)+'\n',{flag:'wx'});
const report={schema:1,status:'PASS',fixtures:records.length,accepted,hostRejected,numericBits,negativeZeroBits,
 wasm:{bytes:wasm.length,sha256:createHash('sha256').update(wasm).digest('hex')},
 scope:'Actual shared WASM raw C ABI replay of every finite Native probe input and all getters; full DTO/wire bit identity. Public owned JavaScript trajectory wrapper remains unimplemented. Independent pure-result comparison is a separate Python step.'};
await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
