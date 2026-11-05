// Bundle tracked publication files without rewriting any source/build URL.
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {constants} from 'node:fs';
import {copyFile,lstat,mkdir,readFile,realpath,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const DEFAULT_BUDGET=384*1024*1024;
export const DEFAULT_COHORT={path:'reports/world-static-mesh-flight-advance-public-checks/run-20261105-bytes-001/receipt.json',files:217,pages:216};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const need=(condition,message)=>{if(!condition)throw new Error(message);};
const inside=(root,target)=>target!==root&&!path.relative(root,target).startsWith('..'+path.sep)&&!path.isAbsolute(path.relative(root,target));
export function safeRelative(name){
  need(typeof name==='string'&&name.length>0&&!name.includes('\\')&&!/[\x00-\x1f:]/.test(name)&&!name.startsWith('/'),'Unsafe relative path: '+name);
  need(name.split('/').every(part=>part&&part!=='.'&&part!=='..'&&!/[. ]$/.test(part)&&! /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part)),'Unsafe path component: '+name);
  return name;
}
function git(root,args){return execFileSync('git',['-C',root,...args],{maxBuffer:32*1024*1024});}
async function checkedFile(root,name,parents){
  safeRelative(name);
  const full=path.resolve(root,...name.split('/'));need(inside(root,full),'Source path escape');
  let current=root;
  for(const component of name.split('/').slice(0,-1)){
    current=path.join(current,component);
    if(!parents.has(current)){const item=await lstat(current);need(item.isDirectory()&&!item.isSymbolicLink(),'Symlink/non-directory ancestor: '+current);parents.add(current);}
  }
  const item=await lstat(full);need(item.isFile()&&!item.isSymbolicLink(),'Non-regular tracked file: '+name);
  need(await realpath(full)===full,'Real source path differs: '+name);
  return {full,bytes:item.size};
}
export function localReference(owner,value){
  value=value.trim();if(!value||value.startsWith('#')||/^[a-z][a-z0-9+.-]*:/i.test(value)||value.startsWith('//'))return null;
  const base='https://pages.invalid/pikapikaengine/';
  const url=new URL(value,base+owner);
  need(url.origin==='https://pages.invalid'&&url.pathname.startsWith('/pikapikaengine/'),'Runtime reference escapes site: '+owner+' -> '+value);
  const result=decodeURIComponent(url.pathname.slice('/pikapikaengine/'.length));
  return {path:result.endsWith('/')?result.slice(0,-1):result,directory:result.endsWith('/')};
}
export function runtimeReferences(name,text){
  const found=[];const add=value=>{
    // Existing capture POST is intentionally gated off on public Pages. This
    // exact conditional endpoint is not an asset and cannot be served statically.
    if(name==='tools/float-lab.mjs'&&value==='/__capture/float'){
      need(text.includes("globalThis.location?.protocol==='http:'&&['localhost','127.0.0.1'].includes(globalThis.location.hostname)&&new URL(globalThis.location.href).searchParams.get('capture')==='1'"),'Local capture guard changed; explicit policy review required');
      found.push({value,localOnly:true,reason:'Existing localhost HTTP + capture=1 POST; not a published asset'});return;
    }
    const ref=localReference(name,value);if(ref)found.push({...ref,value});
  };
  let javascript=/\.m?js$/.test(name)?text:'',css=name.endsWith('.css')?text:'';
  if(name.endsWith('.html')){
    for(const tag of text.matchAll(/<[a-z][^>]*>/gi)){
      for(const match of tag[0].matchAll(/\b(?:src|href|poster)\s*=\s*["']([^"']+)["']/gi))add(match[1]);
      for(const match of tag[0].matchAll(/\bstyle\s*=\s*["']([^"']+)["']/gi))css+='\n'+match[1];
    }
    for(const match of text.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi))if(!/\btype=["'](?:importmap|application\/[^"']+)["']/i.test(match[1]))javascript+='\n'+match[2];
    for(const match of text.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi))css+='\n'+match[1];
    for(const match of text.matchAll(/<script\b[^>]*type=["']importmap["'][^>]*>([\s\S]*?)<\/script>/gi)){
      const map=JSON.parse(match[1]);need(map&&typeof map.imports==='object','Import-map imports required: '+name);
      for(const value of Object.values(map.imports)){need(typeof value==='string','Import-map string URL');add(value);}
    }
  }
  if(javascript){
    for(const regex of [/\b(?:import|export)\s+(?:[^;'"\n]*?\s+from\s*)?["']([^"']+)["']/g,/\bimport\s*\(\s*["']([^"']+)["']/g,/\bfetch\s*\(\s*["']([^"']+)["']/g,/\bnew\s+URL\s*\(\s*["']([^"']+)["']/g]){
      for(const match of javascript.matchAll(regex))if(!match[1].includes('${'))add(match[1]);
    }
  }
  if(css){
    for(const match of css.matchAll(/url\(\s*["']?([^\s)'";]+)["']?\s*\)/gi))add(match[1]);
    for(const match of css.matchAll(/@import\s*["']([^"']+)["']/gi))add(match[1]);
  }
  return found;
}

export async function buildPages({root,output,budget=DEFAULT_BUDGET,cohort=DEFAULT_COHORT}={}){
  root=path.resolve(root??path.join(path.dirname(fileURLToPath(import.meta.url)),'..'));
  need((await lstat(root)).isDirectory()&&await realpath(root)===root,'Repository root must be a real directory');
  output=path.resolve(output??path.join(root,'build/pages-site'));
  need(Number.isSafeInteger(budget)&&budget>0&&budget<=DEFAULT_BUDGET,'Budget must be an integer in (0,384MiB]');
  const build=path.join(root,'build');need(inside(build,output),'Output must be a new directory below repository build/');
  // Validate each existing output ancestor before making any directories.
  let current=root;
  for(const component of path.relative(root,output).split(path.sep)){
    current=path.join(current,component);
    try{const item=await lstat(current);need(current!==output&&item.isDirectory()&&!item.isSymbolicLink(),'Existing output/symlink refused: '+current);}
    catch(error){if(error.code!=='ENOENT')throw error;}
  }
  const index=git(root,['ls-files','--stage','-z']);
  const text=index.toString('utf8');need(Buffer.from(text).equals(index),'Tracked names must be UTF-8');
  const inventory=new Map(),parents=new Set(),caseNames=new Set();
  for(const entry of text.split('\0').filter(Boolean)){
    const match=/^(\d{6}) ([0-9a-f]{40,64}) (\d)\t([\s\S]+)$/.exec(entry);need(match&&match[3]==='0'&&['100644','100755'].includes(match[1]),'Conflict/symlink/unknown Git mode refused');
    const name=safeRelative(match[4]);need(!inventory.has(name)&&!caseNames.has(name.toLowerCase()),'Duplicate/case-colliding tracked path: '+name);caseNames.add(name.toLowerCase());
    need(!name.startsWith(path.relative(root,output).split(path.sep).join('/')+'/'),'Output overlaps tracked source');
    inventory.set(name,{name,mode:match[1],gitBlob:match[2]});
  }
  // Complete name/mode collision validation before touching any source. This
  // also makes Windows case-insensitive aliases fail for the same reason as GNU.
  for(const [name,item] of inventory)Object.assign(item,await checkedFile(root,name,parents));
  need(inventory.has(cohort.path),'Required publication cohort is not tracked');
  const receipt=JSON.parse((await readFile(inventory.get(cohort.path).full)).toString('utf8'));
  need(receipt.schema===1&&receipt.status==='PASS'&&Array.isArray(receipt.files)&&receipt.files.length===cohort.files&&receipt.failedPaths?.length===0,'Known successful cohort receipt required');
  const publicRows=receipt.files.filter(row=>row.distribution==='pages');
  need(publicRows.length===cohort.pages&&new Set(publicRows.map(row=>row.path)).size===cohort.pages,'Exact Pages cohort count/unique paths');
  const selected=new Map();
  function add(name,reason){safeRelative(name);need(inventory.has(name),'Missing tracked dependency: '+name);need(!name.startsWith('.git/')&&!name.startsWith('.github/'),'Private repository metadata dependency refused: '+name);if(!selected.has(name))selected.set(name,new Set());selected.get(name).add(reason);}
  const webRoots=new Set([...inventory.keys()].filter(name=>/^reports\/[^/]+\/[^/]+\.html$/.test(name)).map(name=>path.posix.dirname(name)));
  for(const name of inventory.keys()){
    if(name==='.git'||name.startsWith('.git/')||name==='.github'||name.startsWith('.github/'))continue;
    if(!name.startsWith('reports/'))add(name,'tracked-non-report');
    else if(name.endsWith('.md'))add(name,'report-markdown');
    else if(/^reports\/[^/]+\.json$/.test(name))add(name,'top-level-report-json');
    for(const directory of webRoots)if(name.startsWith(directory+'/'))add(name,'report-web-entry-siblings:'+directory);
  }
  for(const row of publicRows){need(row.httpStatus===200,'Cohort must contain actual successful responses');add(row.path,'accepted-pages-cohort');}
  // Do not mistake archived HTTP/source mirrors for live entry points. Only
  // current ordinary HTML and direct report HTML roots seed runtime closure.
  const queue=[...selected.keys()].filter(name=>name.endsWith('.html')&&(!name.startsWith('reports/')||webRoots.has(path.posix.dirname(name))));
  const visited=new Set(),dependencies=[];
  while(queue.length){
    const name=queue.shift();if(visited.has(name))continue;visited.add(name);
    const source=(await readFile(inventory.get(name).full)).toString('utf8');
    for(const ref of runtimeReferences(name,source)){
      if(ref.localOnly){dependencies.push({from:name,...ref});continue;}
      if(!ref.path)continue;
      if(ref.directory){need([...inventory.keys()].some(p=>p.startsWith(ref.path+'/')),'Missing runtime directory: '+name+' -> '+ref.value);dependencies.push({from:name,to:ref.path,directory:true});continue;}
      add(ref.path,'runtime-reference:'+name);dependencies.push({from:name,to:ref.path});
      if(/\.(?:html|css|m?js)$/.test(ref.path))queue.push(ref.path);
    }
  }
  const head=git(root,['rev-parse','HEAD']).toString('utf8').trim();need(/^[0-9a-f]{40,64}$/.test(head),'Git HEAD identity');
  const files=[],excluded=[],linkImpact=[];
  let sourceBytes=0,selectedBytes=0;
  for(const [name,item] of [...inventory].sort(([a],[b])=>a.localeCompare(b,'en'))){
    sourceBytes+=item.bytes;
    if(selected.has(name)){
      const raw=await readFile(item.full);need(raw.length===item.bytes,'Selected source size changed: '+name);selectedBytes+=raw.length;
      files.push({path:name,bytes:raw.length,sha256:sha(raw),gitBlob:item.gitBlob,reasons:[...selected.get(name)].sort()});
      if(name.endsWith('.md'))for(const match of raw.toString('utf8').matchAll(/\]\(<?([^\s)>]+)>?\)/g)){
        let ref;try{ref=localReference(name,match[1]);}catch{continue;}
        if(ref&&inventory.has(ref.path)&&!selected.has(ref.path))linkImpact.push({from:name,target:ref.path,github:`https://github.com/tatata93/pikapikaengine/blob/${head}/${ref.path.split('/').map(encodeURIComponent).join('/')}`,reason:'tracked evidence omitted from Pages; original remains in Git'});
      }
    }else excluded.push({path:name,bytes:item.bytes,gitBlob:item.gitBlob,reason:name.startsWith('.github/')?'github-workflow-metadata':'nested-report-evidence-not-runtime'});
  }
  const manifest={schema:1,kind:'pikapika-pages-bundle',status:'PASS',head,sourceInventorySha256:sha(index),budgetBytes:budget,
    trackedFiles:inventory.size,trackedBytes:sourceBytes,selectedFiles:files.length,selectedBytes,excludedFiles:excluded.length,excludedBytes:sourceBytes-selectedBytes,
    cohort:{path:cohort.path,sha256:sha(await readFile(inventory.get(cohort.path).full)),total:receipt.files.length,pages:publicRows.length,scope:'Path coverage retained; output bytes match current worktree files, not a claim that all current files equal a historical feature.'},
    policy:{nonReports:'All tracked regular non-reports except .git/.github; no untracked files.',reports:'All Markdown, all top-level JSON (canonical superset), direct report HTML entry directories and siblings, explicit accepted Pages cohort, recursive literal runtime dependencies.',rawEvidence:'Nested raw logs/fixtures/HTTP and source mirrors remain in Git; selected dependencies/cohort take precedence.',webRoots:[...webRoots].sort()},
    dependencyScope:'Static literal HTML/import-map/import/export/dynamic-import/fetch/new-URL/CSS-url references; non-report runtime trees and declared report entry siblings are kept whole. Not a general JS execution proof.',
    files,excluded,dependencies,linkImpact};
  const manifestBytes=Buffer.from(JSON.stringify(manifest,null,2)+'\n');
  need(!inventory.has('pages-manifest.json'),'Manifest path conflicts with tracked source');
  need(selectedBytes+manifestBytes.length<=budget,'Pages bundle budget exceeded before copying: '+(selectedBytes+manifestBytes.length)+' > '+budget);
  await mkdir(output,{recursive:true});
  for(const row of files){
    const item=inventory.get(row.path);await checkedFile(root,row.path,new Set());
    const target=path.join(output,...row.path.split('/'));need(inside(output,target),'Output file escape');
    await mkdir(path.dirname(target),{recursive:true});await copyFile(item.full,target,constants.COPYFILE_EXCL);
    const copied=await readFile(target),again=await readFile(item.full);
    need(copied.length===row.bytes&&sha(copied)===row.sha256&&sha(again)===row.sha256,'Source/output byte mismatch: '+row.path);
  }
  need(git(root,['ls-files','--stage','-z']).equals(index)&&git(root,['rev-parse','HEAD']).toString('utf8').trim()===head,'Git inventory/HEAD changed during bundle');
  await writeFile(path.join(output,'pages-manifest.json'),manifestBytes,{flag:'wx'});
  return {...manifest,output,manifestBytes:manifestBytes.length,bundleBytes:selectedBytes+manifestBytes.length};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const args=process.argv.slice(2);let output,budget=DEFAULT_BUDGET;
    for(let i=0;i<args.length;i++){
      if(args[i]==='--output'&&args[i+1])output=args[++i];
      else if(args[i]==='--budget-bytes'&&/^[1-9]\d*$/.test(args[i+1]??''))budget=Number(args[++i]);
      else throw new Error('Usage: node scripts/build-pages.mjs [--output FRESH_BUILD_DIRECTORY] [--budget-bytes INTEGER]');
    }
    const result=await buildPages({output,budget});
    console.log(JSON.stringify({status:'PASS',output:result.output,selectedFiles:result.selectedFiles,selectedBytes:result.selectedBytes,excludedFiles:result.excludedFiles,excludedBytes:result.excludedBytes,manifestBytes:result.manifestBytes,bundleBytes:result.bundleBytes,budgetBytes:result.budgetBytes,cohortPages:result.cohort.pages,reportWebRoots:result.policy.webRoots,affectedEvidenceLinks:result.linkImpact.length}));
  }catch(error){console.error('Pages bundle FAILED: '+error.message);process.exitCode=1;}
}
