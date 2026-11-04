export const CONTACT_DEFAULTS=Object.freeze({mode:'spheres',gap:2,speed:1000,verticalSpeed:0,targetSpeed:0,lateral:0,horizonSeconds:1/120,preview:1});
const kinds={none:'接触なし',initial_overlap:'初期重なり',initial_touch:'初期接触',impact:'途中で接触',grazing:'接線接触',uncertain:'数値的に不確か'};
const motions={stationary:'相対静止',approaching:'接近',separating:'離反',tangential:'接線方向'};
const fields={gap:['gap',-1,8],speed:['speed',-1500,1500],verticalSpeed:['vertical-speed',-500,500],targetSpeed:['target-speed',-500,500],lateral:['lateral',-2,2]};
const format=(value,digits=3)=>Number(value).toLocaleString('ja-JP',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const vector=(value)=>Array.isArray(value)&&value.length===3&&[0,1,2].every(i=>Number.isFinite(value[i]));
const translate=(position,velocity,time)=>position.map((value,i)=>value+velocity[i]*time);

export function contactCase(input={}) {
  const parameters={...CONTACT_DEFAULTS,...input};
  if(!['spheres','plane'].includes(parameters.mode))throw new Error('相手の形状が不正です。');
  for(const [name,[,min,max]]of Object.entries(fields)){parameters[name]=Number(parameters[name]);if(!Number.isFinite(parameters[name])||parameters[name]<min||parameters[name]>max)throw new Error('位置・速度が操作範囲外です。');}
  parameters.horizonSeconds=Number(parameters.horizonSeconds);parameters.preview=Number(parameters.preview);
  if(!Number.isFinite(parameters.horizonSeconds)||parameters.horizonSeconds<0||parameters.horizonSeconds>0.02000000000001)throw new Error('照会区間は0〜20msで指定してください。');
  if(!Number.isFinite(parameters.preview)||parameters.preview<0||parameters.preview>1)throw new Error('図示時刻が範囲外です。');
  const a={position:[-(parameters.gap+(parameters.mode==='spheres'?1:0.5)),parameters.lateral,0],velocity:[parameters.speed,parameters.verticalSpeed,0],radius:0.5};
  const b={position:[0,0,0],velocity:[parameters.targetSpeed,0,0],radius:0.5};
  const plane={normal:[-1,0,0],offset:0,velocity:[parameters.targetSpeed,0,0]};
  return {parameters,a,b,plane,horizonSeconds:parameters.horizonSeconds};
}

export function contactPose(source,time) {
  return {a:{...source.a,position:translate(source.a.position,source.a.velocity,time)},b:{...source.b,position:translate(source.b.position,source.b.velocity,time)},
    plane:{...source.plane,offset:source.plane.offset+source.plane.normal.reduce((sum,value,i)=>sum+value*source.plane.velocity[i]*time,0)}};
}

function checkResult(result) {
  if(!result||!Object.hasOwn(kinds,result.kind)||!Object.hasOwn(motions,result.initialMotion)||!vector(result.normal)||!Number.isFinite(result.initialGap))throw new Error('計算核の接触結果が不正です。');
  if(result.time!==null&&(!Number.isFinite(result.time)||result.time<0))throw new Error('計算核が不正な時刻を返しました。');
  return result;
}

export function evaluateContactCase(runtime,input={}) {
  const source=contactCase(input),end=contactPose(source,source.horizonSeconds);
  const query=(pose,horizon)=>source.parameters.mode==='spheres'?runtime.querySphereSphere(pose.a,pose.b,horizon):runtime.querySpherePlane(pose.a,pose.plane,horizon);
  // Both the interval result and endpoint-only classification use the real API.
  const result=checkResult(query(source,source.horizonSeconds)),endpoint=checkResult(query(end,0));
  return {source,result,endpoint};
}

function drawContact(canvas,state) {
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('2D図を描く機能を利用できません。');
  const {source,result}=state,mode=source.parameters.mode,initial=contactPose(source,0),end=contactPose(source,source.horizonSeconds),previewTime=source.horizonSeconds*source.parameters.preview,preview=contactPose(source,previewTime),hit=result.time===null?null:contactPose(source,result.time);
  const positions=[initial.a.position,end.a.position,preview.a.position,...(mode==='spheres'?[initial.b.position,end.b.position,preview.b.position]:[[0,0,0],[source.plane.velocity[0]*source.horizonSeconds,0,0]]),...(hit?[hit.a.position]:[])];
  const minX=Math.min(...positions.map(p=>p[0]))-1,maxX=Math.max(...positions.map(p=>p[0]))+1,minY=Math.min(-1,...positions.map(p=>p[1]))-1,maxY=Math.max(1,...positions.map(p=>p[1]))+1;
  const scale=Math.min(760/(maxX-minX),280/(maxY-minY)),centerX=(minX+maxX)/2,centerY=(minY+maxY)/2,project=p=>[450+(p[0]-centerX)*scale,215-(p[1]-centerY)*scale];
  ctx.clearRect(0,0,900,440);ctx.fillStyle='#0a1522';ctx.fillRect(0,0,900,440);ctx.font='15px system-ui';ctx.lineWidth=1;
  const y0=project([0,0,0])[1];ctx.strokeStyle='#30485c';ctx.beginPath();ctx.moveTo(45,y0);ctx.lineTo(855,y0);ctx.stroke();
  ctx.fillStyle='#adc2d3';ctx.fillText('指定した一定速度の軌道（応答なし）',30,30);ctx.fillText(`図示 t=${format(previewTime*1000)} ms`,640,30);
  function circle(sphere,color,dash=[],fill=false,label=''){
    const p=project(sphere.position);ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=2;ctx.setLineDash(dash);ctx.beginPath();ctx.arc(p[0],p[1],sphere.radius*scale,0,Math.PI*2);if(fill){ctx.globalAlpha=0.3;ctx.fill();ctx.globalAlpha=1;}ctx.stroke();ctx.setLineDash([]);if(label){ctx.fillStyle=color;ctx.fillText(label,p[0]-18,p[1]-sphere.radius*scale-10);}
  }
  function line(a,b,color,dash=[]){ctx.strokeStyle=color;ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(...project(a));ctx.lineTo(...project(b));ctx.stroke();ctx.setLineDash([]);}
  if(mode==='plane') {
    const x=preview.plane.offset/preview.plane.normal[0],px=project([x,0,0])[0];ctx.fillStyle='#382b28';ctx.fillRect(px,65,Math.max(0,870-px),290);
    for(const [plane,color,dash]of [[initial.plane,'#72859b',[4,5]],[end.plane,'#a1836c',[2,5]],[preview.plane,'#ffbf75',[]]]){const pp=project([plane.offset/plane.normal[0],0,0])[0];ctx.strokeStyle=color;ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(pp,65);ctx.lineTo(pp,355);ctx.stroke();ctx.setLineDash([]);}
    ctx.fillStyle='#ffbf75';ctx.fillText('固体側 →',Math.min(780,px+12),90);
  }
  line(initial.a.position,end.a.position,'#2f657a',[5,5]);circle(initial.a,'#728fa4',[5,4],false,'A 開始');circle(end.a,'#728fa4',[2,4],false,'A 終点');
  if(mode==='spheres'){line(initial.b.position,end.b.position,'#876944',[5,5]);circle(initial.b,'#a48e75',[5,4]);circle(end.b,'#a48e75',[2,4]);circle(preview.b,'#ffbf75',[],true,'B');}
  circle(preview.a,'#7ee1d1',[],true,'A');
  if(hit) {
    circle(hit.a,'#fff',[7,3]);if(mode==='spheres')circle(hit.b,'#fff',[7,3]);
    const contact=hit.a.position.map((value,i)=>value+(mode==='spheres'?1:-1)*result.normal[i]*source.a.radius);
    if(result.normalValid&&['impact','grazing','initial_touch'].includes(result.kind)){
      const p=project(contact);ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(...p,4,0,Math.PI*2);ctx.fill();
      const n=[result.normal[0],-result.normal[1]],tip=[p[0]+n[0]*48,p[1]+n[1]*48],angle=Math.atan2(n[1],n[0]);
      ctx.strokeStyle='#fff';ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...tip);ctx.stroke();ctx.beginPath();ctx.moveTo(...tip);ctx.lineTo(tip[0]-9*Math.cos(angle-0.4),tip[1]-9*Math.sin(angle-0.4));ctx.lineTo(tip[0]-9*Math.cos(angle+0.4),tip[1]-9*Math.sin(angle+0.4));ctx.closePath();ctx.fill();
    }
    const label=project(hit.a.position);ctx.fillStyle='#fff';ctx.fillText(`${result.kind==='uncertain'?'候補':'照会'} t=${format(result.time*1000)} ms`,Math.max(45,Math.min(680,label[0]-30)),Math.max(65,label[1]+0.5*scale+27));
  }
  ctx.fillStyle='#adc2d3';ctx.fillText(`X ${format(minX,1)} … ${format(maxX,1)} m / Y ${format(minY,1)} … ${format(maxY,1)} m`,30,397);ctx.fillText('実寸比を保って自動拡大 / 法線は向きのみ',30,422);
  canvas.setAttribute('aria-label',`${mode==='spheres'?'球同士':'球と平面'}。区間結果${kinds[result.kind]}。${result.time===null?'確定時刻なし':`時刻${format(result.time*1000)}ms`}。終点の面間隔${format(state.endpoint.initialGap,6)}m。`);
}

