// CPU-observed durations only: no GPU timestamp or display/presentation claim.
// Use a dedicated Renderer. The caller owns initialization, stats snapshots and
// disposal; direct external rendering (including clock side effects) is unsafe.
const busyRenderers=new WeakSet();
const names=['syncRender','validationWait','queueWait'];
const actualError=value=>value instanceof Error?value:new Error('Non-Error value thrown during GPU profiling',{cause:value});

export function createDerivedGPUProfiler(renderer,{now=()=>performance.now()}={}){
  if(!renderer||typeof renderer.render!=='function'||typeof renderer.renderChecked!=='function'||!renderer.device||
    typeof renderer.device.popErrorScope!=='function'||typeof renderer.device.queue?.onSubmittedWorkDone!=='function'||typeof now!=='function')
    throw new TypeError('GPU profiler requires a dedicated renderer and a clock function');
  const device=renderer.device,queue=device.queue,render=renderer.render,checked=renderer.renderChecked;
  let active=null;
  function clock(state){
    if(state.clockError)return null;
    let value;try{value=now();}catch(error){state.clockError=actualError(error);return null;}
    if(!Number.isFinite(value)){state.clockError=new TypeError('GPU profiling clock must return finite numbers');return null;}
    if(state.lastTime!==null&&value<state.lastTime){state.clockError=new RangeError('GPU profiling clock moved backwards');return null;}
    state.lastTime=value;return value;
  }
  function begin(name){
    const state=active;if(!state)return null;
    ++state.stages[name].calls;
    if(state.stage!==null)state.clockError??=new Error('GPU profiling stages overlapped');
    state.stage=name;return {state,name,start:clock(state)};
  }
  function end(mark){
    if(!mark)return;
    const {state,name,start}=mark,finish=clock(state);state.stage=null;
    if(start!==null&&finish!==null){const duration=finish-start,total=state.stages[name].elapsedMs+duration;
      if(!Number.isFinite(duration)||!Number.isFinite(total))state.clockError??=new RangeError('GPU profiling duration is not representable');
      else state.stages[name].elapsedMs=total;
    }
  }
  function sync(operation){const mark=begin('syncRender');try{return operation();}finally{end(mark);}}
  async function wait(name,operation){const mark=begin(name);try{return await operation();}finally{end(mark);}}
  // Separate proxy targets avoid invariants on frozen/non-writable source
  // methods. Native WebGPU methods always receive their original branded this.
  function facade(original,overrides){
    const forwarded=new Map();
    return new Proxy(Object.create(null),{
      get(_target,key){
        if(Object.hasOwn(overrides,key))return overrides[key];
        const value=Reflect.get(original,key,original);if(typeof value!=='function')return value;
        const old=forwarded.get(key);if(old?.value===value)return old.bound;
        const bound=(...args)=>Reflect.apply(value,original,args);forwarded.set(key,{value,bound});return bound;
      },
      set(_target,key,value){return Reflect.set(original,key,value,original);}
    });
  }
  const queueView=facade(queue,{onSubmittedWorkDone:(...args)=>wait('queueWait',()=>Reflect.apply(queue.onSubmittedWorkDone,queue,args))});
  const deviceView=facade(device,{queue:queueView,popErrorScope:(...args)=>wait('validationWait',()=>Reflect.apply(device.popErrorScope,device,args))});
  const view=facade(renderer,{device:deviceView,render:(...args)=>sync(()=>Reflect.apply(render,renderer,args))});

  async function renderChecked(items,camera,time=0){
    if(busyRenderers.has(renderer))return {completed:false,error:new Error('GPU profiler renderer is already active; reentry is unsupported'),clockError:null,timing:null};
    busyRenderers.add(renderer);
    const state={stages:Object.fromEntries(names.map(name=>[name,{calls:0,elapsedMs:0}])),lastTime:null,stage:null,clockError:null};
    let completed=false,error=null,timing=null;active=state;
    try{
      const start=clock(state);
      try{await Reflect.apply(checked,view,[items,camera,time]);completed=true;}catch(failure){error=actualError(failure);}
      const finish=clock(state);
      if(!state.clockError){
        const elapsedMs=finish-start,sum=names.reduce((total,name)=>total+state.stages[name].elapsedMs,0),unassignedMs=elapsedMs-sum;
        if(!Number.isFinite(elapsedMs)||!Number.isFinite(sum)||!Number.isFinite(unassignedMs)||unassignedMs<0)
          state.clockError=new RangeError('GPU profiling duration or exclusive stage residual is not representable');
        else timing={elapsedMs,stages:state.stages,unassignedMs};
      }
    }catch(failure){error??=actualError(failure);}
    finally{active=null;busyRenderers.delete(renderer);}
    return {completed,error:error??state.clockError,clockError:state.clockError,timing};
  }
  // Validation and queue waits include promise scheduling/instrumentation. The
  // latter covers all work queued before that call, not just this mesh. Residual
  // includes checked control flow, wrapper overhead and other unclassified work;
  // do not call it pure JS time. An uninstrumented baseline is still required.
  return Object.freeze({renderChecked});
}
