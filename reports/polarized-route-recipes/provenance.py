import datetime,hashlib,json,pathlib,subprocess
base=pathlib.Path('build/polarized-route-proof')
def sha(path):
    p=pathlib.Path(path);b=p.read_bytes();return {'path':str(p).replace('\\','/'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(args):return subprocess.check_output(args,text=True).strip()
def count(x):
    if type(x) in (int,float):return 1
    if type(x)is list:return sum(map(count,x))
    if type(x)is dict:return sum(map(count,x.values()))
    return 0
native=json.loads((base/'native-fixtures.json').read_text(encoding='utf-8-sig'))
owned=['core/include/pikapika/polarized_route.hpp','core/src/polarized_route.cpp','tests/polarized_route_tests.cpp','scripts/verify-polarized-route.py','docs/POLARIZED_ROUTE.md']
dependencies=['core/include/pikapika/interval.hpp','core/src/interval.cpp','core/include/pikapika/optical_bounds.hpp','core/src/optical_bounds.cpp','core/include/pikapika/optical_route.hpp','core/src/optical_route.cpp']
artifacts=['polarized-tests.exe','polarized-standalone.mjs','polarized-standalone.wasm','native-tests.txt','wasm-tests.txt','native-fixtures.json','wasm-fixtures.json','native-oracle.csv','wasm-oracle.csv','fixture-comparison.json','checker-negative-controls.json','proof-commands.json','build.cmd','build-wasm.mjs','run-wasm.mjs','record-proof.py','negative-controls.py']
proof={
 'createdUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'baseCommit':read(['git','rev-parse','HEAD']),
 'scope':'Original prescribed-route interval coherency POWER transport; no source changes outside owned five files. Shared interval sqrt is parent-owned.',
 'ownedSources':[sha(p) for p in owned], 'dependencies':[sha(p) for p in dependencies],
 'artifacts':[sha(base/p) for p in artifacts],
 'sdk':{'gitHead':read(['git','-C','build/toolchains/emsdk','rev-parse','HEAD']),'compilerVersion':(base/'wasm-compiler.txt').read_text(encoding='utf-8-sig'),'release':'6.0.13'},
 'native':{'compiler':'MSVC 19.51, VC Tools 14.51.36231','flags':['/std:c++20','/EHsc','/MD','/O2','/W4','/fp:strict'],'buildCommand':['cmd','/c','build\\polarized-route-proof\\build.cmd'],'groups':37},
 'wasm':{'flags':['-std=c++20','-O2','-fwasm-exceptions','-fno-rtti','-fno-fast-math','-ffp-contract=off'],'buildCommand':['node','build/polarized-route-proof/build-wasm.mjs'],'groups':37},
 'verification':{'fixtureCount':32,'fixtureNumericValues':count(native),'oracleUniqueRows':128,'oracleBinary64ValuesCompared':3072,'independentInclusionsPerTarget':1539,'independentInclusionsTotal':3078,'allFixtureAndOracleBitsEqual':True,'negativeControlsRejected':88,'references':'docs/POLARIZED_ROUTE.md'},
 'limitations':['Finite acceptance corpus is not a proof for all continuous input families.','Full-family containment follows strict interval construction and stated physical model.','sqrt budget overshoot is bounded by one route or one new sqrt call on failure.','No radiance/irradiance, coherent path recombination, diffraction, automatic visibility or medium geometry validation.']}
(base/'provenance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps({'wasm':sha(base/'polarized-standalone.wasm'),'ownedSources':proof['ownedSources'],'verification':proof['verification']},indent=2))
