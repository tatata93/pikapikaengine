// Generated evidence page: reuse the web builder's import map, rebased to reports.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs';
const root=new URL('../../',import.meta.url);
const index=await readFile(new URL('index.html',root),'utf8');
const sourceMap=JSON.parse(index.match(/<script type="importmap" id="engine-imports">([^<]+)<\/script>/)[1]);
const imports=Object.fromEntries(Object.entries(sourceMap.imports).map(([key,value])=>['../../'+key.replace(/^\.\//,''),'../../'+value.replace(/^\.\//,'')]));
const corpus=parseStrictJson(await readFile(new URL('reports/sphere-triangle-mesh-trajectory-abi-checks/run-20261104-root/native-fixtures.json',root),'utf8'));
const fixture=corpus.fixtures.find(row=>row.name==='short-safe-linear');
if(!fixture)throw Error('Missing frozen browser example');
const output=new URL('reports/sphere-triangle-mesh-trajectory-js-browser/',root);await mkdir(output,{recursive:true});
const module=String.raw`
import {loadSimulationRuntime} from '../../engine/simulation.mjs';
import {parseStrictJson,stringifyStrictJson} from '../../engine/strict-json.mjs';
const input=parseStrictJson(document.querySelector('#fixture').textContent);
const button=document.querySelector('#run'),status=document.querySelector('#status'),error=document.querySelector('#error'),out=document.querySelector('#result');
document.querySelector('#input').textContent=stringifyStrictJson(input);
let runtime;
button.disabled=false;status.textContent='準備できました。ボタンで実WASMの所有APIを照会します。';
button.addEventListener('click',async()=>{
 button.disabled=true;error.hidden=true;out.textContent='';status.textContent='共通WASMを読込み、定義線分を照会中…';
 try{
  runtime??=await loadSimulationRuntime();
  const result=runtime.querySphereTriangleMeshTrajectory({start:input.start,end:input.end,radius:input.radius},input.triangles,input.settings);
  const packet={schema:1,kind:'sphere-triangle-mesh-trajectory-js-browser-proof',fixture:'short-safe-linear',input,result,diagnostics:runtime.diagnostics};
  out.textContent=stringifyStrictJson(packet,{maxBytes:4194304,maxDepth:32,maxNodes:200000});
  status.textContent=result.status+' / 証明葉 '+result.certifiedLeaves.length+' / audit '+result.audits.length+' / workExact '+result.work.workExact;
 }catch(e){error.hidden=false;error.textContent=String(e.message??e);status.textContent='照会を完了できませんでした。結果は公開していません。';}
 finally{button.disabled=false;}
});`;
const html=`<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>線分経路の所有APIを実行する | pikapikaengine</title><link rel="stylesheet" href="../../docs/learn/learn.css">
<style>main{max-width:1050px;margin:auto;padding:1.5rem}h1{font-size:clamp(1.8rem,4vw,2.7rem)}pre{overflow:auto;white-space:pre;max-height:26rem;font-size:.8rem}figure img{width:100%;height:auto}button{margin:1rem 0}#error{white-space:pre-wrap}</style>
<script type="importmap">${JSON.stringify({imports})}</script></head><body><main>
<p><a href="../../index.html">← エンジン</a> · <a href="../../docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_JS.md">APIの契約と検証</a></p>
<p class="eyebrow">OWNED TRAJECTORY API / BROWSER PROOF</p><h1>定義した線分全体の診断を、<br>実WASMから受け取る。</h1>
<p>検証用の固定例です。中心を[0.5,1,0.5]から[1.5,1,0.5]へ動かす半径0.25mの球と、静的な1面を照会します。新しいJavaScript APIが全診断を所有コピーして返します。</p>
<p class="notice">時刻や衝突応答を計算する操作デモではありません。専用の入力編集ラボ、World・ゲーム接触への統合は後続です。</p>
<button id="run" type="button" disabled>この経路を実WASMで照会する</button><p id="status" role="status">JavaScriptを準備中。HTTP/HTTPS配信が必要です。</p><p id="error" role="alert" hidden></p>
<details><summary>固定入力JSON</summary><pre id="input"></pre></details>
<h2>入力・所有結果・SDK情報</h2><p class="small">区間と原本の負零を維持したJSONです。未認証と点貫通を非接触へ変えません。</p><pre id="result">未実行</pre>
<figure><img src="../../docs/learn/diagrams/sphere-triangle-mesh-trajectory-owned.svg" width="960" height="640" alt="入力と共有出力をコピーし、Nativeの原本・全診断とJavaScriptの元入力を独立に所有する。"><figcaption>原著の所有モデル概念図。物理計算や性能の測定図ではありません。</figcaption></figure>
</main><script id="fixture" type="application/json">${stringifyStrictJson(fixture.input)}</script><script type="module">${module}</script></body></html>
`;
await writeFile(new URL('index.html',output),html);console.log(JSON.stringify({generated:'reports/sphere-triangle-mesh-trajectory-js-browser/index.html',fixture:fixture.name,modules:Object.keys(imports).length}));
