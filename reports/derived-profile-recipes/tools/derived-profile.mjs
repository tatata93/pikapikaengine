import {SimulationRuntime} from '../engine/simulation.mjs';

// Synchronous measurement only. Use a dedicated runtime/module without concurrent
// callers. A separate uninstrumented baseline is required: these wrappers and
// clock reads perturb the very operation being measured.
const stageNames=['f64Exchange','u32Exchange','cppQuery','cppGetter','outputCopy'];
const actualError=value=>value instanceof Error?value:new Error('Non-Error value thrown during profiling',{cause:value});
export function createDerivedMeshProfiler(runtime,{now=()=>performance.now()}={}){
  if(!runtime||!runtime.native||typeof now!=='function')throw new TypeError('Profiler requires a runtime and a clock function');
  const originalNative=runtime.native,forwarded=new Map();let active=null;
  function clock(state){
    if(state.clockError)return null;
    let value;try{value=now();}catch(error){state.clockError=actualError(error);return null;}
    if(!Number.isFinite(value)){state.clockError=new TypeError('Profiling clock must return finite numbers');return null;}
    if(state.lastTime!==null&&value<state.lastTime){state.clockError=new RangeError('Profiling clock moved backwards');return null;}
    state.lastTime=value;return value;
  }
  function measure(name,operation){
    const state=active;if(!state)return operation();
    const stage=state.stages[name];++stage.calls;
    // The current runtime mappings do not nest. Reject unusable metrics rather
    // than double-count a future nested stage; continue the real operation.
    if(state.stage!==null){state.clockError??=new Error('Profiling stages overlapped');return operation();}
    state.stage=name;const start=clock(state);
    try{return operation();}
    finally{
      const end=clock(state);state.stage=null;
      if(start!==null&&end!==null){const elapsed=end-start,total=stage.elapsedMs+elapsed;
        if(!Number.isFinite(elapsed)||!Number.isFinite(total))state.clockError??=new RangeError('Profiling duration is not representable');
        else stage.elapsedMs=total;
      }
    }
  }
  // A separate facade avoids Proxy invariant violations even if the original
  // module has frozen non-writable exports. HEAP properties stay live, including
  // replacement TypedArray views after WASM memory growth.
  const native=new Proxy(Object.create(null),{get(_target,key){
    const value=Reflect.get(originalNative,key,originalNative);if(typeof value!=='function')return value;
    const old=forwarded.get(key);if(old?.original===value)return old.wrapper;
    const wrapper=function(...args){
      if(key==='_pp_sim_derived_mesh')return measure('cppQuery',()=>Reflect.apply(value,originalNative,args));
      if(key==='_pp_sim_derived_mesh_record'){
        if(active&&Number.isInteger(args[0])&&args[0]>=0&&args[0]<=3)++active.getterKinds[args[0]];
        return measure('cppGetter',()=>Reflect.apply(value,originalNative,args));
      }
      return Reflect.apply(value,originalNative,args);
    };
    forwarded.set(key,{original:value,wrapper});return wrapper;
  }});
  const measured=new SimulationRuntime(native,runtime.metadata,runtime.wasmBytes,runtime.startupMs);
  for(const [method,stage]of [['inputF64','f64Exchange'],['inputU32','u32Exchange'],['output','outputCopy']]){
    const original=measured[method];measured[method]=function(...args){return measure(stage,()=>Reflect.apply(original,measured,args));};
  }
  function prepare(input,settings){
    if(active)return {result:null,error:new Error('Profiler prepare is synchronous and cannot be reentered'),timing:null,clockError:null};
    const state={stages:Object.fromEntries(stageNames.map(name=>[name,{calls:0,elapsedMs:0}])),getterKinds:[0,0,0,0],lastTime:null,stage:null,clockError:null};
    let result=null,error=null,timing=null;active=state;
    try{
      const start=clock(state);
      try{result=measured.prepareDerivedMesh(input,settings);}catch(failure){error=actualError(failure);}
      const end=clock(state);
      if(!state.clockError){
        const elapsedMs=end-start,sum=stageNames.reduce((total,name)=>total+state.stages[name].elapsedMs,0),unassignedMs=elapsedMs-sum;
        if(!Number.isFinite(elapsedMs)||!Number.isFinite(sum)||!Number.isFinite(unassignedMs)||unassignedMs<0)
          state.clockError=new RangeError('Profiling duration or exclusive stage residual is not representable');
        else timing={elapsedMs,stages:state.stages,getterKinds:state.getterKinds,unassignedMs};
      }
    }catch(failure){error??=actualError(failure);}
    finally{active=null;}
    // Clock failure does not abort production computation or hide its exception.
    // Native queries may already have committed their normal copied snapshots.
    return {result,error:error??state.clockError,timing,clockError:state.clockError};
  }
  // cppQuery includes C ABI validation, prepare and snapshot commit; cppGetter
  // includes its ABI packet copy. outputCopy is JS output() only. unassignedMs
  // includes encoding/decoding/validation, instrumentation and other residual
  // work; it must not be labelled pure JavaScript time or kernel-only overhead.
  return Object.freeze({prepare});
}
