import pathlib,json,hashlib,subprocess,tempfile,time,re,sys
r=pathlib.Path(__file__).resolve().parents[2]
base=r/'build/derived-gpu-root-check';base.mkdir(exist_ok=True)
out=pathlib.Path(tempfile.mkdtemp(prefix='proof-',dir=base));commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
sourceNames=['tools/derived-gpu-profile.mjs','tools/derived-gpu-cases.mjs','tools/derived-gpu-lab.mjs','tools/derived-gpu-lab.html','tests/derived-gpu-profile.test.mjs','tests/derived-gpu-cases.test.mjs','tests/derived-gpu-lab.test.mjs','scripts/build-web.mjs','docs/learn/diagrams/derived-gpu-profile.svg']
before={p:sha((r/p).read_bytes()) for p in sourceNames}
for name,args in [('node',['npm.cmd' if sys.platform=='win32' else 'npm','test']),('syntax',['npm.cmd' if sys.platform=='win32' else 'npm','run','check']),('web',['npm.cmd' if sys.platform=='win32' else 'npm','run','build'])]:
    t=time.time();p=subprocess.run(args,cwd=r,capture_output=True);files=[]
    for kind,data in [('stdout',p.stdout),('stderr',p.stderr)]:
        f=out/f'{name}.{kind}.txt';f.write_bytes(data);files.append(dict(path=str(f.relative_to(r)),bytes=len(data),sha256=sha(data)))
    commands.append(dict(name=name,args=args,exitCode=p.returncode,seconds=time.time()-t,files=files))
    (out/'commands.json').write_bytes((json.dumps(commands,indent=2)+'\n').encode())
    print(name,p.returncode,flush=True)
    if p.returncode:print(p.stdout.decode('utf-8',errors='replace')[-4500:]);print(p.stderr.decode('utf-8',errors='replace'));sys.exit(p.returncode)
m=json.loads((r/'assets/pikapika-simulation.build.json').read_text());audit=[]
for items in [m['sourceSha256'],m['licenses'],m['artifacts']]:
    for path,expected in items.items():
        expected=expected['sha256'] if isinstance(expected,dict) else expected;b=(r/path).read_bytes()
        assert sha(b)==expected,path;audit.append(dict(path=path,bytes=len(b),sha256=sha(b)))
subprocess.run(['git','diff','--quiet','HEAD','--','core','assets','engine','samples','CMakeLists.txt'],cwd=r,check=True)
after={p:sha((r/p).read_bytes()) for p in sourceNames}
# Web generation intentionally changes only the generated import map/entry URL
# in the new HTML. Its final hash is retained alongside the initial source.
assert {p:h for p,h in before.items() if not p.endswith('.html')}=={p:h for p,h in after.items() if not p.endswith('.html')},'Source changed during verification'
text=(out/'node.stdout.txt').read_text(encoding='utf-8');passed=re.findall(r'(?:# |\u2139 )pass (\d+)',text);skips=re.findall(r'(?:# |\u2139 )skipped (\d+)',text)
summary=dict(status='LOCAL PASS; real-browser/public observations separate',commands=commands,nodePassed=int(passed[-1]),nodeSkipped=int(skips[-1]),sourceHashes=after,preBuildSourceHashes=before,sdkAudit=audit,productionGitDiff='none: core/assets/engine/samples/CMakeLists.txt',web=(out/'web.stdout.txt').read_text(encoding='utf-8'))
(out/'verification.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
(base/'latest.json').write_bytes((json.dumps(dict(runDirectory=str(out)),indent=2)+'\n').encode())
print(json.dumps({'passed':summary['nodePassed'],'skip':summary['nodeSkipped'],'run':str(out)},indent=2),flush=True)
