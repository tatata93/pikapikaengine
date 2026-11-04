// Visible complete UI packets vs direct actual SDK; no hidden browser state.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {entryLabPresets,entryLabPreset} from '../../tools/sphere-triangle-mesh-entry-lab.mjs';
const root=new URL('../../',import.meta.url),phase=process.argv[2];assert.ok(['local','public'].includes(phase));
const prefix='sphere-triangle-mesh-entry-lab',dir=new URL(`reports/${prefix}-${phase}-browser/`,root);
const budget={maxBytes:16777216,maxDepth:32,maxNodes:1000000},evidence={};
async function bytes(name){assert.match(name,/^[a-z0-9-]+\.json$/);const b=await readFile(new URL(name,dir));evidence[`reports/${prefix}-${phase}-browser/${name}`]={bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};return b;}
const read=async name=>parseStrictJson((await bytes(name)).toString('utf8'),budget);
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('assets/pikapika-simulation.wasm',root))});
const html=await readFile(new URL('index.html',root),'utf8'),build=html.match(/\?build=([a-f0-9]{16})/)[1];
const view=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
const bits=x=>{assert.ok(Number.isFinite(x));view.setFloat64(0,x);return view.getBigUint64(0);};
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.equal(bits(a),bits(b),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
 else if(a&&typeof a==='object'){assert.ok(b!==null,label);assert.equal(Array.isArray(a),Array.isArray(b),label);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
 else assert.equal(a,b,label);
}
const call=q=>runtime.querySphereTriangleMeshEntry({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);
function checkPacket(p,label,input){
 assert.equal(p.schema,1);assert.equal(p.kind,'sphere-triangle-mesh-entry-lab');if(input)compare(p.input,input,label+'.input');
 compare(p.result,call(p.input),label+'.complete owned result');assert.equal(p.diagnostics.wasmBytes,719410);assert.equal(p.diagnostics.buildId,build);
 assert.ok(['xy','xz','yz'].includes(p.projection));
 if(p.result.audits.length)assert.ok(Number.isInteger(p.inspectedAudit)&&p.inspectedAudit>=0&&p.inspectedAudit<p.result.audits.length);else assert.equal(p.inspectedAudit,null);
 if(p.input.triangles.length){assert.ok(Number.isInteger(p.inspectedOrdinal)&&p.inspectedOrdinal>=0&&p.inspectedOrdinal<p.input.triangles.length);assert.equal(p.inspectedSurfaceId,p.input.triangles[p.inspectedOrdinal].id);}else{assert.equal(p.inspectedOrdinal,null);assert.equal(p.inspectedSurfaceId,null);}
 return p;
}
const rows=await read('presets.json');assert.deepEqual(rows.map(r=>r.name),entryLabPresets.map(r=>r.name));
let models=0,hostRejected=0;const counts={separated:0,entry_window:0,initial_penetration:0,not_certified:0,invalid_input:0};
for(const row of rows){
 const input=entryLabPreset(row.name);
 if(row.name==='65-source-rejection'){
  assert.throws(()=>call(input));assert.equal(row.canSave,false);assert.equal(row.packetBytes,0);for(const k of ['rows','audits','leaves'])assert.equal(row[k],0);assert.match(row.error,/SDK/);hostRejected++;continue;
 }
 const p=checkPacket(await read(row.name+'.json'),row.name,input);assert.equal(row.packetBytes,(await bytes(row.name+'.json')).length);assert.equal(row.canSave,true);
 assert.equal(row.rows,p.input.triangles.length);assert.equal(row.audits,p.result.audits.length);assert.equal(row.leaves,p.result.certifiedLeaves.length);counts[p.result.status]++;models++;
}
assert.deepEqual(counts,{separated:2,entry_window:5,initial_penetration:1,not_certified:12,invalid_input:4});assert.equal(models,24);assert.equal(hostRejected,1);
const extras=await read('extras.json'),packets={};assert.equal(extras.length,13);
const additional=parseStrictJson(await readFile(new URL(`reports/${prefix}-additional-inputs.json`,root),'utf8'),budget);
for(const row of extras){
 const input={'signed-zero':additional['signed-source-zero'],'reverse-entry':additional['reverse-entry-seven-twelfths'],'modified-radius':additional['modified-radius']}[row.kind];
 const p=checkPacket(await read(row.file+'.json'),row.file,input);packets[row.kind]=p;
 if(row.kind==='full-capacity'){assert.equal(p.result.audits.length,256);assert.equal(p.result.partition.length,128);assert.equal(p.result.certifiedLeaves.length,128);assert.equal(p.inspectedAudit,255);assert.equal(p.result.certifiedLeaves[127].auditIndex,255);}
 if(row.kind==='earlier-audit'){assert.equal(p.inspectedAudit,0);assert.equal(p.result.lastMeshAuditIndex,255);}
 if(row.kind==='full-frontier'){assert.equal(p.result.frontier.length,127);assert.equal(p.result.partition.length,128);assert.equal(p.inspectedAudit,127);}
 if(row.kind==='last-source'){assert.equal(p.input.triangles.length,64);assert.equal(p.inspectedOrdinal,63);assert.equal(p.inspectedSurfaceId,1);assert.equal(p.result.lastMesh.rows[63].query.candidates.length,7);assert.deepEqual(p.result.candidateSurfaceIds,Array.from({length:64},(_,i)=>i+1));}
 if(row.kind==='failed-prefix'){assert.equal(p.result.reason,'leaf_budget');assert.equal(p.result.partition.length,127);assert.equal(p.inspectedAudit,253);assert.ok(p.result.safePrefix[1]<1);}
 if(row.kind==='signed-zero'){assert.ok(Object.is(p.input.start[0],-0));assert.ok(Object.is(p.input.end[0],-0));}
 if(row.kind==='reverse-entry'){assert.equal(p.result.status,'entry_window');assert.ok(p.result.window.parameter[0]<7/12&&p.result.window.parameter[1]>7/12);}
 if(row.kind==='failure-last-row'){assert.equal(p.result.lastMesh.status,'row_failure');assert.equal(p.result.lastMesh.nearest,null);assert.equal(p.inspectedOrdinal,2);assert.equal(p.result.lastMesh.rows[2].query.status,'completed');}
 if(row.kind==='all-conservative-ids'){assert.deepEqual(p.result.candidateSurfaceIds,[5,37]);assert.deepEqual(p.result.lastMesh.nearest.possibleSurfaceIds,[37]);}
 if(row.kind==='singleton-prefix'){assert.deepEqual(p.result.safePrefix,[0,0]);assert.deepEqual(p.result.window.parameter,[0,0.375]);assert.ok(p.result.certifiedLeaves.some(l=>l.cell.parameter[0]===0.5&&l.cell.parameter[1]===1));}
 if(row.kind==='recovered-ancestor'){assert.equal(p.result.status,'entry_window');assert.equal(p.inspectedAudit,1);assert.equal(p.result.audits[1].meshStatus,'row_failure');assert.equal(p.result.audits[1].outcome,'split');}
 if(row.kind==='modified-radius')assert.equal(p.input.radius,0.375);
 if(row.kind==='retry-recovered')assert.equal(p.result.status,'entry_window');
}
const actions=await read('actions.json'),action=name=>{const r=actions.find(r=>r.action===name);assert.ok(r,name);return r;},parse=s=>parseStrictJson(s,budget);
const clear=action('edit-clears');assert.equal(clear.json,'');assert.equal(clear.save,false);assert.equal(clear.timeline,'');assert.equal(clear.view,'');for(const k of ['rows','leaves','audits'])assert.equal(clear[k],0);for(const k of ['summary','initial','window','partition','geometry','candidates'])assert.equal(clear[k],'—');
for(const name of ['id-zero-rejected','json-duplicate-rejected']){const r=action(name);assert.equal(r.save,false);assert.equal(r.json,'');assert.match(r.error,name==='id-zero-rejected'?/SDK/:/入力JSON/);}
const earlier=action('earlier-audit-keeps-lastmesh-owner'),g=parse(earlier.geometry);assert.equal(g.selectedAudit,0);assert.equal(g.lastMeshAuditIndex,255);assert.equal(g.lastMeshBelongsToSelectedAudit,false);assert.match(earlier.note,/重ねません/);
const capacity=action('full-capacity-visible');assert.equal(capacity.audits,256);assert.equal(capacity.leaves,128);compare(parse(capacity.partition).partition,packets['full-capacity'].result.partition,'all128 visible partition');assert.equal(parse(capacity.geometry).selectedAudit,255);
const frontier=action('full-frontier-visible');compare(parse(frontier.partition).frontier,packets['full-frontier'].result.frontier,'all127 visible frontier');
const last=action('last-source-visible');assert.equal(last.rows,64);assert.equal(parse(last.geometry).sourceOrdinal,63);compare(parse(last.window).candidateSurfaceIds,packets['last-source'].result.candidateSurfaceIds,'all64 visible IDs');
const failure=parse(action('failure-keeps-later-row').geometry);assert.equal(failure.lastMesh.status,'row_failure');assert.equal(failure.lastMesh.nearest,null);assert.equal(failure.sourceOrdinal,2);assert.equal(failure.rowQuery.status,'completed');
const ids=parse(action('window-ids-are-not-nearest').window);assert.deepEqual(ids.candidateSurfaceIds,[5,37]);assert.deepEqual(ids.lastMeshNearestIds,[37]);
const singleton=action('singleton-prefix-and-later-island');assert.deepEqual(parse(singleton.initial).safePrefix,[0,0]);assert.deepEqual(parse(singleton.window).window.parameter,[0,.375]);
const ancestor=parse(action('failed-ancestor-retained').geometry);assert.equal(ancestor.audit.meshStatus,'row_failure');assert.equal(ancestor.audit.outcome,'split');assert.equal(ancestor.lastMeshBelongsToSelectedAudit,false);
const downloads=await read('downloads.json');assert.equal(downloads.length,2);
for(const row of downloads){const actual=await bytes(row.download),display=await bytes(row.display);assert.deepEqual(actual,display,row.download+' exact visible JSON bytes including LF');assert.equal(actual.at(-1),10);compare(parse(actual.toString('utf8')),parse(display.toString('utf8')),row.download+'.all bytes parsed');checkPacket(parse(actual.toString('utf8')),row.download);}
const game=await read('game-cover-report.json'),state=await readFile(new URL('game-state.txt',dir),'utf8');
assert.equal(game.state,'ready');assert.equal(game.failure,null);assert.deepEqual(game.errors,[]);assert.ok(game.counts.queries>0);assert.equal(game.counts.queries,game.counts.checked);assert.equal(game.counts.queries,game.counts.validated);
assert.ok(game.records.length>0&&game.records.every(r=>r.state==='completed'));assert.ok(game.records.some(r=>r.clipSeconds===1));assert.equal(game.renderer.residentMeshes,3);assert.equal(game.renderer.lost,false);assert.equal(game.startup.diagnostics.wasmBytes,719410);assert.equal(game.startup.diagnostics.buildId,build);
assert.match(state,/一時停止 \/ Pで再開/);const kills=Number(state.match(/撃破 (\d+)/)[1]);assert.ok(kills>0);
const report={schema:1,status:'PASS',phase,buildId:build,wasmBytes:719410,presets:rows.length,actualModelPresets:models,hostRejected,separated:counts.separated,entryWindows:counts.entry_window,initialPenetrations:counts.initial_penetration,notCertified:counts.not_certified,invalidInputs:counts.invalid_input,expectedModelFailures:counts.not_certified+counts.invalid_input,extraModelPackets:extras.length,numericBits,negativeZeroBits,downloads:downloads.length,
 game:{paused:true,kills,coverQueries:game.counts.queries,allCompleted:true,boostClip1Observed:true,residentMeshes:3},evidence,
 scope:'Actual UI sources/full owned results vs direct public SDK; all25 presets,13 supplemental view/input/retry packets and2 real Blob downloads. Supplemental views can share one query: packet count is not executed-query count. Existing game is a regression, not entry contact integration. Independent mixed65 Fraction with declared host3 supplements remains separate; no screenshot or explanation projection as numerical proof.'};
await writeFile(new URL(`reports/${prefix}-${phase}-browser-verification.json`,root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,evidence:Object.keys(evidence).length}));
