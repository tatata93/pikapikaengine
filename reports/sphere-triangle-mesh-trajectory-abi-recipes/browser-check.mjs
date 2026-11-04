import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {evaluateMeshLab} from '../../tools/sphere-triangle-mesh-lab.mjs';
const root=new URL('../../',import.meta.url);
const path=new URL('reports/sphere-triangle-mesh-trajectory-abi-public-browser/mesh-default.json',root);
const packet=parseStrictJson(await readFile(path,'utf8'));
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))});
const expected=evaluateMeshLab(runtime,packet.input),view=new DataView(new ArrayBuffer(8));
let numericBits=0,negativeZeroBits=0;
function bits(x){assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);}
function compare(a,b){
 assert.equal(typeof a,typeof b);
 if(typeof a==='number'){assert.equal(bits(a),bits(b));numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort());for(const key of Object.keys(a))compare(a[key],b[key]);}
 else assert.equal(a,b);
}
compare(packet.input,expected.input);compare(packet.result,expected.result);
assert.equal(packet.result.status,'completed');assert.equal(packet.diagnostics.wasmBytes,674978);
const report={schema:1,status:'PASS',commit:'7a8300b7a39b981f44f4720e6b88f701f46ab4f2',numericBits,negativeZeroBits,modelPackets:1,scope:'Existing mesh lab default input from actual visible public DOM compared bitwise against common WASM. New trajectory guard has raw C ABI exports; owned JS wrapper remains unimplemented. Original proof SVG visually checked; no new game-contact or full lab preset claim.'};
await writeFile(new URL('reports/sphere-triangle-mesh-trajectory-abi-public-browser-verification.json',root),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
