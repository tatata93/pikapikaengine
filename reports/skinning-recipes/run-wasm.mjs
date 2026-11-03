import {readFileSync,writeFileSync} from 'node:fs';
import createModule from './skinning-standalone.mjs';
const output=[],errors=[];
await createModule({wasmBinary:readFileSync(new URL('./skinning-standalone.wasm',import.meta.url)),arguments:process.argv.slice(2),print:x=>output.push(x),printErr:x=>errors.push(x)});
if(errors.length)process.stderr.write(errors.join('\n')+'\n');
process.stdout.write(output.join('\n')+'\n');
