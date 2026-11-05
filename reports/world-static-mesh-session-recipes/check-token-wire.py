"""Fresh main configure, one integer-wire target and actual Debug/Release fixtures.

Previous52 tests are inventory-only; numerical libraries are not rebuilt here.
"""
from pathlib import Path
import hashlib
import json
import re
import runpy
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfow1'
OUT=HERE/'run-20261105-token-wire-001'
TARGET='pikapika_world_static_mesh_session_wire_tests'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    raw=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write(p,data):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh actual MSVC main configuration only');BUILD.mkdir();OUT.mkdir();sys.dont_write_bytecode=True
    old=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'),run_name='readonly_old_paths')
    watched=set(old['protected']())|{Path(__file__).resolve(),ROOT/'core/include/pikapika/world_static_mesh_session_wire.hpp',ROOT/'tests/world_static_mesh_session_wire_tests.cpp',ROOT/'scripts/verify-world-static-mesh-session-wire.py'}
    for name in ['wfos1','wfot1','wfot2']:
        watched.update(p for p in (ROOT/'build'/name).rglob('*') if p.is_file() and (p.suffix in {'.exe','.lib','.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith(('world-flight-','world-owned-'))))
    watched=sorted(watched);identities=lambda:{p.relative_to(ROOT).as_posix():stamp(p) for p in watched};before=identities();write(OUT/'before.json',before)
    (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());commands=[]
    def run(name,argv):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        row={'name':name,'argv':list(map(str,argv)),'exitCode':p.returncode,'seconds':time.monotonic()-start};commands.append(row);write(OUT/(name+'.command.json'),row);print(json.dumps(row),flush=True)
        if p.returncode:print(p.stdout.decode(errors='replace')[-8000:]);print(p.stderr.decode(errors='replace')[-8000:])
        need(p.returncode==0,'Actual command failed: '+name);return p.stdout
    result={'schema':1,'status':'FAIL','scope':__doc__}
    try:
        run('01-configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON'])
        inventories={}
        for cfg,count in [('Release',53),('Debug',52)]:
            data=json.loads(run('02-'+cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));names={r['name'] for r in data['tests']}
            prior=json.loads((HERE/'run-20261105-configuration-gate-002'/('03-'+cfg+'-inventory.stdout.txt')).read_bytes());need(len(names)==count and names=={r['name'] for r in prior['tests']}|{'world_static_mesh_session_wire'},'Old registrations exact plus independent wire test');inventories[cfg]=count
        for stem in ['world-flight-binding','world-flight-scheduler-binding','world-flight-controlled-tick-binding','world-flight-controlled-scheduler-binding','world-owned-session-configuration']:
            for cfg in ['Release','Debug','MinSizeRel','RelWithDebInfo']:
                name=stem+'-'+cfg+'.json';need((BUILD/name).read_bytes()==(ROOT/'build/wfot2'/name).read_bytes(),'All20 numerical/owner configuration documents raw exact')
        captures=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD,'--config',cfg,'--target',TARGET,'--parallel','2'])
            run(cfg+'-ctest',['ctest','--test-dir',BUILD,'-C',cfg,'-R','^world_static_mesh_session_wire$','--output-on-failure'])
            raw=run(cfg+'-fixtures',[BUILD/cfg/(TARGET+'.exe'),'--fixtures']);p=OUT/(cfg+'-wire.json');p.write_bytes(raw);captures.append(raw)
            ref=json.loads(run(cfg+'-independent',[sys.executable,'-B','-X','utf8',ROOT/'scripts/verify-world-static-mesh-session-wire.py',p]));need(ref['status']=='PASS' and ref['rows']==77 and ref['successful']==50 and ref['refused']==27,'Actual independent wire integer reference')
            log=next((BUILD/(TARGET+'.dir')/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16');need(len(re.findall(r'^\^',text,re.M))==1,'One actual integer TU per configuration')
            for flag in ['/W4','/WX','/permissive-','/GL-']:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual strict diagnostics/no-LTO')
            need(re.search(r'(?:^|\s)'+('/MDd' if cfg=='Debug' else '/MD')+r'(?=\s|$)',text),'Actual separate runtime configuration');(OUT/(cfg+'-compile.tlog.txt')).write_bytes(log.read_bytes())
        need(captures[0]==captures[1],'Integer observations raw exact across real Release/Debug')
        optimized=subprocess.run([sys.executable,'-O',str(ROOT/'scripts/verify-world-static-mesh-session-wire.py'),str(OUT/'Release-wire.json')],cwd=ROOT,capture_output=True,timeout=30)
        (OUT/'optimized.stdout.txt').write_bytes(optimized.stdout);(OUT/'optimized.stderr.txt').write_bytes(optimized.stderr);need(optimized.returncode!=0 and b'normal Python' in optimized.stderr,'Actual -O process refused')
        result.update(status='FINITE_NATIVE_INTEGER_TOKEN_WIRE_PASS',inventories=inventories,actualNewCTestPerConfiguration=1,old52TestsRerun=False,old20ConfigurationDocumentsRawExact=True,integerRowsPerBuild=77,successfulRows=50,refusedRows=27,knownIntegerVectors=24,actualOptimizedPythonRefused=True,realDebugReleaseRawExact=True,actualGNUExecuted=False,RegistryOrNumericalKernelChanged=False,CABIOrJSOrWASMChanged=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(OUT/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(watched),commands=commands)
        if before!=after:result['status']='FAIL'
        write(OUT/'result.json',result)
    print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}),flush=True);return int(result['status']!='FINITE_NATIVE_INTEGER_TOKEN_WIRE_PASS')


if __name__=='__main__':raise SystemExit(main())
