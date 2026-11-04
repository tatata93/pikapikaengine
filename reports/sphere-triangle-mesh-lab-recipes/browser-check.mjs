import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs';
import {evaluateMeshLab,meshLabPreset,meshLabPresets} from '../../tools/sphere-triangle-mesh-lab.mjs';
const root=new URL('../../',import.meta.url),phase=process.argv[2];assert.ok(['local','public'].includes(phase));
const dir=new URL(`reports/sphere-triangle-mesh-lab-${phase}-browser/`,root),budget={maxBytes:4194304,maxDepth:20,maxNodes:200000};
const read=async name=>parseStrictJson(await readFile(new URL(name,dir),'utf8'),budget);
const r=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))}),view=new DataView(new ArrayBuffer(8));
let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);};
function compare(a,b,label){assert.equal(typeof a,typeof b,label);if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}else assert.equal(a,b,label);}
const rows=await read('presets.json');assert.deepEqual(rows.map(x=>x.name),meshLabPresets.map(x=>x.name));let completed=0,failed=0,rejected=0;const modelPackets=[];
for(const row of rows){
 if(row.name==='capacity65'){assert.throws(()=>evaluateMeshLab(r,meshLabPreset(row.name)),/at most 64/);assert.equal(row.packetBytes,0);assert.equal(row.rows,0);assert.equal(row.canSave,false);assert.match(row.error,/SDK/);rejected++;continue;}
 const packet=await read(row.name+'.json'),expected=evaluateMeshLab(r,meshLabPreset(row.name));assert.equal(packet.kind,'sphere-triangle-mesh-lab');compare(packet.input,expected.input,row.name+'.input');compare(packet.result,expected.result,row.name+'.result');assert.equal(packet.diagnostics.wasmBytes,638777);assert.equal(row.rows,packet.input.triangles.length);assert.equal(row.canSave,true);if(packet.result.status==='completed')completed++;else{assert.equal(packet.result.nearest,null);failed++;}modelPackets.push({name:row.name,packet});
}
assert.equal(completed,10);assert.equal(failed,6);assert.equal(rejected,1);
for(const name of ['edited-signed-zero','retry-signed-zero','failure-last-row','capacity64-last-row-xy','capacity64-last-row-yz']){
 const packet=await read(name+'.json'),expected=evaluateMeshLab(r,packet.input);compare(packet.input,expected.input,name+'.input');compare(packet.result,expected.result,name+'.result');modelPackets.push({name,packet});
 if(name.includes('signed-zero')){assert.ok(Object.is(packet.input.sphere.position[0],-0));assert.ok(Object.is(packet.input.sphere.position[2],-0));assert.equal(packet.input.sphere.radius,1);}
 if(name.includes('capacity64')){assert.equal(packet.inspectedOrdinal,63);assert.equal(packet.inspectedSurfaceId,64);assert.equal(packet.result.rows[63].query.candidates.length,7);assert.equal(packet.result.nearest.possibleSurfaceIds.length,64);}
}
for(const [download,display]of [['failure-download.json','failure-last-row.json'],['capacity64-download.json','capacity64-last-row-yz.json']]){const a=await readFile(new URL(download,dir)),b=await readFile(new URL(display,dir));assert.deepEqual(a,b,download+' exact displayed bytes');compare(await read(download),await read(display),download+'.full DTO');}
const actions=await read('actions.json');const edit=actions.find(x=>x.action==='edit-clears');assert.deepEqual({...edit},{action:'edit-clears',json:'',geometry:'—',candidates:'—',svg:'',rows:0,save:false});const bad=actions.find(x=>x.action==='id-zero-rejected');assert.equal(bad.save,false);assert.equal(bad.json,'');assert.match(bad.error,/SDK/);const diagnostic=actions.find(x=>x.action==='failure-keeps-last-row-diagnostic');assert.match(diagnostic.geometry,/"aggregateNearestAvailable": false/);assert.match(diagnostic.geometry,/"status": "completed"/);assert.match(diagnostic.note,/nearest.*ありません/);
// Preserve every browser numerical bit for an independent rational replay.
const statuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const reasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const features=['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c'],dispositions=['retained','outside_simplex','kkt_violated'],relations=['separated','penetrating','touching','boundary_unresolved'];
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'],meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const primitive=q=>({...q,status:statuses.indexOf(q.status),reason:reasons.indexOf(q.reason),geometry:q.geometry?{...q.geometry,relation:relations.indexOf(q.geometry.relation)}:null,candidates:q.candidates.map(c=>({...c,feature:features.indexOf(c.feature),disposition:dispositions.indexOf(c.disposition)}))});
const replay=modelPackets.map(({name,packet:p})=>({name:'browser-'+phase+'-'+name,input:{...p.input,sphere:{center:p.input.sphere.position,radius:p.input.sphere.radius}},result:{...p.result,status:meshStatuses.indexOf(p.result.status),reason:meshReasons.indexOf(p.result.reason),rows:p.result.rows.map(row=>({...row,query:row.query?primitive(row.query):null}))}}));
await writeFile(new URL('replay.json',dir),stringifyStrictJson({schema:1,kind:'sphere-triangle-mesh-fixtures',fixtures:replay},budget)+'\n');
const report={schema:1,status:'PASS',phase,presets:17,completed,expectedModelFailures:failed,expectedHostRejections:rejected,actualBrowserModelPackets:modelPackets.length,numericBits,negativeZeroBits,downloads:'exact display bytes and full DTO numeric bits',scope:'Visible DOM input/result checked against actual common WASM, every preset, edits, retry, projections, 64th row and two real Blob downloads; no browser performance equivalence claim.'};
await writeFile(new URL(`reports/sphere-triangle-mesh-lab-${phase}-browser-verification.json`,root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
