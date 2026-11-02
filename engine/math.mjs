import {getPortableCore} from './portable.mjs';
// SI metres, seconds, radians. Right-handed coordinates, +Y up.
export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
export const add = (a,b) => a.map((x,i)=>x+b[i]);
export const sub = (a,b) => a.map((x,i)=>x-b[i]);
export const mul = (a,k) => a.map(x=>x*k);
export const dot = (a,b) => a.reduce((s,x,i)=>s+x*b[i],0);
export const length = a => Math.hypot(...a);
export const normalize = a => mul(a, 1/(length(a)||1));
export const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export const lerp = (a,b,t) => a.map((v,i)=>v+(b[i]-v)*t);
export function multiply(a,b) {
  const o=new Float32Array(16);
  for(let c=0;c<4;c++) for(let r=0;r<4;r++) for(let k=0;k<4;k++) o[c*4+r]+=a[k*4+r]*b[c*4+k];
  return o;
}
export function perspective(fov,aspect,near,far) {
  const f=1/Math.tan(fov/2);
  return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,far/(near-far),-1,0,0,near*far/(near-far),0]);
}
export function lookAt(eye,target) {
  const z=normalize(sub(eye,target)),x=normalize(cross([0,1,0],z)),y=cross(z,x);
  return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);
}
export function transform(position,scale=[1,1,1],yaw=0) {
  const c=Math.cos(yaw),s=Math.sin(yaw);
  return new Float32Array([c*scale[0],0,-s*scale[0],0,0,scale[1],0,0,s*scale[2],0,c*scale[2],0,...position,1]);
}
// Segment vs sphere continuous collision; result is normalized time of first impact.
export function sweepSphere(a,b,center,radius) {
  const d=sub(b,a),m=sub(a,center),c=dot(m,m)-radius*radius;
  const core=getPortableCore();if(core){const t=core.pp_sweep_fraction(...m,...d,radius);return t<0?null:t;}
  if(c<=0) return 0;
  const q=dot(d,d); if(q===0) return null;
  const n=dot(m,d),disc=n*n-q*c;
  if(disc<0) return null;
  const t=(-n-Math.sqrt(disc))/q;
  return t>=0&&t<=1?t:null;
}
export function seeded(seed=1) {
  let s=seed>>>0;
  return ()=>{s=(Math.imul(s,1664525)+1013904223)>>>0; return s/4294967296;};
}
