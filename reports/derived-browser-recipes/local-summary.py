import hashlib
import json
import pathlib

root = pathlib.Path(__file__).resolve().parents[2]
def read(p):
    return json.loads((root/p).read_bytes())
checks = read('reports/derived-browser-checks/latest.json')
run = pathlib.Path(checks['runDirectory']).name
check = read('reports/derived-browser-checks/'+run+'/verification.json')
assert check['nodePassed'] == 468 and check['nodeSkipped'] == 0
commands = read('reports/derived-browser-raw-checks/latest-local.json')
rawrun = pathlib.Path(commands['runDirectory']).name
results = read('reports/derived-browser-raw-checks/'+rawrun+'/commands.json')
audits = {r['name']: read('reports/derived-browser-verifiers/'+pathlib.Path(r['verificationRun']).name+'/verification.json') for r in results}
new, old = audits['local'], audits['historical']
assert (new['schema'],new['browserReports'],new['numericComparisons'],new['draws'],new['newUploads'],new['cacheDraws']) == (2,6,270940,120,60,60)
assert new['nodeReplay']['queries'] == 6 and old['nodeReplay']['queries'] == 4
assert (old['schema'],old['numericComparisons']) == (1,136460)
for p,h in check['sourceHashes'].items():
    assert hashlib.sha256((root/p).read_bytes()).hexdigest() == h, p
paths = []
for family in ['derived-browser-local','derived-browser-recipes','derived-browser-checks-early']:
    paths += [p for p in (root/'reports'/family).rglob('*') if p.is_file()]
files = [dict(path=str(p.relative_to(root)).replace('\\','/'),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(paths)]
medians = [dict(caseName=r['caseName'],readback=r['readback'],baselineMs=next(row['statistics']['medianMs'] for row in r['summary'] if row['kind']=='baseline' and row['group']=='cpu' and row['stage']=='elapsedMs')) for r in new['records']]
result = dict(status='LOCAL PASS; public verification separate',nodePassed=468,nodeSkipped=0,
              browserQueries=60,browserDraws=120,newUploads=60,cacheDraws=60,numericComparisons=270940,
              separateNodeReplayQueries=6,historicalNumericalComparisons=136460,
              defaultReadback='single',sourceHashes=check['sourceHashes'],sdkAudit=check['sdkAudit'],
              build='7f5b0f537e72cef8',cohort=new['cohort'],medians=medians,files=files,
              unchanged='core/assets/engine/samples/CMakeLists.txt',
              limits='No GPU memory readback, timestamp, display FPS or robot combat acceptance. Sample plan remains unimplemented.')
(root/'reports/derived-browser-local-verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k not in ['files','sourceHashes','sdkAudit','cohort']},indent=2))
