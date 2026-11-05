export const WORLD_CCD_DEFAULTS=Object.freeze({mode:'corridor',height:0,speed:100,gravityY:-9.8,forceY:4,torqueZ:.2,dt:.06,timeTolerance:1e-7,spatialTolerance:1e-6,maxEventBatches:32,maxRootEvaluations:1000000});
export const WORLD_CCD_PRESETS=Object.freeze({corridor:{},floor:{mode:'floor',height:2,speed:10000,gravityY:-10,forceY:0,torqueZ:0,dt:.001},budget:{maxEventBatches:1},support:{mode:'support',height:.5,speed:0,gravityY:-10,forceY:0,torqueZ:0,dt:.01}});
const fields={height:['initial-y',-.5,10],speed:['initial-speed',0,10000],gravityY:['gravity-y',-30,30],forceY:['force-y',-30,30],torqueZ:['torque-z',-1,1]};
const failures={none:'なし',invalid_input:'入力が受入範囲外',initial_contact:'初期境界・初期重複（W1未対応）',query_unresolved:'接触照会が未解決',event_budget:'衝撃batch予算不足',segment_budget:'自由区間予算不足',query_budget:'形状照会予算不足',root_budget:'根の評価予算不足',geometric_guard:'時間・空間・丸めguardを証明できない',propagation_failure:'自由伝播・回転の数値範囲外',solver_failure:'衝撃solverの監査・予算が不合格',sustained_contact_required:'持続支持モデルW2が必要',numerical_failure:'数値条件を満たせない'};
const parse=(value,label)=>{if(typeof value==='string'&&!value.trim())throw new Error(`${label}を入力してください。`);const x=Number(value);if(!Number.isFinite(x))throw new Error(`${label}には有限の数を指定してください。`);return x;};
const vector=(a,n=3)=>Array.isArray(a)&&a.length===n&&a.every(Number.isFinite);
const text=v=>String(v);
const vectorText=(v,unit)=>`${v.map(text).join(', ')} ${unit}`;
const clone=v=>JSON.parse(JSON.stringify(v));

export function continuousWorldCase(input={}) {
  const p={...WORLD_CCD_DEFAULTS,...input};
  if(!['corridor','floor','support'].includes(p.mode))throw new Error('未知のWorld実験です。');
  for(const [key,[,lo,hi]]of Object.entries(fields)){p[key]=parse(p[key],key);if(p[key]<lo||p[key]>hi)throw new Error('高さ・速度・荷重がラボの操作範囲外です。');}
  for(const key of ['dt','timeTolerance','spatialTolerance','maxEventBatches','maxRootEvaluations'])p[key]=parse(p[key],key);
  if(p.dt<=0||p.dt>.1)throw new Error('1tickの時間幅は0より大きく0.1秒以下です。');
  if(p.timeTolerance<1e-12||p.timeTolerance>1e-3||p.spatialTolerance<1e-12||p.spatialTolerance>5e-4)throw new Error('時間・空間guardがW1参照実験の範囲外です。');
  if(!Number.isInteger(p.maxEventBatches)||p.maxEventBatches<1||p.maxEventBatches>32||!Number.isInteger(p.maxRootEvaluations)||p.maxRootEvaluations<1||p.maxRootEvaluations>1000000)throw new Error('予算は範囲内の整数で指定してください。');
  const body={id:1,isStatic:false,mass:1,radius:.5,inertia:[.1,.1,.1],position:[0,p.height,0],orientation:[0,0,0,1],linearVelocity:p.mode==='corridor'?[p.speed,0,0]:[0,-p.speed,0],angularMomentum:[0,0,0],force:[0,p.forceY,0],torque:[0,0,p.torqueZ],restitution:p.mode==='support'?0:1,friction:0};
  const planes=p.mode==='corridor'?[{id:100,normal:[1,0,0],offset:-1.5,restitution:1,friction:0},{id:101,normal:[-1,0,0],offset:-1.5,restitution:1,friction:0}]:[{id:100,normal:[0,1,0],offset:0,restitution:body.restitution,friction:0}];
  return {parameters:p,gravity:[0,p.gravityY,0],bodies:[body],planes,dt:p.dt,settings:{timeTolerance:p.timeTolerance,spatialTolerance:p.spatialTolerance,maxEventBatches:p.maxEventBatches,maxRootEvaluations:p.maxRootEvaluations}};
}

