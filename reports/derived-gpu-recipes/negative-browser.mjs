import assert from 'node:assert/strict';
import {readFile,mkdir,mkdtemp,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {stringifyStrictJson} from '../../engine/strict-json.mjs';
const root=fileURLToPath(new URL('../../',import.meta.url)),base=path.join(root,'build/derived-gpu-browser-controls');await mkdir(base,{recursive:true});const out=await mkdtemp(path.join(base,'run-'));
const originals=['4','64','512','retry-4'].map(n=>path.join(root,'reports/derived-gpu-local-'+n+'.json')),raw=await readFile(originals[0],'utf8'),source=JSON.parse(raw),script=path.join(root,'scripts/verify-derived-gpu-lab.mjs'),sha=b=>createHash('sha256').update(b).digest('hex'),results=[];
function falseTyped(x){if(x&&typeof x==='object'){if(x.type==='Float32Array'){x.bytesHex=(x.bytesHex.startsWith('00')?'01':'00')+x.bytesHex.slice(2);return true;}return Object.values(x).some(falseTyped);}return false;}
for(const [name,change] of [
 ['changed-input',r=>r.input.positions[0][0]+=.25],
 ['false-full-dto',r=>assert.ok(falseTyped(r.firstPair.baseline))],
 ['missing-trial',r=>r.trials.pop()],
 ['cache-upload',r=>r.trials[0].draw.baseline.cache.delta.uploadedMeshBytes=4],
 ['false-retirement',r=>r.trials[0].draw.baseline.fresh.delta.destroyedMeshBuffers=1],
 ['false-summary',r=>r.summary[0].statistics.medianMs+=.25],
 ['failed-draw-as-success',r=>r.trials[0].draw.baseline.fresh.state='failed']
]){
 const packet=structuredClone(source);change(packet);const input=path.join(out,name+'.json'),data=stringifyStrictJson(packet)+'\n';await writeFile(input,data,{flag:'wx'});const args=[script,input,...originals.slice(1)];let status=0,stdout='',stderr='';
 try{stdout=execFileSync(process.execPath,args,{cwd:root,encoding:'utf8',windowsHide:true,stdio:['ignore','pipe','pipe'],maxBuffer:4*1024*1024});}catch(error){status=error.status;stdout=error.stdout??'';stderr=error.stderr??String(error);}
 await writeFile(path.join(out,name+'.stdout.txt'),stdout,{flag:'wx'});await writeFile(path.join(out,name+'.stderr.txt'),stderr,{flag:'wx'});assert.ok(Number.isInteger(status)&&status!==0,name+' must be rejected');assert.match(stderr,/AssertionError/);
 results.push({name,command:[process.execPath,...args],exitCode:status,inputSHA256:sha(data),stdoutSHA256:sha(stdout),stderrSHA256:sha(stderr)});
}
const report={status:'PASS',rejected:results.length,scope:'Targeted consistency-check controls; not a GPU clock attestation or arbitrary-packet proof.',sourceSHA256:sha(await readFile(script)),recipeSHA256:sha(await readFile(fileURLToPath(import.meta.url))),runDirectory:out,results};await writeFile(path.join(out,'controls.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({status:'PASS',rejected:results.length,runDirectory:out},null,2));
