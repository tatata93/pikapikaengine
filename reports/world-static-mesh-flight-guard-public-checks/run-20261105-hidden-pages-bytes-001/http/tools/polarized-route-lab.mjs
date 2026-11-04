import {loadSimulationRuntime} from '../engine/simulation.mjs';
export const POLARIZED_ROUTE_PRESETS=Object.freeze({rational:'非共面二反射',plate:'正入射二透過',tir:'非共面二TIR',source_frame:'初期参照軸退化',near_normal:'垂直近傍の族',critical:'臨界',unavailable:'選択透過なし',budget:'段数予算'});
export const POLARIZED_ROUTE_DEFAULTS=Object.freeze({preset:'rational',stokes:'unpolarized',originWidth:0,directionWidth:0,indexWidth:0,maximumSteps:64,maxSqrtRefinements:128,powerMaxSqrtRefinements:128,maximumTotalSqrtRefinements:1000000});
const states={unpolarized:[1,0,0,0],q_plus:[1,1,0,0],q_minus:[1,-1,0,0],u_plus:[1,0,1,0],u_minus:[1,0,-1,0],v_plus:[1,0,0,1],v_minus:[1,0,0,-1]};
const copy=x=>JSON.parse(JSON.stringify(x));
const number=x=>Number.isFinite(x)?Number(x).toPrecision(8):'—';
const range=x=>x?`[${number(x[0])}, ${number(x[1])}]`:'—';
const bounds=x=>{if(!Array.isArray(x)||x.length!==2||!x.every(Number.isFinite)||x[0]>x[1])throw new Error('有限な区間の原出力がありません');return x;};
const vector=x=>{if(!Array.isArray(x)||x.length!==3)throw new Error('3座標の原出力がありません');return x.map(bounds);};
const midpoint=x=>x[0]+(x[1]-x[0])/2; // DISPLAY ONLY
const bits=new DataView(new ArrayBuffer(8));
const next=(x,up)=>{if(x===0)return up?Number.MIN_VALUE:-Number.MIN_VALUE;bits.setFloat64(0,x);let b=bits.getBigUint64(0);b+=(x>0)===up?1n:-1n;bits.setBigUint64(0,b);return bits.getFloat64(0);};
// Outward endpoint generation only. Does not solve any optical equation.
const widen=(x,w)=>w===0?copy(x):[next((Array.isArray(x)?x[0]:x)-w,false),next((Array.isArray(x)?x[1]:x)+w,true)];
export function polarizedRouteCase(parameters={}){
  const p={...POLARIZED_ROUTE_DEFAULTS,...(parameters.preset==='budget'?{maximumSteps:1}:{}),...parameters};
  if(!Object.hasOwn(POLARIZED_ROUTE_PRESETS,p.preset)||!Object.hasOwn(states,p.stokes))throw new Error('参照例・初期Stokesを選択してください');
  const limits={originWidth:[0,1],directionWidth:[0,.1],indexWidth:[0,.25],maximumSteps:[1,64],maxSqrtRefinements:[1,256],powerMaxSqrtRefinements:[1,256],maximumTotalSqrtRefinements:[1,4000000]};
  for(const [key,[lo,hi]]of Object.entries(limits)){if(p[key]===''||typeof p[key]==='boolean'||!Number.isFinite(Number(p[key])))throw new Error('入力は空欄でない有限の数値が必要です');p[key]=Number(p[key]);if(p[key]<lo||p[key]>hi||(key.includes('Refinements')||key==='maximumSteps')&&!Number.isInteger(p[key]))throw new Error(`${key}は${lo}..${hi}の${key.includes('Refinements')||key==='maximumSteps'?'整数':'数値'}で指定してください`);}
  const disk=(center,normal)=>({kind:'disk',center,normal,apertureRadius:100});
  const step=(surface,nextIndex,branch='transmitted')=>({surface,nextIndex,branch,minimumParameter:0,maximumParameter:100});
  let origin=[0,0,0],direction=[0,0,1],index=1,reference=[1,0,0],steps=[step(disk([0,0,1],[0,0,-1]),1.5),step(disk([0,0,2],[0,0,-1]),1)];
  switch(p.preset){
    case 'rational':index=25;reference=[0,-1,0];steps=[step(disk([0,0,1],[3,0,-4]),39,'reflected'),step(disk([24,0,-6],[-543,300,-76]),39,'reflected')];break;
    case 'tir':direction=[4,-3,0];index=1.5;reference=[0,0,-1];steps=[step(disk([4,-3,0],[0,1,0]),1,'reflected'),step(disk([8,0,0],[-96,3,80]),1,'reflected')];break;
    case 'source_frame':reference=[0,0,1];break;
    case 'near_normal':direction=[[-1e-8,1e-8],0,1];steps=steps.slice(0,1);break;
    case 'critical':direction=[3,0,4];index=5;reference=[0,1,0];steps=[step(disk([0,0,1],[0,0,-1]),3)];break;
    case 'unavailable':direction=[4,-3,0];index=1.5;reference=[0,0,-1];steps=[step(disk([4,-3,0],[0,1,0]),1)];break;
    case 'plate':case 'budget':break;
  }
  const ray={origin:origin.map(x=>widen(x,p.originWidth)),direction:direction.map(x=>widen(x,p.directionWidth)),minimumParameter:0,maximumParameter:100};
  steps=steps.map(s=>({...s,nextIndex:widen(s.nextIndex,p.indexWidth)}));
  return {parameters:p,ray,steps,settings:{index:widen(index,p.indexWidth),vacuumWavelength:550e-9,transverseReference:reference,power:copy(states[p.stokes]),maximumSteps:p.maximumSteps,maximumParameterWidth:1e-7,maxSqrtRefinements:p.maxSqrtRefinements,powerMaxSqrtRefinements:p.powerMaxSqrtRefinements,maximumTotalSqrtRefinements:p.maximumTotalSqrtRefinements}};
}
export function evaluatePolarizedRouteCase(runtime,parameters={}){
  const source=polarizedRouteCase(parameters);
  if(typeof runtime?.tracePolarizedRoute!=='function')throw new Error('偏光経路の同梱WASMが未対応です。配信更新後に計算核を再読込してください。');
  return {source,result:runtime.tracePolarizedRoute(source.ray,source.steps,source.settings),diagnostics:runtime.diagnostics};
}
function validateState(state){
  if(!state?.coherency)throw new Error('原coherencyの出力がありません');bounds(state.power);
  const {diagonal,upper}=state.coherency;vector(diagonal);if(!Array.isArray(upper)||upper.length!==3)throw new Error('複素coherency成分が不足しています');for(const c of upper){bounds(c.real);bounds(c.imag);}return state;
}
export function polarizedTensorRows(state){
  if(!state)return null;validateState(state);const {diagonal,upper}=state.coherency,zero=[0,0],matrix=Array.from({length:3},()=>Array(3));
  for(let i=0;i<3;++i)matrix[i][i]={real:diagonal[i],imag:zero};
  [[0,1],[0,2],[1,2]].forEach(([i,j],k)=>{const c=upper[k];matrix[i][j]=c;matrix[j][i]={real:c.real,imag:[-c.imag[1],-c.imag[0]]};});return matrix;
}
export function validatePolarizedRouteOutput(output){
  const r=output?.result;if(!output?.source||!r||!['completed','geometry_failed','power_unresolved','invalid_input','budget_exceeded','numerical_failure'].includes(r.status)||!Array.isArray(r.segments))throw new Error('偏光経路の原出力が不正です');
  if(r.initialState)validateState(r.initialState);for(const s of r.segments){if(s.outgoing)validateState(s.outgoing);for(const a of [s.amplitudeS,s.amplitudeP])if(a){bounds(a.real);bounds(a.imag);}}
  if(r.status==='completed'&&!r.completion)throw new Error('完了結果に最終状態がありません');if(r.status!=='completed'&&r.completion)throw new Error('未完了の最終状態を表示できません');
  if(r.completion){validateState(r.completion.state);vector(r.completion.ray.origin);vector(r.completion.ray.direction);bounds(r.completion.index);}return output;
}
export function drawPolarizedRoute(canvas,output,vertical=1){
  const ctx=canvas.getContext('2d');if(!ctx)return;const w=canvas.width,h=canvas.height,pad=48;
  ctx.fillStyle='#0d1824';ctx.fillRect(0,0,w,h);ctx.font='14px system-ui';ctx.fillStyle='#c7d8e9';ctx.fillText(vertical===1?'XY投影 [m]：X → / Y ↑':'XZ投影 [m]：X → / Z ↑',pad,24);
  const segments=output?.result?.geometry?.segments??[],nodes=segments.flatMap(s=>s.geometry?.hit?[s.incoming.origin,s.geometry.hit.position]:[]);
  if(!nodes.length){ctx.fillText('実計算の交点なし',pad,h/2);return;}
  for(const node of nodes)vector(node);
  const lo=[0,vertical].map(k=>Math.min(...nodes.map(n=>n[k][0]))),hi=[0,vertical].map(k=>Math.max(...nodes.map(n=>n[k][1])));
  const span=Math.max(hi[0]-lo[0],hi[1]-lo[1],1e-3)*1.2,scale=Math.min(w-2*pad,h-2*pad)/span,cx=(lo[0]+hi[0])/2,cy=(lo[1]+hi[1])/2;
  const map=n=>[w/2+(midpoint(n[0])-cx)*scale,h/2-(midpoint(n[vertical])-cy)*scale];
  for(const [i,s]of segments.entries()){
    if(!s.geometry?.hit)continue;const a=map(s.incoming.origin),b=map(s.geometry.hit.position),box=s.geometry.hit.position;
    ctx.strokeStyle=output.result.segments.find(p=>p.ordinal===i)?.outgoing?'#7ee1d1':'#ffbf75';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();
    const left=w/2+(box[0][0]-cx)*scale,top=h/2-(box[vertical][1]-cy)*scale,bw=Math.max(3,(box[0][1]-box[0][0])*scale),bh=Math.max(3,(box[vertical][1]-box[vertical][0])*scale);ctx.strokeRect(left,top,bw,bh);ctx.fillStyle=ctx.strokeStyle;ctx.fillText(String(i+1),b[0]+7,b[1]-7);
  }
  ctx.fillStyle='#c7d8e9';ctx.fillText(`表示幅 ${number(span)} m / 線は位置中央値だけ`,pad,h-16);
}
const yieldFrame=()=>new Promise(resolve=>{if(typeof requestAnimationFrame==='function')requestAnimationFrame(()=>resolve());else setTimeout(resolve,0);});
const friendly=e=>/API unavailable|rebuild|matching WebAssembly/i.test(e?.message??'')?'偏光経路の同梱WASMが未対応です。配信更新後に計算核を再読込してください。':e?.message??String(e);
export async function initializePolarizedRouteLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,evaluate=evaluatePolarizedRouteCase,now=()=>performance.now(),yieldControl=yieldFrame}={}){
  const get=id=>doc.getElementById(id),controls={preset:'pr-preset',stokes:'pr-stokes',originWidth:'pr-origin-width',directionWidth:'pr-direction-width',indexWidth:'pr-index-width',maximumSteps:'pr-step-budget',maxSqrtRefinements:'pr-geometry-sqrt',powerMaxSqrtRefinements:'pr-power-sqrt',maximumTotalSqrtRefinements:'pr-total-sqrt'};
  let runtime=null,output=null,busy=false;
  const error=e=>{get('pr-error').hidden=!e;get('pr-error').textContent=e?friendly(e):'';};
  const lock=()=>{get('pr-controls').disabled=busy||!runtime;get('pr-retry').disabled=busy;get('pr-inspect').disabled=busy||!output;};
  const option=(value,label)=>{const o=doc.createElement('option');o.value=value;o.textContent=label;return o;};
  const tensor=()=>{
    const key=get('pr-inspect').value,r=output?.result,state=key==='final'?r?.completion?.state:key==='initial'?r?.initialState:r?.segments.find(s=>String(s.ordinal)===key)?.outgoing;
    get('pr-tensor').replaceChildren();const rows=polarizedTensorRows(state);get('pr-tensor-label').textContent=state?`${key==='final'?'最終':key==='initial'?'初期':`段${Number(key)+1}の後`} / POWER ${range(state.power)}（入射1に対する比）`:'最終状態なし。途中のprefixは表示選択から確認できます。';
    for(let i=0;i<3;++i){const tr=doc.createElement('tr'),th=doc.createElement('th');th.textContent=['X','Y','Z'][i];tr.appendChild(th);for(let j=0;j<3;++j){const td=doc.createElement('td');td.textContent=rows?`${range(rows[i][j].real)}\n+ i × ${range(rows[i][j].imag)}`:'—';tr.appendChild(td);}get('pr-tensor').appendChild(tr);}
  };
  const clear=()=>{output=null;get('pr-final-power').textContent='—';get('pr-prefix').textContent='—';get('pr-failure').textContent='未実行';get('pr-time').textContent='—';get('pr-work').textContent='—';get('pr-json').textContent='結果なし';get('pr-steps').replaceChildren();get('pr-inspect').replaceChildren(option('final','最終状態'));get('pr-inspect').value='final';tensor();drawPolarizedRoute(get('pr-xy'),null,1);drawPolarizedRoute(get('pr-xz'),null,2);lock();};
  const read=()=>Object.fromEntries(Object.entries(controls).map(([key,id])=>[key,get(id).value]));
  const populate=p=>{for(const [key,id]of Object.entries(controls))get(id).value=String(p[key]);};
  const render=()=>{
    const {source,result:r}=output;get('pr-final-power').textContent=range(r.completion?.state.power);get('pr-prefix').textContent=`幾何 ${r.geometry?.completedSteps??0} / 偏光 ${r.completedPowerSteps}`;
    get('pr-failure').textContent=`${r.status} / power: ${r.powerFailure} / 幾何 ${r.geometry?.status??'未実行'}${r.completion?' — 最終状態あり':' — 最終状態なし'}`;
    get('pr-work').textContent=`幾何照会 ${r.geometryQueries} / 界面 ${r.interfaceQueries} / 幾何√ ${r.geometrySqrtRefinements} / 偏光√ ${r.powerSqrtRefinements}${r.refinementLimited?' / 細分上限あり':''}`;
    get('pr-steps').replaceChildren();for(let i=0;i<source.steps.length;++i){const step=source.steps[i],g=r.geometry?.segments?.[i],p=r.segments.find(s=>s.ordinal===i),tr=doc.createElement('tr');const add=text=>{const td=doc.createElement('td');td.textContent=text;tr.appendChild(td);};
      add(`${i+1} / ${step.branch}`);add(g?`${g.geometry.status}: ${g.geometry.reason}\n界面 ${g.interface?.kind??'未照会'}\nt ${range(g.geometry.hit?.parameter)}`:'幾何は未実行');
      add(`入射 ${range(g?.incidentIndex)}\n他方 ${range(g?.otherIndex??(Array.isArray(step.nextIndex)?step.nextIndex:[step.nextIndex,step.nextIndex]))}`);
      add(p?`後のPOWER ${range(p.outgoing?.power)}\n${p.outgoing?'偏光prefix完了':'偏光の完了状態なし'}${p.exactNormal?' / 厳密正入射':''}${p.homogeneous?' / 同一媒質':''}`:'偏光は未実行');
      add(p?`s: ${p.amplitudeS?range(p.amplitudeS.real)+' + i '+range(p.amplitudeS.imag):'—'}\np: ${p.amplitudeP?range(p.amplitudeP.real)+' + i '+range(p.amplitudeP.imag):'—'}`:'—');get('pr-steps').appendChild(tr);
    }
    get('pr-inspect').replaceChildren(option('final','最終状態'));if(r.initialState)get('pr-inspect').appendChild(option('initial','初期状態'));
    for(const s of r.segments)if(s.outgoing)get('pr-inspect').appendChild(option(String(s.ordinal),`段${s.ordinal+1}の後（prefix）`));get('pr-inspect').value='final';tensor();
    get('pr-json').textContent=JSON.stringify(output,null,2);get('runtime-info').textContent=JSON.stringify(output.diagnostics??runtime?.diagnostics??{});drawPolarizedRoute(get('pr-xy'),output,1);drawPolarizedRoute(get('pr-xz'),output,2);
  };
  const calculate=async()=>{
    if(busy||!runtime)return null;clear();error(null);let parameters;try{parameters=polarizedRouteCase(read()).parameters;}catch(e){error(e);get('pr-status').textContent='入力を修正してください。';return null;}
    busy=true;lock();get('pr-status').textContent='実C++で指定経路を照会中…';const started=now();
    try{await yieldControl();const next=await evaluate(runtime,parameters);validatePolarizedRouteOutput(next);output=next;render();get('pr-status').textContent='照会を終了しました。幾何と偏光のprefix、未実行の行も確認してください。';return copy(output);}
    catch(e){clear();error(e);get('pr-status').textContent='照会に失敗。古い状態を消去しました。再読込や条件修正で再試行できます。';return null;}
    finally{get('pr-time').textContent=`${number(now()-started)} ms`;busy=false;lock();}
  };
  const retry=async()=>{
    if(busy)return;runtime=null;busy=true;clear();error(null);lock();get('pr-status').textContent='共通計算核を読込み中…';
    try{runtime=await loadRuntime();get('runtime-info').textContent=JSON.stringify(runtime?.diagnostics??{});get('pr-status').textContent='準備できました。条件を指定し計算ボタンを押してください。';}
    catch(e){error(e);get('pr-status').textContent='計算核を読込めませんでした。代替計算なし。再読込で再試行できます。';get('runtime-info').textContent='計算核なし';}
    finally{busy=false;lock();}
  };
  for(const [key,id]of Object.entries(controls))get(id).addEventListener(key==='preset'||key==='stokes'?'change':'input',()=>{if(busy)return;if(key==='preset')get('pr-step-budget').value=get(id).value==='budget'?'1':'64';clear();error(null);get('pr-status').textContent='条件を変更しました。計算ボタンを押してください。';});
  get('pr-inspect').addEventListener('change',()=>{if(!busy)tensor();});get('pr-calculate').addEventListener('click',calculate);get('pr-retry').addEventListener('click',retry);
  get('pr-reset').addEventListener('click',()=>{if(busy)return;populate(POLARIZED_ROUTE_DEFAULTS);clear();error(null);get('pr-status').textContent='既定条件へ戻しました。計算ボタンを押してください。';});
  populate(POLARIZED_ROUTE_DEFAULTS);clear();await retry();return {calculate,retry,getState:()=>({output:output?copy(output):null,busy})};
}
if(typeof document!=='undefined')initializePolarizedRouteLab().catch(e=>{const n=document.getElementById('pr-error');if(n){n.hidden=false;n.textContent=friendly(e);}});
