export const SURFACE_DEFAULTS=Object.freeze({kind:'cap',originZ:-3,originX:0,angleDegrees:0,directionScale:1,radius:2,aperture:1,minimumParameter:0,maximumParameter:10});
const fields={originZ:['origin-z',-6,6,' m'],originX:['origin-x',-3,3,' m'],angleDegrees:['ray-angle',-180,180,'°'],directionScale:['direction-scale',.25,4,''],radius:['radius',-3,3,' m'],aperture:['aperture',.1,3,' m'],minimumParameter:['parameter-min',0,8,' m'],maximumParameter:['parameter-max',0,16,' m']};
const statuses={hit:'交差あり',miss:'指定範囲では交差なし',unresolved:'未確定'};
const reasons={none:'なし',no_real_roots:'実根なし',parallel:'平行で別の平面',filtered_roots:'候補を範囲・面・開口で除外',parallel_or_coplanar:'平行または同一平面で確定できない',tangent_or_discriminant:'接線付近の符号が未確定',parameter_boundary:'t範囲の境界が未確定',aperture_boundary:'開口の境界が未確定',cap_boundary:'頂点側半球の境界が未確定',orientation:'面の向きが未確定',precision_limit:'根区間の幅を十分に狭められない',refinement_budget:'平方根の精錬上限',numerical_output:'概算値を成立させられない'};
const candidateStates={not_examined:'未調査',accepted:'採用',rejected_parameter:'t範囲外',rejected_aperture:'開口の外',rejected_cap:'頂点側半球の外',unresolved:'未確定'};
const resultIds=['result-status','result-reason','result-parameter','result-distance','result-position','result-estimate','result-normals','result-discriminant','candidate-0-range','candidate-0-state','candidate-1-range','candidate-1-state'];
const number=n=>n.toLocaleString('ja-JP',{maximumFractionDigits:6});
const intervalText=a=>'['+a.map(n=>n===0?'0':n.toPrecision(17)).join(', ')+']';
const vectorText=a=>'('+a.map(number).join(', ')+')';
const range=a=>Array.isArray(a)&&a.length===2&&a.every(Number.isFinite)&&a[0]<=a[1];
const vector=a=>Array.isArray(a)&&a.length===3&&a.every(Number.isFinite);
// Presets on an exact coordinate axis retain zero transverse components:
// sin(pi) is not zero in JS. General angle controls use ordinary sin/cos.
function direction(angle,scale) {
  if(angle===0)return [0,0,scale];
  if(Math.abs(angle)===180)return [0,0,-scale];
  if(Math.abs(angle)===90)return [Math.sign(angle)*scale,0,0];
  const radians=angle*Math.PI/180;return [Math.sin(radians)*scale,0,Math.cos(radians)*scale];
}
export function surfacePreset(name) {
  const p={...SURFACE_DEFAULTS};
  if(name==='front')return p;
  if(name==='back')return {...p,originZ:5,angleDegrees:180};
  if(name==='tangent')return {...p,kind:'sphere',originX:2};
  if(name==='aperture')return {...p,kind:'disk',originX:1};
  if(name==='self')return {...p,kind:'sphere',originZ:0};
  if(name==='cutoff')return {...p,kind:'sphere',originZ:0,minimumParameter:.001};
  throw new Error('面のプリセットが不正です。');
}
export function surfaceCase(input={}) {
  const p={...SURFACE_DEFAULTS,...input};
  if(!['disk','sphere','cap'].includes(p.kind))throw new Error('面の種類が不正です。');
  for(const [key,[,lo,hi]]of Object.entries(fields)) {
    p[key]=Number(p[key]);if(!Number.isFinite(p[key])||p[key]<lo||p[key]>hi)throw new Error('操作範囲外の入力です。');
  }
  if(p.minimumParameter>p.maximumParameter)throw new Error('t開始はt終了以下にしてください。');
  if(p.kind!=='disk'&&Math.abs(p.radius)<1e-6)throw new Error('球面の半径は0にできません。');
  if(p.kind==='cap'&&p.aperture>Math.abs(p.radius))throw new Error('球面レンズの開口半径は|半径|以下にしてください。');
  const ray={origin:[p.originX,0,p.originZ],direction:direction(p.angleDegrees,p.directionScale),minimumParameter:p.minimumParameter,maximumParameter:p.maximumParameter};
  const surface=p.kind==='disk'?{kind:'disk',center:[0,0,0],normal:[0,0,1],apertureRadius:p.aperture}:p.kind==='sphere'?{kind:'sphere',center:[0,0,2],radius:Math.abs(p.radius)}:{kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:p.radius,apertureRadius:p.aperture};
  return {parameters:p,ray,surface,settings:{parameterTolerance:1e-8,maxSqrtRefinements:128}};
}
function checkResult(r) {
  if(!r||!Object.hasOwn(statuses,r.status)||!Object.hasOwn(reasons,r.reason)||!Array.isArray(r.candidates)||r.candidates.length>2||r.rootCount!==r.candidates.length||r.candidates.some(c=>!range(c.parameter)||!Object.hasOwn(candidateStates,c.state)||!Object.hasOwn(reasons,c.reason))||(r.discriminant!==null&&!range(r.discriminant)))throw new Error('計算核の面交差結果が不正です。');
  if(r.status==='hit') {
    const h=r.hit;if(!h||!range(h.parameter)||!range(h.physicalDistance)||![h.position,h.geometricNormal,h.incidentNormal].every(a=>Array.isArray(a)&&a.length===3&&a.every(range))||!vector(h.positionEstimate)||!vector(h.geometricNormalEstimate)||!vector(h.incidentNormalEstimate)||!Number.isFinite(h.parameterEstimate)||!Number.isFinite(h.physicalDistanceEstimate))throw new Error('計算核の交差点結果が不正です。');
  } else if(r.hit!==null)throw new Error('未確定・交差なしに交差成功値が混在しています。');
  return r;
}
export function evaluateSurfaceCase(runtime,input={}) {
  const source=surfaceCase(input);
  // Only the shared C++ WASM performs intersection/classification.
  return {source,result:checkResult(runtime.queryOpticalSurface(source.ray,source.surface,source.settings))};
}
function drawSurface(canvas,{source,result}) {
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('2D図を描く機能を利用できません。');
  const {ray,surface}=source;
  const at=t=>ray.origin.map((v,i)=>v+t*ray.direction[i]);
  const points=[ray.origin,at(ray.minimumParameter),at(ray.maximumParameter),[0,0,0],[0,0,2]];
  const R=surface.kind==='disk'?surface.apertureRadius:Math.abs(surface.kind==='cap'?surface.signedRadius:surface.radius);
  const center=surface.kind==='cap'?[0,0,surface.signedRadius]:surface.kind==='sphere'?surface.center:surface.center;
  points.push([R,0,center[2]-R],[-R,0,center[2]+R]);
  const xs=points.map(p=>p[0]),zs=points.map(p=>p[2]);
  const minX=Math.min(-1,...xs)-.5,maxX=Math.max(1,...xs)+.5,minZ=Math.min(-1,...zs)-.5,maxZ=Math.max(1,...zs)+.5;
  const scale=Math.min(790/(maxZ-minZ),360/(maxX-minX));
  const project=p=>[450+(p[2]-(minZ+maxZ)/2)*scale,255-(p[0]-(minX+maxX)/2)*scale];
  ctx.clearRect(0,0,900,500);ctx.fillStyle='#0a1522';ctx.fillRect(0,0,900,500);ctx.font='17px system-ui';ctx.fillStyle='#afc2d5';ctx.fillText('XZ断面 / 横 +Z、上 +X [m] / 曲線・点は表示用近似',25,28);
  function line(a,b,color,width=2,dash=[]) {ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(...project(a));ctx.lineTo(...project(b));ctx.stroke();ctx.setLineDash([]);}
  function marker(p,color,r=5) {ctx.fillStyle=color;ctx.beginPath();ctx.arc(...project(p),r,0,Math.PI*2);ctx.fill();}
  line([0,0,minZ],[0,0,maxZ],'#253f52',1);line([minX,0,0],[maxX,0,0],'#253f52',1);
  if(surface.kind==='disk')line([-R,0,0],[R,0,0],'#70bfff',5);
  else {
    ctx.strokeStyle='#526f87';ctx.lineWidth=2;ctx.setLineDash(surface.kind==='cap'?[6,5]:[]);ctx.beginPath();ctx.arc(...project(center),R*scale,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);
    if(surface.kind==='cap') {
      // This sampling only draws the authored cap, never determines a hit.
      ctx.strokeStyle='#70bfff';ctx.lineWidth=5;ctx.beginPath();
      const sign=Math.sign(surface.signedRadius),angle=Math.asin(surface.apertureRadius/R);
      for(let k=0;k<=80;k++){const theta=-angle+2*angle*k/80,p=[R*Math.sin(theta),0,center[2]-sign*R*Math.cos(theta)],q=project(p);if(k===0)ctx.moveTo(...q);else ctx.lineTo(...q);}
      ctx.stroke();
      line([-surface.apertureRadius,0,0],[surface.apertureRadius,0,0],'#70bfff',1,[2,5]);
    }
  }
  line(ray.origin,at(ray.maximumParameter),'#3a736c',1,[5,5]);line(at(ray.minimumParameter),at(ray.maximumParameter),'#66d8c1',3);
  marker(ray.origin,'#66d8c1',6);ctx.fillStyle='#66d8c1';const o=project(ray.origin);ctx.fillText('原点O',o[0]+9,o[1]-12);
  result.candidates.forEach((c,i)=>{const mid=c.parameter[0]+(c.parameter[1]-c.parameter[0])/2,p=at(mid);marker(p,'#e2edf6',4);const q=project(p);ctx.fillStyle='#e2edf6';ctx.fillText('候補'+(i+1),q[0]+8,q[1]+(i===0?-14:24));});
  if(result.hit) {
    const h=result.hit,p=project(h.positionEstimate);marker(h.positionEstimate,'#ffad66',7);
    const a=project([h.position[0][0],0,h.position[2][0]]),b=project([h.position[0][1],0,h.position[2][1]]);
    const width=Math.max(6,Math.abs(b[0]-a[0])),height=Math.max(6,Math.abs(b[1]-a[1]));
    ctx.strokeStyle='#ffad66';ctx.lineWidth=2;ctx.strokeRect((a[0]+b[0]-width)/2,(a[1]+b[1]-height)/2,width,height);
    const endpoint=h.positionEstimate.map((v,i)=>v+.6*h.geometricNormalEstimate[i]);line(h.positionEstimate,endpoint,'#ffad66',2);
    ctx.fillStyle='#ffad66';ctx.fillText('採用（概算点）',p[0]+9,p[1]+45);
  }
  ctx.fillStyle='#afc2d5';ctx.fillText('原点からの軌道は破線 / 調べるt範囲は実線 / 位置区間の枠は最小6px',25,473);
  canvas.setAttribute('aria-label','XZ断面。'+statuses[result.status]+'。'+reasons[result.reason]+(result.hit?'。t区間'+intervalText(result.hit.parameter)+' m、物理距離区間'+intervalText(result.hit.physicalDistance)+' m。':'。確定した交差点を表示していません。'));
}
export async function initializeSurfaceLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();}}={}) {
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false;
  const read=()=>({kind:get('surface-kind').value,...Object.fromEntries(Object.entries(fields).map(([key,[id]])=>[key,get(id).value]))});
  function clear() {state=null;for(const id of resultIds)get(id).textContent='—';try{const canvas=get('surface-view');canvas.getContext('2d')?.clearRect(0,0,canvas.width,canvas.height);canvas.setAttribute('aria-label','現在は有効な交差結果を表示していません。');}catch{}}
  function fail(error) {clear();get('surface-error').hidden=false;get('surface-error').textContent='照会できません: '+error.message;get('surface-status').textContent='結果はありません。条件を戻すか読込みを再試行してください。';get('result-explanation').textContent='未確定やエラーを「当たらない」へ置き換えません。';get('surface-domain').textContent='—';get('surface-json').textContent=JSON.stringify({error:error.message,controls:read()},null,2);}
  function recalculate() {
    if(!runtime)return null;
    try {
      const next=evaluateSurfaceCase(runtime,read()),{source,result:r}=next;drawSurface(get('surface-view'),next);
      for(const [key,[id]]of Object.entries(fields))get(id+'-value').textContent=number(source.parameters[key])+fields[key][3];
      get('result-status').textContent=statuses[r.status]+' ('+r.status+')';get('result-reason').textContent=reasons[r.reason];
      get('result-discriminant').textContent=r.discriminant===null?'平面では未使用':intervalText(r.discriminant);
      if(r.hit){const h=r.hit;get('result-parameter').textContent=intervalText(h.parameter);get('result-distance').textContent=intervalText(h.physicalDistance);get('result-position').textContent=h.position.map((a,i)=>['X','Y','Z'][i]+': '+intervalText(a)).join('\n');get('result-estimate').textContent=vectorText(h.positionEstimate);get('result-normals').textContent=vectorText(h.geometricNormalEstimate)+' / '+vectorText(h.incidentNormalEstimate)+(h.frontFace?'（表側）':'（裏側）');}
      else for(const id of ['result-parameter','result-distance','result-position','result-estimate','result-normals'])get(id).textContent='—';
      for(let i=0;i<2;i++){const c=r.candidates[i];get('candidate-'+i+'-range').textContent=c?intervalText(c.parameter):'—';get('candidate-'+i+'-state').textContent=c?candidateStates[c.state]+(c.reason==='none'?'':' / '+reasons[c.reason]):'—';}
      get('result-explanation').textContent=r.status==='unresolved'?'判定を確定できません。近い候補が未確定なら後の候補を採用せず、交差点は空の結果です。「交差なし」には置き換えません。':r.status==='miss'?'指定した面と閉区間[t開始,t終了]では有効な交差がありません。範囲外や別の面まで含めた全光路の不在は主張しません。':'最初の有効な交差を区間で囲みました。図の点・法線は通常doubleの概算です。原入力の包含区間と区別してください。';
      get('surface-domain').textContent='調べるt: ['+number(source.ray.minimumParameter)+', '+number(source.ray.maximumParameter)+'] m / |d|の表示用近似: '+number(Math.hypot(...source.ray.direction))+' / 平方根精錬 '+r.sqrtRefinements+' 回'+(r.refinementLimited?'（上限に到達。結果の区間幅も確認してください）':'');
      get('surface-status').textContent='実C++ WebAssemblyへ単一面を照会しました。';get('surface-error').hidden=true;get('surface-json').textContent=JSON.stringify({model:'single authored surface; closed parameter domain; original input bounds, separate estimates',input:source,result:r,diagnostics:runtime.diagnostics},null,2);state=next;return next;
    }catch(error){fail(error);return null;}
  }
  async function retry() {
    if(busy)return null;busy=true;runtime=null;clear();get('surface-controls').disabled=true;get('surface-retry').disabled=true;get('surface-error').hidden=true;get('surface-status').textContent='C++ WebAssemblyを読込み中…';
    try{const loaded=await loadRuntime();if(typeof loaded?.queryOpticalSurface!=='function')throw new Error('この計算核は面の照会APIを提供していません。');runtime=loaded;get('surface-controls').disabled=false;get('runtime-info').textContent='計算: '+(runtime.diagnostics?.backend??'—')+' / '+(runtime.diagnostics?.compiler??'—')+' / '+(runtime.diagnostics?.wasmBytes??'—')+' bytes / build '+(runtime.diagnostics?.buildId??'—');return recalculate();}
    catch(error){runtime=null;fail(error);return null;}finally{busy=false;get('surface-retry').disabled=false;}
  }
  for(const [, [id]]of Object.entries(fields))get(id).addEventListener('input',recalculate);
  get('surface-kind').addEventListener('change',recalculate);
  function preset(name){const p=surfacePreset(name);get('surface-kind').value=p.kind;for(const [key,[id]]of Object.entries(fields))get(id).value=String(p[key]);return recalculate();}
  for(const name of ['front','back','tangent','aperture','self','cutoff'])get('preset-'+name).addEventListener('click',()=>preset(name));
  get('surface-retry').addEventListener('click',retry);
  await retry();return {recalculate,retry,getState:()=>state};
}
if(typeof document!=='undefined')initializeSurfaceLab();
