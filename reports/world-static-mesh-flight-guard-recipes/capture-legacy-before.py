"""Capture existing Native/SDK results before any future core binding change."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,time,sys
ROOT=Path(__file__).resolve().parents[2]
base=json.loads((ROOT/'reports/world-static-mesh-flight-guard-development/before-implementation.json').read_text(encoding='utf8'))
out=(ROOT/sys.argv[1]).resolve()
assert out.is_relative_to((ROOT/'reports/world-static-mesh-flight-guard-development').resolve())
out.mkdir(parents=True,exist_ok=False)
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def protected():
 for group in ['protected','generatedEntries','integrations']:
  for path,stamp in base[group].items():assert info((ROOT/path).read_bytes())==stamp,path
 assert json.loads((ROOT/'assets/pikapika-simulation.build.json').read_text(encoding='utf8'))==base['sdkManifest']
protected();rows=[]
def run(name,args,timeout=180):
 protected();start=time.perf_counter();now=datetime.now(timezone.utc).isoformat()
 try:
  process=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout)
  code,stdout,stderr,timedout=process.returncode,process.stdout,process.stderr,False
 except subprocess.TimeoutExpired as e:code,stdout,stderr,timedout=None,e.stdout or b'',e.stderr or b'',True
 row={'name':name,'args':args,'started':now,'wallSeconds':time.perf_counter()-start,'exit':code,'timedOut':timedout}
 for stream,raw in [('stdout',stdout),('stderr',stderr)]:
  p=out/(name+'.'+stream+'.txt');p.write_bytes(raw);row[stream]=p.relative_to(ROOT).as_posix();row[stream+'Hash']=info(raw)
 protected();row['protectedUnchanged']=True;rows.append(row)
 (out/'commands.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
 assert code==0 and not timedout,name
 return stdout
binaries={}
for name,file in [('legacy','pikapika-free-flight-legacy-probe.exe'),('simulation','pikapika-simulation-probe.exe'),('supported','pikapika-supported-probe.exe')]:
 path=ROOT/'build/native/Release'/file;binaries[path.relative_to(ROOT).as_posix()]=info(path.read_bytes())
 payload=run(name,[str(path)]+(['--fixtures'] if name=='supported' else []));json.loads(payload)
 (out/(name+'.json')).write_bytes(payload)
legacy=str((out/'legacy.json').relative_to(ROOT))
run('legacy-wasm',['node','scripts/verify-free-flight-legacy.mjs',legacy,str((out/'legacy-wasm').relative_to(ROOT))])
for path,stamp in binaries.items():assert info((ROOT/path).read_bytes())==stamp,path
record={'schema':1,'status':'PASS','baseCommit':base['baseCommit'],'scope':'Historical before-core-binding capture while Sphere public acceptance is pending. Existing Native full World/W1 reports/state and same-backend SDK fields; no new guard or source-enforced binding acceptance.',
 'binaries':binaries,'protectedRaw':383,'generatedEntries':26,'integrations':3,'sdkManifestUnchanged':True,
 'commands':rows,'allProtectedUnchanged':True,'artifacts':{p.relative_to(ROOT).as_posix():info(p.read_bytes()) for p in out.rglob('*') if p.is_file()}}
(out/'capture.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','commands':len(rows),'protected':383,'scope':'before-core-binding only'}))
