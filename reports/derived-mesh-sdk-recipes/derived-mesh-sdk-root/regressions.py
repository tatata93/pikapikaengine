import json,pathlib,subprocess,sys,tempfile,time,hashlib
root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(tempfile.mkdtemp(prefix='regressions-',dir=root/'build/derived-mesh-sdk-root'))
old=json.loads((root/'reports/skinning-sort-root-regressions.json').read_text())
commands=[]
for i,c in enumerate(old['commands']):
    if c['label']=='motion shared WASM bit replay':continue # Already recorded in root replay proof.
    args=[str(out/a.removeprefix('build/skinning-sort-root/regressions/')) if a.startswith('build/skinning-sort-root/regressions/') else a for a in c['command']]
    if args[0].lower().endswith('python.exe'):args[:1]=['python','-X','utf8']
    p=subprocess.run(args,cwd=root,capture_output=True)
    files=[]
    for tag,data in [('stdout',p.stdout),('stderr',p.stderr)]:
        f=out/f'{i:02d}.{tag}.txt';f.write_bytes(data);files.append({'path':str(f.relative_to(root)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    if c['label']=='strict support final Native fixtures':(out/'regression-support-native-fixtures.json').write_bytes(p.stdout)
    commands.append({'label':c['label'],'command':args,'exitCode':p.returncode,'files':files})
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
    print(c['label'],p.returncode,flush=True)
    if p.returncode:print(p.stderr.decode('utf-8',errors='replace'));sys.exit(p.returncode)
(root/'build/derived-mesh-sdk-root/regression-latest.json').write_text(json.dumps({'runDirectory':str(out)},indent=2)+'\n',encoding='utf-8')
print(out)
