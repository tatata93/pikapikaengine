import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';
import {flightLabPresetData} from './sphere-triangle-mesh-flight-presets.mjs';

const inputBudget={maxBytes:131072,maxDepth:16,maxNodes:24000};
const outputBudget={maxBytes:8388608,maxDepth:32,maxNodes:1000000};
const axesByProjection={xy:[0,1],xz:[0,2],yz:[1,2]};
const primitiveDefaults={maxCandidates:7,sqrtRefinements:128,maxTotalSqrtRefinements:1024,maximumLocalWidth:1e-7,maximumNormalWidth:1e-8,minimumSineSquared:1e-12};
const heldDefaults={timeTolerance:1e-7,maxEvaluations:256,maxLeaves:128,maxDepth:24,enclosureSqrtRefinements:128,maxTotalSqrtRefinements:1000000};
const own=value=>parseStrictJson(stringifyStrictJson(value,outputBudget),outputBudget);
const text=value=>stringifyStrictJson(value);
const readable=(value,depth=0)=>Array.isArray(value)?'['+value.map(v=>readable(v,depth)).join(', ')+']':value&&typeof value==='object'?'{\n'+Object.entries(value).map(([k,v])=>'  '.repeat(depth+1)+JSON.stringify(k)+': '+readable(v,depth+1)).join(',\n')+'\n'+'  '.repeat(depth)+'}':text(value);
const html=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const heldResult=(source,result)=>source.mode==='held'?result:result.inflated;
export const flightLabPresets=Object.freeze(flightLabPresetData.map(({name,label,cohort,fixtureName,mode})=>Object.freeze({name,label,cohort,fixtureName,mode})));
export function flightLabPreset(name=flightLabPresets[0]?.name){
 const preset=flightLabPresetData.find(p=>p.name===name);
 if(!preset)throw new Error('Unknown flight preset: '+name);
 return own(preset.input);
}
function keys(value,allowed,required,label){
 if(!value||Array.isArray(value)||typeof value!=='object'||Object.keys(value).some(k=>!allowed.includes(k))||required.some(k=>!Object.hasOwn(value,k)))throw new Error(label+' has missing or unknown keys');
}
function vector(value,length,label){
 if(!Array.isArray(value)||value.length!==length||!value.every(Number.isFinite))throw new Error(label+' requires '+length+' finite components');
}
function numbers(value,names,label){for(const name of names)if(!Number.isFinite(value[name]))throw new Error(label+'.'+name+' requires a finite number');}
function heldSettings(value){
 keys(value,['mesh',...Object.keys(heldDefaults)],[],'Held settings');
 const mesh=Object.hasOwn(value,'mesh')?value.mesh:{};
 keys(mesh,['maxSurfaces','primitive'],[],'Mesh settings');
 const primitive=Object.hasOwn(mesh,'primitive')?mesh.primitive:{};
 keys(primitive,Object.keys(primitiveDefaults),[],'Primitive settings');
 const result={...heldDefaults,...value,mesh:{maxSurfaces:Object.hasOwn(mesh,'maxSurfaces')?mesh.maxSurfaces:64,primitive:{...primitiveDefaults,...primitive}}};
 numbers(result,Object.keys(heldDefaults),'Held settings');numbers(result.mesh,['maxSurfaces'],'Mesh settings');numbers(result.mesh.primitive,Object.keys(primitiveDefaults),'Primitive settings');
 return result;
}
export function parseFlightLabInput(input){
 const q=parseStrictJson(input,inputBudget),mode=q?.mode;
 if(mode!=='held'&&mode!=='guard')throw new Error('Input.mode must be held or guard');
 const required=mode==='held'?['mode','sphere','triangles','horizon','settings']:['mode','body','gravity','triangles','horizon','settings'];
 keys(q,required,required,'Input');numbers(q,['horizon'],'Input');
 if(!Array.isArray(q.triangles)||q.triangles.length>65)throw new Error('At most 65 editable source surfaces (SDK capacity 64)');
 for(const triangle of q.triangles){
  keys(triangle,['id','vertices'],['id','vertices'],'Triangle');numbers(triangle,['id'],'Triangle');
  if(!Array.isArray(triangle.vertices)||triangle.vertices.length!==3)throw new Error('Triangle requires ABC');
  for(const p of triangle.vertices)vector(p,3,'Triangle vertex');
 }
 if(mode==='held'){
  const fields=['id','position','velocity','mass','force','gravity','radius'];keys(q.sphere,fields,fields,'Held sphere');numbers(q.sphere,['id','mass','radius'],'Held sphere');
  for(const field of ['position','velocity','force','gravity'])vector(q.sphere[field],3,'Held sphere '+field);
  q.settings=heldSettings(q.settings);
 }else{
  const fields=['id','isStatic','mass','radius','inertiaDiagonal','position','orientation','velocity','angularMomentum','force','torque','material'];keys(q.body,fields,fields,'Native body');
  numbers(q.body,['id','mass','radius'],'Native body');if(typeof q.body.isStatic!=='boolean')throw new Error('Native body isStatic requires a boolean');
  for(const field of ['inertiaDiagonal','position','velocity','angularMomentum','force','torque'])vector(q.body[field],3,'Native body '+field);
  vector(q.body.orientation,4,'Native body orientation');vector(q.gravity,3,'Gravity');
  keys(q.body.material,['restitution','friction'],['restitution','friction'],'Material');numbers(q.body.material,['restitution','friction'],'Material');
  keys(q.settings,['heldLoad','maxAngularIncrement'],[],'Guard settings');
  const heldLoad=heldSettings(Object.hasOwn(q.settings,'heldLoad')?q.settings.heldLoad:{}),maxAngularIncrement=Object.hasOwn(q.settings,'maxAngularIncrement')?q.settings.maxAngularIncrement:.5;
  if(!Number.isFinite(maxAngularIncrement))throw new Error('maxAngularIncrement requires a finite number');
  q.settings={heldLoad,maxAngularIncrement};
 }
 return q;
}
function capability(runtime){
 if(typeof runtime?.querySphereTriangleMeshHeldLoad!=='function'||typeof runtime?.querySphereTriangleMeshFreeFlightGuard!=='function')throw new Error('Held-load/free-flight owned APIs unavailable (92-export SDK required)');
}
export function evaluateFlightLab(runtime,source){
 const input=parseFlightLabInput(stringifyStrictJson(source,inputBudget));capability(runtime);
 const result=input.mode==='held'?runtime.querySphereTriangleMeshHeldLoad(input.sphere,input.triangles,input.horizon,input.settings):runtime.querySphereTriangleMeshFreeFlightGuard(input.body,input.gravity,input.triangles,input.horizon,input.settings);
 return own({schema:1,kind:'sphere-triangle-mesh-flight-lab',mode:input.mode,input,result,diagnostics:runtime.diagnostics});
}
function inspection(length,index,label){
 if(length===0){if(index!==0&&index!==null)throw new Error('Empty '+label+' has no ordinal');return null;}
 if(!Number.isInteger(index)||index<0||index>=length)throw new Error('Unknown '+label+' ordinal');return index;
}
export function serializeFlightLab(packet,projection='xy',inspectedAudit=0,inspectedOrdinal=0){
 if(!Object.hasOwn(axesByProjection,projection))throw new Error('Unknown projection');
 if(packet?.schema!==1||packet.kind!=='sphere-triangle-mesh-flight-lab'||!packet.result||packet.mode!==packet.input?.mode)throw new Error('No actual flight query to save');
 const r=heldResult(packet.input,packet.result),audit=inspection(r?.audits.length??0,inspectedAudit,'audit'),ordinal=inspection(packet.input.triangles.length,inspectedOrdinal,'source');
 const output=stringifyStrictJson({...packet,projection,inspectedAudit:audit,inspectedOrdinal:ordinal,inspectedSurfaceId:ordinal===null?null:packet.input.triangles[ordinal].id},outputBudget)+'\n';
 if(new TextEncoder().encode(output).byteLength>outputBudget.maxBytes)throw new Error('Saved packet exceeds the UTF-8 byte budget including final LF');
 return output;
}
// Display-only projection of input vertices and returned boxes/points. No
// acceleration, trajectory, closest-point, interval proof or normal is computed.
export function flightProjection(source,result,projection='xy',inspectedAudit=0,inspectedOrdinal=0){
 if(!Object.hasOwn(axesByProjection,projection))throw new Error('Unknown projection');
 const r=heldResult(source,result),selected=inspection(r?.audits.length??0,inspectedAudit,'audit'),ordinal=inspection(source.triangles.length,inspectedOrdinal,'source'),a=selected===null?null:r.audits[selected];
 const belongs=selected!==null&&selected===r.lastMeshAuditIndex,row=ordinal===null?null:r?.lastMesh?.rows[ordinal],g=belongs?row?.query?.geometry:null;
 const origin=source.mode==='held'?source.sphere.position:source.body.position,originalRadius=source.mode==='held'?source.sphere.radius:source.body.radius;
 const axes=axesByProjection[projection],points=[origin,...source.triangles.flatMap(t=>t.vertices)];
 for(const b of [r?.wholePathBounds,a?.pathBounds,a?.pointBounds,g?.closest])if(b)for(const endpoint of [0,1])points.push(b.map(v=>v[endpoint]));
 if(a?.anchor)points.push(a.anchor);if(source.mode==='guard'&&result.candidate)points.push(result.candidate.position);
 const guardR=source.mode==='guard'?result.tube?.guardRadius??null:null,radius=originalRadius>0?originalRadius:0,extentR=Math.max(radius,guardR??0);
 const extent=axes.map(axis=>[Math.min(...points.map(p=>p[axis]),origin[axis]-extentR),Math.max(...points.map(p=>p[axis]),origin[axis]+extentR)]);
 const span=Math.max(1e-300,...extent.map(b=>b[1]-b[0])),scale=330/span,center=extent.map(b=>b[0]/2+b[1]/2);
 const project=p=>[450+(p[axes[0]]-center[0])*scale,220-(p[axes[1]]-center[1])*scale];
 const rectangle=b=>{if(!b)return null;const p=project(b.map(v=>v[0])),q=project(b.map(v=>v[1]));return {x:Math.min(p[0],q[0]),y:Math.min(p[1],q[1]),width:(b[axes[0]][1]-b[axes[0]][0])*scale,height:(b[axes[1]][1]-b[axes[1]][0])*scale};};
 const model={available:true,mode:source.mode,projection,triangles:source.triangles.map((t,i)=>({ordinal:i,id:t.id,vertices:t.vertices.map(project)})),origin:project(origin),radius:radius*scale,guardRadius:guardR===null?null:guardR*scale,
  pathBox:rectangle(a?.pathBounds),pointBox:rectangle(a?.pointBounds),wholePathBox:rectangle(r?.wholePathBounds),anchor:a?.anchor?project(a.anchor):null,closest:rectangle(g?.closest),candidate:source.mode==='guard'&&result.candidate?project(result.candidate.position):null,
  scale,inspectedAudit:selected,inspectedOrdinal:ordinal,inspectedSurfaceId:ordinal===null?null:source.triangles[ordinal].id,lastMeshAuditIndex:r?.lastMeshAuditIndex??null,geometryBelongsToSelectedAudit:belongs};
 const values=[scale,...model.triangles.flatMap(t=>t.vertices.flat()),...model.origin,model.radius,...(model.guardRadius===null?[]:[model.guardRadius]),...(model.anchor??[]),...(model.candidate??[]),...[model.pathBox,model.pointBox,model.wholePathBox,model.closest].flatMap(b=>Object.values(b??{}))];
 if(!values.every(Number.isFinite)||scale<=0)return {available:false,projection,reason:'説明図の数値範囲を超えています。数値結果と保存は維持します。'};
 return model;
}
function download({text,filename,mime}){
 const url=URL.createObjectURL(new Blob([text],{type:mime})),a=document.createElement('a');
 try{a.href=url;a.download=filename;document.body.append(a);a.click();}finally{a.remove();URL.revokeObjectURL(url);}
}
const statusLabels={separated:'全Hのstrict非接触を証明（数学的保持荷重path）',certified_separated:'丸めtube・候補bodyを含む非接触guardを認証',entry_window:'開始窓を認証（応答/World advanceではありません）',initial_penetration:'初期strict貫通（新規entry窓なし）',not_certified:'未認証 / 安全を確認していません',invalid_input:'モデル入力を拒否',unsupported_environment:'浮動小数点環境を拒否',numerical_failure:'数値計算失敗'};
export async function initializeSphereTriangleMeshFlightLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();},saveFile=download}={}){
 const get=name=>doc.getElementById('flight-'+name),listeners=[];
 let runtime=null,state=null,generation=0,loadGeneration=0,loading=null,disposed=false;
 const on=(name,event,fn)=>{get(name).addEventListener(event,fn);listeners.push([get(name),event,fn]);};
 function clear(message='入力が変更されました。現在入力を明示的に照会してください。'){
  state=null;get('save').disabled=true;get('save-input').disabled=true;
  for(const name of ['inspect','audit']){get(name).innerHTML='';get(name).value='';get(name).disabled=true;}
  for(const name of ['rows','audits','leaves','timeline','view'])get(name).innerHTML='';
  for(const name of ['summary','initial','window','tube','endpoint','body','partition','geometry','candidates'])get(name).textContent='—';
  get('json').textContent='';get('error').hidden=true;get('note').textContent='';get('status').textContent=message;get('status').dataset.state='empty';
  get('view').setAttribute('aria-label','実照会結果は表示していません。');get('timeline').setAttribute('aria-label','時間の証明区間は表示していません。');
 }
 function reject(error,stage){clear('操作を拒否しました。以前の結果は表示していません。');get('error').hidden=false;get('error').textContent=stage+': '+(error?.message??String(error));get('status').dataset.state='error';}
 const selection=(name,length)=>length?Number(get(name).value):null;
 function drawTimeline(r,H){
  const svg=get('timeline');if(!r){svg.innerHTML='';svg.setAttribute('aria-label','inflated held照会は未実行。時間帯を生成していません。');return;}
  if(!(H>0)||!Number.isFinite(828/H)){svg.innerHTML='';svg.setAttribute('aria-label','時間投影の範囲外です。完全数値診断を参照してください。');return;}
  const x=t=>36+828*(t/H),band=(bounds,y,color,label)=>bounds[0]===bounds[1]?`<circle cx="${x(bounds[0])}" cy="${y+7}" r="4" fill="${color}"><title>${html(label)} ${html(text(bounds))} seconds (singleton)</title></circle>`:`<rect x="${x(bounds[0])}" y="${y}" width="${Math.max(1,828*((bounds[1]-bounds[0])/H))}" height="14" fill="${color}"><title>${html(label)} ${html(text(bounds))} seconds (closed / 最小1pxは表示用)</title></rect>`;
  const colors={unqueried:'#72818e',certified:'#75ddbc',unresolved:'#f8ae6e',current:'#ff809a'};
  svg.innerHTML='<rect width="900" height="240" fill="#09121d"/><text x="36" y="18" fill="#c6d9e8">t = 0 s</text>'+`<text x="730" y="18" fill="#c6d9e8">H = ${html(text(H))} s</text>`+
   r.partition.map((l,i)=>band(l.cell.timeBounds,30,colors[l.state]??'#e6edf3',`partition ${i} / ${l.state} / ${l.blockedReason}`)).join('')+
   r.certifiedLeaves.map((l,i)=>band(l.cell.timeBounds,58,'#75ddbc','certified island '+i)).join('')+(r.safePrefix?band(r.safePrefix,86,'#729cdb','safePrefix'):'')+
   (r.window?band(r.window.timeBounds,114,'#bd9bff','held entry window / 元球応答ではない'):'')+r.frontier.map((c,i)=>band(c.timeBounds,142,'#72818e','frontier '+i+' / 未照会tailを含む')).join('')+
   (r.current?band(r.current.timeBounds,170,'#f8ae6e','current'):'')+(r.initial?`<circle cx="36" cy="195" r="4" fill="${r.initialSeparationProven?'#75ddbc':'#f8ae6e'}"><title>initial t=0 / ${html(r.status)}</title></circle>`:'')+
   (r.bestWitness?`<line x1="${x(r.bestWitness.time)}" x2="${x(r.bestWitness.time)}" y1="25" y2="200" stroke="#ff809a" stroke-width="2"><title>strict負点witness t=${html(r.bestWitness.time)} s</title></line>`:'')+
   '<text x="36" y="222" fill="#c6d9e8">全partition / 証明島 / prefix / 窓 / 未照会 / current。帯の最小1pxは表示用。</text>';
  svg.setAttribute('aria-label',`秒[0,${H}]。全partition${r.partition.length}、証明島${r.certifiedLeaves.length}、safePrefix ${text(r.safePrefix)}、window ${text(r.window)}、frontier ${r.frontier.length}。`);
 }
 function display(){
  if(!state||disposed)return;
  const r=heldResult(state.input,state.result),ordinal=selection('inspect',state.input.triangles.length),ai=selection('audit',r?.audits.length??0),audit=ai===null?null:r.audits[ai],row=ordinal===null?null:r?.lastMesh?.rows[ordinal],q=row?.query??null;
  get('geometry').textContent=readable({mode:state.mode,heldResultBelongsTo:state.mode==='held'?'original held sphere':'guard.inflated (radius + B)',selectedAudit:ai,audit,lastMeshAuditIndex:r?.lastMeshAuditIndex??null,lastMeshBelongsToSelectedAudit:ai!==null&&ai===r?.lastMeshAuditIndex,
   lastMesh:r?.lastMesh?{status:r.lastMesh.status,reason:r.lastMesh.reason,nearest:r.lastMesh.nearest,queries:r.lastMesh.queries}:null,sourceOrdinal:ordinal,surfaceId:ordinal===null?null:state.input.triangles[ordinal].id,rowPresent:Boolean(row),queryPresent:Boolean(q),rowQuery:q});
  get('candidates').textContent=q?readable(q.candidates):'lastMeshに実queryはありません。未実行候補を補完していません。';
  const projection=get('projection').value,v=flightProjection(state.input,state.result,projection,ai,ordinal),svg=get('view');
  if(!v.available){svg.innerHTML='';svg.setAttribute('aria-label',v.reason);get('note').textContent=v.reason;}
  else{
   const rect=(b,color)=>b?`<rect x="${b.x-1.5}" y="${b.y-1.5}" width="${b.width+3}" height="${b.height+3}" fill="none" stroke="${color}" stroke-width="2"/>`:'';
   svg.innerHTML='<rect width="900" height="440" fill="#09121d"/>'+v.triangles.map(t=>`<polygon points="${t.vertices.map(p=>p.join(',')).join(' ')}" fill="${t.ordinal===ordinal?'#173c45':'none'}" stroke="${t.ordinal===ordinal?'#75ddbc':'#4a6474'}"/>`).join('')+
    `<circle cx="${v.origin[0]}" cy="${v.origin[1]}" r="${v.radius}" fill="none" stroke="#ffbf75"/><circle cx="${v.origin[0]}" cy="${v.origin[1]}" r="3" fill="#ffbf75"/>`+
    (v.guardRadius===null?'':`<circle cx="${v.origin[0]}" cy="${v.origin[1]}" r="${v.guardRadius}" fill="none" stroke="#bd9bff" stroke-dasharray="6 4"/>`)+
    rect(v.wholePathBox,'#4a6474')+rect(v.pathBox,'#729cdb')+rect(v.pointBox,'#f5f6c0')+rect(v.closest,'#75ddbc')+
    (v.anchor?`<path d="M ${v.anchor[0]-5} ${v.anchor[1]-5} l 10 10 M ${v.anchor[0]-5} ${v.anchor[1]+5} l 10 -10" stroke="#ff809a" stroke-width="2"/>`:'')+(v.candidate?`<circle cx="${v.candidate[0]}" cy="${v.candidate[1]}" r="4" fill="#bd9bff"><title>Hでの実candidate中心（Worldへ未commit）</title></circle>`:'');
   svg.setAttribute('aria-label',`${projection.toUpperCase()}説明proxy。元半径と膨張半径、返却されたbox/anchorだけを描きます。実軌道を再計算していません。`);
   get('note').textContent=`${projection.toUpperCase()} / ${v.scale.toPrecision(5)} px/m。橙=元半径、紫破線=膨張半径、灰=wholePath、青=選択path box、黄=point box、赤×=任意anchor。${v.geometryBelongsToSelectedAudit?'緑は同じaudit所属のclosest box。':'異なる所属のlastMesh幾何は重ねません。'}boxの3px拡張と帯の最小1pxは表示用。曲線・衝突・法線をJS計算しません。`;
  }
  get('json').textContent=serializeFlightLab(state,projection,ai,ordinal);get('save').disabled=false;get('save-input').disabled=false;
 }
 function run(){
  if(disposed||!runtime)return null;
  ++generation;clear('SI保持荷重 / 自由伝播guardを照会中…');let input;
  try{input=parseFlightLabInput(get('source').value);if(input.mode!==get('mode').value)throw new Error('選択modeとinput.modeが一致しません。modeに合う例または入力を選んでください。');}catch(error){reject(error,'入力JSON');return null;}
  let stage='SDK交換';try{
   const next=evaluateFlightLab(runtime,input);state=next;const outer=next.result,r=heldResult(next.input,outer);stage='表示';
   get('status').textContent=`${statusLabels[outer.status]??'不明なモデル分類'} / ${outer.status} / ${outer.reason}`;
   get('status').dataset.state=(outer.status==='separated'||outer.status==='certified_separated')?'separated':outer.status==='entry_window'?'window':'unconfirmed';
   get('summary').textContent=readable({mode:next.mode,status:outer.status,reason:outer.reason,failedIndex:outer.failedIndex,horizonSeconds:next.input.horizon,hasSnapshot:outer.snapshot!==null,heldStatus:r?.status??null,heldReason:r?.reason??null,work:r?.work??null,sourceCount:next.input.triangles.length,auditCount:r?.audits.length??0,leafCount:r?.certifiedLeaves.length??0,lastMeshAuditIndex:r?.lastMeshAuditIndex??null,originalInput:outer.originalInput,snapshot:outer.snapshot});
   get('initial').textContent=readable({owner:next.mode==='held'?'held':'guard.inflated',initial:r?.initial??null,initialSeparationProven:r?.initialSeparationProven??false,safePrefix:r?.safePrefix??null,meaning:'nullは証拠なし。[0,0]のprefixは初期strict正のみ。'});
   get('window').textContent=readable({outerStatus:outer.status,heldStatus:r?.status??null,safePrefix:r?.safePrefix??null,window:r?.window??null,bestWitness:r?.bestWitness??null,timeToleranceSeconds:next.mode==='held'?next.input.settings.timeTolerance:next.input.settings.heldLoad.timeTolerance,candidateSurfaceIds:r?.candidateSurfaceIds??[],meaning:'guard.inflatedの開始窓は元半径の物理entry/応答ではありません。秒幅は空間誤差ではありません。'});
   get('tube').textContent=readable({originalRadius:next.mode==='held'?next.input.sphere.radius:next.input.body.radius,tube:next.mode==='guard'?outer.tube:null,acceleration:r?.acceleration??null,wholePathBounds:r?.wholePathBounds??null,wholeVelocityBounds:r?.wholeVelocityBounds??null,inflatedInput:next.mode==='guard'?r?.snapshot?.input??null:null,meaning:'原半径とr+B、nominal/exact A、B/roundoffを別に保持します。'});
   get('endpoint').textContent=readable({flightFailure:next.mode==='guard'?outer.flightFailure:null,candidateEvaluated:next.mode==='guard'?outer.candidateEvaluated:false,endpoint:next.mode==='guard'?outer.endpoint:null});
   get('body').textContent=readable({originalBody:next.mode==='guard'?next.input.body:null,worldBody:outer.worldBody,candidate:next.mode==='guard'?outer.candidate:null,meaning:'候補は未commit。元body/荷重/時計を進めません。不良captured bodyと成功candidateを混同しません。'});
   get('partition').textContent=readable({partition:r?.partition??null,safePrefix:r?.safePrefix??null,current:r?.current??null,frontier:r?.frontier??null,partitionLeaves:r?.partitionLeaves??null,maximumDepth:r?.maximumDepth??null,meaning:'global秒[0,H]。未照会tailを捨てず、後方島をprefixへ飛ばして接続しません。'});
   get('audits').innerHTML=(r?.audits??[]).map((a,i)=>`<tr><td>${i}</td><td>${html(a.kind)} / ${html(text(a.cell.timeBounds))} s / depth ${a.cell.depth}</td><td>t=${html(text(a.time))} s / ${html(a.outcome)}</td><td>${a.meshQueried?'実照会':'未照会'} / ${html(a.meshStatus??'unreturned')} / ${html(a.meshReason??'—')}</td><td>${html(text(a.work))}</td></tr>`).join('');
   get('leaves').innerHTML=(r?.certifiedLeaves??[]).map((l,i)=>`<tr><td>${i}</td><td>${html(text(l.cell.timeBounds))} s</td><td>${l.cell.depth}</td><td>${html(text(l.lowerGapCertificate))}</td><td>${l.auditIndex}</td></tr>`).join('');
   get('rows').innerHTML=next.input.triangles.map((t,i)=>{const row=r?.lastMesh?.rows[i],q=row?.query;return `<tr><td>${i}</td><td>${html(t.id)}</td><td>${q?'実照会済み':row?'未照会 / fatal':'未照会'} / ${html(q?.status??'unexamined')} / ${html(q?.reason??'—')}</td><td>${q?`${q.candidates.length}/${q.candidatesExamined} candidates / ${q.sqrtRefinements} sqrt / limited=${q.sqrtRefinementLimited}`:'—'}</td><td>${r?.lastMesh?.nearest?.possibleSurfaceIds.includes(t.id)?'possible (lastMesh)':'—'}</td></tr>`;}).join('');
   get('inspect').innerHTML=next.input.triangles.map((t,i)=>`<option value="${i}">${i}: ID ${html(t.id)}</option>`).join('');get('inspect').value=next.input.triangles.length?'0':'';get('inspect').disabled=!next.input.triangles.length;
   get('audit').innerHTML=(r?.audits??[]).map((a,i)=>`<option value="${i}">${i}: ${html(a.kind)} t${html(text(a.cell.timeBounds))} / ${html(a.outcome)}</option>`).join('');get('audit').value=r?.audits.length?'0':'';get('audit').disabled=!r?.audits.length;
   drawTimeline(r,next.input.horizon);display();return own(state);
  }catch(error){reject(error,stage);return null;}
 }
 function retry(){
  if(disposed)return Promise.resolve(null);if(loading)return loading;
  const current=++generation,epoch=++loadGeneration;runtime=null;clear('C++ WebAssemblyを読込み中…');get('runtime').textContent='SDK未初期化';get('retry').disabled=true;get('controls').disabled=true;
  loading=Promise.resolve().then(async()=>{try{
   const loaded=await loadRuntime();if(disposed||epoch!==loadGeneration)return null;capability(loaded);
   runtime=loaded;get('controls').disabled=false;get('runtime').textContent=`${runtime.diagnostics.backend} / ${runtime.diagnostics.wasmBytes} B / build ${runtime.diagnostics.buildId}`;
   if(current!==generation){clear('SDKを読み込みました。現在入力を明示的に照会してください。');return null;}return run();
  }catch(error){if(!disposed&&epoch===loadGeneration){runtime=null;get('runtime').textContent='SDK未初期化';reject(error,'SDK初期化');}return null;}
  finally{if(epoch===loadGeneration){loading=null;if(!disposed)get('retry').disabled=false;}}});return loading;
 }
 function setPreset(name){const input=flightLabPreset(name);get('preset').value=name;get('mode').value=input.mode;get('source').value=readable(input);}
 get('preset').innerHTML=flightLabPresets.map(p=>`<option value="${html(p.name)}">${html(p.label)} (${html(p.mode)})</option>`).join('');setPreset(flightLabPresets[0].name);get('projection').value='xy';
 on('source','input',()=>{if(!disposed){generation++;clear();}});
 on('preset','change',()=>{if(disposed)return;generation++;clear();try{setPreset(get('preset').value);if(runtime)return run();}catch(error){reject(error,'例の選択');}});
 on('mode','change',()=>{if(disposed)return;generation++;clear('modeを変更しました。入力を確認して明示的に照会してください。');const preset=flightLabPresets.find(p=>p.mode===get('mode').value);if(preset)setPreset(preset.name);});
 for(const name of ['projection','inspect','audit'])on(name,'change',()=>{if(!disposed&&state)try{display();}catch(error){reject(error,'表示');}});
 on('query','click',run);on('retry','click',retry);
 on('reset','click',()=>{if(disposed)return;generation++;clear();try{setPreset(get('preset').value);return run();}catch(error){reject(error,'初期値');return null;}});
 on('save','click',()=>{if(!disposed&&state)try{return saveFile({text:serializeFlightLab(state,get('projection').value,selection('audit',heldResult(state.input,state.result)?.audits.length??0),selection('inspect',state.input.triangles.length)),filename:'pikapika-sphere-triangle-mesh-flight-'+state.mode+'.json',mime:'application/json'});}catch(error){reject(error,'結果保存');}});
 on('save-input','click',()=>{if(!disposed&&state)try{const data=stringifyStrictJson(state.input,inputBudget)+'\n';if(new TextEncoder().encode(data).byteLength>inputBudget.maxBytes)throw new Error('Source exceeds byte budget including LF');return saveFile({text:data,filename:'pikapika-sphere-triangle-mesh-flight-input.json',mime:'application/json'});}catch(error){reject(error,'入力保存');}});
 const api={run,retry,getState:()=>state?own(state):null,dispose(){if(disposed)return;clear('ラボを終了しました。');get('controls').disabled=true;get('retry').disabled=true;disposed=true;runtime=null;generation++;loadGeneration++;for(const [element,event,fn]of listeners)element.removeEventListener?.(event,fn);}};
 const view=doc.defaultView;
 if(view?.addEventListener){const close=()=>api.dispose();view.addEventListener('pagehide',close);listeners.push([view,'pagehide',close]);}
 await retry();return api;
}
if(typeof document!=='undefined')initializeSphereTriangleMeshFlightLab();
