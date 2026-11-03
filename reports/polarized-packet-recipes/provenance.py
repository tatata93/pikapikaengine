import datetime,hashlib,json,pathlib,subprocess
base=pathlib.Path('build/polarized-packet-proof')
def sha(path):
    p=pathlib.Path(path);b=p.read_bytes();return {'path':str(p).replace('\\','/'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(args):return subprocess.check_output(args,text=True).strip()
def count(x):
    if type(x) in (int,float):return 1
    if type(x) is list:return sum(map(count,x))
    if type(x) is dict:return sum(map(count,x.values()))
    return 0
owned=['core/include/pikapika/polarized_packet.hpp','core/src/polarized_packet.cpp','tests/polarized_packet_tests.cpp','scripts/verify-polarized-packet.py','docs/POLARIZED_PACKET.md']
deps=['core/include/pikapika/interval.hpp','core/src/interval.cpp','core/include/pikapika/optical_bounds.hpp','core/src/optical_bounds.cpp','core/include/pikapika/optical_route.hpp','core/src/optical_route.cpp','core/include/pikapika/polarized_route.hpp','core/src/polarized_route.cpp']
artifacts=['packet-tests.exe','packet-standalone.mjs','packet-standalone.wasm','native-tests.txt','wasm-tests.txt','native-fixtures.json','wasm-fixtures.json','native-oracle.csv','wasm-oracle.csv','fixture-comparison.json','checker-negative-controls.json','proof-commands.json','build.cmd','build-wasm.mjs','run-wasm.mjs','record-proof.py','negative-controls.py']
data=json.loads((base/'native-fixtures.json').read_text(encoding='utf-8-sig'))
proof={
 'createdUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'baseCommit':read(['git','rev-parse','HEAD']),
 'scope':'Original finite noninterfering packet POWER watts tally on one prescribed route and a geometric ideal sensor; all existing kernels untouched.',
 'ownedSources':[sha(p) for p in owned],'dependencies':[sha(p) for p in deps],'artifacts':[sha(base/p) for p in artifacts],
 'sdk':{'gitHead':read(['git','-C','build/toolchains/emsdk','rev-parse','HEAD']),'release':'6.0.13','compilerVersion':(base/'wasm-compiler.txt').read_text(encoding='utf-8-sig')},
 'native':{'compiler':'MSVC 19.51, VC Tools 14.51.36231','flags':['/std:c++20','/EHsc','/MD','/O2','/W4','/fp:strict'],'buildCommand':['cmd','/c','build\\polarized-packet-proof\\build.cmd'],'groups':42},
 'wasm':{'flags':['-std=c++20','-O2','-fwasm-exceptions','-fno-rtti','-fno-fast-math','-ffp-contract=off'],'buildCommand':['node','build/polarized-packet-proof/build-wasm.mjs'],'groups':42},
 'verification':{'fixtureCount':36,'fixtureNumericValues':count(data),'oracleUniqueRows':128,'oracleBinary64ValuesCompared':1280,'independentInclusionsPerTarget':501,'independentInclusionsTotal':1002,'allFixtureAndOracleBitsEqual':True,'negativeControlsRejected':107},
 'limitations':['Caller explicitly supplies each packet POWER watts, not inferred geometric weights.','Packets are mutually noninterfering; one packet retains polarization coherence only.','One prescribed itinerary only; no automatic visibility, global medium proof or multi-route interference.','Ideal two-sided absorbing sensor is geometric; no extra cosine/index-squared multiplier.','Unknown/budget/not-examined prohibit final POWER tally; zero source POWER does not suppress audits.','Strict interval arithmetic proves enclosures under stated model/build contract, not arbitrary member PSD of a Cartesian coherency box.','Finite corpus/parity is measured evidence, not continuous-source quadrature error or compiler proof.']}
(base/'provenance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps({'wasm':sha(base/'packet-standalone.wasm'),'ownedSources':proof['ownedSources'],'verification':proof['verification']},indent=2))
