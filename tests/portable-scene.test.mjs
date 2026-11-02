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
