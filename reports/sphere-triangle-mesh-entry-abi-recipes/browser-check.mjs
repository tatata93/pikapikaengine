// Compare visible browser data to the current real SDK; never inspect hidden app state.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {trajectoryLabPresets,trajectoryLabPreset} from '../../tools/sphere-triangle-mesh-trajectory-lab.mjs';
const root=new URL('../../',import.meta.url),phase=process.argv[2];assert.ok(['local','public'].includes(phase));
const prefix='sphere-triangle-mesh-entry-abi',dir=new URL(`reports/${prefix}-${phase}-browser/`,root);
const read=async name=>parseStrictJson(await readFile(new URL(name,dir),'utf8'),{maxBytes:16777216,maxDepth:32,maxNodes:1000000});
const wasm=await readFile(new URL('assets/pikapika-simulation.wasm',root)),runtime=await loadSimulationRuntime({wasmBytes:wasm});
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.ok(Number.isFinite(a)&&Number.isFinite(b),label);view.setFloat64(0,a);const bits=view.getBigUint64(0);view.setFloat64(0,b);assert.equal(bits,view.getBigUint64(0),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
 else assert.equal(a,b,label);
}
const p=await read('guard-default.json'),q=p.input;
assert.equal(p.kind,'sphere-triangle-mesh-trajectory-lab');assert.equal(p.schema,1);
compare(q,trajectoryLabPreset(trajectoryLabPresets[0].name),'existing guard default input');
compare(p.result,runtime.querySphereTriangleMeshTrajectory({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings),'existing guard full owned DTO');
assert.equal(p.result.status,'separated');assert.equal(p.diagnostics.wasmBytes,wasm.length);assert.equal(p.diagnostics.buildId,'7999d8fe99c1f44d');
const game=await read('game-cover-report.json'),state=await readFile(new URL('game-state.txt',dir),'utf8');
assert.equal(game.state,'ready');assert.equal(game.failure,null);assert.deepEqual(game.errors,[]);
assert.ok(game.counts.queries>0);assert.equal(game.counts.queries,game.counts.checked);assert.equal(game.counts.queries,game.counts.validated);
assert.ok(game.records.length>0&&game.records.every(r=>r.state==='completed'));assert.ok(game.records.some(r=>r.clipSeconds===1));
assert.equal(game.renderer.residentMeshes,3);assert.equal(game.renderer.lost,false);
assert.equal(game.startup.diagnostics.wasmBytes,wasm.length);assert.equal(game.startup.diagnostics.buildId,'7999d8fe99c1f44d');
assert.match(state,/一時停止 \/ Pで再開/);const kills=Number(state.match(/撃破 (\d+)/)[1]);assert.ok(kills>0);
const report={schema:1,status:'PASS',phase,wasmBytes:wasm.length,buildId:p.diagnostics.buildId,guardDefault:{numericBits,negativeZeroBits,status:p.result.status},game:{paused:true,kills,coverQueries:game.counts.queries,allCompleted:true,boostClip1Observed:true,residentMeshes:3,scope:'Counters are cumulative across the diagnostic session, including any restart. Existing decorative cover/robot gameplay only; entry windows are not applied to game contacts.'},scope:'Actual visible old guard default input/full owned DTO matched bit-for-bit to current Node/WASM; actual game shooting/movement/boost/kills/pause and displayed cover report checked. New entry raw ABI is independently verified in separate Native/Node packet runs; no public owned entry JS/UI claimed.'};
await writeFile(new URL(`reports/${prefix}-${phase}-browser-verification.json`,root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
