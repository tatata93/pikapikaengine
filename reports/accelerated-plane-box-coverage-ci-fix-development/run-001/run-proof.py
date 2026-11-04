from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3]
RUN=Path(__file__).resolve().parent
SCRATCH=ROOT/'build/accelerated-plane-box-ci-fix/run-001'
SCRATCH.mkdir(parents=True,exist_ok=False)
(SCRATCH/'obj').mkdir()
def info(path):
 b=Path(path).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(name,value):
 p=RUN/name
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
old=ROOT/'reports/accelerated-plane-box-coverage-native-development/run-001'
legacy=json.loads((old/'commands.json').read_text('utf-8'))[0]['sourceBefore']
paths=list(legacy)+['assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json']
def sources():return {p:info(ROOT/p) for p in paths}
before=sources()
for p,x in legacy.items():
 if p!='tests/accelerated_plane_box_coverage_tests.cpp':assert before[p]==x,(p,before[p],x)
fix=json.loads((RUN/'before-edit.json').read_text('utf-8'))
assert before[fix['source']]==fix['plannedSource']
oldrsp=(old/'compile.rsp').read_text('utf-8')
rsp=oldrsp.replace(str(old),str(SCRATCH))
(RUN/'compile.rsp').write_text(rsp,encoding='utf-8',newline='\n')
cmd='@echo off\ncall "C:\\Program Files (x86)\\Microsoft Visual Studio\\18\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl.exe @"'+str(RUN/'compile.rsp')+'"\nexit /b %errorlevel%\n'
(RUN/'compile.cmd').write_text(cmd,encoding='utf-8',newline='\n')
save('invocation.json',{'schema':1,'argv':sys.argv,'cwd':str(ROOT),'baseCommit':fix['baseCommit'],'scope':'Postfix targeted strict MSVC tests/fixture provenance only; Linux GCC13 warning closure remains pending public CI. Previous local acceptance hashes remain historical.','script':info(__file__),'sourceBefore':before})
commands=[]
def call(name,args,output,timeout):
 a=sources();start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();timedout=False
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=timeout);out,err,code=p.stdout,p.stderr,p.returncode
 except subprocess.TimeoutExpired as e:
  out,err,code=e.stdout or b'',e.stderr or b'',None;timedout=True
 duration=time.monotonic()-t
 (RUN/output).write_bytes(out);(RUN/(name+'.stderr.txt')).write_bytes(err)
 b=sources();record={'name':name,'args':args,'started':start,'wallSeconds':duration,'exit':code,'timedOut':timedout,'sourceBefore':a,'sourceAfter':b,'sourceStable':a==b,'stdout':output,'stdoutHash':info(RUN/output),'stderr':name+'.stderr.txt','stderrHash':info(RUN/(name+'.stderr.txt'))}
 commands.append(record);(RUN/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8',newline='\n')
 assert not timedout and code==0,(name,code,timedout)
 assert a==b,(name,'source changed')
 return out
call('compile',['cmd.exe','/d','/c',str(RUN/'compile.cmd')],'compile.stdout.txt',180)
exe=str(SCRATCH/'coverage-tests.exe')
tests=call('native-tests',[exe],'native-tests.stdout.txt',45)
fixtures=call('native-fixtures',[exe,'--fixtures'],'native-fixtures.json',45)
storage=call('storage',[exe,'--storage'],'storage.json',45)
assert b'74' in tests and b'1306' in tests and b'15672' in tests and b'2496' in tests
assert fixtures==(old/'native-fixtures.json').read_bytes()
canonical=ROOT/'reports/accelerated-plane-box-coverage-checks/run-20261104-native-001/native-fixtures.json'
if canonical.exists():assert fixtures==canonical.read_bytes()
assert storage==(old/'native-storage.json').read_bytes()
compiletext=(RUN/'compile.stdout.txt').read_text('utf-8',errors='replace')+(RUN/'compile.stderr.txt').read_text('utf-8',errors='replace')
assert not re.search(r'warning C\d+',compiletext)
assert all((RUN/(x['name']+'.stderr.txt')).stat().st_size==0 for x in commands)
assert sources()==before
actualdiff=subprocess.run(['git','diff','--','tests/accelerated_plane_box_coverage_tests.cpp'],cwd=ROOT,capture_output=True,check=True).stdout
(RUN/'actual.patch.txt').write_bytes(actualdiff)
accept={'schema':1,'status':'PASS','phase':'targeted-postfix-local','baseCommit':fix['baseCommit'],'source':fix['source'],'original':fix['original'],'new':sources()[fix['source']],'change':'named accepts string_view by value, explicit string_view include, diagnostic string materialization; references still point to caller-owned corpus','groups':74,'finiteFixtures':67,'fullEvaluationProvenance':1306,'endpointBits':15672,'negativeZeroEndpoints':2496,'fixtures':info(RUN/'native-fixtures.json'),'fixtureByteIdenticalToOriginalStandalone':True,'fixtureByteIdenticalToCanonicalNative':canonical.exists(),'storageByteIdenticalToOriginalStandalone':True,'msvcWarnings':0,'sourceStable':True,'otherCompiledSourcesUnchanged':True,'sdkArtifactsUnchanged':True,'commands':commands,'sourceBefore':before,'sourceAfter':sources(),'patch':info(RUN/'actual.patch.txt'),'scopeLimitations':['No product, kernel, fixture, input, threshold, SDK, compiler flag or CMake edits.','Linux GCC13 Werror verification awaits fresh public CI; MSVC passing is not that verification.','Earlier local verification remains historical and does not retroactively hash this new test.','No fault injection or new mathematical acceptance claimed.']}
save('acceptance.json',accept)
print(json.dumps({k:accept[k] for k in ['status','groups','finiteFixtures','new','fixtures','sourceStable','msvcWarnings']}))
