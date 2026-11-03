import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {POLARIZED_ROUTE_PRESETS,polarizedRouteCase,evaluatePolarizedRouteCase,polarizedTensorRows,validatePolarizedRouteOutput,initializePolarizedRouteLab} from '../tools/polarized-route-lab.mjs';
const htmlUrl=new URL('../tools/polarized-route-lab.html',import.meta.url),html=await readFile(htmlUrl,'utf8'),copy=x=>JSON.parse(JSON.stringify(x));
const b=x=>[x,x],v=a=>a.map(b);
const state=(power=.5)=>({power:b(power),coherency:{diagonal:[b(power/2),b(power/2),b(0)],upper:[{real:b(0),imag:b(power/4)},{real:b(0),imag:b(0)},{real:b(0),imag:b(0)}]}});
// Scripted packet fixture exercises UI contracts, never validates the physics.
function fixture(source,{failed=false}={}){
  const geometry={status:'completed',completedSteps:source.steps.length,failedStep:source.steps.length,segments:source.steps.map((step,i)=>({branch:step.branch,incoming:{origin:v([0,0,i]),direction:v([0,0,1])},geometry:{status:'hit',reason:'none',hit:{parameter:b(1),position:v([i,0,i+1])}},interface:{kind:'refracted'},incidentIndex:b(1),otherIndex:b(1.5)})),completion:{}};
  return {status:failed?'power_unresolved':'completed',powerFailure:failed?'incidence_frame_uncertain':'none',geometry,initialFrame:{direction:v([0,0,1]),first:v([1,0,0]),second:v([0,1,0])},initialState:state(1),segments:source.steps.map((step,ordinal)=>({ordinal,branch:step.branch,amplitudeS:failed&&ordinal===1?null:{real:b(.5),imag:b(0)},amplitudeP:{real:b(.3),imag:b(0)},exactNormal:false,homogeneous:false,outgoing:failed&&ordinal===1?null:state(.5/(ordinal+1))})),completedPowerSteps:failed?1:source.steps.length,failedPowerStep:failed?1:source.steps.length,completion:failed?null:{state:state(.25),ray:{origin:v([1,0,2]),direction:v([0,0,1])},index:b(1)},geometryQueries:2,interfaceQueries:2,geometrySqrtRefinements:32,powerSqrtRefinements:64,refinementLimited:false};
}
function fixtureRuntime(){const calls=[];return {calls,diagnostics:{backend:'scripted packet fixture, not physics'},respond:source=>fixture(source),tracePolarizedRoute(ray,steps,settings){const source=copy({ray,steps,settings});calls.push(source);return copy(this.respond(source));}};}
function harness(){
  const ids=new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1])),elements=new Map(),listeners=new Map(),draws=[];
  const ctx=new Proxy({}, {get:(_t,key)=>(...args)=>draws.push([key,...args]),set:()=>true});
  const create=tag=>({tag,value:'',textContent:'',children:[],appendChild(c){this.children.push(c);},replaceChildren(...c){this.children=c;}});
  const get=id=>{assert.ok(ids.has(id),'missing element '+id);if(!elements.has(id))elements.set(id,{...create(id),hidden:false,disabled:false,width:800,height:360,getContext:()=>ctx,addEventListener:(type,fn)=>listeners.set(id+':'+type,fn)});return elements.get(id);};
  return {get,draws,doc:{getElementById:get,createElement:create},fire:(id,type='input')=>{const fn=listeners.get(id+':'+type);assert.ok(fn,'missing listener '+id+':'+type);return fn();}};
}
const initialize=(ui,runtime,extra={})=>initializePolarizedRouteLab({doc:ui.doc,loadRuntime:async()=>runtime,yieldControl:async()=>{},...extra});

