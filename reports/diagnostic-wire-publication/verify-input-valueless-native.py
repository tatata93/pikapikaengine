"""Four legitimate throwing-conversion emplace attempts on actual MSVC Input; not exhaustive reachability proof."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-input-valueless-native-002'
BUILD=ROOT/'build/wfdip2'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
def main():
    need(__debug__ and sys.platform=='win32' and not OUT.exists() and not BUILD.exists(),'Fresh Native probe')
    OUT.mkdir(parents=True);project=BUILD/'source';project.mkdir(parents=True);binary=BUILD/'binary';commands=[]
    before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tests/coverage_input_valueless_probe.cpp','core/include/pikapika/accelerated_pair_coverage.hpp','core/include/pikapika/accelerated.hpp','core/include/pikapika/core.hpp']}
    source='cmake_minimum_required(VERSION 3.20)\nproject(InputValuelessProbe LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 20)\nset(CMAKE_CXX_STANDARD_REQUIRED ON)\nadd_executable(probe "'+(ROOT/'tests/coverage_input_valueless_probe.cpp').as_posix()+'")\ntarget_include_directories(probe PRIVATE "'+(ROOT/'core/include').as_posix()+'")\ntarget_compile_options(probe PRIVATE /W4 /WX /permissive- /fp:strict /GL-)\ntarget_link_options(probe PRIVATE /LTCG:OFF)\n'
    (project/'CMakeLists.txt').write_text(source,encoding='utf8',newline='\n');(OUT/'CMakeLists.txt.original.txt').write_text(source,encoding='utf8',newline='\n')
    def run(name,args):
        start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,timeout=120)
        (OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        row=dict(name=name,argv=list(map(str,args)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(row);write(OUT/(name+'.command.json'),row)
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(status='FAIL',scope=__doc__)
    try:
        run('configure',['cmake','-S',project,'-B',binary,'-A','x64']);checks=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',binary,'--config',cfg,'--target','probe','--parallel','2'])
            checks.append(json.loads(run(cfg+'-run',[binary/cfg/'probe.exe'])))
        need(checks[0]==checks[1] and checks[0]['attempts']==4 and checks[0]['status']=='PASS','Actual configurations agree')
        result.update(status='FINITE_NATIVE_INPUT_VALUELESS_PROBE_PASS',actual=checks[0],newTranslationUnits=1,modelLibraryLinked=False,gnuExecuted=False,allPossibleOperationsTested=False,inputGetterImplemented=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in before};result.update(commands=commands,sourceBefore=before,sourceAfter=after,sourceStable=before==after)
    if before!=after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','actual','error'] if k in result}));return int(result['status']!='FINITE_NATIVE_INPUT_VALUELESS_PROBE_PASS')
if __name__=='__main__':raise SystemExit(main())
