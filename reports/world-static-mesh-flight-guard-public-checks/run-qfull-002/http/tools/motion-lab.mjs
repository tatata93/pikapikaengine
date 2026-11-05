import {createMotionSource,defaultMotionSource,serializeMotionSource,parseMotionSource,setMotionKey,removeMotionKey,sampleMotion} from '../engine/motion.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const copy=x=>JSON.parse(JSON.stringify(x));
const number=x=>Number.isFinite(x)?Number(x).toPrecision(8):'—';
const vector=(x,n,label)=>{if(!Array.isArray(x)||x.length!==n||!x.every(Number.isFinite))throw new Error(`${label}の有限な原出力がありません`);return x;};
export function validateMotionPose(source,pose){
  if(pose?.status!=='completed'||!Array.isArray(pose.bones)||pose.bones.length!==source.bones.length||!Number.isFinite(pose.sampledTime))throw new Error(`姿勢を得られません: ${pose?.status??'出力なし'}`);
  const ids=new Set();for(const b of pose.bones){const original=source.bones.find(s=>s.id===b.id);if(!original||ids.has(b.id)||original.parentId!==b.parentId)throw new Error('姿勢の骨ID・親IDが原本と一致しません');ids.add(b.id);vector(b.worldPosition,3,'joint位置');vector(b.local?.position,3,'局所位置');vector(b.local?.rotation,4,'局所回転');vector(b.local?.scale,3,'局所scale');vector(b.localMatrix,16,'局所行列');vector(b.worldMatrix,16,'世界行列');}return pose;
}
// Uses only C++ returned joint positions. No TRS matrix or FK calculation here.
export function drawMotionPose(canvas,pose,selectedId,vertical=1){
  const ctx=canvas.getContext('2d');if(!ctx)return;const w=canvas.width,h=canvas.height,pad=45;ctx.fillStyle='#0d1824';ctx.fillRect(0,0,w,h);ctx.font='14px system-ui';ctx.fillStyle='#c7d8e9';ctx.fillText(vertical===1?'XY投影 [m]：X → / Y ↑':'XZ投影 [m]：X → / Z ↑',pad,24);
  if(!pose){ctx.fillText('有効なサンプル姿勢なし',pad,h/2);return;}
  const bones=pose.bones,map=new Map(bones.map(b=>[b.id,b])),xs=bones.map(b=>b.worldPosition[0]),ys=bones.map(b=>b.worldPosition[vertical]),cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2;
  const span=Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys),1)*1.3,scale=Math.min(w-2*pad,h-2*pad)/span;
  const point=b=>[w/2+(b.worldPosition[0]-cx)*scale,h/2-(b.worldPosition[vertical]-cy)*scale];
  for(const b of bones){const parent=map.get(b.parentId);if(!parent)continue;ctx.strokeStyle=b.id===selectedId?'#ffbf75':'#7ee1d1';ctx.lineWidth=b.id===selectedId?5:3;ctx.beginPath();ctx.moveTo(...point(parent));ctx.lineTo(...point(b));ctx.stroke();}
  for(const b of bones){const [x,y]=point(b);ctx.fillStyle=b.id===selectedId?'#ffbf75':'#a9baff';ctx.beginPath();ctx.arc(x,y,6,0,2*Math.PI);ctx.fill();ctx.fillText(String(b.id),x+9,y-9);}
  ctx.fillStyle='#c7d8e9';ctx.fillText(`中心 [${number(cx)}, ${number(cy)}] m / 表示幅 ${number(span)} m`,pad,h-15);
}
const friendly=e=>/API unavailable|rebuild|matching WebAssembly/i.test(e?.message??'')?'この制作ラボに対応する同梱WASMがありません。配信更新後に計算核を再読込してください。':e?.message??String(e);
function downloadJson(name,text){const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),0);}
export async function initializeMotionLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,sample=sampleMotion,requestFrame=cb=>requestAnimationFrame(cb),cancelFrame=id=>cancelAnimationFrame(id),saveJson=downloadJson}={}){
  const get=id=>doc.getElementById(id),editFields=['mo-key-time','mo-px','mo-py','mo-pz','mo-qx','mo-qy','mo-qz','mo-qw','mo-sx','mo-sy','mo-sz'];
  let source=createMotionSource(defaultMotionSource()),pose=null,runtime=null,loading=false,playing=false,pendingEdit=false,frameId=null,anchorTimestamp=null,anchorTime=0,requestedTime=0,selectedId=source.bones.some(b=>b.id===2)?2:source.bones[0].id;
  const undo=[],redo=[];
  const option=(value,label)=>{const o=doc.createElement('option');o.value=String(value);o.textContent=label;return o;};
  const error=e=>{get('mo-error').hidden=!e;get('mo-error').textContent=e?friendly(e):'';};
  const lock=()=>{get('mo-editor').disabled=loading;get('mo-files').disabled=loading;get('mo-playback').disabled=loading||!runtime||pendingEdit;get('mo-retry').disabled=loading;get('mo-play').disabled=playing||!runtime||pendingEdit;get('mo-pause').disabled=!playing;get('mo-undo').disabled=loading||!undo.length;get('mo-redo').disabled=loading||!redo.length;get('mo-edit-state').textContent=pendingEdit?'未適用のキー編集あり。適用または編集を戻してください。':'適用済み原本';};
  const history=()=>{get('mo-history').textContent=`Undo ${undo.length} / Redo ${redo.length}`;lock();};
  const stop=()=>{playing=false;if(frameId!==null)cancelFrame(frameId);frameId=null;anchorTimestamp=null;lock();};
  const clearPose=()=>{pose=null;get('mo-bones').replaceChildren();get('mo-pose-json').textContent='姿勢なし';get('mo-clock').textContent='姿勢なし';drawMotionPose(get('mo-xy'),null,selectedId,1);drawMotionPose(get('mo-xz'),null,selectedId,2);};
  const renderSource=()=>{get('mo-source-json').textContent=serializeMotionSource(source);get('mo-scrub').max=String(source.clip.duration);get('mo-key-time').max=String(source.clip.duration);history();};
  const renderPose=()=>{
    get('mo-bones').replaceChildren();const names=new Map(source.bones.map(b=>[b.id,b.name]));for(const b of pose.bones){const tr=doc.createElement('tr');for(const text of [`${b.id} / ${b.parentId}`,names.get(b.id),b.worldPosition.map(number).join(', '),`p [${b.local.position.map(number).join(', ')}]\nq [${b.local.rotation.map(number).join(', ')}]\ns [${b.local.scale.map(number).join(', ')}]`]){const td=doc.createElement('td');td.textContent=text;tr.appendChild(td);}get('mo-bones').appendChild(tr);}
    get('mo-clock').textContent=`照会 ${number(pose.requestedTime)} s → sample ${number(pose.sampledTime)} s / ${pose.playback} / clip ${number(pose.duration)} s（物理時計ではありません）`;
    get('mo-time').value=String(requestedTime);get('mo-scrub').value=String(pose.sampledTime);get('mo-pose-json').textContent=JSON.stringify(pose,null,2);drawMotionPose(get('mo-xy'),pose,selectedId,1);drawMotionPose(get('mo-xz'),pose,selectedId,2);
  };
  const resample=(time=requestedTime)=>{
    if(loading||!runtime||pendingEdit)return null;try{if(typeof time!=='number'||!Number.isFinite(time))throw new Error('絶対時刻は有限の秒数で指定してください');requestedTime=time;const next=sample(runtime,source,time,{loop:Boolean(get('mo-loop').checked)});validateMotionPose(source,next);pose=next;renderPose();error(null);get('mo-status').textContent='共通C++から姿勢を得ました。';return copy(pose);}
    catch(e){stop();clearPose();error(e);get('mo-status').textContent='姿勢照会に失敗。古い姿勢を消去しました。';return null;}
  };
  const fillEditor=()=>{
    const bone=source.bones.find(b=>b.id===selectedId),track=source.clip.tracks.find(t=>t.boneId===selectedId),key=track?.keys?.[Number(get('mo-key').value)],trs=key??bone.rest;
    get('mo-key-time').value=String(key?.time??pose?.sampledTime??0);for(const [prefix,values]of [['p',trs.position],['q',trs.rotation],['s',trs.scale]])['x','y','z','w'].slice(0,values.length).forEach((axis,i)=>{get('mo-'+prefix+axis).value=String(values[i]);});
    get('mo-track').textContent=track?`${track.interpolation} / 保存キー ${track.keys.length}個。局所TRSを編集。`:'trackなし：restから新しいキーを作成。';pendingEdit=false;lock();
  };
  const selections=(preferredTime=null)=>{
    if(!source.bones.some(b=>b.id===selectedId))selectedId=source.bones[0].id;get('mo-bone').replaceChildren(...source.bones.map(b=>option(b.id,`${b.id}: ${b.name}（親 ${b.parentId}）`)));get('mo-bone').value=String(selectedId);
    const track=source.clip.tracks.find(t=>t.boneId===selectedId),keys=track?.keys??[];get('mo-key').replaceChildren(...keys.map((k,i)=>option(i,`t=${number(k.time)} s`)),option('rest','restから新しいキー'));
    const match=preferredTime===null?-1:keys.findIndex(k=>k.time===preferredTime);get('mo-key').value=match>=0?String(match):keys.length?'0':'rest';fillEditor();
  };
  const commit=(next,preferredTime=null)=>{
    stop();const valid=createMotionSource(next),before=serializeMotionSource(source),after=serializeMotionSource(valid);if(before!==after){undo.push(before);if(undo.length>32)undo.shift();redo.length=0;}source=valid;pendingEdit=false;renderSource();selections(preferredTime);clearPose();error(null);resample();return copy(source);
  };
  const numeric=id=>{const s=String(get(id).value).trim();if(!s||!Number.isFinite(Number(s)))throw new Error('空欄でない有限の数値を指定してください: '+id);return Number(s);};
  const apply=()=>{if(loading)return null;stop();try{const time=numeric('mo-key-time'),read=(p,n)=>['x','y','z','w'].slice(0,n).map(a=>numeric('mo-'+p+a));return commit(setMotionKey(source,{boneId:selectedId,time,position:read('p',3),rotation:read('q',4),scale:read('s',3)}),time);}catch(e){clearPose();error(e);get('mo-status').textContent='キーを適用できませんでした。原本は保持しています。';return null;}};
  const remove=()=>{if(loading)return null;stop();try{return commit(removeMotionKey(source,selectedId,numeric('mo-key-time')));}catch(e){clearPose();error(e);return null;}};
  const travel=direction=>{
    if(loading)return false;stop();const from=direction==='undo'?undo:redo,to=direction==='undo'?redo:undo;if(!from.length)return false;const restored=parseMotionSource(from.at(-1));to.push(serializeMotionSource(source));from.pop();source=restored;pendingEdit=false;renderSource();selections();clearPose();error(null);resample();return true;
  };
  const tick=timestamp=>{
    frameId=null;if(!playing)return;if(doc.hidden){stop();return;}if(anchorTimestamp===null)anchorTimestamp=timestamp;
    const target=anchorTime+(timestamp-anchorTimestamp)/1000,result=resample(target);if(!result){stop();return;}if(!get('mo-loop').checked&&target>=source.clip.duration){requestedTime=source.clip.duration;get('mo-time').value=String(requestedTime);stop();return;}frameId=requestFrame(tick);
  };
  const play=()=>{if(loading||!runtime||pendingEdit||playing)return false;if(!get('mo-loop').checked&&requestedTime>=source.clip.duration)requestedTime=0;anchorTime=requestedTime;anchorTimestamp=null;playing=true;error(null);lock();frameId=requestFrame(tick);return true;};
  const retry=async()=>{if(loading)return;stop();runtime=null;loading=true;clearPose();error(null);lock();get('mo-status').textContent='共通計算核を読込み中…';try{runtime=await loadRuntime();get('runtime-info').textContent=JSON.stringify(runtime?.diagnostics??{});get('mo-status').textContent=pendingEdit?'計算核を読込みました。未適用のキー編集を適用または戻してください。':'計算核を読込みました。';}catch(e){error(e);get('runtime-info').textContent='計算核なし（代替FKなし）';get('mo-status').textContent='計算核を読込めません。再読込で復帰できます。';}finally{loading=false;lock();}if(runtime)resample();};
  const loadSource=async text=>{if(loading)return false;stop();clearPose();try{const next=parseMotionSource(text);commit(next);get('mo-status').textContent='原本を読込みました。停止したまま姿勢を照会しました。';return true;}catch(e){error(e);get('mo-status').textContent='原本を読込めませんでした。古い姿勢を消去しました。';return false;}};
  editFields.forEach(id=>get(id).addEventListener('input',()=>{if(loading)return;stop();pendingEdit=true;clearPose();error(null);lock();get('mo-status').textContent='キーの編集は未適用です。適用または編集を戻してください。';}));
  get('mo-bone').addEventListener('change',()=>{if(loading)return;stop();selectedId=Number(get('mo-bone').value);selections();resample();});get('mo-key').addEventListener('change',()=>{if(loading)return;stop();fillEditor();error(null);resample();});
  get('mo-apply').addEventListener('click',apply);get('mo-remove').addEventListener('click',remove);get('mo-cancel-edit').addEventListener('click',()=>{if(loading)return;stop();fillEditor();error(null);resample();});
  get('mo-undo').addEventListener('click',()=>travel('undo'));get('mo-redo').addEventListener('click',()=>travel('redo'));get('mo-reset').addEventListener('click',()=>{if(!loading){requestedTime=0;commit(defaultMotionSource());}});
  const seek=id=>{if(loading)return;stop();try{resample(numeric(id));}catch(e){clearPose();error(e);}};get('mo-scrub').addEventListener('input',()=>seek('mo-scrub'));get('mo-time').addEventListener('input',()=>seek('mo-time'));get('mo-loop').addEventListener('change',()=>{stop();resample();});
  get('mo-play').addEventListener('click',play);get('mo-pause').addEventListener('click',stop);get('mo-step').addEventListener('click',()=>{stop();resample(requestedTime+1/120);});get('mo-retry').addEventListener('click',retry);doc.addEventListener?.('visibilitychange',()=>{if(doc.hidden)stop();});
  get('mo-save').addEventListener('click',()=>{if(!loading)saveJson('pikapika-motion.json',serializeMotionSource(source));});get('mo-load').addEventListener('change',async()=>{const file=get('mo-load').files?.[0];if(!file||loading)return;stop();try{if(file.size>8*1024*1024)throw new Error('motion JSONは8MiB以下にしてください');await loadSource(await file.text());}catch(e){clearPose();error(e);}finally{get('mo-load').value='';}});
  get('mo-time').value='0';get('mo-loop').checked=false;renderSource();selections();clearPose();await retry();return {play,pause:stop,apply,remove,retry,loadSource,undo:()=>travel('undo'),redo:()=>travel('redo'),resample,getState:()=>({source:copy(source),pose:pose?copy(pose):null,playing,pendingEdit,requestedTime,selectedId,undo:undo.length,redo:redo.length})};
}
if(typeof document!=='undefined')initializeMotionLab().catch(e=>{const n=document.getElementById('mo-error');if(n){n.hidden=false;n.textContent=friendly(e);}});
