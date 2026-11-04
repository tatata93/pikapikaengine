import test from 'node:test';
import assert from 'node:assert/strict';
import {cp,mkdir,mkdtemp,readFile,readdir,rename,rm,writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const repository=fileURLToPath(new URL('../',import.meta.url));
async function fixture(t){
  const directory=await mkdtemp(path.join(tmpdir(),'pikapika-web-build-'));
  // Delete only the absolute directory returned by this test's mkdtemp.
  assert.equal(path.dirname(directory),path.resolve(tmpdir()));
  assert.ok(path.basename(directory).startsWith('pikapika-web-build-'));
  t.after(()=>rm(directory,{recursive:true,force:true}));
  for(const name of ['scripts/build-web.mjs','index.html','style.css','engine','samples','tools','docs/learn','assets']){
    await mkdir(path.dirname(path.join(directory,name)),{recursive:true});
    await cp(path.join(repository,name),path.join(directory,name),{recursive:true});
  }
  return directory;
}
function build(directory){
  const result=spawnSync(process.execPath,['scripts/build-web.mjs'],{cwd:directory,encoding:'utf8',timeout:30000});
  assert.equal(result.status,0,result.stderr||String(result.error));
  const marker=/Web build ([0-9a-f]{16}): (\d+) versioned modules/.exec(result.stdout);
  assert.ok(marker,result.stdout);return marker[1];
}
async function htmlFiles(directory){
  const result=[];
  async function visit(relative){for(const entry of await readdir(path.join(directory,relative),{withFileTypes:true})){
    const name=path.join(relative,entry.name);
    if(entry.isDirectory())await visit(name);else if(name.endsWith('.html'))result.push(name);
  }}
  for(const relative of ['tools','docs/learn'])await visit(relative);
  return ['index.html',...result];
}
const authoredHTML=text=>text.replace(/<script type="importmap" id="engine-imports">[\s\S]*?<\/script>\s*/g,'').replaceAll(/\?build=[0-9a-f]{16}/g,'');
async function verifyPages(directory,marker,before){
  let count=0;
  for(const name of await htmlFiles(directory)){
    const text=await readFile(path.join(directory,name),'utf8');
    assert.equal(authoredHTML(text),before.get(name),name+' authored content');
    const maps=[...text.matchAll(/<script type="importmap" id="engine-imports">([\s\S]*?)<\/script>/g)];
    if(!maps.length)continue;
    assert.equal(maps.length,1,name);++count;
    const imports=JSON.parse(maps[0][1]).imports;
    for(const [key,url]of Object.entries(imports))assert.equal(url,key+'?build='+marker,name+' '+key);
    const entry=/<script type="module" src="([^"]+)"><\/script>/.exec(text);
    assert.ok(entry,name);assert.ok(entry[1].endsWith('?build='+marker),name);
  }
  assert.equal(count,25,'all current game/lab/lesson entry points');
}
test('asset-only Source changes reach the real cover loader through a new build URL',async t=>{
  const directory=await fixture(t),file=path.join(directory,'assets/robot-back-cover.skin.json');
  const before=new Map(await Promise.all((await htmlFiles(directory)).map(async name=>[name,authoredHTML(await readFile(path.join(directory,name),'utf8'))])));
  const original=await readFile(file,'utf8'),first=build(directory);
  async function load(marker){
    const {RobotBackCover}=await import(pathToFileURL(path.join(directory,'samples/back-cover.mjs'))+'?build='+marker);
    const oldFetch=globalThis.fetch,requests=[];
    globalThis.fetch=async url=>{requests.push(String(url));return {ok:true,text:()=>readFile(fileURLToPath(url),'utf8')};};
    try{
      const cover=new RobotBackCover({dropMesh(){}});
      await cover.load({loadRuntime:async()=>({diagnostics:{backend:'asset URL test only'}})});
      assert.equal(cover.state,'ready');assert.equal(requests.length,1);
      const request=new URL(requests[0]);assert.equal(request.searchParams.get('build'),marker);
      assert.equal(fileURLToPath(request),file);assert.equal(cover.startup.assetURL,requests[0]);
      const name=cover.source.name;cover.dispose();return {url:requests[0],name};
    }finally{globalThis.fetch=oldFetch;}
  }
  const initial=await load(first),source=JSON.parse(original);source.name+=' isolated revision';
  await writeFile(file,JSON.stringify(source)+'\n');
  const changed=build(directory);
  assert.notEqual(changed,first,'Source-only revision must invalidate module and asset URLs');
  const loaded=await load(changed);assert.notEqual(loaded.url,initial.url);assert.equal(loaded.name,source.name);
  await verifyPages(directory,changed,before);
  assert.equal(build(directory),changed,'unchanged rebuild is stable');
  await writeFile(file,original);assert.equal(build(directory),first,'restoring exact Source restores build');
});
test('context, level, metadata and portable asset-only changes invalidate the build',async t=>{
  const directory=await fixture(t),baseline=build(directory);
  for(const name of ['robot-back-cover.scene.json','iron-field.scene.json','pikapika-simulation.build.json','iron-field.scene']){
    const file=path.join(directory,'assets',name),original=await readFile(file);
    await writeFile(file,Buffer.concat([original,Buffer.from('\n')]));
    assert.notEqual(build(directory),baseline,name);
    await writeFile(file,original);assert.equal(build(directory),baseline,name+' restore');
  }
  const file=path.join(directory,'assets/extra.skin.json'),renamed=path.join(directory,'assets/renamed.skin.json');
  await writeFile(file,'{"version":1}\n');const added=build(directory);assert.notEqual(added,baseline);
  await rename(file,renamed);assert.notEqual(build(directory),added,'asset path is part of identity');
  await rm(renamed);assert.equal(build(directory),baseline);
});
test('module, stylesheet and both WASM byte changes retain cache invalidation',async t=>{
  const directory=await fixture(t),baseline=build(directory);
  for(const name of ['engine/scene.mjs','samples/back-cover.mjs','tools/benchmark.mjs','tools/sphere-triangle-mesh-entry-lab.mjs','docs/learn/buoyancy.mjs','assets/pikapika-simulation.mjs','style.css','assets/pikapika-core.wasm','assets/pikapika-simulation.wasm']){
    const file=path.join(directory,name),original=await readFile(file);
    await writeFile(file,Buffer.concat([original,Buffer.from([10])]));
    assert.notEqual(build(directory),baseline,name);
    await writeFile(file,original);assert.equal(build(directory),baseline,name+' restore');
  }
});
test('asset enumeration order and checkout line endings do not churn build URLs',async t=>{
  const directory=await fixture(t),baseline=build(directory);
  const a=path.join(directory,'assets/a.scene.json'),z=path.join(directory,'assets/z.scene.json');
  await writeFile(z,'{"name":"z"}\n');await writeFile(a,'{"name":"a"}\n');const first=build(directory);
  await rm(a);await rm(z);await writeFile(a,'{"name":"a"}\n');await writeFile(z,'{"name":"z"}\n');
  assert.equal(build(directory),first);await rm(a);await rm(z);
  for(const name of ['samples/back-cover.mjs','assets/robot-back-cover.skin.json','assets/robot-back-cover.scene.json']){
    const file=path.join(directory,name),original=await readFile(file,'utf8');
    await writeFile(file,original.replaceAll('\r\n','\n').replaceAll('\n','\r\n'));
  }
  assert.equal(build(directory),baseline);
});
