import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {createServer} from '../scripts/serve.mjs';
import {readFile} from 'node:fs/promises';
test('local static host serves modules and blocks hidden/escaped files',async()=>{const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const port=s.address().port;try{const response=await fetch(`http://127.0.0.1:${port}/`);assert.equal(response.status,200);assert.match(await response.text(),/IRON FIELD/);assert.equal(response.headers.get('cross-origin-embedder-policy'),'require-corp');for(const path of ['/.git/config','/%2e%67it/config','/engine/math.mjs']){const r=await fetch(`http://127.0.0.1:${port}${path}`);assert.equal(r.status,path.includes('math')?200:403);}const r=await new Promise((resolve,reject)=>{http.get({hostname:'127.0.0.1',port,path:'/%2e%2e%5cpackage.json'},res=>{res.resume();resolve(res);}).on('error',reject);});assert.equal(r.statusCode,403);}finally{await new Promise(r=>s.close(r));}});

test('explicit local capture keeps full bytes, restricts origin and stays disabled on the normal host',async()=>{
  for(const capture of [false,true]){const s=createServer({capture});await new Promise(r=>s.listen(0,'127.0.0.1',r));const port=s.address().port,url=`http://127.0.0.1:${port}`;
    try{const body=JSON.stringify({schema:1,simulation:{time:1,ticks:[{x:2}]},render:{samples:[{frameMs:50}]}}),options={method:'POST',headers:{Origin:url,'Content-Type':'application/json'},body};
      const response=await fetch(url+'/__capture/float',options);assert.equal(response.status,capture?200:404);
      if(capture){const info=await response.json();assert.equal(info.bytes,Buffer.byteLength(body));assert.equal(await readFile(new URL('../build/browser-capture/'+info.file,import.meta.url),'utf8'),body);
        assert.equal((await fetch(url+'/__capture/float',{...options,headers:{...options.headers,Origin:'https://example.com'}})).status,403);
        assert.equal((await fetch(url+'/__capture/float',{...options,body:'{}'})).status,400);
        assert.equal((await fetch(url+'/__capture/float',{...options,headers:{...options.headers,'Content-Type':'text/plain'}})).status,415);
      }
    }finally{await new Promise(r=>s.close(r));}}
});
