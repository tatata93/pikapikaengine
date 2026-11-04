// Structural consistency boundary for the actual SDK DTO. This does not prove
// the provenance or numerical validity of an arbitrary caller-forged audit.
const privateData=new WeakMap();
const bad=message=>{throw new Error('Invalid completed derived render data: '+message);};
const integer=(x,max)=>Number.isSafeInteger(x)&&x>=0&&x<=max;
function floats(value,length,label){
  if(!(value instanceof Float32Array)||value.length!==length)bad(label+' must be Float32Array['+length+']');
  const copy=new Float32Array(value);if(!copy.every(Number.isFinite))bad(label+' must be finite');return copy;
}
function interval(value,label){
  if(!Array.isArray(value)||value.length!==2)bad(label+' bounds');
  const copy=Array.from(value);if(!copy.every(Number.isFinite)||copy[0]>copy[1])bad(label+' bounds');return copy;
}
function tripleBounds(value,label){if(!Array.isArray(value)||value.length!==3)bad(label+' shape');return Array.from(value,x=>interval(x,label));}
export function createDerivedMeshRenderData(result){
  if(result?.status!=='completed'||result.reason!=='none'||result.failedVertex!==null||result.failedFace!==null||!result.geometry)bad('successful complete SDK result required');
  const g=result.geometry;
  if(!Array.isArray(g.positions)||g.positions.length<3||g.positions.length>2048||!Array.isArray(g.triangles)||g.triangles.length<1||g.triangles.length>32768)bad('SDK counts exceed 2048 vertices / 32768 triangles');
  const vertexCount=g.positions.length,triangleCount=g.triangles.length,floatCount=triangleCount*18;
  if(!Array.isArray(result.audits)||result.audits.length!==triangleCount||!integer(result.sqrtRefinements,triangleCount*512)||!integer(result.sqrtLimitedFaces,triangleCount))bad('audit counts');
  const vertices=floats(g.interleaved,floatCount,'interleaved'),minimum=floats(g.minimum,3,'minimum'),maximum=floats(g.maximum,3,'maximum');
  for(let axis=0;axis<3;++axis)if(minimum[axis]>maximum[axis]||Math.abs(minimum[axis])>1e6||Math.abs(maximum[axis])>1e6)bad('local bounds');
  const positions=Array.from(g.positions,p=>floats(p,3,'position'));
  for(const p of positions)for(let axis=0;axis<3;++axis)if(Math.abs(p[axis])>1e6||p[axis]<minimum[axis]||p[axis]>maximum[axis])bad('position outside local bounds');
  let sqrtTotal=0,limitedTotal=0;
  for(let face=0;face<triangleCount;++face){
    const input=g.triangles[face];if(!(input instanceof Uint32Array)||input.length!==3)bad('triangle typed shape');const t=new Uint32Array(input);
    if(t.some(index=>index>=vertexCount)||new Set(t).size!==3)bad('triangle indices');
    const a=result.audits[face];if(!a||a.face!==face||!integer(a.sqrtRefinements,512)||typeof a.sqrtRefinementLimited!=='boolean')bad('face audit');
    const cross=tripleBounds(a.cross,'cross'),q=interval(a.squaredCross,'cross squared');tripleBounds(a.normalized,'normalized');
    if(q[0]<=1e-24||!cross.some(([lo,hi])=>lo>0||hi<0))bad('missing area evidence');
    const normal=floats(a.normal,3,'normal');
    if(!normal.some(x=>Math.abs(x)>=.5)||normal.some(x=>Math.abs(x)>1.000001))bad('normal component range');
    if(!Array.isArray(a.normalError)||a.normalError.length!==3||!Array.from(a.normalError).every(e=>Number.isFinite(e)&&e>=0&&e<=1e-6))bad('normal error evidence');
    for(let corner=0;corner<3;++corner)for(let axis=0;axis<3;++axis){
      if(!Object.is(vertices[face*18+corner*6+axis],positions[t[corner]][axis]))bad('expanded position/order');
      if(!Object.is(vertices[face*18+corner*6+3+axis],normal[axis]))bad('expanded flat normal');
    }
    sqrtTotal+=a.sqrtRefinements;if(a.sqrtRefinementLimited)++limitedTotal;
  }
  if(sqrtTotal!==result.sqrtRefinements||limitedTotal!==result.sqrtLimitedFaces)bad('audit totals');
  const descriptor=Object.freeze({vertexCount,triangleCount,floatCount});privateData.set(descriptor,vertices);return descriptor;
}
// The private upload bytes are never returned by reference, including to the
// renderer. Public copies may be changed without modifying the opaque token.
export function derivedMeshRenderInfo(descriptor){if(!privateData.has(descriptor))bad('opaque descriptor required');return descriptor;}
export function copyDerivedMeshRenderVertices(descriptor){derivedMeshRenderInfo(descriptor);return new Float32Array(privateData.get(descriptor));}