test('preset source factory retains integer originals, exact Stokes and independent outward boxes',()=>{
  assert.equal(Object.keys(POLARIZED_ROUTE_PRESETS).length,8);for(const preset of Object.keys(POLARIZED_ROUTE_PRESETS))assert.ok(polarizedRouteCase({preset}).steps.length>=1);
  const p=polarizedRouteCase();assert.deepEqual(p.steps.map(s=>s.surface.normal),[[3,0,-4],[-543,300,-76]]);assert.equal(p.settings.index,25);assert.deepEqual(p.settings.transverseReference,[0,-1,0]);assert.equal(p.ray.maximumParameter,100);
  const wide=polarizedRouteCase({originWidth:.1,directionWidth:.01,indexWidth:.2});assert.ok(wide.ray.origin[0][0]<-.1&&wide.ray.origin[0][1]>.1);assert.ok(wide.steps[0].nextIndex[0]<38.8&&wide.steps[0].nextIndex[1]>39.2);assert.notStrictEqual(wide.steps[0].nextIndex,wide.steps[1].nextIndex);
  assert.deepEqual(polarizedRouteCase({preset:'tir',stokes:'u_plus'}).settings.power,[1,0,1,0]);assert.deepEqual(polarizedRouteCase({preset:'near_normal'}).ray.direction[0],[-1e-8,1e-8]);assert.equal(polarizedRouteCase({preset:'budget'}).settings.maximumSteps,1);
  p.steps[0].surface.normal[0]=999;assert.equal(polarizedRouteCase().steps[0].surface.normal[0],3);
  for(const input of [{preset:'bad'},{stokes:'bad'},{originWidth:''},{originWidth:-1},{directionWidth:.2},{indexWidth:NaN},{maximumSteps:1.5},{maxSqrtRefinements:0},{powerMaxSqrtRefinements:257},{maximumTotalSqrtRefinements:true}])assert.throws(()=>polarizedRouteCase(input));
  let calls=0;assert.throws(()=>evaluatePolarizedRouteCase({tracePolarizedRoute(){++calls;}},{originWidth:''}));assert.equal(calls,0);
});

test('Hermitian presentation preserves upper components, conjugates lower bounds and rejects stale completion',()=>{
  const s=state(),matrix=polarizedTensorRows(s);assert.deepEqual(matrix[0][1].imag,[.125,.125]);assert.deepEqual(matrix[1][0].imag,[-.125,-.125]);assert.deepEqual(matrix[2][2].imag,[0,0]);assert.equal(polarizedTensorRows(null),null);
  const source=polarizedRouteCase(),result=fixture(source,{failed:true});assert.ok(validatePolarizedRouteOutput({source,result}));
  result.completion={state:state(),ray:{origin:v([0,0,0]),direction:v([0,0,1])},index:b(1)};assert.throws(()=>validatePolarizedRouteOutput({source,result}),/未完了/);
  const corrupt=fixture(source);corrupt.completion.state.coherency.upper[0].imag=[NaN,NaN];assert.throws(()=>validatePolarizedRouteOutput({source,result:corrupt}),/有限/);
});

test('UI starts without a query and explicitly forwards original families and budgets to the actual API entry',async()=>{
  const ui=harness(),r=fixtureRuntime(),lab=await initialize(ui,r);assert.equal(r.calls.length,0);assert.equal(lab.getState().output,null);
  ui.get('pr-origin-width').value='.01';ui.fire('pr-origin-width');assert.equal(r.calls.length,0);await lab.calculate();assert.equal(r.calls.length,1);assert.ok(r.calls[0].ray.origin[0][0]<-.01);assert.equal(r.calls[0].settings.powerMaxSqrtRefinements,128);
  assert.equal(ui.get('pr-steps').children.length,2);assert.equal(ui.get('pr-tensor').children.length,3);assert.ok(ui.draws.some(d=>d[0]==='strokeRect'));assert.match(ui.get('pr-final-power').textContent,/0\.25000000/);
  const json=JSON.parse(ui.get('pr-json').textContent);assert.deepEqual(json.source.ray,r.calls[0].ray);assert.deepEqual(json.result.completion.state,lab.getState().output.result.completion.state);
  ui.get('pr-stokes').value='v_minus';ui.fire('pr-stokes','change');assert.equal(lab.getState().output,null);assert.equal(ui.get('pr-final-power').textContent,'—');assert.equal(ui.get('pr-json').textContent,'結果なし');assert.equal(r.calls.length,1);
});

