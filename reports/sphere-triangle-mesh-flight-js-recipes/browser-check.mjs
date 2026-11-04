// Audit complete visible browser results against saved actual-owned Node DTOs.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {parseStrictJson} from '../../engine/strict-json.mjs';
const [phase,ownedFile]=process.argv.slice(2);assert.ok(['local','public'].includes(phase));assert.ok(ownedFile);
const root=new URL('../../',import.meta.url),dir=new URL('reports/sphere-triangle-mesh-flight-js-browser/',root);
const budget={maxBytes:67108864,maxDepth:64,maxNodes:4000000};
const load=async url=>parseStrictJson(await readFile(url,'utf8'),budget);
const packet=await load(new URL(phase+'-api-result.json',dir)),owned=await load(new URL(ownedFile,root));
assert.equal(packet.schema,1);assert.equal(packet.kind,'sphere-triangle-mesh-flight-owned-browser-proof');assert.equal(packet.rows.length,2);
const bits=new DataView(new ArrayBuffer(8));let numericBits=0,negativeZeroBits=0;
function compare(a,b,label){
  assert.equal(typeof a,typeof b,label);
  if(typeof a==='number'){assert.ok(Number.isFinite(a));bits.setFloat64(0,a);const aa=bits.getBigUint64(0);bits.setFloat64(0,b);assert.equal(aa,bits.getBigUint64(0),label);numericBits++;if(Object.is(a,-0))negativeZeroBits++;}
  else if(a!==null&&typeof a==='object'){assert.ok(b!==null);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const k of Object.keys(a))compare(a[k],b[k],label+'.'+k);}
  else assert.equal(a,b,label);
}
const api=[];
for(const row of packet.rows){
  const expected=owned.fixtures.find(f=>f.cohort===row.mode&&f.name===row.name);assert.ok(expected?.result);
  const before={numericBits,negativeZeroBits};compare(row.input,expected.input,row.mode+'.input');compare(row.result,expected.result,row.mode+'.result');
  api.push({mode:row.mode,name:row.name,status:row.result.status,numericBits:numericBits-before.numericBits,negativeZeroBits:negativeZeroBits-before.negativeZeroBits});
}
assert.equal(packet.rows[0].result.status,'entry_window');assert.equal(packet.rows[1].result.status,'certified_separated');
const html=await readFile(new URL('index.html',root),'utf8'),buildId=html.match(/\?build=([a-f0-9]{16})/)[1];
assert.equal(packet.diagnostics.buildId,buildId);assert.equal(packet.diagnostics.wasmBytes,800982);
const game=await load(new URL(phase+'-game-cover-report.json',dir)),state=await readFile(new URL(phase+'-game-ax.txt',dir),'utf8');
assert.equal(game.state,'ready');assert.equal(game.failure,null);assert.equal(game.pending,null);assert.deepEqual(game.errors,[]);
assert.ok(game.counts.queries>0);assert.equal(game.counts.queries,game.counts.checked);assert.equal(game.counts.checked,game.counts.validated);assert.equal(game.records.length,game.counts.queries);
assert.ok(game.records.every(r=>r.state==='completed'));assert.ok(game.records.some(r=>r.clipSeconds===1));
assert.equal(game.renderer.residentMeshes,3);assert.equal(game.renderer.lost,false);assert.equal(game.renderer.disposed,false);
assert.equal(game.startup.diagnostics.buildId,buildId);assert.equal(game.startup.diagnostics.wasmBytes,800982);
assert.match(state,/一時停止 \/ Pで再開/);const kills=Number(state.match(/撃破\s+(\d+)/)[1]);assert.ok(kills>0);
const evidence={};
for(const name of ['diagram.jpg','api.jpg','api-result.json','api-ax.txt','game.jpg','game-ax.txt','game-cover-report.json']){
  const filename=phase+'-'+name,data=await readFile(new URL(filename,dir));assert.ok(data.length>0);evidence[filename]={bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')};
}
const report={schema:1,status:'PASS',phase,buildId,wasmBytes:800982,api:{fixtures:2,numericBits,negativeZeroBits,cases:api,scope:'Complete visible input and owned DTOs compared to canonical actual-owned Node DTOs; those are separately matched to Native and independently Fraction checked.'},game:{paused:true,kills,coverQueries:game.counts.queries,allCompleted:true,boostClip1Observed:true,residentMeshes:3},evidence,scope:'Actual HTTP browser fixed API calls and original game regression. No manual editor, World response, performance or allocation measurement.'};
await writeFile(new URL(phase==='local'?'browser-verification.json':'public-browser-verification.json',dir),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
