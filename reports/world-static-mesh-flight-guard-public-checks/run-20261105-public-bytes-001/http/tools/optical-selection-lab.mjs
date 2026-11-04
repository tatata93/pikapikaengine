import {loadSimulationRuntime} from '../engine/simulation.mjs';

export const SELECTION_DEFAULTS=Object.freeze({preset:'front',originX:0,originXHalfWidth:0,originZ:-1,originZHalfWidth:0,directionScale:1,
  minimumParameter:0,maximumParameter:10,maximumQueries:512,maxSqrtRefinements:128,maximumTotalSqrtRefinements:16384,allowPrefixExclusion:true});
export const SELECTION_PRESETS=Object.freeze({
  front:{label:'前後の円盤',values:{}},partial:{label:'手前の開口に一部だけ当たる',values:{originX:.5,originXHalfWidth:.1}},
  simultaneous:{label:'同じ位置の二つの面',values:{}},order:{label:'共有原点でもtの箱が重なる',values:{originZ:-1.5,originZHalfWidth:.5}},
  prefix:{label:'奥の不確定面を閉prefixで除外',values:{originX:.5,originXHalfWidth:.1}},
  self:{label:'原点にある面：t=0も含める',values:{originZ:0}},cutoff:{label:'同じ原点：tMin=.01で領域を限定',values:{originZ:0,minimumParameter:.01}},
  sphere:{label:'球全体と頂点側capの比較',values:{originZ:3}},cap:{label:'capを通過して奥の円盤へ',values:{originZ:3}}
});
const parse=(value,label)=>{if(typeof value==='string'&&!value.trim())throw new Error(`${label}を入力してください。`);const n=Number(value);if(!Number.isFinite(n))throw new Error(`${label}は有限の数で指定してください。`);return n;};
const box=(center,half)=>half===0?center:[center-half,center+half];
const disk=(z,apertureRadius=2)=>({kind:'disk',center:[0,0,z],normal:[0,0,-1],apertureRadius});
const cap=()=>({kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:1,apertureRadius:.6});
export function opticalSelectionCase(input={}){
  const preset=input.preset??SELECTION_DEFAULTS.preset;if(!Object.hasOwn(SELECTION_PRESETS,preset))throw new Error('未知の面比較です。');
  const p={...SELECTION_DEFAULTS,...SELECTION_PRESETS[preset].values,...input,preset};
  for(const key of ['originX','originXHalfWidth','originZ','originZHalfWidth','directionScale','minimumParameter','maximumParameter','maximumQueries','maxSqrtRefinements','maximumTotalSqrtRefinements'])p[key]=parse(p[key],key);
  if(Math.abs(p.originX)>10||Math.abs(p.originZ)>10||p.originXHalfWidth<0||p.originXHalfWidth>1||p.originZHalfWidth<0||p.originZHalfWidth>1||p.directionScale<=0||p.directionScale>10)throw new Error('原点の中心は±10m、半幅は0〜1m、方向の倍率は0より大きく10以下です。');
  if(p.minimumParameter<0||p.maximumParameter<p.minimumParameter||p.maximumParameter>1000)throw new Error('閉じたt領域は0≦tMin≦tMax≦1000mで指定します。');
  for(const [key,max]of [['maximumQueries',4096],['maxSqrtRefinements',256],['maximumTotalSqrtRefinements',1000000]])if(!Number.isInteger(p[key])||p[key]<1||p[key]>max)throw new Error('照会・平方根の予算は指定範囲内の正の整数です。');
  if(typeof p.allowPrefixExclusion!=='boolean')throw new Error('prefixの選択が不正です。');
  let surfaces=[{id:20,surface:disk(2)},{id:10,surface:disk(0)}],sign=1;
  if(preset==='partial')surfaces[1].surface.apertureRadius=.5;
  if(preset==='simultaneous')surfaces[0].surface=disk(0);
  if(preset==='order')surfaces[0].surface=disk(.25);
  if(preset==='prefix')surfaces[0].surface.apertureRadius=.5;
  if(preset==='self'||preset==='cutoff')surfaces[0].surface=disk(1);
  if(preset==='sphere'){sign=-1;surfaces=[{id:20,surface:cap()},{id:10,surface:{kind:'sphere',center:[0,0,1],radius:1}}];}
  if(preset==='cap'){sign=-1;surfaces=[{id:20,surface:disk(-1)},{id:10,surface:cap()}];}
  return {parameters:p,ray:{origin:[box(p.originX,p.originXHalfWidth),0,box(p.originZ,p.originZHalfWidth)],direction:[0,0,sign*p.directionScale],minimumParameter:p.minimumParameter,maximumParameter:p.maximumParameter},records:surfaces,
    settings:{maximumParameterWidth:1e6,maxSqrtRefinements:p.maxSqrtRefinements,maximumSurfaces:128,maximumQueries:p.maximumQueries,maximumTotalSqrtRefinements:p.maximumTotalSqrtRefinements,allowPrefixExclusion:p.allowPrefixExclusion}};
}
const statuses=['hit','miss','unresolved','invalid_input','budget_exceeded','numerical_failure'];
const interval=x=>Array.isArray(x)&&x.length===2&&x.every(Number.isFinite)&&x[0]<=x[1];
const vectorBounds=x=>Array.isArray(x)&&x.length===3&&x.every(interval);
function checked(result,source){
  if(!result||!statuses.includes(result.status)||!Array.isArray(result.surfaces))throw new Error('計算核の面選択結果が不正です。');
  for(const key of ['geometryQueries','prefixQueries','sqrtRefinements'])if(!Number.isInteger(result[key])||result[key]<0)throw new Error('計算核の面選択counterが不正です。');
  const ids=new Set(source.records.map(r=>r.id)),seen=new Set();
  for(const s of result.surfaces){if(!ids.has(s.id)||seen.has(s.id))throw new Error('計算核の面IDが不正です。');seen.add(s.id);
    for(const g of [s.geometry,s.prefix])if(g&&(!['hit','miss','unresolved'].includes(g.status)||(g.status==='hit'&&!interval(g.hit?.parameter))))throw new Error('計算核の個別面結果が不正です。');
    if(s.excludedByPrefix&&s.prefix?.status!=='miss')throw new Error('prefixによる除外にmissの根拠がありません。');
  }
  if(result.status==='hit'){
    const n=result.nearest,h=n?.hit;
    if(!ids.has(n?.id)||!interval(h?.parameter)||!interval(h?.physicalDistance)||!vectorBounds(h?.position)||!vectorBounds(h?.geometricNormal)||!vectorBounds(h?.incidentNormal)||typeof h?.frontFace!=='boolean')throw new Error('計算核の最近傍区間が不正です。');
  }else if(result.nearest!==null)throw new Error('未確定の面選択に最近傍を設定できません。');
  if(['hit','miss'].includes(result.status)&&(result.surfaces.length!==source.records.length||result.surfaces.some(s=>!s.geometry)))throw new Error('未照会の面があるのに選択が成功しています。');
  return result;
}
export function evaluateOpticalSelectionCase(runtime,input={}){
  const source=opticalSelectionCase(input);
  if(typeof runtime?.queryNearestOpticalSurface!=='function')throw new Error('この計算核は最近傍面の照会に未対応です。配信版をそろえて再読込してください。');
  try{return {source,result:checked(runtime.queryNearestOpticalSurface(source.ray,source.records,source.settings),source)};}
  catch(e){if(/Optical selection WASM API unavailable/.test(e.message)||(e instanceof TypeError&&/function|undefined/.test(e.message)))throw new Error('同梱WASMに最近傍照会APIがありません。配信版をそろえて計算核を再読込してください。');throw e;}
}
const midpoint=x=>Array.isArray(x)?x[0]/2+x[1]/2:x; // display only, never a kernel input
const range=x=>x?`[${x[0].toPrecision(17)}, ${x[1].toPrecision(17)}]`:'—';
function draw(canvas,state){
  const c=canvas.getContext('2d');if(!c)return;const w=canvas.width,h=canvas.height;c.clearRect(0,0,w,h);c.fillStyle='#091521';c.fillRect(0,0,w,h);c.font='15px system-ui';c.fillStyle='#afc2d5';if(!state){c.fillText('選択結果なし',24,35);return;}
  const {source,result}=state,p=source.parameters,anchors=source.records.map(r=>r.surface.vertex??r.surface.center);
  const zlo=Math.min(p.originZ-p.originZHalfWidth,...anchors.map(a=>a[2]-1))-.3,zhi=Math.max(p.originZ+p.originZHalfWidth,...anchors.map(a=>a[2]+1))+.3;
  const xspan=Math.max(1.2,Math.abs(p.originX)+p.originXHalfWidth+.3),pz=z=>55+(z-zlo)/(zhi-zlo)*(w-85),px=x=>h/2-x/xspan*(h-100)/2;
  c.strokeStyle='#405a72';c.setLineDash([4,5]);c.beginPath();c.moveTo(pz(zlo),px(0));c.lineTo(pz(zhi),px(0));c.stroke();c.setLineDash([]);
  for(const r of source.records){const s=r.surface,selected=result.status==='hit'&&result.nearest.id===r.id;c.strokeStyle=selected?'#7ee1d1':'#91a4b6';c.lineWidth=selected?4:2;c.beginPath();
    if(s.kind==='disk'){const a=Math.min(s.apertureRadius,xspan);c.moveTo(pz(s.center[2]),px(s.center[0]-a));c.lineTo(pz(s.center[2]),px(s.center[0]+a));}
    if(s.kind==='sphere')c.ellipse(pz(s.center[2]),px(s.center[0]),s.radius/(zhi-zlo)*(w-85),s.radius/xspan*(h-100)/2,0,0,2*Math.PI);
    if(s.kind==='cap')for(let j=0;j<=64;++j){const x=-s.apertureRadius+2*s.apertureRadius*j/64,z=s.vertex[2]+s.signedRadius-Math.sign(s.signedRadius)*Math.sqrt(s.signedRadius*s.signedRadius-x*x);if(j===0)c.moveTo(pz(z),px(x));else c.lineTo(pz(z),px(x));}
    c.stroke();const a=s.vertex??s.center;c.fillStyle=selected?'#7ee1d1':'#d0dae5';c.fillText(`#${r.id} ${s.kind}`,pz(a[2])+8,px(Math.min(xspan-.2,.8))+r.id/10*18);
  }
  const oz=midpoint(source.ray.origin[2]),ox=midpoint(source.ray.origin[0]);c.strokeStyle='#ffbf75';c.strokeRect(pz(p.originZ-p.originZHalfWidth)-3,px(p.originX+p.originXHalfWidth)-3,Math.max(6,2*p.originZHalfWidth/(zhi-zlo)*(w-85)),Math.max(6,2*p.originXHalfWidth/xspan*(h-100)/2));
  c.fillStyle='#ffbf75';c.beginPath();c.arc(pz(oz),px(ox),4,0,2*Math.PI);c.fill();
  if(result.status==='hit'){
    const b=result.nearest.hit.position;c.strokeStyle='#7ee1d1';c.lineWidth=2;c.beginPath();c.moveTo(pz(oz),px(ox));c.lineTo(pz(midpoint(b[2])),px(midpoint(b[0])));c.stroke();
    c.strokeRect(pz(b[2][0])-3,px(b[0][1])-3,Math.max(6,(b[2][1]-b[2][0])/(zhi-zlo)*(w-85)),Math.max(6,(b[0][1]-b[0][0])/xspan*(h-100)/2));
  }
  c.fillStyle='#afc2d5';c.fillText('↑ X [m] / Z [m] →   Y=0断面。原点箱と位置箱は見やすく拡大する場合があります。',20,26);
  c.fillText(`入力方向 D=(0, 0, ${source.ray.direction[2]}) / 原点箱の中心 (${p.originX}, 0, ${p.originZ}) m`,20,48);
  c.fillText(result.status==='hit'?'緑: 実C++が全入力族の最近傍として選んだ面。線は区間の中心値による表示のみ。':'最近傍は描きません。不確定な面を無視して奥の面へ線を延ばしません。',20,h-20);
}
function geometryText(g){if(!g)return '未照会';const roots=g.hit?`t=${range(g.hit.parameter)}`:g.candidates?.length?g.candidates.map(c=>`${range(c.parameter)} ${c.state}`).join('\n'):'t候補なし';return `${g.status} / ${g.reason}\n${roots}`;}
export async function initializeOpticalSelectionLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime}={}){
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false;
  const fields={originX:'selection-x',originXHalfWidth:'selection-x-width',originZ:'selection-z',originZHalfWidth:'selection-z-width',directionScale:'selection-scale',minimumParameter:'selection-min',maximumParameter:'selection-max',maximumQueries:'selection-query-budget',maxSqrtRefinements:'selection-sqrt-budget',maximumTotalSqrtRefinements:'selection-total-sqrt'};
  function clear(){state=null;for(const id of ['selection-nearest','selection-counts','selection-position'])get(id).textContent='—';get('selection-table').replaceChildren();get('selection-json').textContent='結果なし';draw(get('selection-view'),null);}
  function error(e){clear();get('selection-error').hidden=false;get('selection-error').textContent=String(e.message??e);get('selection-status').textContent='照会失敗。古い選択は消去しました。';}
  const read=()=>({...Object.fromEntries(Object.entries(fields).map(([key,id])=>[key,get(id).value])),preset:get('selection-preset').value,allowPrefixExclusion:get('selection-prefix').checked});
  function render(next){state=next;get('selection-error').hidden=true;const {source,result:r}=next,n=r.nearest;
    get('selection-status').textContent=r.status==='hit'?`全入力族の一意な最近傍は面 #${n.id}。`:
      r.status==='miss'?'全ての面が指定した閉t領域でmiss。領域の外側まで見通せるという意味ではありません。':`選択なし: ${r.status}。不確定・未照会の面を無視しません。`;
    get('selection-nearest').textContent=n?`面 #${n.id} / t=${range(n.hit.parameter)} m / 実距離=${range(n.hit.physicalDistance)} m`:'—';
    get('selection-position').textContent=n?`位置包含 X=${range(n.hit.position[0])} m、Z=${range(n.hit.position[2])} m / ${n.hit.frontFace?'表側':'裏側'}からの交差`:'—';
    get('selection-counts').textContent=`総照会 ${r.geometryQueries}（うちprefix ${r.prefixQueries}）/ 平方根の細分化 ${r.sqrtRefinements}${r.refinementLimited?' / 精度予算の制限あり':''}`;
    const rows=source.records.slice().sort((a,b)=>a.id-b.id).map(record=>{
      const s=r.surfaces.find(s=>s.id===record.id);let why='採用なし・判定保留';
      if(r.status==='hit'&&n.id===record.id)why='全族の一意な最近傍';
      else if(s?.excludedByPrefix)why='閉prefix全体がmiss：それ以前を除外';
      else if(s?.geometry?.status==='miss')why='指定t領域でmiss';
      else if(r.status==='hit'&&s?.geometry?.hit&&n.hit.parameter[1]<s.geometry.hit.parameter[0])why='t包含が最近傍より厳密に後方';
      const tr=doc.createElement('tr');for(const value of [`#${record.id} ${record.surface.kind}`,geometryText(s?.geometry),geometryText(s?.prefix),why]){const td=doc.createElement('td');td.textContent=value;tr.appendChild(td);}return tr;
    });get('selection-table').replaceChildren(...rows);get('selection-json').textContent=JSON.stringify({...next,diagnostics:runtime.diagnostics},null,2);draw(get('selection-view'),next);return next;
  }
  function recalculate(){if(!runtime)return null;try{return render(evaluateOpticalSelectionCase(runtime,read()));}catch(e){error(e);return null;}}
  function preset(name){if(!Object.hasOwn(SELECTION_PRESETS,name))throw new Error('未知の面比較です。');const p=opticalSelectionCase({preset:name}).parameters;get('selection-preset').value=name;for(const [key,id]of Object.entries(fields))get(id).value=String(p[key]);get('selection-prefix').checked=p.allowPrefixExclusion;return recalculate();}
  async function retry(){if(busy)return null;busy=true;runtime=null;clear();get('runtime-info').textContent='—';get('selection-controls').disabled=true;get('selection-retry').disabled=true;get('selection-status').textContent='計算核を読込み中…';
    try{runtime=await loadRuntime();if(typeof runtime?.queryNearestOpticalSurface!=='function')throw new Error('この計算核は最近傍面照会に未対応です。配信版をそろえて再読込してください。');get('runtime-info').textContent=`${runtime.diagnostics?.backend} / ${runtime.diagnostics?.compiler??'—'} / ${runtime.diagnostics?.wasmBytes??'—'} bytes / build ${runtime.diagnostics?.buildId??'—'}`;get('selection-controls').disabled=false;return recalculate();}
    catch(e){runtime=null;error(e);return null;}finally{busy=false;get('selection-retry').disabled=false;}
  }
  for(const id of Object.values(fields)){get(id).addEventListener('input',recalculate);get(id).addEventListener('change',recalculate);}
  get('selection-prefix').addEventListener('change',recalculate);get('selection-preset').addEventListener('change',()=>preset(get('selection-preset').value));
  get('selection-reset').addEventListener('click',()=>preset(get('selection-preset').value));get('selection-budget-restore').addEventListener('click',()=>{get('selection-query-budget').value='512';return recalculate();});get('selection-retry').addEventListener('click',retry);
  await retry();return {retry,recalculate,preset,getState:()=>state};
}
if(typeof document!=='undefined')initializeOpticalSelectionLab();
