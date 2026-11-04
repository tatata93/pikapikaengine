import {Renderer} from '../engine/renderer.mjs';
import {FixedClock,FrameLog} from '../engine/time.mjs';
import {lerp,quaternionNlerp,quaternionRotate} from '../engine/math.mjs';

const finiteVector=(v,n)=>Array.isArray(v)&&v.length===n&&Array.from({length:n},(_,i)=>i).every(i=>Number.isFinite(v[i]));
function checkState(s) {
  for(const field of ['position','linearVelocity','angularVelocity','hullPosition','hullSize','hullOriginBody','buoyantForce','buoyantTorque'])if(!finiteVector(s[field],3))throw new Error(`計算核の状態が不正です: ${field}`);
  if(!finiteVector(s.orientation,4)||Math.abs(Math.hypot(...s.orientation)-1)>1e-8)throw new Error('計算核の姿勢が単位quaternionではありません。');
  for(const field of ['time','kineticEnergy','potentialEnergy','totalEnergy','initialEnergy','relativeEnergyError','submergedVolume','mass'])if(!Number.isFinite(s[field]))throw new Error(`計算核の数値が不正です: ${field}`);
  if(s.mass<=0||s.hullSize.some(value=>value<=0))throw new Error('計算核の質量・形状寸法が正ではありません。');
  if(s.contacts!==0)throw new Error('無接触の参照に接触が発生しました。');
  return s;
}
export const rollAngle=orientation=>2*Math.atan2(orientation[2],orientation[3]);

export class FloatLabController {
  constructor(simulation,{now=()=>performance.now()}={}){this.simulation=simulation;this.now=now;this.clock=new FixedClock(120,24);this.tickLimit=7200;this.reset('heave');}
  reset(mode=this.mode) {
    if(!['heave','roll'].includes(mode))throw new Error('未知の浮遊体ケースです。');
    const next=checkState(this.simulation.reset(mode));
    this.mode=mode;this.previous=next;this.current=next;this.running=false;this.clock.reset();
    this.lastStepMs=0;this.totalTicks=0;this.maxEnergyError=Math.abs(next.relativeEnergyError);this.ticks=[];this.recordTick(0);return next;
  }
  recordTick(cpuMs){const s=this.current;this.ticks.push({tick:this.totalTicks,time:s.time,position:[...s.position],orientation:[...s.orientation],linearVelocity:[...s.linearVelocity],angularVelocity:[...s.angularVelocity],totalEnergy:s.totalEnergy,relativeEnergyError:s.relativeEnergyError,submergedVolume:s.submergedVolume,contacts:s.contacts,cpuMs});if(this.ticks.length>this.tickLimit)this.ticks.shift();}
  integrate(dt){const start=this.now(),next=checkState(this.simulation.step(dt));this.lastStepMs=this.now()-start;this.previous=this.current;this.current=next;this.totalTicks++;this.maxEnergyError=Math.max(this.maxEnergyError,Math.abs(next.relativeEnergyError));this.recordTick(this.lastStepMs);return next;}
  step(){this.running=false;this.clock.accumulator=0;const next=this.integrate(this.clock.dt);this.clock.tick++;return next;}
  advance(elapsed){return this.running?this.clock.advance(elapsed,dt=>this.integrate(dt)):1;}
  pose(alpha=1){
    const position=lerp(this.previous.position,this.current.position,alpha),orientation=quaternionNlerp(this.previous.orientation,this.current.orientation,alpha);
    const offset=quaternionRotate(this.current.hullOriginBody,orientation),hullPosition=position.map((value,i)=>value+offset[i]);
    return {position,orientation,hullPosition};
  }
  report(){return {mode:this.mode,simulationHz:120,maximumCatchupTicks:24,droppedSeconds:this.clock.droppedSeconds,totalTicks:this.totalTicks,retainedTickSamples:this.ticks.length,tickSampleLimit:this.tickLimit,maxRelativeEnergyError:this.maxEnergyError,current:this.current,diagnostics:this.simulation.diagnostics,ticks:this.ticks};}
}

const grid=(()=>{const items=[];for(let i=-8;i<=8;i++){
  const strong=i===0,color=strong?[0.15,0.65,0.7]:[0.09,0.3,0.4];
  items.push({position:[i,0,0],scale:[strong?0.035:0.015,0.012,16],color},{position:[0,0,i],scale:[16,0.012,strong?0.035:0.015],color});
}return items;})();
export function floatRenderItems(controller,alpha) {
  const pose=controller.pose(alpha),size=controller.current.hullSize;
  const topOffset=quaternionRotate([0,size[1]/2+0.015,0],pose.orientation);
  return [...grid,{position:pose.hullPosition,scale:size,orientation:pose.orientation,color:[0.52,0.57,0.34]},
    {position:pose.hullPosition.map((value,i)=>value+topOffset[i]),scale:[size[0]*0.75,0.03,size[2]*0.75],orientation:pose.orientation,color:[0.94,0.59,0.2],emission:0.03}];
}

