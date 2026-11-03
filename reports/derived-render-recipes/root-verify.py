import pathlib,json,hashlib,subprocess,tempfile,time,re,sys
r=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(tempfile.mkdtemp(prefix='proof-',dir=r/'build/derived-render-root'));commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
sourceNames=['engine/derived-render.mjs','engine/renderer.mjs','tools/skin-binding-lab.mjs','tests/derived-renderer.test.mjs','tests/skin-binding-lab.test.mjs']
before={p:sha((r/p).read_bytes()) for p in sourceNames}
for name,args in [('node',['npm.cmd','test']),('syntax',['npm.cmd','run','check']),('web',['npm.cmd','run','build'])]:
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
preserved=[]
for path in subprocess.check_output(['git','ls-files','samples','assets','core','CMakeLists.txt'],cwd=r,text=True).splitlines():
    b=(r/path).read_bytes();prior=subprocess.check_output(['git','show','HEAD:'+path],cwd=r)
    if not path.startswith('core/'):assert b==prior,path
    preserved.append(dict(path=path,bytes=len(b),sha256=sha(b),gitBlobSha256=sha(prior),workingTreeBytesEqualGitBlob=b==prior))
subprocess.run(['git','diff','--quiet','HEAD','--','core','CMakeLists.txt'],cwd=r,check=True)
after={p:sha((r/p).read_bytes()) for p in sourceNames}
assert before==after,'Source changed during verification'
text=(out/'node.stdout.txt').read_text(encoding='utf-8');passed=re.findall(r'(?:# |\u2139 )pass (\d+)',text);skips=re.findall(r'(?:# |\u2139 )skipped (\d+)',text)
summary=dict(status='LOCAL PASS; real browser and public validation separate',commands=commands,nodePassed=int(passed[-1]),nodeSkipped=int(skips[-1]),sourceHashes=after,sdkAudit=audit,preserved=preserved,web=(out/'web.stdout.txt').read_text(encoding='utf-8'))
(out/'verification.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
(r/'build/derived-render-root/latest.json').write_bytes((json.dumps(dict(runDirectory=str(out)),indent=2)+'\n').encode())
print(json.dumps({'passed':summary['nodePassed'],'skip':summary['nodeSkipped'],'preserved':len(preserved),'run':str(out)},indent=2),flush=True)
