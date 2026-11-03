import assert from 'node:assert/strict';
import {defaultSkinBindingSource,evaluateSkinBinding,serializeSkinBindingSource} from '../engine/skin-binding.mjs';

const defaults={maxVertices:2048,maxTriangles:32768,sqrtRefinements:128};
const normal=(name,input,recipe)=>({name,input,settings:{...defaults},expectation:{kind:'completed',status:'completed',reason:'none'},recipe});
const unit=()=>({positions:[[0,0,0],[1,0,0],[0,1,0]],triangles:[[0,1,2]]});
function rationalFaces(count){
 const positions=[],triangles=[];
 for(let j=0;j<count;++j){const x=j/8;positions.push([x,-0,0],[x+1/16,0,0],[x,4/16,-3/16]);triangles.push([3*j,3*j+1,3*j+2]);}
 return {positions,triangles};
}
function grid(count,width,height){
 const positions=[],tiles=[];
 for(let y=0;y<height;++y)for(let x=0;x<width;++x){const u=x/32,v=y/16;positions.push([2*u+v/4,v/2+u/8,(x%7)/64+(y%5)/32+x*y/4096]);}
 for(let y=0;y<height-1;++y)for(let x=0;x<width-1;++x){const a=y*width+x,b=a+1,c=a+width,d=c+1;tiles.push([a,b,d],[a,d,c]);}
 // Large cases repeat the explicit indexed tile set to exercise all requested
 // faces within the 2048-source-vertex SDK limit. No duplicate face is removed.
 return {positions,triangles:Array.from({length:count},(_,j)=>[...tiles[j%tiles.length]])};
}
export function createDerivedProfileCases(runtime,{quick=false,now=()=>performance.now()}={}){
 let begin=now();const source=defaultSkinBindingSource(runtime),sourceSetupMs=now()-begin;
 const authorSourceBefore=serializeSkinBindingSource(source);begin=now();
 const state=evaluateSkinBinding(runtime,source,1),sourceEvaluationMs=now()-begin;
 assert.equal(state.deformation.status,'completed','Actual Source FK/LBS preparation must succeed');
 const authorSourceAfter=serializeSkinBindingSource(source);assert.equal(authorSourceAfter,authorSourceBefore,'Author Source changed during case preparation');
 const cases=[normal('actual-source-4',{positions:state.deformation.positions,triangles:source.mesh.triangles},'Original six-vertex arm at t=1 s, actual C++ rest/current FK and LBS; four faces.'),
  normal('rational-normal-64',rationalFaces(64),'64 distinct translated faces with exact oriented normal (0,3/5,4/5) before f32 candidate rounding.'),
  normal('sheared-grid-512',grid(512,32,16),'512 explicit faces of a nonuniformly scaled, sheared grid with varied dyadic heights; 512 source vertices.')];
 if(!quick)cases.push(normal('sheared-grid-4096',grid(4096,64,32),'4096 explicit faces cycling a 3906-face varied dyadic grid; 2048 source vertices.'),normal('sheared-grid-32768',grid(32768,64,32),'32768 explicit faces cycling a 3906-face varied dyadic grid; 2048 source vertices. Repeated faces are deliberate, not a unique-surface workload.'));
 cases.push(
  {name:'expected-area-quality',input:{positions:[[0,0,0],[2**-21,0,0],[0,2**-21,0]],triangles:[[0,1,2]]},settings:{...defaults},expectation:{kind:'model_failure',status:'quality_rejected',reason:'below_area_floor'},recipe:'Exact squared cross 2^-84 is below the binary64 1e-24 quality floor.'},
  {name:'expected-normal-budget',input:unit(),settings:{...defaults,sqrtRefinements:1},expectation:{kind:'model_failure',status:'quality_unresolved',reason:'normal_uncertain'},recipe:'One refinement per sqrt endpoint cannot certify the candidate error for this unit face.'},
  {name:'expected-degenerate',input:{positions:[[0,0,0],[1,0,0],[2,0,0]],triangles:[[0,1,2]]},settings:{...defaults},expectation:{kind:'model_failure',status:'degenerate',reason:'zero_cross'},recipe:'Three exactly collinear distinct indexed points.'},
  {name:'expected-host-2049',input:{positions:[...unit().positions,...Array.from({length:2046},()=>[0,0,0])],triangles:[[0,1,2]]},settings:{...defaults},expectation:{kind:'host_rejection'},recipe:'2049 positions exceed the actual SDK capacity before any C++ query.'},
  normal('recovery-unit',unit(),'A final successful query on the same runtime after all expected failures.'));
 return {cases,verifySourceUnchanged:()=>assert.equal(serializeSkinBindingSource(source),authorSourceBefore,'Author Source changed during derived profiling'),sourcePreparation:{sourceSetupMs,sourceEvaluationMs,sampleSeconds:1,loop:false,authorSourceBefore,authorSourceAfter,sourceUnchanged:true,deformationStatus:state.deformation.status,
  scope:'Case preparation only; Source construction includes real bind/rest FK, evaluation includes real C++ rest/current FK and LBS plus authoring validation. These are not derived-query stage timings.'}};
}
