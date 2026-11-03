import test from 'node:test';
import assert from 'node:assert/strict';
import {transform,quaternionNormalize,quaternionNlerp,quaternionRotate,cross,dot,normalize} from '../engine/math.mjs';
import {Renderer} from '../engine/renderer.mjs';

const close=(actual,expected,tolerance=1e-6)=>assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} != ${expected}`);
const vectorClose=(a,b,tolerance=1e-6)=>a.forEach((value,i)=>close(value,b[i],tolerance));
const apply=(m,p,translation=0)=>[0,1,2].map(row=>m[row]*p[0]+m[4+row]*p[1]+m[8+row]*p[2]+translation*m[12+row]);

test('full orientation preserves existing yaw transforms and rotates known axes right handed',()=>{
  for(const yaw of [0,0.2,-1.3,Math.PI]) {
    const q=[0,Math.sin(yaw/2),0,Math.cos(yaw/2)],old=transform([2,3,4],[2,3,4],yaw),rotated=transform([2,3,4],[2,3,4],0,q);
    vectorClose([...rotated],[...old]);
  }
  const quarterTurn=[0,0,Math.SQRT1_2,Math.SQRT1_2];
  vectorClose(quaternionRotate([1,0,0],quarterTurn),[0,1,0]);
  vectorClose(apply(transform([3,4,5],[2,3,4],0,quarterTurn),[1,0,0],1),[3,6,5]);
  vectorClose(quaternionRotate([0,1,0],[Math.SQRT1_2,0,0,Math.SQRT1_2]),[0,0,1]);
});

test('quaternion model columns stay orthogonal under nonuniform scale and retain right-handed volume',()=>{
  const q=quaternionNormalize([0.3,-0.5,0.2,0.7]),matrix=transform([8,9,10],[2,3,5],0,q);
  const columns=[0,4,8].map(offset=>[...matrix.slice(offset,offset+3)]);
  columns.forEach((column,i)=>close(Math.hypot(...column),[2,3,5][i]));
  close(dot(columns[0],columns[1]),0);close(dot(columns[0],columns[2]),0);close(dot(columns[1],columns[2]),0);
  close(dot(columns[0],cross(columns[1],columns[2])),30,5e-6);
  const [a,b]=[[1,1,0],[0,1,1]],normal=normalize(cross(a,b));
  // A transformed plane supplies an independent geometric normal. The shader's
  // inverse-transpose construction must use the scale, rather than model*n.
  const geometric=normalize(cross(apply(matrix,a),apply(matrix,b)));
  const inverseTranspose=normalize([0,1,2].map(axis=>columns.reduce((sum,column,i)=>sum+column[axis]*normal[i]/dot(column,column),0)));
  vectorClose(inverseTranspose,geometric);
  assert.ok(Math.abs(dot(normalize(apply(matrix,normal)),geometric))<0.99);
});

test('nlerp follows the short route across quaternion signs and normalizes every sample',()=>{
  const a=[0,0,Math.sin(170*Math.PI/360),Math.cos(170*Math.PI/360)];
  const b=[0,0,Math.sin(-170*Math.PI/360),Math.cos(-170*Math.PI/360)];
  vectorClose(quaternionRotate([1,0,0],quaternionNlerp(a,b,0.5)),[-1,0,0]);
  for(const alpha of [0,0.1,0.5,0.9,1]) {
    const q=quaternionNlerp(a,b,alpha);close(Math.hypot(...q),1,1e-12);
    vectorClose(quaternionRotate([1,2,3],quaternionNlerp(a,a.map(value=>-value),alpha)),quaternionRotate([1,2,3],a));
  }
  vectorClose(quaternionRotate([1,0,0],quaternionNlerp([0,0,0,1],[0,0,1,0],0.5)),[0,1,0]);
});

test('orientation helpers keep inputs unchanged and reject invalid rotations',()=>{
  const a=[0,0,0,2],b=[0,2,0,0],before=structuredClone([a,b]);quaternionNlerp(a,b,0.3);assert.deepEqual([a,b],before);
  for(const q of [[0,0,0,0],[NaN,0,0,1],[0,0,1],new Array(4)])assert.throws(()=>quaternionNormalize(q));
  for(const alpha of [-0.1,1.1,Infinity])assert.throws(()=>quaternionNlerp(a,b,alpha));
  assert.throws(()=>transform([0,0,0],[1,1,1],0,[0,0,0,0]));
});

test('the renderer packs live quaternion orientation into the instance matrix without changing yaw items',()=>{
  const pass=new Proxy({}, {get:()=>()=>{}}),q=[0,0,Math.SQRT1_2,Math.SQRT1_2];
  const stub={canvas:{width:640,height:480},resize(){},validateBudget:Renderer.prototype.validateBudget,
    maxInstances:4096,maxMeshes:128,maxTriangles:262144,meshBuffers:new Map(),stats:{},
    globals:new Float32Array(24),data:new Float32Array(40),exposure:1,fog:0,
    context:{getCurrentTexture:()=>({createView:()=>({})})},depth:{createView:()=>({})},
    device:{queue:{writeBuffer(){},submit(){}},createCommandEncoder:()=>({beginRenderPass:()=>pass,finish:()=>({})})}};
  const items=[{position:[1,2,3],scale:[2,3,4],orientation:q,color:[1,1,1]},
    {position:[4,5,6],scale:[1,2,3],yaw:0.4,color:[0,1,0]}];
  Renderer.prototype.render.call(stub,items,{eye:[5,6,7],target:[0,0,0]});
  vectorClose([...stub.data.slice(0,16)],[...transform(items[0].position,items[0].scale,0,q)]);
  vectorClose([...stub.data.slice(20,36)],[...transform(items[1].position,items[1].scale,0.4)]);
  vectorClose(apply(stub.data.slice(0,16),[1,0,0],1),[1,4,3]);
});