test('UI retains geometric completion and power prefix while final unknown tensor stays empty',async()=>{
  const ui=harness(),r=fixtureRuntime();r.respond=s=>fixture(s,{failed:true});const lab=await initialize(ui,r);await lab.calculate();
  assert.equal(ui.get('pr-final-power').textContent,'—');assert.match(ui.get('pr-prefix').textContent,/幾何 2 \/ 偏光 1/);assert.match(ui.get('pr-steps').children[1].children[3].textContent,/完了状態なし/);assert.equal(ui.get('pr-tensor').children[0].children[1].textContent,'—');
  ui.get('pr-inspect').value='0';ui.fire('pr-inspect','change');assert.match(ui.get('pr-tensor-label').textContent,/段1の後/);assert.match(ui.get('pr-tensor').children[0].children[1].textContent,/0\.25000000/);assert.equal(ui.get('pr-final-power').textContent,'—');
  r.respond=s=>({...fixture(s,{failed:true}),geometry:null,segments:[],completedPowerSteps:0});await lab.calculate();assert.equal(ui.get('pr-steps').children.length,2);assert.equal(ui.get('pr-steps').children[0].children[1].textContent,'幾何は未実行');assert.equal(ui.get('pr-steps').children[0].children[3].textContent,'偏光は未実行');
});

test('busy lock prevents interleaved queries and explicit preset/reset changes never trace automatically',async()=>{
  const ui=harness(),r=fixtureRuntime();let finish,clock=10;const lab=await initialize(ui,r,{now:()=>clock,evaluate:async(runtime,parameters)=>{await new Promise(resolve=>{finish=resolve;});return evaluatePolarizedRouteCase(runtime,parameters);}});
  const pending=lab.calculate();await Promise.resolve();await Promise.resolve();assert.equal(ui.get('pr-controls').disabled,true);assert.equal(ui.get('pr-retry').disabled,true);assert.equal(await lab.calculate(),null);await lab.retry();assert.equal(r.calls.length,0);
  clock=50;finish();await pending;assert.equal(r.calls.length,1);assert.equal(ui.get('pr-controls').disabled,false);assert.match(ui.get('pr-time').textContent,/40\.000000 ms/);
  ui.get('pr-preset').value='budget';ui.fire('pr-preset','change');assert.equal(ui.get('pr-step-budget').value,'1');assert.equal(lab.getState().output,null);assert.equal(r.calls.length,1);ui.fire('pr-reset','click');assert.equal(ui.get('pr-preset').value,'rational');assert.equal(ui.get('pr-step-budget').value,'64');assert.equal(r.calls.length,1);
});

test('invalid input, load failure and legacy kernel errors erase stale tensors and recover by retry',async()=>{
  const ui=harness(),r=fixtureRuntime();let fail=true;const lab=await initialize(ui,r,{loadRuntime:async()=>{if(fail)throw new Error('offline');return r;}});assert.equal(ui.get('pr-controls').disabled,true);assert.equal(await lab.calculate(),null);
  fail=false;await lab.retry();assert.equal(r.calls.length,0);await lab.calculate();assert.ok(lab.getState().output);
  ui.get('pr-step-budget').value='';ui.fire('pr-step-budget');assert.equal(lab.getState().output,null);await lab.calculate();assert.equal(r.calls.length,1);assert.match(ui.get('pr-error').textContent,/有限/);
  ui.get('pr-step-budget').value='64';ui.fire('pr-step-budget');r.respond=()=>{throw new Error('Polarized route WASM API unavailable; rebuild');};await lab.calculate();assert.equal(lab.getState().output,null);assert.match(ui.get('pr-error').textContent,/同梱WASM/);assert.equal(ui.get('pr-final-power').textContent,'—');
  r.respond=s=>fixture(s);await lab.retry();await lab.calculate();assert.ok(lab.getState().output);assert.throws(()=>evaluatePolarizedRouteCase({traceOpticalRoute(){throw new Error('not a polarized fallback');}}),/未対応/);
});

