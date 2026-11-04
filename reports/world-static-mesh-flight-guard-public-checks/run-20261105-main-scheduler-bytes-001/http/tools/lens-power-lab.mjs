import {createLensPowerProfile,serializeLensPowerProfile,parseLensPowerProfile,evaluateLensPowerProfile} from '../engine/polarized-camera.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
const copy=x=>JSON.parse(JSON.stringify(x)),colors=['#a9baff','#7ee1d1','#ffbf75','#eea9df','#aad58c','#ffe19c','#9bd6ff','#dedee9'];
const number=x=>Number.isFinite(x)?Number(x).toPrecision(8):'—',range=x=>x?`[${number(x[0])}, ${number(x[1])}]`:'—';
const interval=x=>{if(!Array.isArray(x)||x.length!==2||!x.every(Number.isFinite)||x[0]>x[1])throw new Error('有限の原出力区間がありません');return x;};
const vector=x=>{if(!Array.isArray(x)||x.length!==3)throw new Error('位置の3座標がありません');return x.map(interval);};
const category=s=>s==='accepted'?'accepted':s==='route_miss'?'routeMiss':s==='branch_unavailable'?'branchUnavailable':s==='sensor_miss'?'sensorMiss':s==='not_examined'?'notExamined':'unknown';
const names={accepted:'到達',routeMiss:'指定光路なし',branchUnavailable:'選択枝なし',sensorMiss:'センサー外',unknown:'未解決等',notExamined:'未実行',unadmitted:'未受理・未照会'};
// Presentation only: approximate category sums label original source I, while
// every certified source/detected tally is copied from the C++ final stats.
export function lensPowerDisplayData(output){
  if(!output?.profile||!Array.isArray(output.channels)||!Array.isArray(output.packets))throw new Error('光束結果の構造が不正です');
  const rows=[];
  for(const [channelIndex,channel]of output.channels.entries())for(const path of channel.paths){
    const counts=Object.fromEntries(Object.keys(names).map(k=>[k,0])),watts={...counts},points=[],r=path.result,n=output.packets.length;
    if(!r){counts.unadmitted=n;watts.unadmitted=output.packets.reduce((sum,p)=>sum+p.power[0],0);rows.push({channelIndex,channel,path,counts,watts,points,stats:null});continue;}
    if(!Array.isArray(r.records)||r.records.length>n)throw new Error('原packet記録が不正です');
    for(const record of r.records){if(!Array.isArray(record.power)||record.power.length!==4||!record.power.every(Number.isFinite)||record.power[0]<0)throw new Error('原packetのワット数が不正です');const key=category(record.status);++counts[key];watts[key]+=record.power[0];
      if(key==='accepted'){if(record.sensor?.status!=='hit'||!record.sensor.hit||!record.route?.completion)throw new Error('到達packetの実センサー・経路がありません');interval(record.sensorPower);points.push({packetIndex:record.packetIndex,position:vector(record.sensor.hit.position),sensorPower:record.sensorPower});}
      else if(record.sensorPower!==null)throw new Error('未到達・未知packetを0Wで補えません');
    }
    counts.unadmitted=n-r.records.length;watts.unadmitted=output.packets.slice(r.records.length).reduce((sum,p)=>sum+p.power[0],0);
    if(r.stats){if(r.status!=='completed'||counts.unknown||counts.notExamined||counts.unadmitted)throw new Error('不完全なpacket集合に最終集計は表示できません');for(const key of ['totalSourcePower','acceptedSourcePower','detectedPower'])interval(r.stats[key]);}
    else if(r.status==='completed')throw new Error('完了したpacket集合の最終集計がありません');
    rows.push({channelIndex,channel,path,counts,watts,points,stats:r.stats});
  }
  return rows;
}
export function drawLensPower(canvas,rows=[]){
  const ctx=canvas.getContext('2d');if(!ctx)return;const w=canvas.width,h=canvas.height,pad=55;ctx.fillStyle='#0d1824';ctx.fillRect(0,0,w,h);ctx.font='14px system-ui';
  const points=rows.flatMap(row=>row.points),xs=points.flatMap(p=>p.position[0]),ys=points.flatMap(p=>p.position[1]),cx=xs.length?(Math.min(...xs)+Math.max(...xs))/2:0,cy=ys.length?(Math.min(...ys)+Math.max(...ys))/2:0;
  const extent=Math.max(1e-6,...xs.map(x=>Math.abs(x-cx)),...ys.map(y=>Math.abs(y-cy)))*1.2,scale=Math.min(w-2*pad,h-2*pad)/(2*extent);
  ctx.strokeStyle='#45556b';ctx.beginPath();ctx.moveTo(pad,h/2);ctx.lineTo(w-pad,h/2);ctx.moveTo(w/2,pad);ctx.lineTo(w/2,h-pad);ctx.stroke();ctx.fillStyle='#c7d8e9';ctx.fillText(`X中心 ${number(cx*1000)} / Y中心 ${number(cy*1000)} mm`,pad,24);ctx.fillText(`表示半幅 ±${number(extent*1000)} mm / 点の濃さはWではありません`,pad,h-15);
  for(const row of rows){ctx.strokeStyle=colors[row.channelIndex%colors.length];ctx.fillStyle=ctx.strokeStyle;for(const p of row.points){const [x,y]=p.position,px=w/2+(x[0]+(x[1]-x[0])/2-cx)*scale,py=h/2-(y[0]+(y[1]-y[0])/2-cy)*scale;ctx.strokeRect(w/2+(x[0]-cx)*scale,h/2-(y[1]-cy)*scale,Math.max(1,(x[1]-x[0])*scale),Math.max(1,(y[1]-y[0])*scale));ctx.beginPath();ctx.arc(px,py,2.5,0,2*Math.PI);ctx.fill();}}
  if(!points.length){ctx.fillStyle='#c7d8e9';ctx.fillText(rows.length?'実センサー到達位置なし（未知を0へ補いません）':'条件を指定し、計算ボタンを押してください',pad,h/2-30);}
}
const friendly=e=>/API unavailable|matching WebAssembly|rebuild/i.test(e?.message??'')?'このラボに対応する同梱WASMがありません。配信更新後に計算核を再読込してください。':e?.message??String(e);
const yieldFrame=()=>new Promise(resolve=>{if(typeof requestAnimationFrame==='function')requestAnimationFrame(()=>resolve());else setTimeout(resolve,0);});
function downloadJson(name,text){const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),0);}
export async function initializeLensPowerLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,evaluate=evaluateLensPowerProfile,yieldControl=yieldFrame,now=()=>performance.now(),saveJson=downloadJson}={}){
  const get=id=>doc.getElementById(id),fields=['lp-power','lp-stokes','lp-samples','lp-aperture','lp-tan-x','lp-tan-y','lp-sensor-x','lp-sensor-y','lp-sensor-z','lp-sensor-radius','lp-packet-budget','lp-step-budget','lp-geometry-sqrt','lp-power-sqrt','lp-total-sqrt'];
  let profile=createLensPowerProfile(),output=null,runtime=null,busy=false;const dirty=new Set();
  const error=e=>{get('lp-error').hidden=!e;get('lp-error').textContent=e?friendly(e):'';};
  const lock=()=>{get('lp-controls').disabled=busy||!runtime;get('lp-retry').disabled=busy;get('lp-save-result').disabled=busy||!output;get('lp-inspect').disabled=busy||!output;get('lp-packet').disabled=busy||!output;};
  const option=(value,label)=>{const o=doc.createElement('option');o.value=value;o.textContent=label;return o;};
  const legend=()=>{get('lp-legend').replaceChildren();profile.wavelengths.forEach((w,i)=>{const span=doc.createElement('span');span.textContent=`● ${number(w*1e9)} nm（独立${number(profile.powerWatts)} W実験）`;span.style.color=colors[i%colors.length];get('lp-legend').appendChild(span);});};
  const showProfile=()=>{get('lp-profile-json').textContent=serializeLensPowerProfile(profile);legend();};
  const clear=()=>{output=null;get('lp-table').replaceChildren();get('lp-result-json').textContent='結果なし';get('lp-inspection').textContent='結果なし';get('lp-record-status').textContent='結果なし';get('lp-inspect').replaceChildren();get('lp-summary').textContent='未実行';get('lp-progress').value=0;get('lp-progress-text').textContent='未実行';get('lp-elapsed').textContent='実測時間: —';drawLensPower(get('lp-primary'));drawLensPower(get('lp-ghost'));lock();};
  const populate=()=>{
    const values={'lp-power':profile.powerWatts,'lp-stokes':profile.stokes,'lp-aperture':profile.apertureRadius*1000,'lp-tan-x':profile.source.direction[0]/profile.source.direction[2],'lp-tan-y':profile.source.direction[1]/profile.source.direction[2],'lp-sensor-x':profile.sensor.center[0]*1000,'lp-sensor-y':profile.sensor.center[1]*1000,'lp-sensor-z':profile.sensor.center[2]*1000,'lp-sensor-radius':profile.sensor.apertureRadius*1000,'lp-packet-budget':profile.settings.maximumPacketEvaluations,'lp-step-budget':profile.settings.maximumRouteSteps,'lp-geometry-sqrt':profile.settings.maxSqrtRefinements,'lp-power-sqrt':profile.settings.powerMaxSqrtRefinements,'lp-total-sqrt':profile.settings.maximumTotalSqrtRefinements};
    for(const [id,value]of Object.entries(values))get(id).value=String(value);const samples=`${profile.radialSamples}x${profile.angularSamples}`;if(!['1x4','2x8','4x16','8x32','16x64'].includes(samples))get('lp-samples').appendChild(option(samples,`読込: ${profile.radialSamples}半径 × ${profile.angularSamples}角度`));get('lp-samples').value=samples;get('lp-packet').value='0';dirty.clear();showProfile();
  };
  const read=()=>{
    const numeric=id=>{const s=String(get(id).value).trim();if(!s||!Number.isFinite(Number(s)))throw new Error('空欄でない有限の数値を指定してください: '+id);return Number(s);};
    const changed=(id,old,scale=1)=>dirty.has(id)?numeric(id)*scale:old,parts=/^(\d+)x(\d+)$/.exec(get('lp-samples').value);if(!parts)throw new Error('packet数の組合せが不正です');
    const direction=dirty.has('lp-tan-x')||dirty.has('lp-tan-y')?[numeric('lp-tan-x'),numeric('lp-tan-y'),1]:profile.source.direction;
    return createLensPowerProfile({...profile,powerWatts:changed('lp-power',profile.powerWatts),stokes:get('lp-stokes').value,radialSamples:dirty.has('lp-samples')?Number(parts[1]):profile.radialSamples,angularSamples:dirty.has('lp-samples')?Number(parts[2]):profile.angularSamples,apertureRadius:changed('lp-aperture',profile.apertureRadius,.001),source:{...profile.source,direction},sensor:{center:['x','y','z'].map((axis,i)=>changed('lp-sensor-'+axis,profile.sensor.center[i],.001)),apertureRadius:changed('lp-sensor-radius',profile.sensor.apertureRadius,.001)},settings:{...profile.settings,maximumPacketEvaluations:changed('lp-packet-budget',profile.settings.maximumPacketEvaluations),maximumRouteSteps:changed('lp-step-budget',profile.settings.maximumRouteSteps),maxSqrtRefinements:changed('lp-geometry-sqrt',profile.settings.maxSqrtRefinements),powerMaxSqrtRefinements:changed('lp-power-sqrt',profile.settings.powerMaxSqrtRefinements),maximumTotalSqrtRefinements:changed('lp-total-sqrt',profile.settings.maximumTotalSqrtRefinements)}});
  };
  const inspect=()=>{
    if(!output)return;const [c,p]=get('lp-inspect').value.split(':').map(Number),path=output.channels[c]?.paths[p],n=Number(get('lp-packet').value);
    if(!path||String(get('lp-packet').value).trim()===''||!Number.isInteger(n)||n<0||n>=output.packets.length){get('lp-record-status').textContent='範囲内のpacket番号を指定してください';get('lp-inspection').textContent='結果なし';return;}
    const record=path.result?.records?.find(r=>r.packetIndex===n);get('lp-record-status').textContent=record?`packet ${n} / ${record.status} / 元I ${number(record.power[0])} W / sensorPower ${range(record.sensorPower)} W`:`packet ${n} は未受理・未照会です。最終POWERを0Wで補いません。`;
    get('lp-inspection').textContent=JSON.stringify({wavelength:output.channels[c].wavelength,path:path.id,input:output.packets[n],record:record??null},null,2);
  };
  const render=()=>{
    const rows=lensPowerDisplayData(output);get('lp-table').replaceChildren();get('lp-inspect').replaceChildren();
    for(const row of rows){const tr=doc.createElement('tr'),add=text=>{const td=doc.createElement('td');td.textContent=text;tr.appendChild(td);};add(`${number(row.channel.wavelength*1e9)} nm\n${row.path.id==='primary'?'主透過 T/T':'内部反射 T/R/R/T'}`);add(`${row.path.result?.status??'分散が未確定'}\n`+Object.keys(names).map(k=>`${names[k]} ${row.counts[k]}`).join(' / '));add(Object.keys(names).map(k=>`${names[k]} ΣI≈${number(row.watts[k])} W`).join('\n'));add(row.stats?`全ソース ${range(row.stats.totalSourcePower)} W\n到達の元POWER ${range(row.stats.acceptedSourcePower)} W\n検出 ${range(row.stats.detectedPower)} W`:'—（最終集計なし）');get('lp-table').appendChild(tr);}
    output.channels.forEach((c,i)=>c.paths.forEach((p,j)=>get('lp-inspect').appendChild(option(`${i}:${j}`,`${number(c.wavelength*1e9)} nm / ${p.id}`))));get('lp-inspect').value='0:0';get('lp-packet').max=String(output.packets.length-1);inspect();
    get('lp-summary').textContent=`各λで${output.packets.length}packet・明示${number(profile.powerWatts)} W。各経路は独立した指定列です。波長間・経路間の合計なし。`;get('lp-result-json').textContent=JSON.stringify(output,null,2);get('runtime-info').textContent=JSON.stringify(output.diagnostics??runtime?.diagnostics??{});drawLensPower(get('lp-primary'),rows.filter(r=>r.path.id==='primary'));drawLensPower(get('lp-ghost'),rows.filter(r=>r.path.id==='ghost'));showProfile();
  };
  const calculate=async()=>{
    if(busy||!runtime)return null;clear();error(null);try{profile=read();showProfile();}catch(e){error(e);get('lp-status').textContent='入力を修正してください';return null;}
    busy=true;lock();get('lp-status').textContent='実C++で経路ごとの有限光束を計算中…';const started=now(),elapsed=()=>{get('lp-elapsed').textContent=`経過 ${number(now()-started)} ms（操作の実測）`;},timer=setInterval(elapsed,100);
    try{await yieldControl();const result=await evaluate(runtime,copy(profile),{yieldControl,onProgress:p=>{if(!Number.isFinite(p.completed)||!Number.isFinite(p.total)||p.total<=0||p.completed<0||p.completed>p.total)throw new Error('進行情報が不正です');get('lp-progress').max=p.total;get('lp-progress').value=p.completed;get('lp-progress-text').textContent=`${p.phase==='launch'?'発射条件':'経路照会'} ${p.completed}/${p.total}${p.wavelength?' / '+number(p.wavelength*1e9)+' nm':''}${p.path?' / '+p.path:''}`;elapsed();}});lensPowerDisplayData(result);output=result;render();get('lp-status').textContent='照会を終了しました。各経路の既知・未知・未実行と、最終集計の有無を確認してください。';return copy(output);}
    catch(e){clear();error(e);get('lp-status').textContent='照会できませんでした。古い結果を消去しました。修正や再読込後に再試行できます。';return null;}
    finally{clearInterval(timer);elapsed();busy=false;lock();}
  };
  const retry=async()=>{if(busy)return;runtime=null;busy=true;clear();error(null);lock();get('lp-status').textContent='共通計算核を読込み中…';try{runtime=await loadRuntime();get('runtime-info').textContent=JSON.stringify(runtime?.diagnostics??{});get('lp-status').textContent='準備できました。計算ボタンを押してください。';}catch(e){error(e);get('lp-status').textContent='計算核を読込めません。代替計算なし。再読込できます。';get('runtime-info').textContent='計算核なし';}finally{busy=false;lock();}};
  const loadProfile=async text=>{if(busy)return false;clear();try{profile=parseLensPowerProfile(text);populate();error(null);get('lp-status').textContent='profileを読込みました。計算ボタンを押すまで再実行しません。';return true;}catch(e){error(e);get('lp-status').textContent='profileを読込めませんでした。';return false;}};
  fields.forEach(id=>get(id).addEventListener(id==='lp-stokes'||id==='lp-samples'?'change':'input',()=>{if(busy)return;dirty.add(id);clear();try{profile=read();showProfile();error(null);get('lp-status').textContent='条件を変更しました。計算ボタンを押してください。';}catch(e){error(e);get('lp-profile-json').textContent='入力が不正です。結果は消去しました。';get('lp-status').textContent='入力を修正してください。';}}));
  get('lp-inspect').addEventListener('change',()=>{if(!busy)inspect();});get('lp-packet').addEventListener('input',()=>{if(!busy)inspect();});get('lp-calculate').addEventListener('click',calculate);get('lp-retry').addEventListener('click',retry);
  get('lp-reset').addEventListener('click',()=>{if(busy)return;profile=createLensPowerProfile();populate();clear();error(null);get('lp-status').textContent='既定条件へ戻しました。計算ボタンを押してください。';});
  get('lp-save-profile').addEventListener('click',()=>{if(busy)return;try{profile=read();showProfile();saveJson('pikapika-lens-power-profile.json',serializeLensPowerProfile(profile));error(null);}catch(e){clear();error(e);}});get('lp-save-result').addEventListener('click',()=>{if(!busy&&output)saveJson('pikapika-lens-power-result.json',JSON.stringify(output,null,2)+'\n');});
  get('lp-load-profile').addEventListener('change',async()=>{const file=get('lp-load-profile').files?.[0];if(!file||busy)return;try{if(file.size>2*1024*1024)throw new Error('profile JSONは2MiB以下にしてください');await loadProfile(await file.text());}catch(e){clear();error(e);}finally{get('lp-load-profile').value='';}});
  populate();clear();await retry();return {calculate,retry,loadProfile,getState:()=>({profile:copy(profile),output:output?copy(output):null,busy})};
}
if(typeof document!=='undefined')initializeLensPowerLab().catch(e=>{const n=document.getElementById('lp-error');if(n){n.hidden=false;n.textContent=friendly(e);}});
