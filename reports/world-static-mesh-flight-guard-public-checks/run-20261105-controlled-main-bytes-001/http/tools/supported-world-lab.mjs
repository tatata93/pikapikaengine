import {loadSimulationRuntime} from '../engine/simulation.mjs';

export const SUPPORTED_DT=1/120;
export const SUPPORTED_DEFAULTS=Object.freeze({preset:'floor',maximumSubstep:1/240,maxSegments:4096});
export const SUPPORTED_SETTINGS=Object.freeze({maximumSubstep:1/240,minimumSubstep:1e-10,spatialTolerance:1e-7,contactBand:5e-8,velocityTolerance:1e-9,
  positionErrorTolerance:1e-6,velocityErrorTolerance:1e-5,orientationErrorTolerance:1e-5,relativeImpactEnergyTolerance:1e-10,
  maxAttempts:16384,maxSegments:4096,maxEvents:512,maxPairQueries:1000000,maxGuardEvaluations:4000000,
  maxNewtonIterations:32,maxLinearSolves:64,maxLineSearchSteps:16,maxContacts:128,minimumScaledPivot:1e-10,
  positionTolerance:1e-10,normalVelocityTolerance:1e-10,maximumNormalRotation:.5,maximumAngularIncrement:.5,
  guardMaxDepth:48,guardEvaluationsPerSegment:1000000,impulseIterations:128,guardPairsPerSegment:100000,maximumImpulse:1e24,
  initialGapTolerance:1e-7,initialVelocityTolerance:1e-8,positionEquationTolerance:1e-10,velocityEquationTolerance:1e-10});
export const SUPPORTED_PRESETS=Object.freeze({floor:'床上で水平荷重とトルク',stack:'1・2・3kgの積み重ね',wedge:'非直交の二つの面',return:'離れてから床へ戻る',collision:'床の支持を伴う球同士の衝突',fast:'1000m/sのすれ違い',curved:'球面に沿う支持と離脱'});
const clone=x=>JSON.parse(JSON.stringify(x));
const finite=(x,label)=>{if(typeof x==='string'&&!x.trim())throw new Error(`${label}を入力してください。`);const n=Number(x);if(!Number.isFinite(n))throw new Error(`${label}は有限の数で指定してください。`);return n;};
const vector=(x,n=3)=>Array.isArray(x)&&x.length===n&&x.every(Number.isFinite);
const body=(id,mass,position,extra={})=>({id,isStatic:false,mass,radius:.5,position,orientation:[0,0,0,1],linearVelocity:[0,0,0],angularMomentum:[0,0,0],force:[0,0,0],torque:[0,0,0],restitution:0,friction:0,...extra});
const ground=(extra={})=>({id:100,normal:[0,1,0],offset:0,restitution:0,friction:0,...extra});

