export const ACCELERATED_DEFAULTS=Object.freeze({mode:'plane',height:3,velocityY:0,accelerationY:-4,targetVelocityY:0,targetAccelerationY:0,horizonSeconds:2,timeTolerance:1e-6,maxEvaluations:32768,preview:1});
export const ACCELERATED_PRESETS=Object.freeze({plane:{},pass:{mode:'spheres'},boundary:{height:1},budget:{maxEvaluations:1},tangent:{height:2,velocityY:-2,accelerationY:2},outside:{velocityY:1,accelerationY:2},endpoint:{horizonSeconds:1}});
const controls={height:['initial-height',-5,15],velocityY:['initial-velocity',-30,30],accelerationY:['acceleration',-30,30],targetVelocityY:['target-velocity',-30,30],targetAccelerationY:['target-acceleration',-30,30]};
const kindLabels={none:'全区間で分離を証明',entry_bracket:'入口の存在を幅付きで確認',unresolved:'未解決（接触なしではありません）'};
const reasonLabels={none:'なし',initial_overlap:'初期重複',initial_boundary:'初期境界・初期符号が不確定',evaluation_budget:'評価回数の予算不足',frontier_budget:'未解決区間の記憶予算不足',depth_limit:'細分化の深さ上限',time_resolution:'時刻の表現分解能不足',numerical_uncertainty:'数値的な判定が未解決'};
const number=value=>String(value);
const rangeText=(range,unit)=>range?`[${number(range[0])}, ${number(range[1])}] ${unit}`:'—';
const parse=(value,label)=>{if(typeof value==='string'&&!value.trim())throw new Error(`${label}を入力してください。`);const x=Number(value);if(!Number.isFinite(x))throw new Error(`${label}は有限の数で指定してください。`);return x;};
const range=value=>Array.isArray(value)&&value.length===2&&value.every(Number.isFinite)&&value[0]<=value[1];

export function acceleratedCase(input={}) {
  const parameters={...ACCELERATED_DEFAULTS,...input};
  if(!['plane','spheres'].includes(parameters.mode))throw new Error('相手は平面または球を選択してください。');
  for(const [name,[,min,max]]of Object.entries(controls)){parameters[name]=parse(parameters[name],name);if(parameters[name]<min||parameters[name]>max)throw new Error('高さ・速度・加速度がラボの操作範囲外です。');}
  parameters.horizonSeconds=parse(parameters.horizonSeconds,'時間幅');parameters.timeTolerance=parse(parameters.timeTolerance,'許容幅');parameters.maxEvaluations=parse(parameters.maxEvaluations,'評価予算');parameters.preview=parse(parameters.preview,'図示時刻');
  if(parameters.horizonSeconds<0||parameters.horizonSeconds>6)throw new Error('時間幅は0〜6秒で指定してください。');
  if(parameters.timeTolerance<1e-12||parameters.timeTolerance>1)throw new Error('許容幅は1e-12〜1秒で指定してください。');
  if(!Number.isInteger(parameters.maxEvaluations)||parameters.maxEvaluations<1||parameters.maxEvaluations>32768)throw new Error('評価予算は1〜32768の整数で指定してください。');
  if(parameters.preview<0||parameters.preview>1)throw new Error('図示時刻は0〜100%で指定してください。');
  return {parameters,a:{position:[0,parameters.height,0],velocity:[0,parameters.velocityY,0],acceleration:[0,parameters.accelerationY,0],radius:parameters.mode==='plane'?1:0.5},
    b:{position:[0,0,0],velocity:[0,parameters.targetVelocityY,0],acceleration:[0,parameters.targetAccelerationY,0],radius:0.5},
    plane:{normal:[0,1,0],offset:0},horizonSeconds:parameters.horizonSeconds,
    settings:{timeTolerance:parameters.timeTolerance,maxEvaluations:parameters.maxEvaluations,maxFrontier:4096,maxDepth:64}};
}

