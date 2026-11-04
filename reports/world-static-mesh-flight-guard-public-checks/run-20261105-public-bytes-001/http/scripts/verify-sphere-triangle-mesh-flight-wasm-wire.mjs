// Actual main-WASM raw flight C ABI, with owned packets and no JS solver.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const [nativeFile,outDir,...extra]=process.argv.slice(2);
if(!nativeFile||!outDir||extra.length)throw Error('Usage: node verify-sphere-triangle-mesh-flight-wasm-wire.mjs native-packets.json fresh-output-directory');
const dir=path.resolve(outDir);await mkdir(path.dirname(dir),{recursive:true});await mkdir(dir);
const budget={maxBytes:67108864,maxDepth:64,maxNodes:4000000};
const nativeBytes=await readFile(nativeFile),native=parseStrictJson(nativeBytes.toString('utf8'),budget);
assert.equal(native.schema,1);assert.equal(native.kind,'sphere-triangle-mesh-flight-sdk-packets');
assert.equal(native.fixtureCount,183);assert.equal(native.fixtures.length,183);
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:wasm}),m=runtime.native;
const prefix='_pp_sim_sphere_triangle_mesh_flight';
for(const suffix of ['_begin','_append','_query','_record','_last_mesh','_candidate'])assert.equal(typeof m[prefix+suffix],'function','Required flight export '+suffix);
const bitView=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.equal(typeof x,'number');assert.ok(Number.isFinite(x));bitView.setFloat64(0,x);return bitView.getBigUint64(0).toString(16).padStart(16,'0');};
const integer=(x,max,label)=>{assert.ok(Number.isSafeInteger(x)&&x>=0&&x<=max&&!Object.is(x,-0),label);return x;};
const flag=x=>integer(x,1,'canonical flag');
const same=(a,b)=>a.length===b.length&&a.every((x,i)=>bits(x)===bits(b[i]));
const packet=()=>Array.from(runtime.output());
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a!==null&&typeof a==='object'){
  assert.ok(b!==null,label);assert.equal(Array.isArray(a),Array.isArray(b),label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);
  for(const key of Object.keys(a))compare(a[key],b[key],label+'.'+key);
 }else assert.equal(a,b,label);
}
const heap={initialCapacityBytes:m.HEAPU8.byteLength,maximumCapacityBytes:m.HEAPU8.byteLength,finalCapacityBytes:null,
 bufferChanges:0,viewChecks:0,usedHeapBytes:null,stackHighWaterBytes:null,memoryGrowthExercised:false,
 limitation:'Heap capacity is not allocation usage. No stack watermark or allocator-used-byte export is present; fixed-corpus growth may remain untriggered.'};
