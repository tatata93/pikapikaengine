import json, pathlib, subprocess, sys, hashlib, tempfile, time
root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(tempfile.mkdtemp(prefix='proof-',dir=root/'build/derived-mesh-sdk-root'))
commands=[]
def run(name,args):
    started=time.time()
    p=subprocess.run(args,cwd=root,capture_output=True)
    paths=[]
    for tag,data in [('stdout',p.stdout),('stderr',p.stderr)]:
        f=out/f'{name}.{tag}.txt'; f.write_bytes(data)
        paths.append(dict(path=str(f.relative_to(root)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    commands.append(dict(name=name,argv=args,exitCode=p.returncode,seconds=time.time()-started,outputs=paths))
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
    print(name,p.returncode,flush=True)
    if p.returncode: print(p.stderr.decode('utf-8',errors='replace'));sys.exit(p.returncode)
fixtures=json.loads((root/'build/derived-mesh-sdk-root/latest.json').read_text())['runDirectory']
native=str(pathlib.Path(fixtures)/'native-fixtures.json')
probe=str(pathlib.Path(fixtures)/'probe-fixtures.json')
run('derived-replay',['node','scripts/verify-derived-mesh-wasm.mjs',native,str(out/'replay-report.json'),str(out/'replay-outputs.json'),str(out/'wasm40.json'),probe])
run('wasm-controls',['python','-X','utf8','tests/derived_mesh_reference_tests.py',str(out/'wasm40.json'),'--backend','main-wasm','--output','build/derived-mesh-reference-sdk-root'])
run('motion-replay',['node','scripts/verify-motion-wasm.mjs','reports/motion-native-fixtures.json',str(out/'motion-report.json'),str(out/'motion-outputs.json'),'reports/motion-native-oracle.csv'])
run('skin-replay',['node','scripts/verify-skinning-wasm.mjs','reports/skinning-sort-core-native-fixtures.stdout.bin.txt','reports/skinning-sort-core-native-oracle.csv',str(out/'skin-report.json'),str(out/'skin-outputs.json'),str(out/'skin-replay.json'),str(out/'skin-replay-oracle.csv')])
run('syntax',['npm.cmd','run','check'])
(root/'build/derived-mesh-sdk-root/proof-latest.json').write_text(json.dumps({'runDirectory':str(out)},indent=2)+'\n',encoding='utf-8')
print(out,flush=True)
