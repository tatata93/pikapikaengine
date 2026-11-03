// Verify the public C ABI's classification/interval mapping using native input
// bits. The independent Fraction verifier checks those native certificates too.
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const input=process.argv[2];if(!input)throw new Error('usage: verify-optics-wasm.mjs native-oracle.csv [report.json]');
const corpus=await readFile(input),rows=corpus.toString('utf8').trim().split(/\r?\n/);
assert.equal(rows.length,1029,'complete native optics oracle corpus');
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const view=new DataView(new ArrayBuffer(8));
const decode=text=>{view.setBigUint64(0,BigInt('0x'+text));return view.getFloat64(0);};
const bits=value=>{view.setFloat64(0,value);return view.getBigUint64(0);};
const kinds=['transmission','total_internal_reflection','uncertain'],reasons=['none','incident_side','critical_angle','numerical_output'];
let bounds=0;
for(const [i,row]of rows.entries()){
  const columns=row.split(',');assert.equal(columns.length,14);
  const v=columns.slice(0,8).map(decode),r=runtime.queryDielectricInterface({incident:v.slice(0,3),normal:v.slice(3,6),indexIncident:v[6],indexTransmitted:v[7]});
  assert.equal(r.kind,kinds[Number(columns[12])],`row${i} kind`);assert.equal(r.uncertainty,reasons[Number(columns[13])],`row${i} reason`);
  for(const [j,value]of [...r.discriminant,...r.incidentDot].entries()){
    assert.equal(bits(value),BigInt('0x'+columns[8+j]),`row${i} bound${j}`);bounds++;
  }
  if(r.kind==='uncertain')assert.ok(r.transmitted===null&&r.power===null&&r.cosineTransmitted===null);
}
const result={verification:'Native oracle input bits through actual public WASM optical ABI',rows:rows.length,matchingBoundBits:bounds,corpusSha256:createHash('sha256').update(corpus).digest('hex'),wasmBytes:runtime.wasmBytes,note:'Classification and interval mapping parity; directions and power are numerical estimates, tested independently elsewhere.'};
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
