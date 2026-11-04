"""Accept captured final commands, preserved sources and complete proof data."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from collections import Counter
import json
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-entry'
def read(p):return json.loads((root/p).read_text(encoding='utf-8-sig'))
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=read(f'reports/{prefix}-baseline.json')
assert len(base['protected'])==276
for path,value in base['protected'].items():assert digest((root/path).read_bytes())==value,path
directory=f'reports/{prefix}-checks/run-20261104-final';commands=[]
for phase in ['build','native','reference','regressions','exchange','recheck']:
    rows=read(f'{directory}/{phase}-commands.json')
    assert rows and all(row['exit']==0 and row['authoredStable'] for row in rows)
    for row in rows:
        for p,v in row['authoredAfter'].items():assert digest((root/p).read_bytes())==v,p
        for stream in ['stdout','stderr']:assert digest((root/row[stream]).read_bytes())==row[stream+'Hash']
    commands+=rows
def output(name):return (root/next(row['stdout'] for row in commands if row['name']==name)).read_text(encoding='utf-8')
assert 'PASS 76 groups; 65 complete-input finite entry fixtures' in output('entry')
assert '100% tests passed, 0 tests failed out of 37' in output('ctest')
for name,count in [('node',586),('learn',12)]:
    for marker in [f'ℹ tests {count}',f'ℹ pass {count}','ℹ fail 0','ℹ skipped 0']:assert marker in output(name),marker
assert 'warning ' not in output('build').lower()
fixtures=read(f'{directory}/native-fixtures.json')['fixtures']
assert len(fixtures)==65
counts=dict(Counter(f['result']['status'] for f in fixtures))
assert counts=={'separated':18,'entry_window':8,'not_certified':20,'initial_penetration':2,'invalid_input':17},counts
reference=json.loads(output('reference'));negative=json.loads(output('negative-controls'))
assert reference['status']=='PASS' and reference['certifiedLeaves']==558 and reference['cellAudits']==1452
assert reference['lastMeshReferenceComponents']==3840 and reference['entryWidthReferences']==8
assert negative=={'status':'PASS','fixtures':65,'selfTestGroups':17,'rejectedControls':90,'labelAndOrderIndependent':True}
full=read(f'{directory}/negative-controls/negative-controls.json')
assert len(full['rejectedControls'])==90 and all(x['rejected'] for x in full['rejectedControls'])
owned=read(f'{directory}/owned-sdk/report.json')
assert owned['status']=='PASS' and (owned['actualModelFixtures'],owned['hostRejected'],owned['modelNumericComparisons'],owned['originalInputNumericComparisons'])==(59,3,50663,3877)
assert owned['negativeControls']['rejectedControls']==71
manifest=read('assets/pikapika-simulation.build.json')
assert len(manifest['sourceSha256'])==59 and len(manifest['licenses'])==7
windows=[{'name':f['name'],'parameter':f['result']['window']['parameter'],'width':f['result']['window']['width'],'audits':len(f['result']['audits'])} for f in fixtures if f['result']['window']]
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],
 'nativeGroups':76,'fixtures':65,'statuses':counts,'ctest':37,'nodeTests':586,'learnTests':12,'skipped':0,
 'windows':windows,'reference':reference,'negativeControls':negative,'protectedFilesUnchanged':276,
 'exports':80,'sourceHeaders':59,'licenseNoticesUnchanged':7,'webBuild':'d70b5d9b4436650f','modules':49,'entries':24,
 'artifacts':{p:digest((root/p).read_bytes()) for p in ['assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json']},
 'ownedSdkRegression':owned,'commands':commands,
 'fixtureBytes':digest((root/f'{directory}/native-fixtures.json').read_bytes()),
 'fixtureMatchesFirstRun':(root/f'{directory}/native-fixtures.json').read_bytes()==(root/f'reports/{prefix}-checks/run-20261104-root/native-fixtures.json').read_bytes(),
 'attempts':'First MSVC build/76 groups and first independent65 reference passed. Independent negative-test source initially had an extra parenthesis; failed syntax attempt retained under reference-development/syntax-initial and corrected before first negative run. All original streams retained. No model/fixture values adjusted.',
 'scope':'Native-only defined linear sphere path versus static thin triangles. Initial strict sign, closed safe prefix, E-corrected negative witness and outward width prove an entry window; no unique root, exact physical time, active face, manifold or response. Existing SDK/game unchanged; no new browser entry execution. Deliberate allocation/unknown-work injection, natural parameter_resolution and Windows sanitizer not verified. Public GNU CI/sanitizer and Pages bytes are separate acceptance.'}
assert report['fixtureMatchesFirstRun']
(root/f'reports/{prefix}-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','nativeGroups','fixtures','ctest','nodeTests','protectedFilesUnchanged']}))
