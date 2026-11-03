import assert from 'node:assert/strict';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {hashProfileDTO} from '../../scripts/profile-derived-mesh.mjs';
const root=fileURLToPath(new URL('../../',import.meta.url)),base=fileURLToPath(new URL('./',import.meta.url));
assert.equal(process.argv.length,3);const dir=path.resolve(root,process.argv[2]);assert.equal(path.dirname(dir),path.resolve(base));assert.match(path.basename(dir),/^run-[0-9]+-[0-9a-f]{8}$/);
const load=async name=>JSON.parse(await readFile(path.join(dir,name),'utf8'));
const [report,provenance,prepare,micro,inputs,ownership]=await Promise.all(['report.json','provenance.json','prepare-trials.json','micro-trials.json','inputs.json','ownership.json'].map(load));
assert.equal(report.status,'PASS');assert.ok(report.elapsedMs<30000);assert.deepEqual(provenance.before,provenance.after);
function decode(x){
 if(x.type==='null')return null;
 if(x.type==='number'){assert.match(x.bits,/^[0-9a-f]{16}$/);return Buffer.from(x.bits,'hex').readDoubleBE();}
 if(x.type==='Object')return Object.fromEntries(x.entries.map(([key,value])=>[key,decode(value)]));
 if(x.type==='Array')return x.items.map(decode);
 if(x.type==='string'||x.type==='boolean')return x.value;
 const constructors={Float32Array,Float64Array,Uint32Array,Uint8Array,Int32Array};assert.ok(Object.hasOwn(constructors,x.type));const type=constructors[x.type],bytes=Buffer.from(x.bytesHex,'hex'),out=new type(x.length);assert.equal(bytes.length,out.byteLength);new Uint8Array(out.buffer).set(bytes);return out;
}
assert.deepEqual(hashProfileDTO(decode(inputs.casesExact)),inputs.inputHash);
assert.equal(prepare.trials.length,15);let compared=0;
const names=['actual-source-4','rational-normal-64','sheared-grid-512'];
for(const [c,name]of names.entries()){
 const rows=prepare.trials.filter(r=>r.caseName===name);assert.equal(rows.length,5);
 for(const [j,row]of rows.entries()){assert.equal(row.pair,j);assert.equal(row.phase,['initial','warmup','measure','measure','measure'][j]);assert.deepEqual(row.order,(j+c)%2?['candidate','old']:['old','candidate']);for(const kind of ['old','candidate'])assert.ok(Number.isFinite(row.timing[kind].elapsedMs)&&row.timing[kind].elapsedMs>=0);compared+=row.hash.counts.numbers+row.hash.counts.typedElements;}
 const full=prepare.firstPairFullDTO.find(x=>x.caseName===name),old=decode(full.old),candidate=decode(full.candidate);assert.deepStrictEqual(old,candidate);assert.deepEqual(hashProfileDTO(old),rows[0].hash);
}
assert.equal(compared,report.comparedNumericValues);assert.equal(report.timedPrepareQueries,30);
assert.deepEqual(micro.records.map(r=>decode(r.values).length),[3,18,26,20,64]);assert.match(micro.records.at(-1).origin,/Synthetic/);assert.equal(micro.trials.length,25);
for(const row of micro.trials){assert.equal(row.iterations,10000);for(const kind of ['old','candidate']){assert.ok(Number.isFinite(row.timing[kind].elapsedMs)&&row.timing[kind].elapsedMs>=0);assert.equal(row.timing[kind].perCopyMs,row.timing[kind].elapsedMs/10000);}}
assert.deepEqual(ownership.checks.map(x=>x.length),[0,3,18,20,26,64]);for(const row of ownership.checks)for(const key of ['arrayDense','heapMutationIsolated','replacementViewObserved','subarrayClampingIdentical'])assert.equal(row[key],true);
const files=[];for(const name of await readdir(dir)){const bytes=await readFile(path.join(dir,name));files.push({name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});}
const result={schema:1,status:'PASS',preparePairs:15,microPairs:25,microCopies:500000,comparedNumericValues:compared,firstPairExactDecodingVerified:3,sdkSourceAndNoticeAndArtifactHashesEqualBeforeAfter:true,files,notes:'Light evidence audit only, not another performance measurement. All times and hashes retained from the sole invocation.'};
await writeFile(path.join(dir,'acceptance.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result,null,2));
