"""Fresh main integration; old numerical profiles/dependencies are not unlocked."""
from pathlib import Path
import copy,hashlib,importlib.util,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfocm1'
OUT=HERE/'run-20261105-native-api-main-001'
TARGET='pikapika_world_static_mesh_session_api_tests'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh main build/output');OUT.mkdir();commands=[]
    protected=[p for folder in ['core','engine','samples'] for p in (ROOT/folder).rglob('*') if p.is_file()]
    protected+=[ROOT/'CMakeLists.txt',Path(__file__).resolve(),ROOT/'scripts/verify-world-static-mesh-session-api.py']
    protected+=list((ROOT/'build/wfop1').glob('*.json'))
    before=[stamp(p) for p in protected];write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    def run(name,argv,timeout=180,ok=True):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=timeout);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        r=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(r);write(OUT/(name+'.command.json'),r);print(json.dumps(r),flush=True)
        if ok and p.returncode:print(p.stdout.decode(errors='replace')[-5000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0 if ok else p.returncode!=0,'Actual command '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        run('configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON']);inventories={}
        for cfg,count in [('Release',55),('Debug',54)]:
            listing=json.loads(run(cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));prior=json.loads((HERE/'run-20261105-source-wire-producer-001'/('02-'+cfg+'-inventory.stdout.txt')).read_bytes())
            names={t['name'] for t in listing['tests']};need(len(names)==count and names=={t['name'] for t in prior['tests']}|{'world_static_mesh_session_api'},'Exactly old inventory plus C API test');inventories[cfg]=count
        profiles=list((ROOT/'build/wfop1').glob('world-*.json'));need(len(profiles)==20,'Exactly20 old profile documents')
        for p in profiles:need((BUILD/p.name).read_bytes()==p.read_bytes(),'Old profile raw exact '+p.name)
        captures=[];references=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD,'--config',cfg,'--target',TARGET,'--parallel','2'],900)
            run(cfg+'-ctest',['ctest','--test-dir',BUILD,'-C',cfg,'-R','^world_static_mesh_session_api$','--output-on-failure'])
            raw=run(cfg+'-fixtures',[BUILD/cfg/(TARGET+'.exe'),'--fixtures']);p=OUT/(cfg+'-api.json');p.write_bytes(raw);captures.append(raw)
            need(raw==(HERE/'run-20261105-native-api-001'/(cfg+'-api.json')).read_bytes(),'Whole raw equality to real isolated prototype')
            references.append(json.loads(run(cfg+'-reference',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session-api.py',p])))
            for target in ['pikapika_world_static_mesh_session_api',TARGET]:
                log=next((BUILD/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));rawlog=log.read_bytes();text=rawlog.decode('utf16')
                for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual strict new compiler '+flag)
                need(len(re.findall(r'^\^',text,re.M))==(2 if target==TARGET else 1),'Exactly actual new translation units')
                if target==TARGET:need('/TC' in text and '/TP' in text,'Actual C and C++ compiler languages')
                (OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(rawlog)
        need(captures[0]==captures[1],'Whole raw R/Debug equality')
        path=ROOT/'scripts/verify-world-static-mesh-session-api.py';spec=importlib.util.spec_from_file_location('api_reference',path);ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
        original=json.loads(captures[0]);controls=[]
        def reject(name,mutate):
            d=copy.deepcopy(original);mutate(d);write(OUT/(name+'.rejected-input.json'),d)
            try:ref.verify(d)
            except (ValueError,KeyError,TypeError):controls.append(name);return
            raise ValueError('Copied tamper passed '+name)
        reject('negative-zero',lambda d:d['rows'][0]['readFloatBits'].__setitem__(0,0))
        reject('full64-high-word',lambda d:d['rows'][8]['readWords'].__setitem__(6,0))
        reject('dropped-float',lambda d:d['rows'][8]['readFloatBits'].pop())
        reject('body-order',lambda d:d['rows'][8]['readWords'].__setitem__(slice(5,11),d['rows'][8]['readWords'][8:11]+d['rows'][8]['readWords'][5:8]))
        reject('bool-scalar',lambda d:d['rows'][0].__setitem__('bodies',False))
        reject('bool-word',lambda d:d['rows'][0]['readWords'].__setitem__(0,False))
        reject('generation',lambda d:d['rows'][0]['token'].__setitem__(1,2))
        reject('sequence',lambda d:d['rows'][0]['sequence'].__setitem__(0,1))
        reject('missing-row',lambda d:d['rows'].pop())
        reject('unknown-field',lambda d:d['rows'][0].__setitem__('hidden',0))
        reject('both-input-read',lambda d:[d['rows'][0][k].__setitem__(1,0) for k in ['inputFloatBits','readFloatBits']])
        reject('wrong-maximum',lambda d:d['rows'][8].__setitem__('planes',15))
        optimized=run('optimized-refusal',[sys.executable,'-O',path,OUT/'Release-api.json'],ok=False);need(b'normal Python' in (OUT/'optimized-refusal.stderr.txt').read_bytes(),'Actual optimized refusal')
        result.update(status='FINITE_NATIVE_MAIN_PLAIN_SESSION_C_API_PASS',inventories=inventories,old20ProfileDocumentsRawExact=True,selectedNewCTestPerConfiguration=1,old54TestsRerun=False,newProductionTUsPerBuild=1,newHarnessTUsPerBuild=2,wholeRawEqualToIsolatedAndAcrossBuilds=True,actualReferences=references,copiedRejections=controls,actualOptimizedPythonRefused=True,actualCAndCxxCallers=True,actualLifecycleAssertions=True,actualGNUExecuted=False,pumpOrWASMImplemented=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in protected];write(OUT/'after.json',after);result.update(sourceStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_MAIN_PLAIN_SESSION_C_API_PASS')
if __name__=='__main__':raise SystemExit(main())
