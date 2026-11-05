import {loadSimulationRuntime} from '../engine/simulation.mjs';
export const ROUTE_DEFAULTS={preset:'plate',thickness:.25,wavelengthNm:550,maximumSteps:64,maximumParameterWidth:1e-6,maxSqrtRefinements:128};
export function opticalRouteCase(parameters={}){
  const p={...ROUTE_DEFAULTS,...parameters};
  for(const key of ['thickness','wavelengthNm','maximumSteps','maximumParameterWidth','maxSqrtRefinements'])if(!Number.isFinite(Number(p[key])))throw new Error('光路の入力は有限の数値が必要です。');
  const thickness=Number(p.thickness),wavelength=Number(p.wavelengthNm)*1e-9;
  if(thickness<=0||thickness>10||wavelength<=0)throw new Error('厚さは0より大きく10m以下、波長は正で指定します。');
  const disk=z=>({kind:'disk',center:[0,0,z],normal:[0,0,-1],apertureRadius:10});
  const step=(surface,nextIndex=1,branch='transmitted')=>({surface,nextIndex,branch,minimumParameter:0,maximumParameter:10});
  let ray={origin:[0,0,-1],direction:[0,0,1],minimumParameter:0,maximumParameter:10},index=1,front=disk(0),back=disk(thickness),sensor=disk(thickness+1),steps,materialModel=null;
  switch(p.preset){
    case 'plate':break;
    case 'ghost':break;
    case 'brewster':ray.direction=[3,0,4];index=4;break;
    case 'lens':case 'dispersion':
      if(thickness<.2)throw new Error('球面例の厚さは0.2m以上です。開口内で面が交差しない条件を使います。');
      ray.origin=[.4,0,-1];front={kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:2,apertureRadius:.6};
      back={kind:'cap',vertex:[0,0,thickness],axis:[0,0,1],signedRadius:-2,apertureRadius:.6};sensor=disk(thickness+2);
      if(p.preset==='dispersion')materialModel={kind:'cauchy',coefficients:[1.5,2**-48,2**-100],validBand:[300e-9,900e-9]};break;
    case 'family':ray.origin=[[-.02,.02],0,[-1.001,-.999]];break;
    case 'critical':ray.direction=[4,0,3];index=[1.2,1.3];break;
    default:throw new Error('光路プリセットが不正です。');
  }
  const inside=p.preset==='brewster'?3:p.preset==='family'?[1.4,1.6]:1.5;
  steps=p.preset==='ghost'?[step(front,inside),step(back,1,'reflected'),step(front,1,'reflected'),step(back),step(sensor)]:
    p.preset==='critical'?[step(front)]:[step(front,inside),step(back,index),step(sensor,index)];
  return {parameters:p,ray,steps,materialModel,settings:{index,vacuumWavelength:wavelength,maximumSteps:Number(p.maximumSteps),maximumParameterWidth:Number(p.maximumParameterWidth),maxSqrtRefinements:Number(p.maxSqrtRefinements)}};
}
export function evaluateOpticalRouteCase(runtime,parameters={}){
  const source=opticalRouteCase(parameters);
  if(source.materialModel){
    source.dispersion=runtime.queryDispersion(source.materialModel,source.settings.vacuumWavelength);
    if(source.dispersion.status!=='resolved'||!source.dispersion.values?.withinInterfaceDomain)throw new Error(`屈折率の全包含を光路へ渡せません: ${source.dispersion.reason}`);
    source.steps[0].nextIndex=source.dispersion.values.phase.slice();
  }
  const result=runtime.traceOpticalRoute(source.ray,source.steps,source.settings);return {source,result};
}
const number=x=>Number(x).toPrecision(10),range=a=>a?`[${Number(a[0]).toPrecision(17)}, ${Number(a[1]).toPrecision(17)}]`:'—';
const point=a=>a.map(x=>Array.isArray(x)?(x[0]+x[1])/2:x); // DISPLAY ONLY
function draw(canvas,state){
  const ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#101a28';ctx.fillRect(0,0,w,h);ctx.font='16px sans-serif';ctx.fillStyle='#e1eaf5';
  if(!state){ctx.fillText('光路の結果なし',25,40);return;}
  const {source,result}=state,origin=point(source.ray.origin),hits=result.segments.flatMap(s=>s.geometry.hit?[point(s.geometry.hit.position)]:[]);
  const anchors=source.steps.map(s=>s.surface.vertex??s.surface.center),zs=[origin[2],...anchors.map(a=>a[2]),...hits.map(a=>a[2])],zlo=Math.min(...zs)-.2,zhi=Math.max(...zs)+.25;
  const spread=Math.max(1,...[origin,...hits].map(a=>Math.abs(a[0])+.2)),mapZ=z=>65+(z-zlo)/(zhi-zlo)*(w-95),mapX=x=>h/2-x/spread*(h-100)/2;
  ctx.strokeStyle='#4c6279';ctx.setLineDash([5,5]);ctx.beginPath();ctx.moveTo(55,mapX(0));ctx.lineTo(w-20,mapX(0));ctx.stroke();ctx.setLineDash([]);ctx.fillText('Z [m] →',w-110,h-20);ctx.fillText('↑ X [m]',15,22);
  const unique=new Map();for(const step of source.steps)unique.set(JSON.stringify(step.surface),step.surface);
  for(const surface of unique.values()){
    ctx.strokeStyle=surface.kind==='cap'?'#96a7e7':'#7a91a5';ctx.lineWidth=2;ctx.beginPath();
    if(surface.kind==='disk'){const z=surface.center[2],ap=Math.min(surface.apertureRadius,spread);ctx.moveTo(mapZ(z),mapX(-ap));ctx.lineTo(mapZ(z),mapX(ap));}
    else if(surface.kind==='cap'){
      // Display-only sampled outline; all intersections come from C++.
      for(let j=0;j<=64;++j){const x=-surface.apertureRadius+2*surface.apertureRadius*j/64,r=surface.signedRadius,z=surface.vertex[2]+r-Math.sign(r)*Math.sqrt(r*r-x*x);if(j===0)ctx.moveTo(mapZ(z),mapX(x));else ctx.lineTo(mapZ(z),mapX(x));}
    }ctx.stroke();
  }
  for(const [j,s]of result.segments.entries()){
    if(!s.geometry.hit)continue;const a=point(s.incoming.origin),b=point(s.geometry.hit.position);ctx.strokeStyle=s.accumulated?'#75d6ff':'#ffb97d';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(mapZ(a[2]),mapX(a[0]));ctx.lineTo(mapZ(b[2]),mapX(b[0]));ctx.stroke();
    const box=s.geometry.hit.position,left=mapZ(box[2][0]),right=mapZ(box[2][1]),top=mapX(box[0][1]),bottom=mapX(box[0][0]),bw=Math.max(6,right-left),bh=Math.max(6,bottom-top);
    ctx.strokeRect((left+right-bw)/2,(top+bottom-bh)/2,bw,bh);ctx.fillStyle=ctx.strokeStyle;ctx.fillText(String(j+1),mapZ(b[2])+8,mapX(b[0])-8);
  }
  ctx.fillStyle='#afc2d5';ctx.fillText(`Z: ${number(zlo)} … ${number(zhi)} m / X: ±${number(spread)} m`,65,h-20);
}
export async function initializeOpticalRouteLab({doc=document,loadRuntime=loadSimulationRuntime}={}){
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false;
  const clear=()=>{state=null;for(const id of ['route-length','route-opl','route-power','route-final','route-segments'])get(id).textContent='—';get('route-json').textContent='結果なし';draw(get('route-view'),null);};
  const error=e=>{clear();get('route-error').hidden=false;get('route-error').textContent=String(e.message??e);get('route-status').textContent='光路照会に失敗。古い結果を消去しました。';};
  function recalculate(){
    if(!runtime)return null;
    try{
      const next=evaluateOpticalRouteCase(runtime,{preset:get('route-preset').value,thickness:Number(get('plate-thickness').value),wavelengthNm:Number(get('route-wavelength').value),maximumSteps:Number(get('route-step-budget').value),maximumParameterWidth:Number(get('route-width').value),maxSqrtRefinements:Number(get('route-sqrt-budget').value)}),r=next.result,c=r.completion;
      get('route-status').textContent=c?`指定した${r.completedSteps}段の光路が全入力族について完了。`:`未完了: ${r.status} / 対象は${r.failedStep+1}段目 / 完了prefix ${r.completedSteps}段。最終光線なし。`;
      get('route-length').textContent=range(c?.totals.distance);get('route-opl').textContent=range(c?.totals.opticalPathLength);get('route-power').textContent=range(c?.totals.throughput);
      get('route-final').textContent=c?`センサー位置のX包含 ${range(c.ray.origin[0])} m / 最終媒質n ${range(c.index)}`:'—';
      get('route-segments').textContent=r.segments.length?r.segments.map((s,j)=>`${j+1}: ${s.branch} / ${s.geometry.status}:${s.geometry.reason} / interface=${s.interface?.kind??'なし'}\n  入射n=${range(s.incidentIndex)} / 他方n=${range(s.otherIndex)}\n  距離=${range(s.geometry.hit?.physicalDistance)} m / factor=${range(s.factor)}${s.accumulated?' / 完了prefix':' / 未完了候補'}`).join('\n\n'):'実行された面照会なし';
      get('route-error').hidden=true;get('route-json').textContent=JSON.stringify({...next,diagnostics:runtime.diagnostics},null,2);state=next;draw(get('route-view'),state);return state;
    }catch(e){error(e);return null;}
  }
  async function retry(){
    if(busy)return null;busy=true;runtime=null;clear();get('route-controls').disabled=true;get('route-retry').disabled=true;
    try{runtime=await loadRuntime();if(typeof runtime?.traceOpticalRoute!=='function')throw new Error('指定光路の共通APIを利用できません。');get('route-controls').disabled=false;get('runtime-info').textContent=`${runtime.diagnostics?.backend} / ${runtime.diagnostics?.wasmBytes} bytes / build ${runtime.diagnostics?.buildId}`;return recalculate();
    }catch(e){runtime=null;error(e);return null;}finally{busy=false;get('route-retry').disabled=false;}
  }
  get('route-preset').addEventListener('change',recalculate);
  for(const id of ['plate-thickness','route-wavelength','route-step-budget','route-width','route-sqrt-budget']){get(id).addEventListener('input',recalculate);get(id).addEventListener('change',recalculate);}
  get('route-retry').addEventListener('click',retry);await retry();return {recalculate,retry,getState:()=>state};
}
if(typeof document!=='undefined')initializeOpticalRouteLab();
