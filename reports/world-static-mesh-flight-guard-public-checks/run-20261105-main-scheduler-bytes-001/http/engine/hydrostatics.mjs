import {validateMesh} from './mesh.mjs';

// Y-up SI model: constant-density, still fluid under a horizontal plane.
// No fluid solver, moving free surface, air compression or structural damage.
const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
const vector=(v,n=3)=>Array.isArray(v)&&v.length===n&&Array.from({length:n},(_,i)=>i).every(i=>Number.isFinite(v[i]));
const boundedPosition=v=>vector(v)&&v.every(x=>Math.abs(x)<=1e6);
const positive=(value,name)=>{if(!Number.isFinite(value)||value<=0)throw new Error(`${name} must be finite and positive`);return value;};
const finiteOutput=(values)=>{if(!values.every(Number.isFinite))throw new Error('Fluid calculation exceeds finite numeric range');};
const accumulator=()=>({sum:0,correction:0});
function add(sum,value){const adjusted=value-sum.correction,next=sum.sum+adjusted;sum.correction=(next-sum.sum)-adjusted;sum.sum=next;}

export function hydrostaticPressure(depth,{density=1000,gravity=9.80665}={}) {
  if(!Number.isFinite(depth))throw new Error('Depth must be finite metres');
  positive(density,'Density');positive(gravity,'Gravity');
  const pressure=density*gravity*Math.max(0,depth);finiteOutput([pressure]);return pressure;
}

function closedSource(input) {
  const mesh=validateMesh(input),edges=new Map(),adjacency=mesh.triangles.map(()=>[]);
  for(let face=0;face<mesh.triangles.length;face++) {
    const [a,b,c]=mesh.triangles[face];
    for(const [i,j] of [[a,b],[b,c],[c,a]]) {
      const key=Math.min(i,j)*mesh.positions.length+Math.max(i,j);
      let edge=edges.get(key);
      if(!edge){edge={orientation:0,faces:[]};edges.set(key,edge);}
      edge.orientation+=i<j?1:-1;edge.faces.push(face);
      if(edge.faces.length>2)throw new Error('Displacement mesh has a non-manifold edge');
    }
  }
  for(const edge of edges.values()) {
    if(edge.faces.length!==2)throw new Error('Displacement mesh must be closed; boundary edge found');
    if(edge.orientation!==0)throw new Error('Displacement mesh has inconsistent triangle winding');
    const [a,b]=edge.faces;adjacency[a].push(b);adjacency[b].push(a);
  }
  const visited=new Uint8Array(mesh.triangles.length),volume=accumulator();let components=0;
  for(let start=0;start<visited.length;start++) {
    if(visited[start])continue;
    components++;const pending=[start],part=accumulator(),origin=mesh.positions[mesh.triangles[start][0]];
    visited[start]=1;
    while(pending.length) {
      const face=pending.pop(),[a,b,c]=mesh.triangles[face].map(index=>sub(mesh.positions[index],origin));
      add(part,dot(a,cross(b,c))/6);
      for(const neighbor of adjacency[face])if(!visited[neighbor]){visited[neighbor]=1;pending.push(neighbor);}
    }
    if(!(part.sum>0))throw new Error('Every displacement mesh shell must have positive signed volume and outward winding');
    add(volume,part.sum);
  }
  return {mesh,volume:volume.sum,components};
}

function transformedPositions(mesh,options) {
  const position=options.position??[0,0,0],scale=options.scale??[1,1,1];
  if(!boundedPosition(position))throw new Error('Position must be a finite world coordinate within +/-1000000 metres');
  if(!vector(scale)||scale.some(x=>x<=0||x>1e6))throw new Error('Scale must have three finite positive components within 1000000');
  let q=options.orientation;
  if(q!==undefined) {
    if(options.yaw!==undefined)throw new Error('Choose orientation quaternion or yaw, not both');
    if(!vector(q,4)||Math.abs(Math.hypot(...q)-1)>1e-10)throw new Error('Orientation must be a unit [x,y,z,w] quaternion');
  } else {
    const yaw=options.yaw??0;if(!Number.isFinite(yaw))throw new Error('Yaw must be finite radians');
    q=[0,Math.sin(yaw/2),0,Math.cos(yaw/2)];
  }
  const xyz=q.slice(0,3);
  const positions=mesh.positions.map(point=>{
    const p=point.map((value,i)=>value*scale[i]),uv=cross(xyz,p),uuv=cross(xyz,uv);
    const world=p.map((value,i)=>value+2*(q[3]*uv[i]+uuv[i])+position[i]);
    if(!boundedPosition(world))throw new Error('Transformed fluid mesh exceeds finite +/-1000000 metre world range');
    return world;
  });
  return {positions,position,scale};
}

