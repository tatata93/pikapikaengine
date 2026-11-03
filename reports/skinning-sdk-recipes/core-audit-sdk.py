import hashlib,json,re,subprocess
from pathlib import Path
p=Path('build/skinning-sdk')
def check(ok,message):
 if not ok:raise RuntimeError(message)
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
m=json.loads(Path('assets/pikapika-simulation.build.json').read_text());before=json.loads((p/'before-build.json').read_text())
check(m['schema']==1 and m['apiVersion']==1,'manifest schema/api');check(m['sdkVersion']=='6.0.13' and m['sdkCommit']=='d7b4130688bfa348392b921ab04015aa15c4f154','fixed SDK');check(m['releaseHash']=='eb132757325583b787fe9414b09afea9442b72ad','fixed release');check(m['emscriptenRevision']=='e13ee988ce3d87a738dd8f3661d02223308c412a','fixed compiler')
source_names=m['sources'];check(len(set(source_names))==len(source_names),'duplicate source');check('core/src/skinning.cpp' in source_names,'missing skin source');check('core/include/pikapika/skinning.hpp' in m['sourceSha256'],'missing skin header');check(m['sourceFlags']['core/src/skinning.cpp']==['-fno-fast-math','-ffp-contract=off'],'skin strict flags')
for f,h in m['sourceSha256'].items():check(sha(f)==h,'source hash '+f)
frozen={'core/include/pikapika/skinning.hpp':'8e9af179e88c4f8b144c9cd4fb9c488fdd2c0a00462a26ccd06951be21a9a664','core/src/skinning.cpp':'4d7754cfe2d753c3edceff780b1f99345b6ecc7bdff73c54c55a9e048738a0b3','core/include/pikapika/simulation_api.h':'e752848656509105a6e7295f8789531c0f3243014aac14b4744905d7a5779e0d','core/src/simulation_api.cpp':'038e016a5856a6ebdd3267bba9e7ef12cd8a9ff03343322ef4cf178c5aff2c3d'}
for f,h in frozen.items():check(sha(f)==h,'frozen source '+f)
expected_changed={'core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp'};changed=[]
for f,h in before['sourceSha256'].items():
 if m['sourceSha256'][f]!=h:changed.append(f)
check(set(changed)==expected_changed,'unexpected preexisting source changes')
for f,a in m['artifacts'].items():check(sha(f)==a['sha256'] and Path(f).stat().st_size==a['bytes'],'artifact hash '+f)
check(len(m['licenses'])>=7 and len(m['linkedLibraryMembers'])>0,'missing linked/runtime licenses')
for f,h in m['licenses'].items():check(sha(f)==h,'license hash '+f)
changed_licenses=[f for f,v in before['licenses'].items() if sha(f)!=v['sha256']]
check(set(before['licenses'])==set(m['licenses']),'unexpected license set');check(not changed_licenses,'runtime notices changed outside assigned assets')
header=Path('core/include/pikapika/simulation_api.h').read_text();exports=list(dict.fromkeys(re.findall(r'\b(pp_sim_\w+)\s*\(',header)))
check(len(exports)==63,'export count');check(set(['pp_sim_skin_bind','pp_sim_skin_bind_record','pp_sim_skin_deform','pp_sim_skin_deform_record'])<=set(exports),'new exports missing')
check(m['memory']=={'initialBytes':67108864,'maximumBytes':268435456,'stackBytes':1048576},'memory profile')
result={'passed':True,'exportCount':len(exports),'sourceCount':len(source_names),'sourceHeaderHashesChecked':len(m['sourceSha256']),'artifactHashesChecked':len(m['artifacts']),'licenseHashesChecked':len(m['licenses']),'preexistingSourceChanges':changed,'newSourceFiles':[f for f in m['sourceSha256'] if f not in before['sourceSha256']],'changedRuntimeLicenseFiles':changed_licenses,'artifacts':m['artifacts'],'buildScriptSha256':sha('scripts/build-simulation.mjs'),'frozenSources':frozen,'manifestSha256':sha('assets/pikapika-simulation.build.json')}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