// Drawing/endpoint input only: evaluate the prescribed quadratic, never find roots.
export function acceleratedPose(source,time) {
  const pose=s=>({...s,position:s.position.map((p,i)=>p+s.velocity[i]*time+0.5*s.acceleration[i]*time*time),velocity:s.velocity.map((v,i)=>v+s.acceleration[i]*time)});
  return {a:pose(source.a),b:pose(source.b),plane:source.plane};
}

function checkResult(result,horizon) {
  if(!result||!Object.hasOwn(kindLabels,result.kind)||!Object.hasOwn(reasonLabels,result.reason)||typeof result.initialSeparationProven!=='boolean'||!Number.isFinite(result.safeUntil)||result.safeUntil<0||result.safeUntil>horizon)throw new Error('計算核の加速照会結果が不正です。');
  for(const value of [result.initialValue,result.valueAtSafe,result.bracket,result.negativeValue])if(value!==null&&!range(value))throw new Error('計算核の包含区間が不正です。');
  if(result.initialSeparationProven&&(!result.initialValue||result.initialValue[0]<=0||!result.valueAtSafe||result.valueAtSafe[0]<=0))throw new Error('分離prefixに必要な正値の証拠がありません。');
  if(result.negativeWitness!==null&&(!Number.isFinite(result.negativeWitness)||result.negativeWitness<0||result.negativeWitness>horizon))throw new Error('計算核の負witness時刻が不正です。');
  if((result.negativeWitness===null)!==(result.negativeValue===null)||(result.negativeValue&&result.negativeValue[1]>=0))throw new Error('負witnessに必要な負値の証拠がありません。');
  for(const name of ['evaluations','excludedIntervals','depthReached'])if(!Number.isInteger(result[name])||result[name]<0)throw new Error('計算核の評価統計が不正です。');
  if(result.kind==='entry_bracket'&&(!result.initialSeparationProven||!result.bracket||!result.valueAtSafe||result.valueAtSafe[0]<=0||!result.negativeValue||result.negativeValue[1]>=0||result.bracket[0]!==result.safeUntil||result.bracket[1]!==result.negativeWitness))throw new Error('入口bracketに必要な正負の証拠がありません。');
  if(result.kind==='none'&&(!result.initialSeparationProven||result.safeUntil!==horizon||result.bracket!==null||result.negativeWitness!==null))throw new Error('全区間の分離を示す証拠がありません。');
  if(result.kind==='unresolved'&&(result.reason==='none'||result.bracket!==null))throw new Error('未解決結果の理由が不正です。');
  if(result.kind!=='unresolved'&&result.reason!=='none')throw new Error('確定結果と未解決理由が矛盾しています。');
  return result;
}

export function evaluateAcceleratedCase(runtime,input={}) {
  const source=acceleratedCase(input),query=(pose,horizon)=>source.parameters.mode==='plane'?runtime.queryAcceleratedPlane(pose.a,pose.plane,horizon,source.settings):runtime.queryAcceleratedSpheres(pose.a,pose.b,horizon,source.settings);
  const result=checkResult(query(source,source.horizonSeconds),source.horizonSeconds);
  const endpointInput={...acceleratedPose(source,source.horizonSeconds),horizonSeconds:0};
  const endpoint=checkResult(query(endpointInput,0),0);
  return {source,result,endpoint,endpointInput};
}

