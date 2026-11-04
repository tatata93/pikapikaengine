import {createLensSpotProfile,serializeLensSpotProfile,parseLensSpotProfile,evaluateLensSpotProfile} from '../engine/optical-camera.mjs';
import {loadSimulationRuntime} from '../engine/simulation.mjs';

const copy=x=>JSON.parse(JSON.stringify(x));
const colors=['#a9baff','#7ee1d1','#ffbf75','#eea9df','#aad58c','#ffe19c','#9bd6ff','#dedee9'];
const number=x=>Number.isFinite(x)?Number(x).toPrecision(7):'—';
const interval=(x,label)=>{if(!Array.isArray(x)||x.length!==2||!x.every(Number.isFinite)||x[0]>x[1])throw new Error(`${label}: 有限の包含区間がありません`);return x;};
const vector=(x,label)=>{if(!Array.isArray(x)||x.length!==3)throw new Error(`${label}: 3座標がありません`);return x.map(v=>interval(v,label));};
const rangeText=(x,scale=1)=>x?`[${number(x[0]*scale)}, ${number(x[1]*scale)}]`:'—';
const category=s=>s==='accepted'?'accepted':s==='route_miss'?'routeMiss':s==='branch_unavailable'?'branchUnavailable':s==='sensor_miss'?'sensorMiss':s==='not_examined'?'notExamined':'unknown';
const names={accepted:'到達',routeMiss:'指定光路なし',branchUnavailable:'選択枝なし',sensorMiss:'センサー外',unknown:'未解決等',notExamined:'未実行'};

// Only presentation: no intersection, refractive law, or pupil integration here.
// Approximate sums below label original geometric weights, not certified moments.
export function lensSpotDisplayData(output){
  if(!output?.profile||!Array.isArray(output.channels)||!Array.isArray(output.nodes))throw new Error('スポット結果の構造が不正です');
  return output.channels.map((channel,channelIndex)=>{
    const counts=Object.fromEntries(Object.keys(names).map(k=>[k,0])),weights={...counts},points=[],result=channel.result;
    if(!result){counts.unknown=output.nodes.length;weights.unknown=output.nodes.reduce((sum,n)=>sum+n.weight,0);return {channel,channelIndex,counts,weights,points,stats:null};}
    if(!Array.isArray(result.records))throw new Error('標本の原記録がありません');
    for(const record of result.records){
      if(!Number.isFinite(record.weight)||record.weight<=0)throw new Error('標本の原重みが不正です');
      const key=category(record.status);++counts[key];weights[key]+=record.weight;
      if(key==='accepted'){
        if(record.sensor?.status!=='hit'||!record.sensor.hit)throw new Error('到達した標本にセンサー位置の包含がありません');
        points.push({sampleIndex:record.sampleIndex,weight:record.weight,position:vector(record.sensor.hit.position,'センサー位置')});
      }
    }
    if(result.records.length!==output.nodes.length)throw new Error('未実行を含む標本記録が不足しています');
    if((counts.unknown||counts.notExamined)&&result.stats!==null)throw new Error('未解決・未実行がある結果に最終統計を表示できません');
    const stats=result.stats;
    if(stats){interval(stats.totalWeight,'全重み');interval(stats.acceptedWeight,'到達重み');if(stats.moments){vector(stats.moments.centroid,'重心');vector(stats.moments.hull,'位置範囲');interval(stats.moments.meanSquaredRadius,'RMS²');}}
    return {channel,channelIndex,counts,weights,points,stats};
  });
}