export function supportedWorldCase(input={}){
  const p={...SUPPORTED_DEFAULTS,...input};if(!Object.hasOwn(SUPPORTED_PRESETS,p.preset))throw new Error('未知の実験です。');
  p.maximumSubstep=finite(p.maximumSubstep,'内部時間幅');p.maxSegments=finite(p.maxSegments,'区間予算');
  if(p.maximumSubstep<1e-8||p.maximumSubstep>.1)throw new Error('内部時間幅は0.00001〜100msの範囲です。');
  if(!Number.isInteger(p.maxSegments)||p.maxSegments<1||p.maxSegments>100000)throw new Error('区間予算は1〜100000の整数です。');
  let gravity=[0,-10,0],bodies=[body(1,1,[0,.5,0],{force:[2,0,0],torque:[0,0,.2]})],planes=[ground()];
  switch(p.preset){
    case 'floor':break;
    case 'stack':bodies=[1,2,3].map(id=>body(id,id,[0,id-.5,0],{force:[2*id,0,0]}));break;
    case 'wedge':bodies=[body(1,1,[0,0,0],{force:[-6,0,0]})];planes=[ground({offset:-.5}),ground({id:101,normal:[.6,.8,0],offset:-.5})];break;
    case 'return':gravity=[0,-40,0];bodies=[body(1,1,[0,.5,0],{linearVelocity:[0,1,0]})];break;
    case 'collision':bodies=[body(1,1,[0,.5,0],{linearVelocity:[20,0,0],force:[2,0,0],restitution:1}),body(2,1,[2,.5,0],{force:[2,0,0],restitution:1})];planes=[ground({restitution:1})];break;
    case 'fast':gravity=[0,0,0];planes=[];bodies=[body(1,1,[-2,0,0],{linearVelocity:[1000,0,0],restitution:1}),body(2,1,[2,0,0],{linearVelocity:[-1000,0,0],restitution:1})];break;
    case 'curved':gravity=[0,-4,0];planes=[];bodies=[body(1,1,[0,1,0],{linearVelocity:[1,0,0]}),body(2,1,[0,0,0],{isStatic:true})];break;
  }
  return {parameters:p,dt:SUPPORTED_DT,gravity,bodies,planes,settings:{...SUPPORTED_SETTINGS,maximumSubstep:p.maximumSubstep,maxSegments:p.maxSegments}};
}
function validateBody(b){
  for(const key of ['position','linearVelocity','angularMomentum','force','torque'])if(!vector(b?.[key]))throw new Error(`計算核の状態が不正です: ${key}`);
  if(!vector(b.orientation,4)||Math.abs(Math.hypot(...b.orientation)-1)>1e-7||!Number.isFinite(b.kineticEnergy)||b.kineticEnergy<0)throw new Error('計算核の姿勢・エネルギーが不正です。');return b;
}
const failures={none:'なし',invalid_input:'入力条件',initial_geometry:'初期幾何',pair_budget:'pair照会予算',contact_budget:'接触数予算',attempt_budget:'試行予算',segment_budget:'内部区間予算',event_budget:'イベント予算',minimum_step:'最小時間幅',constraint_failure:'拘束計算',trajectory_failure:'途中軌道監査',impulse_failure:'衝撃応答',energy_failure:'衝撃エネルギー監査',numerical_failure:'数値条件',guard_budget:'全区間監査の評価予算'};
function validateReport(r,before,after,dt){
  if(!r||typeof r.success!=='boolean'||!Object.hasOwn(failures,r.failure)||!Array.isArray(r.events)||r.eventCount!==r.events.length)throw new Error('計算核の支持World診断が不正です。');
  for(const key of ['advancedDt','candidateTime','attempts','acceptedSegments','guardEvaluations','maximumGapResidual','maximumVelocityResidual','maximumPositionErrorEstimate','maximumVelocityErrorEstimate','time','ticks'])if(!Number.isFinite(r[key])||r[key]<0)throw new Error('計算核の支持World数値が不正です。');
  for(const e of r.events)if(!['impact','velocity_repair','release'].includes(e.kind)||!Number.isFinite(e.at)||e.at<0||e.at>dt||!vector(e.normal))throw new Error('計算核の接触イベントが不正です。');
  const unchanged=JSON.stringify(before)===JSON.stringify(after);
  if(r.success){
    if(r.failure!=='none'||r.advancedDt!==dt||after.info.ticks!==before.info.ticks+1||Math.abs(after.info.time-before.info.time-dt)>1e-12||after.bodies.some(b=>b.force.some(x=>x!==0)||b.torque.some(x=>x!==0)))throw new Error('成功tickの時計または荷重消費が不正です。');
  }else if(r.failure==='none'||r.advancedDt!==0||!unchanged)throw new Error('失敗したtickで全状態・荷重・時計が保持されませんでした。');
  if(r.time!==after.info.time||r.ticks!==after.info.ticks)throw new Error('返却された時計とWorld時計が一致しません。');
  return !r.success&&unchanged;
}

