// A fixed public-method proof page, separate from the later manual entry editor.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs';
const root=new URL('../../',import.meta.url);
const html=await readFile(new URL('index.html',root),'utf8'),build=html.match(/\?build=([a-f0-9]{16})/)[1];
const original=JSON.parse(html.match(/<script type="importmap" id="engine-imports">([\s\S]*?)<\/script>/)[1]);
const imports=Object.fromEntries(Object.entries(original.imports).map(([k,v])=>[k.replace(/^\.\//,'../../'),v.replace(/^\.\//,'../../')]));
const pure=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-entry-checks/run-20261104-final/native-fixtures.json',root),'utf8'),{maxBytes:8388608,maxDepth:32,maxNodes:1000000});
const input=pure.fixtures.find(f=>f.name==='analytic-entry-quarter').input;
const page=`<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>貫通開始窓の所有APIを実行する | pikapikaengine</title><link rel="stylesheet" href="../../docs/learn/learn.css">
<style>main{max-width:1080px;margin:auto;padding:1.5rem}pre{max-height:28rem;overflow:auto;font-size:.8rem;white-space:pre}figure img{width:100%;height:auto}button{margin:1rem 0}</style>
<script type="importmap">${JSON.stringify({imports})}</script></head><body><main>
<p><a href="../../index.html">← エンジン</a> · <a href="../../docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md">所有APIの契約と検証</a></p>
<p class="eyebrow">OWNED ENTRY WINDOW / FIXED INPUT PROOF</p><h1>貫通開始窓の全診断を、<br>実WASMから所有する。</h1>
<p>既受入Nativeの固定例を公開JavaScript APIへ渡します。初期の正証拠・closed安全prefix・負witness・外向き窓幅と全partitionを、そのまま保存対象へ表示します。</p>
<p class="notice">parameterは無次元です。単一根・厳密な物理時刻・接触応答・ゲーム接触を計算する画面ではありません。入力編集ラボは後続です。</p>
<button id="run" disabled>固定経路を実WASMで照会する</button><p id="status" role="status">共有SDKの準備中。HTTP/HTTPS配信が必要です。</p><p id="error" role="alert" hidden></p>
<details><summary>固定原入力の完全JSON</summary><pre id="input"></pre></details>
<h2>返された窓と先行証拠</h2><pre id="summary">未実行</pre>
<h2>所有した全結果</h2><p>省略しない全原本・audit・partition/tail・lastMeshと負零を表示します。画面のscrollは保存内容を削りません。</p><pre id="result">未実行</pre>
<figure><img src="../../docs/learn/diagrams/sphere-triangle-mesh-entry-owned.svg" width="1000" height="620" alt="原入力と共有scratch、Native snapshotと旧結果を別々に所有する。"><figcaption>原著の所有構造の模式図。実行結果や性能の測定図ではありません。</figcaption></figure>
<script id="fixture" type="application/json">${stringifyStrictJson(input)}</script></main>
<script type="module">
import {loadSimulationRuntime} from '../../engine/simulation.mjs?build=${build}';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs?build=${build}';
const el=id=>document.getElementById(id),budget={maxBytes:8388608,maxDepth:32,maxNodes:1000000};
const q=parseStrictJson(el('fixture').textContent,budget);el('input').textContent=stringifyStrictJson(q,budget);
try{const runtime=await loadSimulationRuntime();el('status').textContent='共有WASMを準備しました。固定例を照会できます。';el('run').disabled=false;
el('run').onclick=()=>{el('result').textContent='未実行';el('error').hidden=true;
try{const result=runtime.querySphereTriangleMeshEntry({start:q.start,end:q.end,radius:q.radius},q.triangles,q.settings);
const packet={schema:1,kind:'sphere-triangle-mesh-entry-owned-browser-proof',input:q,result,diagnostics:runtime.diagnostics};
el('summary').textContent=JSON.stringify({status:result.status,initialSeparationProven:result.initialSeparationProven,safePrefix:result.safePrefix,window:result.window,bestWitnessParameter:result.bestWitness?.parameter??null},null,2);
el('result').textContent=stringifyStrictJson(packet,budget);el('status').textContent=result.status+' / '+result.reason+' / '+result.audits.length+' audits / '+result.partition.length+' partition';
}catch(error){el('error').hidden=false;el('error').textContent=String(error);el('status').textContent='照会を拒否しました。古い結果は表示しません。';}};
}catch(error){el('status').textContent='共有SDKを読み込めませんでした。';el('error').hidden=false;el('error').textContent=String(error);}
</script></body></html>\n`;
const directory=new URL('reports/sphere-triangle-mesh-entry-js-browser/',root);await mkdir(directory,{recursive:true});await writeFile(new URL('index.html',directory),page);console.log(JSON.stringify({build,fixedInput:'analytic-entry-quarter',bytes:Buffer.byteLength(page)}));
