import pathlib,subprocess,json,hashlib,urllib.request,sys,datetime
r=pathlib.Path(__file__).resolve().parents[2];revision=sys.argv[1]
assert len(revision)==40 and all(c in '0123456789abcdef' for c in revision)
names=['index.html','docs/learn/index.html','docs/learn/diagrams/derived-gpu-profile.svg','docs/DERIVED_MESH_GPU_PROFILE.md','tools/derived-gpu-lab.html','tools/derived-gpu-lab.mjs','tools/derived-gpu-profile.mjs','tools/derived-gpu-cases.mjs','tools/derived-profile.mjs','engine/simulation.mjs','engine/renderer.mjs','engine/derived-render.mjs','assets/pikapika-simulation.build.json']
manifest=json.loads(subprocess.check_output(['git','show',revision+':assets/pikapika-simulation.build.json'],cwd=r));names+=list(manifest['artifacts']);rows=[]
for p in names:
    expected=subprocess.check_output(['git','show',revision+':'+p],cwd=r)
    url='https://tatata93.github.io/pikapikaengine/'+p+'?v='+revision[:7]
    with urllib.request.urlopen(url,timeout=45) as response:
        actual=response.read();assert actual==expected,p
        rows.append(dict(path=p,url=url,status=response.status,bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest(),contentType=response.headers.get('Content-Type'),etag=response.headers.get('ETag')))
out=dict(status='PASS',revision=revision,checkedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference='Exact commit blob bytes, not Windows working-tree newline representation',files=rows)
(r/'reports/derived-gpu-http.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(rows),bytes=sum(x['bytes'] for x in rows))))
