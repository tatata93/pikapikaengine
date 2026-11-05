import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const primitiveDefaults=Object.freeze({maxCandidates:7,sqrtRefinements:128,maxTotalSqrtRefinements:1024,maximumLocalWidth:1e-7,maximumNormalWidth:1e-8,minimumSineSquared:1e-12});
const inputBudget={maxBytes:65536,maxDepth:10,maxNodes:6000};
const outputBudget={maxBytes:4194304,maxDepth:20,maxNodes:200000};
const axesByProjection={xy:[0,1],xz:[0,2],yz:[1,2]};
const own=value=>parseStrictJson(stringifyStrictJson(value,outputBudget),outputBudget);
const readable=(value,depth=0)=>Array.isArray(value)?'['+value.map(v=>readable(v,depth)).join(', ')+']':value&&typeof value==='object'?'{\n'+Object.entries(value).map(([k,v])=>'  '.repeat(depth+1)+JSON.stringify(k)+': '+readable(v,depth+1)).join(',\n')+'\n'+'  '.repeat(depth)+'}':stringifyStrictJson(value);
export const meshLabPresets=Object.freeze([
 ['singleton','1面 / 面の内部'],['back','1面 / 裏側'],['dominance','明確に近い面'],['shared_edge','共有辺の複数候補'],['shared_vertex','共有頂点の複数候補'],['separate_tie','離れた最近接点'],['reversed','面順を反転'],['uncertain_order','区間で順序未確定'],['huge_offset','巨大な共通offset'],['capacity64','実64面 / 全ID保持'],['middle_degenerate','途中の退化面'],['far_degenerate','遠方の退化面も省略しない'],['candidate_budget','面ごとの候補予算'],['normal_precision','法線幅の品質失敗'],['duplicate_id','ID重複 / 事前拒否'],['empty','空集合 / モデル拒否'],['capacity65','65面 / host交換拒否']
].map(([name,label])=>Object.freeze({name,label})));
const triangle=(id,y=0)=>({id,vertices:[[-0,y,-0],[4,y,0],[0,y,4]]});
export function meshLabPreset(name='singleton'){
 if(!meshLabPresets.some(p=>p.name===name))throw new Error('Unknown mesh preset: '+name);
 const input={sphere:{position:[1,1,1],radius:.5},triangles:[triangle(37)],settings:{maxSurfaces:64,primitive:{...primitiveDefaults}}};
 if(name==='back')input.sphere.position=[1,-1,1];
 else if(name==='dominance'||name==='reversed'){input.triangles.push(triangle(99,-4));if(name==='reversed')input.triangles.reverse();}
 else if(name==='shared_edge'){input.sphere.position=[2,1,2];input.triangles.push({id:11,vertices:[[4,0,0],[4,0,4],[0,0,4]]});}
 else if(name==='shared_vertex'){input.sphere.position=[0,1,0];input.triangles.push({id:11,vertices:[[0,0,0],[-4,0,0],[0,0,-4]]});}
 else if(name==='separate_tie'){input.sphere={position:[0,0,0],radius:.25};input.triangles=[{id:99,vertices:[[-1,-2,-2],[-1,2,-2],[-1,0,2]]},{id:7,vertices:[[1,-2,-2],[1,2,-2],[1,0,2]]}];}
 else if(name==='uncertain_order')input.triangles.push(triangle(5,-Number.MIN_VALUE));
 else if(name==='huge_offset'){input.triangles.push(triangle(99,-4));const offset=2**40;for(const t of input.triangles)t.vertices=t.vertices.map(([x,y,z])=>[x+offset,y-offset,z+offset]);input.sphere.position=[offset+1,-offset+1,offset+1];}
 else if(name==='capacity64'||name==='capacity65')input.triangles=Array.from({length:name==='capacity64'?64:65},(_,i)=>triangle(i+1));
 else if(name==='middle_degenerate'||name==='far_degenerate'){const x=name==='far_degenerate'?1000:0;input.triangles.push({id:99,vertices:[[x,0,0],[x+4,0,0],[x+8,0,0]]},triangle(5,-4));}
 else if(name==='candidate_budget'){input.triangles.push(triangle(99,-4));input.settings.primitive.maxCandidates=3;}
 else if(name==='normal_precision'){input.triangles.push(triangle(99,-4));input.settings.primitive.maximumNormalWidth=1e-30;}
 else if(name==='duplicate_id')input.triangles.push(triangle(37,-4));
 else if(name==='empty')input.triangles=[];
 return input;
}
function keys(value,allowed,required,label){if(!value||Array.isArray(value)||typeof value!=='object'||Object.keys(value).some(k=>!allowed.includes(k))||required.some(k=>!Object.hasOwn(value,k)))throw new Error(label+' has missing or unknown keys');}
export function parseMeshLabInput(text){
 const q=parseStrictJson(text,inputBudget);keys(q,['sphere','triangles','settings'],['sphere','triangles','settings'],'Input');keys(q.sphere,['position','radius'],['position','radius'],'Sphere');keys(q.settings,['maxSurfaces','primitive'],[],'Settings');
 const vector=x=>Array.isArray(x)&&x.length===3&&x.every(Number.isFinite);
 if(!vector(q.sphere.position)||!Number.isFinite(q.sphere.radius)||!Array.isArray(q.triangles)||q.triangles.length>65)throw new Error('Source requires finite sphere XYZ and at most 65 editable triangles (SDK capacity 64)');
 for(const t of q.triangles){keys(t,['id','vertices'],['id','vertices'],'Triangle');if(!Number.isFinite(t.id)||!Array.isArray(t.vertices)||t.vertices.length!==3||!t.vertices.every(vector))throw new Error('Triangle requires numeric ID and finite ABC XYZ');}
 if(Object.hasOwn(q.settings,'primitive'))keys(q.settings.primitive,Object.keys(primitiveDefaults),[],'Primitive settings');
 const primitive={...primitiveDefaults,...q.settings.primitive},maxSurfaces=Object.hasOwn(q.settings,'maxSurfaces')?q.settings.maxSurfaces:64;
 if(!Number.isFinite(maxSurfaces)||!Object.values(primitive).every(Number.isFinite))throw new Error('Settings require finite numeric values');
 q.settings={maxSurfaces,primitive};return q;
}
export function evaluateMeshLab(runtime,source){
 const input=parseMeshLabInput(stringifyStrictJson(source,inputBudget));
 if(typeof runtime?.querySphereTriangleMesh!=='function')throw new Error('Sphere triangle mesh API unavailable (74-export SDK required)');
 const result=runtime.querySphereTriangleMesh(input.sphere,input.triangles,input.settings);
 return own({schema:1,kind:'sphere-triangle-mesh-lab',input,result,diagnostics:runtime.diagnostics});
}
function inspection(source,ordinal){
 if(source.triangles.length===0){if(ordinal!==0&&ordinal!==null)throw new Error('Empty source has no inspection ordinal');return null;}
 if(!Number.isInteger(ordinal)||ordinal<0||ordinal>=source.triangles.length)throw new Error('Unknown inspection ordinal');return ordinal;
}
export function serializeMeshLab(packet,projection='xz',inspectedOrdinal=0){
 if(!Object.hasOwn(axesByProjection,projection))throw new Error('Unknown projection');
 if(packet?.schema!==1||packet.kind!=='sphere-triangle-mesh-lab'||!packet.result)throw new Error('No actual mesh query to save');
 const ordinal=inspection(packet.input,inspectedOrdinal);
 return stringifyStrictJson({...packet,projection,inspectedOrdinal:ordinal,inspectedSurfaceId:ordinal===null?null:packet.input.triangles[ordinal].id},outputBudget)+'\n';
}
// Explanatory drawing only. No distance, KKT, normal, nearest selection or
// geometric fallback is calculated in JS. Each returned rectangle belongs to
// the inspected actual row, including when the aggregate failed elsewhere.
export function meshProjection(source,result,projection='xz',inspectedOrdinal=0){
 if(!Object.hasOwn(axesByProjection,projection))throw new Error('Unknown projection');
 const ordinal=inspection(source,inspectedOrdinal),axes=axesByProjection[projection],row=ordinal===null?null:result.rows[ordinal],g=row?.query?.geometry??null;
 const points=[source.sphere.position,...source.triangles.flatMap(t=>t.vertices)];if(g)for(const end of [0,1])points.push(g.closest.map(b=>b[end]));
 const extent=axes.map(axis=>[Math.min(...points.map(p=>p[axis]),source.sphere.position[axis]-Math.abs(source.sphere.radius)),Math.max(...points.map(p=>p[axis]),source.sphere.position[axis]+Math.abs(source.sphere.radius))]);
 const span=Math.max(1e-300,...extent.map(b=>b[1]-b[0])),scale=300/span,center=extent.map(b=>b[0]/2+b[1]/2);
 const project=p=>[450+(p[axes[0]]-center[0])*scale,220-(p[axes[1]]-center[1])*scale];
 const triangles=source.triangles.map((t,i)=>({ordinal:i,id:t.id,vertices:t.vertices.map(project)})),sphereCenter=project(source.sphere.position),radius=source.sphere.radius>0?source.sphere.radius*scale:0;
 let closest=null;if(g){const a=project(g.closest.map(b=>b[0])),b=project(g.closest.map(b=>b[1]));closest={x:Math.min(a[0],b[0]),y:Math.min(a[1],b[1]),width:(g.closest[axes[0]][1]-g.closest[axes[0]][0])*scale,height:(g.closest[axes[1]][1]-g.closest[axes[1]][0])*scale};}
 const numbers=[scale,...triangles.flatMap(t=>t.vertices.flat()),...sphereCenter,radius,...Object.values(closest??{})];
 if(!numbers.every(Number.isFinite)||scale<=0)return {available:false,projection,reason:'投影の数値範囲を超えています。実数値の区間表を参照してください。'};
 return {available:true,projection,triangles,sphereCenter,radius,closest,scale,inspectedOrdinal:ordinal,inspectedSurfaceId:ordinal===null?null:source.triangles[ordinal].id,rowStatus:row?.query?.status??'unexamined',aggregateStatus:result.status};
}
function download({text,filename,mime}){const url=URL.createObjectURL(new Blob([text],{type:mime})),a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);}
const html=text=>String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export async function initializeSphereTriangleMeshLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();},saveFile=download}={}){
 const get=name=>doc.getElementById('mesh-'+name),listeners=[];let runtime=null,state=null,generation=0,loading=null,disposed=false;
 const on=(name,event,fn)=>{get(name).addEventListener(event,fn);listeners.push([name,event,fn]);};
 function clear(message='入力が変更されました。明示的に照会してください。'){
  state=null;get('save').disabled=true;get('inspect').disabled=true;get('inspect').innerHTML='';get('inspect').value='';get('rows').innerHTML='';get('summary').textContent='—';get('geometry').textContent='—';get('candidates').textContent='—';get('json').textContent='';get('view').innerHTML='';get('view').setAttribute('aria-label','実照会結果は表示していません。');get('status').textContent=message;get('error').hidden=true;get('note').textContent='';
 }
 function reject(error,stage){clear('操作に失敗しました。以前の集合結果は表示していません。');get('error').hidden=false;get('error').textContent=stage+': '+(error?.message??String(error));}
 function ordinal(){return state?.input.triangles.length?Number(get('inspect').value):null;}
 function display(){
  if(!state||disposed)return;
  const selected=ordinal(),r=state.result,row=selected===null?null:r.rows[selected],q=row?.query??null;
  get('geometry').textContent=q?readable({aggregateStatus:r.status,aggregateNearestAvailable:r.nearest!==null,sourceOrdinal:selected,surfaceId:state.input.triangles[selected].id,status:q.status,reason:q.reason,candidateCount:q.candidates.length,candidatesExamined:q.candidatesExamined,sqrtRefinements:q.sqrtRefinements,sqrtRefinementLimited:q.sqrtRefinementLimited,squaredCross:q.squaredCross,sineSquared:q.sineSquared,geometry:q.geometry}):'未照会（元sourceは存在しても実Native row/queryはありません）';
  get('candidates').textContent=q?q.candidates.map((c,i)=>`${i}: ${c.feature} / ${c.disposition} / KKT ${c.kktCount}\nbarycentric ${stringifyStrictJson(c.barycentric)}\nkkt ${stringifyStrictJson(c.kkt)}`).join('\n\n')||'実queryの候補prefixは空です。':'未照会 / 候補は生成していません。';
  const projection=get('projection').value,view=meshProjection(state.input,r,projection,selected),svg=get('view');
  if(!view.available){svg.innerHTML='';svg.setAttribute('aria-label',view.reason);get('note').textContent=view.reason;}
  else{
   svg.innerHTML='<rect width="900" height="440" fill="#0b1722"/>'+view.triangles.map(t=>`<polygon points="${t.vertices.map(p=>p.join(',')).join(' ')}" fill="${t.ordinal===selected?'#244653':'none'}" stroke="${t.ordinal===selected?'#7ee1d1':'#47626f'}" stroke-width="${t.ordinal===selected?2:1}"/>`).join('')+`<circle cx="${view.sphereCenter[0]}" cy="${view.sphereCenter[1]}" r="${view.radius}" fill="none" stroke="#ffbf75" stroke-width="2"/><circle cx="${view.sphereCenter[0]}" cy="${view.sphereCenter[1]}" r="3" fill="#ffbf75"/>`+(view.closest?`<rect x="${view.closest.x-1.5}" y="${view.closest.y-1.5}" width="${view.closest.width+3}" height="${view.closest.height+3}" fill="#fff"/>`:'');
   svg.setAttribute('aria-label',`${projection.toUpperCase()}説明投影。集合 ${r.status}。閲覧面 ${view.inspectedSurfaceId??'なし'} / ${view.rowStatus}。${view.closest?'白い区間は当該行の診断で、集合nearestの確定ではありません。':'成功geometryはありません。'}`);
   get('note').textContent=`${projection.toUpperCase()}の説明投影 / ${view.scale.toPrecision(5)} px/m。${r.nearest?'集合に最小となり得るIDを保持。':'集合nearestはありません。'}白い区間は閲覧面固有の返却区間、表示線幅を3px拡張。重なる面も全IDは表に残ります。`;
  }
  get('json').textContent=serializeMeshLab(state,projection,selected);get('save').disabled=false;
 }
 function run(){
  if(disposed||!runtime)return null;
  ++generation;clear('照会中…');let input;
  try{input=parseMeshLabInput(get('source').value);}catch(error){reject(error,'入力JSON');return null;}
  try{
   const next=evaluateMeshLab(runtime,input);state=next;const r=next.result;
   get('status').textContent=r.status==='completed'?`集合成功 / 最小となり得るID: ${r.nearest.possibleSurfaceIds.join(', ')}`:`集合モデル失敗 / ${r.status} / ${r.reason} / nearestなし`;
   const {rows,...summary}=r;get('summary').textContent=readable(summary);
   get('rows').innerHTML=next.input.triangles.map((t,i)=>{const row=rows[i],q=row?.query;return `<tr><td>${i}</td><td>${html(t.id)}</td><td>${q?'実照会済み':row?'未照会 / fatal':'事前拒否で未照会'} / ${html(q?.status??'unexamined')} / ${html(q?.reason??'—')}</td><td>${q?`${q.candidates.length}/${q.candidatesExamined} candidates / ${q.sqrtRefinements} sqrt / limited=${q.sqrtRefinementLimited}`:'—'}</td><td>${r.nearest?.possibleSurfaceIds.includes(t.id)?'possible':'—'}</td></tr>`;}).join('');
   get('inspect').innerHTML=next.input.triangles.map((t,i)=>`<option value="${i}">${i}: ID ${html(t.id)}</option>`).join('');get('inspect').value=next.input.triangles.length?'0':'';get('inspect').disabled=next.input.triangles.length===0;display();return own(state);
  }catch(error){reject(error,'SDK交換');return null;}
 }
 async function retry(){
  if(disposed)return null;if(loading)return loading;
  const current=++generation;runtime=null;clear('C++ WebAssemblyを読込み中…');get('runtime').textContent='SDK未初期化';get('retry').disabled=true;get('controls').disabled=true;
  loading=Promise.resolve().then(async()=>{try{
   const loaded=await loadRuntime();if(disposed)return null;
   if(typeof loaded?.querySphereTriangleMesh!=='function')throw new Error('Sphere triangle mesh API unavailable (74-export SDK required)');
   runtime=loaded;get('controls').disabled=false;get('runtime').textContent=`${runtime.diagnostics.backend} / ${runtime.diagnostics.wasmBytes} B / build ${runtime.diagnostics.buildId}`;
   if(current!==generation){clear('SDKを読み込みました。現在の入力を照会してください。');return null;}return run();
  }catch(error){if(!disposed){runtime=null;get('runtime').textContent='SDK未初期化';reject(error,'SDK初期化');}return null;}
  finally{loading=null;if(!disposed)get('retry').disabled=false;}});return loading;
 }
 get('source').value=readable(meshLabPreset());get('projection').value='xz';get('preset').value='singleton';
 on('source','input',()=>{if(!disposed){generation++;clear();}});
 on('preset','change',()=>{if(disposed)return;generation++;clear();try{get('source').value=readable(meshLabPreset(get('preset').value));if(runtime)return run();}catch(error){reject(error,'例の選択');}});
 for(const name of ['projection','inspect'])on(name,'change',()=>{if(disposed||!state)return;try{display();}catch(error){reject(error,'表示');}});
 on('run','click',run);on('retry','click',retry);
 on('reset','click',()=>{if(disposed)return;generation++;clear();try{get('source').value=readable(meshLabPreset(get('preset').value));return run();}catch(error){reject(error,'初期値');return null;}});
 on('save','click',()=>{if(disposed||!state)return;try{return saveFile({text:serializeMeshLab(state,get('projection').value,ordinal()),filename:'pikapika-sphere-triangle-mesh-query.json',mime:'application/json'});}catch(error){reject(error,'保存');}});
 const api={run,retry,getState:()=>state?own(state):null,dispose(){if(disposed)return;clear('ラボを終了しました。');get('controls').disabled=true;get('retry').disabled=true;disposed=true;runtime=null;generation++;for(const [name,event,fn]of listeners)get(name).removeEventListener?.(event,fn);}};
 await retry();return api;
}
if(typeof document!=='undefined')initializeSphereTriangleMeshLab();
