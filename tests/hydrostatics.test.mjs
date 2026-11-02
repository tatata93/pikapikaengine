import test from 'node:test';
import assert from 'node:assert/strict';
import {createBoxMesh,validateMesh} from '../engine/mesh.mjs';
import {hydrostaticPressure,hydrostaticForces,quadraticDrag} from '../engine/hydrostatics.mjs';

const close=(actual,expected,tolerance=1e-8)=>assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} != ${expected} (tol ${tolerance})`);
const vectorClose=(actual,expected,tolerance=1e-8)=>actual.forEach((value,i)=>close(value,expected[i],tolerance));
const water={density:1000,gravity:10};
const cube=()=>createBoxMesh([2,2,2]);

test('gauge pressure is zero at/above the plane and rho*g*depth below',()=>{
  assert.equal(hydrostaticPressure(-3,water),0);assert.equal(hydrostaticPressure(0,water),0);
  assert.equal(hydrostaticPressure(2.5,water),25000);
  assert.equal(hydrostaticPressure(1,{density:1025,gravity:9.81}),10055.25);
});

test('dry, half and fully submerged cube match independent displaced-volume and centroid formulas',()=>{
  const dry=hydrostaticForces(cube(),{...water,position:[0,2,0]});
  vectorClose(dry.force,[0,0,0]);vectorClose(dry.torque,[0,0,0]);assert.equal(dry.wetArea,0);assert.equal(dry.submergedVolume,0);assert.equal(dry.centerOfBuoyancy,null);
  const half=hydrostaticForces(cube(),water);
  vectorClose(half.force,[0,40000,0]);vectorClose(half.torque,[0,0,0]);close(half.wetArea,12);close(half.submergedVolume,4);close(half.totalVolume,8);vectorClose(half.centerOfBuoyancy,[0,-0.5,0]);
  const full=hydrostaticForces(cube(),{...water,position:[0,-2,0]});
  vectorClose(full.force,[0,80000,0]);vectorClose(full.torque,[0,0,0]);close(full.wetArea,24);close(full.submergedVolume,8);vectorClose(full.centerOfBuoyancy,[0,-2,0]);
});

test('waterline slicing has the exact cube displacement continuously across all depths',()=>{
  for(const level of [-2,-1,-0.95,-0.4,0,0.4,0.95,1,2]) {
    const result=hydrostaticForces(cube(),{...water,waterLevel:level});
    const height=Math.max(0,Math.min(2,level+1)),volume=4*height;
    close(result.submergedVolume,volume);vectorClose(result.force,[0,10000*volume,0]);
    if(height>0)vectorClose(result.centerOfBuoyancy,[0,-1+height/2,0]);else assert.equal(result.centerOfBuoyancy,null);
  }
});

test('uniform translation of hull and waterline preserves forces and translates center of buoyancy',()=>{
  const base=hydrostaticForces(cube(),water),offset=[12345,54321,-23456];
  const translated=hydrostaticForces(cube(),{...water,position:offset,waterLevel:offset[1]});
  vectorClose(translated.force,base.force);vectorClose(translated.torque,base.torque);close(translated.submergedVolume,base.submergedVolume);
  vectorClose(translated.centerOfBuoyancy,base.centerOfBuoyancy.map((value,i)=>value+offset[i]));
  const deeper=hydrostaticForces(cube(),{...water,position:[0,-20,0]});
  vectorClose(deeper.force,[0,80000,0]);vectorClose(deeper.centerOfBuoyancy,[0,-20,0]);
});

test('nonuniform scaling and yaw preserve expected rectangular displacement and wet area',()=>{
  const mesh=createBoxMesh(),result=hydrostaticForces(mesh,{...water,scale:[2,4,6],yaw:0.73});
  close(result.totalVolume,48);close(result.submergedVolume,24);vectorClose(result.force,[0,240000,0]);
  close(result.wetArea,44);vectorClose(result.centerOfBuoyancy,[0,-1,0]);vectorClose(result.torque,[0,0,0]);
});

test('90 degree roll swaps box extents and tilted symmetric cube remains half displaced',()=>{
  const rolled=hydrostaticForces(createBoxMesh([2,4,6]),{...water,orientation:[0,0,Math.SQRT1_2,Math.SQRT1_2]});
  close(rolled.submergedVolume,24);vectorClose(rolled.force,[0,240000,0]);vectorClose(rolled.centerOfBuoyancy,[0,-0.5,0]);close(rolled.wetArea,44);
  const a=0.37,b=0.21,ca=Math.cos(a/2),sa=Math.sin(a/2),cb=Math.cos(b/2),sb=Math.sin(b/2);
  const tilted=hydrostaticForces(cube(),{...water,orientation:[sa*cb,ca*sb,sa*sb,ca*cb]});
  close(tilted.submergedVolume,4);vectorClose(tilted.force,[0,40000,0]);
  // Independent resultant-line check: pressure torque must act through the displaced-volume centroid.
  const [x,,z]=tilted.centerOfBuoyancy;
  vectorClose(tilted.torque,[-z*40000,0,x*40000]);
});

test('pressure moment gives known off-center torque about the supplied world-space center of mass',()=>{
  const result=hydrostaticForces(cube(),{...water,centerOfMass:[1,2,3]});
  vectorClose(result.force,[0,40000,0]);vectorClose(result.torque,[120000,0,-40000]);
  const moved=hydrostaticForces(cube(),{...water,position:[10,4,-7],waterLevel:4,centerOfMass:[11,6,-4]});
  vectorClose(moved.torque,result.torque);
});

function subdivide(mesh) {
  const positions=mesh.positions.map(p=>[...p]),triangles=[],midpoints=new Map();
  const midpoint=(a,b)=>{
    const key=[Math.min(a,b),Math.max(a,b)].join(':');
    if(!midpoints.has(key)){midpoints.set(key,positions.length);positions.push(positions[a].map((x,i)=>(x+positions[b][i])/2));}
    return midpoints.get(key);
  };
  for(const [a,b,c] of mesh.triangles){const ab=midpoint(a,b),bc=midpoint(b,c),ca=midpoint(c,a);triangles.push([a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]);}
  return validateMesh({version:1,positions,triangles});
}

test('refining surface triangulation does not change pressure, torque, displacement or centroid',()=>{
  const mesh=cube();mesh.positions[6]=[1.4,1.7,1.2];
  const options={...water,waterLevel:0.23,position:[2,-0.4,-1],yaw:0.6,centerOfMass:[1,0,2]};
  const coarse=hydrostaticForces(mesh,options),fine=hydrostaticForces(subdivide(subdivide(mesh)),options);
  vectorClose(fine.force,coarse.force);vectorClose(fine.torque,coarse.torque);close(fine.wetArea,coarse.wetArea);close(fine.submergedVolume,coarse.submergedVolume);vectorClose(fine.centerOfBuoyancy,coarse.centerOfBuoyancy);
});

test('density and gravity scale force and torque but not displaced geometry',()=>{
  const options={...water,centerOfMass:[1,2,3]},base=hydrostaticForces(cube(),options);
  for(const scale of [0.5,1.025,2]) {
    const result=hydrostaticForces(cube(),{...options,density:1000*scale});
    vectorClose(result.force,base.force.map(value=>value*scale));vectorClose(result.torque,base.torque.map(value=>value*scale));
    close(result.submergedVolume,base.submergedVolume);vectorClose(result.centerOfBuoyancy,base.centerOfBuoyancy);
  }
  vectorClose(hydrostaticForces(cube(),{...options,gravity:20}).force,base.force.map(value=>value*2));
});

test('partially submerged sloping tetrahedron agrees with an independent volume subtraction and centroid',()=>{
  const mesh={version:1,positions:[[0,0,0],[2,0,0],[0,2,0],[0,0,2]],triangles:[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]};
  // Whole tetra: V=4/3, C=(1/2,1/2,1/2). Dry top tetra: V=1/6, C=(1/4,5/4,1/4).
  const result=hydrostaticForces(mesh,{...water,waterLevel:1});
  close(result.submergedVolume,7/6);vectorClose(result.force,[0,10000*7/6,0]);
  vectorClose(result.centerOfBuoyancy,[15/28,11/28,15/28]);vectorClose(result.torque,[-6250,0,6250]);
});

test('open, inverted, inconsistent and non-manifold displacement shells are rejected',()=>{
  const open=cube();open.triangles.pop();assert.throws(()=>hydrostaticForces(open),/closed/);
  const inverted=cube();inverted.triangles=inverted.triangles.map(([a,b,c])=>[a,c,b]);assert.throws(()=>hydrostaticForces(inverted),/positive signed volume/);
  const wrong=cube();wrong.triangles[0].reverse();assert.throws(()=>hydrostaticForces(wrong),/winding/);
  const duplicate=cube();duplicate.triangles.push([...duplicate.triangles[0]]);assert.throws(()=>hydrostaticForces(duplicate),/non-manifold/);
  const flat={version:1,positions:[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],triangles:[[0,1,2],[0,2,3],[0,3,1],[1,3,2]]};
  assert.throws(()=>hydrostaticForces(flat),/positive signed volume/);
});

test('separate outward hulls are summed and an inverted shell cannot hide inside a larger positive volume',()=>{
  const a=cube(),b=cube(),joined={version:1,positions:[...a.positions,...b.positions.map(p=>[p[0]+4,p[1],p[2]])],triangles:[...a.triangles,...b.triangles.map(t=>t.map(i=>i+8))]};
  const result=hydrostaticForces(joined,water);assert.equal(result.shells,2);close(result.submergedVolume,8);vectorClose(result.centerOfBuoyancy,[2,-0.5,0]);
  joined.triangles.splice(12,12,...b.triangles.map(([x,y,z])=>[x+8,z+8,y+8]));
  assert.throws(()=>hydrostaticForces(joined),/positive signed volume/);
});

test('invalid SI parameters, reflected scales, non-unit orientations and overflowing outputs fail explicitly',()=>{
  for(const options of [{density:0},{gravity:-1},{waterLevel:NaN},{waterLevel:1e6+1},{position:[0,Infinity,0]},{scale:[1,-1,1]},{scale:[0,1,1]},{orientation:[0,0,0,2]},{orientation:[0,0,0,1],yaw:0},{centerOfMass:[NaN,0,0]},{density:1e308,gravity:1e308}])assert.throws(()=>hydrostaticForces(cube(),options));
  for(const depth of [NaN,Infinity])assert.throws(()=>hydrostaticPressure(depth));
  assert.throws(()=>hydrostaticPressure(1e308,{density:1e308}),/numeric range/);
});

test('uniform-current quadratic drag has known magnitude, relative-motion invariance and nonpositive relative power',()=>{
  const base=quadraticDrag({velocity:[3,4,0],density:1000,dragCoefficient:0.8,area:2});
  vectorClose(base.force,[-12000,-16000,0]);close(base.relativePower,-100000);
  const shifted=quadraticDrag({velocity:[13,1,-4],current:[10,-3,-4],density:1000,dragCoefficient:0.8,area:2});
  vectorClose(shifted.force,base.force);close(shifted.relativePower,base.relativePower);
  for(const velocity of [[0,0,0],[-2,0,1],[2,-1,-3],[0.1,0.2,0.3]])assert.ok(quadraticDrag({velocity,current:[0.2,-0.3,0.1],dragCoefficient:1,area:2}).relativePower<=0);
  vectorClose(quadraticDrag({velocity:[3,4,0],current:[3,4,0],dragCoefficient:1,area:2}).force,[0,0,0]);
  vectorClose(quadraticDrag({velocity:[3,4,0],dragCoefficient:0,area:2}).force,[0,0,0]);
  assert.throws(()=>quadraticDrag({velocity:[1,0,0],dragCoefficient:-1,area:2}));
  assert.throws(()=>quadraticDrag({velocity:[1,0,0],dragCoefficient:1,area:-2}));
  assert.throws(()=>quadraticDrag({velocity:[1,0,0],dragCoefficient:1}));
});
