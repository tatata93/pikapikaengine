// Compare complete visible browser output; no hidden application state.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
const phase=process.argv[2];assert.ok(['local','public'].includes(phase));
const root=new URL('../../',import.meta.url),dir=new URL(`reports/sphere-triangle-mesh-entry-js-${phase}-browser/`,root);
const budget={maxBytes:16777216,maxDepth:32,maxNodes:1000000};
const packet=parseStrictJson(await readFile(new URL('owned-case.json',dir),'utf8'),budget);
const pure=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',root),'utf8'),budget);
const fixture=pure.fixtures.find(f=>f.name==='analytic-entry-quarter'),q=fixture.input;
const wasm=await readFile(new URL('assets/pikapika-simulation.wasm',root));
const runtime=await loadSimulationRuntime({wasmBytes:wasm});
const expected=runtime.querySphereTriangleMeshEntry({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const singleStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const singleReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'];
const dispositions=['retained','outside_simplex','kkt_violated'];
const relations=['separated','penetrating','touching','boundary_unresolved'];
function ordinal(value,choices,label){assert.equal(typeof value,'string',label);const index=choices.indexOf(value);assert.ok(index>=0,label);return index;}
function projectSingle(result){
 return {...result,status:ordinal(result.status,singleStatuses,'single status'),reason:ordinal(result.reason,singleReasons,'single reason'),
  geometry:result.geometry===null?null:{...result.geometry,relation:ordinal(result.geometry.relation,relations,'relation')},
  candidates:result.candidates.map(c=>({...c,feature:ordinal(c.feature,features,'candidate feature'),disposition:ordinal(c.disposition,dispositions,'candidate disposition')}))};
}
function projectMesh(result){
 return {...result,status:ordinal(result.status,meshStatuses,'mesh status'),reason:ordinal(result.reason,meshReasons,'mesh reason'),
  rows:result.rows.map(row=>({...row,query:row.query===null?null:projectSingle(row.query)}))};
}
function project(result){
 assert.ok(result&&typeof result==='object'&&!Array.isArray(result));
 const {originalInput,...model}=result;
 assert.ok(originalInput&&typeof originalInput==='object');
 return {...model,audits:model.audits.map(a=>({...a,
  meshStatus:a.meshStatus===null?null:ordinal(a.meshStatus,meshStatuses,'audit mesh status'),
  meshReason:a.meshReason===null?null:ordinal(a.meshReason,meshReasons,'audit mesh reason')})),
  lastMesh:model.lastMesh===null?null:projectMesh(model.lastMesh)};
}
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);};
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
 else assert.equal(a,b,label);
}
assert.equal(packet.schema,1);assert.equal(packet.kind,'sphere-triangle-mesh-entry-owned-browser-proof');
compare(packet.input,q,'browser input');compare(packet.result,expected,'browser full owned DTO');
const browserBits={numericBits,negativeZeroBits};
const model=project(packet.result);numericBits=0;negativeZeroBits=0;compare(model,fixture.result,'browser model vs pinned Native');
const nativeBits={numericBits,negativeZeroBits};
const html=await readFile(new URL('index.html',root),'utf8'),build=html.match(/\?build=([a-f0-9]{16})/)[1];
assert.equal(packet.diagnostics.wasmBytes,719410);assert.equal(packet.diagnostics.buildId,build);
assert.equal(packet.result.status,'entry_window');assert.equal(packet.result.audits.length,61);assert.equal(packet.result.partition.length,41);
const game=parseStrictJson(await readFile(new URL('game-cover-report.json',dir),'utf8'),budget),state=await readFile(new URL('game-state.txt',dir),'utf8');
assert.equal(game.state,'ready');assert.equal(game.failure,null);assert.deepEqual(game.errors,[]);
assert.ok(game.counts.queries>0);assert.equal(game.counts.queries,game.counts.checked);assert.equal(game.counts.queries,game.counts.validated);
assert.ok(game.records.length>0&&game.records.every(r=>r.state==='completed'));assert.ok(game.records.some(r=>r.clipSeconds===1));
assert.equal(game.renderer.residentMeshes,3);assert.equal(game.renderer.lost,false);
assert.equal(game.startup.diagnostics.wasmBytes,719410);assert.equal(game.startup.diagnostics.buildId,build);
assert.match(state,/一時停止 \/ Pで再開/);const kills=Number(state.match(/撃破 (\d+)/)[1]);assert.ok(kills>0);
const report={schema:1,status:'PASS',phase,wasmBytes:719410,buildId:build,
 entry:{...browserBits,nativeModel:nativeBits,status:packet.result.status,audits:61,partition:41},
 game:{paused:true,kills,coverQueries:game.counts.queries,allCompleted:true,boostClip1Observed:true,residentMeshes:3},
 scope:'One actual fixed browser API call, complete visible input/owned DTO vs Node and model vs pinned Native bits. Existing original game combat/boost/pause and visible cover diagnostics are a regression; entry windows are not used for game contacts. Full65 mathematics, 62 actual decoded models/3 declared supplements remain separately checked.'};
await writeFile(new URL(`reports/sphere-triangle-mesh-entry-js-${phase}-browser-verification.json`,root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
