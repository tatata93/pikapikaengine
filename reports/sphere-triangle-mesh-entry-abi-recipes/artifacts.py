"""Audit the real regenerated SDK, original sources and distribution notices."""
from pathlib import Path
from hashlib import sha256
import json,re,sys
root=Path(__file__).resolve().parents[2]
def read(p):return json.loads((root/p).read_text(encoding='utf-8-sig'))
def sha(p):return sha256((root/p).read_bytes()).hexdigest()
base=read('reports/sphere-triangle-mesh-entry-abi-baseline.json');old=base['manifest'];new=read('assets/pikapika-simulation.build.json')
assert new['sdkVersion']==old['sdkVersion']=='6.0.13' and new['sdkCommit']==old['sdkCommit']
assert new['memory']==old['memory'] and new['licenses']==old['licenses'] and len(new['licenses'])==7
for p,d in new['licenses'].items():assert sha(p)==d,p
for p,d in new['sourceSha256'].items():assert sha(p)==d,p
assert len(new['sourceSha256'])==61 and len(new['sources'])==30
changed=[p for p in old['sourceSha256'] if new['sourceSha256'][p]!=old['sourceSha256'][p]]
assert set(changed)=={'core/src/simulation_api.cpp','core/include/pikapika/simulation_api.h'},changed
added=set(new['sourceSha256'])-set(old['sourceSha256'])
assert added=={'core/src/sphere_triangle_mesh_entry.cpp','core/include/pikapika/sphere_triangle_mesh_entry.hpp'}
def exports(m):return json.loads(next(x.split('=',1)[1] for x in m['flags'] if x.startswith('-sEXPORTED_FUNCTIONS=')))
before,after=exports(old),exports(new)
assert len(before)==80 and len(after)==86 and set(before)<=set(after)
assert len(set(after))==86 and all(x.startswith('_pp_sim_sphere_triangle_mesh_entry') for x in set(after)-set(before))
for p,v in new['artifacts'].items():
    data=(root/p).read_bytes();assert {'bytes':len(data),'sha256':sha256(data).hexdigest()}==v,p
for p,v in base['protected'].items():
    data=(root/p).read_bytes();assert {'bytes':len(data),'sha256':sha256(data).hexdigest()}==v,p
for p,v in base['generatedEntries'].items():
    data=(root/p).read_bytes();data=re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',re.sub(rb'\?build=[a-f0-9]{16}',b'?build=GENERATED',data),flags=re.S).replace(b'\r\n',b'\n')
    assert {'bytes':len(data),'sha256':sha256(data).hexdigest()}==v,p
members_before=set(old['linkedLibraryMembers']);members_after=set(new['linkedLibraryMembers'])
report={'schema':1,'status':'PASS','exports':86,'previousExports':80,'addedExports':sorted(set(after)-set(before)),'sources':30,'sourceHeaders':61,'originalSourceHashChanges':changed,'addedSourceHeaders':sorted(added),'protectedFilesUnchanged':len(base['protected']),'generatedEntriesOnly':len(base['generatedEntries']),'licenseNoticesUnchanged':7,'runtimeMembers':len(members_after),'runtimeMembersAdded':sorted(members_after-members_before),'runtimeMembersRemoved':sorted(members_before-members_after),'artifacts':new['artifacts'],'memory':new['memory'],'scope':'Actual generated distribution and source provenance; memory limits are configuration, not measured high-water usage or performance. Notice bytes and linked-member differences are explicit. No external solver or engine-license decision.'}
target=root/sys.argv[1];target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
