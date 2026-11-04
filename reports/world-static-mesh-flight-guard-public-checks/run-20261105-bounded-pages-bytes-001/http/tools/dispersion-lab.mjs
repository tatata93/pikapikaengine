import {loadSimulationRuntime} from '../engine/simulation.mjs';

export const DISPERSION_DEFAULTS={kind:'cauchy',minimumNm:400,maximumNm:700,maximumPhaseWidth:1,maxSqrtRefinements:128};
export function dispersionCase(parameters={}){
  const p={...DISPERSION_DEFAULTS,...parameters};
  if(!['cauchy','sellmeier','pole'].includes(p.kind))throw new Error('分散モデルが不正です。');
  for(const key of ['minimumNm','maximumNm','maximumPhaseWidth','maxSqrtRefinements'])if(!Number.isFinite(Number(p[key])))throw new Error('入力は有限の数値が必要です。');
  const lo=Number(p.minimumNm)*1e-9,hi=Number(p.maximumNm)*1e-9;
  if(lo<=0||hi<lo)throw new Error('波長は正で、開始≦終了が必要です。');
  const model=p.kind==='cauchy'?{kind:'cauchy',coefficients:[1.5,2**-48,2**-100],validBand:[300e-9,900e-9]}:
    {kind:'sellmeier',terms:[[.75,p.kind==='pole'?(550e-9)**2:(150e-9)**2]],validBand:[300e-9,900e-9]};
  return {parameters:p,model,wavelength:[lo,hi],settings:{maximumPhaseWidth:Number(p.maximumPhaseWidth),maxSqrtRefinements:Number(p.maxSqrtRefinements)}};
}
export function evaluateDispersionCase(runtime,parameters={}){
  const source=dispersionCase(parameters),result=runtime.queryDispersion(source.model,source.wavelength,source.settings);
  // Adjacent bins share the SAME binary64 boundary, with no gaps. Every plotted
  // rectangle comes from a full-band C++ query, never a JS dispersion equation.
  const edges=Array.from({length:33},(_,j)=>source.wavelength[0]+(source.wavelength[1]-source.wavelength[0])*(j/32));
  edges[0]=source.wavelength[0];edges[32]=source.wavelength[1];
  const bins=edges.slice(0,-1).map((lo,j)=>({wavelength:[lo,edges[j+1]],result:runtime.queryDispersion(source.model,[lo,edges[j+1]],source.settings)}));
  return {source,result,bins};
}
const formatted=x=>Number(x).toPrecision(12),range=x=>x?`[${Number(x[0]).toPrecision(17)}, ${Number(x[1]).toPrecision(17)}]`:'—';
function draw(canvas,state){
  const ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#101a28';ctx.fillRect(0,0,w,h);
  ctx.font='15px sans-serif';ctx.fillStyle='#e1eaf5';
  if(!state){ctx.fillText('照会結果なし',32,45);return;}
  const finite=state.bins.flatMap(b=>b.result.values?[...b.result.values.phase,...b.result.values.group]:[]).filter(Number.isFinite);
  if(!finite.length){ctx.fillText('全区間が未解決。曲線は作りません。',32,45);return;}
  const min=Math.min(...finite),max=Math.max(...finite),padding=Math.max((max-min)*.08,.001),lower=min-padding,upper=max+padding;
  const x=lambda=>65+(lambda-state.source.wavelength[0])/Math.max(state.source.wavelength[1]-state.source.wavelength[0],1e-30)*(w-95);
  const y=n=>h-50-(n-lower)/(upper-lower)*(h-100);
  ctx.strokeStyle='#798ba3';ctx.beginPath();ctx.moveTo(65,45);ctx.lineTo(65,h-50);ctx.lineTo(w-30,h-50);ctx.stroke();
  ctx.fillText(`n, ng: ${formatted(lower)} … ${formatted(upper)}`,70,24);
  ctx.fillText(`${state.source.parameters.minimumNm} nm`,65,h-20);ctx.fillText(`${state.source.parameters.maximumNm} nm`,w-105,h-20);
  for(const b of state.bins){
    const left=x(b.wavelength[0]),width=Math.max(1,x(b.wavelength[1])-left);
    if(!b.result.values){ctx.fillStyle='#fb9f58';ctx.fillRect(left,h-47,width,6);continue;}
    for(const [key,color]of [['phase','#73c9ff'],['group','#edb9fa']]){
      const bound=b.result.values[key];ctx.strokeStyle=color;ctx.strokeRect(left,y(bound[1]),width,Math.max(1,y(bound[0])-y(bound[1])));
    }
  }
}
export async function initializeDispersionLab({doc=document,loadRuntime=loadSimulationRuntime}={}){
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false;
  const clear=()=>{state=null;for(const id of ['phase-value','derivative-value','group-value','phase-domain'])get(id).textContent='—';get('dispersion-json').textContent='結果なし';draw(get('dispersion-view'),null);};
  const error=e=>{clear();get('dispersion-error').hidden=false;get('dispersion-error').textContent=String(e.message??e);get('dispersion-status').textContent='照会失敗。表示結果を消去しました。';};
  function recalculate(){
    if(!runtime)return null;
    try{
      const next=evaluateDispersionCase(runtime,{kind:get('dispersion-kind').value,minimumNm:Number(get('lambda-min').value),maximumNm:Number(get('lambda-max').value),maximumPhaseWidth:Number(get('phase-width').value),maxSqrtRefinements:Number(get('sqrt-budget').value)});
      const r=next.result;get('dispersion-status').textContent=`${r.status} / ${r.reason} / sqrt精錬 ${r.sqrtRefinements}回`;
      get('phase-value').textContent=range(r.values?.phase);get('derivative-value').textContent=range(r.values?.derivative);get('group-value').textContent=range(r.values?.group);
      get('phase-domain').textContent=r.values?(r.values.withinInterfaceDomain?'この全屈折率包含区間は、既存の界面APIの数値入力域内です。':'界面APIの入力域内であることを、この包含区間では保証できません。'):'未解決または非物理モデル。成功値はありません。';
      get('dispersion-error').hidden=true;get('dispersion-json').textContent=JSON.stringify({...next,diagnostics:runtime.diagnostics},null,2);state=next;draw(get('dispersion-view'),state);return state;
    }catch(e){error(e);return null;}
  }
  async function retry(){
    if(busy)return null;busy=true;runtime=null;clear();get('dispersion-controls').disabled=true;get('dispersion-retry').disabled=true;
    try{runtime=await loadRuntime();if(typeof runtime?.queryDispersion!=='function')throw new Error('分散の共通APIを利用できません。');get('dispersion-controls').disabled=false;
      get('runtime-info').textContent=`${runtime.diagnostics?.backend} / ${runtime.diagnostics?.wasmBytes} bytes / build ${runtime.diagnostics?.buildId}`;return recalculate();
    }catch(e){runtime=null;error(e);return null;}finally{busy=false;get('dispersion-retry').disabled=false;}
  }
  for(const id of ['dispersion-kind','lambda-min','lambda-max','phase-width','sqrt-budget'])get(id).addEventListener('change',recalculate);
  for(const id of ['lambda-min','lambda-max','phase-width','sqrt-budget'])get(id).addEventListener('input',recalculate);
  get('dispersion-retry').addEventListener('click',retry);await retry();return {recalculate,retry,getState:()=>state};
}
if(typeof document!=='undefined')initializeDispersionLab();
