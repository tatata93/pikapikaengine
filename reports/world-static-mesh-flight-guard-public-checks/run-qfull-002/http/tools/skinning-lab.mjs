import {loadSimulationRuntime} from '../engine/simulation.mjs';
const copy=x=>structuredClone(x);
const identity=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const trs=(position=[0,0,0],rotation=[0,0,0,1],scale=[1,1,1])=>({position,rotation,scale});
const numeric=(value,label)=>{if(typeof value!=='number'||!Number.isFinite(value))throw new Error(label+' は有限の数値が必要です');return value;};
const display=x=>Number(x).toPrecision(8);
export function makeSkinningCase(kind,time=1,rootWeight=1,childWeight=1){
 numeric(time,'時刻');numeric(rootWeight,'骨7のweight');numeric(childWeight,'骨19のweight');
 if(!['arm','shear','cancellation','underflow'].includes(kind))throw new Error('未対応の例です');
 if(kind==='cancellation'||kind==='underflow'){
  const a=identity(),b=identity();if(kind==='cancellation'){a[12]=2**53;b[12]=-(2**53);}
  return {kind,time:null,rest:[{id:7,matrix:identity()},{id:19,matrix:identity()}],pose:[{id:19,matrix:b},{id:7,matrix:a}],vertices:[{position:[1,0,0],influences:[{id:19,weight:childWeight},{id:7,weight:rootWeight}]}],triangles:[]};
 }
 const stretch=kind==='shear'?2:1,bones=[{id:19,parentId:7,rest:trs([1,0,0])},{id:7,parentId:0,rest:trs([0,0,0],[0,0,0,1],[stretch,1,1])}],rotation=kind==='shear'?[0,0,1,2]:[0,0,1,1];
 const key=(time,q)=>({time,...trs([1,0,0],q)}),motion={bones,clip:{duration:2,tracks:[{boneId:19,interpolation:'linear',keys:[key(0,[0,0,0,1]),key(1,rotation),key(2,[0,0,0,1])]}]}};
 const positions=[[0,-.2,0],[stretch,-.2,0],[2*stretch,-.2,0],[0,.2,0],[stretch,.2,0],[2*stretch,.2,0]];
 return {kind,time,motion,vertices:positions.map((position,j)=>({position,influences:j%3===0?[{id:7,weight:1}]:j%3===2?[{id:19,weight:1}]:[{id:19,weight:childWeight},{id:7,weight:rootWeight}]})),triangles:[[0,1,4],[0,4,3],[1,2,5],[1,5,4]]};
}
export function runSkinningCase(runtime,input,settings={}){
 for(const method of ['bindSkin','deformSkin'])if(typeof runtime?.[method]!=='function')throw new Error('同梱のskin SDKを再読込してください');
 const source=copy(input);let rest=source.rest,pose=source.pose;
 if(source.motion){
  const original=runtime.sampleMotion({bones:source.motion.bones,clip:{duration:2,tracks:[]}},0),sample=runtime.sampleMotion(source.motion,source.time);
  if(original.status!=='completed'||sample.status!=='completed')throw new Error('共通C++ motionから姿勢を得られません: '+sample.status);
  rest=original.bones.map(b=>({id:b.id,matrix:b.worldMatrix}));pose=sample.bones.map(b=>({id:b.id,matrix:b.worldMatrix}));
 }
 const binding=runtime.bindSkin(rest,settings),deformation=binding.status==='completed'?runtime.deformSkin({joints:binding.joints,pose,vertices:source.vertices},settings):null;
 if(deformation?.status==='completed'){
  if(!Array.isArray(deformation.positions)||deformation.positions.length!==source.vertices.length||deformation.positions.some(p=>!Array.isArray(p)||p.length!==3||!p.every(Number.isFinite)))throw new Error('C++の変形位置が欠損/非有限です');
 }
 return {schema:1,source,input:{rest,joints:binding.joints,pose,vertices:source.vertices,settings:copy(settings)},binding,deformation};
}
// View projection only. Inverse binds, matrix blending and FK are common C++ calls.
export function drawSkinning(canvas,packet,vertical=1){
 const ctx=canvas.getContext('2d');if(!ctx)return;const width=canvas.width,height=canvas.height,pad=42;
 ctx.fillStyle='#0d1824';ctx.fillRect(0,0,width,height);ctx.font='14px system-ui';ctx.fillStyle='#c7d8e9';ctx.fillText(vertical===1?'XY投影 [m] : X → / Y ↑':'XZ投影 [m] : X → / Z ↑',pad,24);
 if(packet?.deformation?.status!=='completed'){ctx.fillText('有効な変形位置なし',pad,height/2);return;}
 const original=packet.source.vertices.map(v=>v.position),deformed=packet.deformation.positions,all=[...original,...deformed],xs=all.map(p=>p[0]),ys=all.map(p=>p[vertical]);
 const cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2,span=Math.max(1,Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys))*1.3,scale=Math.min(width-2*pad,height-2*pad)/span;
 const project=p=>[width/2+(p[0]-cx)*scale,height/2-(p[vertical]-cy)*scale];
 function shape(points,color,dashed){ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=dashed?1:2;ctx.setLineDash(dashed?[5,5]:[]);for(const t of packet.source.triangles){ctx.beginPath();ctx.moveTo(...project(points[t[0]]));ctx.lineTo(...project(points[t[1]]));ctx.lineTo(...project(points[t[2]]));ctx.closePath();ctx.stroke();}ctx.setLineDash([]);for(const [j,p]of points.entries()){const xy=project(p);ctx.beginPath();ctx.arc(...xy,dashed?3:5,0,2*Math.PI);ctx.fill();if(!dashed)ctx.fillText(String(j),xy[0]+7,xy[1]-7);}}
 shape(original,'#7892a5',true);shape(deformed,'#7ee1d1',false);ctx.fillStyle='#c7d8e9';ctx.fillText('灰: 原本 / 緑: C++変形位置（番号は頂点index）',pad,height-15);
}
export async function initializeSkinningLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,saveJson}={}){
 const get=id=>doc.getElementById(id),elements=Object.fromEntries(['example','time','root','child','condition','run','retry','save','status','error','stats','rows','json','xy','xz'].map(k=>[k,get('sk-'+k)]));let runtime=null,packet=null,loading=false;
 const save=saveJson??((name,text)=>{const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=doc.createElement('a');a.href=url;a.download=name;doc.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);});
 function clear(message='入力が変わりました。計算するボタンで更新してください。'){
  packet=null;elements.status.textContent=message;elements.error.hidden=true;elements.error.textContent='';elements.stats.textContent='変形位置なし';elements.rows.replaceChildren();elements.json.textContent='未実行';elements.save.disabled=true;drawSkinning(elements.xy,null,1);drawSkinning(elements.xz,null,2);
 }
 const value=(element,label)=>{const text=element.value.trim();if(text==='')throw new Error(label+' が空です');const n=numeric(Number(text),label);if(n===0&&/[1-9]/.test(text.split(/[eE]/)[0]))throw new Error(label+' は数値化でunderflowしました');return n;};
 function query(){
  clear('共通C++へ照会中…');try{
   if(!runtime)throw new Error('計算核を再読込してください');
   const input=makeSkinningCase(elements.example.value,value(elements.time,'時刻'),value(elements.root,'骨7のweight'),value(elements.child,'骨19のweight')),settings={maximumCondition:value(elements.condition,'condition上限')};
   packet=runSkinningCase(runtime,input,settings);elements.json.textContent=JSON.stringify(packet,null,2);elements.save.disabled=false;
   const result=packet.deformation;if(!result||result.status!=='completed'){
    const status=result?.status??packet.binding.status;elements.status.textContent='変形位置を返しません: '+status;elements.error.textContent='原本は保持しています。診断と入力は下のJSONで確認できます。';elements.error.hidden=false;return packet;
   }
   elements.status.textContent='共通C++の位置変形が完了しました。';elements.stats.textContent=`${result.positions.length}頂点 / ${input.triangles.length}三角形 / bind ${packet.binding.status} / deform ${result.status}`;
   for(const [j,p]of result.positions.entries()){const row=doc.createElement('tr');for(const text of [j,input.vertices[j].position.map(display).join(', '),input.vertices[j].influences.map(w=>w.id+': '+String(w.weight)).join(' / '),p.map(display).join(', ')]){const td=doc.createElement('td');td.textContent=String(text);row.appendChild(td);}elements.rows.appendChild(row);}
   drawSkinning(elements.xy,packet,1);drawSkinning(elements.xz,packet,2);return packet;
  }catch(error){clear('姿勢を計算できませんでした。');elements.error.textContent=/Skinning WASM API unavailable/.test(error.message)?'同梱のskin SDKを再読込してください。':error.message;elements.error.hidden=false;return null;}
 }
 function example(){const name=elements.example.value,staticCase=['cancellation','underflow'].includes(name);elements.time.value=staticCase?'0':'1';elements.time.disabled=staticCase;elements.root.value=name==='underflow'?String(Number.MIN_VALUE):'1';elements.child.value=name==='underflow'?String(Number.MAX_VALUE):'1';elements.condition.value='1e10';clear();}
 async function retry(){if(loading)return;loading=true;elements.retry.disabled=true;elements.run.disabled=true;clear('共通計算核を読込み中…');try{runtime=await loadRuntime();get('runtime-info').textContent=JSON.stringify(runtime.diagnostics??{});query();}catch(error){runtime=null;elements.error.textContent=error.message;elements.error.hidden=false;elements.status.textContent='計算核を利用できません。';}finally{loading=false;elements.retry.disabled=false;elements.run.disabled=!runtime;}}
 elements.example.addEventListener('change',example);for(const k of ['time','root','child','condition'])elements[k].addEventListener('input',()=>clear());elements.run.addEventListener('click',query);elements.retry.addEventListener('click',retry);elements.save.addEventListener('click',()=>{if(packet)save('pikapika-skinning-query.json',JSON.stringify(packet,null,2)+'\n');});
 example();await retry();return {query,retry,getState:()=>({packet:packet?copy(packet):null,available:Boolean(runtime),loading})};
}
if(typeof document!=='undefined'&&document.getElementById('sk-run'))initializeSkinningLab();
