import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {parseStrictJson} from '../../engine/strict-json.mjs';
import {Scene} from '../../engine/scene.mjs';
import {parsePortableScene,savePortableScene} from '../../engine/portable-scene.mjs';
import {serializeSkinBindingSource} from '../../engine/skin-binding.mjs';
const root=new URL('../../',import.meta.url),sha=b=>createHash('sha256').update(b).digest('hex');
const read=async name=>parseStrictJson(await readFile(new URL(name,root),'utf8'),{maxBytes:16*1024*1024,maxNodes:2000000});
const base='reports/robot-cover-public-release/',names=['02-combat','04-paused-stable','07-loaded','08-resumed','09-redeployed'];
const author=serializeSkinBindingSource(await read('assets/robot-back-cover.skin.json')),reports=[];
for(const name of names){
 const r=await read(base+name+'.json');assert.equal(r.state,'ready');assert.equal(r.failure,null);assert.equal(r.errors.length,0);assert.equal(r.pending,null);assert.equal(r.authorSource,author);
 assert.equal(r.updateEveryTicks,2);assert.equal(r.simulationHz,120);assert.equal(r.startup.diagnostics.buildId,'b576823ff1731dba');assert.equal(r.startup.diagnostics.wasmBytes,592939);
 assert.equal(r.counts.queries,r.counts.checked);assert.equal(r.counts.checked,r.counts.validated);assert.equal(r.renderer.residentMeshes,3);assert.equal(r.renderer.disposed,false);assert.equal(r.renderer.lost,false);
 assert.equal(r.records.length,r.counts.queries);for(const item of r.records){assert.equal(item.state,'completed');for(const key of ['sourceMs','derivedMs','tokenMs'])assert.ok(Number.isFinite(item[key])&&item[key]>=0);assert.ok(item.clipSeconds>=0&&item.clipSeconds<=1);}
 reports.push(r);
}
assert.ok(reports[0].records.some(r=>r.clipSeconds===1));
for(const key of ['tick','opening','counts','renderer'])assert.deepEqual(reports[0][key],reports[1][key],'paused state changed');
const combat=await read(base+'02-combat-ui.json');assert.ok(combat.objective.includes('撃破 2'));assert.equal(combat.fatal,false);assert.equal(combat.pauseVisible,true);
assert.equal(reports[0].renderer.stats.uploadedMeshBytes,1728+288*reports[0].counts.queries);assert.equal(reports[0].renderer.stats.destroyedMeshBuffers,reports[0].counts.queries-1);
assert.ok(reports.at(-1).generation>reports[0].generation);assert.ok(reports.at(-1).tick<reports[0].tick);assert.equal(reports.at(-1).opening,0);
const scene=Scene.load(await readFile(new URL(base+'05-edited.scene.json',root),'utf8')),portableText=await readFile(new URL(base+'06-edited.scene',root),'utf8');
assert.equal(savePortableScene(scene),portableText);assert.deepEqual(parsePortableScene(savePortableScene(scene)).entities,parsePortableScene(portableText).entities);
assert.deepEqual(scene.entities.find(e=>e.id==='barricade-left').position,[-22.5,4,-12]);assert.ok(!scene.entities.some(e=>e.type==='derived-mesh'||e.id==='robot/player/back-cover'));
const local=Scene.load(await readFile(new URL('reports/robot-cover-local-release/05-edited.scene.json',root),'utf8'));assert.deepEqual(scene.entities,local.entities);
const frame=await read(base+'03-frame-log.json');assert.equal(frame.environment.clockDroppedSeconds,0);assert.equal(frame.gpuMs,null);assert.equal(frame.totalFrames,frame.samples.length);assert.equal(frame.retainedFrames,frame.samples.length);assert.ok(frame.samples.length<7200);assert.ok(new Set(frame.samples.map(s=>s.entities)).size>1);assert.ok(frame.overBudget>0);assert.equal(frame.environment.cover.authorSource,author);
const pilot=await read('reports/robot-cover-public/03-frame-log.json');assert.equal(pilot.retainedFrames,7200);assert.ok(pilot.totalFrames>7200);
const paths=names.flatMap(name=>[base+name+'.json',base+name+'-ui.json']);paths.push(base+'05-edited.scene.json',base+'06-edited.scene',base+'03-frame-log.json');
const files=[];for(const path of paths){const data=await readFile(new URL(path,root));files.push({path,bytes:data.length,sha256:sha(data)});}
const result={status:'PASS',build:'b576823ff1731dba',revision:'8ebec4c850547c210426b65bdb3f34e9e9e17cb5',uiKills:2,finiteCaptureCount:reports.length,maximumObservedClip:Math.max(...reports[0].records.map(r=>r.clipSeconds)),resourceMeshes:3,allRecordedQueries:reports.at(-1).counts.queries,
 actualGPUReadback:false,hiddenBrowserPathRetested:false,frameScope:'Fresh finite run including startup/idle/paused intervals; all retained below 7200 limit. Unfiltered rAF/CPU observations, not display timestamps.',frame:{totalFrames:frame.totalFrames,median:frame.median,p95:frame.p95,max:frame.max,overBudget:frame.overBudget,droppedSeconds:frame.environment.clockDroppedSeconds},
 initialLongCapture:{totalFrames:pilot.totalFrames,retainedFrames:pilot.retainedFrames,note:'UI operation was delayed. Bounded log retained only the last 7200 paused frames. Preserved as exploratory data; not used to represent active battle performance.'},files};
await writeFile(new URL('reports/robot-cover-public-browser-verification.json',root),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,uiKills:2,finiteCaptureCount:result.finiteCaptureCount,frame:result.frame,initialLongCapture:result.initialLongCapture},null,2));
