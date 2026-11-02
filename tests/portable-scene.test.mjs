import test from 'node:test';
import assert from 'node:assert/strict';
import {Scene,box} from '../engine/scene.mjs';
import {parsePortableScene,savePortableScene} from '../engine/portable-scene.mjs';
import {createBoxMesh,compileMesh} from '../engine/mesh.mjs';
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
test('portable v2 preserves indexed mesh geometry, original IDs and material metadata',()=>{
  const entity={...box('authored-mesh',[1,2,3],[2,1,3],[.2,.8,.4],.3),type:'mesh',mesh:createBoxMesh([2,4,6])};
  const scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[entity]});
  const text=savePortableScene(scene);assert.ok(text.startsWith('pikapika-scene 2\n'));
  const restored=parsePortableScene(text),mesh=restored.entities[0];
  assert.equal(mesh.id,'authored-mesh');assert.equal(mesh.type,'mesh');assert.deepEqual(mesh.mesh,entity.mesh);
  assert.deepEqual(mesh.color,entity.color);assert.deepEqual(mesh.position,entity.position);
  assert.deepEqual(compileMesh(mesh.mesh),compileMesh(entity.mesh));
  const legacy=new Scene();legacy.add(box('legacy-box',[0,0,0],[1,1,1]));
  assert.ok(savePortableScene(legacy).startsWith('pikapika-scene 1\n'));
  assert.equal(parsePortableScene(savePortableScene(legacy)).data.version,1);
});
test('portable mesh blocks reject missing duplicate malformed counts indices and Float32 collapse',()=>{
  const scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[
    {...box('mesh',[0,0,0],[1,1,1]),type:'mesh',mesh:createBoxMesh()}]});
  const text=savePortableScene(scene),block=text.slice(text.indexOf('\nmesh ')+1);
  assert.throws(()=>parsePortableScene(text.replace('pikapika-scene 2','pikapika-scene 1')),/version/);
  assert.throws(()=>parsePortableScene(text.slice(0,text.indexOf('\nmesh '))+'\n'),/Missing mesh/);
  assert.throws(()=>parsePortableScene(text+block),/duplicate mesh/);
  assert.throws(()=>parsePortableScene(text.replace(/mesh (\d+) 8 12/,'mesh $1 65537 12')),/count limit/);
  assert.throws(()=>parsePortableScene(text.replace('triangle 0 2 1','triangle 0 2 99')),/indices/);
  assert.throws(()=>parsePortableScene(text.replace('triangle 0 2 1','triangle 0 0 1')),/Degenerate/);
  const collapse='pikapika-scene 2\nunits m s kg\naxes right-handed y-up\n'+
    'entity 8 "mesh" "precision" 0 0 0 0 0 0 1 1 1 1 0\nmesh 8 3 1\n'+
    'vertex 999999 0 0\nvertex 999999.001 0 0\nvertex 999999 1 0\ntriangle 0 1 2\n';
  assert.throws(()=>parsePortableScene(collapse),/Float32/);
});
test('native mesh vertex command edits exact indexed geometry and updates derived normals',
  {skip:process.platform!=='win32'||!existsSync(nativeCli)},()=>{
    const directory=mkdtempSync(join(tmpdir(),'pikapika-mesh-roundtrip-'));
    try {
      const source={...box('browser-mesh',[1,2,3],[1,1,1],[.3,.7,.8]),type:'mesh',mesh:createBoxMesh([2,2,2])};
      const scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[source]});
      const text=savePortableScene(scene),original=parsePortableScene(text).entities[0],id=original.nativeId;
      const input=join(directory,'input.scene'),output=join(directory,'output.scene');writeFileSync(input,text);
      const result=spawnSync(nativeCli,['mesh-vertex',input,id,'6','1.5','2','1.25',output],{encoding:'utf8'});
      assert.equal(result.status,0,result.stderr);
      const restored=parsePortableScene(readFileSync(output,'utf8')).entities[0];
      assert.equal(restored.id,source.id);assert.equal(restored.nativeId,id);assert.deepEqual(restored.color,source.color);
      assert.deepEqual(restored.mesh.positions[6],[1.5,2,1.25]);assert.deepEqual(restored.mesh.triangles,source.mesh.triangles);
      assert.notDeepEqual(compileMesh(restored.mesh),compileMesh(source.mesh));
      const indices=source.mesh.triangles.findIndex(t=>t.includes(6));
      const normalA=compileMesh(source.mesh).slice(indices*18+3,indices*18+6);
      const normalB=compileMesh(restored.mesh).slice(indices*18+3,indices*18+6);
      assert.notDeepEqual(normalB,normalA);
    } finally {rmSync(directory,{recursive:true,force:true});}
  });