function bodyValid(body) {
  for(const name of ['position','linearVelocity','angularMomentum','force','torque'])if(!vector(body?.[name]))throw new Error(`計算核のbody状態が不正です: ${name}`);
  if(!vector(body.orientation,4)||Math.abs(Math.hypot(...body.orientation)-1)>1e-8)throw new Error('計算核の姿勢が不正です。');
  if(!Number.isFinite(body.radius)||body.radius<=0||!Number.isFinite(body.mass)||body.mass<=0||!Number.isFinite(body.kineticEnergy)||body.kineticEnergy<0)throw new Error('計算核のbody寸法・質量・エネルギーが不正です。');
  return body;
}
function reportValid(report,source,before,after,infoBefore,infoAfter) {
  if(!report||typeof report.success!=='boolean'||!Object.hasOwn(failures,report.failure)||!Array.isArray(report.events)||report.events.length>source.settings.maxEventBatches)throw new Error('計算核のWorld CCD診断が不正です。');
  for(const key of ['advancedDt','candidateTime','pairQueries','rootEvaluations','freeSegments','maximumPropagationError','accumulatedPositionRoundoff','timeRoundoff','time','ticks'])if(!Number.isFinite(report[key])||report[key]<0)throw new Error('計算核のWorld CCD数値が不正です。');
  if(report.eventCount!==report.events.length||(!report.success&&report.failure==='none'))throw new Error('計算核のWorld CCD件数・失敗理由が不正です。');
  for(const e of report.events)if(!vector(e.entryBracket,2)||e.entryBracket[0]>e.entryBracket[1]||e.entryBracket[1]-e.entryBracket[0]>source.settings.timeTolerance+2*report.timeRoundoff||!Number.isFinite(e.respondedAt)||e.respondedAt<0||e.respondedAt>source.dt||e.respondedAt<e.entryBracket[0]-report.timeRoundoff||e.respondedAt>e.entryBracket[1]+report.timeRoundoff||!Number.isFinite(e.maximumGap)||!Number.isFinite(e.propagationError)||e.propagationError<0||e.maximumGap<0||e.maximumGap>source.settings.spatialTolerance)throw new Error('計算核のevent bracketまたは空間guardが不正です。');
  if(report.success) {
    if(report.failure!=='none'||report.advancedDt!==source.dt||infoAfter.ticks!==infoBefore.ticks+1||Math.abs(infoAfter.time-infoBefore.time-source.dt)>1e-14||after.force.some(x=>x!==0)||after.torque.some(x=>x!==0))throw new Error('計算核の成功tick・荷重消費の契約が不正です。');
  } else if(report.advancedDt!==0||JSON.stringify(before)!==JSON.stringify(after)||JSON.stringify(infoBefore)!==JSON.stringify(infoAfter))throw new Error('計算核の失敗tickが原状保持されませんでした。');
  return report;
}

