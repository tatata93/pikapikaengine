import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {createDerivedGPUProfileCases} from '../tools/derived-gpu-cases.mjs';
import {createDerivedMeshRenderData,copyDerivedMeshRenderVertices} from '../engine/derived-render.mjs';

test('Browser GPU inputs use actual Source/FK/LBS and distinct finite bounded faces without changing author data',async()=>{
  const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
  let tick=0;const setup=createDerivedGPUProfileCases(runtime,{now:()=>++tick});
  assert.deepEqual(setup.cases.map(x=>[x.input.positions.length,x.input.triangles.length]),[[6,4],[192,64],[512,512]]);
  assert.equal(setup.sourcePreparation.sourceSetupMs,1);assert.equal(setup.sourcePreparation.sourceEvaluationMs,1);
  assert.equal(setup.sourcePreparation.authorSourceBefore,setup.sourcePreparation.authorSourceAfter);
  for(const item of setup.cases){
    const snapshot=structuredClone(item.input),settings=structuredClone(item.settings),r=runtime.prepareDerivedMesh(item.input,item.settings);
    assert.equal(r.status,'completed',item.name);assert.equal(r.geometry.triangles.length,item.input.triangles.length);
    assert.equal(new Set(item.input.triangles.map(t=>t.join(','))).size,item.input.triangles.length);
    const token=createDerivedMeshRenderData(r),bytes=copyDerivedMeshRenderVertices(token);
    assert.equal(bytes.byteLength,item.input.triangles.length*72);assert.deepEqual(item.input,snapshot);assert.deepEqual(item.settings,settings);
  }
  const r=runtime.prepareDerivedMesh(setup.cases[1].input,setup.cases[1].settings);
  for(const audit of r.audits){assert.ok(Math.abs(audit.normal[0])<=1e-6);assert.ok(Math.abs(audit.normal[1]-3/5)<=1e-6);assert.ok(Math.abs(audit.normal[2]-4/5)<=1e-6);}
  assert.equal(setup.verifySourceUnchanged(),true);
});