const format=(value,digits=4)=>Number(value).toLocaleString('ja-JP',{minimumFractionDigits:digits,maximumFractionDigits:digits});
function drawTrace(canvas,controller){
  const ctx=canvas.getContext('2d');if(!ctx)return;
  ctx.clearRect(0,0,850,220);ctx.fillStyle='#091521';ctx.fillRect(0,0,850,220);ctx.font='13px system-ui';
  const points=controller.ticks.filter(row=>row.time>=controller.current.time-10),end=Math.max(10,controller.current.time),begin=end-10,limit=controller.mode==='heave'?0.12:0.18;
  const value=row=>controller.mode==='heave'?row.position[1]:rollAngle(row.orientation),px=t=>50+(t-begin)/10*775,py=v=>105-v/limit*75;
  ctx.lineWidth=1;ctx.strokeStyle='#375569';ctx.beginPath();ctx.moveTo(50,105);ctx.lineTo(825,105);ctx.stroke();ctx.fillStyle='#b7cbd8';
  for(const v of [-limit,0,limit])ctx.fillText(v.toFixed(2),4,py(v)+4);
  for(let i=0;i<=5;i++)ctx.fillText(`${(begin+2*i).toFixed(0)}s`,px(begin+2*i)-8,201);
  ctx.fillText(controller.mode==='heave'?'Y [m]':'Z傾き [rad]',7,18);ctx.strokeStyle='#7ee1d1';ctx.lineWidth=2;ctx.beginPath();
  points.forEach((row,i)=>{if(i===0)ctx.moveTo(px(row.time),py(value(row)));else ctx.lineTo(px(row.time),py(value(row)));});ctx.stroke();
}

