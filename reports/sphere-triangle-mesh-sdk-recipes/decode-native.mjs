// Early decoder check with REAL Native packets. This is not a WASM execution.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {SimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson} from '../../engine/strict-json.mjs';
const root=new URL('../../',import.meta.url);
const bytes=await readFile(new URL('build/sphere-triangle-mesh-sdk-core/probe.json',root));
const native=parseStrictJson(bytes.toString());let decoded=0;
for(const row of native.fixtures){
  if(row.exchangeStatus)continue;
  let packet=row.summary;const indexed=new Map(row.rows.map(r=>[r.rowOrdinal,r]));
  const m={_pp_sim_api_version:()=>1,_pp_sim_sphere_triangle_mesh_begin:()=>0,_pp_sim_sphere_triangle_mesh_append:()=>0,
    _pp_sim_sphere_triangle_mesh:()=>{packet=row.summary;return 0;},
    _pp_sim_sphere_triangle_mesh_source:i=>{packet=row.sources[i];return 0;},
    _pp_sim_sphere_triangle_mesh_row:i=>{packet=indexed.get(i).packet;return 0;},
    _pp_sim_sphere_triangle_mesh_candidate:(i,j)=>{packet=indexed.get(i).candidates[j];return 0;}};
  const r=new SimulationRuntime(m,{},0,0);r.inputF64=values=>values.length;r.output=()=>[...packet];
  const p=row.input,sphere={position:p.slice(0,3),radius:p[3]},triangles=row.triangles.map(t=>({id:t[0],vertices:[t.slice(1,4),t.slice(4,7),t.slice(7,10)]}));
  const result=r.querySphereTriangleMesh(sphere,triangles,{maxSurfaces:p[4],primitive:{maxCandidates:p[5],sqrtRefinements:p[6],maxTotalSqrtRefinements:p[7],maximumLocalWidth:p[8],maximumNormalWidth:p[9],minimumSineSquared:p[10]}});
  assert.equal(result.rows.length,row.summary[4]);decoded++;
}
assert.equal(decoded,native.accepted);
const report={status:'PASS',decoded,scope:'Real Native packet decoder only, fake exchange methods; not a WASM result.'};
await writeFile(new URL('reports/sphere-triangle-mesh-sdk-native-decode.json',root),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
