"""Audit stable local Native-only held-load evidence, never infer public CI success."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, re

if not __debug__:
    raise SystemExit('Run without Python -O')
root=Path(__file__).resolve().parents[2]
prefix='sphere-triangle-mesh-held-load'
final=f'reports/{prefix}-checks/run-20261104-final'
def read(path): return json.loads((root/path).read_text(encoding='utf-8-sig'))
def digest(path):
    data=(root/path).read_bytes()
    return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=read(f'reports/{prefix}-baseline.json')
assert base['baseCommit']=='b58f2d861fdbb8da18f064751fc4f6af6ac5f409'
assert len(base['protected'])==345
for path,expected in base['protected'].items(): assert digest(path)==expected,path
commands=[]
for phase in ['build','native','reference','regressions','old-exchange']:
    rows=read(f'{final}/{phase}-commands.json')
    assert rows,phase
    for row in rows:
        assert row['exit']==0 and row['authoredStable'] and row['authoredBefore']==row['authoredAfter'],row['name']
        for path,expected in row['authoredAfter'].items(): assert digest(path)==expected,path
        for stream in ['stdout','stderr']: assert digest(row[stream])==row[stream+'Hash'],row['name']
    commands+=rows
def output(name):
    rows=[r for r in commands if r['name']==name]
    assert len(rows)==1,name
    return (root/rows[0]['stdout']).read_text(encoding='utf-8-sig')
for label,count in [('tests',631),('pass',631),('fail',0),('skipped',0)]:
    assert re.search(r'(?:ℹ\s+|#\s+)'+label+r'\s+'+str(count)+r'(?:\s|$)',output('node')),(label,count)
assert '100% tests passed, 0 tests failed out of 39' in output('ctest')
assert 'PASS 92 groups; 79 complete-input finite held-load fixtures' in output('native-tests')
assert (root/f'{final}/native-fixtures.json').read_bytes()==(root/f'{final}/native-fixtures.stdout.txt').read_bytes()
owned=read(f'{final}/old-entry-owned/report.json')
assert owned['status']=='PASS'
assert (owned['fixtureCount'],owned['actualModelFixtures'],owned['hostRejected'])==(65,62,3)
assert (owned['modelNumericComparisons'],owned['modelNegativeZeroComparisons'],owned['originalInputNumericComparisons'],owned['originalInputNegativeZeroComparisons'])==(105056,3239,4728,108)
assert owned['negativeControls']=={'status':'PASS','fixtures':65,'selfTestGroups':17,'rejectedControls':90,'labelAndOrderIndependent':True}
for path,expected in owned['files'].items(): assert digest(f'{final}/old-entry-owned/{path}')==expected,path
for relative,expected in owned['dependencies'].items():
    p=(root/'scripts'/relative).resolve()
    assert p.is_relative_to(root) and digest(p)==expected,p
assert owned['wasm']==digest('assets/pikapika-simulation.wasm')
source={p:digest(p) for row in commands for p in row['authoredAfter']}
for p in ['docs/SPHERE_TRIANGLE_MESH_HELD_LOAD.md','docs/learn/diagrams/sphere-triangle-mesh-held-load.svg']:
    source[p]=digest(p)
corpus=read(f'{final}/native-fixtures.json')
assert corpus['schema']==1 and corpus['kind']=='sphere-triangle-mesh-held-load-fixtures'
states={}
for fixture in corpus['fixtures']:
    state=fixture['result']['status'];states[state]=states.get(state,0)+1
assert states.get('entry_window',0)>=4 and states.get('separated',0)>=2
assert len(corpus['fixtures'])==79 and states=={'separated':8,'entry_window':13,'not_certified':23,'initial_penetration':2,'invalid_input':33}
reference=read(f'{final}/reference/reference.json')
controls=read(f'{final}/reference/negative-controls.json')
assert json.loads(output('fraction'))==reference==controls['baseline']
assert reference['status']=='PASS' and reference['inputFingerprint']=='3a7679cff9aa2cebf0b162bdb920821d16b272fe645cec5ccc9849f0025dc85e'
assert (reference['fixtures'],reference['cellAudits'],reference['certifiedLeaves'],reference['positiveIslandsBeyondPrefix'],reference['lastMeshReferenceComponents'])==(79,2028,748,37,2268)
assert controls['status']=='PASS' and controls['selfTestGroups']==16 and controls['labelAndOrderIndependent'] is True
assert len(controls['rejectedControls'])==63 and all(c['rejected'] is True for c in controls['rejectedControls'])
assert len({c['name'] for c in controls['rejectedControls']})==63
assert read(f'{final}/reference/optimized-command.json')['exitCode']==1
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),
        'baseCommit':base['baseCommit'],'protectedFilesUnchanged':len(base['protected']),
        'nativeTestsOutput':output('native-tests').strip(),'node':631,'skipped':0,'ctest':39,
        'fixtures':len(corpus['fixtures']),'statuses':states,'fractionOutput':output('fraction').strip(),
        'referenceOutput':output('reference').strip(),'sources':source,'commands':commands,
        'reference':reference,'negativeControls':controls,
        'fixtureFile':digest(f'{final}/native-fixtures.json'),'oldEntryOwned':owned,
        'diagramEvidence':digest(f'reports/{prefix}-browser/diagram.png'),
        'scope':'Native-only read-only held-load sphere versus static finite triangle mesh. Independent exact Fraction certificate and analytic controls; no World propagation/response or SDK exports changed. Linux strict warnings/sanitizers/public CI remain separate, unverified until their actual jobs succeed.'}
(root/f'reports/{prefix}-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','protectedFilesUnchanged','node','ctest','fixtures','statuses']}))
