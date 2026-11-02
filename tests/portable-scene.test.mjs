import test from 'node:test';
import assert from 'node:assert/strict';
import {Scene,box} from '../engine/scene.mjs';
import {parsePortableScene,savePortableScene} from '../engine/portable-scene.mjs';
import {existsSync,mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
const header='pikapika-scene 1\nunits m s kg\naxes right-handed y-up\n';
const entity='entity 42 "robot" "Player \\"quoted\\"" 1 2 3 0 0 0 1 1 2 3 0.5';
test('native stable IDs and source types survive browser edits and roundtrip',()=>{
  const scene=parsePortableScene(header+entity+'\n');
  assert.equal(scene.entities[0].id,'native:42');assert.equal(scene.entities[0].name,'Player "quoted"');
  scene.edit('native:42',{position:[4,5,6]});
  const round=parsePortableScene(savePortableScene(scene));
  assert.deepEqual(round.entities,scene.entities);
  assert.match(savePortableScene(scene),/entity 42 "robot"/);
});
test('authored browser IDs get deterministic nonsequential identities and retain material metadata',()=>{
  const s=new Scene();s.add(box('authored-player',[1,2,3],[1,1,1],[.2,.4,.8]));
  const first=savePortableScene(s),nativeId=parsePortableScene(first).entities[0].nativeId;
  s.edit('authored-player',{position:[7,8,9]});s.add(box('new-wall',[0,0,0],[2,2,2]));
  const restored=parsePortableScene(savePortableScene(s));
  assert.equal(restored.entities[0].nativeId,nativeId);assert.equal(restored.entities[0].id,'authored-player');
  assert.deepEqual(restored.entities[0].color,[.2,.4,.8]);assert.deepEqual(restored.entities[0].position,[7,8,9]);
});
test('native plane scale and Y rotation preserve source transform',()=>{
  const source=header+'entity 9 "plane" "Floor" 0 0 0 0 0.7071067811865475 0 0.7071067811865476 100 1 100 0\n';
  const scene=parsePortableScene(source);assert.equal(scene.entities[0].scale[1],.02);
  const output=savePortableScene(scene);assert.match(output,/100 1 100 0/);
  const restored=parsePortableScene(output);assert.deepEqual(restored.entities,scene.entities);
});
test('camera source listener retain exact typed transforms across portable edits',()=>{
  const records=[
    'entity 4 "camera" "Main camera" 0 18 65 0 0 0 1 1 1 1 0',
    'entity 5 "source" "Direct sound source" -20 5 -10 0 0 0 1 1 1 1 0',
    'entity 6 "listener" "Direct sound listener" 0 5 30 0 0 0 1 1 1 1 0'];
  const scene=parsePortableScene(header+records.join('\n')+'\n');
  assert.deepEqual(scene.entities.map(e=>e.type),['camera','source','listener']);
  scene.edit('native:5',{position:[-10,6,-20]});
  const restored=parsePortableScene(savePortableScene(scene));assert.deepEqual(restored.entities,scene.entities);
  assert.equal(restored.entities[1].nativeRadius,0);
  assert.throws(()=>parsePortableScene(header+records[0].slice(0,-1)+'1\n'),/reserved as zero/);
});
test('unsupported rotations types malformed IDs and duplicate metadata fail explicitly',()=>{
  assert.throws(()=>parsePortableScene(header+entity.replace('0 0 0 1','0.7071067811865475 0 0 0.7071067811865476')),/Y rotation/);
  assert.throws(()=>parsePortableScene(header+entity.replace('"robot"','"sphere"')),/primitive/);
  assert.throws(()=>parsePortableScene(header+entity.replace('42','9007199254740992')),/stable ID/);
  assert.throws(()=>parsePortableScene(header+entity+'\n'+entity),/Duplicate/);
  assert.throws(()=>parsePortableScene(header+'# browser-meta {"nativeId":"9","id":"orphan","color":[1,1,1]}\n'),/missing entity/);
});
const nativeCli=resolve('build/native/Release/pikapika.exe');
test('native CLI edits browser-authored scene while preserving stable identity and material metadata',
  {skip:process.platform!=='win32'||!existsSync(nativeCli)},()=>{
    const directory=mkdtempSync(join(tmpdir(),'pikapika-roundtrip-'));
    try {
      const scene=new Scene();scene.add(box('browser-player',[1,2,3],[2,3,4],[.2,.6,.8]));
      const input=join(directory,'input.scene'),output=join(directory,'output.scene');
      const text=savePortableScene(scene),id=parsePortableScene(text).entities[0].nativeId;
      writeFileSync(input,text);
      const result=spawnSync(nativeCli,['move',input,id,'4','5','6',output],{encoding:'utf8'});
      assert.equal(result.status,0,result.stderr);
      const restored=parsePortableScene(readFileSync(output,'utf8'));
      assert.equal(restored.entities[0].id,'browser-player');assert.equal(restored.entities[0].nativeId,id);
      assert.deepEqual(restored.entities[0].color,[.2,.6,.8]);assert.deepEqual(restored.entities[0].position,[4,5,6]);
    } finally {rmSync(directory,{recursive:true,force:true});}
  });
test('native CLI creates typed scene and renders source listener direct-path impulse',
  {skip:process.platform!=='win32'||!existsSync(nativeCli)},()=>{
    const directory=mkdtempSync(join(tmpdir(),'pikapika-typed-scene-'));
    try {
      const scenePath=join(directory,'typed.scene'),wavePath=join(directory,'direct.wav');
      const initialized=spawnSync(nativeCli,['init',scenePath],{encoding:'utf8'});assert.equal(initialized.status,0,initialized.stderr);
      const scene=parsePortableScene(readFileSync(scenePath,'utf8'));
      assert.deepEqual(scene.entities.map(e=>e.type),['box','box','box','camera','source','listener']);
      assert.deepEqual(scene.entities.find(e=>e.type==='camera').position,[0,18,65]);
      const rendered=spawnSync(nativeCli,['audio-scene',scenePath,wavePath],{encoding:'utf8'});assert.equal(rendered.status,0,rendered.stderr);
      assert.match(rendered.stdout,/distance_m=44\.7214/);
      const wave=readFileSync(wavePath);assert.equal(wave.subarray(0,4).toString(),'RIFF');
      assert.equal(wave.readUInt32LE(24),48000);assert.ok(wave.length>44);
    } finally {rmSync(directory,{recursive:true,force:true});}
  });