// There is no alternative JS integrator: every transition calls the actual World.
export class SupportedWorldExperiment {
  constructor(runtime,input={}, {now=()=>globalThis.performance?.now()??Date.now()}={}){if(typeof runtime?.createWorld!=='function')throw new Error('World APIがありません。');this.runtime=runtime;this.now=now;this.world=null;this.reset(input);}
  read(){return {info:clone(this.world.info()),bodies:this.source.bodies.map(b=>clone(validateBody(this.world.getBody(b.id))))};}
  reset(input={}){
    const source=supportedWorldCase(input),next=this.runtime.createWorld({gravity:source.gravity});
    try{if(typeof next.stepSupported!=='function')throw new Error('支持時間積分APIがありません。');for(const b of source.bodies)next.addBody(b);for(const p of source.planes)next.addPlane(p);for(const b of source.bodies)validateBody(next.getBody(b.id));}catch(e){next.dispose();throw e;}
    this.world?.dispose();this.world=next;this.source=source;this.initial=this.read();this.current=this.initial;this.records=[];this.recordsTruncated=0;this.events=[];this.eventsTruncated=0;this.traces=this.initial.bodies.map(b=>({id:b.id,points:[b.position.slice()],pointsTruncated:0}));this.report=null;this.lastRecord=null;this.batch=null;return this.snapshot();
  }
  step(settings={}){
    if(!this.world)throw new Error('Worldは破棄されています。');
    if(Object.keys(settings).some(k=>!['maximumSubstep','maxSegments'].includes(k)))throw new Error('再試行で変更できるのは内部時間幅と区間予算です。');
    const source=supportedWorldCase({...this.source.parameters,...settings});this.source=source;
    // setBody REPLACES loads rather than accumulating them. A successful C++
    // tick consumes them once; every new 120Hz tick receives the same held load.
    for(const original of source.bodies){const current=this.world.getBody(original.id);this.world.setBody({...current,force:original.force.slice(),torque:original.torque.slice()});}
    const before=this.read(),start=this.now();const report=this.world.stepSupported(source.dt,source.settings),after=this.read(),callMilliseconds=Math.max(0,this.now()-start);
    const worldUnchanged=validateReport(report,before,after,source.dt);
    const record={before,after,report:clone(report),worldUnchanged,callMilliseconds,settings:clone(source.settings)};
    this.lastRecord=record;this.report=record.report;this.current=after;this.records.push(record);
    if(this.records.length>256){this.records.shift();++this.recordsTruncated;}
    if(report.success){
      for(const trace of this.traces){trace.points.push(after.bodies.find(b=>b.id===trace.id).position.slice());if(trace.points.length>385){trace.points.shift();++trace.pointsTruncated;}}
      for(const e of report.events)this.events.push({...clone(e),worldTime:before.info.time+e.at,tick:after.info.ticks});
      if(this.events.length>2048){const n=this.events.length-2048;this.events.splice(0,n);this.eventsTruncated+=n;}
    }
    return this.snapshot();
  }
  snapshot(){return clone({input:this.source,initial:this.initial,current:this.current,report:this.report,lastRecord:this.lastRecord,records:this.records,recordsTruncated:this.recordsTruncated,
    events:this.events,eventsTruncated:this.eventsTruncated,traces:this.traces,batch:this.batch,droppedTime:0,clockMode:'manual 120Hz; not synchronized to wall time',diagnostics:this.runtime.diagnostics});}
  dispose(){this.world?.dispose();this.world=null;}
}
const number=x=>Number(x).toPrecision(8),vec=(v,unit)=>`${v.map(number).join(', ')} ${unit}`;
function draw(canvas,state){
  const c=canvas.getContext('2d');if(!c)return;const w=canvas.width,h=canvas.height;c.clearRect(0,0,w,h);c.fillStyle='#091521';c.fillRect(0,0,w,h);if(!state)return;
  const points=state.traces.flatMap(t=>t.points),bodies=state.current.bodies;
  const minX=Math.min(-1.5,...points.map(p=>p[0]-.7)),maxX=Math.max(1.5,...points.map(p=>p[0]+.7));
  const minY=Math.min(-.8,...points.map(p=>p[1]-.7)),maxY=Math.max(2,...points.map(p=>p[1]+.7));
  const scale=Math.min((w-90)/(maxX-minX),(h-100)/(maxY-minY)),px=x=>w/2+(x-(minX+maxX)/2)*scale,py=y=>h/2+10-(y-(minY+maxY)/2)*scale;
  c.strokeStyle='#677e94';c.lineWidth=2;
  for(const p of state.input.planes){const [nx,ny]=p.normal;c.beginPath();if(ny!==0){c.moveTo(px(minX),py((p.offset-nx*minX)/ny));c.lineTo(px(maxX),py((p.offset-nx*maxX)/ny));}else if(nx!==0){c.moveTo(px(p.offset/nx),py(minY));c.lineTo(px(p.offset/nx),py(maxY));}c.stroke();}
  const colors=['#7ee1d1','#ffbf75','#a9baff'];
  for(const [i,trace]of state.traces.entries()){c.strokeStyle=colors[i%3];c.lineWidth=1;c.beginPath();trace.points.forEach((p,k)=>k?c.lineTo(px(p[0]),py(p[1])):c.moveTo(px(p[0]),py(p[1])));c.stroke();}
  for(const [i,b]of bodies.entries()){c.strokeStyle=b.isStatic?'#8195a9':colors[i%3];c.fillStyle=b.isStatic?'#233242':'#153445';c.lineWidth=2;c.beginPath();c.arc(px(b.position[0]),py(b.position[1]),b.radius*scale,0,2*Math.PI);c.fill();c.stroke();
    const q=b.orientation,ux=1-2*(q[1]*q[1]+q[2]*q[2]),uy=2*(q[0]*q[1]+q[3]*q[2]);c.beginPath();c.moveTo(px(b.position[0]),py(b.position[1]));c.lineTo(px(b.position[0]+b.radius*.8*ux),py(b.position[1]+b.radius*.8*uy));c.stroke();c.fillStyle='#e6edf5';c.font='14px system-ui';c.fillText(`#${b.id} ${b.mass} kg`,px(b.position[0])+10,py(b.position[1])-b.radius*scale-8);}
  c.font='14px system-ui';c.fillStyle='#afc2d5';c.fillText(`XY面 / 位置 m / 目盛長 ${number(1/scale*100)} m = 100px`,22,26);c.fillText('線: 成功tickの位置を結ぶ模式軌跡 / 棒: 実姿勢のbody X軸',22,h-20);
}

