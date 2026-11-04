import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {parseSkinBindingSource,serializeSkinBindingSource,parseSkinBindingPortable,serializeSkinBindingPortable,
 setSkinWeight,validateSkinBindingContext,evaluateSkinBinding,defaultSkinBindingSource} from '../engine/skin-binding.mjs';
import {drawSkinning} from './skinning-lab.mjs';
import {Renderer} from '../engine/renderer.mjs';
import {createDerivedMeshRenderData} from '../engine/derived-render.mjs';

const numeric=(text,label)=>{const value=parseStrictJson(text.trim());if(typeof value!=='number')throw new Error(label+'は有限の数値が必要です');return value;};
const clone=value=>structuredClone(value);
const plain=value=>ArrayBuffer.isView(value)?Array.from(value):Array.isArray(value)?value.map(plain):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([key,item])=>[key,plain(item)])):value;
export async function initializeSkinBindingLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,saveFile,createRenderer=(canvas,onError)=>Renderer.create(canvas,onError)}={}){
 const get=id=>doc.getElementById('sb-'+id),ui=Object.fromEntries(['input','file','apply','default','retry','run','time','loop','vertex','bone','weight','edit','save-json','save-portable','scene','match','clear-scene','status','error','summary','json','portable','result','rows','xy','xz','runtime','prepare','derived-budget','derived-status','derived-result','3d','show-3d','gpu-status','view'].map(id=>[id,get(id)]));
 let runtime=null,source=null,packet=null,derived=null,scene=null,dirty=false,loading=false,revision=0;
 let renderer=null,gpuLoading=false,gpuEpoch=0;
 const camera=()=>({eye:ui.view.value==='front'?[1,.35,4]:ui.view.value==='back'?[1,.35,-4]:[3,2,4],target:[1,.35,0]});
 function dropRenderer(){const previous=renderer;renderer=null;try{previous?.dispose();}catch{}ui['3d'].hidden=true;}
 function gpuFailure(message){++gpuEpoch;dropRenderer();ui['gpu-status'].textContent='3D表示を利用できません: '+message+'。数値監査と原本保存は利用できます。';buttons();}
 function clearPreview(message='3D表示は未実行です。'){
  ++gpuEpoch;ui['3d'].hidden=true;ui['gpu-status'].textContent=message;
  try{renderer?.render([],camera());}catch(e){gpuFailure(e?.message??String(e));}
 }
 async function show3D(){
  if(gpuLoading)return false;
  if(!derived||derived.status!=='completed'||dirty){clearPreview('先にFloat32監査を完了してください。');return false;}
  const ownEpoch=++gpuEpoch,ownDerived=derived;gpuLoading=true;ui['gpu-status'].textContent='監査済みbufferを3D表示へ準備中…';buttons();
  try{
   const data=createDerivedMeshRenderData(ownDerived);
   if(!renderer){let candidate=null;candidate=await createRenderer(ui['3d'],message=>{if(candidate===renderer)gpuFailure(message);});if(ownEpoch!==gpuEpoch){candidate.dispose();return false;}renderer=candidate;}
   ui['3d'].hidden=false;
   await renderer.renderChecked([{id:'skin-binding-preview',type:'derived-mesh',mesh:data,position:[0,0,0],scale:[1,1,1],color:[.20,.78,.67]}],camera());
   if(ownEpoch!==gpuEpoch||derived!==ownDerived)return false;
   ui['gpu-status'].textContent=`WebGPU表示を完了しました。${data.triangleCount}面 / ${data.floatCount*4} bytes。原本・数値監査は変更していません。`;return true;
  }catch(e){if(ownEpoch===gpuEpoch)gpuFailure(e?.message??String(e));return false;}
  finally{gpuLoading=false;buttons();}
 }
 const save=saveFile??((name,text,type)=>{const a=doc.createElement('a'),url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;doc.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),0);});
 function buttons(){const ready=source&&!dirty;ui['save-json'].disabled=ui['save-portable'].disabled=ui.edit.disabled=ui.match.disabled=!ready;ui.run.disabled=!ready||!runtime;ui.default.disabled=!runtime;ui.retry.disabled=loading;ui.prepare.disabled=!ready||!runtime||packet?.deformation.status!=='completed';ui['show-3d'].disabled=gpuLoading||!ready||derived?.status!=='completed';}
 function clearDerived(message='派生メッシュは未実行です。'){derived=null;clearPreview();ui['derived-status'].textContent=message;ui['derived-result'].textContent='未実行';}
 function clear(message){packet=null;clearDerived();ui.status.textContent=message;ui.error.hidden=true;ui.error.textContent='';ui.summary.textContent='有効な変形位置なし';ui.result.textContent='未実行';ui.rows.replaceChildren();drawSkinning(ui.xy,null,1);drawSkinning(ui.xz,null,2);buttons();}
 function error(e){clear('位置を表示できません。');ui.error.textContent=e?.message??String(e);ui.error.hidden=false;}
 function publish(candidate,text){source=candidate;dirty=false;ui.input.value=text??serializeSkinBindingSource(source);ui.json.textContent=serializeSkinBindingSource(source);ui.portable.textContent=serializeSkinBindingPortable(source);buttons();}
 function query(){
  clear('共通C++へ照会中…');
  try{
   if(!runtime||!source||dirty)throw new Error('原本を読み込み、共通計算核を利用可能にしてください。');
   if(scene===null&&ui.scene.value.trim())throw new Error('入力されたSceneを先に照合するか、単体照会へ戻してください。');
   const result=evaluateSkinBinding(runtime,source,numeric(ui.time.value,'時刻'),{loop:ui.loop.checked,scene:scene??undefined});
   packet={source:clone(source),sceneMatched:scene!==null,...result};
   ui.result.textContent=stringifyStrictJson(packet,{maxBytes:16*1024*1024,maxNodes:2000000});
   const deformation=result.deformation;
   if(deformation.status!=='completed'){ui.status.textContent='原本は保存できます。位置計算: '+deformation.status;ui.error.textContent='C++が変形位置を返していません。原本の数値を修正して再計算してください。';ui.error.hidden=false;return packet;}
   if(deformation.positions?.length!==source.mesh.positions.length||deformation.positions.some(p=>!Array.isArray(p)||p.length!==3||!p.every(Number.isFinite)))throw new Error('共通C++の変形位置が欠損/非有限です。');
   const drawing={source:{vertices:source.mesh.positions.map((position,i)=>({position,influences:source.influences[i].map(w=>({id:w.boneId,weight:w.weight}))})),triangles:source.mesh.triangles},deformation};
   drawSkinning(ui.xy,drawing,1);drawSkinning(ui.xz,drawing,2);
   for(let i=0;i<Math.min(32,deformation.positions.length);++i){const row=doc.createElement('tr');for(const text of [String(i),source.influences[i].map(w=>`${w.boneId}: ${Object.is(w.weight,-0)?'-0':w.weight}`).join(' / '),deformation.positions[i].map(v=>v.toPrecision(8)).join(', ')]){const td=doc.createElement('td');td.textContent=text;row.appendChild(td);}ui.rows.appendChild(row);}
   ui.summary.textContent=`${source.mesh.positions.length}頂点 / ${source.motion.bones.length}骨 / fingerprint ${source.fingerprint} / ${scene?'Scene照合済み':'Scene未指定の単体照会'}`;
   ui.status.textContent='共通C++の位置計算が完了しました。';buttons();return packet;
  }catch(e){error(e);return null;}
 }
 function prepare(){
  clearDerived('Float32位置と法線を共通C++で監査中…');
  try{
   if(!runtime||!source||dirty||packet?.deformation.status!=='completed')throw new Error('先に位置計算を完了してください。');
   if(typeof runtime.prepareDerivedMesh!=='function')throw new Error('この計算核は派生メッシュ照会に対応していません。計算核を再読込してください。');
   const settings={sqrtRefinements:numeric(ui['derived-budget'].value,'sqrt予算')};
   const result=runtime.prepareDerivedMesh({positions:packet.deformation.positions,triangles:source.mesh.triangles},settings),g=result.geometry;
   if(result.status==='completed'&&(!g||g.positions.length!==packet.deformation.positions.length||g.triangles.length!==source.mesh.triangles.length))throw new Error('共通C++の派生geometryが欠損しています。');
   const preview={...result,geometry:g?{...g,positions:g.positions.slice(0,32),triangles:g.triangles.slice(0,32),interleaved:g.interleaved.slice(0,32*18)}:null,audits:result.audits.slice(0,32)};
   ui['derived-result'].textContent=stringifyStrictJson(plain({settings,input:{sourceFingerprint:source.fingerprint,seconds:numeric(ui.time.value,'時刻'),loop:ui.loop.checked,vertices:packet.deformation.positions.length,triangles:source.mesh.triangles.length},display:{firstVertices:32,firstFaces:32,totalVertices:g?.positions.length??0,totalFaces:g?.triangles.length??0,totalFloats:g?.interleaved.length??0,totalAudits:result.audits.length},result:preview}),{maxBytes:2*1024*1024,maxNodes:200000});
   derived=result;ui['derived-status'].textContent=result.status==='completed'?`Float32監査が完了しました。全${g.triangles.length}面 / ${g.interleaved.length} floats。原本は変更していません。`:`位置計算は完了しています。派生監査: ${result.status} / ${result.reason}。描画用geometryはありません。`;return result;
  }catch(e){clearDerived('派生監査を実行できません: '+(e?.message??String(e)));return null;}
  finally{buttons();}
 }
 function readText(text=ui.input.value){
  ++revision;dirty=true;ui.input.value=text;clear('原本を検査中…');
  try{const candidate=text.trimStart().startsWith('pikapika_skin')?parseSkinBindingPortable(text):parseSkinBindingSource(text);publish(candidate,text);query();return true;}catch(e){error(e);return false;}
 }
 async function readFile(){
  const file=ui.file.files?.[0];if(!file)return false;const ownRevision=++revision;dirty=true;clear('原本ファイルを読込み中…');
  try{if(file.size>8388608)throw new Error('原本ファイルの上限はUTF-8 8MiBです。');const bytes=await file.arrayBuffer();if(ownRevision!==revision)return false;if(bytes.byteLength>8388608)throw new Error('原本ファイルの上限はUTF-8 8MiBです。');const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);if(ownRevision!==revision)return false;ui.input.value=text;return readText(text);}catch(e){if(ownRevision===revision)error(e);return false;}
 }
 function edit(){
  ++revision;clear('author weightを検査中…');try{if(!source||dirty)throw new Error('先に入力した原本を読み込んでください。');const next=setSkinWeight(source,numeric(ui.vertex.value,'頂点index'),numeric(ui.bone.value,'骨ID'),numeric(ui.weight.value,'weight'));publish(next);query();return true;}catch(e){error(e);return false;}
 }
 function match(){
  ++revision;scene=null;clear('Scene原本を照合中…');try{if(!source||dirty)throw new Error('先に原本を読み込んでください。');const candidate=parseStrictJson(ui.scene.value);validateSkinBindingContext(source,candidate);scene=candidate;query();return true;}catch(e){error(e);return false;}
 }
 function reset(){++revision;try{if(!runtime)throw new Error('共通計算核を読み込んでください。');const candidate=defaultSkinBindingSource(runtime);scene=null;ui.scene.value='';ui.time.value='1';ui.loop.checked=false;ui.vertex.value='1';ui.bone.value='19';ui.weight.value='1';ui['derived-budget'].value='128';publish(candidate);query();return true;}catch(e){error(e);return false;}}
 async function retry(){if(loading)return;loading=true;clear('共通計算核を読込み中…');try{runtime=await loadRuntime();ui.runtime.textContent=stringifyStrictJson(runtime.diagnostics??{});if(!source&&!ui.input.value.trim())reset();else if(source&&!dirty)query();else clear('原本を読むボタンで入力を検査してください。');}catch(e){runtime=null;error(e);}finally{loading=false;buttons();}}
 ui.input.addEventListener('input',()=>{++revision;dirty=true;ui.json.textContent=ui.portable.textContent='入力はまだ適用していません';clear('入力が変わりました。原本を読むボタンで検査してください。');});
 ui.scene.addEventListener('input',()=>{++revision;scene=null;clear('Scene入力が変わりました。照合するか、単体照会へ戻してください。');});
 for(const id of ['time','loop'])ui[id].addEventListener(id==='loop'?'change':'input',()=>clear('時刻設定が変わりました。位置を計算するボタンで更新してください。'));
 ui.prepare.addEventListener('click',prepare);ui['derived-budget'].addEventListener('input',()=>{clearDerived('予算が変わりました。Float32監査を実行してください。');buttons();});
 ui['show-3d'].addEventListener('click',show3D);ui.view.addEventListener('change',()=>{if(gpuLoading)clearPreview('視点が変わりました。3D表示ボタンで更新してください。');else if(!ui['3d'].hidden)void show3D();});
 ui.apply.addEventListener('click',()=>readText());ui.file.addEventListener('change',readFile);ui.default.addEventListener('click',reset);ui.retry.addEventListener('click',retry);ui.run.addEventListener('click',query);ui.edit.addEventListener('click',edit);ui.match.addEventListener('click',match);
 ui['clear-scene'].addEventListener('click',()=>{++revision;scene=null;ui.scene.value='';clear('Scene未指定の単体照会です。位置を計算するボタンで更新してください。');});
 ui['save-json'].addEventListener('click',()=>{if(source&&!dirty)save('pikapika-skin-binding.json',serializeSkinBindingSource(source),'application/json');});
 ui['save-portable'].addEventListener('click',()=>{if(source&&!dirty)save('pikapika-skin-binding.skin',serializeSkinBindingPortable(source),'text/plain;charset=utf-8');});
 const dispose=()=>{++gpuEpoch;dropRenderer();ui['gpu-status'].textContent='3D表示のGPU資源を解放しました。';buttons();};
 doc.defaultView?.addEventListener('pagehide',dispose);
 if(!ui.time.value)ui.time.value='1';if(!ui.view.value)ui.view.value='oblique';clear('共通計算核を読込み中…');await retry();
 return {readText,readFile,query,prepare,show3D,dispose,edit,match,retry,reset,getState:()=>({source:source?clone(source):null,packet:packet?clone(packet):null,derived:derived?clone(derived):null,preview:{available:Boolean(renderer),visible:!ui['3d'].hidden,loading:gpuLoading},scene:scene?clone(scene):null,dirty,available:Boolean(runtime),revision})};
}
if(typeof document!=='undefined'&&document.getElementById('sb-run'))initializeSkinBindingLab();