// The ONLY physics transition here is the actual shared C++ World method.
// Drawing below consumes returned snapshots/events; no alternative integrator.
export class ContinuousWorldExperiment {
  constructor(runtime,input={}) {if(typeof runtime?.createWorld!=='function')throw new Error('この計算核にはWorld APIがありません。');this.runtime=runtime;this.world=null;this.reset(input);}
  reset(input={}) {
    const source=continuousWorldCase(input),next=this.runtime.createWorld({gravity:source.gravity});
    try {if(typeof next.stepContinuous!=='function')throw new Error('この計算核にはWorld CCD APIがありません。');for(const b of source.bodies)next.addBody(b);for(const p of source.planes)next.addPlane(p);bodyValid(next.getBody(1));}
    catch(error){next.dispose();throw error;}
    this.world?.dispose();this.world=next;this.source=source;this.initial=bodyValid(next.getBody(1));this.current=this.initial;this.report=null;this.finished=false;return this.snapshot();
  }
  step(settings={}) {
    if(!this.world)throw new Error('Worldは破棄されています。');if(this.finished)throw new Error('この実験は1tickを実行済みです。リセットしてください。');
    if(Object.keys(settings).some(key=>!['timeTolerance','spatialTolerance','maxEventBatches','maxRootEvaluations'].includes(key)))throw new Error('同じWorldへの再試行で変更できるのはguardと予算だけです。');
    const merged=continuousWorldCase({...this.source.parameters,...settings});this.source.settings=merged.settings;this.source.parameters=merged.parameters;
    const before=bodyValid(this.world.getBody(1)),infoBefore=this.world.info();
    const report=this.world.stepContinuous(this.source.dt,this.source.settings),after=bodyValid(this.world.getBody(1)),infoAfter=this.world.info();
    this.report=reportValid(report,this.source,before,after,infoBefore,infoAfter);this.current=after;this.finished=report.success;return this.snapshot();
  }
  snapshot(){return {input:clone(this.source),initial:clone(this.initial),current:clone(this.current),report:this.report?clone(this.report):null,info:this.world.info(),diagnostics:this.runtime.diagnostics};}
  dispose(){this.world?.dispose();this.world=null;}
}

function draw(canvas,state) {
  const c=canvas.getContext('2d');if(!c)return;c.clearRect(0,0,900,360);c.fillStyle='#091521';c.fillRect(0,0,900,360);if(!state)return;
  const a=state.initial,b=state.current,p=state.input.parameters,loX=p.mode==='corridor'?-2:-2,hiX=2;
  const loY=Math.min(-.8,a.position[1]-.8,b.position[1]-.8),hiY=Math.max(2,a.position[1]+1,b.position[1]+1),scale=Math.min(760/(hiX-loX),270/(hiY-loY));
  const px=x=>450+x*scale,py=y=>315-(y-loY)*scale;
  c.font='14px system-ui';c.fillStyle='#afc2d5';c.fillText('初期・最終の実body状態（中間軌道は補間しません）',24,26);
  c.strokeStyle='#6d8197';c.lineWidth=3;for(const plane of state.input.planes){c.beginPath();if(plane.normal[0]){const x=plane.offset/plane.normal[0];c.moveTo(px(x),py(loY));c.lineTo(px(x),py(hiY));}else{c.moveTo(40,py(0));c.lineTo(860,py(0));}c.stroke();}
  const sphere=(body,color,dashed)=>{c.save();c.strokeStyle=color;c.fillStyle=color;c.lineWidth=2;c.setLineDash(dashed?[5,5]:[]);c.beginPath();c.arc(px(body.position[0]),py(body.position[1]),body.radius*scale,0,Math.PI*2);c.stroke();const q=body.orientation,ux=1-2*(q[1]*q[1]+q[2]*q[2]),uy=2*(q[0]*q[1]+q[3]*q[2]);c.beginPath();c.moveTo(px(body.position[0]),py(body.position[1]));c.lineTo(px(body.position[0]+ux*body.radius*.8),py(body.position[1]+uy*body.radius*.8));c.stroke();c.restore();};
  sphere(a,'#8197ae',true);sphere(b,'#7ee1d1',false);c.fillStyle='#afc2d5';c.fillText('灰点線: 初期 / 緑: commitされた現在 / 棒: 実quaternionのbody X軸',24,345);
}
function drawTimeline(canvas,state) {
  const c=canvas.getContext('2d');if(!c)return;c.clearRect(0,0,900,180);c.fillStyle='#091521';c.fillRect(0,0,900,180);if(!state)return;
  const dt=state.input.dt,px=t=>65+770*t/dt;c.font='13px system-ui';c.strokeStyle='#455e75';c.lineWidth=1;c.beginPath();c.moveTo(65,105);c.lineTo(835,105);c.stroke();c.fillStyle='#afc2d5';for(let i=0;i<=4;i++)c.fillText(`${text(dt*i/4)} s`,px(dt*i/4)-20,145);
  c.fillText('実C++のentry bracketと早期応答時刻（区間幅は通常1px未満）',24,25);
  const r=state.report;if(!r)return;c.fillStyle=r.success?'#7ee1d1':'#ffbf75';c.fillText(r.success?'commitした1tick':'候補eventは破棄。World時計は進みません。',24,50);
  r.events.forEach((e,i)=>{const x0=px(e.entryBracket[0]),x1=px(e.entryBracket[1]);c.strokeStyle='#ffbf75';c.lineWidth=3;c.beginPath();c.moveTo(x0,78);c.lineTo(x1,78);c.stroke();c.fillStyle='#7ee1d1';c.beginPath();c.arc(px(e.respondedAt),105,4,0,Math.PI*2);c.fill();c.fillStyle='#afc2d5';c.fillText(String(i+1),px(e.respondedAt)-4,68);});
}

