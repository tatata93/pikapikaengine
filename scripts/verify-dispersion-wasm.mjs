// Replay ORIGINAL input bits through the shipped common C++ ABI, not JS math.
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const path=process.argv[2];if(!path)throw new Error('usage: node scripts/verify-dispersion-wasm.mjs oracle.csv');
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const decode=x=>Buffer.from(x,'hex').readDoubleBE(),encode=x=>{const b=Buffer.alloc(8);b.writeDoubleBE(x);return b.toString('hex');};
const rows=(await readFile(path,'utf8')).trim().split(/\r?\n/).slice(1);assert.equal(rows.length,320);
let endpoints=0;
for(const [j,line]of rows.entries()){
  const cells=line.split(',');assert.equal(cells.length,15);assert.equal(Number(cells[0]),j);
  const [lo,hi,a,b,c,sb,sc]=cells.slice(2,9).map(decode);
  const kind=Number(cells[1]);assert.ok(kind===0||kind===1);
  const model=kind===0?{kind:'cauchy',coefficients:[a,b,c]}:{kind:'sellmeier',terms:[[sb,sc]]};
  const r=runtime.queryDispersion(model,[lo,hi]);assert.equal(r.status,'resolved');
  const bits=[...r.values.phase,...r.values.derivative,...r.values.group].map(encode);
  assert.deepEqual(bits,cells.slice(9),`input ${j}: endpoint bit difference`);endpoints+=bits.length;
}
console.log(JSON.stringify({cases:rows.length,exactEndpointBits:endpoints,backend:runtime.diagnostics.backend}));
