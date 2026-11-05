"""Actual isolated owner global-new failure and allocator reentry injection.

Unchanged accepted owner library; one test executable overrides scalar/array new.
No OS OOM, aligned/CRT interception, post-child physics fault or GNU/SDK claim.
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
TEST=ROOT/'tests/world_static_mesh_session_allocation_tests.cpp'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    raw=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write(p,value):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',default='build/wfoa1');parser.add_argument('--name',default='run-20261105-allocation-001');args=parser.parse_args()
    need(sys.platform=='win32','Actual MSVC only');build=(ROOT/args.build).resolve();out=RECIPE.parent/args.name
    need(build.parent==ROOT/'build' and re.fullmatch('wfoa[1-9][0-9]*',build.name),'Fresh short build/wfoaN');need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}',args.name),'Fresh report component');need(not build.exists() and not out.exists(),'Never overwrite build/evidence')
    build.mkdir();out.mkdir();(out/'recipe.py.txt').write_bytes(RECIPE.read_bytes());(out/'allocation-test.cpp.txt').write_bytes(TEST.read_bytes());sys.dont_write_bytecode=True
    old=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'),run_name='readonly_paths');helper=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-advance-recipes/check-configured-prototype.py'),run_name='readonly_quote');quote=helper['cmake_path']
    base=ROOT/'build/wfcqm2';libs=[ROOT/'build/wfo1/configured/Release/owner_kernel.lib',ROOT/'build/wfor2/configured/Release/codec_library.lib',*[base/'Release'/(n+'.lib') for n in ['pikapika_world_static_mesh_flight_controlled_scheduler','pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler','pikapika_core']]]
    objects=sorted(p for p in (base/'pikapika_world_static_mesh_flight_controlled_scheduler_tests.dir/Release').glob('*.obj') if p.name!='world_static_mesh_flight_controlled_scheduler_tests.obj');need(len(objects)==9 and all(p.is_file() for p in libs),'Actual immutable6 libraries and9 serializer objects')
    freeze=json.loads((RECIPE.parent/'freeze.json').read_bytes())
    for row in freeze['sources']:
        if row['path'].startswith(('core/','tests/')):need(stamp(ROOT/row['path'])==row,'Exactly accepted owner3 sources; no fault hooks in production')
    watched=set(old['protected']())|{RECIPE,TEST,*libs,*objects,RECIPE.parent/'freeze.json'}
    for name in ['wfo1','wfor2','wfof3','wfcqm2']:
        watched.update(p for p in (ROOT/'build'/name).rglob('*') if p.is_file() and (p.suffix in {'.exe','.lib','.map','.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith('world-flight-')))
    watched=sorted(watched);identities=lambda:{p.relative_to(ROOT).as_posix():stamp(p) for p in watched};before=identities();write(out/'before.json',before)
    project=build/'project';project.mkdir();lines=['cmake_minimum_required(VERSION 3.24)','project(ActualOwnerAllocationInjection LANGUAGES CXX)','set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)','set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL)','set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)',
        'if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR CMAKE_CROSSCOMPILING)','message(FATAL_ERROR "Actual matching MSVC19.51 x64 required")','endif()',
        'file(WRITE "${CMAKE_BINARY_DIR}/actual-compiler.txt" "${CMAKE_CXX_COMPILER}\\n${CMAKE_CXX_COMPILER_VERSION}\\n${CMAKE_SYSTEM_PROCESSOR}\\n")',
        'add_executable(owner_allocation '+quote(TEST)+' '+' '.join(quote(p) for p in objects)+')','target_include_directories(owner_allocation PRIVATE '+quote(ROOT/'core/include')+' '+quote(ROOT/'tests')+')','target_compile_options(owner_allocation PRIVATE /W4 /WX /permissive- /fp:strict /GL-)',
        'target_link_libraries(owner_allocation PRIVATE '+' '.join(quote(p) for p in libs)+')','target_link_options(owner_allocation PRIVATE /LTCG:OFF /OPT:NOREF /OPT:NOICF "/MAP:$<TARGET_FILE_DIR:owner_allocation>/owner_allocation.map")']
    (project/'CMakeLists.txt').write_text('\n'.join(lines)+'\n',encoding='utf8',newline='\n');(out/'project.cmake.txt').write_bytes((project/'CMakeLists.txt').read_bytes());commands=[]
    def run(name,argv):
        started=time.monotonic();done=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=600);(out/(name+'.stdout.txt')).write_bytes(done.stdout);(out/(name+'.stderr.txt')).write_bytes(done.stderr)
        row={'name':name,'argv':list(map(str,argv)),'cwd':str(ROOT),'exitCode':done.returncode,'seconds':time.monotonic()-started,'sourceStable':before==identities()};commands.append(row);write(out/(name+'.command.json'),row);print(json.dumps({k:row[k] for k in ['name','exitCode','seconds','sourceStable']}),flush=True)
        if done.returncode:print(done.stdout.decode(errors='replace')[-12000:]);print(done.stderr.decode(errors='replace')[-12000:])
        need(done.returncode==0 and row['sourceStable'],'Actual command failed: '+name);return done.stdout
    result={'schema':1,'status':'FAIL','scope':__doc__,'actualGNUExecuted':False,'productionOwnerChanged':False,'actualOSOutOfMemory':False,'actualPostChildPhysicsFaultInjected':False}
    try:
        run('01-configure',['cmake','-S',project,'-B',build/'configured','-A','x64'])
        compiler=(build/'configured/actual-compiler.txt').read_text().replace('\\n','\n').splitlines();expected=json.loads((base/'world-flight-binding-Release.json').read_bytes())['compiler'];need(Path(compiler[0]).resolve()==Path(expected['path']).resolve() and compiler[1]==expected['version'] and compiler[2]=='AMD64','Actual matching imported ABI compiler')
        run('02-release-build',['cmake','--build',build/'configured','--config','Release','--parallel','2'])
        raw=run('03-actual-injection',[build/'configured/Release/owner_allocation.exe']);(out/'allocation-results.json').write_bytes(raw);data=json.loads(raw)
        need(data['status']=='PASS' and data['schema']==1 and data['kind']=='actual-owned-session-allocation-injection','Actual complete finite injection result')
        total=0
        for operation in ['create','reset','read']:
            count=data['baselineAllocationAttempts'][operation];need(type(count) is int and 1<=count<=32,'Measured bounded allocation attempts')
            rows=[r for r in data['failures'] if r['operation']==operation];need([r['failAfter'] for r in rows]==list(range(count)),'Every observed global-new position injected')
            for row in rows:need(row['actualAttempts']==row['failAfter']+1 and all(row[k] is True for k in ['activeStateRetained','pastSnapshotRetained','nextOperationValid']),'Actual failure retained state and reusable context')
            total+=count
        need(data['actualAllocationFailures']==total==len(data['failures']),'Every failure counted')
        need(len(data['busyReentry'])==data['actualBusyChecks']==5 and {r['operation'] for r in data['busyReentry']}=={'create','reset','read','destroy','pump'},'All five real reentrant owner operations')
        for row in data['busyReentry']:need(row['outerReadAllocations']>0 and row['actualCallbacks']==1 and all(row[k] is True for k in ['busyRefused','noOutputOrModelCall','stateUnchanged']),'Actual allocation-hook reentry rejected without mutation')
        logs=[p for p in (build/'configured').rglob('CL.command.1.tlog') if 'owner_allocation.dir' in p.parts];need(len(logs)==1,'One actual allocation test compile log');command=logs[0].read_bytes().decode('utf16')
        for token in ['/W4','/WX','/permissive-','/fp:strict','/GL-']:need(re.search(r'(?:^|\s)'+re.escape(token)+r'(?=\s|$)',command,re.I),'Actual strict token '+token)
        (out/'compile.tlog.txt').write_bytes(logs[0].read_bytes());result.update(status='FINITE_ACTUAL_OWNER_ALLOCATION_REENTRY_PASS',actualAllocationFailures=total,baselineAllocationAttempts=data['baselineAllocationAttempts'],actualReentrantBusyChecks=5,actualResult=stamp(out/'allocation-results.json'),actualCompileLog=stamp(out/'compile.tlog.txt'),actualCompiler=compiler,
            limits='Controlled scalar/array new only in this normal MSVC executable. Create/reset/read private copy faults; nested API calls during outer read allocation. No OS OOM, aligned/CRT/malloc interception, post-child physics fault, thread atomicity, all-path/whole-heap proof, sanitizer/GNU/SDK acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(out/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(watched),commands=commands)
        if before!=after:result['status']='FAIL'
        write(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ['status','actualAllocationFailures','actualReentrantBusyChecks','sourceStable','error'] if k in result}),flush=True);return 0 if result['status']=='FINITE_ACTUAL_OWNER_ALLOCATION_REENTRY_PASS' else 1


if __name__=='__main__':raise SystemExit(main())
