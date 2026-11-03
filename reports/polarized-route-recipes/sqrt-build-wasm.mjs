import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,renameSync} from 'node:fs';
import path from 'node:path';
const root=process.cwd(),sdk=path.join(root,'build/toolchains/emsdk'),em=path.join(sdk,'upstream/emscripten/em++.py'),env={...process.env,EM_CONFIG:path.join(sdk,'.emscripten')};
const common=['-std=c++20','-O2','-fwasm-exceptions','-fno-rtti','-Icore/include'],objects=[];
writeFileSync('build/polarized-route-proof/sqrt-wasm-compiler.txt',execFileSync('python',[em,'--version'],{env}));
for(const source of ['core/src/interval.cpp','tests/interval_sqrt_tests.cpp']){const object='build/polarized-route-proof/sqrt-'+path.basename(source,'.cpp')+'.o';objects.push(object);execFileSync('python',[em,source,...common,'-fno-fast-math','-ffp-contract=off','-c','-o',object],{env,stdio:'inherit'});}
execFileSync('python',[em,...objects,...common,'-sMODULARIZE=1','-sEXPORT_ES6=1','-sENVIRONMENT=node','-sFILESYSTEM=0','-sEXIT_RUNTIME=0','-sALLOW_MEMORY_GROWTH=1','-sMAXIMUM_MEMORY=268435456','-sSTACK_SIZE=1048576','-sINCOMING_MODULE_JS_API='+JSON.stringify(['wasmBinary','arguments','print','printErr']),'-o','build/polarized-route-proof/sqrt-standalone.mjs'],{env,stdio:'inherit'});
for(const extension of ['mjs','wasm']){const file='build/polarized-route-proof/sqrt-standalone.'+extension,bytes=readFileSync(file);writeFileSync(file+'.tmp',bytes);renameSync(file+'.tmp',file);}