export async function initializeContactLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();}}={}) {
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false;
  function read(){return {mode:get('contact-mode').value,...Object.fromEntries(Object.entries(fields).map(([name,[id]])=>[name,get(id).value])),horizonSeconds:Number(get('horizon').value)/(get('horizon-unit').value==='ms'?1000:1),preview:Number(get('preview').value)/100};}
  function showError(error){state=null;get('contact-error').hidden=false;get('contact-error').textContent=`照会できません: ${error.message}`;get('contact-status').textContent='計算結果は表示していません。条件を戻すか、読込みを再試行してください。';for(const id of ['result-kind','result-time','result-gap','result-motion','result-initial-speed','result-speed','result-normal','endpoint-gap','endpoint-kind'])get(id).textContent='—';get('comparison').textContent='不明な結果を「接触なし」として扱いません。';get('roundoff').textContent='';get('contact-json').textContent='照会失敗';try{const canvas=get('contact-view');canvas.getContext('2d')?.clearRect(0,0,canvas.width,canvas.height);canvas.setAttribute('aria-label','現在の入力または計算核では照会できません。');}catch{}}
  function recalculate(){
    if(!runtime)return null;
    try{
      const input=read(),next=evaluateContactCase(runtime,input),{source,result,endpoint}=next;drawContact(get('contact-view'),next);
      for(const [name,[id]]of Object.entries(fields))get(`${id}-value`).textContent=`${format(source.parameters[name],name==='gap'||name==='lateral'?2:0)} ${name==='gap'||name==='lateral'?'m':'m/s'}`;
      const unit=get('horizon-unit').value;get('horizon-value').textContent=`${format(Number(get('horizon').value),unit==='ms'?3:6)} ${unit}`;
      get('horizon-seconds').textContent=`${format(source.horizonSeconds*1000,6)} ms = ${format(source.horizonSeconds,9)} s`;
      get('preview-value').textContent=`${format(source.parameters.preview*100,0)} %`;
      get('result-kind').textContent=`${kinds[result.kind]} (${result.kind})`;get('result-time').textContent=result.time===null?'確定時刻なし':`${format(result.time*1000,6)} ms / ${format(result.time,9)} s${result.atHorizon?'（区間端）':''}`;
      get('result-gap').textContent=format(result.initialGap,6);get('result-motion').textContent=motions[result.initialMotion];get('result-initial-speed').textContent=result.normalValid&&Number.isFinite(result.initialNormalSpeed)?format(result.initialNormalSpeed,6):'法線なし';get('result-speed').textContent=result.kind==='none'?'イベントなし':result.normalValid&&Number.isFinite(result.normalSpeed)?format(result.normalSpeed,6):'法線なし';get('result-normal').textContent=result.normalValid?`(${result.normal.map(value=>format(value,6)).join(', ')})`:'方向を定められません';
      get('endpoint-gap').textContent=format(endpoint.initialGap,6);get('endpoint-kind').textContent=kinds[endpoint.kind];
      const hit=['impact','grazing','initial_touch','initial_overlap'].includes(result.kind),endHit=['initial_overlap','initial_touch'].includes(endpoint.kind);
      get('comparison').textContent=result.kind==='uncertain'?'区間内の結果は数値的に不確かです。接触なしへ置き換えられません。':result.kind==='initial_touch'?`開始時点で接しています。相対運動は${motions[result.initialMotion]}です。初期接触と、正の時刻に初めて起こる接触を区別します。`:result.kind==='initial_overlap'?'開始時点で重なっています。返した0秒は重なりから退出する時刻ではありません。重なりの解消や衝突後応答は計算していません。':hit&&!endHit&&endpoint.kind==='none'?'終点では離れていますが、区間内で接触しています。終点だけの検査ではこの接触を見落とします。':hit?'区間内に接触があります。衝突後の応答は計算していません。':'指定した直線軌道の区間では、接触が報告されていません。';
      get('roundoff').textContent=result.roundoffSensitive?'丸めへの感度を示す診断が付いています。厳密な区間証明ではありません。':'この照会には丸め感度の診断は付いていません。一般的な精度保証を意味しません。';
      get('preview-time').textContent=`図示する軌道時刻: ${format(source.horizonSeconds*source.parameters.preview*1000,6)} ms（接触後も指定軌道を継続）`;
      get('contact-error').hidden=true;get('contact-status').textContent='実C++ WebAssemblyへ区間と終点を照会しました。';get('contact-json').textContent=JSON.stringify({model:'constant linear trajectories; no response',input:source,result,endpoint,diagnostics:runtime.diagnostics},null,2);state=next;return next;
    }catch(error){showError(error);return null;}
  }
  async function retry(){if(busy)return null;busy=true;get('contact-retry').disabled=true;get('contact-controls').disabled=true;get('contact-status').textContent='C++ WebAssemblyを読込み中…';try{const loaded=await loadRuntime();if(typeof loaded.querySphereSphere!=='function'||typeof loaded.querySpherePlane!=='function')throw new Error('この計算核は接触時刻の照会APIを提供していません。');runtime=loaded;get('contact-controls').disabled=false;get('runtime-info').textContent=`計算: ${runtime.diagnostics.backend} / ${runtime.diagnostics.compiler??'compiler情報なし'} / ${runtime.diagnostics.wasmBytes??'—'} bytes / build ${runtime.diagnostics.buildId??'—'}`;return recalculate();}catch(error){runtime=null;showError(error);return null;}finally{busy=false;get('contact-retry').disabled=false;}}
  for(const [id]of Object.values(fields))get(id).addEventListener('input',recalculate);
  for(const id of ['contact-mode','horizon','preview'])get(id).addEventListener(id==='contact-mode'?'change':'input',recalculate);
  let previousUnit='ms';get('horizon-unit').addEventListener('change',()=>{const unit=get('horizon-unit').value,seconds=Number(get('horizon').value)/(previousUnit==='ms'?1000:1);get('horizon').max=unit==='ms'?'20':'0.02';get('horizon').value=String(seconds*(unit==='ms'?1000:1));previousUnit=unit;recalculate();});
  function preset(patch){const p={...CONTACT_DEFAULTS,...patch};get('contact-mode').value=p.mode;for(const [name,[id]]of Object.entries(fields))get(id).value=String(p[name]);get('horizon-unit').value='ms';previousUnit='ms';get('horizon').max='20';get('horizon').value=String(p.horizonSeconds*1000);get('preview').value=String(p.preview*100);recalculate();}
  get('preset-fast').addEventListener('click',()=>preset({}));get('preset-grazing').addEventListener('click',()=>preset({lateral:1}));get('preset-touch').addEventListener('click',()=>preset({mode:get('contact-mode').value,gap:0,speed:100}));get('preset-tangent').addEventListener('click',()=>preset({mode:get('contact-mode').value,gap:0,speed:0,verticalSpeed:100}));get('preset-away').addEventListener('click',()=>preset({mode:get('contact-mode').value,gap:0,speed:-100}));get('preset-overlap').addEventListener('click',()=>preset({mode:get('contact-mode').value,gap:-0.2,speed:100}));get('contact-retry').addEventListener('click',retry);
  await retry();return {recalculate,retry,getState:()=>state};
}

if(typeof document!=='undefined')initializeContactLab();
