import {readFile} from 'node:fs/promises';
import createModule from './packet-standalone.mjs';
await createModule({wasmBinary:await readFile(new URL('./packet-standalone.wasm',import.meta.url)),arguments:process.argv.slice(2),print:line=>process.stdout.write(line+'\n'),printErr:line=>process.stderr.write(line+'\n')});


