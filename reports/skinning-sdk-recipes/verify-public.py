import datetime,hashlib,json,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parents[2]
paths=['tools/skinning-lab.html','tools/skinning-lab.mjs','engine/simulation.mjs',
 'assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json','docs/learn/index.html']
proof=dict(schema=1,observedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 codeCommit='051c2a9e1cc8a6c681725af21a3ba2b41e524bb8',files=[])
for path in paths:
    url='https://tatata93.github.io/pikapikaengine/'+path+'?v=051c2a9'
    with urllib.request.urlopen(url,timeout=45) as response:
        data=response.read();headers=dict(response.headers);status=response.status
    local=(root/path).read_bytes()
    same=data==local
    proof['files'].append(dict(path=path,url=url,status=status,bytes=len(data),
      sha256=hashlib.sha256(data).hexdigest(),expectedSHA256=hashlib.sha256(local).hexdigest(),
      byteEqual=same,headers=headers))
    print(path,status,len(data),same,flush=True)
proof['status']='PASS' if all(f['byteEqual'] and f['status']==200 for f in proof['files']) else 'FAIL'
(root/'reports/skinning-sdk-public-http.json').write_text(json.dumps(proof,indent=2)+'\n','utf-8',newline='\n')
assert proof['status']=='PASS'
