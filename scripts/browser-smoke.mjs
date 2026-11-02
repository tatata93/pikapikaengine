// Isolated headless browser QA through Chrome DevTools Protocol, no product dependency.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {root,createServer} from './serve.mjs';
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const assert=(condition,message)=>{if(!condition)throw new Error(message);};
await mkdir(path.join(root,'.browser-test'),{recursive:true});await mkdir(path.join(root,'reports/raw'),{recursive:true});
const profile=await mkdtemp(path.join(root,'.browser-test','chrome-'));
const executable=process.env.CHROME_PATH||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
const browser=spawn(executable,['--headless=new','--no-first-run','--no-default-browser-check','--disable-background-timer-throttling','--disable-renderer-backgrounding','--enable-unsafe-webgpu','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--window-size=1440,1000','about:blank'],{windowsHide:true,stdio:'ignore'});
let socket;const pending=new Map(),errors=[];let id=0;
browser.on('error',error=>errors.push(error.message));
try {
  let port;
  for(let i=0;i<100;i++){try{port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}catch{await pause(100);}}
  assert(port,'Chrome did not start: '+errors.join('; '));
  const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  socket.onmessage=event=>{const data=JSON.parse(event.data);if(data.id){const p=pending.get(data.id);pending.delete(data.id);data.error?p?.reject(new Error(JSON.stringify(data.error))):p?.resolve(data.result);}else if(data.method==='Runtime.exceptionThrown')errors.push(data.params.exceptionDetails.exception?.description||data.params.exceptionDetails.text);};
  function cdp(method,params={}){return new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>{pending.delete(n);reject(new Error('CDP timeout: '+method));},15000);pending.set(n,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});socket.send(JSON.stringify({id:n,method,params}));});}
  async function evaluate(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
  async function waitFor(expression,timeout=20000){const start=Date.now();while(Date.now()-start<timeout){if(await evaluate(expression))return;await pause(100);}throw new Error('Timed out: '+expression);}
  console.log('Chrome connected');await cdp('Runtime.enable');await cdp('Page.enable');await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await cdp('Page.navigate',{url:base});await waitFor('window.__pikapika?.ready || !document.getElementById("fatal")?.hidden');
  console.log('Page loaded');const fatal=await evaluate('document.getElementById("fatal-message").textContent');assert(!fatal,'WebGPU initialization failed: '+fatal);
  await pause(500);
  const before=await evaluate('window.__pikapika.frameCount');
  const rect=await evaluate('(()=>{const r=document.getElementById("launch").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()');
  await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...rect});await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...rect});
  await waitFor('window.__pikapika.game.state === "playing"');
  const initial=await evaluate('window.__pikapika.game.player.p');
  for(const code of ['KeyW','ShiftLeft','KeyF'])await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:code==='KeyW'?'w':code==='KeyF'?'f':'Shift',code});
  await pause(1800);
  for(const code of ['KeyW','ShiftLeft','KeyF'])await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:code==='KeyW'?'w':code==='KeyF'?'f':'Shift',code});
  const after=await evaluate('({p:window.__pikapika.game.player.p,shots:window.__pikapika.game.shotId,ticks:window.__pikapika.clock.tick,frameCount:window.__pikapika.frameCount})');
  assert(Math.hypot(...after.p.map((x,i)=>x-initial[i]))>10,'Keyboard movement did not change player position');assert(after.shots>3,'Shooting input did not produce projectiles');assert(after.frameCount>before+5,'Renderer did not continue drawing');
  // Add a primitive, edit its transform, then undo/redo via the same public Scene API.
  const editor=await evaluate('(()=>{document.getElementById("tab-editor").click();const n=window.__pikapika.game.scene.entities.length;document.getElementById("add-box").click();const s=window.__pikapika.game.scene;const id=s.entities.at(-1).id;document.getElementById("entity-select").value=id;document.getElementById("entity-select").dispatchEvent(new Event("change"));document.getElementById("edit-x").value=42;document.getElementById("apply-edit").click();const x=s.entities.find(e=>e.id===id).position[0];document.getElementById("undo").click();document.getElementById("redo").click();return {before:n,after:s.entities.length,x,reloaded:JSON.parse(s.save()).entities.find(e=>e.id===id).position[0],paused:!document.getElementById("pause-indicator").hidden};})()');
  assert(editor.after===editor.before+1&&editor.x===42&&editor.reloaded===42&&editor.paused,'Editor add/edit/roundtrip failed');
  await evaluate('document.getElementById("tab-flight").click()');
  const screen=await cdp('Page.captureScreenshot',{format:'png'});await writeFile(path.join(root,'reports/webgpu-smoke.png'),Buffer.from(screen.data,'base64'));
  const environment=await evaluate('(async()=>{const a=await navigator.gpu.requestAdapter();return {userAgent:navigator.userAgent,adapter:a.info?{vendor:a.info.vendor,architecture:a.info.architecture,device:a.info.device,description:a.info.description}:null,width:document.getElementById("world").width,height:document.getElementById("world").height}})()');
  const performanceLog=await evaluate('window.__pikapika.log.report()');
  await writeFile(path.join(root,'reports/raw/webgpu-frames.json'),JSON.stringify({...performanceLog,environment},null,2));
  // Learning pages: actual DOM load and interaction; runtime exceptions remain captured.
  await cdp('Page.navigate',{url:base+'/docs/learn/'});await waitFor('document.readyState === "complete"');assert(await evaluate('document.body.textContent.includes("固定")'),'Learning entrance missing fixed-step explanation');
  await cdp('Page.navigate',{url:base+'/docs/learn/flame.html'});await waitFor('document.readyState === "complete"');await pause(200);
  const lesson=await evaluate('({title:document.title,buttons:[...document.querySelectorAll("button")].map(e=>e.textContent.trim()),inputs:document.querySelectorAll("input").length,canvas:document.querySelectorAll("canvas").length})');
  assert(lesson.inputs>=6&&lesson.buttons.length>=3,'Flame lesson controls missing');
  const flameScreen=await cdp('Page.captureScreenshot',{format:'png'});await writeFile(path.join(root,'reports/flame-smoke.png'),Buffer.from(flameScreen.data,'base64'));
  assert(errors.length===0,'Browser runtime errors: '+errors.join('\n'));
  const summary={date:new Date().toISOString(),browser:environment,actions:{movement:after,editor,flame:lesson},measurement:{frames:performanceLog.retainedFrames,median:performanceLog.median,p95:performanceLog.p95,p99:performanceLog.p99,max:performanceLog.max,overBudget:performanceLog.overBudget,maxConsecutiveOverBudget:performanceLog.maxConsecutiveOverBudget},errors,status:'PASS',limitations:'Headless smoke only; enabled unsafe WebGPU for automation. Actual presentation, sustained 60fps, GPU duration and listening not verified.'};
  await writeFile(path.join(root,'reports/browser-smoke.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
}catch(error){console.error(error);process.exitCode=1;}finally{socket?.close();browser.kill();server.closeAllConnections();await new Promise(r=>server.close(r));}
