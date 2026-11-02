import {clamp,add,sub,mul} from './math.mjs';
// Axis-aligned static boxes. Yaw is intentionally unsupported for colliders.
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
