"""Fresh main packet-data target only; no old model/core targets rebuilt."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfopkm1'
OUT=HERE/'run-20261105-packet-wire-main-001'
LIB='pikapika_world_static_mesh_session_packet_wire'
TEST=LIB+'_tests'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh main packet output/build');OUT.mkdir();commands=[]
    paths=[p for folder in ['core','engine','samples'] for p in (ROOT/folder).rglob('*') if p.is_file()]+[ROOT/'CMakeLists.txt',ROOT/'tests/world_static_mesh_session_packet_wire_tests.cpp',Path(__file__).resolve()];before=[stamp(p) for p in paths];write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    def run(name,argv):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);r=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(r);write(OUT/(name+'.command.json'),r)
        if p.returncode:print(p.stdout.decode(errors='replace')[-5000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        run('configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON']);inventory={}
        for cfg,count in [('Release',57),('Debug',55)]:
            listing=json.loads(run(cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));old=json.loads((HERE/'run-20261105-native-api-allocation-main-001'/(cfg+'-inventory.stdout.txt')).read_bytes());names={r['name'] for r in listing['tests']};need(len(names)==count and names=={r['name'] for r in old['tests']}|{'world_static_mesh_session_packet_wire'},'Old inventory plus packet test only');inventory[cfg]=count
        profiles=list((ROOT/'build/wfocam1').glob('world-*.json'));need(len(profiles)==20 and all((BUILD/p.name).read_bytes()==p.read_bytes() for p in profiles),'Old20 profiles raw exact')
        captures=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD,'--config',cfg,'--target',TEST,'--parallel','2']);run(cfg+'-ctest',['ctest','--test-dir',BUILD,'-C',cfg,'-R','^world_static_mesh_session_packet_wire$','--output-on-failure']);raw=run(cfg+'-fixtures',[BUILD/cfg/(TEST+'.exe'),'--fixtures']);p=OUT/(cfg+'-packet-wire.json');p.write_bytes(raw);need(raw==(HERE/'run-20261105-packet-wire-producer-002'/(cfg+'-packet-wire.json')).read_bytes(),'Whole24 raw exact to isolated actual producer');captures.append(raw)
            ref=json.loads(run(cfg+'-independent-reference',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session-packet-wire.py',p]));need(ref['status']=='PASS' and ref['mappedFloatBitValues']==492,'Actual pinned full reference')
            for target in [LIB,TEST]:
                log=next((BUILD/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16');need(len(re.findall(r'^\^',text,re.M))==1,'One actual TU per new target')
                for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual new strict flag '+flag)
                (OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(log.read_bytes())
        need(captures[0]==captures[1],'Whole raw exact across R/Debug')
        need(not any((BUILD/'pikapika_core.dir').rglob('*.obj')) and not list(BUILD.glob('**/pikapika_core.lib')),'Actual target did not build/link old model core')
        result.update(status='FINITE_NATIVE_MAIN_PACKET_WIRE_PASS',inventories=inventory,old20ProfilesRawExact=True,selectedNewCTestPerConfiguration=1,old56TestsRerun=False,wholeRawExactToIsolatedAndAcrossBuilds=True,independentReferenceAccepted=True,actualFourFpuModesObservedAndRetained=True,modelOrCAPIOrWASMCalled=False,coreModelTargetsBuilt=False,actualGNUExecuted=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in paths];write(OUT/'after.json',after);result.update(sourceStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_MAIN_PACKET_WIRE_PASS')
if __name__=='__main__':raise SystemExit(main())
