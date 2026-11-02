import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {createServer} from '../scripts/serve.mjs';
test('local static host serves modules and blocks hidden/escaped files',async()=>{const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const port=s.address().port;try{const response=await fetch(`http://127.0.0.1:${port}/`);assert.equal(response.status,200);assert.match(await response.text(),/IRON FIELD/);assert.equal(response.headers.get('cross-origin-embedder-policy'),'require-corp');for(const path of ['/.git/config','/%2e%67it/config','/engine/math.mjs']){const r=await fetch(`http://127.0.0.1:${port}${path}`);assert.equal(r.status,path.includes('math')?200:403);}const r=await new Promise((resolve,reject)=>{http.get({hostname:'127.0.0.1',port,path:'/%2e%2e%5cpackage.json'},res=>{res.resume();resolve(res);}).on('error',reject);});assert.equal(r.statusCode,403);}finally{await new Promise(r=>s.close(r));}});
