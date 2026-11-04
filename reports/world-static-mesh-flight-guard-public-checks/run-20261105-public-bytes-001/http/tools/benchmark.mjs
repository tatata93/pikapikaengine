import {Renderer} from '../engine/renderer.mjs';
import {initializePortableCore} from '../engine/portable.mjs';
import {FixedClock,FrameLog} from '../engine/time.mjs';
import {RobotGame} from '../samples/robot.mjs';
const $=id=>document.getElementById(id);let renderer,running=false;const started=performance.now();
try{await initializePortableCore();renderer=await Renderer.create($('view'),message=>{$('status').textContent=message;running=false;});renderer.pixelRatio=1;$('run').disabled=false;$('run').textContent='試験を開始';$('status').textContent='C++ WASM / WEBGPU READY';}catch(error){$('status').textContent=error.message;}
const initializationMs=performance.now()-started;
$('run').onclick=()=>{
  if(running)return;running=true;$('run').disabled=true;$('download').disabled=true;
  const game=new RobotGame(),clock=new FixedClock(),log=new FrameLog(20000),duration=Math.max(10,Math.min(120,Number($('duration').value)||30));game.state='playing';
  let previous=null,begin=null,frameIndex=0;const visibilityChanges=[];
  const visibility=()=>visibilityChanges.push({atMs:begin===null?null:performance.now()-begin,state:document.visibilityState});document.addEventListener('visibilitychange',visibility);
  function frame(now){
    if(!running){document.removeEventListener('visibilitychange',visibility);$('run').disabled=false;return;}
    try{
      if(begin===null){begin=now;previous=now;}
      const cpuStart=performance.now(),frameMs=now-previous;previous=now;const elapsed=(now-begin)/1000,phase=Math.min(3,Math.floor(elapsed/duration*4));
      const alpha=clock.advance(Math.max(0,frameMs)/1000,dt=>{
        const t=game.time,yaw=phase>=1?t*1.6:0;game.step(dt,{forward:phase!==2,right:phase===2,boost:phase===1,fire:phase>=2,yaw});
        if(phase===3&&clock.tick%3===0&&game.projectiles.length<480){const a=t*9;game.fire([Math.sin(a)*80,40,Math.cos(a)*80],[Math.sin(a+.6)*80,45,Math.cos(a+.6)*80],true);}
      });
      const simulationMs=performance.now()-cpuStart,p=game.player.p,angle=phase>=1?game.time*1.6:0,items=game.view(alpha);
      renderer.render(items,{eye:[p[0]+Math.sin(angle)*27,p[1]+14,p[2]+Math.cos(angle)*27],target:[p[0]-Math.sin(angle)*20,p[1]+4,p[2]-Math.cos(angle)*20]},game.time);
      log.record(frameMs,performance.now()-cpuStart,simulationMs,items.length,game.projectiles.length);log.samples.at(-1).phase=['movement','turn','combat','projectile-stress'][phase];
      if(frameIndex++%15===0)$('status').textContent=`${elapsed.toFixed(1)} / ${duration} s · ${log.samples.at(-1).phase} · ${game.projectiles.length} 弾`;
      if(elapsed<duration){requestAnimationFrame(frame);return;}
      running=false;document.removeEventListener('visibilitychange',visibility);
      const info=renderer.adapter.info;
      const report=log.report({codeVersion:'0.2.0',moduleBuild:new URL(import.meta.url).searchParams.get('build'),sourceMeshes:game.scene.entities.filter(e=>e.type==='mesh').length,seed:93,simulationHz:120,resolution:[$('view').width,$('view').height],dpr:1,quality:'fixed GGX direct + constant ambient, roughness .52, exposure1.15, fog.0025, no shadow',userAgent:navigator.userAgent,gpu:info?{vendor:info.vendor,architecture:info.architecture,device:info.device,description:info.description}:null,startupMs:initializationMs,intervalSeconds:elapsed,visibilityAtFinish:document.visibilityState,visibilityChanges,clockDroppedSeconds:clock.droppedSeconds,gameState:game.state,wave:game.wave,maxProjectiles:Math.max(...log.samples.map(s=>s.projectiles)),audio:'disabled; separate test required',presentedFrames:null,gpuMs:null,exclusions:'Initialization measured separately. No frame samples or visibility intervals removed. First sample interval is zero because it has no preceding rAF; first-frame CPU time is retained.',timingThreshold:'strict 1000/60ms; browser timestamp quantization may cause threshold crossings; no post-hoc tolerance'});
      report.date=new Date().toISOString();report.status=report.overBudget?'TARGET_NOT_MET':'RAF_INTERVALS_WITHIN_BUDGET_PRESENTATION_UNVERIFIED';
      const text=JSON.stringify(report,null,2);$('result').textContent=text;$('status').textContent=`完了: ${report.retainedFrames}フレーム / p95 ${report.p95.toFixed(2)} ms / 超過 ${report.overBudget}件 / 実提示未検証`;$('run').disabled=false;$('download').disabled=false;
      $('download').onclick=()=>{const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='pikapika-benchmark.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    }catch(error){running=false;document.removeEventListener('visibilitychange',visibility);$('status').textContent=error.stack||error.message;$('run').disabled=false;}
  }
  requestAnimationFrame(frame);
};