function draw(canvas,state) {
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('軌道グラフを描く機能を利用できません。');
  const {source,result}=state,p=source.parameters,h=source.horizonSeconds,pair=p.mode==='spheres';
  const samples=Array.from({length:97},(_,i)=>({t:h*i/96,...acceleratedPose(source,h*i/96)}));
  const heights=[0,...samples.flatMap(s=>[s.a.position[1]-s.a.radius,s.a.position[1]+s.a.radius,...(pair?[s.b.position[1]-s.b.radius,s.b.position[1]+s.b.radius]:[])])];
  const min=Math.min(...heights),max=Math.max(...heights),padding=Math.max(0.7,(max-min)*0.12),bottom=min-padding,top=max+padding;
  const x=t=>80+760*t/(h||1),y=v=>285-225*(v-bottom)/(top-bottom),line=(points,color,dash=[])=>{ctx.strokeStyle=color;ctx.lineWidth=2;ctx.setLineDash(dash);ctx.beginPath();points.forEach((point,i)=>i?ctx.lineTo(...point):ctx.moveTo(...point));ctx.stroke();ctx.setLineDash([]);};
  ctx.clearRect(0,0,900,440);ctx.fillStyle='#0a1522';ctx.fillRect(0,0,900,440);ctx.font='14px system-ui';
  ctx.fillStyle='#afc2d5';ctx.fillText('指定した二次軌道 / 中心Y [m]',24,27);ctx.fillText('接触後も軌道を継続（応答なし）',520,27);
  if(pair){ctx.fillStyle='#3a3026';ctx.beginPath();samples.forEach((s,i)=>i?ctx.lineTo(x(s.t),y(s.b.position[1]+s.b.radius)):ctx.moveTo(x(s.t),y(s.b.position[1]+s.b.radius)));for(const s of [...samples].reverse())ctx.lineTo(x(s.t),y(s.b.position[1]-s.b.radius));ctx.closePath();ctx.fill();}
  else {ctx.fillStyle='#322a28';ctx.fillRect(80,y(0),760,Math.max(0,285-y(0)));line([[80,y(0)],[840,y(0)]],'#ffbf75');}
  for(let i=0;i<=4;i++){const time=h*i/4,level=bottom+(top-bottom)*i/4;line([[80,y(level)],[840,y(level)]],'#23374a');ctx.fillStyle='#afc2d5';ctx.fillText(level.toFixed(1),25,y(level)+5);ctx.fillText(number(time),x(time)-10,310);}
  for(const sign of [-1,1])line(samples.map(s=>[x(s.t),y(s.a.position[1]+sign*s.a.radius)]),'#4c8594',[4,5]);
  line(samples.map(s=>[x(s.t),y(s.a.position[1])]),'#7ed5f6');if(pair)line(samples.map(s=>[x(s.t),y(s.b.position[1])]),'#ffbf75');
  const previewTime=h*p.preview,preview=acceleratedPose(source,previewTime);line([[x(previewTime),50],[x(previewTime),286]],'#8294a8',[2,4]);
  ctx.fillStyle='#7ed5f6';ctx.beginPath();ctx.arc(x(previewTime),y(preview.a.position[1]),5,0,2*Math.PI);ctx.fill();
  ctx.fillStyle='#afc2d5';ctx.fillText('時間 t [s] →',740,331);ctx.fillText(`図示時刻 ${number(previewTime)} s`,80,331);
  ctx.fillStyle='#344355';ctx.fillRect(80,355,h>0?760:1,15);
  if(result.initialSeparationProven){ctx.fillStyle='#7ee1d1';ctx.fillRect(80,355,Math.max(1,x(result.safeUntil)-80),15);}
  if(result.bracket){line([[x(result.bracket[0]),350],[x(result.bracket[0]),377]],'#ffbf75');line([[x(result.bracket[1]),350],[x(result.bracket[1]),377]],'#ffbf75');}
  ctx.fillStyle='#7ee1d1';ctx.fillText('緑: 分離を証明したprefix',80,403);ctx.fillStyle='#ffbf75';ctx.fillText('橙線: 存在確認した入口bracket',390,403);
  ctx.fillStyle='#afc2d5';ctx.fillText(h>0?'灰: 分離を証明していない / bracketの細かい幅は数値を参照':'時間幅0秒：図示と証明の対象は初期点のみ',80,427);
  canvas.setAttribute('aria-label',`中心Yの二次軌道。${kindLabels[result.kind]}。${result.initialSeparationProven?`分離prefixは0から${result.safeUntil}秒`:'初期分離の証明なし'}。${result.bracket?`入口bracketは${result.bracket[0]}から${result.bracket[1]}秒。`:'入口bracketなし。'}`);
}

