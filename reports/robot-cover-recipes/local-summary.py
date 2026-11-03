import hashlib
import json
import pathlib
import re

root=pathlib.Path(__file__).resolve().parents[2]
def read(p):return json.loads((root/p).read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
latest=read('reports/robot-cover-checks/latest.json')
run=pathlib.Path(latest['runDirectory']).name
checks=read('reports/robot-cover-checks/'+run+'/verification.json')
log=(root/'reports/robot-cover-checks'/run/'node.stdout.txt').read_text(encoding='utf-8')
for needle in ['tests 492','pass 492','fail 0','skipped 0']:assert needle in log
for p,h in checks['sourceHashes'].items():assert sha((root/p).read_bytes())==h,p
source=read('reports/robot-cover-source/robot-cover-source-GzrtcP/report.json')
assert source['status']=='PASS' and source['vertices']==6 and source['faces']==4 and source['bytes']==288
assert source['sourceUnchanged'] and not source['authoredShapeChangedFromPlan']
assert source['sdkBefore']==source['sdkAfter'] and source['nativeCLI']['commands']==6
assert sha((root/'assets/robot-back-cover.skin.json').read_bytes())==source['sourceSHA256']
assert sha((root/'assets/robot-back-cover.scene.json').read_bytes())==source['sceneSHA256']
browser=read('reports/robot-cover-browser-verification.json')
assert browser['status']=='PASS' and browser['uiKills']==2 and browser['resourceMeshes']==3
assert sha((root/'docs/learn/diagrams/robot-back-cover.svg').read_bytes())=='93660a7c709b1da8b30f1503c7573b5adb2c2497b7208ef0db88a61de90c5096'
names=['docs/ROBOT_BACK_COVER.md','docs/learn/index.html','docs/learn/diagrams/robot-back-cover.svg',
       'docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md']
sourceHashes={**checks['sourceHashes'],**{p:sha((root/p).read_bytes()) for p in names}}
paths=[]
for family in ['robot-cover-local','robot-cover-local-final','robot-cover-local-verified','robot-cover-local-release','robot-cover-recipes']:
    paths += [p for p in (root/'reports'/family).rglob('*') if p.is_file()]
paths += [root/'reports/robot-cover-browser-verification.json']
files=[dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(paths)]
record=dict(status='LOCAL PASS; public CI/Pages and interaction verification separate',nodePassed=492,nodeSkipped=0,
            sourceTestGroups=7,controllerTestGroups=11,derivedRendererTestGroups=24,build='b576823ff1731dba',modules=45,
            sourceVertices=6,sourceFaces=4,sourceBones=2,sourceSampledClipParameters=33,finiteSourceMeasurements=15,
            nativeSourceCLICommands=6,browserUIKills=2,sourceHashes=sourceHashes,sdkAudit=checks['sdkAudit'],files=files,
            continuousParameterQualityProven=False,strictHingeDynamicsImplemented=False,actualGPUReadback=False,
            actualHiddenBrowserPathRetested=False,scope='Original decorative mechanism through actual C++ FK/LBS/derived; physics/gameplay unchanged apart from observational drive metadata. Prior pilot builds and intermediate logs retained separately.')
(root/'reports/robot-cover-local-verification.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in record.items() if k not in ['files','sourceHashes','sdkAudit']},indent=2))