let lastBuffer=m.HEAPU8.buffer;
function observeHeap(){
 assert.equal(m.HEAPF64.buffer,m.HEAPU8.buffer);assert.equal(m.HEAPU32.buffer,m.HEAPU8.buffer);heap.viewChecks++;
 heap.maximumCapacityBytes=Math.max(heap.maximumCapacityBytes,m.HEAPU8.byteLength);
 if(lastBuffer!==m.HEAPU8.buffer){heap.bufferChanges++;lastBuffer=m.HEAPU8.buffer;}
}
function call(suffix,...args){const code=m[prefix+suffix](...args);observeHeap();return code;}
function getter(suffix,length,...args){runtime.check(call(suffix,...args));const p=packet();assert.equal(p.length,length);p.forEach(bits);return p;}
function plan(summary,h){
 const lengths=[summary[0]===0?32:48,14,summary[0]===0?32:48,48,32,32,24,40,32,8,8,8,64,6,8,4,4,6,18,14,2];
 const counts=[1,integer(summary[3],64,'source count'),flag(summary[4]),flag(summary[15]),h?flag(h[3]):0,
  flag(summary[7]),flag(summary[8]),flag(summary[12]),flag(summary[14]),h?flag(h[7]):0,h?flag(h[8]):0,h?flag(h[9]):0,
  h?integer(h[15],256,'audit count'):0,h?integer(h[12],128,'leaf count'):0,h?integer(h[13],128,'partition count'):0,
  h?integer(h[14],128,'frontier count'):0,h?flag(h[22]):0,h?flag(h[10]):0,h?flag(h[19]):0,h?flag(h[20]):0,h?integer(h[21],64,'ID count'):0];
 return counts.map((count,kind)=>({kind,count,length:lengths[kind]}));
}
runtime.check(m._pp_sim_reset());observeHeap();
const records=[];let accepted=0,hostRejected=0;
for(const expected of native.fixtures){
 assert.ok(expected.mode===0||expected.mode===1);assert.equal(expected.input.length,expected.mode===0?32:48);
 const row={cohort:expected.cohort,name:expected.name,mode:expected.mode,input:[...expected.input],inputBits:expected.input.map(bits),
  triangles:expected.triangles.map(x=>[...x]),triangleBits:expected.triangles.map(x=>x.map(bits)),
  beginStatus:0,appendStatuses:[],exchangeStatus:0,failedPhase:null,hostFailurePreserved:null,
  summary:null,summaryBits:null,packets:[],lastMeshSummary:null,lastMeshSummaryBits:null,lastMeshRows:[],
  outputBefore:packet(),outputBeforeBits:null,outputAfter:null,outputAfterBits:null};
 row.outputBeforeBits=row.outputBefore.map(bits);
 row.beginStatus=call('_begin',row.mode,row.triangles.length);row.exchangeStatus=row.beginStatus;
 if(row.exchangeStatus!==0)row.failedPhase='begin';
 for(let i=0;!row.failedPhase&&i<row.triangles.length;i+=6){
  const values=row.triangles.slice(i,i+6).flat();runtime.inputF64(values);row.exchangeStatus=call('_append',row.mode,values.length);row.appendStatuses.push(row.exchangeStatus);
  if(row.exchangeStatus!==0)row.failedPhase='append';
 }
 if(!row.failedPhase){runtime.inputF64(row.input);row.exchangeStatus=call('_query',row.mode,row.input.length);if(row.exchangeStatus!==0)row.failedPhase='query';}
 if(row.failedPhase){hostRejected++;row.hostFailurePreserved=same(row.outputBefore,packet());assert.equal(row.hostFailurePreserved,true);}
 else{
  accepted++;row.summary=packet();assert.equal(row.summary.length,24);row.summaryBits=row.summary.map(bits);
  // Read original kinds 0..3 first. The header is needed for later cardinalities.
  let h=null;
  for(let kind=0;kind<=3;kind++){
   const count=kind===0?1:kind===1?integer(row.summary[3],64,'N'):kind===2?flag(row.summary[4]):flag(row.summary[15]);
   for(let index=0;index<count;index++){
    const length=kind===0||kind===2?row.input.length:kind===1?14:48;
    const values=getter('_record',length,row.mode,kind,index);row.packets.push({kind,index,values,bits:values.map(bits)});if(kind===3)h=values;
   }
  }
  for(const {kind,count,length} of plan(row.summary,h).slice(4))for(let index=0;index<count;index++){
   const values=getter('_record',length,row.mode,kind,index);row.packets.push({kind,index,values,bits:values.map(bits)});
  }
  if(h&&flag(h[23])){
   row.lastMeshSummary=getter('_last_mesh',24,row.mode,0,0);row.lastMeshSummaryBits=row.lastMeshSummary.map(bits);
   const sources=row.packets.filter(p=>p.kind===1).map(p=>p.values);
   for(let i=0;i<sources.length;i++)if(flag(sources[i][11])){
    const item={rowOrdinal:i,packet:null,bits:null,candidates:[],candidateBits:[]};
    if(flag(sources[i][12])){
     item.packet=getter('_last_mesh',58,row.mode,1,i);item.bits=item.packet.map(bits);
     for(let c=0;c<integer(item.packet[6],7,'candidate count');c++){const p=getter('_candidate',13,row.mode,i,c);item.candidates.push(p);item.candidateBits.push(p.map(bits));}
    }row.lastMeshRows.push(item);
   }
  }
 }
 row.outputAfter=packet();row.outputAfterBits=row.outputAfter.map(bits);compare(row,expected,row.cohort+'/'+row.name);records.push(row);
}
assert.equal(accepted,native.accepted);assert.equal(hostRejected,native.hostRejected);
const captured={schema:1,kind:native.kind,fixtureCount:records.length,accepted,hostRejected,fixtures:records};
const raw=stringifyStrictJson(captured,budget)+'\n';assert.ok(Buffer.byteLength(raw)<=budget.maxBytes);
await writeFile(path.join(dir,'wasm-packets.json'),raw,{flag:'wx'});

