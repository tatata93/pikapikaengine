import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {evaluateTriangleLab} from '../../tools/sphere-triangle-lab.mjs';
const root=new URL('../../',import.meta.url);
const packet=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-sdk-public-browser/single-default-packet.json',root),'utf8'));
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))});
const expected=evaluateTriangleLab(runtime,packet.input),view=new DataView(new ArrayBuffer(8));let numericBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);};
function compare(a,b){
  assert.equal(typeof a,typeof b);
  if(typeof a==='number'){assert.equal(bits(a),bits(b));numericBits++;}
  else if(a&&typeof a==='object'){assert.ok(b!==null);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort());for(const k of Object.keys(a))compare(a[k],b[k]);}
  else assert.equal(a,b);
}
compare(packet.input,expected.input);compare(packet.result,expected.result);
const cover=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-sdk-public-browser/cover.json',root),'utf8'));
assert.equal(cover.state,'ready');assert.equal(cover.failure,null);assert.equal(cover.pending,null);assert.deepEqual(cover.errors,[]);
assert.equal(cover.startup.diagnostics.wasmBytes,638777);assert.equal(cover.startup.diagnostics.buildId,'1f40cf023bb8472f');
assert.equal(cover.counts.queries,21);assert.equal(cover.counts.checked,21);assert.equal(cover.counts.validated,21);assert.equal(cover.renderer.residentMeshes,3);
assert.ok(cover.records.every(r=>r.state==='completed')&&cover.records.some(r=>r.clipSeconds===1));
assert.equal(packet.diagnostics.wasmBytes,638777);assert.equal(packet.diagnostics.buildId,'1f40cf023bb8472f');
const report={status:'PASS',publicSingleLabInputAndResultNumericBits:numericBits,coverQueries:21,allCompleted:true,residentMeshes:3,fullOpenObservedInRecords:true,scope:'Published existing game and single-face lab compatibility; no mesh-contact integration or timing equivalence claim.'};
await writeFile(new URL('reports/sphere-triangle-mesh-sdk-browser-verification.json',root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
