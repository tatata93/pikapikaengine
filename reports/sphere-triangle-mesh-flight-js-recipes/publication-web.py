"""Rebuild the exact published feature without mixing the next unpublished lab."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess,tarfile,time,shutil
root=Path(__file__).resolve().parents[2];feature='8035f931ada107af7a83fe6599d4a55bb1784cec'
out=root/'build/flight-js-publication-web-20261104';out.mkdir(parents=True,exist_ok=False)
archive=out/'source.tar';source=out/'source';source.mkdir()
args=['git','archive','--format=tar','--output='+str(archive),feature,'engine','assets','samples','tools','docs/learn','scripts/build-web.mjs','style.css','index.html']
subprocess.run(args,cwd=root,check=True)
with tarfile.open(archive) as tar:tar.extractall(source,filter='data')
started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter();command=[shutil.which('node'),'scripts/build-web.mjs'];process=subprocess.run(command,cwd=source,capture_output=True,timeout=60)
report={'schema':1,'commit':feature,'started':started,'command':command,'cwd':source.relative_to(root).as_posix(),'exit':process.returncode,'wallSeconds':time.perf_counter()-clock,'scope':'Exact tracked feature exported locally; next unpublished lab files are excluded. No live working tree sources/artifacts are overwritten.'}
def info(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
for name in ['stdout','stderr']:
 data=getattr(process,name);target=root/f'reports/sphere-triangle-mesh-flight-js-publication-web.{name}.txt';target.write_bytes(data);report[name]=target.relative_to(root).as_posix();report[name+'Hash']=info(data)
assert process.returncode==0 and b'836a4c2102a528cd: 52 versioned modules' in process.stdout
base=json.loads((root/'reports/sphere-triangle-mesh-flight-js-baseline.json').read_text());files={}
for path in base['generatedEntries']:
 expected=subprocess.check_output(['git','show',feature+':'+path],cwd=root);actual=(source/path).read_bytes();assert actual==expected,path;files[path]=info(actual)
assert len(files)==25;report.update(status='PASS',generatedEntries=files,webBuild='836a4c2102a528cd',modules=52)
(root/'reports/sphere-triangle-mesh-flight-js-publication-web.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':report['status'],'generated':len(files),'build':report['webBuild'],'exit':process.returncode}))