export async function initializeAcceleratedLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();}}={}) {
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false,previousUnit=get('time-unit').value;
  const factor=unit=>unit==='ms'?1000:1;
  const form=()=>Object.fromEntries(['accelerated-mode',...Object.values(controls).map(([id])=>id),'horizon','tolerance','evaluation-budget','time-unit','preview'].map(id=>[id,get(id).value]));
  function read(){const unit=get('time-unit').value;if(!['s','ms'].includes(unit))throw new Error('時間の単位が不正です。');return {mode:get('accelerated-mode').value,...Object.fromEntries(Object.entries(controls).map(([name,[id]])=>[name,get(id).value])),horizonSeconds:parse(get('horizon').value,'時間幅')/factor(unit),timeTolerance:parse(get('tolerance').value,'許容幅')/factor(unit),maxEvaluations:get('evaluation-budget').value,preview:parse(get('preview').value,'図示時刻')/100};}
  function units(){const f=factor(get('time-unit').value);get('horizon').max=String(6*f);get('tolerance').min=String(1e-12*f);get('tolerance').max=String(f);get('horizon-unit').textContent=get('time-unit').value;get('tolerance-unit').textContent=get('time-unit').value;}
  function json(){if(state)get('accelerated-json').textContent=JSON.stringify({model:'prescribed constant-acceleration trajectories; no World response',input:state.source,result:state.result,endpointInput:state.endpointInput,endpoint:state.endpoint,diagnostics:runtime.diagnostics},null,2);}
  function showError(error){state=null;get('accelerated-error').hidden=false;get('accelerated-error').textContent=`照会できません: ${error.message}`;get('accelerated-status').textContent='現在の結果は表示していません。条件を直すか読込みを再試行してください。';for(const id of ['result-kind','result-prefix','result-bracket','result-reason','result-evaluations','result-initial','result-witness','result-endpoint'])get(id).textContent='—';get('time-seconds').textContent='照会未完了';get('preview-time').textContent='図示時刻: —';if(!runtime)get('runtime-info').textContent='計算核の準備未完了';get('result-explanation').textContent='失敗を「接触なし」へ置き換えません。';get('accelerated-json').textContent=JSON.stringify({inputForm:form(),error:error.message},null,2);try{get('accelerated-view').getContext('2d')?.clearRect(0,0,900,440);get('accelerated-view').setAttribute('aria-label','現在の照会結果はありません。');}catch{}}
  function recalculate(){if(!runtime)return null;try{
    const next=evaluateAcceleratedCase(runtime,read()),{source,result,endpoint}=next;draw(get('accelerated-view'),next);
    get('target-controls').hidden=source.parameters.mode!=='spheres';get('radius-info').textContent=source.parameters.mode==='plane'?'球の半径1m、静的平面Y=0m、負Y側が固体。':'球A/Bの半径は各0.5m。相手球の初期中心Y=0m。';
    get('result-kind').textContent=kindLabels[result.kind];get('result-prefix').textContent=result.initialSeparationProven?`[0, ${number(result.safeUntil)}] s${result.safeUntil===0?'（初期点のみ）':''}`:'初期分離の証明なし';
    get('result-bracket').textContent=result.bracket?`${rangeText(result.bracket,'s')}（両端差 ≈ ${number(result.bracket[1]-result.bracket[0])} s）`:'入口bracketなし';
    get('result-reason').textContent=`${reasonLabels[result.reason]} (${result.reason})`;get('result-evaluations').textContent=`${result.evaluations} / ${source.settings.maxEvaluations} 回 · 除外 ${result.excludedIntervals} 区間 · 深さ ${result.depthReached}`;
    get('equation-unit').textContent=source.parameters.mode==='plane'?'m':'m²';get('result-initial').textContent=rangeText(result.initialValue,source.parameters.mode==='plane'?'m':'m²');
    get('result-witness').textContent=result.negativeWitness===null?'負の点の証明なし':`${number(result.negativeWitness)} s · 値 ${rangeText(result.negativeValue,source.parameters.mode==='plane'?'m':'m²')}`;
    get('result-endpoint').textContent=endpoint.kind==='none'?'終点では分離を証明':endpoint.reason==='initial_overlap'?'終点では重複を証明':'終点の符号も未解決';
    get('time-seconds').textContent=`照会幅 ${number(source.horizonSeconds)} s / 要求するbracket幅 ${number(source.settings.timeTolerance)} s`;
    get('result-explanation').textContent=result.kind==='entry_bracket'?(source.parameters.mode==='spheres'&&endpoint.kind==='none'?'終点では離れていますが、途中の入口がこのbracket内に存在します。':'このbracketより前の連続prefixは分離し、bracket内に入口の存在を確認しました。')+' 一点の厳密時刻や根の一意性、衝突後応答は示していません。':result.kind==='none'?'指定した閉区間全体で間隔式が正と証明されました。加速度や時間幅を変えれば、新しい照会が必要です。':`未解決の理由: ${reasonLabels[result.reason]}。${result.negativeWitness!==null?'負の点があっても先行区間の証拠や幅が不足するため成功にしません。':'零を含むだけでは入口の存在を確定できません。'} 接触なしへ置き換えません。`;
    get('preview-time').textContent=`図示時刻 ${number(source.horizonSeconds*source.parameters.preview)} s（指定した軌道、応答なし）`;
    get('accelerated-error').hidden=true;get('accelerated-status').textContent='実C++ WebAssemblyで区間と終点を照会しました。';state=next;json();return state;
  }catch(error){showError(error);return null;}}
  async function retry(){if(busy)return null;busy=true;get('accelerated-retry').disabled=true;get('accelerated-controls').disabled=true;get('accelerated-status').textContent='C++ WebAssemblyを読込み中…';try{const loaded=await loadRuntime();if(typeof loaded.queryAcceleratedSpheres!=='function'||typeof loaded.queryAcceleratedPlane!=='function')throw new Error('この計算核には加速軌道の照会APIがありません。');runtime=loaded;get('accelerated-controls').disabled=false;get('runtime-info').textContent=`計算: ${runtime.diagnostics.backend} / ${runtime.diagnostics.compiler??'—'} / build ${runtime.diagnostics.buildId??'—'}`;return recalculate();}catch(error){runtime=null;showError(error);return null;}finally{busy=false;get('accelerated-retry').disabled=false;}}
  function preset(name){if(!Object.hasOwn(ACCELERATED_PRESETS,name))throw new Error('不明な例です。');const p={...ACCELERATED_DEFAULTS,...ACCELERATED_PRESETS[name]};get('accelerated-mode').value=p.mode;for(const [key,[id]]of Object.entries(controls))get(id).value=String(p[key]);get('time-unit').value='s';previousUnit='s';units();get('horizon').value=String(p.horizonSeconds);get('tolerance').value=String(p.timeTolerance);get('evaluation-budget').value=String(p.maxEvaluations);get('preview').value=String(p.preview*100);return recalculate();}
  for(const [id]of Object.values(controls))get(id).addEventListener('input',recalculate);
  for(const id of ['horizon','tolerance','evaluation-budget'])get(id).addEventListener('input',recalculate);
  get('accelerated-mode').addEventListener('change',recalculate);
  get('time-unit').addEventListener('change',()=>{try{const unit=get('time-unit').value;if(!['s','ms'].includes(unit))throw new Error('時間の単位が不正です。');const h=parse(get('horizon').value,'時間幅')/factor(previousUnit),t=parse(get('tolerance').value,'許容幅')/factor(previousUnit);get('horizon').value=String(h*factor(unit));get('tolerance').value=String(t*factor(unit));previousUnit=unit;units();recalculate();}catch(error){get('time-unit').value=previousUnit;showError(error);}});
  get('preview').addEventListener('input',()=>{if(!state)return;try{const preview=parse(get('preview').value,'図示時刻')/100;if(preview<0||preview>1)throw new Error('図示時刻は0〜100%で指定してください。');state.source.parameters.preview=preview;draw(get('accelerated-view'),state);get('preview-time').textContent=`図示時刻 ${number(state.source.horizonSeconds*preview)} s（指定した軌道、応答なし）`;json();}catch(error){showError(error);}});
  for(const name of Object.keys(ACCELERATED_PRESETS))get(`preset-${name}`).addEventListener('click',()=>preset(name));
  get('accelerated-retry').addEventListener('click',retry);units();await retry();return {recalculate,retry,preset,getState:()=>state};
}
if(typeof document!=='undefined')initializeAcceleratedLab();
