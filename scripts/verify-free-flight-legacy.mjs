// Preserve every exposed W1 SDK result before and after the private bridge.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const [input,output,baseline]=process.argv.slice(2);
assert.ok(input&&output,'usage: verify-free-flight-legacy.mjs legacy.json new-output-directory [baseline-directory]');
const hash=data=>({bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')});
const sourceBytes=await readFile(input),source=JSON.parse(sourceBytes);
assert.equal(source.schema,1);assert.equal(source.kind,'free-flight-legacy-world-fixtures');assert.equal(source.fixtures.length,20);
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url));
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(wasm)});
function serialize(value){
 if(typeof value==='number'){assert.ok(Number.isFinite(value));return Object.is(value,-0)?'-0':JSON.stringify(value);}
 if(value===null||typeof value!=='object')return JSON.stringify(value);
 if(Array.isArray(value))return '['+value.map(serialize).join(',')+']';
 return '{'+Object.entries(value).map(([k,v])=>JSON.stringify(k)+':'+serialize(v)).join(',')+'}';
}
const failures=['none','invalid_input','initial_contact','query_unresolved','event_budget','segment_budget','query_budget','root_budget','geometric_guard','propagation_failure','solver_failure','sustained_contact_required','numerical_failure'];
const results=[];let completed=0,rejected=0,hostRejected=0;
for(const item of source.fixtures){
 const world=runtime.createWorld({gravity:item.input.world.gravity});
 try{
  const nativeInput=item.input.world;
  for(const body of nativeInput.bodies)world.addBody({id:body.id,isStatic:body.isStatic,mass:body.mass,radius:body.radius,inertia:body.inertiaDiagonal,
   position:body.position,linearVelocity:body.velocity,angularMomentum:body.angularMomentum,orientation:body.orientation,force:body.force,torque:body.torque,...body.material});
  for(const plane of nativeInput.planes)world.addPlane({...plane,...plane.material});
  const snapshot=()=>({info:world.info(),bodies:nativeInput.bodies.map(b=>world.getBody(b.id))});
  const before=snapshot(),settings={...item.input.settings,...item.input.settings.solver,maxContacts:8192};delete settings.solver;
  // The established ABI caps contacts at8192; preserve the explicit SDK profile
  // alongside the original Native profile16384. No input/profile identity claim.
  const record={name:item.name,originalInput:item.input,sdkSettings:settings,before};
  let result;
  try{result=world.stepContinuous(item.input.duration,settings);}
  catch(error){
   assert.equal(item.input.duration,0,'Only the independently declared zero-duration host gate may reject');
   record.hostError=String(error.message);++hostRejected;
  }
  const after=snapshot();record.after=after;
  if(result){
   record.result=result;assert.equal(result.success,item.report.success,item.name);assert.equal(result.failure,failures[item.report.failure],item.name);
   assert.equal(result.events.length,item.report.events.length,item.name);
   if(result.success)++completed;else{++rejected;assert.deepStrictEqual(after,before,item.name+' model rollback');}
  }else assert.deepStrictEqual(after,before,item.name+' host rollback');
  results.push(record);
 }finally{world.dispose();}
}
assert.equal(completed,14);assert.equal(rejected,5);assert.equal(hostRejected,1);
let numbers=0,negativeZeros=0;
function compare(a,b,label){
 assert.equal(typeof a,typeof b,label);
 if(typeof a==='number'){assert.ok(Object.is(a,b),label+' changed numeric bits');++numbers;if(Object.is(a,-0))++negativeZeros;return;}
 if(a===null||typeof a!=='object'){assert.strictEqual(a,b,label);return;}
 assert.equal(Array.isArray(a),Array.isArray(b),label);assert.deepStrictEqual(Object.keys(a),Object.keys(b),label+' keys/order');
 for(const key of Object.keys(a))compare(a[key],b[key],label+'/'+key);
}
if(baseline){
 const previous=JSON.parse(await readFile(path.join(baseline,'results.json'),'utf8'));
 compare(results,previous,'all W1 SDK fields');
}
await mkdir(output,{recursive:true});
try{await access(path.join(output,'results.json'));throw Error('Refusing to overwrite captured W1 results');}catch(error){if(error.code!=='ENOENT')throw error;}
const data=Buffer.from(serialize(results)+'\n');await writeFile(path.join(output,'results.json'),data);
const report={schema:1,status:'PASS',source:hash(sourceBytes),wasm:hash(wasm),fixtures:20,completed,modelRejected:rejected,hostRejected,
 comparedToBaseline:Boolean(baseline),numericBits:numbers,negativeZeroBits:negativeZeros,results:hash(data),
 scope:'All API-exposed W1 output/body/clock fields compared on the same actual WASM backend. Native full diagnostics and pointer preservation are a separate corpus. The SDK profile explicitly uses its8192 contact cap; the zero-duration case is a host rejection, not a model result.'};
await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
