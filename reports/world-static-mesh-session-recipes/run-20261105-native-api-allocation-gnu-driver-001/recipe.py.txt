"""Normal-only actual C API global-new faults after the separate sanitizer audit."""
from pathlib import Path
import argparse,importlib.util,json,re,shlex,sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TEST='pikapika_world_static_mesh_session_api_allocation_tests'
def need(v,m):
    if not v:raise ValueError(m)
def imported(name,p):
    sys.dont_write_bytecode=True;s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def observe(d):
    keys={'schema','kind','contextAllocationFailures','operationAllocations','rows','allocatorCallbackOuterOperations','actualBusyReentryChecks','stageInputCapturedBeforeAllocation','cachedGetterAllocations','normalOnly'}
    need(type(d)==dict and set(d)==keys,'Exact actual allocation envelope')
    need(type(d['schema'])==int and d['schema']==1 and d['kind']=='native-session-api-actual-allocation' and d['normalOnly'] is True and type(d['contextAllocationFailures'])==int and 0<d['contextAllocationFailures']<=8,'Actual context fault observations')
    counts=d['operationAllocations'];need(type(counts)==list and len(counts)==4 and all(type(v)==int and 0<v<=32 for v in counts) and type(d['rows'])==list and len(d['rows'])==sum(counts),'Every measured operation allocation position')
    expected=[(op,i) for op,n in zip(['stage','create','reset','read'],counts) for i in range(n)]
    for r,(op,i) in zip(d['rows'],expected):
        need(type(r)==dict and set(r)=={'operation','failAfter','actualAttempts','wholePreviousCacheRetained','activeOwnerRetained','recoveryValid'},'Exact actual failure record')
        need(r['operation']==op and type(r['failAfter'])==int and r['failAfter']==i and type(r['actualAttempts'])==int and r['actualAttempts']==i+1 and all(r[k] is True for k in ['wholePreviousCacheRetained','activeOwnerRetained','recoveryValid']),'Typed ordered observed position/retention/recovery '+op)
    need(type(d['allocatorCallbackOuterOperations'])==int and d['allocatorCallbackOuterOperations']==4 and type(d['actualBusyReentryChecks'])==int and d['actualBusyReentryChecks']==20 and d['stageInputCapturedBeforeAllocation'] is True and type(d['cachedGetterAllocations'])==int and d['cachedGetterAllocations']==0,'Actual callback/input-capture/getter assertions')
    return {'contextFailurePositions':d['contextAllocationFailures'],'operationFailurePositions':counts,'actualOperationFailures':sum(counts)}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k,v in [('normal','build/ci-world-owner'),('parent','build/public-checks/owner-api-gnu/verification.json'),('output','build/public-checks/owner-api-allocation-gnu')]:p.add_argument('--'+k,type=Path,default=ROOT/v)
    a=p.parse_args()
    for k in ['normal','parent','output']:
        v=getattr(a,k).resolve();need(v.is_relative_to(ROOT/'build') and v!=ROOT/'build','Repository build children');setattr(a,k,v)
    need(a.output.is_relative_to(ROOT/'build/public-checks') and a.output!=ROOT/'build/public-checks' and a.parent.is_relative_to(ROOT/'build/public-checks') and not a.output.exists() and not a.parent.is_relative_to(a.output) and not a.output.is_relative_to(a.normal) and not a.normal.is_relative_to(a.output),'Fresh bounded output and separate actual parent/normal')
    a.output.mkdir(parents=True);owner=imported('api_fault_owner',HERE/'verify-gnu.py');packet=imported('api_fault_packet',ROOT/'reports/world-static-mesh-flight-controlled-scheduler-recipes/verify-gnu.py');tick=imported('api_fault_tick',ROOT/'reports/world-static-mesh-flight-controlled-tick-recipes/verify-gnu.py');helper=imported('api_fault_helper',tick.GUARD_RECIPE);stamp,write=owner.stamp,owner.write;commands=helper.Commands(a.output,120)
    (a.output/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    def sources():return [stamp(p) for p in sorted({Path(x['path']) for x in helper.source_stamps()}|{Path(__file__).resolve(),ROOT/'.github/workflows/verify.yml'})]
    before=sources();write(a.output/'sources-before.json',before);artifacts_before=None;result=dict(schema=1,status='FAIL',actualGNUFaultExecuted=False,normalBuildReconfiguredOrBuilt=False,actualSanitizedFaultExecutable=False,scope=__doc__)
    try:
        need(sys.platform.startswith('linux'),'Actual Linux GNU13 required; other platforms refusal-only')
        parent=helper.load(a.parent);need(parent['status']=='PASS' and parent['actualGNUExecuted'] and parent['libraryTranslationUnits']==46 and len(parent['commands'])==15 and all(x['exitCode']==0 for x in parent['commands']),'Actual completed API GNU parent')
        need(all(parent[k] is True for k in ['sourceStable','normalArtifactsStable','parentArtifactsStable','compilerStable','normalDebugSanitizedWholeRawExact']),'Actual stable API parent')
        records=helper.load(a.parent.parent/'normal-artifacts-after.json');need(all(Path(r['path']).is_relative_to(a.normal) and stamp(r['path'])==r for r in records),'Same actual immutable normal build')
        production=helper.load(a.parent.parent/'normal-production-compilation.json');need(len(production)==46 and all(stamp(r['object']['path'])==r['object'] and not any(v.startswith('-fsanitize=') for v in r['argv']) for r in production.values()),'All46 dependencies actual unchanged normal objects')
        rows=packet.compile_rows(helper,a.normal,TEST,{'tests/world_static_mesh_session_api_allocation_tests.cpp'});row=next(iter(rows.values()));tick.strict_command(row['argv'],werror=True);need('-DNDEBUG' in row['argv'] and not any(v.startswith('-fsanitize=') for v in row['argv']),'Actual new normal Release-only fault harness flags')
        compiler=Path(helper.cache(a.normal)['CMAKE_CXX_COMPILER']).resolve();need(Path(row['argv'][0]).resolve()==compiler and re.fullmatch(r'13(?:\.[0-9]+)*',parent['actualCxxCompilerVersion']),'Actual GNU13 C++ compiler provenance')
        link=a.normal/'CMakeFiles'/(TEST+'.dir/link.txt');exe=a.normal/TEST
        link_argv=shlex.split(link.read_text())
        for lib in ['pikapika_world_static_mesh_session_api','pikapika_world_static_mesh_session_source_wire',owner.LIB,packet.LIB,tick.LIBRARY,'pikapika_world_static_mesh_flight_scheduler','pikapika_core']:need(any(Path(v).name=='lib'+lib+'.a' for v in link_argv),'Actual normal fault executable links '+lib)
        paths={Path(r['path']) for r in records}|{row['object'],link,exe,a.parent,compiler}
        def artifacts():return [stamp(p) for p in sorted(paths)]
        artifacts_before=artifacts();write(a.output/'artifacts-before.json',artifacts_before);write(a.output/'actual-normal-compilation.json',dict(argv=row['argv'],directory=str(row['directory']),object=stamp(row['object'])))
        raw=commands.run('actual-normal-faults',[exe,'--run']);(a.output/'actual-allocation.json').write_bytes(raw);d=json.loads(raw)
        observed=observe(d);counts=observed['operationFailurePositions']
        result.update(status='PASS',actualGNUFaultExecuted=True,actualCxxCompilerVersion=parent['actualCxxCompilerVersion'],contextFailurePositions=d['contextAllocationFailures'],operationFailurePositions=counts,actualOperationFailures=sum(counts),actualAllocatorBusyReentryChecks=20,stageCapturedBeforeAllocation=True,cachedGetterAllocations=0,normalReleaseOnly=True,actualParentVerification=stamp(a.parent),scope='Actual finite GNU13 normal-only scalar/array global-new injection into C API context/stage/create/reset/read. Each observed position/whole old cache/live owner/recovery and20 callback busy gates checked. Separate earlier C/C++ ASan audit is not this fault executable. Counts may differ with STL; no normalization or fabricated Native/GNU count equality. No all allocator/OS OOM/aligned/CRT/thread/post-pump fault, pump/mesh/full guard/WASM/game acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=sources();write(a.output/'sources-after.json',after);result['sourceStable']=before==after
        if before!=after:result['status']='FAIL'
        if artifacts_before is not None:
            after=artifacts();write(a.output/'artifacts-after.json',after);result['normalArtifactsAndCompilerStable']=artifacts_before==after
            if artifacts_before!=after:result['status']='FAIL'
        result.update(commands=commands.items,recipe=stamp(Path(__file__)));write(a.output/'verification.json',result);print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    return int(result['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