export async function initializeContinuousWorldLab({doc=globalThis.document,loadRuntime=async()=>(await import('../engine/simulation.mjs')).loadSimulationRuntime()}={}) {
  const get=id=>doc.getElementById(id);let runtime=null,experiment=null,state=null,busy=false,previousUnit='s';
  const unitFactor=unit=>unit==='ms'?1000:1;
  const form=()=>Object.fromEntries(['world-mode','initial-y','initial-speed','gravity-y','force-y','torque-z','tick-dt','time-guard','space-guard','event-budget','root-budget','time-unit'].map(id=>[id,get(id).value]));
  function read(){const p={mode:get('world-mode').value};for(const [key,[id]]of Object.entries(fields))p[key]=get(id).value;p.dt=parse(get('tick-dt').value,'時間幅')/unitFactor(previousUnit);p.timeTolerance=parse(get('time-guard').value,'時間guard')/unitFactor(previousUnit);p.spatialTolerance=get('space-guard').value;p.maxEventBatches=get('event-budget').value;p.maxRootEvaluations=get('root-budget').value;return continuousWorldCase(p).parameters;}
  function clear(error){state=null;get('world-error').hidden=false;get('world-error').textContent=`実験を実行できません: ${error?.message??error}`;get('world-status').textContent='結果はありません。条件修正または読込み再試行で復帰します。';get('world-step').disabled=true;get('world-budget-retry').hidden=true;for(const id of ['world-outcome','world-time','world-ticks','world-advance','world-candidate','world-position','world-velocity','world-momentum','world-loads','world-counts','world-guard','world-events'])get(id).textContent='—';get('world-json').textContent=JSON.stringify({inputForm:form(),error:String(error?.message??error),diagnostics:runtime?.diagnostics??null},null,2);draw(get('world-view'),null);drawTimeline(get('world-timeline'),null);}
  function render(next){state=next;const r=next.report;get('world-error').hidden=true;get('world-step').disabled=Boolean(r?.success);get('world-budget-retry').hidden=r?.failure!=='event_budget';
    get('world-status').textContent=!r?'初期条件を実C++ Worldに設定しました。1tickを実行できます。':r.success?'1tickをcommitしました。別の条件を試すにはリセットします。':'tick全体をrollbackしました。候補の進行はWorldへ反映していません。';
    const values={'world-outcome':!r?'未実行':r.success?'成功（1tick全体をcommit）':`失敗: ${failures[r.failure]} (${r.failure})`,'world-time':`${text(next.info.time)} s`,'world-ticks':text(next.info.ticks),'world-advance':r?`${text(r.advancedDt)} s`:'—','world-candidate':r?`${text(r.candidateTime)} s（失敗時は破棄）`:'—','world-position':vectorText(next.current.position,'m'),'world-velocity':vectorText(next.current.linearVelocity,'m/s'),'world-momentum':vectorText(next.current.angularMomentum,'kg m²/s'),'world-loads':`F: ${vectorText(next.initial.force,'N')} → ${vectorText(next.current.force,'N')} / τ: ${vectorText(next.initial.torque,'N m')} → ${vectorText(next.current.torque,'N m')}`,'world-counts':r?`${r.events.length} batches / ${r.freeSegments} 自由区間 / ${r.pairQueries} 形状照会 / ${r.rootEvaluations} 評価`:'—','world-guard':r?`最大伝播誤差 ${text(r.maximumPropagationError)} m / 時間和誤差 ${text(r.timeRoundoff)} s`:'—'};
    for(const [id,value]of Object.entries(values))get(id).textContent=value;
    get('world-events').textContent=!r?'未実行':r.events.length?r.events.map((e,i)=>`${i+1}. ${r.success?'commit':'破棄した候補'} / IDs ${e.firstId}, ${e.secondId}\n   entry [${text(e.entryBracket[0])}, ${text(e.entryBracket[1])}] s\n   応答 ${text(e.respondedAt)} s / 空間guard ${text(e.maximumGap)} m / ${e.contacts} contacts`).join('\n\n'):'eventなし。失敗時は接触なしの証拠ではありません。';
    get('world-json').textContent=JSON.stringify(next,null,2);draw(get('world-view'),next);drawTimeline(get('world-timeline'),next);return next;
  }
  function reset(){if(!runtime)return null;try{const p=read();if(experiment)return render(experiment.reset(p));experiment=new ContinuousWorldExperiment(runtime,p);return render(experiment.snapshot());}catch(error){clear(error);return null;}}
  function step(settings={}){if(!experiment||!state)return null;try{return render(experiment.step(settings));}catch(error){clear(error);return null;}}
  function units(){const unit=get('time-unit').value;get('dt-unit').textContent=unit;get('guard-unit').textContent=unit;get('tick-dt').max=String(.1*unitFactor(unit));get('time-guard').min=String(1e-12*unitFactor(unit));get('time-guard').max=String(1e-3*unitFactor(unit));}
  function preset(name){if(!Object.hasOwn(WORLD_CCD_PRESETS,name))throw new Error('未知の実験プリセットです。');const p={...WORLD_CCD_DEFAULTS,...WORLD_CCD_PRESETS[name]};get('world-mode').value=p.mode;for(const [key,[id]]of Object.entries(fields))get(id).value=String(p[key]);get('time-unit').value='s';previousUnit='s';units();for(const [id,key]of [['tick-dt','dt'],['time-guard','timeTolerance'],['space-guard','spatialTolerance'],['event-budget','maxEventBatches'],['root-budget','maxRootEvaluations']])get(id).value=String(p[key]);return reset();}
  async function retry(){if(busy)return null;busy=true;get('world-retry').disabled=true;get('world-controls').disabled=true;try{const loaded=await loadRuntime();if(typeof loaded.createWorld!=='function')throw new Error('World APIがありません。');experiment?.dispose();experiment=null;runtime=loaded;get('runtime-info').textContent=`計算: ${runtime.diagnostics.backend} / ${runtime.diagnostics.compiler??'—'} / build ${runtime.diagnostics.buildId??'—'}`;get('world-controls').disabled=false;return reset();}catch(error){runtime=null;experiment?.dispose();experiment=null;clear(error);return null;}finally{busy=false;get('world-retry').disabled=false;}}
  get('world-step').addEventListener('click',()=>step());get('world-reset').addEventListener('click',reset);get('world-retry').addEventListener('click',retry);
  get('world-budget-retry').addEventListener('click',()=>{get('event-budget').value='32';return step({maxEventBatches:32});});
  for(const [id]of Object.values(fields))get(id).addEventListener('input',reset);
  for(const id of ['tick-dt','time-guard','space-guard','event-budget','root-budget'])get(id).addEventListener('input',reset);
  get('world-mode').addEventListener('change',()=>preset(get('world-mode').value));get('time-unit').addEventListener('change',()=>{try{const unit=get('time-unit').value;if(!['s','ms'].includes(unit))throw new Error('時間単位が不正です。');const dt=parse(get('tick-dt').value,'時間幅')/unitFactor(previousUnit),guard=parse(get('time-guard').value,'時間guard')/unitFactor(previousUnit);get('tick-dt').value=String(dt*unitFactor(unit));get('time-guard').value=String(guard*unitFactor(unit));previousUnit=unit;units();reset();}catch(error){get('time-unit').value=previousUnit;clear(error);}});
  for(const name of Object.keys(WORLD_CCD_PRESETS))get(`preset-${name}`).addEventListener('click',()=>preset(name));
  units();await retry();return {reset,step,retry,preset,getState:()=>state,dispose:()=>experiment?.dispose()};
}
if(typeof document!=='undefined')initializeContinuousWorldLab();
