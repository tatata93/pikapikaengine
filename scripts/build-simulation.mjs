// Build the existing C++ physics kernels; no downloaded physics implementation.
import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../',import.meta.url));
const sdk=path.resolve(root,process.argv[2]??'build/toolchains/emsdk');
const upstream=path.join(sdk,'upstream/emscripten');
const version='6.0.13',sdkCommit='d7b4130688bfa348392b921ab04015aa15c4f154';
const releaseHash='eb132757325583b787fe9414b09afea9442b72ad';
const python=process.env.PYTHON??(process.platform==='win32'?'python':'python3');
const env={...process.env,EM_CONFIG:path.join(sdk,'.emscripten')};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const git=(args,cwd=root)=>execFileSync('git',args,{cwd,encoding:'utf8'}).trim();
if(git(['rev-parse','HEAD'],sdk)!==sdkCommit)throw new Error('SDK checkout must match the pinned emsdk revision');
const releases=JSON.parse(await readFile(path.join(sdk,'emscripten-releases-tags.json'),'utf8'));
if(releases.releases[version]!==releaseHash)throw new Error('SDK release mapping differs from the recorded release');
const compiler=execFileSync(python,[path.join(upstream,'em++.py'),'--version'],{env,encoding:'utf8'}).trim();
if(!compiler.includes(` ${version} (`))throw new Error('Unexpected Emscripten compiler version');
const sources=['core/src/core.cpp','core/src/portable.cpp','core/src/dynamics.cpp','core/src/hydrostatics.cpp','core/src/continuous.cpp','core/src/interval.cpp','core/src/accelerated.cpp','core/src/optics.cpp','core/src/continuous_world.cpp','core/src/optical_geometry.cpp','core/src/polarization.cpp','core/src/dispersion.cpp','core/src/optical_bounds.cpp','core/src/support.cpp','core/src/optical_route.cpp','core/src/optical_selection.cpp','core/src/optical_spot.cpp','core/src/polarized_route.cpp','core/src/polarized_packet.cpp','core/src/motion.cpp','core/src/skinning.cpp','core/src/constrained.cpp','core/src/trajectory_guard.cpp','core/src/supported_world.cpp','core/src/simulation_api.cpp'];
const headers=['core/include/pikapika/core.hpp','core/include/pikapika/portable.h','core/include/pikapika/dynamics.hpp','core/src/dynamics_internal.hpp','core/src/support_internal.hpp','core/include/pikapika/hydrostatics.hpp','core/include/pikapika/continuous.hpp','core/include/pikapika/interval.hpp','core/include/pikapika/accelerated.hpp','core/include/pikapika/optics.hpp','core/include/pikapika/optical_geometry.hpp','core/include/pikapika/polarization.hpp','core/include/pikapika/dispersion.hpp','core/include/pikapika/optical_bounds.hpp','core/include/pikapika/support.hpp','core/include/pikapika/optical_route.hpp','core/include/pikapika/optical_selection.hpp','core/include/pikapika/optical_spot.hpp','core/include/pikapika/polarized_route.hpp','core/include/pikapika/polarized_packet.hpp','core/include/pikapika/motion.hpp','core/include/pikapika/skinning.hpp','core/include/pikapika/constrained.hpp','core/include/pikapika/trajectory_guard.hpp','core/include/pikapika/supported_world.hpp','core/include/pikapika/simulation_api.h'];
const sourceFlags=Object.fromEntries(['core/src/interval.cpp','core/src/accelerated.cpp','core/src/optics.cpp','core/src/continuous_world.cpp','core/src/optical_geometry.cpp','core/src/polarization.cpp','core/src/dispersion.cpp','core/src/optical_bounds.cpp','core/src/support.cpp','core/src/optical_route.cpp','core/src/optical_selection.cpp','core/src/optical_spot.cpp','core/src/polarized_route.cpp','core/src/polarized_packet.cpp','core/src/motion.cpp','core/src/skinning.cpp','core/src/constrained.cpp','core/src/trajectory_guard.cpp','core/src/supported_world.cpp'].map(name=>[name,['-fno-fast-math','-ffp-contract=off']]));
const header=await readFile(path.join(root,headers.at(-1)),'utf8');
const exports=[...new Set([...header.matchAll(/\b(pp_sim_\w+)\s*\(/g)].map(match=>'_'+match[1]))];
if(exports.length<20)throw new Error('Missing simulation C exports');
await mkdir(path.join(root,'build/wasm-simulation'),{recursive:true});
const flags=['-std=c++20','-O2','-fwasm-exceptions','-fno-rtti','-Icore/include',
  '-sMODULARIZE=1','-sEXPORT_ES6=1','-sEXPORT_NAME=createPikapikaSimulation','-sENVIRONMENT=web,node',
  '-sFILESYSTEM=0','-sALLOW_MEMORY_GROWTH=1','-sINITIAL_MEMORY=67108864','-sMAXIMUM_MEMORY=268435456',
  '-sSTACK_SIZE=1048576','-sEXIT_RUNTIME=0','-sMALLOC=emmalloc','-sABORTING_MALLOC=0','-sASSERTIONS=1',
  '-sINCOMING_MODULE_JS_API='+JSON.stringify(['wasmBinary','print','printErr','locateFile','onAbort']),
  '-sEXPORTED_FUNCTIONS='+JSON.stringify(exports),'-sEXPORTED_RUNTIME_METHODS='+JSON.stringify(['HEAPU8','HEAPU32','HEAPF64']),
  '--emit-symbol-map','-Wl,--Map=build/wasm-simulation/link.map','-o','assets/pikapika-simulation.mjs'];
const revisionBase=git(['rev-parse','HEAD']),dirty=Boolean(git(['status','--porcelain','--untracked-files=normal']));
const beforeCompilation={};
for(const name of [...sources,...headers])beforeCompilation[name]=sha(await readFile(path.join(root,name)));
const objects=[];
for(const [source,extra]of Object.entries(sourceFlags)){
  const object='build/wasm-simulation/'+path.basename(source,'.cpp')+'.o';objects.push(object);
  execFileSync(python,[path.join(upstream,'em++.py'),source,...flags.slice(0,5),...extra,'-c','-o',object],{cwd:root,env,stdio:'inherit',timeout:300000});
}
execFileSync(python,[path.join(upstream,'em++.py'),...sources.filter(name=>!sourceFlags[name]),...objects,...flags],{cwd:root,env,stdio:'inherit',timeout:300000});
// Compiler temporary files can retain a different Windows ACL after rename.
// Recreate in the destination directory: WASM byte-exact, generated glue LF.
for(const name of ['assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm']){const file=path.join(root,name),bytes=await readFile(file);await writeFile(file+'.tmp',name.endsWith('.mjs')?Buffer.from(bytes.toString('utf8').replaceAll('\r\n','\n')):bytes);await rename(file+'.tmp',file);}
await rename(path.join(root,'assets/pikapika-simulation.mjs.symbols'),path.join(root,'build/wasm-simulation/simulation.symbols'));
const sourceSha256={};for(const name of [...sources,...headers]){
  sourceSha256[name]=sha(await readFile(path.join(root,name)));
  if(sourceSha256[name]!==beforeCompilation[name])throw new Error('Source changed during WASM compilation: '+name+'; rebuild from a stable snapshot');
}
const licenseFiles=[['LICENSE','EMSCRIPTEN-LICENSE.txt'],['system/lib/libcxx/LICENSE.TXT','LIBCXX-LICENSE.txt'],
 ['system/lib/libcxxabi/LICENSE.TXT','LIBCXXABI-LICENSE.txt'],['system/lib/libunwind/LICENSE.TXT','LIBUNWIND-LICENSE.txt'],
 ['system/lib/compiler-rt/LICENSE.TXT','COMPILER-RT-LICENSE.txt'],['system/lib/libc/musl/COPYRIGHT','MUSL-COPYRIGHT.txt']];
const licenseDir='third_party/emscripten-6.0.13';await mkdir(path.join(root,licenseDir),{recursive:true});
const licenses={};
for(const [input,output]of licenseFiles){const bytes=Buffer.from((await readFile(path.join(upstream,input),'utf8')).replaceAll('\r\n','\n'));await writeFile(path.join(root,licenseDir,output),bytes);licenses[`${licenseDir}/${output}`]=sha(bytes);}
// Preserve the per-file notices of the linked musl math objects as well.
const linkMap=await readFile(path.join(root,'build/wasm-simulation/link.map'),'utf8');
const members=[...new Set([...linkMap.matchAll(/(lib[^ /\\()]+\.a)\(([^)]+)\)/g)].map(m=>m[1]+'('+m[2]+')'))].sort();
const mathNotices=[];
for(const member of members.filter(name=>name.startsWith('libc-'))){const object=member.match(/\(([^)]+)\.o\)/)?.[1];if(!object)continue;try{const source=await readFile(path.join(upstream,'system/lib/libc/musl/src/math',object+'.c'),'utf8');const comments=source.match(/\/\*[\s\S]*?\*\//g)??[];for(const comment of comments.filter(text=>/copyright|permission|SPDX-License/i.test(text)))mathNotices.push(`${object}.c\n${comment}`);}catch(error){if(error.code!=='ENOENT')throw error;}}
const mathNoticeFile=`${licenseDir}/MUSL-MATH-NOTICES.txt`,mathNotice=Buffer.from(mathNotices.join('\n\n').replaceAll('\r\n','\n')+'\n');await writeFile(path.join(root,mathNoticeFile),mathNotice);licenses[mathNoticeFile]=sha(mathNotice);
const artifacts={};for(const name of ['assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm']){const bytes=await readFile(path.join(root,name));artifacts[name]={bytes:bytes.length,sha256:sha(bytes)};}
const manifest={schema:1,apiVersion:1,revisionBase,worktreeDirty:dirty,compiler:compiler.split('\n')[0].trimEnd(),
 sdkVersion:version,sdkCommit,releaseHash,emscriptenRevision:'e13ee988ce3d87a738dd8f3661d02223308c412a',
 sources,flags,sourceFlags,sourceSha256,artifacts,licenses,linkedLibraryMembers:members,
 runtime:'Emscripten generated ES module; libc/libc++/libc++abi/compiler-rt/emmalloc; single-threaded Wasm EH; no filesystem',
 memory:{initialBytes:67108864,maximumBytes:268435456,stackBytes:1048576},
 note:'Common authored physics sources are compiled unchanged. Existing 650-byte portable module is separate.'};
await writeFile(path.join(root,'assets/pikapika-simulation.build.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({sdk:version,exports:exports.length,artifacts,memory:manifest.memory},null,2));
