import {clamp,add,sub,mul} from './math.mjs';
import {meshBounds} from './mesh.mjs';
const colliderCache=new WeakMap();
// Immutable source entities key derived data. A Scene edit/undo/load creates new
// source objects, so stale bounds are never reused after a geometry change.
export function deriveCollider(entity) {
  const cached=colliderCache.get(entity);if(cached)return cached;
  if(!['box','mesh'].includes(entity.type))throw new Error('Collider requires box or mesh geometry');
  const bounds=entity.type==='mesh'?meshBounds(entity.mesh):{min:[-.5,-.5,-.5],max:[.5,.5,.5]};
  const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity],c=Math.cos(entity.yaw),s=Math.sin(entity.yaw);
  for(let corner=0;corner<8;corner++){
    const p=[0,1,2].map(i=>(corner&(1<<i)?bounds.max[i]:bounds.min[i])*entity.scale[i]);
    const world=[entity.position[0]+c*p[0]+s*p[2],entity.position[1]+p[1],entity.position[2]-s*p[0]+c*p[2]];
    for(let i=0;i<3;i++){min[i]=Math.min(min[i],world[i]);max[i]=Math.max(max[i],world[i]);}
  }
  const collider=Object.freeze({id:entity.id,position:Object.freeze(min.map((n,i)=>(n+max[i])/2)),scale:Object.freeze(min.map((n,i)=>max[i]-n)),approximation:entity.type==='mesh'||entity.yaw!==0?'conservative-world-aabb':'axis-aligned-box'});
  colliderCache.set(entity,collider);return collider;
}
// Axis-aligned broad proxy: meshes are enclosed by a conservative world AABB.
// This is not triangle-surface contact or a deformable material solver.
export function sweepAabb(a,b,center,scale,radius=0) {
  let enter=0,exit=1; const d=sub(b,a);
  for(let i=0;i<3;i++) {
    const low=center[i]-scale[i]/2-radius,high=center[i]+scale[i]/2+radius;
    if(Math.abs(d[i])<1e-12) {if(a[i]<low||a[i]>high)return null;continue;}
    let t0=(low-a[i])/d[i],t1=(high-a[i])/d[i]; if(t0>t1)[t0,t1]=[t1,t0];
    enter=Math.max(enter,t0);exit=Math.min(exit,t1); if(enter>exit)return null;
  }
  return enter;
}
export function moveController(position,velocity,dt,obstacles,radius=1.8) {
  // Axis sweep and slide; game controller, not a general rigid body solver.
  let p=[...position];
  for(const axis of [0,2,1]) {
    const next=[...p]; next[axis]+=velocity[axis]*dt; let fraction=1;
    for(const e of obstacles) {
      const hit=sweepAabb(p,next,e.position,e.scale,radius);
      if(hit!==null) fraction=Math.min(fraction,Math.max(0,hit-.001));
    }
    p[axis]+=(next[axis]-p[axis])*fraction;
    if(fraction<1)velocity[axis]=0;
  }
  p[0]=clamp(p[0],-220,220);p[2]=clamp(p[2],-220,220);
  if(p[1]<3){p[1]=3;velocity[1]=Math.max(0,velocity[1]);}
  return p;
}
export function impactPoint(a,b,t) {return add(a,mul(sub(b,a),t));}