// These controls execute AFTER capture, so they cannot alter the recorded chain.
const controls=[];
function rejected(label,action){const before=packet(),code=action();assert.notEqual(code,0,label);assert.ok(same(before,packet()),label+' retains output/count');controls.push({label,status:'PASS',exchangeStatus:code});}
const echoes=[getter('_record',32,0,0,0),getter('_record',48,1,0,0)];
for(const mode of [0,1]){
 rejected('invalid mode begin '+mode,()=>call('_begin',2,1));
 rejected('invalid record kind '+mode,()=>call('_record',mode,21,0));
 rejected('invalid record index '+mode,()=>call('_record',mode,0,1));
 rejected('invalid last-mesh part '+mode,()=>call('_last_mesh',mode,2,0));
 rejected('invalid candidate row '+mode,()=>call('_candidate',mode,64,0));
 assert.ok(same(getter('_record',echoes[mode].length,mode,0,0),echoes[mode]));
}
const two=records.find(r=>r.mode===0&&r.exchangeStatus===0&&r.triangles.length===2);
assert.ok(two,'actual two-surface source for atomic staging control');
runtime.check(call('_begin',0,2));runtime.inputF64(two.triangles[0]);runtime.check(call('_append',0,10));
const bad=[...two.triangles[1]];bad[0]=0;runtime.inputF64(bad);rejected('append invalid ID atomically retains staged prefix',()=>call('_append',0,10));
runtime.inputF64(two.triangles[1]);runtime.check(call('_append',0,10));
const reserved=[...two.input];reserved[31]=-0;runtime.inputF64(reserved);rejected('reserved negative zero rejected without consuming stage',()=>call('_query',0,32));
runtime.inputF64(two.input);runtime.check(call('_query',0,32));assert.ok(same(packet(),two.summary));
assert.ok(same(getter('_record',48,1,0,0),echoes[1]),'other mode snapshot remains independent');
controls.push({label:'valid staging, failed append/query recovery and mode independence',status:'PASS'});
const ownedFirst=records[0].packets[0].values,ownedBits=ownedFirst.map(bits);
m.HEAPF64.fill(0,m._pp_sim_input_f64_ptr()/8,m._pp_sim_input_f64_ptr()/8+48);
assert.deepEqual(ownedFirst.map(bits),ownedBits,'owned packet survives scratch mutation');
runtime.check(m._pp_sim_reset());observeHeap();assert.equal(packet().length,0);
for(const mode of [0,1])rejected('reset removes mode record '+mode,()=>call('_record',mode,0,0));
heap.finalCapacityBytes=m.HEAPU8.byteLength;heap.memoryGrowthExercised=heap.bufferChanges>0;
const sha=x=>createHash('sha256').update(x).digest('hex');
const report={schema:1,status:'PASS',fixtures:records.length,accepted,hostRejected,numericBits,negativeZeroBits,controls,
 memory:heap,sourceNativePackets:{bytes:nativeBytes.length,sha256:sha(nativeBytes)},wasm:{bytes:wasm.length,sha256:sha(wasm)},
 capturedPackets:{bytes:Buffer.byteLength(raw),sha256:sha(raw)},
 scope:'Actual raw main-WASM flight family. Complete Native packet/bit comparison; separate Python decodes these captured packets and runs Fraction references only on accepted models. No JS geometric/math fallback, no owned public API/UI/World response. Heap capacity/view observations do not establish allocator usage or stack highwater.'};
await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