export async function initializeSupportedWorldLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,yieldFrame=()=>new Promise(resolve=>globalThis.requestAnimationFrame?requestAnimationFrame(resolve):resolve()),now}={}){
  const get=id=>doc.getElementById(id);let runtime=null,experiment=null,state=null,busy=false;
  const settings=()=>({maximumSubstep:finite(get('maximum-substep').value,'内部時間幅')/1000,maxSegments:finite(get('segment-budget').value,'区間予算')});
  function lock(){get('supported-controls').disabled=busy||!runtime;get('supported-retry').disabled=busy;}
  function clear(error){state=null;get('supported-error').hidden=false;get('supported-error').textContent=String(error.message??error);get('supported-status').textContent='実行結果なし。入力修正または計算核の再読込で復帰できます。';
    for(const id of ['supported-clock','supported-counts','supported-geometry','supported-estimate','supported-invariant','supported-bodies','supported-events'])get(id).textContent='—';get('supported-json').textContent=JSON.stringify({error:String(error.message??error),diagnostics:runtime?.diagnostics??null},null,2);draw(get('supported-view'),null);}
  function render(next){
    state=next;get('supported-error').hidden=true;const r=next.report,record=next.lastRecord;get('supported-status').textContent=!r?'初期状態を設定しました。ボタンを押すまで時間は進みません。':r.success?'120Hzの成功tickだけをWorldへ反映しました。':`tick失敗: ${failures[r.failure]} (${r.failure})。状態・荷重・時計は保持されています。`;
    get('supported-clock').textContent=`t=${number(next.current.info.time)} s / ${next.current.info.ticks} tick / 落ちた時間 0 s（手動。実時間同期なし）`;
    get('supported-counts').textContent=r?`直近tick: ${r.acceptedSegments} 内部区間 / ${r.attempts} 試行 / ${r.rejectedAttempts} 棄却 / ${r.constraintSolves} 拘束計算 / ${r.guardEvaluations} 幾何評価 / 呼出し ${number(record.callMilliseconds)} ms`:'未実行';
    get('supported-geometry').textContent=r?`定義した候補放物線全体: 貫通許容帯 ${number(next.input.settings.spatialTolerance)} m / 拘束端点gap残差 ${number(r.maximumGapResidual)} m / 最後の監査 ${r.lastGuardFailure}`:'全区間監査はtick実行時に行います。';
    get('supported-estimate').textContent=r?`粗い1歩と細かい2歩の差: 位置 ${number(r.maximumPositionErrorEstimate)} m / 速度 ${number(r.maximumVelocityErrorEstimate)} m/s。連続真解を囲む誤差上限ではありません。`:'時間積分の誤差推定と、区間による幾何監査は別に表示します。';
    get('supported-invariant').textContent=!record?'各tick前に同じ保持荷重を再設定します。':r.success?'成功: 全bodyの保持荷重を一度消費、時計を1tick進めたことを前後状態から確認。':record.worldUnchanged?'失敗: 全body状態・保持荷重・World infoが完全一致。リセットせず再試行できます。':'状態保持の確認なし';
    get('supported-bodies').textContent=next.current.bodies.map(b=>`#${b.id} ${b.isStatic?'静的':'動的'} / ${b.mass} kg\np: ${vec(b.position,'m')}\nv: ${vec(b.linearVelocity,'m/s')}\nL: ${vec(b.angularMomentum,'kg m²/s')}\n保持F: ${vec(b.force,'N')} / τ: ${vec(b.torque,'N m')}`).join('\n\n');
    const kinds={impact:'衝撃',velocity_repair:'微小法線速度の処理',release:'離脱'};
    const committed=next.events.map(e=>`t=${number(e.worldTime)} s / ${kinds[e.kind]} / #${e.firstId}→#${e.secondId} / ${e.contacts}接触 / impulse ${number(e.impulseSum)} N s`);
    if(r&&!r.success)committed.push(...r.events.map(e=>`破棄した候補: tick内${number(e.at)} s / ${kinds[e.kind]} / #${e.firstId}→#${e.secondId}`));
    get('supported-events').textContent=committed.length?committed.join('\n'):'接触イベント記録なし。支持を保つ各小区間は衝撃イベントとは別です。';
    get('supported-json').textContent=JSON.stringify(next,null,2);draw(get('supported-view'),next);lock();return next;
  }
  function reset(){if(busy||!runtime)return null;try{const input={preset:get('supported-preset').value,...settings()};if(experiment)return render(experiment.reset(input));experiment=new SupportedWorldExperiment(runtime,input,{now});return render(experiment.snapshot());}catch(e){clear(e);return null;}}
  async function run(count=1){
    if(busy||!experiment)return null;if(![1,12,96].includes(count))throw new Error('手動tick数は1、12、96です。');
    busy=true;lock();let completed=0;
    try{const input=settings();supportedWorldCase({...experiment.source.parameters,...input});
      for(let i=0;i<count;++i){const next=experiment.step(input);if(next.report.success)++completed;experiment.batch={requested:count,completed};render(experiment.snapshot());if(!next.report.success)break;if((i+1)%4===0&&i+1<count)await yieldFrame();}
      return state;
    }catch(e){clear(e);return null;}finally{busy=false;lock();}
  }
  async function retry(){if(busy)return null;busy=true;experiment?.dispose();experiment=null;runtime=null;state=null;lock();
    get('supported-status').textContent='計算核を読込み中…';get('supported-error').hidden=true;
    for(const id of ['supported-clock','supported-counts','supported-geometry','supported-estimate','supported-invariant','supported-bodies','supported-events'])get(id).textContent='—';get('supported-json').textContent='読込み中';draw(get('supported-view'),null);
    try{runtime=await loadRuntime();if(typeof runtime?.createWorld!=='function')throw new Error('World APIがありません。');get('runtime-info').textContent=`${runtime.diagnostics?.backend} / ${runtime.diagnostics?.compiler??'—'} / ${runtime.diagnostics?.wasmBytes??'—'} bytes / build ${runtime.diagnostics?.buildId??'—'}`;}
    catch(e){runtime=null;clear(e);}finally{busy=false;lock();}if(runtime)return reset();return null;
  }
  for(const count of [1,12,96])get(`supported-step-${count}`).addEventListener('click',()=>run(count));
  get('supported-reset').addEventListener('click',reset);get('supported-retry').addEventListener('click',retry);get('supported-preset').addEventListener('change',reset);
  get('supported-budget-retry').addEventListener('click',()=>{get('segment-budget').value='4096';return run(1);});
  await retry();return {reset,run,retry,getState:()=>state,getExperiment:()=>experiment,dispose:()=>{experiment?.dispose();experiment=null;}};
}
if(typeof document!=='undefined')initializeSupportedWorldLab();
