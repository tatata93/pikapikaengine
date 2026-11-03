import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time

root=pathlib.Path(__file__).resolve().parents[2]
base=root/'build/robot-cover-checks'
base.mkdir(exist_ok=True)
out=pathlib.Path(tempfile.mkdtemp(prefix='run-',dir=base))
commands=[]
for name,args,timeout in [('web',['npm.cmd' if sys.platform=='win32' else 'npm','run','build'],120),
                          ('node',['npm.cmd' if sys.platform=='win32' else 'npm','test'],240),
                          ('syntax',['npm.cmd' if sys.platform=='win32' else 'npm','run','check'],180)]:
    start=time.time()
    try:
        result=subprocess.run(args,cwd=root,capture_output=True,timeout=timeout)
        code,stdout,stderr=result.returncode,result.stdout,result.stderr
    except subprocess.TimeoutExpired as error:
        code,stdout,stderr=124,error.stdout or b'',error.stderr or b''
    (out/(name+'.stdout.txt')).write_bytes(stdout)
    (out/(name+'.stderr.txt')).write_bytes(stderr)
    commands.append(dict(name=name,args=args,exitCode=code,elapsedSeconds=time.time()-start))
    (out/'commands.json').write_bytes((json.dumps(commands,indent=2)+'\n').encode())
    print(name,code,flush=True)
    if code:
        print(stdout.decode('utf-8',errors='replace')[-6500:])
        print(stderr.decode('utf-8',errors='replace')[-3000:])
        raise RuntimeError(name+' failed')
manifest=json.loads((root/'assets/pikapika-simulation.build.json').read_bytes())
sdkAudit=[]
for family in ['sourceSha256','licenses','artifacts']:
    for p,h in manifest[family].items():
        expected=h['sha256'] if isinstance(h,dict) else h
        data=(root/p).read_bytes()
        assert hashlib.sha256(data).hexdigest()==expected,p
        sdkAudit.append(dict(path=p,bytes=len(data),sha256=expected))
names=['samples/back-cover.mjs','samples/app.mjs','samples/robot.mjs','engine/renderer.mjs',
       'tests/robot-back-cover.test.mjs','tests/robot-back-cover-source.test.mjs','tests/derived-renderer.test.mjs',
       'scripts/create-robot-back-cover.mjs','assets/robot-back-cover.skin.json','assets/robot-back-cover.scene.json','index.html']
sourceHashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in names}
record=dict(status='PASS',commands=commands,sourceHashes=sourceHashes,sdkAudit=sdkAudit,runDirectory=str(out))
(out/'verification.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
(base/'latest.json').write_bytes((json.dumps(dict(runDirectory=str(out)),indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',runDirectory=str(out))),flush=True)
