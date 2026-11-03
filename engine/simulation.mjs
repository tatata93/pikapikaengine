import createModule from '../assets/pikapika-simulation.mjs';
import {validateMesh,createBoxMesh} from './mesh.mjs';
import {quaternionRotate,add} from './math.mjs';

const bytesCache=new WeakMap();let defaultRuntime;
const asset=name=>{const url=new URL('../assets/'+name,import.meta.url),build=new URL(import.meta.url).searchParams.get('build');if(build)url.searchParams.set('build',build);return url;};
const finiteArray=(input,length,label)=>{
  if(!(Array.isArray(input)||ArrayBuffer.isView(input))||input.length!==length)throw new Error(`${label} requires ${length} components`);
  const values=Array.from(input);if(!values.every(Number.isFinite))throw new Error(`${label} requires finite numbers`);return values;
};
const stepCount=value=>{if(!Number.isInteger(value)||value<1||value>32)throw new Error('Simulation batch requires 1..32 complete ticks');return value;};
const validBodyId=value=>{if(!Number.isSafeInteger(value)||value<1)throw new Error('Body ID requires an integer in 1..9007199254740991');return value;};
export class SimulationError extends Error {constructor(code,message){super(message);this.name='SimulationError';this.code=code;}}
export class SimulationRuntime {
  constructor(native,metadata,wasmBytes,startupMs){
    if(native._pp_sim_api_version()!==1)throw new Error('Unsupported C++ simulation ABI');
    this.native=native;this.metadata=metadata;this.wasmBytes=wasmBytes;this.startupMs=startupMs;
  }
  get diagnostics(){return {backend:'C++ WebAssembly',compiler:this.metadata.compiler??'Emscripten 6.0.13',buildId:new URL(import.meta.url).searchParams.get('build')??'local-unversioned',wasmBytes:this.wasmBytes,memoryBytes:this.native.HEAPU8.byteLength,startupMs:this.startupMs,apiVersion:1};}
  check(status){if(status!==0){const m=this.native,p=m._pp_sim_error_ptr(),n=m._pp_sim_error_length();throw new SimulationError(status,new TextDecoder().decode(m.HEAPU8.subarray(p,p+n)));}}
  handle(value){if(!value){this.check(this.native._pp_sim_last_status());throw new Error('C++ returned an empty simulation handle');}return value;}
  inputF64(values){
    const data=finiteArray(values,values.length,'Float64 exchange'),m=this.native;
    if(data.length>m._pp_sim_input_f64_capacity())throw new Error('Float64 exchange capacity exceeded');
    m.HEAPF64.set(data,m._pp_sim_input_f64_ptr()/8);return data.length;
  }
  inputU32(values){
    const data=Array.from(values),m=this.native;if(data.length>m._pp_sim_input_u32_capacity()||!data.every(x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff))throw new Error('Invalid triangle index exchange');
    m.HEAPU32.set(data,m._pp_sim_input_u32_ptr()/4);return data.length;
  }
  output(){const m=this.native,p=m._pp_sim_output_f64_ptr()/8;return Array.from(m.HEAPF64.subarray(p,p+m._pp_sim_output_count()));}
  createHull(source){return new SimulationHull(this,source);}
  createWorld({gravity=[0,-9.80665,0]}={}){const world=new SimulationWorld(this);try{world.setGravity(gravity);return world;}catch(error){world.dispose();throw error;}}
}
async function initialize({wasmBytes,manifest}={}){
  const start=performance.now();let bytes=wasmBytes,metadata=manifest??{};
  if(bytes===undefined){
    const [binary,record]=await Promise.all([fetch(asset('pikapika-simulation.wasm')),fetch(asset('pikapika-simulation.build.json'))]);
    if(!binary.ok||!record.ok)throw new Error('数値コアの配信ファイルを読み込めません');
    bytes=new Uint8Array(await binary.arrayBuffer());metadata=await record.json();
    const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));
    const hash=Array.from(digest,x=>x.toString(16).padStart(2,'0')).join('');
    if(hash!==metadata.artifacts?.['assets/pikapika-simulation.wasm']?.sha256)throw new Error('数値コアのWASMと来歴が一致しません');
  }
  if(!(bytes instanceof Uint8Array)||bytes.byteLength===0)throw new Error('Simulation requires nonempty WebAssembly bytes');
  const native=await createModule({wasmBinary:bytes,print:()=>{},printErr:message=>console.error(message)});
  return new SimulationRuntime(native,metadata,bytes.byteLength,performance.now()-start);
}
export function loadSimulationRuntime(options={}){
  if(options.wasmBytes!==undefined){
    if(!(options.wasmBytes instanceof Uint8Array))return Promise.reject(new Error('wasmBytes must be Uint8Array'));
    let promise=bytesCache.get(options.wasmBytes);if(!promise){promise=initialize(options);bytesCache.set(options.wasmBytes,promise);promise.catch(()=>bytesCache.delete(options.wasmBytes));}return promise;
  }
  if(!defaultRuntime){defaultRuntime=initialize(options);defaultRuntime.catch(()=>{defaultRuntime=undefined;});}return defaultRuntime;
}
function uploadHull(runtime,source){
  const mesh=validateMesh(source);
  if(mesh.positions.length>16384||mesh.triangles.length>32768)throw new Error('WASM hull profile: at most 16384 vertices / 32768 triangles');
  runtime.inputF64(mesh.positions.flat());runtime.inputU32(mesh.triangles.flat());return mesh;
}
const hydroResult=a=>({force:a.slice(0,3),torque:a.slice(3,6),wetArea:a[6],submergedVolume:a[7],totalVolume:a[8],shells:a[9],centerOfBuoyancy:a[10]?a.slice(11,14):null});
class SimulationHull {
  #source;
  constructor(runtime,source){this.runtime=runtime;const mesh=uploadHull(runtime,source);this.handle=runtime.handle(runtime.native._pp_sim_hull_create(mesh.positions.length,mesh.triangles.length));this.#source=mesh;}
  get source(){return structuredClone(this.#source);}
  requireLive(){if(!this.handle)throw new Error('Hull is disposed');}
  replace(source){this.requireLive();const mesh=uploadHull(this.runtime,source);this.runtime.check(this.runtime.native._pp_sim_hull_replace(this.handle,mesh.positions.length,mesh.triangles.length));this.#source=mesh;}
  query({density=1000,gravity=9.80665,waterLevel=0,position=[0,0,0],orientation=[0,0,0,1],scale=[1,1,1],centerOfMass=position}={}){
    this.requireLive();const r=this.runtime,n=r.inputF64([density,gravity,waterLevel,...finiteArray(position,3,'Position'),...finiteArray(orientation,4,'Orientation'),...finiteArray(scale,3,'Scale'),...finiteArray(centerOfMass,3,'Center of mass')]);
    r.check(r.native._pp_sim_hydro_query(this.handle,n));return hydroResult(r.output());
  }
  dispose(){if(this.handle){this.runtime.check(this.runtime.native._pp_sim_hull_destroy(this.handle));this.handle=0;}}
}
function bodyInput(body){
  const {id,isStatic=false,mass=1,radius=1,inertia=[.4*mass*radius*radius,.4*mass*radius*radius,.4*mass*radius*radius],position=[0,0,0],orientation=[0,0,0,1],linearVelocity=[0,0,0],angularMomentum=[0,0,0],force=[0,0,0],torque=[0,0,0],restitution=0,friction=.6}=body;
  if(typeof isStatic!=='boolean')throw new Error('isStatic requires a boolean');
  return [id,Number(isStatic),mass,radius,...finiteArray(inertia,3,'Inertia'),...finiteArray(position,3,'Position'),...finiteArray(orientation,4,'Orientation'),...finiteArray(linearVelocity,3,'Velocity'),...finiteArray(angularMomentum,3,'Angular momentum'),...finiteArray(force,3,'Force'),...finiteArray(torque,3,'Torque'),restitution,friction];
}
const bodyResult=a=>({id:a[0],isStatic:Boolean(a[1]),mass:a[2],radius:a[3],inertia:a.slice(4,7),position:a.slice(7,10),orientation:a.slice(10,14),linearVelocity:a.slice(14,17),angularMomentum:a.slice(17,20),force:a.slice(20,23),torque:a.slice(23,26),restitution:a[26],friction:a[27],angularVelocity:a.slice(28,31),kineticEnergy:a[31],time:a[32],ticks:a[33]});
const stepResult=a=>({midpointHydro:hydroResult(a),contacts:a[14],velocityIterations:a[15],maxPenetration:a[16],normalImpulse:a[17],frictionImpulse:a[18],closingResidual:a[19],time:a[20],ticks:a[21]});
class SimulationWorld {
  constructor(runtime){this.runtime=runtime;this.handle=runtime.handle(runtime.native._pp_sim_world_create());}
  requireLive(){if(!this.handle)throw new Error('World is disposed');}
  setGravity(gravity){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_set_gravity(this.handle,r.inputF64(finiteArray(gravity,3,'Gravity'))));}
  reset(){this.requireLive();this.runtime.check(this.runtime.native._pp_sim_world_reset(this.handle));}
  info(){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_info(this.handle));const a=r.output();return {gravity:a.slice(0,3),bodies:a[3],planes:a[4],time:a[5],ticks:a[6]};}
  addBody(body){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_body_add(this.handle,r.inputF64(bodyInput(body))));}
  setBody(body){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_body_set(this.handle,r.inputF64(bodyInput(body))));}
  getBody(id){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_body_get(this.handle,validBodyId(id)));return bodyResult(r.output());}
  addPlane({id,normal=[0,1,0],offset=0,restitution=0,friction=.6}){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_plane_add(this.handle,r.inputF64([id,...finiteArray(normal,3,'Plane normal'),offset,restitution,friction,0])));}
  step(dt,steps=1){this.requireLive();const r=this.runtime;r.check(r.native._pp_sim_world_step(this.handle,dt,stepCount(steps)));return stepResult(r.output());}
  buoyancyStep(hull,{bodyId=1,dt=1/120,steps=1,density=1000,gravity=9.80665,waterLevel=0,hullOriginBody=[0,0,0],scale=[1,1,1]}={}){
    this.requireLive();if(!(hull instanceof SimulationHull)||hull.runtime!==this.runtime)throw new Error('Hull and World must belong to the same WASM runtime');hull.requireLive();
    const r=this.runtime,n=r.inputF64([density,gravity,waterLevel,...finiteArray(hullOriginBody,3,'Hull origin'),...finiteArray(scale,3,'Scale')]);
    validBodyId(bodyId);
    r.check(r.native._pp_sim_world_buoyancy_step(this.handle,hull.handle,bodyId,dt,stepCount(steps),n));return stepResult(r.output());
  }
  dispose(){if(this.handle){this.runtime.check(this.runtime.native._pp_sim_world_destroy(this.handle));this.handle=0;}}
}
export async function createFloatSimulation({mode='heave',wasmBytes,manifest}={}){
  const runtime=await loadSimulationRuntime({wasmBytes,manifest}),hull=runtime.createHull(createBoxMesh([4,2,4]));
  let world,currentMode,origin,initialEnergy=0,contacts=0,disposed=false;
  function snapshot(){
    if(disposed)throw new Error('Float simulation is disposed');
    const body=world.getBody(1),hullPosition=add(body.position,quaternionRotate(origin,body.orientation));
    const hydro=hull.query({density:1000,gravity:10,position:hullPosition,orientation:body.orientation,centerOfMass:body.position});
    const potentialEnergy=currentMode==='heave'?.5*160000*body.position[1]**2:320000*(.5-quaternionRotate(origin,body.orientation)[1]);
    const totalEnergy=body.kineticEnergy+potentialEnergy;
    return {...body,mode:currentMode,hullPosition,hullSize:[4,2,4],hullOriginBody:[...origin],potentialEnergy,totalEnergy,initialEnergy,relativeEnergyError:initialEnergy?(totalEnergy-initialEnergy)/initialEnergy:0,submergedVolume:hydro.submergedVolume,buoyantForce:hydro.force,buoyantTorque:hydro.torque,contacts};
  }
  function reset(nextMode=currentMode){
    if(disposed)throw new Error('Float simulation is disposed');if(!['heave','roll'].includes(nextMode))throw new Error('Unknown floating reference mode');
    const candidate=runtime.createWorld({gravity:[0,-10,0]});
    try{candidate.addBody({id:1,mass:nextMode==='heave'?16000:32000,radius:.25,inertia:nextMode==='heave'?[16000*20/12,16000*32/12,16000*20/12]:[24000,48000,40000],position:nextMode==='heave'?[0,.1,0]:[0,-4,0],orientation:nextMode==='heave'?[0,0,0,1]:[0,0,Math.sin(.075),Math.cos(.075)]});}
    catch(error){candidate.dispose();throw error;}
    world?.dispose();world=candidate;currentMode=nextMode;origin=nextMode==='heave'?[0,0,0]:[0,.5,0];contacts=0;initialEnergy=0;initialEnergy=snapshot().totalEnergy;return snapshot();
  }
  try{reset(mode);}catch(error){world?.dispose();hull.dispose();throw error;}
  return {get diagnostics(){return runtime.diagnostics;},snapshot,reset,
    step(dt=1/120){if(disposed)throw new Error('Float simulation is disposed');contacts=world.buoyancyStep(hull,{dt,gravity:10,hullOriginBody:origin}).contacts;return snapshot();},
    dispose(){if(!disposed){world.dispose();hull.dispose();disposed=true;}}};
}
