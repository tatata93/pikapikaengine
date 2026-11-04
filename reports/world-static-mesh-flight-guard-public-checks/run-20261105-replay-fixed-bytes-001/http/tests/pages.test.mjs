import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {lstat,mkdir,mkdtemp,readFile,rm,symlink,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {buildPages,localReference,runtimeReferences,safeRelative} from '../scripts/build-pages.mjs';

const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
async function fixture(t){
  const root=await mkdtemp(path.join(tmpdir(),'pikapika-pages-'));
  assert.equal(path.dirname(root),path.resolve(tmpdir()));assert.ok(path.basename(root).startsWith('pikapika-pages-'));
  t.after(async()=>{assert.equal(path.dirname(root),path.resolve(tmpdir()));assert.ok(path.basename(root).startsWith('pikapika-pages-'));await rm(root,{recursive:true,force:true});});
  const put=async(name,value)=>{await mkdir(path.dirname(path.join(root,name)),{recursive:true});await writeFile(path.join(root,name),value);};
  const git=(...args)=>execFileSync('git',['-C',root,...args],{stdio:['ignore','pipe','pipe']});
  git('init','-q');
  const files={
    'index.html':'<!doctype html><script type="importmap">{"imports":{"./engine/app.mjs":"./engine/app.mjs?build=unchanged"}}</script><script type="module" src="engine/app.mjs?build=unchanged"></script>',
    'engine/app.mjs':"fetch(new URL('../assets/scene.json',import.meta.url));\n",
    'assets/scene.json':'{"signed":-0}\r\n','assets/binary.wasm':Buffer.from([0,97,115,109,0,255,13,10]),
    'docs/guide.md':'source docs\n','.github/workflows/verify.yml':'private workflow metadata\n',
    'reports/overview.md':'[Raw evidence](raw/log.txt)\n','reports/summary.json':'{"status":"PASS"}\n',
    'reports/raw/log.txt':'large raw evidence stays in Git\n','reports/raw/http/index.html':'historical HTTP mirror\n',
    'reports/proof/keep.txt':'explicit public cohort evidence\n',
    'reports/demo-browser/index.html':'<link rel="stylesheet" href="style.css"><script type="module" src="main.mjs"></script>',
    'reports/demo-browser/main.mjs':"fetch('./input.json');\n",'reports/demo-browser/input.json':'{"value":1}\n',
    'reports/demo-browser/style.css':"body{background:url('picture.svg')}\n",'reports/demo-browser/picture.svg':'<svg/>\n',
  };
  for(const [name,value] of Object.entries(files))await put(name,value);
  const cohort={path:'reports/cohort/receipt.json',files:3,pages:2};
  await put(cohort.path,JSON.stringify({schema:1,status:'PASS',failedPaths:[],files:[
    {path:'index.html',distribution:'pages',httpStatus:200},{path:'reports/proof/keep.txt',distribution:'pages',httpStatus:200},
    {path:'.github/workflows/verify.yml',distribution:'github-source',httpStatus:200},
  ]}));
  function commit(){git('add','.');git('-c','user.name=Pages test','-c','user.email=pages-fixture@example.invalid','commit','-qm','isolated fixture');}
  commit();
  return {root,put,git,commit,cohort,options:{root,cohort,output:path.join(root,'build/site')}};
}

test('Pages selects original runtime/metadata/UI dependencies, exact cohort and records excluded evidence links',async t=>{
  const f=await fixture(t),before=await readFile(path.join(f.root,'index.html'));
  const report=await buildPages(f.options),names=new Set(report.files.map(row=>row.path));
  for(const name of ['index.html','engine/app.mjs','assets/binary.wasm','reports/overview.md','reports/summary.json','reports/proof/keep.txt','reports/demo-browser/input.json','reports/demo-browser/picture.svg'])assert.ok(names.has(name),name);
  for(const name of ['.github/workflows/verify.yml','reports/raw/log.txt','reports/raw/http/index.html'])assert.ok(!names.has(name),name);
  assert.deepEqual(await readFile(path.join(f.root,'index.html')),before,'generated import URLs and source remain unchanged');
  for(const row of report.files){const source=await readFile(path.join(f.root,row.path)),copy=await readFile(path.join(f.options.output,row.path));assert.deepEqual(copy,source,row.path);assert.equal(digest(copy),row.sha256);}
  const manifest=JSON.parse(await readFile(path.join(f.options.output,'pages-manifest.json'),'utf8'));
  assert.equal(manifest.cohort.pages,2);assert.equal(manifest.selectedBytes+manifest.excludedBytes,manifest.trackedBytes);
  assert.ok(manifest.linkImpact.some(row=>row.target==='reports/raw/log.txt'&&row.github.includes('/blob/')));
  assert.equal(report.bundleBytes,report.selectedBytes+report.manifestBytes);assert.ok(report.bundleBytes<=report.budgetBytes);
});

test('untracked content is excluded; fresh-output and byte budgets fail before copying',async t=>{
  const f=await fixture(t);await f.put('assets/untracked-secret.txt','not tracked');
  const result=await buildPages(f.options);assert.ok(!result.files.some(row=>row.path.includes('untracked')));
  await assert.rejects(buildPages(f.options),/Existing output/);
  const output=path.join(f.root,'build/too-small');await assert.rejects(buildPages({...f.options,output,budget:1}),/budget exceeded/);
  await assert.rejects(lstat(output),{code:'ENOENT'});
});

test('missing literal runtime dependency never falls back to partial publication',async t=>{
  const f=await fixture(t);await f.put('engine/app.mjs',"fetch('../reports/not-tracked.json');\n");f.commit();
  await assert.rejects(buildPages(f.options),/Missing tracked dependency/);
  await assert.rejects(lstat(f.options.output),{code:'ENOENT'});
});

test('runtime dependency outside ordinary UI selection is retained explicitly',async t=>{
  const f=await fixture(t);await f.put('reports/runtime/data.json','{"raw":-0}\n');await f.put('engine/app.mjs',"fetch('../reports/runtime/data.json');\n");f.commit();
  const result=await buildPages(f.options);assert.ok(result.files.find(row=>row.path==='reports/runtime/data.json').reasons.includes('runtime-reference:engine/app.mjs'));
});

test('Git symlink mode and unresolved merge stages are refused without following a file',async t=>{
  const f=await fixture(t);await f.put('link','assets/scene.json');const blob=f.git('hash-object','-w','--stdin').toString().trim();
  // The deliberately empty blob is enough: index mode is rejected before read.
  f.git('update-index','--add','--cacheinfo','120000,'+blob+',link');
  await assert.rejects(buildPages(f.options),/Conflict\/symlink\/unknown Git mode/);
  const other=await fixture(t),content=other.git('rev-parse',':assets/scene.json').toString().trim();
  execFileSync('git',['-C',other.root,'update-index','--index-info'],{input:`0 ${'0'.repeat(40)}\tassets/scene.json\n100644 ${content} 1\tassets/scene.json\n100644 ${content} 2\tassets/scene.json\n`});
  await assert.rejects(buildPages(other.options),/Conflict\/symlink\/unknown Git mode/);
});

test('output path and output ancestor junction cannot escape the repository',async t=>{
  const f=await fixture(t);await assert.rejects(buildPages({...f.options,output:path.join(f.root,'outside')}),/below repository build/);
  await mkdir(path.join(f.root,'elsewhere'));await mkdir(path.join(f.root,'build'));
  try{await symlink(path.join(f.root,'elsewhere'),path.join(f.root,'build/redirect'),'junction');}
  catch(error){if(['EPERM','ENOTSUP','EACCES'].includes(error.code)){t.skip('Platform denied junction creation');return;}throw error;}
  await assert.rejects(buildPages({...f.options,output:path.join(f.root,'build/redirect/site')}),/symlink refused/);
});

test('safe relative paths reject traversal, device names, control characters and case collisions',async t=>{
  for(const name of ['../x','/x','a//b','a/./b','a\\b','C:x','a\nname','con.txt','a/end.'])assert.throws(()=>safeRelative(name),/Unsafe/);
  assert.equal(safeRelative('docs/日本語.md'),'docs/日本語.md');
  const f=await fixture(t);await f.put('extra.txt','x');f.git('add','extra.txt');
  const blob=f.git('rev-parse',':extra.txt').toString().trim();f.git('update-index','--add','--cacheinfo','100644,'+blob+',EXTRA.txt');
  await assert.rejects(buildPages(f.options),/case-colliding/);
});

test('bad cohort and missing explicitly retained path are rejected',async t=>{
  const f=await fixture(t),file=path.join(f.root,f.cohort.path);const data=JSON.parse(await readFile(file,'utf8'));
  data.status='FAIL';await f.put(f.cohort.path,JSON.stringify(data));f.commit();
  await assert.rejects(buildPages(f.options),/successful cohort/);
  data.status='PASS';data.files[1].path='reports/missing.txt';await f.put(f.cohort.path,JSON.stringify(data));f.commit();
  await assert.rejects(buildPages(f.options),/Missing tracked dependency/);
});

test('reference resolution keeps project mount, cache URLs and external protocols separate',()=>{
  assert.deepEqual(localReference('tools/a.html','../assets/x.wasm?build=abc#part'),{path:'assets/x.wasm',directory:false});
  assert.equal(localReference('index.html','https://example.invalid/x'),null);
  assert.equal(localReference('index.html','data:image/png,x'),null);
  assert.throws(()=>localReference('index.html','../../outside.json'),/escapes site/);
  const rows=runtimeReferences('tools/a.html','<img src="../assets/a.svg"><script type="module">import x from "../engine/x.mjs";fetch("../assets/data.json")</script>');
  assert.deepEqual(new Set(rows.map(row=>row.path)),new Set(['assets/a.svg','engine/x.mjs','assets/data.json']));
  assert.deepEqual(runtimeReferences('docs/lesson.html','<pre>import x from "./example-only.mjs";</pre><code>&lt;img src="illustration-only.svg"&gt;</code>'),[], 'teaching text is not executable script or an HTML tag');
  assert.throws(()=>runtimeReferences('tools/float-lab.mjs',"fetch('/__capture/float')"),/guard changed/,'local-only endpoint requires its actual localhost condition');
  assert.deepEqual(runtimeReferences('reports/demo/a.css',"@import '../theme.css';"),[{path:'reports/theme.css',directory:false,value:'../theme.css'}]);
});
