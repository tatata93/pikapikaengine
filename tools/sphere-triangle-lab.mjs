import {parseStrictJson,stringifyStrictJson} from '../engine/strict-json.mjs';

const defaults=Object.freeze({maxCandidates:7,sqrtRefinements:128,maxTotalSqrtRefinements:1024,maximumLocalWidth:1e-7,maximumNormalWidth:1e-8,minimumSineSquared:1e-12});
const budget={maxBytes:32768,maxDepth:8,maxNodes:2048};
const projectionAxes={xy:[0,1],xz:[0,2],yz:[1,2]};
const own=value=>parseStrictJson(stringifyStrictJson(value,{maxBytes:262144,maxDepth:16,maxNodes:20000}),{maxBytes:262144,maxDepth:16,maxNodes:20000});
const readable=(value,depth=0)=>Array.isArray(value)?'['+value.map(v=>readable(v,depth)).join(', ')+']':value&&typeof value==='object'?'{\n'+Object.entries(value).map(([k,v])=>'  '.repeat(depth+1)+JSON.stringify(k)+': '+readable(v,depth+1)).join(',\n')+'\n'+'  '.repeat(depth)+'}':stringifyStrictJson(value);
export function triangleLabPreset(name='face'){
 const input={sphere:{position:[1,2,1],radius:.5},triangle:{id:17,vertices:[[0,0,0],[4,0,0],[0,0,4]]},settings:{...defaults}};
 const positions={face:[1,2,1],edge_ab:[2,2,-1],edge_bc:[3,2,3],edge_ca:[-1,2,2],vertex_a:[-1,2,-1],vertex_b:[5,2,-1],vertex_c:[-1,2,5],back:[1,-2,1],coincident:[0,0,0]};
 if(Object.hasOwn(positions,name))input.sphere.position=[...positions[name]];
 else if(name==='degenerate')input.triangle.vertices=[[0,0,0],[4,0,0],[8,0,0]];
 else if(name==='thin')input.triangle.vertices=[[0,0,0],[4,0,0],[4,0,2**-30]];
 else if(name==='budget')input.settings.maxCandidates=3;
 else if(name==='normal_precision')input.settings.maximumNormalWidth=1e-30;
 else throw new Error('Unknown sphere triangle preset: '+name);
 return input;
}
function keys(value,allowed,required,label){
 if(!value||Array.isArray(value)||typeof value!=='object'||Object.keys(value).some(k=>!allowed.includes(k))||required.some(k=>!Object.hasOwn(value,k)))throw new Error(label+' has missing or unknown keys');
}
export function parseTriangleLabInput(text){
 const q=parseStrictJson(text,budget);keys(q,['sphere','triangle','settings'],['sphere','triangle','settings'],'Input');
 keys(q.sphere,['position','radius'],['position','radius'],'Sphere');keys(q.triangle,['id','vertices'],['id','vertices'],'Triangle');keys(q.settings,Object.keys(defaults),[],'Settings');
 const vector=x=>Array.isArray(x)&&x.length===3&&x.every(Number.isFinite);
 if(!vector(q.sphere.position)||!Number.isFinite(q.sphere.radius)||!Number.isFinite(q.triangle.id)||!Array.isArray(q.triangle.vertices)||q.triangle.vertices.length!==3||!q.triangle.vertices.every(vector)||!Object.values(q.settings).every(Number.isFinite))throw new Error('Source requires finite XYZ vectors and numeric settings');
 q.settings={...defaults,...q.settings};return q;
}
export function evaluateTriangleLab(runtime,source){
 const input=parseTriangleLabInput(stringifyStrictJson(source,budget));
 if(typeof runtime?.querySphereTriangle!=='function')throw new Error('Sphere triangle API unavailable');
 const result=runtime.querySphereTriangle(input.sphere,input.triangle,input.settings);
 return own({schema:1,kind:'sphere-triangle-lab',input,result,diagnostics:runtime.diagnostics});
}
export function serializeTriangleLab(packet,projection='xz'){
 if(!Object.hasOwn(projectionAxes,projection))throw new Error('Unknown projection');
 if(packet?.schema!==1||packet.kind!=='sphere-triangle-lab')throw new Error('No actual triangle query to save');
 return stringifyStrictJson({...packet,projection},{maxBytes:262144,maxDepth:16,maxNodes:20000})+'\n';
}
// Drawing only: source points and returned interval rectangles are projected.
// No closest point/normal midpoint, distance computation or contact fallback.
export function triangleProjection(source,result,projection='xz'){
 if(!Object.hasOwn(projectionAxes,projection))throw new Error('Unknown projection');
 const axes=projectionAxes[projection],positions=[source.sphere.position,...source.triangle.vertices],g=result.status==='completed'?result.geometry:null;
 if(g)for(const end of [0,1])positions.push(g.closest.map(b=>b[end]));
 const extent=axes.map(axis=>[Math.min(...positions.map(p=>p[axis]),source.sphere.position[axis]-Math.abs(source.sphere.radius)),Math.max(...positions.map(p=>p[axis]),source.sphere.position[axis]+Math.abs(source.sphere.radius))]);
 const span=Math.max(1e-300,...extent.map(b=>b[1]-b[0])),scale=Math.min(740,300)/span,center=extent.map(b=>b[0]/2+b[1]/2);
 const project=p=>[450+(p[axes[0]]-center[0])*scale,220-(p[axes[1]]-center[1])*scale];
 const triangle=source.triangle.vertices.map(project),sphereCenter=project(source.sphere.position),radius=source.sphere.radius>0?source.sphere.radius*scale:0;
 let closest=null;
 if(g){const x=g.closest[axes[0]],y=g.closest[axes[1]],a=project(g.closest.map(b=>b[0])),b=project(g.closest.map(b=>b[1]));closest={x:Math.min(a[0],b[0]),y:Math.min(a[1],b[1]),width:(x[1]-x[0])*scale,height:(y[1]-y[0])*scale};}
 const numbers=[scale,...triangle.flat(),...sphereCenter,radius,...Object.values(closest??{})];
 if(!numbers.every(Number.isFinite)||scale<=0)return {available:false,projection,reason:'投影の数値範囲を超えています。計算結果の区間表を参照してください。'};
 return {available:true,projection,triangle,sphereCenter,radius,closest,scale};
}
function download({text,filename,mime}){
 const url=URL.createObjectURL(new Blob([text],{type:mime})),a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);
}
export async function initializeSphereTriangleLab({doc=globalThis.document,loadRuntime=async()=>{const {loadSimulationRuntime}=await import('../engine/simulation.mjs');return loadSimulationRuntime();},saveFile=download}={}){
 const get=id=>doc.getElementById(id),listeners=[];let runtime=null,state=null,generation=0,loading=null,disposed=false;
 const on=(id,event,fn)=>{get(id).addEventListener(event,fn);listeners.push([id,event,fn]);};
 const clear=(message='入力が変更されました。照会を実行してください。')=>{
  state=null;get('triangle-save').disabled=true;get('triangle-geometry').textContent='—';get('triangle-candidates').textContent='—';get('triangle-json').textContent='';get('triangle-view').innerHTML='';get('triangle-view').setAttribute('aria-label','計算結果は表示していません。');get('triangle-status').textContent=message;get('triangle-error').hidden=true;get('triangle-note').textContent='';
 };
 const rejected=(error,stage)=>{clear('照会に失敗しました。成功geometryは表示していません。');get('triangle-error').hidden=false;get('triangle-error').textContent=stage+': '+error.message;};
 function draw(){
  if(!state||disposed)return;
  const view=triangleProjection(state.input,state.result,get('triangle-projection').value),svg=get('triangle-view');
  if(!view.available){svg.innerHTML='';svg.setAttribute('aria-label',view.reason);get('triangle-note').textContent=view.reason;return;}
  const {triangle,sphereCenter,radius,closest}=view;
  svg.innerHTML=`<rect width="900" height="440" fill="#0b1722"/><polygon points="${triangle.map(p=>p.join(',')).join(' ')}" fill="#244653" stroke="#7ee1d1" stroke-width="2"/><circle cx="${sphereCenter[0]}" cy="${sphereCenter[1]}" r="${radius}" fill="none" stroke="#ffbf75" stroke-width="2"/><circle cx="${sphereCenter[0]}" cy="${sphereCenter[1]}" r="3" fill="#ffbf75"/>`+
   triangle.map((p,i)=>`<text x="${p[0]+8}" y="${p[1]-8}" fill="#b6d5df" font-size="18">${'ABC'[i]}</text>`).join('')+
   (closest?`<rect x="${closest.x}" y="${closest.y}" width="${closest.width}" height="${closest.height}" fill="#fff" stroke="#fff" stroke-width="3"/>`:'');
  svg.setAttribute('aria-label',`${view.projection.toUpperCase()}投影。${state.result.status}。${closest?'白い領域は最近接点の返却区間。細い区間は3pxの線幅で表示。':'成功geometryはありません。'}`);
  get('triangle-note').textContent=`${view.projection.toUpperCase()}への説明用投影 / 縮尺 ${view.scale.toPrecision(5)} px/m。白い領域は返却区間、最小線幅3px。接触点の中点・単位法線・時間発展は描いていません。`;
 }
 function run(){
  if(disposed||!runtime)return null;
  ++generation;clear('照会中…');let input;
  try{input=parseTriangleLabInput(get('triangle-source').value);}catch(error){rejected(error,'入力JSON');return null;}
  try{
   const next=evaluateTriangleLab(runtime,input);state=next;const r=next.result;
   get('triangle-status').textContent=r.status==='completed'?`成功 / ${r.geometry.relation}`:`モデル失敗 / ${r.status} / ${r.reason}`;
   get('triangle-geometry').textContent=r.geometry?readable(r.geometry):'geometry: null（成功形状なし）';get('triangle-candidates').textContent=r.candidates.map((c,i)=>`${i}: ${c.feature} / ${c.disposition} / KKT ${c.kktCount}\nbarycentric ${stringifyStrictJson(c.barycentric)}\nkkt ${stringifyStrictJson(c.kkt)}`).join('\n\n')||'候補の記録はありません。';
   get('triangle-json').textContent=serializeTriangleLab(next,get('triangle-projection').value);draw();get('triangle-save').disabled=false;return own(state);
  }catch(error){rejected(error,'SDK交換');return null;}
 }
 async function retry(){
  if(disposed)return null;if(loading)return loading;
  const current=++generation;runtime=null;clear('C++ WebAssemblyを読込み中…');get('triangle-retry').disabled=true;get('triangle-controls').disabled=true;
  loading=Promise.resolve().then(async()=>{try{
   const loaded=await loadRuntime();if(disposed)return null;
   if(typeof loaded?.querySphereTriangle!=='function')throw new Error('Sphere triangle API unavailable');runtime=loaded;get('triangle-controls').disabled=false;get('triangle-runtime').textContent=`${runtime.diagnostics.backend} / ${runtime.diagnostics.wasmBytes} B / build ${runtime.diagnostics.buildId}`;
   if(current!==generation){clear('SDKを読み込みました。現在の入力を照会してください。');return null;}return run();
  }catch(error){if(!disposed){runtime=null;get('triangle-runtime').textContent='SDK未初期化';rejected(error,'SDK初期化');}return null;}
  finally{loading=null;if(!disposed)get('triangle-retry').disabled=false;}});return loading;
 }
 get('triangle-source').value=readable(triangleLabPreset());get('triangle-projection').value='xz';get('triangle-preset').value='face';
 on('triangle-source','input',()=>{if(!disposed){generation++;clear();}});
 on('triangle-preset','change',()=>{if(disposed)return;get('triangle-source').value=readable(triangleLabPreset(get('triangle-preset').value));generation++;clear();if(runtime)run();});
 on('triangle-projection','change',()=>{if(disposed||!state)return;try{draw();get('triangle-json').textContent=serializeTriangleLab(state,get('triangle-projection').value);}catch(error){rejected(error,'表示');}});
 on('triangle-run','click',run);on('triangle-retry','click',retry);
 on('triangle-reset','click',()=>{if(disposed)return;get('triangle-source').value=readable(triangleLabPreset(get('triangle-preset').value));generation++;clear();return run();});
 on('triangle-save','click',()=>{if(disposed||!state)return;try{return saveFile({text:serializeTriangleLab(state,get('triangle-projection').value),filename:'pikapika-sphere-triangle-query.json',mime:'application/json'});}catch(error){rejected(error,'保存');}});
 const api={run,retry,getState:()=>state?own(state):null,dispose(){if(disposed)return;clear('ラボを終了しました。');get('triangle-controls').disabled=true;get('triangle-retry').disabled=true;disposed=true;generation++;for(const [id,event,fn]of listeners)get(id).removeEventListener?.(event,fn);}};
 await retry();return api;
}
if(typeof document!=='undefined')initializeSphereTriangleLab();
