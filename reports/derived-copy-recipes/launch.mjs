import {spawnSync} from 'node:child_process';
import {writeFile,readFile} from 'node:fs/promises';
import {randomBytes,createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../../',import.meta.url)),base=fileURLToPath(new URL('./',import.meta.url));
const prefix='invocation-'+Date.now()+'-'+randomBytes(4).toString('hex'),args=['build/derived-copy-pilot/run.mjs','--run'];
const begin=performance.now(),startedAt=new Date().toISOString(),run=spawnSync(process.execPath,args,{cwd:root,timeout:30000,maxBuffer:2*1024*1024});
const files=[];
for(const [kind,data]of [['stdout',run.stdout??Buffer.alloc(0)],['stderr',run.stderr??Buffer.alloc(0)]]){const name=prefix+'.'+kind+'.txt';await writeFile(path.join(base,name),data,{flag:'wx'});files.push({name,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')});}
const script=await readFile(new URL('./run.mjs',import.meta.url)),launcher=await readFile(new URL('./launch.mjs',import.meta.url));
const record={schema:1,startedAt,elapsedMs:performance.now()-begin,command:[process.execPath,...args],cwd:root,exitCode:run.status,signal:run.signal,error:run.error?{code:run.error.code,message:run.error.message}:null,stdoutStderr:files,scriptSha256:createHash('sha256').update(script).digest('hex'),launcherSha256:createHash('sha256').update(launcher).digest('hex'),concurrency:'Parent confirmed heavy local suite/GPU measurements completed before this invocation. Parent performs light archive/commit/GitHub reads only.'};
await writeFile(path.join(base,prefix+'.json'),JSON.stringify(record,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(record,null,2));
if(run.status!==0||run.error)process.exitCode=1;
