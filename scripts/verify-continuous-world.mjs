import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import assert from 'node:assert/strict';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const input=process.argv[2];if(!input)throw new Error('usage: verify-continuous-world.mjs native-executable-or-fixture.json [report.json]');
const source=JSON.parse(input.endsWith('.json')?await readFile(input,'utf8'):execFileSync(path.resolve(input),['--fixtures'],{encoding:'utf8'}));
assert.equal(source.version,1);assert.equal(source.model,'held-load early-response W1');assert.equal(source.input.bodies.length,1);
const runtime=await loadSimulationRuntime({wasmBytes:new Uint8Array(await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)))});
function create(){
  const world=runtime.createWorld({gravity:source.input.gravity});
  try{
    for(const b of source.input.bodies)world.addBody({id:b.id,isStatic:b.isStatic,mass:b.mass,radius:b.radius,inertia:b.inertiaDiagonal,position:b.position,
      linearVelocity:b.velocity,angularMomentum:b.angularMomentum,orientation:b.orientation,force:b.force,torque:b.torque,...b.material});
    for(const p of source.input.planes)world.addPlane({id:p.id,normal:p.normal,offset:p.offset,...p.material});return world;
  }catch(error){world.dispose();throw error;}
}
let values=0,maxAbsoluteError=0,maxNormalizedError=0;
function compare(a,b,label){
  assert.ok(Number.isFinite(a)&&Number.isFinite(b),label);const error=Math.abs(a-b),normalized=error/Math.max(1,Math.abs(a),Math.abs(b));
  ++values;maxAbsoluteError=Math.max(maxAbsoluteError,error);maxNormalizedError=Math.max(maxNormalizedError,normalized);
  assert.ok(error<=1e-9+1e-10*Math.max(Math.abs(a),Math.abs(b)),`${label}: ${a} != ${b}`);
}
function counters(r){assert.ok(r.pairQueries<=100000&&r.rootEvaluations<=1000000&&r.freeSegments<=65,'bounded traversal counters');}
const world=create();let actual;
try{
  actual=world.stepContinuous(source.dt,source.settings);assert.equal(actual.success,source.success);assert.equal(actual.failure,'none');counters(actual);
  assert.equal(actual.events.length,source.events.length);assert.equal(actual.ticks,1);compare(actual.time,source.dt,'completed time');
  actual.events.forEach((e,i)=>{const n=source.events[i];assert.equal(e.contacts,n.contacts);
    for(const [a,b,label]of [[e.respondedAt,n.respondedAt,'response'],[e.entryBracket[0],n.entryLower,'entryLo'],[e.entryBracket[1],n.entryUpper,'entryHi'],
      [e.maximumGap,n.maximumGap,'gap'],[e.propagationError,n.propagationError,'propagation']])compare(a,b,`event${i}/${label}`);
    assert.ok(e.maximumGap<=source.settings.spatialTolerance&&e.propagationError>=0);
  });
  for(const b of source.bodies){const a=world.getBody(b.id);for(const [native,js]of [['position','position'],['velocity','linearVelocity'],['angularMomentum','angularMomentum'],['orientation','orientation'],['force','force'],['torque','torque']])
    b[native].forEach((x,i)=>compare(a[js][i],x,`body${b.id}/${native}/${i}`));}
  compare(actual.maximumPropagationError,source.maximumPropagationError,'maximum propagation');compare(actual.accumulatedPositionRoundoff,source.accumulatedPositionRoundoff,'accumulated roundoff');compare(actual.timeRoundoff,source.timeRoundoff,'time roundoff');
}finally{world.dispose();}
const refinement=[];
for(const item of source.refinement){const w=create();try{
  const r=w.stepContinuous(source.dt,{...source.settings,spatialTolerance:item.spaceTolerance});assert.equal(r.success,true);counters(r);assert.equal(r.events.length,item.eventCount);
  const x=w.getBody(1).position[0],error=Math.abs(x);compare(x,item.finalPositionX,'refined final position');
  refinement.push({spatialTolerance:item.spaceTolerance,absoluteFinalXError:error,eventCount:r.events.length});
}finally{w.dispose();}}
for(let i=1;i<refinement.length;++i)assert.ok(refinement[i].absoluteFinalXError<refinement[i-1].absoluteFinalXError,'independent corridor x=0 error decreases');
let rollback;
const failed=create();try{
  const before=JSON.stringify({info:failed.info(),bodies:source.input.bodies.map(b=>failed.getBody(b.id))});
  rollback=failed.stepContinuous(source.dt,{...source.settings,maxEventBatches:1});assert.equal(rollback.success,false);assert.equal(rollback.failure,'event_budget');assert.equal(rollback.advancedDt,0);
  assert.equal(JSON.stringify({info:failed.info(),bodies:source.input.bodies.map(b=>failed.getBody(b.id))}),before,'failed attempt retains every exposed state/load/clock');
}finally{failed.dispose();}
const result={verification:'Native held-load W1 fixtures through actual shared WASM World API',wasmBytes:runtime.wasmBytes,numericalValues:values,maxAbsoluteError,maxNormalizedError,
  events:actual.events.length,refinement,rollback:{failure:rollback.failure,advancedDt:rollback.advancedDt,candidateEvents:rollback.events.length,stateUnchanged:true},
  actualCounters:{queries:actual.pairQueries,evaluations:actual.rootEvaluations,segments:actual.freeSegments},
  limits:'Comparative results for this corridor; numerical parity is not independent dynamics proof. Initial support/tangent/uncertifiable contacts remain unsupported W1 failures.'};
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
