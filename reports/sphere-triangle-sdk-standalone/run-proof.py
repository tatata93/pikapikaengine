import hashlib,json,pathlib,struct,subprocess,time
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parent.parent
def load(path):
    return json.loads(path.read_text(encoding='utf-8'),parse_int=lambda t:-0.0 if t=='-0' else int(t))
def desc(path):
    b=path.read_bytes();return {'path':str(path.relative_to(ROOT)).replace('\\','/'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def bits(v):return struct.pack('>d',v).hex()
commands=[]
def run(label,args,timeout=120):
    started=time.perf_counter();r=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout)
    (P/(label+'.stdout.txt')).write_bytes(r.stdout);(P/(label+'.stderr.txt')).write_bytes(r.stderr)
    commands.append({'label':label,'args':args,'exitCode':r.returncode,'elapsedObservedSeconds':time.perf_counter()-started,'stdout':desc(P/(label+'.stdout.txt')),'stderr':desc(P/(label+'.stderr.txt'))})
    (P/'commands-final.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
    print(label,r.returncode,len(r.stdout),len(r.stderr),flush=True)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace') or r.stdout.decode(errors='replace'))
    return r
sources=[ROOT/x for x in ['core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','tests/simulation_api_tests.cpp','tools/sphere_triangle_sdk_probe.cpp']]
before=[desc(p) for p in sources]
run('compile-final',['cmd','/c',str(P/'build-native.cmd')])
r=run('native-tests-final',[str(P/'simulation-api-tests.exe')]);assert b'77 simulation C ABI test groups passed' in r.stdout
r=run('probe-final',[str(P/'sphere-triangle-sdk-probe.exe'),'--rows',str(P/'input.rows')]);(P/'probe-final.json').write_bytes(r.stdout)
native=load(P/'probe-final.json');pure=load(ROOT/'build/sphere-triangle-core/native-fixtures.json')
assert native['fixtureCount']==113 and native['accepted']==111 and native['hostRejected']==2
assert len(native['fixtures'])==len(pure['fixtures'])==113
compared=0;host=0;last=[]
def compare(actual,hexes,expected):
    global compared
    assert len(actual)==len(hexes)==len(expected)
    a=[bits(x) for x in actual];assert a==hexes==[bits(x) for x in expected]
    compared+=len(a)
def flatten(x):return [v for pair in x for v in pair]
for row,source in zip(native['fixtures'],pure['fixtures']):
    assert row['name']==source['name']
    i=source['input'];s=i['settings'];expected_input=i['sphere']['center']+[i['sphere']['radius'],i['triangle']['id']]+[v for vertex in i['triangle']['vertices'] for v in vertex]+[s[k] for k in ['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared']]+[0]*4
    compare(row['input'],row['inputBits'],expected_input)
    assert [bits(x) for x in row['outputBefore']]==row['outputBeforeBits']==last
    if i['triangle']['id'] not in (0,9007199254740992):
        assert row['exchangeStatus']==0 and row['hostFailurePreserved'] is None
        r=source['result'];g=r['geometry'];a=[0.0]*58
        a[:11]=[r['status'],r['reason'],int(g is not None),i['triangle']['id'],g['survivingFeatures'] if g else 0,g['relation'] if g else 0,len(r['candidates']),r['candidatesExamined'],r['sqrtRefinements'],int(r['sqrtRefinementLimited']),int(r['squaredCross'] is not None)]
        if r['squaredCross'] is not None:a[11:13]=r['squaredCross']
        a[13]=int(r['sineSquared'] is not None)
        if r['sineSquared'] is not None:a[14:16]=r['sineSquared']
        if g:
            for offset,key in [(16,'barycentric'),(22,'closestLocal'),(28,'closest'),(34,'delta'),(40,'normal'),(46,'spherePoint')]:a[offset:offset+6]=flatten(g[key])
            a[52:54]=g['squaredDistance'];a[54:56]=g['distance'];a[56:58]=g['gap']
        compare(row['summary'],row['summaryBits'],a)
        assert len(row['candidates'])==len(row['candidateBits'])==len(r['candidates'])
        for packet,hexes,c in zip(row['candidates'],row['candidateBits'],r['candidates']):compare(packet,hexes,[c['feature'],c['disposition'],c['kktCount']]+flatten(c['barycentric'])+flatten(c['kkt']))
        last=row['candidateBits'][-1] if row['candidateBits'] else row['summaryBits']
    else:
        host+=1;assert row['exchangeStatus']==1 and row['hostFailurePreserved'] is True and row['summary'] is None and row['summaryBits'] is None and row['candidates']==row['candidateBits']==[]
    assert [bits(x) for x in row['outputAfter']]==row['outputAfterBits']==last
assert host==2 and before==[desc(p) for p in sources]
assert b'warning ' not in (P/'compile-final.stdout.txt').read_bytes()
audit={'status':'PASS','fixtures':113,'acceptedModels':111,'explicitIdExchangeRejections':2,'numericBitsCompared':compared,'packetLayoutAgainstFrozenPureKernel':True,'independentGeometryOracle':False,'outputHistoryAndCapturedHexValidated':True,'unusedKktNegativeZero':native['fixtures'][0]['candidateBits'][0][9]}
(P/'transport-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
provenance={'schema':1,'status':'PASS','sources':before,'readOnlyLibrary':desc(P/'frozen-core.lib'),'pureKernelSources':[desc(ROOT/'core/include/pikapika/sphere_triangle.hpp'),desc(ROOT/'core/src/sphere_triangle.cpp')],'corpus':desc(ROOT/'build/sphere-triangle-core/native-fixtures.json'),'rows':desc(P/'input.rows'),'commands':'commands-final.json','audit':audit,'scope':'Independent build of new API object/tests/probe linked against byte-copied existing core library. Original library API object is not extracted; full fresh CMake validation is parent-owned. No shared build/native files were written. No SDK build by this agent.','initialWarning':'First build C4389 signed/unsigned comparison at candidate KKT count; only 0/1/2 literals changed to 0u/1u/2u before final freeze/rebuild.'}
(P/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
print(json.dumps(audit,indent=2),flush=True)
