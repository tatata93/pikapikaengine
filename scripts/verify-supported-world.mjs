import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const source=process.argv[2];if(!source)throw new Error('usage: verify-supported-world.mjs native-executable-or-fixtures.json [report.json]');
const fixtures=JSON.parse(source.endsWith('.json')?await readFile(source,'utf8'):execFileSync(path.resolve(source),['--fixtures'],{encoding:'utf8',maxBuffer:8*1024*1024,timeout:60000}));
assert.equal(fixtures.version,1);assert.equal(fixtures.model,'W2 normal-only RATTLE plus audited numerical paths');assert.equal(fixtures.fixtures.length,17);
assert.deepEqual(fixtures.fixtures.map(x=>x.name).sort(),['floor-torque','stack','wedge','wedge-release','active-set-counterexample','return-and-rest','supported-collision','fast-crossing','curved-release','terminal-impact','tiny-cold-newton','segment-budget','attempt-budget','guard-budget','impact-then-rollback','friction-rejected','penetrated-rejected'].sort());
const wasm=await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url)),runtime=await loadSimulationRuntime({wasmBytes:wasm}),m=runtime.native;
let numericalValues=0,maxAbsoluteError=0,maxNormalizedError=0,counterDifferences=0,repairEventCountDifferences=0;
const compare=(a,b,label)=>{assert.equal(a.length,b.length,label);a.forEach((x,j)=>{assert.ok(Number.isFinite(x)&&Number.isFinite(b[j]),label);++numericalValues;const d=Math.abs(x-b[j]);maxAbsoluteError=Math.max(maxAbsoluteError,d);maxNormalizedError=Math.max(maxNormalizedError,d/Math.max(1,Math.abs(x),Math.abs(b[j])));assert.ok(d<=1e-8+1e-9*Math.max(Math.abs(x),Math.abs(b[j])),`${label}[${j}]: ${x} / ${b[j]}`);});};
const body=(w,id)=>{runtime.check(m._pp_sim_world_body_get(w,id));return runtime.output();};
const outcomes=[],actualFixtures=[];
for(const f of fixtures.fixtures){
  const input=f.input;assert.equal(input.settings.length,33);assert.ok(input.dt>=2e-12&&input.dt<=.1);assert.ok(f.steps.length>=1&&f.steps.length<=input.ticks);
  const w=runtime.handle(m._pp_sim_world_create());
  const actualFixture={name:f.name,input,steps:[]};actualFixtures.push(actualFixture);
  try{
    runtime.check(m._pp_sim_world_set_gravity(w,runtime.inputF64(input.gravity)));
    for(const b of input.bodies)runtime.check(m._pp_sim_world_body_add(w,runtime.inputF64(b)));
    for(const p of input.planes)runtime.check(m._pp_sim_world_plane_add(w,runtime.inputF64(p)));
    for(const [tick,expected] of f.steps.entries()){
      for(const b of input.bodies){const current=body(w,b[0]);current.splice(20,6,...b.slice(20,26));runtime.check(m._pp_sim_world_body_set(w,runtime.inputF64(current.slice(0,28))));}
      const before=input.bodies.map(b=>body(w,b[0]));before.forEach((b,j)=>compare(b,expected.before[j],`${f.name}/${tick}/before${j}`));
      runtime.check(m._pp_sim_world_step_supported(w,input.dt,runtime.inputF64(input.settings)));const summary=runtime.output();assert.equal(summary.length,32);
      const counters=new Set([4,5,6,7,8,9,10]);for(const j of counters){assert.ok(Number.isSafeInteger(summary[j])&&summary[j]>=0);if(summary[j]!==expected.summary[j])++counterDifferences;}
      assert.ok(summary[4]<=input.settings[9]&&summary[5]<=input.settings[10]&&summary[6]<=summary[4]&&summary[8]<=input.settings[12]&&summary[9]<=input.settings[13]&&summary[10]<=summary[9]);
      for(const j of [0,1,28,29,31])assert.equal(summary[j],expected.summary[j],`${f.name} enum/ID/clock ${j}`);
      // Residual/work/state comparisons; iteration/tree counts may differ
      // between conforming native toolchains and remain explicitly bounded.
      compare(summary.filter((_,j)=>!counters.has(j)&&j!==27),expected.summary.filter((_,j)=>!counters.has(j)&&j!==27),`${f.name}/${tick}/summary`);
      assert.ok(Number.isSafeInteger(summary[27])&&summary[27]>=0&&summary[27]<=input.settings[11]);
      const events=[];for(let j=0;j<summary[27];++j){runtime.check(m._pp_sim_world_supported_event(w,j));const e=runtime.output();assert.equal(e.length,12);assert.ok(e.every(Number.isFinite));assert.ok([0,1,2].includes(e[0])&&e[1]>=0&&e[1]<=input.dt);assert.ok(Number.isSafeInteger(e[7])&&e[7]>=0&&e[7]<=input.settings[17]);assert.ok(e[8]>=0&&e[10]<=e[9]+input.settings[8]*Math.max(1,e[9]));events.push(e);}
      const significant=events.filter(e=>e[0]!==1),reference=expected.events.filter(e=>e[0]!==1);assert.equal(significant.length,reference.length,`${f.name} impact/release count`);
      for(const [j,e]of reference.entries()){compare(significant[j],e,`${f.name}/${tick}/impact-or-release${j}`);for(const k of [0,2,3,7])assert.equal(significant[j][k],e[k]);}
      // Signs of rounded tangent dot products can differ at ~1e-16. Keep every
      // repair in the raw evidence; compare its total impulse/energy effects,
      // not the number of times a negative residual crossed exactly zero.
      const repairs=events.filter(e=>e[0]===1),referenceRepairs=expected.events.filter(e=>e[0]===1);
      if(repairs.length!==referenceRepairs.length)++repairEventCountDifferences;
      compare([repairs.reduce((x,e)=>x+e[8],0),repairs.reduce((x,e)=>x+e[10]-e[9],0)],
        [referenceRepairs.reduce((x,e)=>x+e[8],0),referenceRepairs.reduce((x,e)=>x+e[10]-e[9],0)],`${f.name}/${tick}/repair-effects`);
      const after=input.bodies.map(b=>body(w,b[0]));after.forEach((b,j)=>compare(b,expected.after[j],`${f.name}/${tick}/after${j}`));
      actualFixture.steps.push({before,summary,events,after});
      if(summary[0]===0){assert.equal(summary[2],0);assert.deepEqual(after,before,`${f.name} rollback`);}else{assert.equal(summary[2],input.dt);assert.equal(summary[31],tick+1);for(const b of after)assert.ok(b.slice(20,26).every(x=>x===0),'single load consumption');}
      outcomes.push({name:f.name,tick,success:Boolean(summary[0]),failure:summary[1],segments:summary[5],events:summary[27],rollback:summary[0]===0});
    }
  }finally{runtime.check(m._pp_sim_world_destroy(w));}
}
const report={verification:'Complete raw Native W2 inputs replayed through shipped C++ WebAssembly ABI',fixtures:17,ticks:outcomes.length,numericalValues,maxAbsoluteError,maxNormalizedError,counterDifferences,repairEventCountDifferences,wasmBytes:wasm.length,wasmSha256:createHash('sha256').update(wasm).digest('hex'),outcomes,
  limits:'Finite comparative evidence. Repair counts may differ with rounded residual signs; raw repairs and aggregate effects are retained. Independent analytic cases reside in supported_world_tests. Dense-path geometry certification does not bound the true continuous mechanical trajectory.'};
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
if(process.argv[4])await writeFile(process.argv[4],JSON.stringify({version:1,model:fixtures.model,fixtures:actualFixtures})+'\n');
