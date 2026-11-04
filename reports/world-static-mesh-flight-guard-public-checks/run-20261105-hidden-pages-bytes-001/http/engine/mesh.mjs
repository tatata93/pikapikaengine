// Editable source geometry uses SI metres and right-handed winding.
// It stays indexed; flat-shaded GPU buffers are a derived representation.
export const MESH_LIMITS=Object.freeze({vertices:65536,triangles:131072,coordinate:1e6,minCrossSquared:1e-24});
const vector=value=>Array.isArray(value)&&value.length===3&&[0,1,2].every(i=>Number.isFinite(value[i])&&Math.abs(value[i])<=MESH_LIMITS.coordinate);
function normal(a,b,c) {
  const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2];
  const vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];
  return [uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx];
}
const crossSquared=n=>n[0]*n[0]+n[1]*n[1]+n[2]*n[2];

export function validateMesh(mesh) {
  if(mesh?.version!==1)throw new Error('Unsupported mesh version; expected 1');
  if(!Array.isArray(mesh.positions)||mesh.positions.length<3||mesh.positions.length>MESH_LIMITS.vertices)throw new Error('Mesh vertex count must be 3..65536');
  if(!Array.isArray(mesh.triangles)||mesh.triangles.length<1||mesh.triangles.length>MESH_LIMITS.triangles)throw new Error('Mesh triangle count must be 1..131072');
  const positions=Array.from(mesh.positions,(p,i)=>{
    if(!vector(p))throw new Error(`Invalid mesh position ${i}; finite SI coordinates within +/-1000000 required`);
    return [...p];
  });
  const floatPositions=positions.map(p=>p.map(Math.fround));
  const triangles=Array.from(mesh.triangles,(triangle,i)=>{
    if(!Array.isArray(triangle)||triangle.length!==3||![0,1,2].every(j=>Number.isInteger(triangle[j])&&triangle[j]>=0&&triangle[j]<positions.length))throw new Error(`Invalid mesh triangle indices: ${i}`);
    if(new Set(triangle).size!==3)throw new Error(`Degenerate mesh triangle: ${i}`);
    const [a,b,c]=triangle;
    if(crossSquared(normal(positions[a],positions[b],positions[c]))<=MESH_LIMITS.minCrossSquared)throw new Error(`Zero-area or numerically degenerate mesh triangle: ${i}`);
    if(crossSquared(normal(floatPositions[a],floatPositions[b],floatPositions[c]))===0)throw new Error(`Mesh triangle collapses at Float32 render precision: ${i}`);
    return [...triangle];
  });
  return {version:1,positions,triangles};
}

export function createBoxMesh(dimensions=[1,1,1]) {
  if(!vector(dimensions)||dimensions.some(x=>x<=0))throw new Error('Box dimensions must be finite positive metres within 1000000');
  const [x,y,z]=dimensions.map(value=>value/2);
  return validateMesh({version:1,positions:[[-x,-y,-z],[x,-y,-z],[x,y,-z],[-x,y,-z],[-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z]],
    triangles:[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,4,7],[0,7,3],[1,2,6],[1,6,5],[3,7,6],[3,6,2],[0,1,5],[0,5,4]]});
}

export function moveVertex(mesh,index,position) {
  const next=validateMesh(mesh);
  if(!Number.isInteger(index)||index<0||index>=next.positions.length)throw new Error('Mesh vertex index is out of range');
  if(!vector(position))throw new Error('Invalid mesh vertex position');
  next.positions[index]=[...position];
  return validateMesh(next);
}

export function compileMesh(mesh) {
  const source=validateMesh(mesh);
  const output=new Float32Array(source.triangles.length*3*6);
  let cursor=0;
  for(const triangle of source.triangles) {
    const points=triangle.map(index=>source.positions[index].map(Math.fround));
    const face=normal(...points),length=Math.hypot(...face),unit=face.map(value=>value/length);
    for(const p of points){output.set(p,cursor);output.set(unit,cursor+3);cursor+=6;}
  }
  return output;
}

export function meshBounds(mesh) {
  const source=validateMesh(mesh);
  const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];
  for(const p of source.positions)for(let axis=0;axis<3;axis++){min[axis]=Math.min(min[axis],p[axis]);max[axis]=Math.max(max[axis],p[axis]);}
  return {min,max,center:min.map((value,axis)=>(value+max[axis])/2),size:min.map((value,axis)=>max[axis]-value)};
}
