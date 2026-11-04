from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3];RUN=Path(__file__).resolve().parent
SCRATCH=ROOT/'build/accelerated-sphere-box-coverage-native-development/run-001'
SCRATCH.mkdir(parents=True,exist_ok=False);(SCRATCH/'obj').mkdir()
BASE=ROOT/'reports/accelerated-sphere-box-coverage-development/before-implementation.json'
baseline=json.loads(BASE.read_text('utf-8'))
SOURCES=['core/include/pikapika/accelerated_sphere_box_coverage.hpp','core/src/accelerated_sphere_box_coverage.cpp','tests/accelerated_sphere_box_coverage_tests.cpp','tests/accelerated_sphere_box_coverage_fixtures.cpp','tests/accelerated_sphere_box_coverage_test_support.hpp','core/include/pikapika/accelerated.hpp','core/src/accelerated.cpp','core/include/pikapika/interval.hpp','core/src/interval.cpp','core/include/pikapika/core.hpp']
def info(path):
 b=Path(path).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def sourceinfo():return {p:info(ROOT/p) for p in SOURCES}
def protection():
 return {k:{'checked':len(baseline[k]),'differences':[p for p,m in baseline[k].items() if info(ROOT/p)!=m]} for k in ['protected','generatedEntries','integrations']}
def save(name,value):
 with (RUN/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
initial=sourceinfo(); initialprotection=protection()
assert all(not p['differences'] for p in initialprotection.values())
lookup=(ROOT/'tests/accelerated_sphere_box_coverage_tests.cpp').read_text('utf-8')
assert 'named(const std::vector<f::Case>& corpus,std::string_view name)' in lookup
old=ROOT/'reports/accelerated-plane-box-coverage-native-development/run-001'
rsp=(old/'compile.rsp').read_text('utf-8').replace(str(old),str(SCRATCH)).replace('accelerated_plane_box_coverage','accelerated_sphere_box_coverage')
(RUN/'compile.rsp').write_text(rsp,encoding='utf-8',newline='\n')
cmd='@echo off\ncall "C:\\Program Files (x86)\\Microsoft Visual Studio\\18\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl.exe @"'+str(RUN/'compile.rsp')+'"\nexit /b %errorlevel%\n'
(RUN/'compile.cmd').write_text(cmd,encoding='utf-8',newline='\n')
save('invocation.json',{'schema':1,'argv':sys.argv,'cwd':str(ROOT),'scope':'Future independent Native-only first standalone; current corrected plane public acceptance separate/pending. Not actual World or SDK acceptance.','script':info(__file__),'baseline':{'path':str(BASE.relative_to(ROOT)),'file':info(BASE),'baseCommit':baseline['baseCommit'],'scope':baseline['scope']},'sourceBefore':initial,'protectionBefore':initialprotection,'fiveTUCompile':True,'namedLookupStringViewByValue':True})
commands=[]
def call(name,args,outname,timeout):
 before=sourceinfo();pBefore=protection();start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();timeoutflag=False
 try:p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout);out,err,code=p.stdout,p.stderr,p.returncode
 except subprocess.TimeoutExpired as e:out,err,code=e.stdout or b'',e.stderr or b'',None;timeoutflag=True
 duration=time.monotonic()-t
 (RUN/outname).write_bytes(out);(RUN/(name+'.stderr.txt')).write_bytes(err)
 after=sourceinfo();pAfter=protection()
 record={'name':name,'args':args,'started':start,'wallSeconds':duration,'exit':code,'timedOut':timeoutflag,'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after,'protectionBefore':pBefore,'protectionAfter':pAfter,'stdout':outname,'stdoutHash':info(RUN/outname),'stderr':name+'.stderr.txt','stderrHash':info(RUN/(name+'.stderr.txt'))}
 commands.append(record);(RUN/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8',newline='\n')
 assert not timeoutflag and code==0,(name,code,timeoutflag)
 assert before==after and all(not p['differences'] for p in pAfter.values()),(name,'source/protected changed')
 return out
call('compile',['cmd.exe','/d','/c',str(RUN/'compile.cmd')],'compile.stdout.txt',180)
exe=str(SCRATCH/'coverage-tests.exe')
stdout=call('native-tests',[exe],'native-tests.stdout.txt',60)
raw=call('native-fixtures',[exe,'--fixtures'],'native-fixtures.json',60)
storage=call('storage',[exe,'--storage'],'native-storage.json',60)
text=stdout.decode('utf-8');m=re.search(r'(\d+) groups PASS; (\d+) finite fixtures; (\d+) full Evaluation exact-bit replays / (\d+) endpoint comparisons / (\d+) negative-zero endpoints / (\d+) root diagnostic comparisons',text);assert m,text
counts=list(map(int,m.groups()))
data=json.loads(raw);fixtures=data['fixtures'];assert len(fixtures)==counts[1]
status={}
for f in fixtures:
 s=str(f['result']['status']);status[s]=status.get(s,0)+1
compiletext=(RUN/'compile.stdout.txt').read_text('utf-8',errors='replace')+(RUN/'compile.stderr.txt').read_text('utf-8',errors='replace')
assert not re.search(r'warning C\d+',compiletext)
assert all((RUN/(r['name']+'.stderr.txt')).stat().st_size==0 for r in commands)
assert sourceinfo()==initial
sizes=json.loads(storage);logical=sum(sizes['sizes'][name]*sizes['capacities'][field] for name,field in [('audit','audits'),('partitionLeaf','partition'),('cell','frontier')])
accept={'schema':1,'status':'PASS','phase':'future-first-independent-Native','nativeGroups':counts[0],'finiteFixtures':counts[1],'fullEvaluationPublicValueBitReplays':counts[2],'endpointBitComparisons':counts[3],'negativeZeroEndpoints':counts[4],'rootDiagnosticComparisons':counts[5],'statusDistribution':status,'fixture':info(RUN/'native-fixtures.json'),'msvcWarningCount':0,'allCommandsSucceeded':True,'sourceStable':True,'protection':protection(),'observedStorage':sizes,'logicalRetainedSizeofTimesCapacityBytes':logical,'scopeLimits':['Exact public-value bit provenance and metadata/topology tests only; independent Fraction mathematics pending.','Synthetic unknown block controls do not execute actual C++ allocator/value/root faults.','No actual World/compiler-sqrt binding, SDK, general-target, performance or physical-memory guarantee.','Timing is observed command wall time only.','Baseline pre-authoring is explicitly public-pending historical scope, not a final integration acceptance.'],'commands':commands,'sourceBefore':initial,'sourceAfter':sourceinfo()}
save('acceptance.json',accept)
print(json.dumps({k:accept[k] for k in ['status','nativeGroups','finiteFixtures','fullEvaluationPublicValueBitReplays','endpointBitComparisons','negativeZeroEndpoints','rootDiagnosticComparisons','statusDistribution','fixture','msvcWarningCount','logicalRetainedSizeofTimesCapacityBytes']}))
