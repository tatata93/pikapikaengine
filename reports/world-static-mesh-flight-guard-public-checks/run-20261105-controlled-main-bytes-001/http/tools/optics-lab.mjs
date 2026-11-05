export const OPTICS_DEFAULTS=Object.freeze({angleDegrees:0,indexIncident:1,indexTransmitted:1.5,wavelengthNm:550,incidentOverride:null});
const kinds={transmission:'透過可能',total_internal_reflection:'全反射',uncertain:'未確定'};
const reasons={none:'なし',incident_side:'入射側の符号を確定できません',critical_angle:'臨界の符号を確定できません',numerical_output:'方向・パワーの近似計算を成立させられません'};
const controls={angleDegrees:['angle',0,89.9],indexIncident:['index-incident',0.5,5],indexTransmitted:['index-transmitted',0.5,5],wavelengthNm:['wavelength',380,780]};
const powerFields={reflectanceS:'power-rs',transmittanceS:'power-ts',reflectanceP:'power-rp',transmittanceP:'power-tp',reflectanceUnpolarized:'power-ru',transmittanceUnpolarized:'power-tu'};
const resultIds=['result-kind','result-cosines','result-reflected','result-transmitted','result-discriminant','result-dot',...Object.values(powerFields)];
const vector=value=>Array.isArray(value)&&value.length===3&&value.every(Number.isFinite);
const range=value=>Array.isArray(value)&&value.length===2&&value.every(Number.isFinite)&&value[0]<=value[1];
const number=(value,digits=6)=>Number(value).toLocaleString('ja-JP',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const scientific=value=>value===0?'0':value.toExponential(6);
const vectorText=value=>`(${value.map(v=>number(v,7)).join(', ')})`;
const rangeText=value=>`[${scientific(value[0])}, ${scientific(value[1])}]`;
const percent=value=>value>0&&value<1e-7?`${(value*100).toExponential(3)} %`:`${number(value*100,5)} %`;

export function opticsPreset(name) {
  const p={...OPTICS_DEFAULTS};
  if(name==='normal')return p;
  if(name==='brewster')return {...p,angleDegrees:Math.atan(1.5)*180/Math.PI};
  if(name==='tir')return {...p,angleDegrees:60,indexIncident:1.5,indexTransmitted:1};
  if(name==='equal')return {...p,angleDegrees:40,indexIncident:1.5,indexTransmitted:1.5};
  if(name==='critical')return {...p,angleDegrees:Math.atan2(3,4)*180/Math.PI,indexIncident:5,indexTransmitted:3,incidentOverride:[3,-4,0]};
  throw new Error('光学プリセットが不正です。');
}

export function opticsCase(input={}) {
  const parameters={...OPTICS_DEFAULTS,...input};
  for(const [name,[,min,max]]of Object.entries(controls)) {
    parameters[name]=Number(parameters[name]);
    if(!Number.isFinite(parameters[name])||parameters[name]<min||parameters[name]>max)throw new Error('角度・屈折率・波長が操作範囲外です。');
  }
  if(parameters.incidentOverride!==null&&(!vector(parameters.incidentOverride)||parameters.incidentOverride.some((v,i)=>v!==[3,-4,0][i])))throw new Error('保持する原ベクトルが不正です。');
  const angle=parameters.angleDegrees*Math.PI/180;
  const incident=parameters.incidentOverride===null?[Math.sin(angle),-Math.cos(angle),0]:[...parameters.incidentOverride];
  parameters.incidentOverride=parameters.incidentOverride===null?null:[...parameters.incidentOverride];
  return {parameters,incidentSource:parameters.incidentOverride===null?'angle':'exact-critical-vector',
    query:{incident,normal:[0,1,0],indexIncident:parameters.indexIncident,indexTransmitted:parameters.indexTransmitted,vacuumWavelength:parameters.wavelengthNm*1e-9}};
}

function checkResult(result) {
  if(!result||!Object.hasOwn(kinds,result.kind)||!Object.hasOwn(reasons,result.uncertainty)||!vector(result.incidentUnit)||!vector(result.normalUnit)||!vector(result.reflected)||!range(result.discriminant)||!range(result.incidentDot)||!Number.isFinite(result.cosineIncident)||!Number.isFinite(result.vacuumWavelength))throw new Error('計算核の光学結果が不正です。');
  if(result.kind==='uncertain') {
    if(result.power!==null||result.transmitted!==null||result.cosineTransmitted!==null)throw new Error('未確定の光学結果に成功値が混在しています。');
  } else {
    if(!result.power||Object.keys(powerFields).some(key=>!Number.isFinite(result.power[key])||result.power[key]<0||result.power[key]>1))throw new Error('計算核のパワー配分が不正です。');
    if(result.kind==='transmission'&&(!vector(result.transmitted)||!Number.isFinite(result.cosineTransmitted)))throw new Error('計算核の屈折方向が不正です。');
    if(result.kind==='total_internal_reflection'&&(result.transmitted!==null||result.cosineTransmitted!==null))throw new Error('全反射に伝播屈折方向が混在しています。');
  }
  return result;
}

export function evaluateOpticsCase(runtime,input={}) {
  const source=opticsCase(input);
  // There is no alternate JS Fresnel/Snell calculation. Every result comes
  // through the shared C++ WebAssembly API, including exact critical presets.
  return {source,result:checkResult(runtime.queryDielectricInterface(source.query))};
}

function drawOptics(canvas,{source,result}) {
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('2D図を描く機能を利用できません。');
  const origin=[450,245],scale=190,project=v=>[origin[0]+v[0]*scale,origin[1]-v[1]*scale];
  ctx.clearRect(0,0,900,500);ctx.fillStyle='#0a1522';ctx.fillRect(0,0,900,500);ctx.fillStyle='#142d40';ctx.fillRect(25,245,850,230);
  ctx.strokeStyle='#a4c5dc';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(25,245);ctx.lineTo(875,245);ctx.stroke();
  ctx.font='18px system-ui';ctx.fillStyle='#afc2d5';ctx.fillText(`入射媒質 nᵢ=${number(source.query.indexIncident,2)}`,30,35);ctx.fillText(`透過媒質 nₜ=${number(source.query.indexTransmitted,2)}`,30,280);
  function arrow(start,end,color,dash=[],label='',labelPosition=null) {
    ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=3;ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(...start);ctx.lineTo(...end);ctx.stroke();ctx.setLineDash([]);
    const angle=Math.atan2(end[1]-start[1],end[0]-start[0]);
    ctx.beginPath();ctx.moveTo(...end);ctx.lineTo(end[0]-12*Math.cos(angle-0.4),end[1]-12*Math.sin(angle-0.4));ctx.lineTo(end[0]-12*Math.cos(angle+0.4),end[1]-12*Math.sin(angle+0.4));ctx.closePath();ctx.fill();
    if(label){const p=labelPosition??[end[0]+12,end[1]+5];ctx.fillText(label,...p);}
  }
  const incoming=project(result.incidentUnit.map(v=>-v)),reflection=project(result.reflected);
  arrow(incoming,origin,'#7ee1d1',[],'入射',[Math.max(90,incoming[0]-65),Math.max(60,incoming[1]-14)]);
  arrow(origin,reflection,result.kind==='uncertain'?'#bdc5d1':'#ffbf75',[7,5],result.kind==='uncertain'?'反射方向（近似診断）':'反射',[Math.min(675,reflection[0]+14),Math.max(65,reflection[1]-14)]);
  const normalStart=[origin[0]+25,origin[1]],normalEnd=[normalStart[0]+result.normalUnit[0]*115,normalStart[1]-result.normalUnit[1]*115];
  arrow(normalStart,normalEnd,'#899fb4',[3,5],'法線 n',[normalEnd[0]+12,normalEnd[1]]);
  if(result.transmitted) {
    const transmitted=project(result.transmitted);arrow(origin,transmitted,'#8bc7ff',[],'屈折',[Math.min(750,transmitted[0]+14),Math.min(448,transmitted[1]+18)]);
  }
  const angle=Math.atan2(result.incidentUnit[0],-result.incidentUnit[1]);
  ctx.strokeStyle='#7ee1d1';ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(...origin,50,-Math.PI/2,-Math.PI/2-angle,true);ctx.stroke();
  ctx.fillStyle='#7ee1d1';ctx.font='16px system-ui';ctx.fillText('θᵢ',origin[0]-35,origin[1]-62);
  ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(...origin,4,0,Math.PI*2);ctx.fill();
  ctx.font='18px system-ui';ctx.fillStyle='#e6edf5';ctx.fillText(kinds[result.kind],30,320);
  if(result.kind==='uncertain') {ctx.fillStyle='#ffbf75';ctx.fillText('屈折・パワーは未確定',30,355);ctx.font='15px system-ui';ctx.fillText('0%や透過成功に置き換えません',30,385);}
  if(result.kind==='total_internal_reflection'){ctx.fillStyle='#afc2d5';ctx.font='16px system-ui';ctx.fillText('伝播する透過光なし',30,355);}
  ctx.fillStyle='#afc2d5';ctx.font='15px system-ui';ctx.fillText('方向のみ / 色は光路の識別 / 法線は平行移動して表示',30,480);
  canvas.setAttribute('aria-label',`単一の平面界面。${kinds[result.kind]}。反射方向${vectorText(result.reflected)}。${result.transmitted?`屈折方向${vectorText(result.transmitted)}`:'伝播屈折方向の表示なし'}。${result.power?`無偏光反射${percent(result.power.reflectanceUnpolarized)}、透過${percent(result.power.transmittanceUnpolarized)}`:'パワー未確定'}。`);
}

export async function initializeOpticsLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();}}={}) {
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false,incidentOverride=null;
  function read() {return {...Object.fromEntries(Object.entries(controls).map(([name,[id]])=>[name,get(id).value])),incidentOverride};}
  function clear() {
    state=null;for(const id of resultIds)get(id).textContent='—';
    try{const canvas=get('optics-view');canvas.getContext('2d')?.clearRect(0,0,canvas.width,canvas.height);canvas.setAttribute('aria-label','現在は有効な計算結果を表示していません。');}catch{}
  }
  function showError(error) {
    clear();get('optics-error').hidden=false;get('optics-error').textContent=`照会できません: ${error.message}`;
    get('optics-status').textContent='計算結果はありません。条件を戻すか、計算核の読込みを再試行してください。';
    get('result-explanation').textContent='不明な屈折・パワーを0%や透過成功として表示しません。';
    get('optics-json').textContent=JSON.stringify({error:error.message,controls:read()},null,2);
  }
  function recalculate() {
    if(!runtime)return null;
    try {
      const next=evaluateOpticsCase(runtime,read()),{source,result}=next;drawOptics(get('optics-view'),next);
      get('angle-value').textContent=`${number(source.parameters.angleDegrees,5)}°`;
      for(const id of ['index-incident','index-transmitted'])get(`${id}-value`).textContent=number(source.query[id==='index-incident'?'indexIncident':'indexTransmitted'],2);
      get('wavelength-value').textContent=`${number(source.parameters.wavelengthNm,0)} nm`;
      get('result-kind').textContent=`${kinds[result.kind]} (${result.kind})`;
      get('result-cosines').textContent=`${number(result.cosineIncident,8)} / ${result.cosineTransmitted===null?'—':number(result.cosineTransmitted,8)}`;
      get('result-reflected').textContent=vectorText(result.reflected);
      get('result-transmitted').textContent=result.transmitted?vectorText(result.transmitted):result.kind==='uncertain'?'—（未確定）':'伝播する透過光なし';
      get('result-discriminant').textContent=rangeText(result.discriminant);get('result-dot').textContent=rangeText(result.incidentDot);
      for(const [key,id]of Object.entries(powerFields))get(id).textContent=result.power===null?'—':percent(result.power[key]);
      get('result-explanation').textContent=result.kind==='uncertain'?`${reasons[result.uncertainty]}。屈折方向とR/Tは空の結果です。未確定を0%に置き換えません。`:result.kind==='total_internal_reflection'?'Dの上限が負で、全反射を確定しました。s/pともR=100%、T=0%。透過側の伝播光線や全反射の位相差は出力しません。':source.query.indexIncident===source.query.indexTransmitted?'屈折率が厳密に等しい入力です。界面のない解析的な特例としてR=0%、T=100%、方向不変を返します。':'Dの下限が正で、透過可能と確定しました。方向・パワー自体は通常doubleの近似値です。';
      get('input-source').textContent=source.incidentSource==='exact-critical-vector'?'原ベクトル(3, −4, 0)を保持中。表示角度は参考値です。屈折率・波長を動かしても保持し、次の角度編集で通常のsin/cos入力へ戻ります。':'角度をJavaScriptのsin/cosでdoubleの入射ベクトルへ変換しました。変換前の角度誤差までの包含ではありません。';
      get('wavelength-metres').textContent=`指定波長 ${number(source.parameters.wavelengthNm,0)} nm → ${source.query.vacuumWavelength.toExponential(9)} m。nや色の自動変更なし（分散モデル未導入）。`;
      get('optics-error').hidden=true;get('optics-status').textContent='実C++ WebAssemblyへ単一界面を照会しました。';
      get('optics-json').textContent=JSON.stringify({model:'single lossless isotropic planar interface; equal permeability; approximate directions and power',inputSource:source.incidentSource,controls:source.parameters,input:source.query,result,diagnostics:runtime.diagnostics},null,2);
      state=next;return next;
    }catch(error){showError(error);return null;}
  }
  async function retry() {
    if(busy)return null;busy=true;runtime=null;clear();get('optics-retry').disabled=true;get('optics-controls').disabled=true;get('optics-error').hidden=true;get('optics-status').textContent='C++ WebAssemblyを読込み中…';
    try {
      const loaded=await loadRuntime();if(typeof loaded?.queryDielectricInterface!=='function')throw new Error('この計算核は単一界面光学の照会APIを提供していません。');
      runtime=loaded;get('optics-controls').disabled=false;
      get('runtime-info').textContent=`計算: ${runtime.diagnostics?.backend??'—'} / ${runtime.diagnostics?.compiler??'compiler情報なし'} / ${runtime.diagnostics?.wasmBytes??'—'} bytes / build ${runtime.diagnostics?.buildId??'—'}`;
      return recalculate();
    }catch(error){runtime=null;showError(error);return null;}finally{busy=false;get('optics-retry').disabled=false;}
  }
  get('angle').addEventListener('input',()=>{incidentOverride=null;recalculate();});
  for(const id of ['index-incident','index-transmitted','wavelength'])get(id).addEventListener('input',recalculate);
  function preset(name) {
    const p=opticsPreset(name);incidentOverride=p.incidentOverride;
    for(const [key,[id]]of Object.entries(controls))get(id).value=String(p[key]);
    return recalculate();
  }
  for(const name of ['normal','brewster','tir','equal','critical'])get(`preset-${name}`).addEventListener('click',()=>preset(name));
  get('optics-retry').addEventListener('click',retry);
  await retry();return {recalculate,retry,getState:()=>state};
}

if(typeof document!=='undefined')initializeOpticsLab();
