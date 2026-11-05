"""Regression for shared actual-report codec and pure pump validation extraction.

No production kernel changes. Full84 byte equality precedes independent80 copied
controls; the new library-mode smoke records one actual waiting pump, not a fake
World or invented outer pointer row. Old builds stay immutable.
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
WRITER=ROOT/'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp'
SUPPORT=ROOT/'tests/world_static_mesh_flight_controlled_scheduler_fixture_support.hpp'
CHECKER=ROOT/'scripts/verify-world-static-mesh-flight-controlled-scheduler.py'
CONTROLS=ROOT/'tests/world_static_mesh_flight_controlled_scheduler_reference_tests.py'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    raw=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write(p,value):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',default='build/wfor1');parser.add_argument('--name',default='run-20261105-bridge-001');args=parser.parse_args()
    need(sys.platform=='win32','Actual MSVC only');build=(ROOT/args.build).resolve();out=RECIPE.parent/args.name
    need(build.parent==ROOT/'build' and re.fullmatch('wfor[1-9][0-9]*',build.name),'Fresh build/wforN');need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}',args.name),'Fresh report component');need(not build.exists() and not out.exists(),'Never overwrite evidence/build')
    build.mkdir();out.mkdir();(out/'recipe.py.txt').write_bytes(RECIPE.read_bytes());sys.dont_write_bytecode=True
    old=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'),run_name='readonly_paths');helper=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-advance-recipes/check-configured-prototype.py'),run_name='readonly_quote');quote=helper['cmake_path']
    base=ROOT/'build/wfcqm2';libs=[base/'Release'/(x+'.lib') for x in ['pikapika_world_static_mesh_flight_controlled_scheduler','pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler','pikapika_core']]
    objects=sorted(p for p in (base/'pikapika_world_static_mesh_flight_controlled_scheduler_tests.dir/Release').glob('*.obj') if p.name!='world_static_mesh_flight_controlled_scheduler_tests.obj');need(len(objects)==9,'Nine actual shared serializer objects')
    baseline=ROOT/'reports/world-static-mesh-flight-controlled-scheduler-recipes/run-20261105-main-integration-002/controlled-scheduler-full.json'
    watched=set(old['protected']())|{RECIPE,WRITER,SUPPORT,CHECKER,CONTROLS,baseline,*libs,*objects}
    for name in ['wfcqm2','wfo1']:
        watched.update(p for p in (ROOT/'build'/name).rglob('*') if p.is_file() and (p.suffix in {'.exe','.lib','.map','.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith('world-flight-')))
    watched=sorted(watched);identities=lambda:{p.relative_to(ROOT).as_posix():stamp(p) for p in watched};before=identities();write(out/'before.json',before)
    for p in [WRITER,SUPPORT,CHECKER]:(out/(p.name+'.txt')).write_bytes(p.read_bytes())
    project=build/'project';project.mkdir();smoke=project/'smoke.cpp'
    smoke.write_text('''#include "world_static_mesh_flight_controlled_scheduler_fixture_support.hpp"
#include "world_static_mesh_flight_controlled_tick_fixture_support.hpp"
#include <iostream>
#include <iomanip>
#include <limits>
#include <locale>
int main() {
    namespace q=pikapika::world_static_mesh_flight_controlled_scheduler;
    namespace f=controlled_tick_fixture;namespace codec=controlled_scheduler_fixture;
    auto x=f::base_case();q::Scheduler scheduler({.0625,8});
    std::cout.imbue(std::locale::classic());
    const auto progress=[&] {std::cout<<"{\\\"time\\\":"<<std::setprecision(std::numeric_limits<double>::max_digits10)<<x.progress.time<<",\\\"ticks\\\":"<<x.progress.ticks<<'}';};
    std::cout<<"{\\\"input\\\":{\\\"scene\\\":";world_guard_fixture::input_json(std::cout,x.scene);
    std::cout<<",\\\"progress\\\":";progress();std::cout<<",\\\"packets\\\":[]}";
    const auto actual=scheduler.pump(x.scene.world,x.scene.meshes,x.scene.settings,x.progress,0.,{});
    std::cout<<",\\\"report\\\":";codec::report_json(std::cout,actual);
    std::cout<<",\\\"inputAfter\\\":{\\\"scene\\\":";world_guard_fixture::input_json(std::cout,x.scene);
    std::cout<<",\\\"progress\\\":";progress();std::cout<<",\\\"packets\\\":[]},\\\"clock\\\":";
    codec::snapshot_json(std::cout,scheduler.snapshot());std::cout<<",\\\"meshes\\\":";codec::meshes_json(std::cout,x.scene.meshes);std::cout<<"}\\n";
    return actual.status==q::Status::waiting&&actual.elapsed_accepted&&actual.attempts==0?0:1;
}
''',encoding='utf8',newline='\n');(out/'smoke.cpp.txt').write_bytes(smoke.read_bytes())
    lines=['cmake_minimum_required(VERSION 3.24)','project(SessionCodecBridge LANGUAGES CXX)','set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)','set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL)','set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)',
        'if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR CMAKE_CROSSCOMPILING)','message(FATAL_ERROR "Actual matching MSVC19.51 x64 required")','endif()',
        'file(WRITE "${CMAKE_BINARY_DIR}/actual-compiler.txt" "${CMAKE_CXX_COMPILER}\\n${CMAKE_CXX_COMPILER_VERSION}\\n${CMAKE_SYSTEM_PROCESSOR}\\n")',
        'add_library(codec_library STATIC '+quote(WRITER)+')','target_compile_definitions(codec_library PRIVATE PIKAPIKA_CONTROLLED_SCHEDULER_FIXTURE_LIBRARY_ONLY=1)',
        'target_include_directories(codec_library PUBLIC '+quote(ROOT/'core/include')+' '+quote(ROOT/'tests')+')','target_compile_options(codec_library PRIVATE /W4 /WX /permissive- /fp:strict /GL-)']
    for name,main in [('full_regression',WRITER),('codec_smoke',smoke)]:
        lines+=['add_executable('+name+' '+quote(main)+' '+' '.join(quote(p) for p in objects)+')','target_include_directories('+name+' PRIVATE '+quote(ROOT/'core/include')+' '+quote(ROOT/'tests')+')','target_compile_options('+name+' PRIVATE /W4 /WX /permissive- /fp:strict /GL-)',
            'target_link_libraries('+name+' PRIVATE '+('codec_library ' if name=='codec_smoke' else '')+' '.join(quote(p) for p in libs)+')','target_link_options('+name+' PRIVATE /LTCG:OFF /OPT:NOREF /OPT:NOICF "/MAP:$<TARGET_FILE_DIR:'+name+'>/'+name+'.map")']
    (project/'CMakeLists.txt').write_text('\n'.join(lines)+'\n',encoding='utf8',newline='\n');(out/'project.cmake.txt').write_bytes((project/'CMakeLists.txt').read_bytes());commands=[]
    def run(name,argv,timeout=600):
        started=time.monotonic();done=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=timeout);(out/(name+'.stdout.txt')).write_bytes(done.stdout);(out/(name+'.stderr.txt')).write_bytes(done.stderr)
        row={'name':name,'argv':list(map(str,argv)),'exitCode':done.returncode,'seconds':time.monotonic()-started,'sourceStable':before==identities()};commands.append(row);write(out/(name+'.command.json'),row);print(json.dumps({k:row[k] for k in ['name','exitCode','seconds','sourceStable']}),flush=True)
        if done.returncode:print(done.stdout.decode(errors='replace')[-10000:]);print(done.stderr.decode(errors='replace')[-10000:])
        need(done.returncode==0 and row['sourceStable'],'Actual command failed: '+name);return done.stdout
    result={'schema':1,'status':'FAIL','scope':__doc__}
    try:
        run('01-configure',['cmake','-S',project,'-B',build/'configured','-A','x64'])
        # CMake writes escaped LF in this generated tiny project; normalize only
        # that compiler metadata transport, never a numerical transcript.
        compiler=(build/'configured/actual-compiler.txt').read_text().replace('\\n','\n').splitlines();expected=json.loads((base/'world-flight-binding-Release.json').read_bytes())['compiler'];need(Path(compiler[0]).resolve()==Path(expected['path']).resolve() and compiler[1]==expected['version'] and compiler[2]=='AMD64','Actual imported compiler ABI')
        run('02-release-build',['cmake','--build',build/'configured','--config','Release','--parallel','2'])
        raw=run('03-full84',[build/'configured/Release/full_regression.exe','--fixtures']);(out/'controlled-scheduler-full.json').write_bytes(raw);need(raw==baseline.read_bytes(),'All old84 raw bytes exact, including signed zero/IDs/order/sizeof')
        reference=json.loads(run('04-independent',[sys.executable,'-B','-X','utf8',CHECKER,out/'controlled-scheduler-full.json']))
        controls=json.loads(run('05-controls',[sys.executable,'-B','-X','utf8',CONTROLS,out/'controlled-scheduler-full.json','--output',out/'controls'],360))
        raw=run('06-actual-smoke',[build/'configured/Release/codec_smoke.exe']);(out/'actual-smoke.json').write_bytes(raw)
        q=runpy.run_path(str(CHECKER),run_name='readonly_pure_pump_reference');data=q['load'](out/'actual-smoke.json');stats={'frames':0,'admitted':0,'attempts':0,'committedTicks':0,'statusCounts':{},'fixedBoundaryBodyObservations':0,'controlled':q['controlled'].new_stats()};old_data=q['load'](out/'controlled-scheduler-full.json')
        q['verify_pump'](data['input'],data['inputAfter'],data['report'],0,old_data['layoutSizes'],old_data['controlledSchedulerLayoutSizes'],stats);q['equal'](data['clock'],data['report']['after'],'actual clock codec');q['equal'](data['meshes'],data['input']['scene']['meshes'],'actual mesh codec');need(stats['frames']==1 and stats['attempts']==0,'One actual waiting pump, no fabricated pointer observations')
        write(out/'pure-smoke-reference.json',{'status':'PASS','stats':stats,'outerPointerObservationsInvented':False})
        logs=[]
        for path in sorted((build/'configured').rglob('CL.command.1.tlog')):
            if not any(x+'.dir' in path.parts for x in ['codec_library','full_regression','codec_smoke']):continue
            text=path.read_bytes().decode('utf16')
            for token in ['/W4','/WX','/permissive-','/fp:strict','/GL-']:need(re.search(r'(?:^|\s)'+re.escape(token)+r'(?=\s|$)',text,re.I),'Actual strict token '+token)
            copy=out/('compile-'+str(len(logs))+'.tlog.txt');copy.write_bytes(path.read_bytes());logs.append({'original':stamp(path),'copy':stamp(copy)})
        need(len(logs)==3,'Three actual codec/library/standalone compiler logs')
        result.update(status='FINITE_CODEC_PURE_PUMP_BRIDGE_PASS',old84RawByteExact=True,fullReference=reference,fullControls=controls,actualPureSmoke=stats,compileLogs=logs,actualGNUExecuted=False,productionKernelsChanged=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(out/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(watched),commands=commands)
        if before!=after:result['status']='FAIL'
        write(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}),flush=True);return 0 if result['status']=='FINITE_CODEC_PURE_PUMP_BRIDGE_PASS' else 1


if __name__=='__main__':raise SystemExit(main())
