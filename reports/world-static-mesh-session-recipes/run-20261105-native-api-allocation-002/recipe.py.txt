"""Normal Release only: actual C API bad_alloc/reentry with frozen Native libs."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfoca2'
OUT=HERE/'run-20261105-native-api-allocation-002'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh normal Native allocation build/output');BUILD.mkdir();OUT.mkdir();project=BUILD/'project';project.mkdir();commands=[]
    source=ROOT/'tests/world_static_mesh_session_api_allocation_tests.cpp';base=ROOT/'build/wfocm1';names=['pikapika_world_static_mesh_session_api','pikapika_world_static_mesh_session_source_wire','pikapika_world_static_mesh_session','pikapika_world_static_mesh_flight_controlled_scheduler','pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler','pikapika_core'];libs=[base/'Release'/(n+'.lib') for n in names];need(all(p.is_file() for p in libs),'Seven actual normal Native dependency libs')
    paths=[source,Path(__file__).resolve(),ROOT/'core/include/pikapika/world_static_mesh_session_api.h',ROOT/'core/src/world_static_mesh_session_api.cpp',*libs];before=[stamp(p) for p in paths];write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());q=lambda p:'"'+Path(p).as_posix()+'"'
    lines=['cmake_minimum_required(VERSION 3.24)','project(NativeAPIAllocation LANGUAGES CXX)','set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)','set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL)','set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)','if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)','message(FATAL_ERROR "Matching MSVC19.51 x64 normal Release only")','endif()','file(WRITE "${CMAKE_BINARY_DIR}/compiler.txt" "${CMAKE_CXX_COMPILER}\\n${CMAKE_CXX_COMPILER_VERSION}\\n${CMAKE_SYSTEM_PROCESSOR}\\n")']
    for i,lib in enumerate(libs):lines.extend(['add_library(imported'+str(i)+' STATIC IMPORTED)','set_target_properties(imported'+str(i)+' PROPERTIES IMPORTED_LOCATION '+q(lib)+')'])
    lines.extend(['add_executable(native_api_allocation '+q(source)+')','target_include_directories(native_api_allocation PRIVATE '+q(ROOT/'core/include')+')','target_compile_options(native_api_allocation PRIVATE /W4 /WX /permissive- /fp:strict /GL-)','target_link_options(native_api_allocation PRIVATE /LTCG:OFF)','target_link_libraries(native_api_allocation PRIVATE '+' '.join('imported'+str(i) for i in range(7))+')']);cmake=('\n'.join(lines)+'\n').encode();(project/'CMakeLists.txt').write_bytes(cmake);(OUT/'project.cmake.txt').write_bytes(cmake)
    def run(name,argv):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);row=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(row);write(OUT/(name+'.command.json'),row)
        if p.returncode:print(p.stdout.decode(errors='replace')[-5000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        run('configure',['cmake','-S',project,'-B',BUILD/'configured','-A','x64']);compiler=(BUILD/'configured/compiler.txt').read_text().replace('\\n','\n').splitlines();expected=json.loads((base/'world-flight-binding-Release.json').read_bytes())['compiler'];need(Path(compiler[0]).resolve()==Path(expected['path']).resolve() and compiler[1]==expected['version'] and compiler[2]=='AMD64','Actual imported normal ABI compiler')
        run('build',['cmake','--build',BUILD/'configured','--config','Release','--parallel','2']);raw=run('actual-allocation',[BUILD/'configured/Release/native_api_allocation.exe','--run']);(OUT/'actual-allocation.json').write_bytes(raw);d=json.loads(raw);need(d['schema']==1 and d['kind']=='native-session-api-actual-allocation' and d['normalOnly'] is True,'Actual normal-only allocation observation')
        need(d['contextAllocationFailures']>0 and len(d['operationAllocations'])==4 and all(0<v<=32 for v in d['operationAllocations']),'Observed finite allocation inventory');need(len(d['rows'])==sum(d['operationAllocations']),'All measured positions exercised')
        for op,count in zip(['stage','create','reset','read'],d['operationAllocations']):
            rows=[r for r in d['rows'] if r['operation']==op];need([r['failAfter'] for r in rows]==list(range(count)) and all(r['actualAttempts']==r['failAfter']+1 and r['wholePreviousCacheRetained'] and r['activeOwnerRetained'] and r['recoveryValid'] for r in rows),'All observed failures/retention/recovery '+op)
        need(d['actualBusyReentryChecks']==20 and d['allocatorCallbackOuterOperations']==4 and d['stageInputCapturedBeforeAllocation'] is True and d['cachedGetterAllocations']==0,'Actual allocator callback and getter assertions')
        log=next((BUILD/'configured/native_api_allocation.dir/Release').rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16')
        for flag in ['/W4','/WX','/fp:strict','/GL-','/MD']:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual normal strict flag '+flag)
        need(re.search(r'(?:^|\s)/D\s*(?:"NDEBUG"|NDEBUG)(?=\s|$)',text,re.I),'Actual normal NDEBUG macro')
        need(raw==(HERE/'run-20261105-native-api-allocation-001/actual-allocation.json').read_bytes(),'Whole actual allocation observation unchanged after macro-token parser correction')
        (OUT/'actual-compile.tlog.txt').write_bytes(log.read_bytes());result.update(status='FINITE_NATIVE_C_API_ACTUAL_ALLOCATION_PASS',actualCompiler=compiler,contextFailurePositions=d['contextAllocationFailures'],operationFailurePositions=d['operationAllocations'],actualOperationFailures=len(d['rows']),actualAllocatorBusyReentryChecks=20,cachedGetterAllocations=0,stageCapturedBeforeAllocation=True,normalReleaseOnly=True,actualSanitizedFaultExecutable=False,actualGNUExecuted=False,oldProjectsReconfiguredOrBuilt=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in paths];write(OUT/'after.json',after);result.update(sourceAndDependencyStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceAndDependencyStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_C_API_ACTUAL_ALLOCATION_PASS')
if __name__=='__main__':raise SystemExit(main())