export function drawLensSpot(canvas,rows=[]){
  const ctx=canvas.getContext('2d');if(!ctx)return;
  const w=canvas.width,h=canvas.height,pad=60,cx=w/2,cy=h/2;
  ctx.fillStyle='#0d1824';ctx.fillRect(0,0,w,h);
  let extent=1e-6;
  for(const row of rows)for(const point of row.points)for(let k=0;k<2;++k)extent=Math.max(extent,...point.position[k].map(Math.abs));
  extent*=1.15;const scale=Math.min(w-2*pad,h-2*pad)/(2*extent);
  ctx.strokeStyle='#45556b';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(pad,cy);ctx.lineTo(w-pad,cy);ctx.moveTo(cx,pad);ctx.lineTo(cx,h-pad);ctx.stroke();
  ctx.fillStyle='#c7d8e9';ctx.font='14px system-ui';ctx.fillText(`X ±${number(extent*1e3)} mm`,pad,h-20);ctx.fillText(`Y ±${number(extent*1e3)} mm`,pad,25);ctx.fillText('0',cx+5,cy+18);
  for(const row of rows){ctx.strokeStyle=colors[row.channelIndex%colors.length];ctx.fillStyle=ctx.strokeStyle;
    for(const point of row.points){const [x,y]=point.position,px=cx+(x[0]+(x[1]-x[0])/2)*scale,py=cy-(y[0]+(y[1]-y[0])/2)*scale;
      ctx.strokeRect(cx+x[0]*scale,cy-y[1]*scale,Math.max(1,(x[1]-x[0])*scale),Math.max(1,(y[1]-y[0])*scale));ctx.beginPath();ctx.arc(px,py,2.2,0,2*Math.PI);ctx.fill();}
  }
  if(!rows.length){ctx.fillStyle='#c7d8e9';ctx.fillText('条件を指定し「この条件で計算する」を押してください',pad,cy-35);}
}

function downloadJson(name,text){const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),0);}
const defaultYield=()=>new Promise(resolve=>{if(typeof requestAnimationFrame==='function')requestAnimationFrame(()=>resolve());else setTimeout(resolve,0);});
const friendly=error=>/API unavailable|matching WebAssembly|rebuild/i.test(error?.message??'')?'同梱WASMがこのラボに未対応です。配信を更新し、計算核を再読込してください。':error?.message??String(error);

