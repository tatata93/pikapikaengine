import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
const phase=process.argv[2];assert.ok(['local','public'].includes(phase));
const root=new URL('../../',import.meta.url),budget={maxBytes:16777216,maxDepth:32,maxNodes:1000000};
const packet=parseStrictJson(await readFile(new URL(`reports/sphere-triangle-mesh-trajectory-js-${phase}-browser/owned-case.json`,root),'utf8'),budget);
const source=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root/native-fixtures.json',root),'utf8'),budget);
const fixture=source.fixtures.find(row=>row.name==='short-safe-linear');assert.ok(fixture);
assert.equal(packet.schema,1);assert.equal(packet.kind,'sphere-triangle-mesh-trajectory-js-browser-proof');assert.equal(packet.fixture,fixture.name);
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))});
const q=fixture.input,expected=runtime.querySphereTriangleMeshTrajectory({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);};
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const key of Object.keys(a))compare(a[key],b[key],label+'.'+key);}
 else assert.equal(a,b,label);
}
compare(packet.input,q,'actual browser input');compare(packet.result,expected,'actual browser owned DTO');
assert.equal(packet.result.status,'separated');assert.deepEqual(packet.result.safePrefix,[0,1]);assert.equal(packet.result.audits.length,1);
assert.equal(packet.diagnostics.wasmBytes,674978);assert.equal(packet.diagnostics.buildId,'7f0cfa4ee56be1ca');
const report={schema:1,status:'PASS',phase,modelCalls:1,numericBits,negativeZeroBits,wasmBytes:674978,webBuild:'7f0cfa4ee56be1ca',
 scope:'One fixed original browser example actually executes the public owned JS method; its complete visible input and owned DTO match Node using the same shared WASM bitwise. Full59 Native-DTO and mixed62 rational acceptance remain separate, with host3 supplements declared.'};
await writeFile(new URL(`reports/sphere-triangle-mesh-trajectory-js-${phase}-browser-verification.json`,root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
