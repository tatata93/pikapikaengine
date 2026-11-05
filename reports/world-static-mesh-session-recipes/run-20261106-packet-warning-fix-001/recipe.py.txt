"""Fresh Native warning correction; original decoder unchanged, full24 raw retained."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfopkw1'
OUT=HERE/'run-20261106-packet-warning-fix-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh Native packet build/output');BUILD.mkdir();OUT.mkdir();project=BUILD/'project';project.mkdir();commands=[]
    paths=[ROOT/'core/include/pikapika/world_static_mesh_session_packet_wire.hpp',ROOT/'core/src/world_static_mesh_session_packet_wire.cpp',ROOT/'tests/world_static_mesh_session_packet_wire_tests.cpp',Path(__file__).resolve()];before=[stamp(p) for p in paths];write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());q=lambda p:'"'+Path(p).as_posix()+'"'
    lines=['cmake_minimum_required(VERSION 3.24)','project(PacketWirePrototype LANGUAGES CXX)','set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)','set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")','set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)','if(NOT MSVC OR NOT MSVC_VERSION EQUAL 1951 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)','message(FATAL_ERROR "MSVC19.51 x64 required")','endif()','add_library(packet_wire STATIC '+q(paths[1])+')','target_include_directories(packet_wire PUBLIC '+q(ROOT/'core/include')+')','add_executable(packet_wire_tests '+q(paths[2])+')','target_link_libraries(packet_wire_tests PRIVATE packet_wire)','foreach(t packet_wire packet_wire_tests)','target_compile_options(${t} PRIVATE /W4 /WX /permissive- /fp:strict /GL-)','target_link_options(${t} PRIVATE /LTCG:OFF)','endforeach()'];cmake=('\n'.join(lines)+'\n').encode();(project/'CMakeLists.txt').write_bytes(cmake);(OUT/'project.cmake.txt').write_bytes(cmake)
    def run(name,argv):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr);r=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(r);write(OUT/(name+'.command.json'),r)
        if p.returncode:print(p.stdout.decode(errors='replace')[-6000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__,independentReferenceAccepted=True)
    try:
        run('configure',['cmake','-S',project,'-B',BUILD/'configured','-A','x64']);captures=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD/'configured','--config',cfg,'--parallel','2']);run(cfg+'-lifetime',[BUILD/'configured'/cfg/'packet_wire_tests.exe','--run']);raw=run(cfg+'-fixtures',[BUILD/'configured'/cfg/'packet_wire_tests.exe','--fixtures']);(OUT/(cfg+'-packet-wire.json')).write_bytes(raw);d=json.loads(raw);need(d['actualRows']==len(d['rows'])==24,'Actual24 packet rows');need(raw==(HERE/'run-20261105-packet-wire-producer-002'/(cfg+'-packet-wire.json')).read_bytes(),'Whole24 raw unchanged by reference loop correction');captures.append(raw);ref=json.loads(run(cfg+'-reference',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session-packet-wire.py',OUT/(cfg+'-packet-wire.json')]));need(ref['status']=='PASS' and ref['mappedFloatBitValues']==492,'Actual pinned reference after correction')
            for target in ['packet_wire','packet_wire_tests']:
                log=next((BUILD/'configured'/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16')
                for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual new strict flags '+flag)
                (OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(log.read_bytes())
        need(captures[0]==captures[1],'Whole24 raw equality on true Release/Debug')
        result.update(status='FINITE_NATIVE_PACKET_WARNING_CORRECTION_PASS',rowsPerBuild=24,wholeReleaseDebugRawExact=True,actualCallerCopyMoveLifetimeAssertions=True,actualFourFpuModesObservedAndRetained=True,newProductionTUsPerBuild=1,newHarnessTUsPerBuild=1,mainCMakeIntegrated=False,actualGNUExecuted=False,modelOrSDKCalled=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in paths];write(OUT/'after.json',after);result.update(sourceStable=before==after,commands=commands)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_PACKET_WARNING_CORRECTION_PASS')
if __name__=='__main__':raise SystemExit(main())