test('static lesson, original diagram, bounded table layout and one new entry registration are present',async()=>{
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g))if(!/^(https?:|#)/.test(m[1]))await access(new URL(m[1],htmlUrl));
  for(const term of ['毎回無偏光へ戻しません','最終completion','表示中央値','HTTP/HTTPS','入射パワーを1','経路間の干渉'])assert.ok(html.includes(term),term);assert.match(html,/overflow-x:auto/);assert.match(html,/white-space:nowrap/);assert.match(html,/src="polarized-route-lab\.mjs(?:\?[^\"]*)?"/);
  const index=await readFile(new URL('../docs/learn/index.html',import.meta.url),'utf8');assert.equal([...index.matchAll(/<article\s/g)].length,20);assert.match(index,/id="polarized-route"/);
  const build=await readFile(new URL('../scripts/build-web.mjs',import.meta.url),'utf8');assert.equal((build.match(/\['tools\/polarized-route-lab.html','\.\.\/','polarized-route-lab.mjs'\]/g)??[]).length,1);
  const svg=await readFile(new URL('../docs/learn/diagrams/polarized-route.svg',import.meta.url),'utf8');assert.match(svg,/<svg /);assert.doesNotMatch(svg,/<image|https?:\/\/(?!www.w3.org)/);
});

// Independent exact rational arithmetic on output binary64 endpoints. This does
// not use the old ordinary-double polarization kernel as an inclusion oracle.
const gcd=(a,b)=>{a=a<0n?-a:a;while(b){const r=a%b;a=b;b=r;}return a;};
function f(n,d=1n){n=BigInt(n);d=BigInt(d);if(d<0n){n=-n;d=-d;}const g=gcd(n,d);return {n:n/g,d:d/g};}
const plus=(a,b)=>f(a.n*b.d+b.n*a.d,a.d*b.d),times=(a,b)=>f(a.n*b.n,a.d*b.d),neg=a=>f(-a.n,a.d),compare=(a,b)=>a.n*b.d-b.n*a.d;
function exact(x){assert.ok(Number.isFinite(x));const data=new DataView(new ArrayBuffer(8));data.setFloat64(0,x);const bits=data.getBigUint64(0),sign=bits>>63n?-1n:1n,e=Number((bits>>52n)&2047n),m=bits&((1n<<52n)-1n);if(!e&&!m)return f(0);const mant=e?m+(1n<<52n):m,shift=e?e-1023-52:-1074;return shift>=0?f(sign*(mant<<BigInt(shift))):f(sign*mant,1n<<BigInt(-shift));}
function containsRational(box,n,d=1){const target=f(n,d);assert.ok(compare(exact(box[0]),target)<=0n&&compare(exact(box[1]),target)>=0n,`${box} excludes ${n}/${d}`);}
const addBox=(a,b)=>[plus(a[0],b[0]),plus(a[1],b[1])];
const scaleBox=(a,k)=>k.n<0n?[times(a[1],k),times(a[0],k)]:[times(a[0],k),times(a[1],k)];
function projection(matrix,left,right,part){let box=[f(0),f(0)];for(let i=0;i<3;++i)for(let j=0;j<3;++j)box=addBox(box,scaleBox(matrix[i][j][part].map(exact),times(left[i],right[j])));return box;}
const containsF=(box,target)=>assert.ok(compare(box[0],target)<=0n&&compare(box[1],target)>=0n,'rational reference outside exact projected endpoint intervals');
let runtime;async function actual(){if(!runtime)runtime=await loadSimulationRuntime({wasmBytes:await readFile(new URL('../assets/pikapika-simulation.wasm',import.meta.url))});return runtime;}

