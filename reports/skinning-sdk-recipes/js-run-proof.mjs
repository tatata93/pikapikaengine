import {spawnSync} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';

const root=fileURLToPath(new URL('../../',import.meta.url)),dir=path.join(root,'build/skinning-sdk-js');
const testFiles=['tests/skinning.test.mjs','tests/motion.test.mjs','tests/optics.test.mjs','tests/simulation.test.mjs','tests/continuous-world.test.mjs','tests/supported-world.test.mjs'];
const commands=[];
async function run(args,name){
 const r=spawnSync(process.execPath,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:60000,maxBuffer:8*1024*1024});
 await writeFile(path.join(dir,name+'.stdout.txt'),r.stdout??'');await writeFile(path.join(dir,name+'.stderr.txt'),r.stderr??'');
 commands.push({command:['node',...args],exitCode:r.status,error:r.error?.message??null});
 assert.equal(r.status,0,(r.stderr??'')+(r.stdout??'')+(r.error?.message??''));
}
await run(['--test','--test-reporter=spec',...testFiles],'tests');
await run(['scripts/verify-skinning-wasm.mjs','build/skinning-proof/native.json','build/skinning-proof/native-oracle.csv',
 'build/skinning-sdk-js/report.json','build/skinning-sdk-js/outputs.json','build/skinning-sdk-js/replay.json','build/skinning-sdk-js/replay-oracle.csv'],'replay');
const files=['engine/simulation.mjs','tests/skinning.test.mjs','scripts/verify-skinning-wasm.mjs','scripts/verify-skinning.py',
 'assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json',
 'core/include/pikapika/skinning.hpp','core/src/skinning.cpp','core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp',
 'build/skinning-sdk-js/report.json','build/skinning-sdk-js/outputs.json','build/skinning-sdk-js/replay.json','build/skinning-sdk-js/replay-oracle.csv'];
const hashes=[];for(const file of files){const data=await readFile(path.join(root,file));hashes.push({path:file,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')});}
await writeFile(path.join(dir,'provenance.json'),JSON.stringify({schema:1,date:new Date().toISOString(),node:process.version,commands,files:hashes,
 scope:'60 actual C++ model fixture results, five explicit host-exchange rejections, and 128 actual C++ oracle bind/deform queries. Original signed-zero JSON and bit trees retained. Independent Fraction checker unchanged.'},null,2)+'\n');
console.log('PASS main WASM skin SDK replay and motion/optics/World regression; provenance saved.');
