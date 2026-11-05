"""Fresh isolated Native C ABI with actual immutable Release/Debug dependencies."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'build/wfoc1'
OUT=Path(__file__).resolve().parent/'run-20261105-native-api-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh Native build/output');BUILD.mkdir();OUT.mkdir();project=BUILD/'project';project.mkdir();commands=[]
    base=ROOT/'build/wfop1';names=['pikapika_world_static_mesh_session_source_wire','pikapika_world_static_mesh_session','pikapika_world_static_mesh_flight_controlled_scheduler','pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler','pikapika_core']
    libs=[base/cfg/(n+'.lib') for cfg in ['Release','Debug'] for n in names];need(all(p.is_file() for p in libs),'Actual twelve matching dependency libraries')
    sources=[ROOT/'core/include/pikapika/world_static_mesh_session_api.h',ROOT/'core/src/world_static_mesh_session_api.cpp',ROOT/'tests/world_static_mesh_session_api_tests.cpp',ROOT/'tests/world_static_mesh_session_api_c_tests.c',ROOT/'scripts/verify-world-static-mesh-session-api.py',Path(__file__).resolve()]
    before=[stamp(p) for p in [*sources,*libs]];write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    q=lambda p:'"'+Path(p).as_posix()+'"'
    lines=['cmake_minimum_required(VERSION 3.24)','project(NativeSessionABI LANGUAGES C CXX)','set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)','set(CMAKE_C_STANDARD 11)','set(CMAKE_C_STANDARD_REQUIRED ON)','set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")','set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)','if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)','message(FATAL_ERROR "Matching MSVC19.51 x64 required")','endif()','file(WRITE "${CMAKE_BINARY_DIR}/actual-compiler.txt" "${CMAKE_CXX_COMPILER}\\n${CMAKE_CXX_COMPILER_VERSION}\\n${CMAKE_C_COMPILER}\\n${CMAKE_C_COMPILER_VERSION}\\n${CMAKE_SYSTEM_PROCESSOR}\\n")']
    for i,n in enumerate(names):lines.extend(['add_library(imported'+str(i)+' STATIC IMPORTED)','set_target_properties(imported'+str(i)+' PROPERTIES IMPORTED_CONFIGURATIONS "Release;Debug" IMPORTED_LOCATION_RELEASE '+q(base/'Release'/(n+'.lib'))+' IMPORTED_LOCATION_DEBUG '+q(base/'Debug'/(n+'.lib'))+')'])
    lines.extend(['add_library(native_session_api STATIC '+q(sources[1])+')','target_include_directories(native_session_api PUBLIC '+q(ROOT/'core/include')+')','target_link_libraries(native_session_api PUBLIC '+' '.join('imported'+str(i) for i in range(6))+')','add_executable(native_session_api_tests '+q(sources[2])+' '+q(sources[3])+')','target_link_libraries(native_session_api_tests PRIVATE native_session_api)','foreach(target native_session_api native_session_api_tests)','target_compile_options(${target} PRIVATE /W4 /WX /permissive- /fp:strict /GL-)','target_link_options(${target} PRIVATE /LTCG:OFF)','endforeach()'])
    cmake=('\n'.join(lines)+'\n').encode();(project/'CMakeLists.txt').write_bytes(cmake);(OUT/'project.cmake.txt').write_bytes(cmake)
    def run(name,argv,ok=True):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        r=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(r);write(OUT/(name+'.command.json'),r)
        if ok and p.returncode:print(p.stdout.decode(errors='replace')[-6000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0 if ok else p.returncode!=0,'Actual command '+name);return p
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        run('01-configure',['cmake','-S',project,'-B',BUILD/'configured','-A','x64']);compiler=(BUILD/'configured/actual-compiler.txt').read_text().replace('\\n','\n').splitlines();expected=json.loads((base/'world-flight-binding-Release.json').read_bytes())['compiler'];need(Path(compiler[0]).resolve()==Path(expected['path']).resolve() and compiler[1]==compiler[3]==expected['version'] and compiler[0]==compiler[2] and compiler[4]=='AMD64','Actual C/C++ compiler ABI matches six imported libs')
        captures=[];refs=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD/'configured','--config',cfg,'--parallel','2']);run(cfg+'-directed',[BUILD/'configured'/cfg/'native_session_api_tests.exe','--run']);raw=run(cfg+'-fixtures',[BUILD/'configured'/cfg/'native_session_api_tests.exe','--fixtures']).stdout;capture=OUT/(cfg+'-api.json');capture.write_bytes(raw);captures.append(raw)
            refs.append(json.loads(run(cfg+'-reference',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session-api.py',capture]).stdout))
            for target in ['native_session_api','native_session_api_tests']:
                log=next((BUILD/'configured'/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16')
                for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual '+cfg+' '+target+' flag '+flag)
                if target.endswith('tests'):need('/TC' in text and '/TP' in text,'Actual separately compiled C/C++ TUs')
                (OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(log.read_bytes())
        need(captures[0]==captures[1],'Whole raw exact Release/Debug with no normalization')
        opt=run('optimized-refusal',[sys.executable,'-O',ROOT/'scripts/verify-world-static-mesh-session-api.py',OUT/'Release-api.json'],False);need(b'normal Python' in opt.stderr,'Actual optimized interpreter refusal')
        result.update(status='FINITE_NATIVE_PLAIN_SESSION_C_API_PASS',actualCompiler=compiler,newProductionTUsPerBuild=1,newHarnessTUsPerBuild=2,actualCAndCxxCallers=True,actualLifecycleAssertions=True,actualIndependentReferences=refs,wholeReleaseDebugRawExact=True,actualOptimizedPythonRefused=True,oldProjectsReconfiguredOrBuilt=False,actualGNUExecuted=False,mainCMakeIntegrated=False,pumpOrWASMImplemented=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in [*sources,*libs]];write(OUT/'after.json',after);result.update(sourceAndDependencyStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceAndDependencyStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_PLAIN_SESSION_C_API_PASS')
if __name__=='__main__':raise SystemExit(main())
