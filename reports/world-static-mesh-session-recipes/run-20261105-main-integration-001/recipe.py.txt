"""Fresh main-CMake owner acceptance with genuine Release and Debug dependencies.

Finite MSVC source/command provenance, complete77 reference/raw regression,
actual allocation injection and parent refusal. No GNU/SDK/machine proof.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import runpy
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
RECIPE=Path(__file__).resolve()
OWNER='pikapika_world_static_mesh_session'
PARENT='pikapika_world_static_mesh_flight_controlled_scheduler'
MODULE=ROOT/'cmake/PikapikaWorldStaticMeshSessionConfiguration.cmake'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    raw=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write(p,data):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',default='build/wfos1');parser.add_argument('--name',default='run-20261105-main-integration-001');args=parser.parse_args()
    need(sys.platform=='win32','Actual MSVC Windows only');build=(ROOT/args.build).resolve();out=RECIPE.parent/args.name
    need(build.parent==ROOT/'build' and re.fullmatch('wfos[1-9][0-9]*',build.name),'Fresh short build/wfosN')
    need(re.fullmatch('run-[A-Za-z0-9_.-]{1,70}',args.name) and not build.exists() and not out.exists(),'Never overwrite build/evidence')
    build.mkdir();out.mkdir();sys.dont_write_bytecode=True
    (out/'recipe.py.txt').write_bytes(RECIPE.read_bytes());write(out/'invocation.json',{'argv':sys.argv,'cwd':str(Path.cwd())})
    old=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'),run_name='readonly_paths')
    watched=set(old['protected']())|{RECIPE,MODULE,ROOT/'CMakeLists.txt'}
    watched.update(ROOT/p for p in ['core/include/pikapika/world_static_mesh_session.hpp','core/src/world_static_mesh_session.cpp','tests/world_static_mesh_session_tests.cpp','tests/world_static_mesh_session_fixtures.cpp','tests/world_static_mesh_session_allocation_tests.cpp','tests/world_static_mesh_flight_controlled_scheduler_fixture_support.hpp','tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp','scripts/verify-world-static-mesh-session.py','scripts/verify-world-static-mesh-flight-controlled-scheduler.py','tests/world_static_mesh_session_reference_tests.py'])
    for name in ['wfcqm2','wfo1','wfor2','wfof3','wfoa1']:
        watched.update(p for p in (ROOT/'build'/name).rglob('*') if p.is_file() and (p.suffix in {'.exe','.lib','.map','.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith('world-flight-')))
    watched=sorted(watched);identities=lambda:{p.relative_to(ROOT).as_posix():stamp(p) for p in watched};before=identities();write(out/'before.json',before)
    for p in [MODULE,ROOT/'CMakeLists.txt']:(out/(p.name+'.txt')).write_bytes(p.read_bytes())
    commands=[]
    def run(name,argv,timeout=600):
        started=time.monotonic();row={'name':name,'argv':list(map(str,argv)),'cwd':str(ROOT)}
        try:
            done=subprocess.run(row['argv'],cwd=ROOT,capture_output=True,timeout=timeout);code,stdout,stderr=done.returncode,done.stdout,done.stderr
        except BaseException as error:code,stdout,stderr=None,getattr(error,'stdout',None) or b'',(getattr(error,'stderr',None) or b'')+str(error).encode()
        (out/(name+'.stdout.txt')).write_bytes(stdout);(out/(name+'.stderr.txt')).write_bytes(stderr)
        row.update(exitCode=code,seconds=time.monotonic()-started,stdout=stamp(out/(name+'.stdout.txt')),stderr=stamp(out/(name+'.stderr.txt')))
        commands.append(row);write(out/(name+'.command.json'),row);print(json.dumps({k:row[k] for k in ['name','exitCode','seconds']}),flush=True)
        if code!=0:print(stdout.decode(errors='replace')[-12000:]);print(stderr.decode(errors='replace')[-12000:])
        need(code==0,'Actual command failed: '+name);return stdout
    result={'schema':1,'status':'FAIL','scope':__doc__}
    try:
        run('01-configure',['cmake','-S',ROOT,'-B',build,'-A','x64','-DBUILD_TESTING=ON'])
        for stem in ['world-flight-binding','world-flight-scheduler-binding','world-flight-controlled-tick-binding','world-flight-controlled-scheduler-binding']:
            for cfg in ['Release','Debug']:
                name=stem+'-'+cfg+'.json';need((build/name).read_bytes()==(ROOT/'build/wfcqm2'/name).read_bytes(),'All four old identities raw exact: '+name)
        profiles={}
        for cfg in ['Release','Debug']:
            p=build/('world-owned-session-configuration-'+cfg+'.json');d=json.loads(p.read_bytes());m=d['identityMaterial']
            need(hashlib.sha256(json.dumps(m,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==d['configurationId'],'Independent configured ID recomputation')
            need(d['configuredSource'] is True and d['artifactAuditComplete'] is False and m['helperSha256']==stamp(MODULE)['sha256'],'Configured source only, not artifact certificate')
            need(m['numericalParentProfile']==int(cfg=='Release') and m['numericalParentBuildId']==json.loads((build/('world-flight-controlled-scheduler-binding-'+cfg+'.json')).read_bytes())['buildId'],'Actual parent identity/profile')
            need(len(m['sources'])==2,'Separate two-source owner material')
            for source in m['sources']:need(source['sha256']==stamp(ROOT/source['path'])['sha256'],'Actual owner source hash')
            profiles[cfg]=d;(out/p.name).write_bytes(p.read_bytes())
        inventory=json.loads(run('02-inventory',['ctest','--test-dir',build,'-C','Release','--show-only=json-v1']))
        old_names=set(re.findall(r'^\s*add_test\(\[=\[([^\]]+)\]=\]',(ROOT/'build/wfcqm2/CTestTestfile.cmake').read_text(),re.M))
        names={x['name'] for x in inventory['tests']};need(len(old_names)==50 and len(names)==52 and names==old_names|{'world_static_mesh_session','world_static_mesh_session_allocation'},'Exactly old50 plus2 meaningful owner tests')
        run('03-release-build',['cmake','--build',build,'--config','Release','--parallel','2'],1800)
        run('04-directed',[build/'Release'/(OWNER+'_tests.exe'),'--run'])
        raw=run('05-owner-full',[build/'Release'/(OWNER+'_fixtures.exe'),'--fixtures']);full=out/'owner-full.json';full.write_bytes(raw)
        need(raw==(RECIPE.parent/'run-20261105-full-003/owner-full.json').read_bytes(),'Entire77 owner history same-ABI raw exact')
        reference=json.loads(run('06-reference',[sys.executable,'-B','-X','utf8',ROOT/'scripts/verify-world-static-mesh-session.py',full]))
        need(reference['rows']==77 and reference['pump']['controlled']['child']['guard']['childCalls']==54,'Independent77 /54 math children')
        run('07-controls',[sys.executable,'-B','-X','utf8',ROOT/'tests/world_static_mesh_session_reference_tests.py',full,'--output',out/'controls'])
        controls=json.loads((out/'controls/verification.json').read_bytes());need(controls['status']=='PASS' and controls['copiedRejectionControls']==65,'Actual full reference controls')
        allocation=run('08-allocation',[build/'Release'/(OWNER+'_allocation_tests.exe')]);(out/'allocation-results.json').write_bytes(allocation)
        need(allocation==(RECIPE.parent/'run-20261105-allocation-001/allocation-results.json').read_bytes(),'Actual23 failures/5 reentry raw exact')
        raw=run('09-old-full',[build/'Release'/(PARENT+'_fixtures.exe'),'--fixtures']);(out/'controlled-scheduler-full.json').write_bytes(raw)
        need(raw==(RECIPE.parent/'run-20261105-bridge-002/controlled-scheduler-full.json').read_bytes(),'Entire old84 same-ABI raw exact')
        run('10-ctest',['ctest','--test-dir',build,'-C','Release','--output-on-failure'],900)
        debug_targets=[OWNER+'_tests',PARENT+'_tests','pikapika_world_static_mesh_flight_controlled_tick_tests','pikapika_world_static_mesh_flight_scheduler_tests','pikapika_world_static_mesh_flight_advance_tests','pikapika_world_static_mesh_flight_guard_tests']
        run('11-debug-build',['cmake','--build',build,'--config','Debug','--target',*debug_targets,'--parallel','2'],1200)
        for i,target in enumerate(debug_targets):run(str(12+i)+'-debug-refusal',[build/'Debug'/(target+'.exe'),'--unsupported-profile'])
        provenance=[]
        for cfg,targets in [('Release',[OWNER,'pikapika_session_fixture_support',OWNER+'_tests',OWNER+'_fixtures',OWNER+'_allocation_tests']),('Debug',[OWNER,'pikapika_session_fixture_support',OWNER+'_tests'])]:
            for target in targets:
                logs=list((build/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));need(len(logs)==1,'One actual compiler log: '+target+'/'+cfg)
                text=logs[0].read_bytes().decode('utf16');chunks=re.findall(r'^\^([^\r\n]+)\r?\n([^\r\n]+)',text,re.M);need(chunks,'Actual compile entries')
                for source,command in chunks:
                    for flag in ['/W4','/permissive-','/fp:strict','/GL-']:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',command,re.I),'Actual owner strict flag '+flag)
                    if target!='pikapika_session_fixture_support':need(re.search(r'(?:^|\s)/WX(?=\s|$)',command,re.I),'Actual new TU warnings fatal')
                    if cfg=='Debug':need('/MDd' in command and '_ITERATOR_DEBUG_LEVEL=0' not in command and 'NDEBUG' not in command,'Genuine Debug ABI, no Release import workaround')
                copy=out/('compile-'+str(len(provenance))+'.tlog.txt');copy.write_bytes(logs[0].read_bytes());provenance.append({'target':target,'configuration':cfg,'entries':len(chunks),'copy':stamp(copy)})
        for target in ['pikapika_core',PARENT,'pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler']:
            logs=list((build/(target+'.dir/Debug')).rglob('CL.command.1.tlog'));need(len(logs)==1,'Real Debug numerical dependency '+target);raw=logs[0].read_bytes();text=raw.decode('utf16')
            need('/MDd' in text and '_ITERATOR_DEBUG_LEVEL=0' not in text and 'NDEBUG' not in text,'Real Debug numerical ABI');(out/(target+'-debug.tlog.txt')).write_bytes(raw)
        result.update(status='FINITE_MAIN_OWNED_SESSION_INTEGRATION_PASS',profiles=profiles,allFourParentProfilesRawExact=True,fullOwnerRawExact=True,old84RawExact=True,reference=reference,copiedRejectionControls=65,actualAllocationFailures=23,actualBusyReentryChecks=5,ctestPassed=52,actualDebugOwnerAndAllNumericalDependenciesBuilt=True,actualDebugRefusals=len(debug_targets),compileProvenance=provenance,actualGNUExecuted=False,actualSanitizerExecuted=False,SDKChanged=False,productionOwnerSourcesChanged=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(out/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(watched),commands=commands)
        if before!=after:result['status']='FAIL'
        write(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}),flush=True)
    return 0 if result['status']=='FINITE_MAIN_OWNED_SESSION_INTEGRATION_PASS' else 1


if __name__=='__main__':raise SystemExit(main())
