// Check actual public ABI mapping against independently verified native packets.
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const input=process.argv[2];if(!input)throw new Error('usage: verify-optical-geometry-wasm.mjs native.csv [report.json]');
const corpus=await readFile(input),rows=corpus.toString('utf8').trim().split(/\r?\n/);
assert.equal(rows.length,200,'complete native geometry corpus');
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
const view=new DataView(new ArrayBuffer(8));
const decode=text=>{view.setBigUint64(0,BigInt('0x'+text));return view.getFloat64(0);};
const bits=value=>{view.setFloat64(0,value);return view.getBigUint64(0);};
let matchingBoundBits=0;
for(const [i,row]of rows.entries()){
  const c=row.split(',');assert.equal(c.length,37);const v=c.slice(1,17).map(decode);
  const kind={P:0,S:1,C:2}[c[0]];assert.notEqual(kind,undefined);
  const count=runtime.inputF64([kind,...v,1e-8,128]);runtime.check(runtime.native._pp_sim_optical_geometry(count));const a=runtime.output();assert.equal(a.length,52);
  for(const [offset,column]of [[0,17],[1,18],[3,19],[4,20],[2,21],[12,26],[16,27],[51,36]])assert.equal(a[offset],Number(c[column]),`row${i} field${offset}`);
  const actual=[a[10],a[11],a[14],a[15],...a.slice(22,28),a[20],a[21]];
  const expected=[...c.slice(22,26),...c.slice(28,36)];
  for(let j=0;j<actual.length;++j){assert.equal(bits(actual[j]),BigInt('0x'+expected[j]),`row${i} certificate${j}`);++matchingBoundBits;}
}
const result={verification:'Native optical geometry input/certificate bits through actual public WASM ABI',rows:rows.length,matchingBoundBits,
  corpusSha256:createHash('sha256').update(corpus).digest('hex'),wasmBytes:runtime.wasmBytes,
  limits:'Packet/certificate mapping parity. Independent Fraction correctness is checked by verify-optical-geometry.py; approximate points/normals are not required bit identical.'};
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
