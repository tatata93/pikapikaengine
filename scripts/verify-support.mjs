import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import assert from 'node:assert/strict';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const input=process.argv[2];if(!input)throw new Error('usage: verify-support.mjs native-executable-or-fixtures.json [report.json]');
const source=JSON.parse(input.endsWith('.json')?await readFile(input,'utf8'):execFileSync(path.resolve(input),['--fixtures'],{encoding:'utf8'}));
assert.equal(source.version,1);assert.equal(source.model,'normal-only acceleration support, no integration');assert.equal(source.fixtures.length,12);
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const failures=['none','invalid_input','geometry_incompatible','geometry_uncertain','impact_required','velocity_uncertain','static_constraint','pair_budget','contact_budget','ill_conditioned','iteration_budget','numerical_uncertainty','numerical_failure'];
let numericalValues=0,maxAbsoluteError=0,maxNormalizedError=0;const cases=[];
function compare(a,b,label){
  if(Array.isArray(a)){assert.equal(a.length,b.length,label);a.forEach((x,j)=>compare(x,b[j],label+'/'+j));return;}
  assert.ok(Number.isFinite(a)&&Number.isFinite(b),label);const error=Math.abs(a-b),scale=Math.max(1,Math.abs(a),Math.abs(b));
  ++numericalValues;maxAbsoluteError=Math.max(maxAbsoluteError,error);maxNormalizedError=Math.max(maxNormalizedError,error/scale);
  assert.ok(error<=1e-8+1e-10*scale,`${label}: ${a} != ${b}`);
}
const zipped=(lower,upper)=>lower.map((lo,k)=>[lo,upper[k]]);
for(const f of source.fixtures){
  const world=runtime.createWorld({gravity:f.input.world.gravity});try{
    for(const b of f.input.world.bodies)world.addBody({...b,linearVelocity:b.velocity,...b.material});
    for(const p of f.input.world.planes)world.addPlane({...p,...p.material});
    const state=()=>JSON.stringify({info:world.info(),bodies:f.input.world.bodies.map(b=>world.getBody(b.id))}),before=state();
    const actual=world.querySupport(f.input.settings),expected=f.result;
    assert.equal(state(),before,`${f.name}: no state/load/time mutation`);assert.equal(f.worldUnchanged,true);
    assert.equal(actual.success,expected.success,f.name);assert.equal(actual.failure,failures[expected.failure],f.name);
    for(const key of ['firstId','secondId','pairQueries','separatedPairs','restingConstraints','separatingConstraints'])assert.equal(actual[key],expected[key],f.name+'/'+key);
    assert.ok(actual.iterations<=f.input.settings.maxIterations,'bounded iteration count');
    for(const key of ['maximumGeometryOffset','maximumVelocityIntervalWidth','minimumScaledPivot'])compare(actual[key],expected[key],f.name+'/'+key);
    for(const key of Object.keys(expected.residuals))compare(actual.residuals[key],expected.residuals[key],f.name+'/residual/'+key);
    assert.equal(actual.constraints.length,expected.constraints.length);assert.equal(actual.bodies.length,expected.bodies.length);
    actual.constraints.forEach((a,j)=>{
      const b=expected.constraints[j];assert.equal(a.firstId,b.firstId);assert.equal(a.secondId,b.secondId);assert.equal(a.phase,b.phase===0?'resting':'separating');assert.equal(a.guardedGeometry,b.guardedGeometry);
      for(const key of ['normal','gap','normalVelocity','curvature','freeNormalAcceleration','lambda','normalAcceleration','accelerationBounds'])compare(a[key],b[key],`${f.name}/constraint${j}/${key}`);
      compare(a.normalBounds,zipped(b.normalLower,b.normalUpper),f.name+'/normalBounds');
    });
    actual.bodies.forEach((a,j)=>{const b=expected.bodies[j];assert.equal(a.id,b.id);
      for(const key of ['force','normalTorque','acceleration'])compare(a[key],b[key],`${f.name}/body${j}/${key}`);
      compare(a.forceBounds,zipped(b.forceLower,b.forceUpper),f.name+'/forceBounds');compare(a.accelerationBounds,zipped(b.accelerationLower,b.accelerationUpper),f.name+'/accelerationBounds');
    });
    assert.equal(actual.queryTime,0);assert.equal(actual.queryTicks,0);
    if(actual.success){assert.ok(actual.residuals.negativeAcceleration<=f.input.settings.accelerationTolerance);assert.ok(actual.residuals.complementarity<=f.input.settings.complementarityTolerance);assert.ok(actual.residuals.projectedForce<=f.input.settings.projectedForceTolerance);}
    cases.push({name:f.name,success:actual.success,failure:actual.failure,iterations:actual.iterations,worldUnchanged:true});
  }finally{world.dispose();}
}
const report={verification:'Complete Native inputs replayed through shipped C++ WASM support API',fixtures:cases.length,numericalValues,maxAbsoluteError,maxNormalizedError,cases,
  limits:'Comparative finite corpus; independent analytic correctness resides in support_tests. Guard-band normal support only; no World integration or friction.'};
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
