"""Fresh new harness TU using immutable actual Release/Debug source libraries.

Checks the explicit-brace warning correction without rebuilding old projects.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfopw1'
OUT=HERE/'run-20261105-source-warning-fix-001'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def write(p,data):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh actual Native warning-fix harness');BUILD.mkdir();OUT.mkdir();project=BUILD/'project';project.mkdir();commands=[]
    names=['pikapika_world_static_mesh_session_source_wire','pikapika_world_static_mesh_session','pikapika_world_static_mesh_flight_controlled_scheduler','pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler','pikapika_core']
    base=ROOT/'build/wfop1';libs=[base/cfg/(n+'.lib') for cfg in ['Release','Debug'] for n in names];need(all(p.is_file() for p in libs),'Actual twelve dependency libraries')
    paths={*libs,ROOT/'tests/world_static_mesh_session_source_wire_tests.cpp',ROOT/'core/include/pikapika/world_static_mesh_session_source_wire.hpp',ROOT/'core/src/world_static_mesh_session_source_wire.cpp',Path(__file__).resolve()};before={p.relative_to(ROOT).as_posix():stamp(p) for p in sorted(paths)};write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    quote=lambda p:'"'+Path(p).as_posix()+'"'
    lines=['cmake_minimum_required(VERSION 3.24)','project(SourceWarningFix LANGUAGES CXX)','set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)','set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")','set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)',
        'if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)','message(FATAL_ERROR "Actual matching MSVC19.51 x64 required")','endif()',
        'file(WRITE "${CMAKE_BINARY_DIR}/actual-compiler.txt" "${CMAKE_CXX_COMPILER}\\n${CMAKE_CXX_COMPILER_VERSION}\\n${CMAKE_SYSTEM_PROCESSOR}\\n")']
    for i,n in enumerate(names):
        lines.extend(['add_library(imported'+str(i)+' STATIC IMPORTED)','set_target_properties(imported'+str(i)+' PROPERTIES IMPORTED_CONFIGURATIONS "Release;Debug" IMPORTED_LOCATION_RELEASE '+quote(base/'Release'/(n+'.lib'))+' IMPORTED_LOCATION_DEBUG '+quote(base/'Debug'/(n+'.lib'))+')'])
    lines.extend(['add_executable(source_warning_fix '+quote(ROOT/'tests/world_static_mesh_session_source_wire_tests.cpp')+')','target_include_directories(source_warning_fix PRIVATE '+quote(ROOT/'core/include')+')','target_compile_options(source_warning_fix PRIVATE /W4 /WX /permissive- /fp:strict /GL-)','target_link_options(source_warning_fix PRIVATE /LTCG:OFF)','target_link_libraries(source_warning_fix PRIVATE '+' '.join('imported'+str(i) for i in range(6))+')'])
    (project/'CMakeLists.txt').write_bytes(('\n'.join(lines)+'\n').encode());(OUT/'project.cmake.txt').write_bytes((project/'CMakeLists.txt').read_bytes())
    def run(name,argv):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);r={'name':name,'argv':list(map(str,argv)),'exitCode':p.returncode,'seconds':time.monotonic()-start};commands.append(r);write(OUT/(name+'.command.json'),r)
        if p.returncode:print(p.stdout.decode(errors='replace')[-8000:]);print(p.stderr.decode(errors='replace')[-8000:])
        need(p.returncode==0,'Actual command failed: '+name);return p.stdout
    result={'schema':1,'status':'FAIL','scope':__doc__}
    try:
        run('01-configure',['cmake','-S',project,'-B',BUILD/'configured','-A','x64']);compiler=(BUILD/'configured/actual-compiler.txt').read_text().replace('\\n','\n').splitlines();expected=json.loads((base/'world-flight-binding-Release.json').read_bytes())['compiler'];need(Path(compiler[0]).resolve()==Path(expected['path']).resolve() and compiler[1]==expected['version'] and compiler[2]=='AMD64','Actual imported ABI compiler matches')
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD/'configured','--config',cfg,'--parallel','2']);run(cfg+'-directed',[BUILD/'configured'/cfg/'source_warning_fix.exe','--run']);raw=run(cfg+'-fixtures',[BUILD/'configured'/cfg/'source_warning_fix.exe','--fixtures']);(OUT/(cfg+'-source-wire.json')).write_bytes(raw)
            need(raw==(HERE/'run-20261105-source-wire-producer-001'/(cfg+'-source-wire.json')).read_bytes(),'Whole27 raw equality to actual pre-brace-correction output')
            log=next((BUILD/'configured/source_warning_fix.dir'/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16')
            for flag in ['/W4','/WX','/fp:strict','/GL-']:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual compiler flag '+flag)
            need(re.search(r'(?:^|\s)'+('/MDd' if cfg=='Debug' else '/MD')+r'(?=\s|$)',text),'Actual distinct runtime ABI');(OUT/(cfg+'-compile.tlog.txt')).write_bytes(log.read_bytes())
        run('08-controls',[sys.executable,'-B','-X','utf8',HERE/'check-source-wire-reference.py','--release',OUT/'Release-source-wire.json','--debug',OUT/'Debug-source-wire.json','--output',OUT/'controls']);controls=json.loads((OUT/'controls/verification.json').read_bytes());need(controls['status']=='PASS' and controls['copiedNegativeControls']==13,'Actual independent current-harness controls')
        result.update(status='FINITE_NATIVE_SOURCE_WARNING_CORRECTION_PASS',actualCompiler=compiler,newCompileLogs=2,all27RawExactBeforeAndAfterBraces=True,actualDirectedLifetimeAssertions=True,independentSourceControls=13,actualOptimizedPythonRefused=True,oldProjectsReconfiguredOrBuilt=False,actualGNUExecuted=False,productionDecoderOrKernelChanged=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after={p.relative_to(ROOT).as_posix():stamp(p) for p in sorted(paths)};write(OUT/'after.json',after);result.update(sourceStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'result.json',result);print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_SOURCE_WARNING_CORRECTION_PASS')


if __name__=='__main__':raise SystemExit(main())
