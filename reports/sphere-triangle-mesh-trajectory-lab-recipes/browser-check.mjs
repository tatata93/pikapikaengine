import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {trajectoryLabPresets,trajectoryLabPreset} from '../../tools/sphere-triangle-mesh-trajectory-lab.mjs';
const root=new URL('../../',import.meta.url),phase=process.argv[2];assert.ok(['local','public'].includes(phase));
const dir=new URL(`reports/sphere-triangle-mesh-trajectory-lab-${phase}-browser/`,root),budget={maxBytes:16777216,maxDepth:32,maxNodes:1000000};
const read=async name=>parseStrictJson(await readFile(new URL(name,dir),'utf8'),budget);
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))});
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);};
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
 else assert.equal(a,b,label);
}
const rows=await read('presets.json');assert.deepEqual(rows.map(row=>row.name),trajectoryLabPresets.map(row=>row.name));
let models=0,hostRejected=0,separated=0,witness=0,failed=0;
async function check(name,expectedInput){
 const p=await read(name+'.json'),q=p.input;assert.equal(p.schema,1);assert.equal(p.kind,'sphere-triangle-mesh-trajectory-lab');
 if(expectedInput)compare(q,expectedInput,name+'.input');
 const result=runtime.querySphereTriangleMeshTrajectory({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);
 compare(p.result,result,name+'.full owned DTO');assert.equal(p.diagnostics.wasmBytes,674978);
 assert.ok(['xy','xz','yz'].includes(p.projection));
 if(p.result.audits.length)assert.ok(Number.isInteger(p.inspectedAudit)&&p.inspectedAudit>=0&&p.inspectedAudit<p.result.audits.length);else assert.equal(p.inspectedAudit,null);
 if(q.triangles.length){assert.ok(Number.isInteger(p.inspectedOrdinal)&&p.inspectedOrdinal>=0&&p.inspectedOrdinal<q.triangles.length);assert.equal(p.inspectedSurfaceId,q.triangles[p.inspectedOrdinal].id);}else assert.equal(p.inspectedOrdinal,null);
 return p;
}
for(const row of rows){
 const input=trajectoryLabPreset(row.name);
 if(row.name==='65-source-rejection'){
  assert.throws(()=>runtime.querySphereTriangleMeshTrajectory({start:input.start,end:input.end,radius:input.radius},input.triangles,input.settings));
  assert.equal(row.canSave,false);assert.equal(row.packetBytes,0);assert.equal(row.rows,0);assert.equal(row.audits,0);assert.equal(row.leaves,0);assert.match(row.error,/SDK/);hostRejected++;continue;
 }
 const p=await check(row.name,input);assert.equal(row.canSave,true);assert.equal(row.rows,input.triangles.length);assert.equal(row.audits,p.result.audits.length);assert.equal(row.leaves,p.result.certifiedLeaves.length);models++;
 if(p.result.status==='separated')separated++;else if(p.result.status==='penetration_witness')witness++;else failed++;
}
const extras=await read('extras.json');
for(const row of extras){
 const p=await check(row.file);
 if(row.kind==='full-capacity'){assert.equal(p.result.audits.length,255);assert.equal(p.result.certifiedLeaves.length,128);assert.equal(p.inspectedAudit,254);assert.equal(p.result.certifiedLeaves[127].auditIndex,254);}
 if(row.kind==='failed-prefix'){assert.equal(p.result.status,'not_certified');assert.equal(p.result.certifiedLeaves.length,126);assert.equal(p.result.partitionLeaves,127);assert.equal(p.result.reason,'leaf_budget');assert.ok(p.result.safePrefix[1]<1);assert.ok(p.result.current);}
 if(row.kind==='last-source'){assert.equal(p.input.triangles.length,64);assert.equal(p.input.triangles[0].id,64);assert.equal(p.inspectedOrdinal,63);assert.equal(p.inspectedSurfaceId,1);assert.equal(p.result.lastMesh.rows[63].query.candidates.length,7);assert.equal(p.result.lastMesh.nearest.possibleSurfaceIds.length,64);}
 if(row.kind==='signed-zero'){assert.ok(Object.is(p.input.start[0],-0));assert.ok(Object.is(p.input.end[0],-0));}
 if(row.kind==='failure-last-row'){assert.equal(p.result.status,'not_certified');assert.equal(p.result.lastMesh.status,'row_failure');assert.equal(p.result.lastMesh.nearest,null);assert.equal(p.inspectedOrdinal,2);assert.equal(p.result.lastMesh.rows[2].query.status,'completed');}
}
const actions=await read('actions.json'),edit=actions.find(row=>row.action==='edit-clears');assert.ok(edit);
assert.equal(edit.json,'');assert.equal(edit.rows,0);assert.equal(edit.leaves,0);assert.equal(edit.audits,0);assert.equal(edit.save,false);assert.equal(edit.timeline,'');assert.equal(edit.view,'');
for(const field of ['summary','partition','geometry','candidates'])assert.equal(edit[field],'—');
const rejected=actions.find(row=>row.action==='id-zero-rejected');assert.ok(rejected);assert.equal(rejected.save,false);assert.equal(rejected.json,'');assert.match(rejected.error,/SDK/);
const earlier=actions.find(row=>row.action==='earlier-audit-keeps-lastmesh-owner');assert.ok(earlier);
const earlierGeometry=parseStrictJson(earlier.geometry,budget);assert.equal(earlierGeometry.selectedAudit,0);assert.equal(earlierGeometry.lastMeshAuditIndex,254);assert.equal(earlierGeometry.lastMeshBelongsToSelectedAudit,false);assert.match(earlier.note,/重ねません/);
const later=actions.find(row=>row.action==='failure-keeps-later-row');assert.ok(later);const laterGeometry=parseStrictJson(later.geometry,budget);
assert.equal(laterGeometry.lastMesh.nearest,null);assert.equal(laterGeometry.lastMesh.status,'row_failure');assert.equal(laterGeometry.sourceOrdinal,2);assert.equal(laterGeometry.rowQuery.status,'completed');
const downloads=await read('downloads.json');assert.ok(downloads.length>=2);
for(const row of downloads){
 const actual=await readFile(new URL(row.download,dir)),display=await readFile(new URL(row.display,dir));assert.deepEqual(actual,display,row.download+' exact visible JSON bytes');compare(parseStrictJson(actual.toString('utf8'),budget),parseStrictJson(display.toString('utf8'),budget),row.download+'.complete saved packet');
}
const report={schema:1,status:'PASS',phase,presets:rows.length,actualModelPresets:models,hostRejected,separated,witness,expectedModelFailures:failed,extraModelPackets:extras.length,numericBits,negativeZeroBits,downloads:downloads.length,
 scope:'Actual visible UI complete inputs/results compared to direct public owned WASM method, every preset plus selected capacity/prefix/edit/retry/projection packets and real Blob bytes. No screenshot-as-numerical-proof or independent mathematical solver claim; previous mixed62 exact-rational acceptance remains distinct.'};
await writeFile(new URL(`reports/sphere-triangle-mesh-trajectory-lab-${phase}-browser-verification.json`,root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
