import datetime,hashlib,json,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parents[2]
paths=['index.html','tools/skinning-lab.html','tools/skinning-lab.mjs','engine/simulation.mjs',
 'assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json','docs/learn/index.html']
proof=dict(schema=1,observedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 codeCommit='331b6cc0f92ce9cd65c8033ae8cd1f5b017f7237',files=[])
for path in paths:
    url='https://tatata93.github.io/pikapikaengine/'+path+'?v=331b6cc'
    with urllib.request.urlopen(url,timeout=45) as response:
        data=response.read();headers=dict(response.headers);status=response.status
    local=(root/path).read_bytes()
    same=data==local
    proof['files'].append(dict(path=path,url=url,status=status,bytes=len(data),
      sha256=hashlib.sha256(data).hexdigest(),expectedSHA256=hashlib.sha256(local).hexdigest(),
      byteEqual=same,headers=headers))
    print(path,status,len(data),same,flush=True)
proof['status']='PASS' if all(f['byteEqual'] and f['status']==200 for f in proof['files']) else 'FAIL'
(root/'reports/skinning-sort-public-http.json').write_text(json.dumps(proof,indent=2)+'\n','utf-8',newline='\n')
assert proof['status']=='PASS'
