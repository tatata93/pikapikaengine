import {defaultSkinBindingSource,evaluateSkinBinding,serializeSkinBindingSource} from '../engine/skin-binding.mjs';

// Original finite inputs for a browser-only experiment. All coordinates below
// are dyadic. They are not imported models or calibrated character workloads.
const settings=()=>({maxVertices:2048,maxTriangles:32768,sqrtRefinements:128});
function rationalFaces(){
  const positions=[],triangles=[];
  for(let j=0;j<64;++j){const x=j/8;positions.push([x,-0,0],[x+1/16,0,0],[x,4/16,-3/16]);triangles.push([3*j,3*j+1,3*j+2]);}
  return {positions,triangles};
}
function grid(){
  const positions=[],triangles=[];
  for(let y=0;y<16;++y)for(let x=0;x<32;++x){const u=x/32,v=y/16;positions.push([2*u+v/4,v/2+u/8,(x%7)/64+(y%5)/32+x*y/4096]);}
  for(let y=0;y<15&&triangles.length<512;++y)for(let x=0;x<31&&triangles.length<512;++x){const a=y*32+x,b=a+1,c=a+32,d=c+1;triangles.push([a,b,d],[a,d,c]);}
  return {positions,triangles};
}
export function createDerivedGPUProfileCases(runtime,{now=()=>performance.now()}={}){
  let begin=now();const source=defaultSkinBindingSource(runtime),sourceSetupMs=now()-begin;
  const authorSourceBefore=serializeSkinBindingSource(source);begin=now();
  const state=evaluateSkinBinding(runtime,source,1),sourceEvaluationMs=now()-begin;
  if(state.deformation.status!=='completed')throw new Error('Original Source FK/LBS must complete before GPU profiling');
  const authorSourceAfter=serializeSkinBindingSource(source);
  if(authorSourceAfter!==authorSourceBefore)throw new Error('Author Source changed during case preparation');
  const cases=[
    {name:'actual-source-4',input:{positions:state.deformation.positions,triangles:source.mesh.triangles},settings:settings(),recipe:'Original six-vertex arm at t=1 s; real C++ bind/rest/current FK and LBS, four faces.'},
    {name:'rational-normal-64',input:rationalFaces(),settings:settings(),recipe:'64 distinct translated faces, 192 vertices; exact pre-rounding oriented normal (0,3/5,4/5).'},
    {name:'sheared-grid-512',input:grid(),settings:settings(),recipe:'512 distinct faces of a 32 by 16 dyadic grid, 512 vertices, nonuniform scale/shear and varied height.'}
  ];
  const sourcePreparation={sourceSetupMs,sourceEvaluationMs,sampleSeconds:1,loop:false,authorSourceBefore,authorSourceAfter,sourceUnchanged:true,deformationStatus:state.deformation.status,
    scope:'Source setup includes validation and real bind/rest FK; evaluation includes real FK/LBS and authoring validation. Separate from derived query and GPU timing.'};
  return {cases,sourcePreparation,verifySourceUnchanged(){if(serializeSkinBindingSource(source)!==authorSourceBefore)throw new Error('Author Source changed during profiling');return true;}};
}
