import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile, access} from 'node:fs/promises';
import vm from 'node:vm';

const mathSource = await readFile(new URL('./flame-math.js', import.meta.url), 'utf8');
const uiSource = await readFile(new URL('./flame.js', import.meta.url), 'utf8');
const context = vm.createContext({});
vm.runInContext(mathSource, context);
const math = context.PikaFlameMath;
const close = (a, b, epsilon = 1e-9) => assert.ok(Math.abs(a - b) <= epsilon, `${a} != ${b}`);

test('sine agrees with independently known quarter-cycle positions in px', () => {
  for (const [t, expected] of [[0,0],[0.25,24],[0.5,0],[0.75,-24],[1,0]]) {
    close(math.sample(t, {amplitude:24,frequency:1,phase:0,mode:'sine'}).selected, expected);
  }
  close(math.sample(0, {amplitude:24,frequency:1,phase:Math.PI/2,mode:'sine'}).selected, 24);
});

test('noise is deterministic, seed-sensitive, bounded and continuous at interval boundaries', () => {
  const samples = Array.from({length:1000}, (_, i) => i / 53);
  assert.ok(samples.some(t => math.smoothNoise(t,42) !== math.smoothNoise(t,43)));
  for (const t of samples) {
    assert.equal(math.smoothNoise(t,42), math.smoothNoise(t,42));
    assert.ok(Math.abs(math.smoothNoise(t,42)) <= 1);
  }
  for (let i = 1; i <= 20; i++) close(math.smoothNoise(i-1e-7,42), math.smoothNoise(i+1e-7,42), 1e-10);
});

test('all modes stay within the documented displacement limits over the control extremes', () => {
  for (const mode of ['sine','multiple','random','smooth']) {
    for (const phase of [-3.14,0,3.14]) {
      const p = {amplitude:60,frequency:8,phase,noise:30,speed:12,seed:4294967295,mode};
      const bound = mode === 'smooth' ? 90 : mode === 'random' ? 30 : 60;
      for (let i=0;i<2000;i++) assert.ok(Math.abs(math.sample(i/113,p).selected) <= bound+1e-12);
    }
  }
  for (const mode of ['sine','multiple','random','smooth']) close(math.sample(100, {amplitude:0,noise:0,mode}).selected,0);
});

test('zero noise reduces smooth mode to sine; zero speed freezes random mode', () => {
  for (const t of [0,0.1,1,5.7,100]) {
    const result = math.sample(t, {noise:0,mode:'smooth'}); close(result.selected,result.sine);
    close(math.sample(t,{speed:0,mode:'random'}).selected, math.sample(0,{speed:0,mode:'random'}).selected);
  }
});

test('same elapsed time agrees after 30, 60 and 120 updates per second', () => {
  for (const mode of ['sine','multiple','random','smooth']) {
    for (const fps of [30,60,120]) {
      let timestamp = 0;
      for (let i=0;i<=fps*10;i++) timestamp = i * 1000/fps;
      const result = math.sample(timestamp / 1000,{mode});
      close(result.selected, math.sample(10,{mode}).selected);
    }
  }
});

test('non-finite and out-of-range controls become finite bounded values', () => {
  const p = math.parameters({amplitude:Infinity,frequency:-5,phase:500,noise:NaN,speed:999,seed:-1,mode:'bad'});
  assert.equal(p.amplitude,24); assert.equal(p.frequency,0); close(p.phase,Math.PI);
  assert.equal(p.noise,10); assert.equal(p.speed,12); assert.equal(p.seed,0); assert.equal(p.mode,'smooth');
  assert.ok(Number.isFinite(math.sample(Infinity,p).selected));
});

function uiHarness() {
  const listeners = new Map();
  const elements = new Map();
  const context2d = new Proxy({}, {get:(_target, key) => key === 'createLinearGradient'
    ? () => ({addColorStop(){}}) : () => {}, set:() => true});
  function element(id) {
    if (!elements.has(id)) elements.set(id, {value:'',textContent:'',hidden:false,disabled:false,
      dataset:{}, setAttribute(name,value){this[name]=value;},
      addEventListener(name,fn){listeners.set(`${id}:${name}`,fn);},getContext(){return context2d;}});
    return elements.get(id);
  }
  for (const [key,value] of Object.entries(math.defaults)) element(key).value=String(value);
  element('sample-fps').value='60';
  const frames=[];
  const document={hidden:false,getElementById:element,querySelectorAll:()=>[],
    addEventListener(name,fn){listeners.set(`document:${name}`,fn);}};
  const ctx=vm.createContext({document,requestAnimationFrame:fn=>frames.push(fn)});
  vm.runInContext(mathSource,ctx);vm.runInContext(uiSource,ctx);
  return {element, document,fire:(id,type='click')=>listeners.get(`${id}:${type}`)(),
    frame:timestamp=>frames.shift()(timestamp)};
}

test('actual UI script starts paused, plays, stops, steps, resets and pauses when hidden', () => {
  const ui=uiHarness();
  assert.match(ui.element('demo-status').textContent,/停止中.*0\.000/);
  ui.fire('play');ui.frame(0);ui.frame(1000);
  assert.match(ui.element('demo-status').textContent,/再生中.*1\.000/);
  ui.fire('play');ui.frame(2000);
  assert.match(ui.element('demo-status').textContent,/停止中.*1\.000/);
  ui.fire('step');assert.match(ui.element('demo-status').textContent,/停止中.*1\.017/);
  ui.element('amplitude').value='60';ui.fire('amplitude','input');
  assert.equal(ui.element('amplitude-value').textContent,'60 px');
  ui.element('mode').value='random';ui.fire('mode','input');
  assert.match(ui.element('mode-description').textContent,/振幅A/);
  ui.fire('reset');assert.match(ui.element('demo-status').textContent,/停止中.*0\.000/);
  assert.equal(ui.element('amplitude').value,24);assert.equal(ui.element('mode').value,'smooth');
  ui.fire('play');ui.document.hidden=true;ui.fire('document','visibilitychange');
  assert.equal(ui.element('play')['aria-pressed'],'false');
  for(const fps of [30,60,120]) assert.equal(ui.element(`sample-${fps}`).textContent,ui.element('sample-30').textContent);
});

test('actual playback clock uses timestamps without frame-count dependence at 30/60/120fps', () => {
  const results=[];
  for(const fps of [30,60,120]) {
    const ui=uiHarness();ui.element('sample-fps').value=String(fps);
    ui.element('mode').value='random';ui.element('speed').value='1';ui.fire('play');
    for(let i=0;i<=fps;i++) ui.frame(i*1000/fps);
    ui.fire('play');results.push(ui.element('demo-status').textContent);
  }
  assert.equal(results[0],results[1]);assert.equal(results[1],results[2]);
  assert.match(results[0],/1\.000/);
});

test('HTML has unique IDs, images with alt, and existing local links and fragment targets', async () => {
  for(const filename of ['index.html','flame.html','modeling.html']) {
    const url=new URL(filename,import.meta.url);
    const html=await readFile(url,'utf8');
    const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
    assert.equal(new Set(ids).size,ids.length,`duplicate id in ${filename}`);
    for(const image of html.matchAll(/<img\b[^>]*>/g)) assert.match(image[0],/\balt="[^"]+"/);
    for(const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
      const target=new URL(match[1],url);
      if(target.protocol!=='file:') continue;
      const fragment=target.hash.slice(1);target.hash='';
      await access(target);
      if(fragment) {
        const content=await readFile(target,'utf8');
        assert.ok(content.includes(`id="${fragment}"`),`missing ${match[1]} in ${filename}`);
      }
    }
  }
});
