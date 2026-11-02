import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {initializePortableCore,getPortableCore} from '../engine/portable.mjs';
import {sweepSphere} from '../engine/math.mjs';
import {propagation} from '../engine/audio.mjs';
import {createHash} from 'node:crypto';
test('committed WASM provenance matches its source and binary',async()=>{
  const provenance=JSON.parse(await readFile(new URL('../assets/pikapika-core.build.json',import.meta.url),'utf8'));
  const sha=value=>createHash('sha256').update(value).digest('hex');
  assert.equal(sha(await readFile(new URL('../assets/pikapika-core.wasm',import.meta.url))),provenance.binarySha256);
  for(const [file,expected]of Object.entries(provenance.sourceSha256))assert.equal(sha((await readFile(new URL('../'+file,import.meta.url),'utf8')).replaceAll('\r\n','\n')),expected,`Rebuild WebAssembly after changing ${file}`);
});
test('real C++ WebAssembly is connected to engine collision and propagation APIs',async()=>{
  const reference=sweepSphere([-20,0,0],[20,0,0],[0,0,0],1);
  await initializePortableCore(await readFile(new URL('../assets/pikapika-core.wasm',import.meta.url)));
  assert.ok(getPortableCore());assert.equal(sweepSphere([-20,0,0],[20,0,0],[0,0,0],1),reference);
  assert.equal(sweepSphere([-20,5,0],[20,5,0],[0,0,0],1),null);
  assert.equal(sweepSphere([0,0,0],[0,0,0],[0,0,0],1),0);
  assert.equal(sweepSphere([-2,0,0],[-20,0,0],[0,0,0],1),null);
  assert.deepEqual(propagation(343),{delaySeconds:1,amplitude:1/343});
  assert.deepEqual(propagation(.5),{delaySeconds:.5/343,amplitude:1});
  assert.equal(getPortableCore().pp_integrate_velocity(2,3,.5),3.5);
});
