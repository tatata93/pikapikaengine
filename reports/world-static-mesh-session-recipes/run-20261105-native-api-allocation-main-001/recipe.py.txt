"""Fresh main normal Release fault executable; Debug is registration-only."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfocam1'
OUT=HERE/'run-20261105-native-api-allocation-main-001'
API='pikapika_world_static_mesh_session_api_tests'
TARGET='pikapika_world_static_mesh_session_api_allocation_tests'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh main allocation build/output');OUT.mkdir();commands=[]
    paths=[p for folder in ['core','engine','samples'] for p in (ROOT/folder).rglob('*') if p.is_file()]+[ROOT/'CMakeLists.txt',ROOT/'tests/world_static_mesh_session_api_allocation_tests.cpp',Path(__file__).resolve()]
    before=[stamp(p) for p in paths];write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    def run(name,argv,timeout=180):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=timeout);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);row=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(row);write(OUT/(name+'.command.json'),row);print(json.dumps(row),flush=True)
        if p.returncode:print(p.stdout.decode(errors='replace')[-5000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        run('configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON']);inventories={}
        for cfg,count in [('Release',56),('Debug',54)]:
            listing=json.loads(run(cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));prior=json.loads((HERE/'run-20261105-native-api-main-001'/(cfg+'-inventory.stdout.txt')).read_bytes());names={t['name'] for t in listing['tests']};need(len(names)==count and names=={t['name'] for t in prior['tests']}|({'world_static_mesh_session_api_allocation'} if cfg=='Release' else set()),'Exact Release-only new allocation inventory');inventories[cfg]=count
        profiles=list((ROOT/'build/wfocm1').glob('world-*.json'));need(len(profiles)==20 and all((BUILD/p.name).read_bytes()==p.read_bytes() for p in profiles),'All old20 profile documents raw identical')
        run('Release-build',['cmake','--build',BUILD,'--config','Release','--target',TARGET,API,'--parallel','2'],900)
        run('Release-two-ctests',['ctest','--test-dir',BUILD,'-C','Release','-R','^world_static_mesh_session_api(_allocation)?$','--output-on-failure'])
        raw=run('actual-fault',[BUILD/'Release'/(TARGET+'.exe'),'--run']);(OUT/'actual-allocation.json').write_bytes(raw);need(raw==(HERE/'run-20261105-native-api-allocation-002/actual-allocation.json').read_bytes(),'Whole actual allocation evidence equal to isolated normal executable')
        api=run('api-nine-fixtures',[BUILD/'Release'/(API+'.exe'),'--fixtures']);(OUT/'Release-api.json').write_bytes(api);need(api==(HERE/'run-20261105-native-api-main-001/Release-api.json').read_bytes(),'Whole nine API fixtures unchanged')
        ref=json.loads(run('api-independent-reference',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session-api.py',OUT/'Release-api.json']));need(ref['status']=='PASS' and ref['mappedFloatBitValues']==1254,'Actual unchanged independent reference')
        log=next((BUILD/(TARGET+'.dir')/'Release').rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16');need(len(re.findall(r'^\^',text,re.M))==1,'One actual new allocation harness TU')
        for flag in ['/W4','/WX','/fp:strict','/GL-','/MD']:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual normal flag '+flag)
        need(re.search(r'(?:^|\s)/D\s*(?:"NDEBUG"|NDEBUG)(?=\s|$)',text,re.I),'Actual normal NDEBUG');(OUT/'allocation-compile.tlog.txt').write_bytes(log.read_bytes())
        d=json.loads(raw);need(d['contextAllocationFailures']==1 and d['operationAllocations']==[14,3,3,2] and len(d['rows'])==22 and d['actualBusyReentryChecks']==20,'Actual Native observed finite fault inventory')
        result.update(status='FINITE_NATIVE_MAIN_C_API_ALLOCATION_PASS',inventories=inventories,old20ProfilesRawExact=True,actualReleaseCTests=2,old54TestsRerun=False,actualContextFailurePositions=1,actualOperationFailurePositions=[14,3,3,2],actualOperationFailures=22,actualBusyReentryChecks=20,actualGetterAllocations=0,allRawExactToIsolated=True,normalReleaseOnly=True,DebugExecuted=False,actualGNUFaultExecuted=False,actualSanitizedFaultExecutable=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in paths];write(OUT/'after.json',after);result.update(sourceStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_MAIN_C_API_ALLOCATION_PASS')
if __name__=='__main__':raise SystemExit(main())
