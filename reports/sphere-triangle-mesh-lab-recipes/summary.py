from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess,re
root=Path(__file__).resolve().parents[2]
out=root/'reports/sphere-triangle-mesh-lab-checks/run-20261104-root'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):
 b=path.read_bytes();return {'bytes':len(b),'sha256':sha256(b).hexdigest()}
commands=sum([read(out/(phase+'-commands.json')) for phase in ['native','validate']],[])
assert all(c['exit']==0 for c in commands)
for c in commands:
 assert digest(root/c['stdout'])==c['stdoutHash'] and digest(root/c['stderr'])==c['stderrHash']
assert '100% tests passed, 0 tests failed out of 34' in (out/'ctest.stdout.txt').read_text()
node=(out/'node.stdout.txt').read_text(encoding='utf8');assert all(x in node for x in ['tests 544','pass 544','fail 0','skipped 0'])
build=(out/'web-build.stdout.txt').read_text();assert '457dd1cda43de02c: 47 versioned modules' in build
protected=['core','engine','assets','samples','third_party']
assert not subprocess.check_output(['git','diff','--name-only','HEAD','--',*protected],cwd=root).strip()
assert not subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*protected],cwd=root).strip()
m=read(root/'assets/pikapika-simulation.build.json')
assert len(m['sourceSha256'])==57 and len(m['licenses'])==7
files={}
for p,h in {**m['sourceSha256'],**m['licenses']}.items():
 actual=digest(root/p);assert actual['sha256']==h,p;files[p]=actual
for p,expected in m['artifacts'].items():assert digest(root/p)==expected,p
baseline=read(root/'reports/sphere-triangle-mesh-sdk-baseline.json')
for p,expected in baseline['assetsAndSampleSourceBeforeBuild'].items():
 if p not in ['assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json']:assert digest(root/p)==expected,p
exports=json.loads(next(f.split('=',1)[1] for f in m['flags'] if f.startswith('-sEXPORTED_FUNCTIONS=')));assert len(set(exports))==len(exports)==74
sdk=read(out/'sdk/report.json');assert (sdk['packetNumericComparisons'],sdk['modelNumericComparisons'],sdk['negativeZeroComparisons'])==(27160,20808,4453)
assert sdk['reference']['primitiveReference']['referenceComponents']+sdk['reference']['aggregateReferenceComponents']==2775
assert len(read(out/'sdk/negative-controls/negative-controls.json')['rejectedControls'])==43
old=read(out/'single-sdk/report.json');assert (old['packetNumericComparisons'],old['modelNumericComparisons'])==(22327,13432)
browser=read(root/'reports/sphere-triangle-mesh-lab-local-browser-verification.json');assert browser['status']=='PASS' and browser['numericBits']==42644
rational=read(root/'reports/sphere-triangle-mesh-lab-local-rational-verification.json');assert rational['browserAdditionalComponents']==4578
entries=[]
for p in [root/'index.html',*sorted((root/'tools').glob('*.html')),*sorted((root/'docs/learn').glob('*.html'))]:
 s=p.read_text(encoding='utf8')
 if 'id="engine-imports"' in s:
  assert s.count('id="engine-imports"')==1 and '?build=457dd1cda43de02c' in s;entries.append(p.relative_to(root).as_posix())
assert len(entries)==23
report={'schema':1,'status':'PASS','generated':datetime.now(timezone.utc).isoformat(),'baseCommit':'4c0432a','commands':commands,'node':544,'dedicatedTests':18,'ctest':34,'ctestScope':'Existing unchanged Release binaries executed; no new C++ build or local sanitizer claimed in UI stage.','webBuild':'457dd1cda43de02c','webModules':47,'webEntries':entries,'exports':74,'sourceHeaders':57,'licenses':7,'protectedFiles':files,'artifacts':m['artifacts'],'sdk':sdk,'oldSingle':old,'browser':browser,'rational':rational,'cppSdkAssetsGameUnchanged':True,'publicCiPages':'NOT_YET_VERIFIED','scope':'Manual instantaneous mesh query inspector; no World/CCD/manifold/contact response or game integration.'}
(root/'reports/sphere-triangle-mesh-lab-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:report[k] for k in ['status','node','dedicatedTests','ctest','webBuild','exports','sourceHeaders','cppSdkAssetsGameUnchanged']}))