// Sutherland-Hodgman clipping against y<=level, preserving face winding.
function wetPolygon(points,level) {
  const output=[];
  for(let i=0;i<points.length;i++) {
    const a=points[i],b=points[(i+1)%points.length],insideA=a[1]<=level,insideB=b[1]<=level;
    if(insideA)output.push(a);
    if(insideA!==insideB) {
      const t=(level-a[1])/(b[1]-a[1]);
      output.push([a[0]+t*(b[0]-a[0]),level,a[2]+t*(b[2]-a[2])]);
    }
  }
  return output;
}

export function hydrostaticForces(input,options={}) {
  if(!options||typeof options!=='object')throw new Error('Fluid options must be an object');
  const density=positive(options.density??1000,'Density'),gravity=positive(options.gravity??9.80665,'Gravity');
  const waterLevel=options.waterLevel??0;
  if(!Number.isFinite(waterLevel)||Math.abs(waterLevel)>1e6)throw new Error('Water level must be finite within +/-1000000 metres');
  const source=closedSource(input),{positions,position,scale}=transformedPositions(source.mesh,options);
  const centerOfMass=options.centerOfMass??position;
  if(!boundedPosition(centerOfMass))throw new Error('Center of mass must be a finite world position within +/-1000000 metres');
  const reference=[position[0],waterLevel,position[2]],force=[accumulator(),accumulator(),accumulator()],torque=[accumulator(),accumulator(),accumulator()];
  const wetArea=accumulator(),volume=accumulator(),firstMoment=[accumulator(),accumulator(),accumulator()];
  for(const face of source.mesh.triangles) {
    const polygon=wetPolygon(face.map(index=>positions[index]),waterLevel);
    for(let i=1;i+1<polygon.length;i++) {
      const points=[polygon[0],polygon[i],polygon[i+1]],areaVector=cross(sub(points[1],points[0]),sub(points[2],points[0])).map(value=>value/2);
      const area=Math.hypot(...areaVector);if(area===0)continue;
      const relative=points.map(p=>sub(p,reference)),h=relative.map(p=>p[1]),sumH=h[0]+h[1]+h[2];
      const pressure=h.map(depth=>-density*gravity*depth),sumP=pressure[0]+pressure[1]+pressure[2];
      const pressureMoment=[0,0,0];
      for(let vertex=0;vertex<3;vertex++)for(let axis=0;axis<3;axis++)pressureMoment[axis]+=(points[vertex][axis]-centerOfMass[axis])*(sumP+pressure[vertex])/12;
      const moment=cross(pressureMoment,areaVector);
      for(let axis=0;axis<3;axis++){add(force[axis],-areaVector[axis]*sumP/3);add(torque[axis],-moment[axis]);}
      add(wetArea,area);add(volume,areaVector[1]*sumH/3);
      // Exact barycentric quadratic integrals; the artificial y=level cap contributes zero.
      for(const axis of [0,2]) {
        const sum=relative[0][axis]+relative[1][axis]+relative[2][axis];
        const diagonal=relative.reduce((value,p,j)=>value+p[axis]*h[j],0);
        add(firstMoment[axis],areaVector[1]*(sum*sumH+diagonal)/12);
      }
      add(firstMoment[1],areaVector[1]*(sumH*sumH+h.reduce((sum,value)=>sum+value*value,0))/24);
    }
  }
  const resultant=force.map(value=>value.sum),resultTorque=torque.map(value=>value.sum);
  const submergedVolume=resultant[1]/(density*gravity);
  const centerOfBuoyancy=submergedVolume>0?firstMoment.map((value,i)=>reference[i]+value.sum/volume.sum):null;
  const totalVolume=source.volume*scale[0]*scale[1]*scale[2];
  finiteOutput([...resultant,...resultTorque,wetArea.sum,submergedVolume,totalVolume,...(centerOfBuoyancy??[])]);
  if(submergedVolume<0)throw new Error('Negative displaced volume; invalid shell or numerical conditioning');
  return {force:resultant,torque:resultTorque,wetArea:wetArea.sum,submergedVolume,centerOfBuoyancy,totalVolume,shells:source.components};
}

// A supplied-coefficient approximation, separate from hydrostatic pressure.
export function quadraticDrag({velocity,current=[0,0,0],density=1000,dragCoefficient,area}={}) {
  if(!vector(velocity)||!vector(current))throw new Error('Velocity and current require finite three-vectors in m/s');
  positive(density,'Density');
  if(!Number.isFinite(dragCoefficient)||dragCoefficient<0||!Number.isFinite(area)||area<0)throw new Error('Nonnegative finite drag coefficient and reference area are required');
  const relativeVelocity=sub(velocity,current),speed=Math.hypot(...relativeVelocity);
  const factor=speed===0||dragCoefficient===0||area===0?0:0.5*density*dragCoefficient*area*speed;
  const force=relativeVelocity.map(value=>-factor*value),relativePower=dot(force,relativeVelocity);
  finiteOutput([...relativeVelocity,...force,relativePower]);
  return {force,relativeVelocity,relativePower};
}
