import {Renderer} from '../engine/renderer.mjs';
import {SpatialAudio} from '../engine/audio.mjs';
import {FixedClock,FrameLog} from '../engine/time.mjs';
import {Scene,box} from '../engine/scene.mjs';
import {parsePortableScene,savePortableScene} from '../engine/portable-scene.mjs';
import {RobotGame} from './robot.mjs';
import {length,sub,clamp,lerp,multiply,perspective,lookAt} from '../engine/math.mjs';
const $=id=>document.getElementById(id),canvas=$('world'),audio=new SpatialAudio(),clock=new FixedClock(),log=new FrameLog();
const game=new RobotGame();let renderer,yaw=0,lastTime=0,paused=false,dragging=false,mouseFire=false,renderAlpha=0,frameCount=0,lastCpu=0,editor=false;
const keys=new Set();let camera={eye:[0,18,65],target:[0,5,0]};
function fatal(message){$('fatal-message').textContent=message;$('fatal').hidden=false;$('opening').hidden=true;$('status').textContent='ERROR';game.state='error';}
function download(name,text,type='application/json'){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
const input=()=>({forward:keys.has('KeyW'),backward:keys.has('KeyS'),left:keys.has('KeyA'),right:keys.has('KeyD'),boost:keys.has('ShiftLeft')||keys.has('ShiftRight'),ascend:keys.has('Space'),fire:keys.has('KeyF')||mouseFire,yaw});
function setPaused(value){paused=value;$('pause-indicator').hidden=!paused;clock.accumulator=0;keys.clear();mouseFire=false;}
window.addEventListener('keydown',event=>{
  if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(event.target.tagName))return;
  if(['Space','Tab','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.code))event.preventDefault();
  if(!event.repeat&&event.code==='Tab')game.cycleLock();
  if(!event.repeat&&event.code==='KeyP'&&game.state==='playing')setPaused(!paused);
  keys.add(event.code);
});window.addEventListener('keyup',e=>keys.delete(e.code));
window.addEventListener('blur',()=>{if(game.state==='playing')setPaused(true);});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&game.state==='playing')setPaused(true);lastTime=0;});
canvas.addEventListener('pointerdown',event=>{canvas.focus();if(event.button===0)mouseFire=true;if(event.button===2){dragging=true;canvas.setPointerCapture(event.pointerId);}});
canvas.addEventListener('contextmenu',event=>event.preventDefault());
canvas.addEventListener('pointermove',event=>{if(dragging)yaw-=event.movementX*.006;});
window.addEventListener('pointerup',()=>{mouseFire=false;dragging=false;});
async function launch(){
  try{await audio.start();$('capability').textContent='音声出力を開始しました（聴感は未確認）。';}catch(error){$('capability').textContent=`音声を開始できません: ${error.message}`;}
  game.reset();game.state='playing';clock.reset();yaw=0;paused=false;lastTime=0;$('opening').hidden=true;$('result').hidden=true;$('pause-indicator').hidden=true;$('status').textContent='SIMULATION ONLINE';canvas.focus();
}
$('launch').onclick=launch;$('restart').onclick=launch;$('mute').onchange=e=>audio.mute(e.target.checked);
$('export-log').onclick=()=>download('pikapika-frame-log.json',JSON.stringify(log.report({userAgent:navigator.userAgent,viewport:[canvas.width,canvas.height],devicePixelRatio,quality:'fixed 1.5 DPR cap, GGX direct + ambient, no shadows',backend:'WebGPU',simulationHz:120,seed:93,wave:game.wave,stress:$('stress').checked,clockDroppedSeconds:clock.droppedSeconds,visibility:document.visibilityState,codeVersion:'0.1.0',cpuMs:'JS simulation + encode/submit; excludes GPU and presentation',audio:'generated triangle pulse, capped 24 voices'}),null,2));
function tabs(value){editor=value;$('editor-panel').hidden=!value;$('flight-panel').hidden=value;for(const name of ['flight','editor']){const selected=(name==='editor')===value;$('tab-'+name).classList.toggle('selected',selected);$('tab-'+name).setAttribute('aria-selected',String(selected));}if(value&&game.state==='playing')setPaused(true);refreshEditor();}
$('tab-flight').onclick=()=>tabs(false);$('tab-editor').onclick=()=>tabs(true);
function selected(){return game.scene.entities.find(e=>e.id===$('entity-select').value);}
function fillEdit(){const e=selected();if(!e)return;for(const [i,axis]of ['x','y','z'].entries())$('edit-'+axis).value=e.position[i];for(const [i,axis]of ['width','height','depth'].entries())$('edit-'+axis).value=e.scale[i];}
function refreshEditor(){const previous=$('entity-select').value;$('entity-select').replaceChildren(...game.scene.entities.filter(e=>e.id!=='ground'&&!e.id.startsWith('lane-')).map(e=>{const o=document.createElement('option');o.value=e.id;o.textContent=e.name||e.id;return o;}));if([...$('entity-select').options].some(e=>e.value===previous))$('entity-select').value=previous;fillEdit();}
$('entity-select').onchange=fillEdit;
function editing(action){try{action();refreshEditor();$('edit-message').textContent='更新しました。シーン保存で原本を書き出せます。';}catch(error){$('edit-message').textContent=error.message;}}
$('apply-edit').onclick=()=>editing(()=>{const e=selected();if(!e)throw new Error('オブジェクトがありません');const position=['x','y','z'].map(a=>Number($('edit-'+a).value)),scale=['width','height','depth'].map(a=>Number($('edit-'+a).value));if(scale.some(x=>x<1||x>100)||position.some(x=>Math.abs(x)>500))throw new Error('位置は±500m、寸法は1〜100mにしてください');game.scene.edit(e.id,{position,scale});});
$('add-box').onclick=()=>editing(()=>{const id=`edit-${crypto.randomUUID()}`;game.scene.add(box(id,[game.player.p[0]+15,5,game.player.p[2]-15],[10,10,10],[.32,.45,.39]));});
$('undo').onclick=()=>editing(()=>game.scene.undo());$('redo').onclick=()=>editing(()=>game.scene.redo());$('save-scene').onclick=()=>download('iron-field.scene.json',game.scene.save());
$('save-native').onclick=()=>editing(()=>download('iron-field.scene',savePortableScene(game.scene),'text/plain'));
$('load-scene').onchange=async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>2e6)throw new Error('シーンは2 MB以下にしてください');const text=await file.text(),scene=text.startsWith('pikapika-scene')?parsePortableScene(text):Scene.load(text);if(scene.entities.length>3000)throw new Error('ゲーム用シーンは3000物体以下にしてください');if(scene.entities.some(e=>e.yaw!==0))throw new Error('このサンプルの衝突は回転した障害物に未対応です');game.scene=scene;game.reset();game.state='playing';setPaused(true);refreshEditor();$('edit-message').textContent='読込完了。Pで試験を再開できます。';}catch(error){$('edit-message').textContent=error.message;}event.target.value='';};
function updateHud(){const p=game.player;$('hp').textContent=Math.ceil(p.hp);$('hp-bar').style.width=p.hp/10+'%';$('energy').textContent=Math.round(p.energy);$('energy-bar').style.width=p.energy+'%';$('wave').textContent=`WAVE ${String(Math.min(3,game.wave)).padStart(2,'0')} / 03`;$('objective').textContent=`残存 ${game.enemies.length} 機 / 撃破 ${game.kills}`;$('speed').textContent=`${Math.round(length(p.v)*3.6)} km/h`;$('bullets').innerHTML=`${game.projectiles.length}<small>/ 512</small>`;
const report=log.report();$('frame').innerHTML=`${report.median.toFixed(1)}<small>ms</small>`;$('cpu').innerHTML=`${lastCpu.toFixed(1)}<small>ms</small>`;
}
function marker(){const target=game.target(),el=$('target-marker');if(!target){el.hidden=true;return;}const vp=multiply(perspective(Math.PI/3,canvas.width/canvas.height,.2,1600),lookAt(camera.eye,camera.target)),p=[...target.p,1],clip=[0,0,0,0];for(let r=0;r<4;r++)for(let c=0;c<4;c++)clip[r]+=vp[c*4+r]*p[c];const x=clip[0]/clip[3],y=clip[1]/clip[3];el.hidden=clip[3]<=0||Math.abs(x)>1||Math.abs(y)>1;if(!el.hidden){el.style.left=(x*.5+.5)*100+'%';el.style.top=(-y*.5+.5)*100+'%';$('target-range').textContent=Math.round(length(sub(target.p,game.player.p)))+' m';}}
function frame(now){
  if(game.state==='error')return;
  try{
    const start=performance.now(),elapsed=lastTime?(now-lastTime)/1000:0;lastTime=now;
    if(!paused&&game.state==='playing'){
      yaw+=((keys.has('ArrowLeft')?1:0)-(keys.has('ArrowRight')?1:0))*elapsed*1.8;
      renderAlpha=clock.advance(elapsed,dt=>{
        game.step(dt,input());
        if($('stress').checked&&clock.tick%3===0&&game.projectiles.length<480){const a=game.time*8;game.fire([Math.sin(a)*80,40,Math.cos(a)*80],[Math.sin(a+.6)*80,45,Math.cos(a+.6)*80],true);}
        for(const e of game.events){const d=length(sub(e.p,game.player.p));audio.pulse(Math.max(1,d),(e.p[0]-game.player.p[0])/Math.max(20,d),e.kind==='shot'?e.friendly?150:90:65);}
      });
    }else renderAlpha=1;
    const simulationMs=performance.now()-start,p=lerp(game.player.previous,game.player.p,renderAlpha),desiredEye=[p[0]+Math.sin(yaw)*27,p[1]+14,p[2]+Math.cos(yaw)*27];
    const smooth=1-Math.exp(-Math.min(.1,elapsed)*10);camera.eye=lerp(camera.eye,desiredEye,smooth);camera.target=lerp(camera.target,[p[0]-Math.sin(yaw)*20,p[1]+4,p[2]-Math.cos(yaw)*20],smooth);
    const items=game.view(renderAlpha);renderer.render(items,camera,game.time);marker();lastCpu=performance.now()-start;
    if(elapsed>0)log.record(elapsed*1000,lastCpu,simulationMs,items.length,game.projectiles.length);
    if(frameCount++%15===0)updateHud();
    if(['victory','defeat'].includes(game.state)&&$('result').hidden){$('result-title').textContent=game.state==='victory'?'試験完了。帰投せよ。':'機体の稼働限界に到達。';$('result-copy').textContent=`撃破 ${game.kills} 機 / スコア ${game.score} / 経過 ${Math.round(game.time)} 秒`;$('result').hidden=false;$('status').textContent=game.state.toUpperCase();}
    window.__pikapika={ready:true,frameCount,game,log,renderer,clock};requestAnimationFrame(frame);
  }catch(error){fatal(error.stack||error.message);}
}
try{renderer=await Renderer.create(canvas,fatal);$('launch').disabled=false;$('launch').innerHTML='出撃する <span>→</span>';$('status').textContent='WEBGPU READY';$('capability').textContent='WebGPU 初期化済み / 音声は起動時に開始';refreshEditor();requestAnimationFrame(frame);}catch(error){fatal(error.message);}
