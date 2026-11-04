// Fixed input public API proof, independent of a future manual flight editor.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs';
const root=new URL('../../',import.meta.url),budget={maxBytes:8388608,maxDepth:64,maxNodes:1000000};
const html=await readFile(new URL('index.html',root),'utf8'),build=html.match(/\?build=([a-f0-9]{16})/)[1];
const sourceMap=JSON.parse(html.match(/<script type="importmap" id="engine-imports">([\s\S]*?)<\/script>/)[1]);
const imports=Object.fromEntries(Object.entries(sourceMap.imports).map(([k,v])=>[k.replace(/^\.\//,'../../'),v.replace(/^\.\//,'../../')]));
const inputs=[];
for(const [mode,path,name] of [
  ['held','reports/sphere-triangle-mesh-held-load-checks/run-20261104-final/native-fixtures.json','analytic-chord-false-safe-force-gravity'],
  ['guard','reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final/native-fixtures.json','held-input-static-face'],
]){
  const fixture=parseStrictJson(await readFile(new URL(path,root),'utf8'),budget).fixtures.find(f=>f.name===name);
  if(!fixture)throw Error('Missing fixed fixture '+name);inputs.push({mode,name,input:fixture.input});
}
const page=`<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>保持荷重と自由伝播guardの所有API | pikapikaengine</title><link rel="stylesheet" href="../../docs/learn/learn.css"><style>main{max-width:1080px;margin:auto;padding:1.5rem}pre{max-height:30rem;overflow:auto;white-space:pre;font-size:.8rem}figure img{width:100%;height:auto}button{margin:1rem 0}</style><script type="importmap">${JSON.stringify({imports})}</script></head><body><main>
<p><a href="../../index.html">← エンジン</a> · <a href="../../docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS.md">所有APIの契約</a></p>
<p class="eyebrow">HELD LOAD / FREE FLIGHT GUARD / FIXED INPUT PROOF</p><h1>曲線と丸め伝播の診断を、<br>次の照会の後にも保持する。</h1>
<p>固定Native原入力2例を公開JavaScript APIで照会し、元入力・全audit・partition・mesh候補と成功candidateを省略せず表示します。距離はm、時間は秒です。</p>
<p class="notice">read-only照会です。Worldの時間進行・衝突応答・流体・材料損傷を計算する画面ではありません。入力編集UIは後続です。</p>
<button id="run" disabled>固定2例を実WASMで照会する</button><p id="status" role="status">共有SDKを準備中。HTTP/HTTPS配信が必要です。</p><p id="error" role="alert" hidden></p>
<details><summary>固定原入力の完全JSON</summary><pre id="input"></pre></details><h2>結果の概要</h2><pre id="summary">未実行</pre><h2>所有した全結果</h2><pre id="result">未実行</pre>
<figure><img src="../../docs/learn/diagrams/sphere-triangle-mesh-flight-owned.svg" width="1080" height="740" alt="全6能力を確認し、元入力とsnapshot、inflated照会とcandidateを別々に所有する。"><figcaption>原著の所有構造の模式図。測定図ではありません。</figcaption></figure>
<script id="fixture" type="application/json">${stringifyStrictJson(inputs,budget)}</script></main><script type="module">
import {loadSimulationRuntime} from '../../engine/simulation.mjs?build=${build}';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs?build=${build}';
const el=id=>document.getElementById(id),budget={maxBytes:8388608,maxDepth:64,maxNodes:1000000};
const inputs=parseStrictJson(el('fixture').textContent,budget);el('input').textContent=stringifyStrictJson(inputs,budget);
try{const runtime=await loadSimulationRuntime();el('status').textContent='共有WASMを準備しました。固定例を照会できます。';el('run').disabled=false;
el('run').onclick=()=>{el('result').textContent='未実行';el('error').hidden=true;
try{const rows=inputs.map(row=>{const q=row.input;const result=row.mode==='held'?runtime.querySphereTriangleMeshHeldLoad(q.sphere,q.triangles,q.horizon,q.settings):runtime.querySphereTriangleMeshFreeFlightGuard(q.body,q.gravity,q.triangles,q.horizon,q.settings);return {...row,result};});
el('summary').textContent=JSON.stringify(rows.map(r=>({mode:r.mode,name:r.name,status:r.result.status,reason:r.result.reason})),null,2);
el('result').textContent=stringifyStrictJson({schema:1,kind:'sphere-triangle-mesh-flight-owned-browser-proof',rows,diagnostics:runtime.diagnostics},budget);
el('status').textContent='2例の全所有結果を表示しました。第1結果は第2照会後の値です。';
}catch(error){el('error').hidden=false;el('error').textContent=String(error);el('status').textContent='照会を拒否しました。';}};
}catch(error){el('error').hidden=false;el('error').textContent=String(error);el('status').textContent='共有SDKを読み込めませんでした。';}
</script></body></html>\n`;
const directory=new URL('reports/sphere-triangle-mesh-flight-js-browser/',root);await mkdir(directory,{recursive:true});
await writeFile(new URL('index.html',directory),page);console.log(JSON.stringify({build,inputs:inputs.map(x=>x.name),bytes:Buffer.byteLength(page)}));
