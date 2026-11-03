// Original family input bits -> shipped shared C++ ABI -> output endpoint bits.
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const [geometryPath,indexPath]=process.argv.slice(2);if(!geometryPath||!indexPath)throw new Error('usage: verify-optical-bounds-wasm.mjs geometry.csv index.csv');
const runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});
const decode=x=>Buffer.from(x.padStart(16,'0'),'hex').readDoubleBE(),encode=x=>{const b=Buffer.alloc(8);b.writeDoubleBE(x);return b.toString('hex');};
const rows=async path=>(await readFile(path,'utf8')).trim().split(/\r?\n/).slice(1).map(l=>l.split(','));
const power=r=>['reflectanceS','transmittanceS','reflectanceP','transmittanceP'].flatMap(key=>r.power[key]);
const verify=(actual,expected,label)=>assert.deepEqual(actual.map(encode),expected.map(x=>x.padStart(16,'0')),label);
let geometryBits=0,indexBits=0;
const geometric=await rows(geometryPath);assert.equal(geometric.length,302);
for(const [j,c]of geometric.entries()){
  const [lo,hi,dl,dh,value]=c.slice(2,7).map(decode);let values;
  if(['P','Q','C'].includes(c[0])){
    const shape=c[0]==='P'?{kind:'disk',center:[0,0,value],normal:[0,0,-2],apertureRadius:2}:c[0]==='Q'?{kind:'sphere',center:[0,0,0],radius:value}:
      {kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:2,apertureRadius:1};
    const r=runtime.queryBoundedSurface({origin:[0,0,[lo,hi]],direction:[0,0,[dl,dh]],minimumParameter:0,maximumParameter:100},shape);
    assert.equal(r.status,'hit');values=[...r.hit.parameter,...r.hit.physicalDistance,...r.hit.position.flat()];
    if(c[0]!=='P')values.push(...r.candidates.flatMap(x=>x.parameter));
    if(c[0]==='C'){assert.equal(r.candidates[0].state,'rejected_cap');assert.equal(r.candidates[1].state,'accepted');}
  }else{
    assert.ok(c[0]==='B'||c[0]==='N');const r=runtime.queryBoundedInterface(c[0]==='B'?{incident:[3,-4,0],normal:[0,1,0],indexIncident:4,indexTransmitted:3}:
      {incident:[0,[-4,-2],0],normal:[0,[2,3],0],indexIncident:1,indexTransmitted:1.5});
    assert.equal(r.kind,'transmission');values=[...r.transmitted.flat(),...r.reflected.flat(),...power(r)];
  }
  verify(values,c.slice(7),'geometry family '+j);geometryBits+=values.length;
}
const indexed=await rows(indexPath);assert.equal(indexed.length,111);
for(const [j,c]of indexed.entries()){
  assert.ok(['N','S','F'].includes(c[0]));const [nil,nih,ntl,nth,wavelength]=c.slice(2,7).map(decode);
  const r=runtime.queryBoundedInterface({incident:c[0]==='N'?[0,-1,0]:[3,-4,0],normal:[0,1,0],indexIncident:[nil,nih],indexTransmitted:[ntl,nth],vacuumWavelength:wavelength});
  assert.equal(r.kind,'transmission');const values=[...r.transmitted.flat(),...r.reflected.flat(),...power(r)];verify(values,c.slice(7),'index family '+j);indexBits+=values.length;
}
assert.equal(geometryBits,3760);assert.equal(indexBits,2220);
console.log(JSON.stringify({geometryFamilies:302,geometryEndpointBits:geometryBits,indexFamilies:111,indexEndpointBits:indexBits,backend:runtime.diagnostics.backend}));
