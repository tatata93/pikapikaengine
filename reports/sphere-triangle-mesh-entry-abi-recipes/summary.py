"""Verify local raw ABI/WASM evidence and retain the original failed test."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,re
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-entry-abi'
def read(p):return json.loads((root/p).read_text(encoding='utf-8-sig'))
def digest(data):return {'bytes':len(data),'sha256':sha256(data).hexdigest()}
base=read(f'reports/{prefix}-baseline.json');artifacts=read(f'reports/{prefix}-artifacts.json')
assert len(base['protected'])==303
for p,v in base['protected'].items():assert digest((root/p).read_bytes())==v,p
for p,v in base['generatedEntries'].items():
    data=re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',(root/p).read_bytes()),flags=re.S).replace(b'\r\n',b'\n')
    assert digest(data)==v,p
manifest=read('assets/pikapika-simulation.build.json')
assert (len(manifest['sourceSha256']),len(manifest['licenses']),len(manifest['linkedLibraryMembers']))==(61,7,91)
for p,v in manifest['sourceSha256'].items():assert sha256((root/p).read_bytes()).hexdigest()==v,p
assert manifest['licenses']==base['manifest']['licenses']
for p,v in manifest['artifacts'].items():assert digest((root/p).read_bytes())==v,p
assert manifest['linkedLibraryMembers']==base['manifest']['linkedLibraryMembers']
initial=f'reports/{prefix}-checks/run-20261104-initial';final=f'reports/{prefix}-checks/run-20261104-final'
commands=[]
for directory,phases in [(final,['native','exchange','regressions','old-sdk','recheck']),(initial,['wasm','wasm-exchange'])]:
    for phase in phases:
        for row in read(f'{directory}/{phase}-commands.json'):
            assert row['exit']==0 and row['authoredStable'],row['name']
            for stream in ['stdout','stderr']:assert digest((root/row[stream]).read_bytes())==row[stream+'Hash']
            for p,v in row['authoredAfter'].items():
                # The only source changed after the WASM build was the Native-only
                # API test: no compiled WASM source/header changed (all61 pinned).
                if phase=='wasm' and p=='tests/sphere_triangle_mesh_entry_sdk_tests.cpp':continue
                assert digest((root/p).read_bytes())==v,p
            commands.append(row)
def output(name):return (root/next(row['stdout'] for row in commands if row['name']==name)).read_text(encoding='utf-8')
assert '24 sphere triangle mesh entry C ABI groups passed' in output('entry-sdk')
assert '100% tests passed, 0 tests failed out of 38' in output('ctest')
for name,count in [('node',586),('learn',12)]:
    for marker in [f'ℹ tests {count}',f'ℹ pass {count}','ℹ fail 0','ℹ skipped 0']:assert marker in output(name),marker
native=read(f'{final}/native-exchange/report.json');wasm=read(f'{initial}/wasm-exchange/report.json');wire=read(f'{initial}/wasm-wire/report.json')
for packet in [native,wasm]:
    assert packet['status']=='PASS' and (packet['modelFixtures'],packet['hostRejected'])==(62,3)
    assert (packet['wireNumericComparisons'],packet['negativeZeroComparisons'])==(147638,3599)
    assert (packet['audits'],packet['certifiedLeaves'],packet['partitionLeaves'],packet['frontierLeaves'],packet['lastMeshRows'],packet['lastMeshCandidates'])==(1452,558,866,276,182,1256)
    assert packet['packetNegativeControls']['count']==27 and packet['packetNegativeControls']['allRejected']
    assert (packet['mathematicalNegativeControls']['selfTestGroups'],packet['mathematicalNegativeControls']['rejectedControls'])==(17,90)
assert (wire['accepted'],wire['hostRejected'],wire['numericBits'],wire['negativeZeroBits'])==(62,3,146130,3525)
assert (root/f'{initial}/native-exchange/packets.json').read_bytes()==(root/f'{final}/native-exchange/packets.json').read_bytes()
first=read(f'{initial}/native-commands.json');assert first[-1]['name']=='entry-sdk' and first[-1]['exit']==1
assert 'FAIL after 3 groups: Later certified island disappeared into prefix' in (root/first[-1]['stderr']).read_text()
assert 'warning ' not in output('native-build').lower()
browser=read(f'reports/{prefix}-local-browser-verification.json');assert browser['status']=='PASS'
assert browser['guardDefault']=={'numericBits':324,'negativeZeroBits':24,'status':'separated'}
owned=read(f'{final}/owned-sdk/report.json');assert owned['status']=='PASS' and (owned['actualModelFixtures'],owned['hostRejected'],owned['modelNumericComparisons'],owned['originalInputNumericComparisons'])==(59,3,50663,3877)
assert owned['negativeControls']['rejectedControls']==71
report={'schema':1,'status':'PASS','checked':datetime.now(timezone.utc).isoformat(),'baseCommit':base['baseCommit'],
 'ctest':38,'node':586,'skipped':0,'nativeExchangeGroups':24,'pureEntryGroups':76,'fixtures':65,
 'exports':86,'sourceHeaders':61,'protectedFilesUnchanged':303,'generatedEntriesOnly':24,'licenseNoticesUnchanged':7,
 'webBuild':'7999d8fe99c1f44d','modules':49,'entries':24,'artifacts':artifacts,
 'nativeExchange':native,'wasmExchange':wasm,'wasmWire':wire,'ownedSdkRegression':owned,'browser':browser,'commands':commands,
 'attempts':{'initial':'Initial all-Native build passed with no new warnings; new API test failed after3 groups. The two-surface case incorrectly required an island that the pinned pure corpus only demonstrates in its one-surface example. Test-only corrected; two-surface window/all-ID assertions retained, ordinary mesh unqueried-stage independence added. Final24 groups pass. All original streams retained; no API/kernel/fixture model values changed.',
 'wasmSourceStability':'The initial successful WASM command captured stable authored files. Only the Native-only API test was subsequently corrected. The build itself checked all61 actual compiled source/header hashes before/after and the current61 hashes still match its manifest; no WASM rebuild was needed for that test-only correction.',
 'browser':'First local combat reached defeat after2 kills; original visible state/report retained. Restarted, shot1 enemy, boosted and paused.72 displayed cover queries are cumulative across the session, not a count of the final flight alone.'},
 'scope':'Raw read-only C ABI/WASM exchange of defined sphere-path entry proof. Original pure65 mathematical reference is separate from expected packet equality of62 executed models/3 host-rejected inputs. No public owned JavaScript entry decoder/UI, World/TOI/contact response or deliberate allocation/unknown-work fault injection; no Windows sanitizer success claimed. Public GNU CI/Pages/byte checks remain separate.'}
(root/f'reports/{prefix}-local-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','ctest','node','nativeExchangeGroups','exports','sourceHeaders','protectedFilesUnchanged']}))