export async function initializeFloatLab({doc=globalThis.document,requestFrame=callback=>requestAnimationFrame(callback),now=()=>performance.now(),createSimulation=null,createRenderer=(canvas,onError)=>Renderer.create(canvas,onError)}={}) {
  const get=id=>doc.getElementById(id),events=[],frameLog=new FrameLog(7200);let simulation,renderer,controller,lastTimestamp=null,alpha=1,faulted=false,lastFrameMs=0,lastCpuMs=0,totalEvents=0,exportUrl;
  const modeDescription={heave:'4×2×4m、質量16000kg、初期中心y=0.1m、初速0。水面の近くで上下に振動する参照です。',roll:'4×2×4m、質量32000kg、重心Y=−4m、排水原点が重心よりbodyYで0.5m上。全没した箱をZ軸へ0.15rad傾けます。'};
  function event(type,extra={}){totalEvents++;events.push({type,wallMs:now(),simulationTime:controller?.current.time??null,...extra});if(events.length>1000)events.shift();}
  function fatal(error){faulted=true;if(controller)controller.running=false;get('float-status').textContent='実験を続行できません。';get('float-error').hidden=false;get('float-error').textContent=String(error?.message??error);for(const id of ['float-run','float-step','float-reset','float-mode'])get(id).disabled=true;event('failure',{message:String(error?.message??error)});}
  function updateReadouts(){
    const s=controller.current,values={'float-time':format(s.time,3),'float-ticks':String(controller.totalTicks),'float-position':s.position.map(v=>format(v)).join(', '),'float-velocity':s.linearVelocity.map(v=>format(v)).join(', '),'float-angle':format(rollAngle(s.orientation),5),'float-omega':format(s.angularVelocity[2],5),'float-volume':format(s.submergedVolume,4),'float-force':format(s.buoyantForce[1],2),'float-energy':format(s.totalEnergy,6),'float-energy-error':s.relativeEnergyError.toExponential(3),'float-energy-max':controller.maxEnergyError.toExponential(3),'float-dropped':format(controller.clock.droppedSeconds,4),'float-frame-ms':format(lastFrameMs,2),'float-cpu-ms':format(lastCpuMs,3),'float-step-ms':format(controller.lastStepMs,3),'float-contacts':String(s.contacts)};
    for(const [id,value]of Object.entries(values))get(id).textContent=value;
    get('float-run').textContent=controller.running?'停止':'再生';get('float-run').setAttribute('aria-pressed',String(controller.running));
    get('float-status').textContent=controller.running?'C++ WebAssemblyで120Hz更新中。':'停止中。コマ送りまたは再生できます。';
    drawTrace(get('trace'),controller);
  }
  function setRunning(value){controller.running=value;alpha=1;event(value?'run':'pause');updateReadouts();}
  const initializationStart=now();
  try {
    const factory=createSimulation??(await import('../engine/simulation.mjs')).createFloatSimulation;
    simulation=await factory({mode:'heave'});controller=new FloatLabController(simulation,{now});
    renderer=await createRenderer(get('float-view'),fatal);renderer.fog=0.012;
    if(faulted)throw new Error('GPU初期化中に検証エラーが発生しました。');
    for(const id of ['float-run','float-step','float-reset','float-mode','float-download','float-inspect'])get(id).disabled=false;
    const initializationMs=now()-initializationStart,diagnostics=simulation.diagnostics;
    get('runtime-info').textContent=`計算: ${diagnostics.backend} / ${diagnostics.compiler??'compiler情報なし'} / ${diagnostics.wasmBytes??'—'} bytes / build ${diagnostics.buildId??'—'}`;
    get('float-run').addEventListener('click',()=>{try{setRunning(!controller.running);}catch(error){fatal(error);}});
    get('float-step').addEventListener('click',()=>{try{controller.step();alpha=1;event('step',{cpuMs:controller.lastStepMs});updateReadouts();}catch(error){fatal(error);}});
    function reset(){try{controller.reset(get('float-mode').value);alpha=1;event('reset',{mode:controller.mode});get('mode-description').textContent=modeDescription[controller.mode];updateReadouts();}catch(error){fatal(error);}}
    get('float-reset').addEventListener('click',reset);get('float-mode').addEventListener('change',reset);
    doc.addEventListener('visibilitychange',()=>{if(doc.hidden){if(controller.running)setRunning(false);event('visibility-pause');lastTimestamp=null;}});
    function report(){return {schema:1,created:new Date().toISOString(),measurement:'rAF callback interval + CPU simulation/encode/submit/chart/DOM; final CPU-label write, GPU and presentation unmeasured',initializationMs,simulation:controller.report(),render:frameLog.report({quality:'GGX direct + constant ambient; fixed geometry; water reference grid; no shadows',userAgent:globalThis.navigator?.userAgent??null,resolution:[get('float-view').width,get('float-view').height],backend:'WebGPU',gpuMs:null,presentedFrames:null}),events,totalEvents,eventSampleLimit:1000,scope:'Single isolated dynamic body, no contact, static fluid field. No CFD, waves, drag or audio. Tick history covers the current reset segment. Render history spans resets with mode and running markers. Pauses stop simulation; visibility pause gaps are events, not hidden simulation progress.'};}
    get('float-download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(report(),null,2)],{type:'application/json'})),anchor=doc.createElement('a');anchor.href=url;anchor.download='pikapika-float-lab.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    get('float-inspect').addEventListener('click',()=>{
      const data=report(),{ticks,...simulationSummary}=data.simulation,{samples,...renderSummary}=data.render;
      if(exportUrl)URL.revokeObjectURL(exportUrl);exportUrl=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      get('float-report-link').href=exportUrl;
      get('float-report').value=JSON.stringify({...data,simulation:simulationSummary,render:renderSummary,detail:'All retained tick/frame samples are in the full JSON download.'},null,2);
      get('float-report-panel').hidden=false;
    });
    // Explicit local development capture; production Pages has no write endpoint.
    if(globalThis.location?.protocol==='http:'&&['localhost','127.0.0.1'].includes(globalThis.location.hostname)&&new URL(globalThis.location.href).searchParams.get('capture')==='1'){
      get('float-capture').hidden=false;
      get('float-capture').addEventListener('click',async()=>{try{const response=await fetch('/__capture/float',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report(),null,2)});if(!response.ok)throw new Error(`HTTP ${response.status}`);const result=await response.json();get('capture-status').textContent=`ローカル計測保存済み: ${result.bytes} bytes / ${result.file}`;}catch(error){get('capture-status').textContent=`計測保存に失敗: ${error.message}`;}});
    }
    updateReadouts();event('ready');
    function frame(timestamp){
      if(faulted)return;
      try {
        const start=now(),elapsed=lastTimestamp===null?0:Math.max(0,(timestamp-lastTimestamp)/1000);lastTimestamp=timestamp;lastFrameMs=elapsed*1000;
        const before=now();alpha=controller.advance(elapsed);const simulationMs=now()-before;
        const items=floatRenderItems(controller,controller.running?Math.min(1,alpha):1);
        renderer.render(items,{eye:[7,controller.mode==='roll'?3:4,9],target:[0,controller.mode==='roll'?-2:0,0]},controller.current.time);
        updateReadouts();lastCpuMs=now()-start;frameLog.record(lastFrameMs,lastCpuMs,simulationMs,items.length,0);
        Object.assign(frameLog.samples.at(-1),{running:controller.running,mode:controller.mode,simulationTime:controller.current.time,droppedSeconds:controller.clock.droppedSeconds});
        get('float-cpu-ms').textContent=format(lastCpuMs,3);requestFrame(frame);
      }catch(error){fatal(error);}
    }
    requestFrame(frame);
    return {controller,renderer,report,dispose(){faulted=true;controller.running=false;simulation.dispose();if(exportUrl)URL.revokeObjectURL(exportUrl);event('dispose');}};
  }catch(error){simulation?.dispose();fatal(error);return null;}
}

if(typeof document!=='undefined')initializeFloatLab();