export async function initializeLensSpotLab({doc=globalThis.document,loadRuntime=loadSimulationRuntime,evaluate=evaluateLensSpotProfile,now=()=>performance.now(),yieldControl=defaultYield,saveJson=downloadJson}={}){
  const get=id=>doc.getElementById(id),fields=['spot-aperture','spot-sensor-z','spot-samples','spot-source-mode','spot-tan-x','spot-tan-y','spot-source-x','spot-source-y','spot-source-z'];
  let profile=createLensSpotProfile(),output=null,runtime=null,busy=false,sourceEdited=false,lastError=null;const dirty=new Set();
  const error=e=>{lastError=e;get('spot-error').hidden=!e;get('spot-error').textContent=e?friendly(e):'';};
  const lock=()=>{get('spot-controls').disabled=busy||!runtime;get('spot-retry').disabled=busy;get('spot-save-result').disabled=busy||!output;};
  const sourceVisibility=()=>{get('spot-parallel-controls').hidden=get('spot-source-mode').value!=='parallel';get('spot-finite-controls').hidden=get('spot-source-mode').value!=='finite';};
  const clear=()=>{output=null;get('spot-table').replaceChildren();get('spot-result-json').textContent='結果なし';get('spot-summary').textContent='未実行';get('spot-progress').value=0;get('spot-progress-text').textContent='未実行';get('spot-elapsed').textContent='計算時間: —';drawLensSpot(get('spot-view'));lock();};
  const showProfile=()=>{get('spot-profile-json').textContent=serializeLensSpotProfile(profile);};
  const legend=wavelengths=>{get('spot-legend').replaceChildren();wavelengths.forEach((wavelength,i)=>{const span=doc.createElement('span');span.textContent=`● ${number(wavelength*1e9)} nm`;span.style.color=colors[i%colors.length];get('spot-legend').appendChild(span);});};
  const populate=()=>{
    get('spot-aperture').value=String(profile.apertureRadius*1000);get('spot-sensor-z').value=String(profile.sensorZ*1000);
    const sampleText=`${profile.radialSamples}x${profile.angularSamples}`;
    if(!['2x8','4x16','8x32','16x64'].includes(sampleText)){
      const option=doc.createElement('option');option.value=sampleText;option.textContent=`読込: ${profile.radialSamples}半径 × ${profile.angularSamples}角度`;get('spot-samples').appendChild(option);
    }
    get('spot-samples').value=sampleText;get('spot-source-mode').value=profile.source.kind;
    const direction=profile.source.direction??[0,0,1],position=profile.source.position??[0,0,-1];
    get('spot-tan-x').value=String(direction[0]/direction[2]);get('spot-tan-y').value=String(direction[1]/direction[2]);
    ['x','y','z'].forEach((axis,i)=>{get('spot-source-'+axis).value=String(position[i]);});sourceEdited=false;dirty.clear();sourceVisibility();showProfile();legend(profile.wavelengths);
  };
  const read=()=>{
    const numeric=id=>{const text=String(get(id).value).trim();if(!text||!Number.isFinite(Number(text)))throw new Error('入力を有限の数値で指定してください: '+id);return Number(text);};
    const match=/^(\d+)x(\d+)$/.exec(get('spot-samples').value);if(!match)throw new Error('瞳標本数を指定してください');
    let source=profile.source;
    if(sourceEdited){const mode=get('spot-source-mode').value;if(mode==='parallel')source={kind:mode,direction:[numeric('spot-tan-x'),numeric('spot-tan-y'),1]};else if(mode==='finite')source={kind:mode,position:['x','y','z'].map(axis=>numeric('spot-source-'+axis))};else throw new Error('入射光の種類が不正です');}
    return createLensSpotProfile({...profile,apertureRadius:dirty.has('spot-aperture')?numeric('spot-aperture')/1000:profile.apertureRadius,sensorZ:dirty.has('spot-sensor-z')?numeric('spot-sensor-z')/1000:profile.sensorZ,radialSamples:dirty.has('spot-samples')?Number(match[1]):profile.radialSamples,angularSamples:dirty.has('spot-samples')?Number(match[2]):profile.angularSamples,source});
  };
  const render=()=>{
    const rows=lensSpotDisplayData(output);get('spot-table').replaceChildren();legend(output.channels.map(c=>c.wavelength));
    for(const row of rows){const tr=doc.createElement('tr');const add=text=>{const td=doc.createElement('td');td.textContent=text;tr.appendChild(td);};
      add(`${number(row.channel.wavelength*1e9)} nm`);
      add(Object.keys(names).map(key=>`${names[key]} ${row.counts[key]}`).join(' / ')+` — ${row.channel.result?.status??'分散が未確定'}`);
      add(Object.keys(names).map(key=>`${names[key]} Σw≈${number(row.weights[key])}`).join(' / '));
      let stats='—（最終統計なし。未解決・未実行を0へ置換しません）';
      if(row.stats){const m=row.stats.moments;stats=`全重み ${rangeText(row.stats.totalWeight)} / 到達重み ${rangeText(row.stats.acceptedWeight)}\n`+(m?`重心X ${rangeText(m.centroid[0],1e3)} mm / Y ${rangeText(m.centroid[1],1e3)} mm\nRMS² ${rangeText(m.meanSquaredRadius,1e6)} mm²`:'到達標本なし：重心・RMS² —');}
      add(stats);get('spot-table').appendChild(tr);
    }
    drawLensSpot(get('spot-view'),rows);get('spot-result-json').textContent=JSON.stringify(output,null,2);
    get('spot-summary').textContent=`${rows.length}波長 / ${output.nodes.length}標本/λ。内訳Σw≈は原重みの表示用和で、最終統計の包含ではありません。波長色はラベルであり輝度ではありません。`;
    get('runtime-info').textContent=JSON.stringify(output.diagnostics??runtime?.diagnostics??{});
  };
  const change=id=>{
    if(busy)return;dirty.add(id);if(['spot-source-mode','spot-tan-x','spot-tan-y','spot-source-x','spot-source-y','spot-source-z'].includes(id))sourceEdited=true;
    sourceVisibility();clear();try{profile=read();showProfile();error(null);get('spot-status').textContent='条件を変更しました。計算ボタンを押してください。';}catch(e){get('spot-profile-json').textContent='入力が不正です。前の結果は消去しました。';error(e);get('spot-status').textContent='入力を修正してください。';}
  };
  const calculate=async()=>{
    if(busy||!runtime)return null;clear();error(null);
    try{profile=read();showProfile();}catch(e){error(e);get('spot-status').textContent='入力を修正してください。';return null;}
    busy=true;lock();const started=now();get('spot-status').textContent='実C++で幾何スポットを計算中…';get('spot-progress-text').textContent='計算を開始します';
    const elapsed=()=>{get('spot-elapsed').textContent=`経過 ${number(now()-started)} ms（この操作の実測）`;};const timer=setInterval(elapsed,100);
    try{
      await yieldControl();
      const result=await evaluate(runtime,copy(profile),{yieldControl,onProgress:p=>{if(!Number.isFinite(p.completed)||!Number.isFinite(p.total)||p.total<=0||p.completed<0||p.completed>p.total)throw new Error('進行情報が不正です');get('spot-progress').max=p.total;get('spot-progress').value=p.completed;get('spot-progress-text').textContent=`${p.phase==='launch'?'発射条件':'波長ごとの照会'} ${p.completed} / ${p.total}${p.wavelength?` — ${number(p.wavelength*1e9)} nm`:''}`;elapsed();}});
      // Validate all channel DTOs before exposing any new result.
      lensSpotDisplayData(result);output=result;render();get('spot-status').textContent='計算を終了しました。未解決・欠落・未実行と重みの内訳も確認してください。';return copy(output);
    }catch(e){clear();error(e);get('spot-status').textContent='計算を終了できませんでした。条件修正や計算核の再読込後に再試行できます。';return null;
    }finally{clearInterval(timer);elapsed();busy=false;lock();}
  };
  const retry=async()=>{
    if(busy)return;runtime=null;busy=true;clear();error(null);lock();get('spot-status').textContent='共通計算核を読込み中…';
    try{runtime=await loadRuntime();get('runtime-info').textContent=JSON.stringify(runtime?.diagnostics??{});get('spot-status').textContent='準備できました。条件を指定し、計算ボタンを押してください。';}
    catch(e){error(e);get('spot-status').textContent='計算核を読込めませんでした。再読込で同じ条件から再試行できます。';get('runtime-info').textContent='計算核なし（代替計算なし）';}
    finally{busy=false;lock();}
  };
  const loadProfile=async text=>{
    if(busy)return false;clear();try{const next=parseLensSpotProfile(text);profile=next;populate();error(null);get('spot-status').textContent='profileを読込みました。計算ボタンを押すまで再計算しません。';return true;}
    catch(e){error(e);get('spot-status').textContent='profileを読込めませんでした。入力JSONを修正してください。';return false;}
  };
  fields.forEach(id=>get(id).addEventListener(id==='spot-source-mode'||id==='spot-samples'?'change':'input',()=>change(id)));
  get('spot-calculate').addEventListener('click',calculate);get('spot-retry').addEventListener('click',retry);
  get('spot-reset').addEventListener('click',()=>{if(busy)return;profile=createLensSpotProfile();populate();clear();error(null);get('spot-status').textContent='既定条件に戻しました。計算ボタンを押してください。';});
  get('spot-save-profile').addEventListener('click',()=>{if(busy)return;try{profile=read();showProfile();saveJson('pikapika-lens-spot-profile.json',serializeLensSpotProfile(profile));error(null);}catch(e){clear();error(e);}});
  get('spot-save-result').addEventListener('click',()=>{if(!busy&&output)saveJson('pikapika-lens-spot-result.json',JSON.stringify(output,null,2)+'\n');});
  get('spot-load-profile').addEventListener('change',async()=>{const file=get('spot-load-profile').files?.[0];if(!file||busy)return;try{if(file.size>2*1024*1024)throw new Error('profile JSONは2MiB以下にしてください');await loadProfile(await file.text());}catch(e){clear();error(e);}finally{get('spot-load-profile').value='';}});
  populate();clear();await retry();return {calculate,retry,loadProfile,getState:()=>({profile:copy(profile),output:output?copy(output):null,busy,error:lastError?friendly(lastError):null})};
}
if(typeof document!=='undefined')initializeLensSpotLab().catch(error=>{const node=document.getElementById('spot-error');if(node){node.hidden=false;node.textContent=friendly(error);}});
