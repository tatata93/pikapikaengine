import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const file=process.argv[2]||'assets/pikapika-core.wasm';
const bytes=await readFile(file),{instance}=await WebAssembly.instantiate(bytes,{}),e=instance.exports;
assert.equal(e.pp_direct_delay(343,343),1);assert.equal(e.pp_direct_pressure_gain(2,1),.5);assert.equal(e.pp_integrate_velocity(10,4,.25),11);
assert.ok(Math.abs(e.pp_sweep_fraction(-20,0,0,40,0,0,1)-.475)<1e-12);
assert.equal(e.pp_sweep_fraction(-20,5,0,40,0,0,1),-1);
console.log(`WebAssembly executed: ${bytes.length} bytes; 5 known-result assertions passed`);
