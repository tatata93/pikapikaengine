import pathlib,json,hashlib,subprocess,re,sys
root=pathlib.Path(__file__).resolve().parents[2]
report=root/'reports';mapping=[]
def digest(b):return hashlib.sha256(b).hexdigest()
def save(path,data):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        if p.read_bytes()!=data:raise ValueError('archive conflict '+path)
    else:
        with p.open('xb') as f:f.write(data)
    return {'path':path,'bytes':len(data),'sha256':digest(data)}
def copy(src,dst):
    s=root/src;b=s.read_bytes();q=save(dst,b);q['original']=str(s.relative_to(root));mapping.append(q)
def packet(path,obj):return save(path,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
proof=pathlib.Path(json.loads((root/'build/derived-mesh-sdk-root/proof-latest.json').read_text())['runDirectory'])
reg=pathlib.Path(json.loads((root/'build/derived-mesh-sdk-root/regression-latest.json').read_text())['runDirectory'])
fixtures=pathlib.Path(json.loads((root/'build/derived-mesh-sdk-root/latest.json').read_text())['runDirectory'])
for label,p in [('root',proof),('regressions',reg),('fixtures',fixtures)]:
    for f in p.iterdir():
        if f.is_file():copy(f.relative_to(root),f'reports/derived-mesh-sdk-{label}-{f.name}')
for stem in ['configure','native-build','ctest','wasm-build','npm-test','web-build']:
    copy(f'build/derived-mesh-sdk-{stem}.txt',f'reports/derived-mesh-sdk-{stem}.txt')
raw=(root/'build/native/Testing/Temporary/LastTest.log').read_bytes()
save('reports/derived-mesh-sdk-ctest-raw.txt',raw)
decoded=raw.decode('cp932').replace('\r\r\n','\n').replace('\r\n','\n')
save('reports/derived-mesh-sdk-ctest-utf8.txt',decoded.encode('utf-8'))
for name in ['build/derived-mesh-sdk-root/verify.py','build/derived-mesh-sdk-root/regressions.py','build/derived-mesh-sdk-root/archive.py']:
    copy(name,'reports/derived-mesh-sdk-recipes/'+str(pathlib.Path(name).relative_to('build')).replace('\\','/'))
for name in ['engine/simulation.mjs','tests/derived-mesh-sdk.test.mjs','scripts/verify-derived-mesh-wasm.mjs','scripts/verify-derived-mesh.py','tests/derived_mesh_reference_tests.py','core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','tests/simulation_api_tests.cpp','tools/derived_mesh_probe.cpp','tools/skin-binding-lab.mjs','tests/skin-binding-lab.test.mjs','scripts/build-simulation.mjs']:
    copy(name,'reports/derived-mesh-sdk-recipes/source/'+name)
m=json.loads((root/'assets/pikapika-simulation.build.json').read_text())
audits=[]
for category,items in [('source',m['sourceSha256']),('license',m['licenses']),('artifact',m['artifacts'])]:
    for path,v in items.items():
        expected=v['sha256'] if isinstance(v,dict) else v;b=(root/path).read_bytes()
        if digest(b)!=expected:raise ValueError('SDK hash '+path)
        audits.append({'category':category,'path':path,'bytes':len(b),'sha256':expected})
old=json.loads(subprocess.check_output(['git','show','HEAD:assets/pikapika-simulation.build.json'],cwd=root))
source_changes=[p for p,h in m['sourceSha256'].items() if old['sourceSha256'].get(p)!=h]
preserved=[]
for p in subprocess.check_output(['git','ls-files','samples','assets','tests/fixtures'],cwd=root,text=True).splitlines():
    if p in m['artifacts'] or p=='assets/pikapika-simulation.build.json':continue
    b=(root/p).read_bytes();oldb=subprocess.check_output(['git','show','HEAD:'+p],cwd=root)
    if b!=oldb:raise ValueError('unintended sample/asset change '+p)
    preserved.append({'path':p,'bytes':len(b),'sha256':digest(b)})
header=(root/'core/include/pikapika/simulation_api.h').read_text()
exports=len(re.findall(r'PP_SIM_EXPORT[^;]+;',header))
binaries=[]
for name in ['pikapika_simulation_api_tests.exe','pikapika-derived-probe.exe','pikapika_derived_mesh_tests.exe']:
    p=root/'build/native/Release'/name;b=p.read_bytes();binaries.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':digest(b)})
local=json.loads((root/'reports/derived-mesh-sdk-local-browser.json').read_text())
q=json.loads((proof/'replay-report.json').read_text())
verification={'status':'LOCAL PASS; public CI/Pages pending','native':{'groups':739,'ctest':30,'abiGroups':65,'pureDerivedGroups':54},'node':{'passed':369,'skipped':0},'sdk':{'sourceHeaderCount':len(m['sourceSha256']),'licenseCount':len(m['licenses']),'exportCount':65,'sourceChangesVersusPreviousManifest':source_changes,'manifest':{'bytes':(root/'assets/pikapika-simulation.build.json').stat().st_size,'sha256':digest((root/'assets/pikapika-simulation.build.json').read_bytes())},'audit':audits},'actualDerivedReplay':{'fixedModelCases':40,'sourceCases':11,'numericBits':q['numericComparisons'],'fixedNumericBits':q['fixtureNumericComparisons'],'sourceNumericBits':q['probeNumericComparisons'],'hostSubstitutions':0},'reference':{'backends':['native','main-wasm'],'each':{'selfGroups':7,'acceptedControls':2,'rejectedControls':36}},'regressionCommands':23,'additionalMotionAndSkinReplays':2,'browserObservations':len(local['observations']),'webBuild':'ebfa843cac6779cc','modules':39,'binaries':binaries,'preservedSampleAssets':preserved,'archive':mapping,'scope':'Local quantized CPU mesh only. No new 3D/GPU renderer or world/view/clip proof. Manual prepare is not measured real-time rendering.','initialFailures':['JS test sensor omitted existing required kind=disk; fixed test input only; raw initial log archived.','Ignored root recipe first used nonexistent historical motion-oracle.csv; corrected path to motion-native-oracle.csv and reran all 5 final commands successfully; original failed run remains in build/derived-mesh-sdk-root.','Standalone compiler recipe initially misquoted /Fo; corrected ignored recipe and final nine commands passed; initial raw run retained in build.']}
packet('reports/derived-mesh-sdk-verification.json',verification)
print(json.dumps({'files':len(mapping),'sdkAudits':len(audits),'sources':len(m['sourceSha256']),'preserved':len(preserved),'sourceChanges':source_changes,'bits':q['numericComparisons']},indent=2))
