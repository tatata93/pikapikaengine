// Version every module URL as one build, preserving unmodified source imports
// for native Node tests. Import-map URL keys also match relative nested imports.
import {readdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const modules=[];
for(const dir of ['engine','samples','tools'])for(const name of (await readdir(path.join(root,dir))).sort())if(name.endsWith('.mjs'))modules.push(`${dir}/${name}`);
const hash=createHash('sha256');
for(const name of [...modules,'style.css','assets/pikapika-core.wasm']){hash.update(name);const bytes=await readFile(path.join(root,name));hash.update(name.endsWith('.wasm')?bytes:bytes.toString('utf8').replaceAll('\r\n','\n'));}
const build=hash.digest('hex').slice(0,16);
for(const [file,prefix,entry]of [['index.html','./','samples/app.mjs'],['tools/benchmark.html','../','benchmark.mjs']]){
  let html=await readFile(path.join(root,file),'utf8');
  const imports=Object.fromEntries(modules.map(name=>[prefix+name,prefix+name+'?build='+build]));
  const map=`<script type="importmap" id="engine-imports">${JSON.stringify({imports})}</script>`;
  html=html.replace(/<script type="importmap" id="engine-imports">[\s\S]*?<\/script>\s*/g,'');
  html=html.replace(/<script type="module" src="[^"]+"><\/script>/,`${map}\n<script type="module" src="${entry}?build=${build}"></script>`);
  html=html.replace(/href="style\.css(?:\?[^"]*)?"/g,`href="style.css?build=${build}"`);
  await writeFile(path.join(root,file),html);
}
console.log(`Web build ${build}: ${modules.length} versioned modules; no external bundler/runtime`);
