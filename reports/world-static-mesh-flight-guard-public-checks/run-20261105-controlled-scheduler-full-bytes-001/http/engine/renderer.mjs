import {perspective,lookAt,multiply,transform} from './math.mjs';
import {compileMesh} from './mesh.mjs';
import {derivedMeshRenderInfo,copyDerivedMeshRenderVertices} from './derived-render.mjs';
const shader=`
struct Globals { vp:mat4x4<f32>, eye:vec4<f32>, settings:vec4<f32> }
@group(0) @binding(0) var<uniform> g:Globals;
struct VOut { @builtin(position) clip:vec4<f32>, @location(0) world:vec3<f32>, @location(1) normal:vec3<f32>, @location(2) color:vec4<f32> }
@vertex fn vs(@location(0) p:vec3<f32>,@location(1) n:vec3<f32>,@location(2) a:vec4<f32>,@location(3) b:vec4<f32>,@location(4) c:vec4<f32>,@location(5) d:vec4<f32>,@location(6) color:vec4<f32>)->VOut {
 let model=mat4x4<f32>(a,b,c,d); let w=model*vec4<f32>(p,1.);
 var o:VOut; o.clip=g.vp*w; o.world=w.xyz;
 o.normal=normalize(a.xyz*n.x/dot(a.xyz,a.xyz)+b.xyz*n.y/dot(b.xyz,b.xyz)+c.xyz*n.z/dot(c.xyz,c.xyz));
 o.color=color; return o;
}
fn srgb(v:vec3<f32>)->vec3<f32> { return select(1.055*pow(v,vec3<f32>(1./2.4))-.055,12.92*v,v<=vec3<f32>(.0031308)); }
@fragment fn fs(i:VOut)->@location(0) vec4<f32> {
 let n=normalize(i.normal); let v=normalize(g.eye.xyz-i.world); let l=normalize(vec3<f32>(-.45,.85,.3)); let h=normalize(v+l);
 let nl=max(dot(n,l),0.); let nv=max(dot(n,v),.001); let nh=max(dot(n,h),0.); let vh=max(dot(v,h),0.);
 let rough=.52; let a2=rough*rough*rough*rough; let den=nh*nh*(a2-1.)+1.; let D=a2/(3.14159265*den*den);
 let k=(rough+1.)*(rough+1.)/8.; let G=(nl/(nl*(1.-k)+k))*(nv/(nv*(1.-k)+k));
 let F=vec3<f32>(.04)+(vec3<f32>(1.)-vec3<f32>(.04))*pow(1.-vh,5.);
 let spec=D*G*F/(4.*max(nl,.001)*nv); let diffuse=(vec3<f32>(1.)-F)*i.color.rgb/3.14159265;
 var linear=(diffuse+spec)*nl*3.4+i.color.rgb*(.12+.16*max(n.y,0.))+i.color.rgb*i.color.a;
 let fog=1.-exp(-distance(i.world,g.eye.xyz)*g.settings.z);
 linear=mix(linear,vec3<f32>(.095,.16,.19),fog); linear*=g.settings.y;
 let mapped=linear/(vec3<f32>(1.)+linear); return vec4<f32>(srgb(mapped),1.);
}`;
function cube() {
  const out=[], faces=[[[1,0,0],[1,-1,-1],[1,1,-1],[1,1,1],[1,-1,1]],[[-1,0,0],[-1,-1,1],[-1,1,1],[-1,1,-1],[-1,-1,-1]],[[0,1,0],[-1,1,-1],[-1,1,1],[1,1,1],[1,1,-1]],[[0,-1,0],[-1,-1,1],[-1,-1,-1],[1,-1,-1],[1,-1,1]],[[0,0,1],[1,-1,1],[1,1,1],[-1,1,1],[-1,-1,1]],[[0,0,-1],[-1,-1,-1],[-1,1,-1],[1,1,-1],[1,-1,-1]]];
  for(const [n,...p] of faces) for(const j of [0,1,2,0,2,3]) out.push(...p[j].map(x=>x*.5),...n);
  return new Float32Array(out);
}
const isMesh=e=>e.type==='mesh'||e.type==='derived-mesh';
const live=renderer=>{if(renderer.disposed||renderer.lost)throw new Error('Renderer is disposed or its GPU device is lost');};
function releaseMesh(renderer,resource){resource.buffer.destroy();renderer.stats.destroyedMeshBuffers=(renderer.stats.destroyedMeshBuffers??0)+1;}
function releaseMeshes(renderer){for(const resource of renderer.meshBuffers.values())releaseMesh(renderer,resource);renderer.meshBuffers.clear();}
export class Renderer {
  static async create(canvas,onError=()=>{}) {
    if(!navigator.gpu) throw new Error('WebGPUを利用できません。GPUアクセラレーションが有効な最新のChromeまたはEdgeで localhost / HTTPS から起動してください。');
    const adapter=await navigator.gpu.requestAdapter(); if(!adapter) throw new Error('対応GPUが見つかりません。ブラウザのGPU設定を確認してください。');
    const device=await adapter.requestDevice();
    let renderer,scope=false;
    try{
      device.pushErrorScope('validation');scope=true;renderer=new Renderer(canvas,device,adapter,onError);
      scope=false;const pending=device.popErrorScope();const error=await pending;if(error)throw new Error(error.message);
      live(renderer);return renderer;
    }catch(error){if(scope){try{await device.popErrorScope();}catch{}}renderer?.dispose();throw error;}
  }
  constructor(canvas,device,adapter,onError=()=>{}) {
    this.canvas=canvas; this.device=device; this.adapter=adapter; this.maxInstances=4096;this.maxTriangles=262144;this.maxMeshes=128;
    this.meshBuffers=new Map();this.stats={drawCalls:0,triangles:0,uploadedMeshBytes:0,destroyedMeshBuffers:0};
    this.disposed=false;this.lost=false;this.onError=onError;
    this.reportError=message=>{try{this.onError(message);}catch{}};
    this.uncaptured=e=>{if(!this.disposed)this.reportError(e.error?.message??'WebGPU error');};
    try{
    device.addEventListener?.('uncapturederror',this.uncaptured);
    device.lost?.then(info=>{if(this.disposed)return;this.lost=true;this.dispose();this.reportError(`GPU接続が失われました: ${info.message}。ページを再読み込みしてください。`);});
    this.context=canvas.getContext('webgpu'); this.format=navigator.gpu.getPreferredCanvasFormat();
    this.context.configure({device,format:this.format,alphaMode:'opaque'});
    const module=device.createShaderModule({code:shader});
    this.pipeline=device.createRenderPipeline({layout:'auto',vertex:{module,entryPoint:'vs',buffers:[{arrayStride:24,attributes:[{shaderLocation:0,offset:0,format:'float32x3'},{shaderLocation:1,offset:12,format:'float32x3'}]},{arrayStride:80,stepMode:'instance',attributes:[0,1,2,3,4].map((x)=>({shaderLocation:x+2,offset:x*16,format:'float32x4'}))}]},fragment:{module,entryPoint:'fs',targets:[{format:this.format}]},primitive:{topology:'triangle-list',cullMode:'none'},depthStencil:{format:'depth24plus',depthWriteEnabled:true,depthCompare:'less'}});
    const vertices=cube(); this.vertices=device.createBuffer({size:vertices.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}); device.queue.writeBuffer(this.vertices,0,vertices);
    this.instances=device.createBuffer({size:this.maxInstances*80,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}); this.data=new Float32Array(this.maxInstances*20);
    this.uniform=device.createBuffer({size:96,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
    this.bind=device.createBindGroup({layout:this.pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:this.uniform}}]});
    this.globals=new Float32Array(24); this.exposure=1.15; this.fog=.0025;
    }catch(error){this.dispose();throw error;}
  }
  validateBudget(items) {
    if(!Array.isArray(items))throw new Error('Render items must be an array');
    if(items.length>this.maxInstances)throw new Error('Render instance budget exceeded: 4096');
    const meshes=items.filter(isMesh);
    if(meshes.length>this.maxMeshes)throw new Error('Mesh draw budget exceeded: 128');
    const triangles=items.reduce((sum,e)=>sum+(e.type==='derived-mesh'?derivedMeshRenderInfo(e.mesh).triangleCount:e.type==='mesh'?e.mesh.triangles.length:12),0);
    if(triangles>this.maxTriangles)throw new Error('Render triangle budget exceeded: 262144');
    if(new Set(meshes.map(e=>e.id)).size!==meshes.length)throw new Error('Mesh render IDs must be unique');
    return {meshes,triangles};
  }
  dropMesh(id) {
    const resource=this.meshBuffers.get(id);
    if(!resource)return false;
    // Retire only this cache entry. Advancing the epoch makes an older checked
    // failure unable to clear unrelated resources after this explicit removal.
    // Submitted pixels/draw statistics remain those of the last full frame.
    this.meshBuffers.delete(id);this.renderEpoch=(this.renderEpoch??0)+1;
    releaseMesh(this,resource);return true;
  }
  resize() {
    live(this);
    const ratio=this.pixelRatio??Math.min(devicePixelRatio,1.5),width=Math.max(1,Math.round(this.canvas.clientWidth*ratio)),height=Math.max(1,Math.round(this.canvas.clientHeight*ratio));
    if(width!==this.canvas.width||height!==this.canvas.height||!this.depth) {
      const depth=this.device.createTexture({size:[width,height],format:'depth24plus',usage:GPUTextureUsage.RENDER_ATTACHMENT});
      this.canvas.width=width;this.canvas.height=height;this.depth?.destroy();this.depth=depth;
    }
  }
  render(items,camera,time=0) {
    live(this);this.renderEpoch=(this.renderEpoch??0)+1;
    const {meshes,triangles}=this.validateBudget(items),boxes=items.filter(e=>!isMesh(e));items=[...boxes,...meshes];
    // Explicit removal remains effective even if drawing the clearing frame
    // later fails (for example, its canvas texture is no longer available).
    if(!meshes.length){releaseMeshes(this);this.stats.drawCalls=0;this.stats.triangles=0;}
    // Finish CPU preparation before changing any live mesh GPU resources.
    const prepared=[];
    for(const entity of meshes){
      const resource=this.meshBuffers.get(entity.id);
      if(resource?.source!==entity.mesh||resource.kind!==entity.type)prepared.push({entity,vertices:entity.type==='derived-mesh'?copyDerivedMeshRenderVertices(entity.mesh):compileMesh(entity.mesh)});
    }
    this.resize();this.globals.set(multiply(perspective(Math.PI/3,this.canvas.width/this.canvas.height,.2,1600),lookAt(camera.eye,camera.target)));
    this.globals.set([...camera.eye,1],16);this.globals.set([time,this.exposure,this.fog,0],20);
    let offset=0;
    for(const e of items) { this.data.set(transform(e.position,e.scale,e.yaw||0,e.orientation),offset);this.data.set([...e.color,e.emission||0],offset+16);offset+=20; }
    const staged=new Map();
    try{
    for(const {entity,vertices}of prepared){
      const buffer=this.device.createBuffer({size:vertices.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
      const resource={source:entity.mesh,kind:entity.type,buffer,count:vertices.length/6,bytes:vertices.byteLength};staged.set(entity.id,resource);
      this.device.queue.writeBuffer(buffer,0,vertices);
    }
    this.device.queue.writeBuffer(this.uniform,0,this.globals);
    if(offset)this.device.queue.writeBuffer(this.instances,0,this.data,0,offset);
    const encoder=this.device.createCommandEncoder();
    const pass=encoder.beginRenderPass({colorAttachments:[{view:this.context.getCurrentTexture().createView(),clearValue:{r:.20,g:.29,b:.33,a:1},loadOp:'clear',storeOp:'store'}],depthStencilAttachment:{view:this.depth.createView(),depthClearValue:1,depthLoadOp:'clear',depthStoreOp:'store'}});
    pass.setPipeline(this.pipeline);pass.setBindGroup(0,this.bind);pass.setVertexBuffer(0,this.vertices);pass.setVertexBuffer(1,this.instances);
    if(boxes.length)pass.draw(36,boxes.length);
    for(let i=0;i<meshes.length;i++){const resource=staged.get(meshes[i].id)??this.meshBuffers.get(meshes[i].id);pass.setVertexBuffer(0,resource.buffer);pass.draw(resource.count,1,0,boxes.length+i);}
    pass.end();this.device.queue.submit([encoder.finish()]);
    }catch(error){for(const resource of staged.values())releaseMesh(this,resource);throw error;}
    const active=new Set(meshes.map(e=>e.id));
    for(const [id,resource]of this.meshBuffers)if(!active.has(id)||staged.has(id)){releaseMesh(this,resource);this.meshBuffers.delete(id);}
    for(const [id,resource]of staged){this.meshBuffers.set(id,resource);this.stats.uploadedMeshBytes+=resource.bytes;}
    this.stats.drawCalls=(boxes.length?1:0)+meshes.length;this.stats.triangles=triangles;
  }
  async renderChecked(items,camera,time=0){
    live(this);let scope=false,synchronousError,pending,epoch=this.renderEpoch??0;
    try{
      this.device.pushErrorScope('validation');scope=true;
      try{this.render(items,camera,time);}catch(error){synchronousError=error;}epoch=this.renderEpoch??0;
      scope=false;pending=this.device.popErrorScope();const validation=await pending;
      if(synchronousError)throw synchronousError;if(validation)throw new Error(validation.message);
      await this.device.queue.onSubmittedWorkDone();live(this);
    }catch(error){if(scope){try{await this.device.popErrorScope();}catch{}}
      // An older asynchronous failure must not delete a newer frame's resources.
      if((this.renderEpoch??0)===epoch){releaseMeshes(this);this.stats.drawCalls=0;this.stats.triangles=0;}throw error;}
  }
  dispose(){
    if(this.disposed)return;this.disposed=true;
    // GPUDevice may be shared by an embedding caller and is not destroyed here.
    this.device.removeEventListener?.('uncapturederror',this.uncaptured);
    releaseMeshes(this);
    for(const resource of [this.vertices,this.instances,this.uniform,this.depth])resource?.destroy();
    this.depth=undefined;this.context?.unconfigure?.();this.stats.drawCalls=0;this.stats.triangles=0;
  }
}