test('actual WASM: two noncoplanar reflections enclose independent rational POWER and reject reset prediction',async()=>{
  const r=await actual();for(const [stokes,n,d]of [['unpolarized',42544,17294403],['u_plus',322768,259416045]]){const out=evaluatePolarizedRouteCase(r,{stokes});validatePolarizedRouteOutput(out);assert.equal(out.result.status,'completed');assert.equal(out.result.completedPowerSteps,2);containsRational(out.result.completion.state.power,n,d);assert.ok(out.result.completion.state.power[1]<1263376/466948881);containsRational(out.result.geometry.completion.totals.distance,26);containsRational(out.result.geometry.completion.totals.opticalPathLength,650);}
});

test('actual WASM: normal plate preserves global circular tensor with analytical 576/625 power',async()=>{
  const r=await actual(),out=evaluatePolarizedRouteCase(r,{preset:'plate',stokes:'v_plus'});assert.equal(out.result.status,'completed');const state=out.result.completion.state;containsRational(state.power,576,625);containsRational(state.coherency.upper[0].imag,288,625);containsRational(state.coherency.diagonal[0],288,625);containsRational(state.coherency.diagonal[1],288,625);assert.equal(out.result.segments.length,2);
  const source=polarizedRouteCase({preset:'plate',stokes:'v_plus'}),reflected=r.tracePolarizedRoute(source.ray,[{...source.steps[0],branch:'reflected'}],source.settings);assert.equal(reflected.status,'completed');containsRational(reflected.completion.state.power,1,25);containsRational(reflected.completion.state.coherency.upper[0].imag,1,50); // World tensor has no artificial V sign flip.
});

test('actual WASM: noncoplanar two-TIR global tensor encloses algebraic Q U V without midpoint projection',async()=>{
  const out=evaluatePolarizedRouteCase(await actual(),{preset:'tir',stokes:'u_plus'});assert.equal(out.result.status,'completed');const state=out.result.completion.state;containsRational(state.power,1);
  const matrix=polarizedTensorRows(state),s=[f(-12,25),f(16,25),f(-3,5)],p=[f(-543,625),f(-276,625),f(28,125)];
  const q=addBox(projection(matrix,s,s,'real'),scaleBox(projection(matrix,p,p,'real'),f(-1))),u=scaleBox(projection(matrix,s,p,'real'),f(2)),v=scaleBox(projection(matrix,s,p,'imag'),f(2));
  containsF(q,f(424,625));containsF(u,f(-10007,15625));const squareTarget=times(f(11),times(f(1696,15625),f(1696,15625)));
  assert.ok(compare(v[1],f(0))>0n);assert.ok(compare(times(v[1],v[1]),squareTarget)>=0n);if(compare(v[0],f(0))>0n)assert.ok(compare(times(v[0],v[0]),squareTarget)<=0n);
});

test('actual WASM: uncertainty, unavailable branch and budget keep final state absent and all input rows inspectable',async()=>{
  const r=await actual();for(const [preset,status,powerFailure,geometryStatus,completed]of [['source_frame','power_unresolved','initial_frame_uncertain','completed',2],['near_normal','power_unresolved','incidence_frame_uncertain','completed',1],['critical','geometry_failed','none','interface_unresolved',0],['unavailable','geometry_failed','none','branch_unavailable',0],['budget','budget_exceeded','none',undefined,undefined]]){const out=evaluatePolarizedRouteCase(r,{preset});validatePolarizedRouteOutput(out);assert.equal(out.result.status,status,preset);assert.equal(out.result.powerFailure,powerFailure,preset);assert.equal(out.result.geometry?.status,geometryStatus,preset);assert.equal(out.result.geometry?.completedSteps,completed,preset);assert.equal(out.result.completion,null,preset);if(geometryStatus==='completed')assert.ok(out.result.geometry.completion,'completed geometry survives power failure');}
  const ui=harness(),lab=await initialize(ui,r);ui.get('pr-preset').value='budget';ui.fire('pr-preset','change');await lab.calculate();assert.equal(lab.getState().output.result.status,'budget_exceeded');assert.equal(ui.get('pr-steps').children.length,2);assert.equal(ui.get('pr-final-power').textContent,'—');ui.get('pr-step-budget').value='64';ui.fire('pr-step-budget');await lab.calculate();assert.equal(lab.getState().output.result.status,'completed');
});
