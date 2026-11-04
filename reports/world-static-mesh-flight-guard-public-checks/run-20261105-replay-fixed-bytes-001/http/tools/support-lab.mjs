import {loadSimulationRuntime} from '../engine/simulation.mjs';
export const SUPPORT_DEFAULTS={preset:'floor',forceDeltaY:0,normalVelocity:0,gapTolerance:1e-8,maxIterations:20000};
export function supportCase(parameters={}){
  const p={...SUPPORT_DEFAULTS,...parameters};
  for(const key of ['forceDeltaY','normalVelocity','gapTolerance','maxIterations'])if(!Number.isFinite(Number(p[key])))throw new Error('支持条件は有限の数値が必要です。');
  if(!Number.isInteger(Number(p.maxIterations))||Number(p.maxIterations)<1||Number(p.maxIterations)>100000)throw new Error('反復上限は1〜100000の整数です。');
  const body=(id,mass,position,isStatic=false)=>({id,mass,radius:.5,position,isStatic,linearVelocity:[0,0,0],force:[0,0,0],torque:[1,2,3]});
  let bodies=[body(1,1,[0,.5,0])],planes=[{id:100,normal:[0,1,0],offset:0}];
  switch(p.preset){
    case 'floor':break;
    case 'stack':bodies=[1,2,3].map(id=>({...body(id,id,[0,id-.5,0]),force:[0,[5,-4,7][id-1],0]}));break;
    case 'slope':planes=[{id:100,normal:[.6,.8,0],offset:-.5}];bodies=[body(1,1,[0,0,0])];break;
    case 'curvature':case 'detach':planes=[];bodies=[{...body(1,1,[0,1,0]),linearVelocity:[p.preset==='detach'?4:2,0,0]},body(2,1,[0,0,0],true)];break;
    case 'positive-gap':bodies[0].position[1]+=1e-9;break;
    case 'impact':bodies[0].linearVelocity[1]=-1e-20;break;
    default:throw new Error('支持プリセットが不正です。');
  }
  bodies[0].force[1]+=Number(p.forceDeltaY);bodies[0].linearVelocity[1]+=Number(p.normalVelocity);
  return {parameters:p,gravity:[0,-10,0],bodies,planes,settings:{gapTolerance:Number(p.gapTolerance),velocityIntervalTolerance:1e-9,accelerationTolerance:1e-8,complementarityTolerance:1e-7,
    projectedForceTolerance:1e-8,minimumScaledPivot:1e-10,maximumForce:1e24,maxIterations:Number(p.maxIterations),maxContacts:128,maxPairQueries:100000}};
}
export function evaluateSupportCase(runtime,parameters={}){
  const source=supportCase(parameters),world=runtime.createWorld({gravity:source.gravity});
  try{
    for(const b of source.bodies)world.addBody(b);for(const p of source.planes)world.addPlane(p);
    const snapshot=()=>({info:world.info(),bodies:source.bodies.map(b=>world.getBody(b.id))});
    const before=snapshot(),result=world.querySupport(source.settings),after=snapshot();
    if(JSON.stringify(before)!==JSON.stringify(after))throw new Error('支持照会がWorldを変更しました。');
    return {source,result,before,after,worldUnchanged:true};
  }finally{world.dispose();}
}
const number=x=>Number(x).toPrecision(8),range=a=>`[${Number(a[0]).toPrecision(17)}, ${Number(a[1]).toPrecision(17)}]`;
function draw(canvas,state){
  const ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#101a28';ctx.fillRect(0,0,w,h);ctx.font='17px sans-serif';ctx.fillStyle='#e1eaf5';
  if(!state){ctx.fillText('照会結果なし',30,40);return;}
  const bodies=state.before.bodies,minY=Math.min(...bodies.map(b=>b.position[1]-b.radius),-.8),maxY=Math.max(...bodies.map(b=>b.position[1]+b.radius),1.2);
  const minX=Math.min(...bodies.map(b=>b.position[0]-b.radius),-1.6),maxX=Math.max(...bodies.map(b=>b.position[0]+b.radius),1.6);
  const scale=Math.min((w-180)/(maxX-minX),(h-100)/(maxY-minY)),x=v=>w/2+(v-(minX+maxX)/2)*scale,y=v=>h-50-(v-minY)*scale;
  ctx.strokeStyle='#718da5';ctx.lineWidth=2;
  for(const p of state.source.planes){const nx=p.normal[0],ny=p.normal[1];ctx.beginPath();
    if(ny!==0){ctx.moveTo(x(minX),y((p.offset-nx*minX)/ny));ctx.lineTo(x(maxX),y((p.offset-nx*maxX)/ny));}
    else if(nx!==0){ctx.moveTo(x(p.offset/nx),y(minY));ctx.lineTo(x(p.offset/nx),y(maxY));}ctx.stroke();}
  const reactions=state.result.success?state.result.bodies:[],largest=Math.max(1,...reactions.map(b=>Math.hypot(b.force[0],b.force[1])));
  for(const b of bodies){const px=x(b.position[0]),py=y(b.position[1]);ctx.fillStyle=b.isStatic?'#526478':'#24577c';ctx.strokeStyle='#9ed8ff';ctx.beginPath();ctx.arc(px,py,b.radius*scale,0,2*Math.PI);ctx.fill();ctx.stroke();ctx.fillStyle='#e1eaf5';ctx.fillText(`#${b.id} ${number(b.mass)} kg`,px+b.radius*scale+12,py+5);
    const r=reactions.find(r=>r.id===b.id);if(!r)continue;const length=Math.hypot(r.force[0],r.force[1]);if(length===0)continue;
    const factor=110/largest,dx=r.force[0]*factor,dy=-r.force[1]*factor,angle=Math.atan2(dy,dx);ctx.strokeStyle='#80edc1';ctx.fillStyle='#80edc1';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px+dx,py+dy);ctx.stroke();ctx.beginPath();ctx.moveTo(px+dx,py+dy);ctx.lineTo(px+dx-12*Math.cos(angle-.5),py+dy-12*Math.sin(angle-.5));ctx.lineTo(px+dx-12*Math.cos(angle+.5),py+dy-12*Math.sin(angle+.5));ctx.closePath();ctx.fill();
  }
  ctx.fillStyle=state.result.success?'#80edc1':'#ffbc8c';ctx.fillText(state.result.success?'緑: 各球に働く法線反力の合計（実C++・表示倍率あり）':'失敗候補は支持反力として描きません。',22,30);
}
export async function initializeSupportLab({doc=document,loadRuntime=loadSimulationRuntime}={}){
  const get=id=>doc.getElementById(id);let runtime=null,state=null,busy=false;
  const clear=()=>{state=null;for(const id of ['support-counts','support-residuals','support-constraints','support-invariant'])get(id).textContent='—';get('support-json').textContent='結果なし';draw(get('support-view'),null);};
  const error=e=>{clear();get('support-error').hidden=false;get('support-error').textContent=String(e.message??e);get('support-status').textContent='照会失敗。古い結果を消去しました。';};
  function recalculate(){
    if(!runtime)return null;
    try{
      const next=evaluateSupportCase(runtime,{preset:get('support-preset').value,forceDeltaY:Number(get('force-delta').value),normalVelocity:Number(get('normal-velocity').value),gapTolerance:Number(get('gap-band').value),maxIterations:Number(get('support-iterations').value)}),r=next.result;
      get('support-status').textContent=r.success?'法線支持の候補解を残差条件内で確認しました。':`支持照会は不成立: ${r.failure}。候補をWorldへ適用しません。`;
      get('support-counts').textContent=`rest ${r.restingConstraints} / separating ${r.separatingConstraints} / 反復 ${r.iterations} / pair照会 ${r.pairQueries}`;
      get('support-residuals').textContent=`負加速度 ${number(r.residuals.negativeAcceleration)} m/s²、相補性 ${number(r.residuals.complementarity)} N·m/s²、投影残差 ${number(r.residuals.projectedForce)} N、最大幾何offset ${number(r.maximumGeometryOffset)} m`;
      get('support-constraints').textContent=r.constraints.length?r.constraints.map(c=>`#${c.firstId} → #${c.secondId} / ${c.phase}\n  λ=${number(c.lambda)} N、gap=${range(c.gap)} m\n  vn=${range(c.normalVelocity)} m/s、曲率=${range(c.curvature)} m/s²\n  a_n=${range(c.accelerationBounds)} m/s²`).join('\n\n'):'保持された接触候補なし';
      get('support-invariant').textContent=`照会前後の全body状態・保持荷重・時刻が一致。t=${next.after.info.time} s / ${next.after.info.ticks} tick。時間積分は行っていません。`;
      get('support-error').hidden=true;get('support-json').textContent=JSON.stringify({...next,diagnostics:runtime.diagnostics},null,2);state=next;draw(get('support-view'),state);return state;
    }catch(e){error(e);return null;}
  }
  async function retry(){
    if(busy)return null;busy=true;runtime=null;clear();get('support-controls').disabled=true;get('support-retry').disabled=true;
    try{runtime=await loadRuntime();if(typeof runtime?.createWorld!=='function')throw new Error('World APIを利用できません。');get('support-controls').disabled=false;get('runtime-info').textContent=`${runtime.diagnostics?.backend} / ${runtime.diagnostics?.wasmBytes} bytes / build ${runtime.diagnostics?.buildId}`;return recalculate();
    }catch(e){runtime=null;error(e);return null;}finally{busy=false;get('support-retry').disabled=false;}
  }
  get('support-preset').addEventListener('change',recalculate);
  for(const id of ['force-delta','normal-velocity','gap-band','support-iterations']){get(id).addEventListener('input',recalculate);get(id).addEventListener('change',recalculate);}
  get('support-retry').addEventListener('click',retry);await retry();return {recalculate,retry,getState:()=>state};
}
if(typeof document!=='undefined')initializeSupportLab();
