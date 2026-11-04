// Version every module URL as one build, preserving unmodified source imports
// for native Node tests. Import-map URL keys also match relative nested imports.
import {readdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const modules=[];
for(const dir of ['engine','samples','tools','docs/learn','assets'])for(const name of (await readdir(path.join(root,dir))).sort())if(name.endsWith('.mjs')&&!name.endsWith('.test.mjs'))modules.push(`${dir}/${name}`);
// Version authored Source/context/level data and SDK metadata with their loaders.
// Keep sorted paths and the same text newline normalization as module inputs.
const assetData=(await readdir(path.join(root,'assets'),{withFileTypes:true})).filter(entry=>entry.isFile()&&/\.(json|scene)$/.test(entry.name)).map(entry=>`assets/${entry.name}`).sort();
const hash=createHash('sha256');
for(const name of [...modules,'style.css','assets/pikapika-core.wasm','assets/pikapika-simulation.wasm',...assetData]){hash.update(name);const bytes=await readFile(path.join(root,name));hash.update(name.endsWith('.wasm')?bytes:bytes.toString('utf8').replaceAll('\r\n','\n'));}
const build=hash.digest('hex').slice(0,16);
for(const [file,prefix,entry]of [['index.html','./','samples/app.mjs'],['tools/benchmark.html','../','benchmark.mjs'],['tools/float-lab.html','../','float-lab.mjs'],['tools/contact-lab.html','../','contact-lab.mjs'],['tools/sphere-triangle-lab.html','../','sphere-triangle-lab.mjs'],['tools/sphere-triangle-mesh-lab.html','../','sphere-triangle-mesh-lab.mjs'],['tools/sphere-triangle-mesh-trajectory-lab.html','../','sphere-triangle-mesh-trajectory-lab.mjs'],['tools/accelerated-lab.html','../','accelerated-lab.mjs'],['tools/optics-lab.html','../','optics-lab.mjs'],['tools/lens-surface-lab.html','../','lens-surface-lab.mjs'],['tools/continuous-world-lab.html','../','continuous-world-lab.mjs'],['tools/dispersion-lab.html','../','dispersion-lab.mjs'],['tools/support-lab.html','../','support-lab.mjs'],['tools/supported-world-lab.html','../','supported-world-lab.mjs'],['tools/optical-route-lab.html','../','optical-route-lab.mjs'],['tools/optical-selection-lab.html','../','optical-selection-lab.mjs'],['tools/lens-spot-lab.html','../','lens-spot-lab.mjs'],['tools/polarized-route-lab.html','../','polarized-route-lab.mjs'],['tools/lens-power-lab.html','../','lens-power-lab.mjs'],['tools/motion-lab.html','../','motion-lab.mjs'],['tools/skinning-lab.html','../','skinning-lab.mjs'],['tools/skin-binding-lab.html','../','skin-binding-lab.mjs'],['tools/derived-gpu-lab.html','../','derived-gpu-lab.mjs'],['docs/learn/buoyancy.html','../../','buoyancy.mjs']]){
  let html=await readFile(path.join(root,file),'utf8');
  const imports=Object.fromEntries(modules.map(name=>[prefix+name,prefix+name+'?build='+build]));
  const map=`<script type="importmap" id="engine-imports">${JSON.stringify({imports})}</script>`;
  html=html.replace(/<script type="importmap" id="engine-imports">[\s\S]*?<\/script>\s*/g,'');
  html=html.replace(/<script type="module" src="[^"]+"><\/script>/,`${map}\n<script type="module" src="${entry}?build=${build}"></script>`);
  html=html.replace(/href="style\.css(?:\?[^"]*)?"/g,`href="style.css?build=${build}"`);
  await writeFile(path.join(root,file),html);
}
console.log(`Web build ${build}: ${modules.length} versioned modules; generated import maps`);
