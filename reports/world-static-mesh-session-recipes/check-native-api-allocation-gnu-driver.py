"""Copied actual Native fault-record controls; real Windows GNU refusal only."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'run-20261105-native-api-allocation-gnu-driver-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(sys.platform=='win32' and not OUT.exists(),'Fresh actual Windows check');OUT.mkdir();driver=HERE/'verify-native-api-allocation-gnu.py';ast.parse(driver.read_text(encoding='utf8'));sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location('api_fault_gnu_controls',driver);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    paths=[driver,Path(__file__).resolve(),ROOT/'tests/world_static_mesh_session_api_allocation_tests.cpp',ROOT/'CMakeLists.txt',ROOT/'.github/workflows/verify.yml'];before=[stamp(p) for p in paths];write(OUT/'before.json',before)
    actual=HERE/'run-20261105-native-api-allocation-002/actual-allocation.json';d=json.loads(actual.read_bytes());observed=m.observe(d);need(observed['actualOperationFailures']==22,'Actual earlier Native observation only');negative=[]
    def reject(name,mutate):
        value=copy.deepcopy(d);mutate(value);write(OUT/(name+'.rejected-input.json'),value)
        try:m.observe(value)
        except (ValueError,KeyError,TypeError):negative.append(name);return
        raise ValueError('Copied tamper passed '+name)
    reject('missing-row',lambda x:x['rows'].pop());reject('duplicate-row',lambda x:x['rows'].__setitem__(1,copy.deepcopy(x['rows'][0])));reject('bool-index',lambda x:x['rows'][0].__setitem__('failAfter',False));reject('attempt-mismatch',lambda x:x['rows'][-1].__setitem__('actualAttempts',999));reject('cache-retention',lambda x:x['rows'][0].__setitem__('wholePreviousCacheRetained',False));reject('owner-retention',lambda x:x['rows'][0].__setitem__('activeOwnerRetained',False));reject('recovery',lambda x:x['rows'][0].__setitem__('recoveryValid',False));reject('wrong-outer-count',lambda x:x.__setitem__('allocatorCallbackOuterOperations',3));reject('wrong-busy-count',lambda x:x.__setitem__('actualBusyReentryChecks',19));reject('uncaptured-input',lambda x:x.__setitem__('stageInputCapturedBeforeAllocation',False));reject('allocating-getter',lambda x:x.__setitem__('cachedGetterAllocations',1));reject('bool-context-count',lambda x:x.__setitem__('contextAllocationFailures',True));reject('not-normal-only',lambda x:x.__setitem__('normalOnly',False));reject('unknown-field',lambda x:x.__setitem__('hidden',0))
    refusal=ROOT/'build/public-checks/native-api-allocation-gnu-refusal-001';need(not refusal.exists(),'Fresh refusal output');argv=[sys.executable,'-B','-X','utf8',str(driver),'--output',str(refusal)];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60);(OUT/'refusal.stdout.txt').write_bytes(p.stdout);(OUT/'refusal.stderr.txt').write_bytes(p.stderr);write(OUT/'refusal.command.json',dict(argv=argv,exitCode=p.returncode));r=json.loads((refusal/'verification.json').read_bytes());need(p.returncode==1 and r['status']=='FAIL' and 'Actual Linux GNU13 required' in r['error'] and r['actualGNUFaultExecuted'] is False and r['commands']==[] and r['sourceStable'],'Actual zero-command Windows refusal')
    for f in refusal.iterdir():
        if f.is_file():(OUT/f.name).write_bytes(f.read_bytes())
    need(before==[stamp(p) for p in paths],'Actual source stable');write(OUT/'after.json',[stamp(p) for p in paths]);write(OUT/'local-verification.json',dict(status='PASS',actualNativeObservation=stamp(actual),copiedRecordRejections=negative,actualWindowsRefusal=True,actualGNUFaultExecuted=False,actualBuildCommands=0,sourceStable=True,scope=__doc__));print(json.dumps(dict(status='PASS',copiedRecordRejections=len(negative),actualGNUFaultExecuted=False)))
if __name__=='__main__':main()
