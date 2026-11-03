import create from './sqrt-standalone.mjs';
import {readFile} from 'node:fs/promises';
await create({wasmBinary:await readFile(new URL('./sqrt-standalone.wasm',import.meta.url)),arguments:process.argv.slice(2),print:console.log,printErr:console.error});
