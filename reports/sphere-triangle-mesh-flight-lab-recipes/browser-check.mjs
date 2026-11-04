// Actual visible UI proof, with no hidden browser evaluation or extra query.
// Capture selectors: #flight-source.value, #flight-json.textContent;
// #flight-{rows,audits,leaves} tr; #flight-audit option;
// #flight-status.textContent / .dataset.state; #flight-error text + visibility;
// #flight-{save,save-input}.disabled; #flight-{timeline,view}.innerHTML.
// Diagnostic panels: #flight-{summary,initial,window,tube,endpoint,body,
// partition,geometry,candidates}.textContent. Hidden error text can remain stale;
// it is an error only when the separately captured errorVisible is true.
import assert from 'node:assert/strict';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {flightLabPresetData,flightLabPresetProvenance} from '../../tools/sphere-triangle-mesh-flight-presets.mjs';

const [captureDirectory,nodeReportPath,outputPath,...extra]=process.argv.slice(2);
assert.ok(captureDirectory&&nodeReportPath&&outputPath&&!extra.length,'Usage: browser-check.mjs CAPTURE_DIR NODE_UI_REPORT OUTPUT_JSON');
const root=fileURLToPath(new URL('../../',import.meta.url)),dir=path.resolve(captureDirectory),nodePath=path.resolve(nodeReportPath),output=path.resolve(outputPath);
const within=p=>{const r=path.relative(root,p);assert.ok(r&&!r.startsWith('..')&&!path.isAbsolute(r),'Evidence stays inside repository');return r.split(path.sep).join('/');};
within(dir);within(nodePath);within(output);
const budget={maxBytes:16777216,maxDepth:64,maxNodes:2000000},fullBudget={maxBytes:8388608,maxDepth:32,maxNodes:1000000};
const info=b=>({bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')});
const evidence={};const archive=(p,b)=>{evidence[within(p)]=info(b);return b;};
async function raw(p){const b=await readFile(p);assert.ok(b.length<=budget.maxBytes,p+' bounded bytes');return archive(p,b);}
const parse=(b,budgetOverride=budget)=>parseStrictJson(b.toString('utf8'),budgetOverride);
async function json(p){return parse(await raw(p));}
function file(name){assert.equal(typeof name,'string');assert.ok(name.length&&name.length<240&&!name.includes('\\')&&!path.isAbsolute(name));
  const p=path.resolve(dir,name);assert.ok(path.relative(dir,p)&&!path.relative(dir,p).startsWith('..'));return p;}
async function captured(name){return json(file(name));}
const buckets=Object.fromEntries(['source','nodeModel','nativeModel','canonicalOwned','downloads','visiblePanels','view'].map(k=>[k,{numericBits:0,negativeZeroBits:0}]));
const bitView=new DataView(new ArrayBuffer(8));const bits=n=>{assert.equal(typeof n,'number');assert.ok(Number.isFinite(n));bitView.setFloat64(0,n);return bitView.getBigUint64(0);};
function compare(a,b,label,count=buckets.source){assert.equal(typeof a,typeof b,label);
  if(typeof b==='number'){assert.equal(bits(a),bits(b),label);count.numericBits++;if(Object.is(a,-0))count.negativeZeroBits++;}
  else if(b!==null&&typeof b==='object'){
    assert.ok(a!==null,label);assert.equal(Array.isArray(a),Array.isArray(b),label);
    assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label+' complete keys');
    if(Array.isArray(b))assert.equal(a.length,b.length,label+' full array');
    for(const k of Object.keys(b))compare(a[k],b[k],label+'.'+k,count);
  }else assert.equal(a,b,label);
}
const heldResult=p=>p.mode==='held'?p.result:p.result.inflated;
const nodeReport=await json(nodePath);assert.equal(nodeReport.status,'PASS');assert.equal(nodeReport.presets,30);assert.equal(nodeReport.actualModelPresets,29);assert.equal(nodeReport.hostRejected,1);
assert.equal(nodeReport.sourceStable,true);assert.deepEqual(nodeReport.sourceBefore,nodeReport.sourceAfter);
for(const [name,expected] of Object.entries(nodeReport.sourceAfter))assert.deepEqual(info(await raw(path.resolve(root,name))),expected,name+' current frozen dependency');
const nodeDir=path.dirname(nodePath),nodeFiles=nodeReport.files;
for(const [name,expected] of Object.entries(nodeFiles))assert.deepEqual(info(await raw(path.join(nodeDir,name))),expected,name+' canonical Node artifact');
const nodeRows=parse(await readFile(path.join(nodeDir,'presets.json'))).rows;
assert.deepEqual(nodeRows.map(p=>p.name),flightLabPresetData.map(p=>p.name));
const ownedBytes=await raw(path.join(root,nodeReport.reference.path));assert.deepEqual(info(ownedBytes),{bytes:nodeReport.reference.bytes,sha256:nodeReport.reference.sha256});
const canonicalOwned=parse(ownedBytes),native={};
for(const [cohort,record] of Object.entries(flightLabPresetProvenance.sourceFiles)){
  const b=await raw(path.join(root,record.path));assert.deepEqual(info(b),{bytes:record.bytes,sha256:record.sha256});native[cohort]=parse(b);
}
const html=(await raw(path.join(root,'index.html'))).toString('utf8'),build=html.match(/\?build=([0-9a-f]{16})/)[1];
const manifest=await json(path.join(root,'assets/pikapika-simulation.build.json')),wasm=manifest.artifacts['assets/pikapika-simulation.wasm'];
assert.deepEqual(wasm,nodeReport.wasm);assert.equal(wasm.bytes,800982);
assert.deepEqual(info(await raw(path.join(root,'assets/pikapika-simulation.wasm'))),wasm);
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const primitiveStatuses=['completed','invalid_input','degenerate','ill_conditioned','quality_unresolved','budget_exceeded','numerical_failure','unsupported_environment'];
const primitiveReasons=['none','settings','surface_id','input_domain','zero_cross','cross_uncertain','conditioning_rejected','conditioning_uncertain','candidate_budget','no_candidate','local_width','zero_distance','distance_uncertain','sqrt_budget','normal_width','nonfinite_intermediate','allocation_failure','environment'];
const CCD=['none','invalid_input','initial_contact','query_unresolved','event_budget','segment_budget','query_budget','root_budget','geometric_guard','propagation_failure','solver_failure','sustained_contact_required','numerical_failure'];
const ordinal=(value,values)=>{const i=values.indexOf(value);assert.ok(i>=0,'Known enum '+value);return i;};
function projectHeld(result){
  for(const audit of result.audits){if(audit.meshStatus!==null)audit.meshStatus=ordinal(audit.meshStatus,meshStatuses);if(audit.meshReason!==null)audit.meshReason=ordinal(audit.meshReason,meshReasons);}
  if(result.lastMesh){const m=result.lastMesh;m.status=ordinal(m.status,meshStatuses);m.reason=ordinal(m.reason,meshReasons);
    for(const row of m.rows)if(row.query){const q=row.query;q.status=ordinal(q.status,primitiveStatuses);q.reason=ordinal(q.reason,primitiveReasons);
      if(q.geometry)q.geometry.relation=ordinal(q.geometry.relation,['separated','penetrating','touching','boundary_unresolved']);
      for(const c of q.candidates){c.feature=ordinal(c.feature,['face','edge_ab','edge_bc','edge_ca','vertex_a','vertex_b','vertex_c']);c.disposition=ordinal(c.disposition,['retained','outside_simplex','kkt_violated']);}}}
  return result;
}
function projectNative(result,mode){const r=structuredClone(result);delete r.originalInput;
  if(mode==='held')return projectHeld(r);if(r.flightFailure!==null)r.flightFailure=ordinal(r.flightFailure,CCD);if(r.inflated)projectHeld(r.inflated);return r;}
const packetKeys=['schema','kind','mode','input','result','diagnostics','projection','inspectedAudit','inspectedOrdinal','inspectedSurfaceId'];
const nodePackets=new Map();for(const row of nodeRows)if(row.hostError===null)nodePackets.set(row.name,parse(await readFile(path.join(nodeDir,row.file))));
const packets=new Map();
function presetForInput(input){return flightLabPresetData.find(p=>{try{assert.deepEqual(input,p.input);return true;}catch{return false;}});}
function checkPacket(p,label,preset){
  assert.deepEqual(Object.keys(p).sort(),packetKeys.slice().sort(),label+' packet keys');assert.equal(p.schema,1);assert.equal(p.kind,'sphere-triangle-mesh-flight-lab');
  preset??=presetForInput(p.input);assert.ok(preset,label+' original fixed input');assert.equal(p.mode,preset.mode);
  compare(p.input,preset.input,label+'.original input',buckets.source);
  const node=nodePackets.get(preset.name);assert.ok(node,label+' actual Node model');
  compare(p.result,node.result,label+'.Node full owned result',buckets.nodeModel);
  const old=canonicalOwned.fixtures.find(f=>f.cohort===preset.cohort&&f.name===preset.fixtureName);assert.ok(old?.result,label+' previous actual-owned model');
  compare(p.result,old.result,label+'.canonical173 result',buckets.canonicalOwned);
  const original=native[preset.cohort].fixtures.find(f=>f.name===preset.fixtureName);assert.ok(original);
  compare(projectNative(p.result,p.mode),original.result,label+'.Native full projection',buckets.nativeModel);
  assert.equal(p.diagnostics.buildId,build);assert.equal(p.diagnostics.wasmBytes,wasm.bytes);assert.equal(p.diagnostics.apiVersion,1);
  assert.equal(p.diagnostics.backend,'C++ WebAssembly');assert.ok(Number.isFinite(p.diagnostics.startupMs)&&p.diagnostics.startupMs>=0);
  assert.ok(Number.isSafeInteger(p.diagnostics.memoryBytes)&&p.diagnostics.memoryBytes>0);
  assert.ok(['xy','xz','yz'].includes(p.projection));const h=heldResult(p);
  if(h?.audits.length)assert.ok(Number.isInteger(p.inspectedAudit)&&p.inspectedAudit>=0&&p.inspectedAudit<h.audits.length);else assert.equal(p.inspectedAudit,null);
  if(p.input.triangles.length){assert.ok(Number.isInteger(p.inspectedOrdinal)&&p.inspectedOrdinal>=0&&p.inspectedOrdinal<p.input.triangles.length);assert.equal(p.inspectedSurfaceId,p.input.triangles[p.inspectedOrdinal].id);}
  else{assert.equal(p.inspectedOrdinal,null);assert.equal(p.inspectedSurfaceId,null);}
  return p;
}
async function packetFile(name,preset){if(packets.has(name))return packets.get(name);const b=await raw(file(name));assert.ok(b.length<=fullBudget.maxBytes);assert.equal(b.at(-1),10,name+' final LF');
  const p=checkPacket(parse(b,fullBudget),name,preset);packets.set(name,p);return p;}
const rows=await captured('presets.json');assert.ok(Array.isArray(rows));assert.deepEqual(rows.map(r=>r.name),flightLabPresetData.map(r=>r.name));
const counts={held:{},guard:{}},maximums={audits:0,leaves:0,partition:0,frontier:0,sources:0,candidateIds:0,lastMeshRows:0,lastMeshCandidates:0};let actualModels=0,hosts=0;
for(let i=0;i<rows.length;i++){
  const row=rows[i],preset=flightLabPresetData[i];for(const key of ['mode','cohort','fixtureName'])assert.equal(row[key],preset[key]);
  compare(await captured(row.inputFile),preset.input,row.name+'.visible editor',buckets.source);
  const expected=nodeRows[i];assert.equal(expected.name,row.name);
  if(expected.hostError!==null){assert.equal(row.packetFile,null);assert.equal(row.packetBytes,0);assert.equal(row.canSave,false);assert.equal(row.canSaveInput,false);assert.equal(row.errorVisible,true);assert.match(row.error,/SDK/);assert.equal(row.state,'error');
    for(const key of ['rows','audits','leaves','auditOptions'])assert.equal(row[key],0);hosts++;continue;}
  const p=await packetFile(row.packetFile,preset),h=heldResult(p);assert.equal(row.packetBytes,evidence[within(file(row.packetFile))].bytes);assert.equal(row.canSave,true);assert.equal(row.canSaveInput,true);assert.equal(row.errorVisible,false);
  assert.match(row.status,new RegExp(p.result.status));assert.equal(row.state,['separated','certified_separated'].includes(p.result.status)?'separated':p.result.status==='entry_window'?'window':'unconfirmed');
  assert.equal(row.rows,p.input.triangles.length);assert.equal(row.audits,h?.audits.length??0);assert.equal(row.auditOptions,h?.audits.length??0);assert.equal(row.leaves,h?.certifiedLeaves.length??0);
  if(row.summary!==undefined){const s=parseStrictJson(row.summary,budget);compare(s.originalInput,p.result.originalInput,row.name+'.visible original',buckets.visiblePanels);compare(s.snapshot,p.result.snapshot,row.name+'.visible snapshot',buckets.visiblePanels);assert.equal(s.status,p.result.status);assert.equal(s.auditCount,h?.audits.length??0);assert.equal(s.sourceCount,p.input.triangles.length);}
  counts[p.mode][p.result.status]=(counts[p.mode][p.result.status]??0)+1;
  for(const [key,value] of Object.entries({audits:h?.audits.length??0,leaves:h?.certifiedLeaves.length??0,partition:h?.partition.length??0,frontier:h?.frontier.length??0,sources:p.input.triangles.length,candidateIds:h?.candidateSurfaceIds.length??0,lastMeshRows:h?.lastMesh?.rows.length??0,lastMeshCandidates:h?.lastMesh?.rows.reduce((n,r)=>n+(r.query?.candidates.length??0),0)??0}))maximums[key]=Math.max(maximums[key],value);
  actualModels++;
}
assert.equal(actualModels,nodeReport.actualModelPresets);assert.equal(hosts,nodeReport.hostRejected);assert.deepEqual(counts,nodeReport.counts);assert.deepEqual(maximums,nodeReport.maximums);
const extras=await captured('extras.json');assert.ok(Array.isArray(extras)&&extras.length>=1&&extras.length<=32);
assert.equal(new Set(extras.map(r=>r.file)).size,extras.length);
for(const extra of extras){assert.equal(typeof extra.kind,'string');const p=await packetFile(extra.file),h=heldResult(p);
  if(extra.kind==='full-capacity'){assert.equal(h.audits.length,256);assert.equal(h.certifiedLeaves.length,128);assert.equal(p.inspectedAudit,255);}
  if(extra.kind==='earlier-audit'){assert.equal(p.inspectedAudit,0);assert.equal(h.lastMeshAuditIndex,255);}
  if(extra.kind==='full-frontier'){assert.equal(h.frontier.length,127);assert.equal(h.partition.length,128);}
  if(extra.kind==='last-source'){assert.equal(p.inspectedOrdinal,63);assert.equal(p.input.triangles.length,64);assert.equal(h.lastMesh.rows[63].query.candidates.length,7);}
  if(extra.kind==='nested-entry'){assert.equal(p.result.status,'not_certified');assert.equal(p.result.inflated.status,'entry_window');assert.equal(p.result.candidate,null);}
}
const actions=await captured('actions.json');assert.ok(Array.isArray(actions)&&actions.length<=64);assert.equal(new Set(actions.map(r=>r.action)).size,actions.length);
const action=name=>{const row=actions.find(r=>r.action===name);assert.ok(row,name+' observed action');return row;};
function clear(row){assert.equal(row.json,'');assert.equal(row.save,false);assert.equal(row.saveInput,false);assert.equal(row.timeline,'');assert.equal(row.view,'');for(const k of ['rows','audits','leaves'])assert.equal(row[k],0);
  for(const k of ['summary','initial','window','tube','endpoint','body','partition','geometry','candidates'])assert.equal(row[k],'—',row.action+'.'+k);}
clear(action('edit-clears'));assert.equal(action('edit-clears').errorVisible,false);assert.equal(action('edit-clears').state,'empty');
for(const name of ['malformed-rejected','host-rejected']){const a=action(name);clear(a);assert.equal(a.errorVisible,true);assert.equal(a.state,'error');assert.match(a.error,name==='host-rejected'?/SDK/:/入力JSON/);}
const transientRetry=actions.find(a=>a.action==='retry-start-clears'),cachedRetry=actions.find(a=>a.action==='retry-cached-completed');
assert.ok(Boolean(transientRetry)!==Boolean(cachedRetry),'Exactly one actually observed retry path');
let browserRetryTransientClearObserved=false;
if(transientRetry){clear(transientRetry);assert.equal(transientRetry.errorVisible,false);assert.equal(transientRetry.state,'empty');browserRetryTransientClearObserved=true;}
else{
  assert.equal(cachedRetry.ready,true);assert.equal(cachedRetry.save,true);assert.equal(cachedRetry.saveInput,true);assert.equal(cachedRetry.errorVisible,false);
  assert.equal(typeof cachedRetry.note,'string');assert.match(cachedRetry.note,/cache|キャッシュ|transient|過渡|一過/i);
  const p=await packetFile(cachedRetry.file);assert.equal(cachedRetry.state,['separated','certified_separated'].includes(p.result.status)?'separated':p.result.status==='entry_window'?'window':'unconfirmed');
  if(cachedRetry.json!==undefined)compare(parseStrictJson(cachedRetry.json,fullBudget),p,'Actually observed completed cached retry packet',buckets.visiblePanels);
}
const restored=action('retry-restored');await packetFile(restored.file);assert.equal(restored.save,true);assert.equal(restored.saveInput,true);assert.equal(restored.errorVisible,false);
const viewed=action('view-only'),beforeView=await packetFile(viewed.beforeFile),afterView=await packetFile(viewed.afterFile);
compare(afterView.input,beforeView.input,'view retained input',buckets.view);compare(afterView.result,beforeView.result,'view retained full result',buckets.view);compare(afterView.diagnostics,beforeView.diagnostics,'view retained diagnostics',buckets.view);
assert.ok(afterView.projection!==beforeView.projection||afterView.inspectedAudit!==beforeView.inspectedAudit||afterView.inspectedOrdinal!==beforeView.inspectedOrdinal,'Observed selection changed');
const geometry=parseStrictJson(viewed.geometry,budget),h=heldResult(afterView),audit=afterView.inspectedAudit===null?null:h.audits[afterView.inspectedAudit];
assert.equal(geometry.selectedAudit,afterView.inspectedAudit);compare(geometry.audit,audit,'visible selected audit',buckets.visiblePanels);assert.equal(geometry.lastMeshAuditIndex,h?.lastMeshAuditIndex??null);
assert.equal(geometry.lastMeshBelongsToSelectedAudit,afterView.inspectedAudit!==null&&afterView.inspectedAudit===h?.lastMeshAuditIndex);
assert.equal(geometry.sourceOrdinal,afterView.inspectedOrdinal);assert.equal(geometry.surfaceId,afterView.inspectedSurfaceId);compare(geometry.rowQuery,h?.lastMesh?.rows[afterView.inspectedOrdinal]?.query??null,'visible owned row',buckets.visiblePanels);
assert.equal(typeof viewed.note,'string');assert.ok(viewed.note.length);

const downloads=await captured('downloads.json');assert.equal(downloads.length,2);assert.deepEqual(downloads.map(r=>r.kind).sort(),['failure','success']);const realDownloadEvidence=[];
for(const row of downloads){assert.equal(typeof row.actualPath,'string');assert.ok(path.isAbsolute(row.actualPath)&&!/^[/\\]{2}/.test(row.actualPath),'Real local browser download path required');
  assert.equal(typeof row.capturedFilename,'string');assert.ok(row.capturedFilename.length>0&&row.capturedFilename.length<=255&&!row.capturedFilename.includes('/')&&!row.capturedFilename.includes('\\')&&row.capturedFilename.endsWith('.json'));
  assert.ok(Number.isSafeInteger(row.bytes)&&row.bytes>0);assert.match(row.sha256,/^[0-9a-f]{64}$/);
  const original=await readFile(row.actualPath);assert.ok(original.length<=fullBudget.maxBytes);const archived=await raw(file(row.download)),display=await raw(file(row.display));
  assert.deepEqual(info(original),{bytes:row.bytes,sha256:row.sha256});assert.deepEqual(archived,original,'Archived actual download bytes');assert.deepEqual(original,display,'Actual Blob download equals visible JSON bytes including final LF');assert.equal(original.at(-1),10);
  const p=checkPacket(parse(original,fullBudget),row.download);compare(parse(original,fullBudget),parse(display,fullBudget),row.download+'.strict full saved packet',buckets.downloads);
  if(row.kind==='success')assert.ok(['separated','certified_separated'].includes(p.result.status));else assert.ok(!['separated','certified_separated'].includes(p.result.status));
  realDownloadEvidence.push({kind:row.kind,actualPath:row.actualPath,capturedFilename:row.capturedFilename,download:row.download,display:row.display,...info(original)});
}

// Hash every captured JPEG/AX/JSON/Blob archive; screenshots are display evidence.
async function inventory(directory){for(const entry of await readdir(directory,{withFileTypes:true})){
  const p=path.join(directory,entry.name);assert.equal(entry.isSymbolicLink(),false,'No evidence symlink');if(entry.isDirectory())await inventory(p);else if(entry.isFile()&&p!==output)await raw(p);
}}
await inventory(dir);assert.ok(Object.keys(evidence).length<=512);assert.ok(Object.values(evidence).reduce((n,v)=>n+v.bytes,0)<=128*1024*1024);
const capturePrefix=within(dir)+'/',displayEvidence=Object.keys(evidence).filter(p=>p.startsWith(capturePrefix)&&/\.(?:jpg|jpeg|txt)$/i.test(p));
assert.ok(displayEvidence.some(p=>/\.(?:jpg|jpeg)$/i.test(p)),'Actual captured JPEG evidence required');
assert.ok(displayEvidence.some(p=>/\.txt$/i.test(p)),'Actual visible AX/text evidence required');
for(const p of displayEvidence.filter(p=>/\.(?:jpg|jpeg)$/i.test(p))){const b=await readFile(path.join(root,p));assert.equal(b.readUInt16BE(0),0xffd8,'Captured JPEG signature');}
const report={schema:1,status:'PASS',phase:path.basename(dir).includes('public')?'public':'local',buildId:build,wasmBytes:wasm.bytes,presets:rows.length,actualModelPresets:actualModels,hostRejected:hosts,
  counts,maximums,counters:buckets,numericBits:Object.values(buckets).reduce((n,v)=>n+v.numericBits,0),negativeZeroBits:Object.values(buckets).reduce((n,v)=>n+v.negativeZeroBits,0),extraModelPackets:extras.length,downloads:downloads.length,
  realDownloadEvidence,displayEvidence,browserRetryTransientClearObserved,nodeUiReport:{path:within(nodePath),...info(await readFile(nodePath))},evidence,
  comparisonCountScope:'Numeric/negative-zero counters count pairwise assertions in named buckets; a UI number can be compared to multiple independent stored targets and is not counted as a distinct executed simulation.',
  scope:'Actual visible full packets for30 original presets,29 actual models and1 host refusal; extras are views of fixed inputs. Full owned result keys/types/bits are compared separately to canonical Node UI, previous actual173-owned DTO and enum-only Native projection. Hosts are never filled. Real downloaded files are read at recorded local paths, matched to archives and visible JSON including LF. Temporary original paths must remain readable for rerunning this comparator; archived bytes/hashes are retained afterward. A changed view preserves complete result/diagnostics; query0 is established by separate counted23-group Node tests, not inferred as a measured browser query count. Retry transient clearing is observed only when browserRetryTransientClearObserved=true; an already-completed cached retry otherwise proves restored full results, while delayed-loader generation/clear behavior remains separately tested by Node23. No artificial production latency or invented empty browser state is used. JPEG/AX evidence is not mathematical proof; no game/World response, memory-use or performance acceptance is inferred.'};
await writeFile(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({...report,evidence:Object.keys(evidence).length}));
