import hashlib,json,re
from pathlib import Path
p=Path('build/skinning-sort')
def check(ok,message):
 if not ok:raise RuntimeError(message)
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
old=json.loads((p/'before-sdk.build.json').read_text());new=json.loads(Path('assets/pikapika-simulation.build.json').read_text())
check(old['sources']==new['sources'] and old['flags']==new['flags'] and old['sourceFlags']==new['sourceFlags'],'unchanged build recipe/domain')
check(set(old['sourceSha256'])==set(new['sourceSha256']),'unchanged source set');changed=[f for f,h in old['sourceSha256'].items() if new['sourceSha256'][f]!=h];check(changed==['core/src/skinning.cpp'],'only intended kernel source changes')
check(new['sourceSha256']['core/src/skinning.cpp']=='5f9e3a24db5adcc97c382a47d7dd1812fdf6938d3b104079654f7276e161cb87','frozen kernel');check(sha('tests/skinning_tests.cpp')=='ed1df7923bc6ab9ba0d1c8a00cb85a1b2303de742bbe4aeead18b9740a7db044','frozen tests')
for f,h in new['sourceSha256'].items():check(sha(f)==h,'source '+f)
for f,a in new['artifacts'].items():check(sha(f)==a['sha256'] and Path(f).stat().st_size==a['bytes'],'artifact '+f)
check(old['licenses']==new['licenses'],'license manifest unchanged')
for f,h in new['licenses'].items():check(sha(f)==h,'license '+f)
names=list(dict.fromkeys(re.findall(r'\b(pp_sim_\w+)\s*\(',Path('core/include/pikapika/simulation_api.h').read_text())));check(len(names)==63,'exports')
r={'passed':True,'changedSourceFiles':changed,'sourceHeaderHashesChecked':len(new['sourceSha256']),'artifactHashesChecked':len(new['artifacts']),'runtimeLicenseHashesChecked':len(new['licenses']),'runtimeLicensesUnchanged':True,'exportCount':len(names),'artifacts':new['artifacts'],'manifestSha256':sha('assets/pikapika-simulation.build.json'),'strictFlagsUnchanged':True,'buildScriptSha256':sha('scripts/build-simulation.mjs')}
(p/'sdk-audit.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r,indent=2))
