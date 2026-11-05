"""Add only pure owned packet-data targets after the actual C API fault audit."""
from pathlib import Path
import argparse,importlib.util,json,shlex,sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
LIB='pikapika_world_static_mesh_session_packet_wire'
TEST=LIB+'_tests'
def need(v,m):
    if not v:raise ValueError(m)
def imported(name,p):
    sys.dont_write_bytecode=True;s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k,v in [('normal','build/ci-world-owner'),('debugbuild','build/wfo-api-debug'),('sanbuild','build/wfo-api-san'),('parent','build/public-checks/owner-api-allocation-gnu/verification.json'),('output','build/public-checks/owner-packet-wire-gnu')]:p.add_argument('--'+k,type=Path,default=ROOT/v)
    a=p.parse_args()
    for k in ['normal','debugbuild','sanbuild','parent','output']:
        v=getattr(a,k).resolve();need(v.is_relative_to(ROOT/'build') and v!=ROOT/'build','Repository build children');setattr(a,k,v)
    builds=[a.normal,a.debugbuild,a.sanbuild,a.output];need(len(set(builds))==4 and all(not x.is_relative_to(y) and not y.is_relative_to(x) for i,x in enumerate(builds) for y in builds[i+1:]),'Distinct nonoverlapping paths')
    need(not a.output.exists() and a.output.is_relative_to(ROOT/'build/public-checks') and a.output!=ROOT/'build/public-checks' and a.parent.is_relative_to(ROOT/'build/public-checks') and not a.parent.is_relative_to(a.output),'Fresh bounded output/parent')
    a.output.mkdir(parents=True);owner=imported('pk_gnu_owner',HERE/'verify-gnu.py');packet=imported('pk_gnu_packet',ROOT/'reports/world-static-mesh-flight-controlled-scheduler-recipes/verify-gnu.py');tick=imported('pk_gnu_tick',ROOT/'reports/world-static-mesh-flight-controlled-tick-recipes/verify-gnu.py');helper=imported('pk_gnu_helper',tick.GUARD_RECIPE);stamp,write=owner.stamp,owner.write;commands=helper.Commands(a.output,180);(a.output/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    def sources():return [stamp(p) for p in sorted({Path(r['path']) for r in helper.source_stamps()}|{Path(__file__).resolve(),ROOT/'.github/workflows/verify.yml'})]
    before=sources();write(a.output/'sources-before.json',before);normal_before=parent_before=None;result=dict(schema=1,status='FAIL',actualGNUExecuted=False,normalBuildReconfiguredOrBuilt=False,reusedFreshParentDebugSanitizerBuilds=False,scope=__doc__)
    try:
        need(sys.platform.startswith('linux'),'Actual Linux GNU13 required; other platforms refusal-only')
        fault=helper.load(a.parent);need(fault['status']=='PASS' and fault['actualGNUFaultExecuted'] and fault['sourceStable'] and fault['normalArtifactsAndCompilerStable'] and len(fault['commands'])==1 and fault['commands'][0]['exitCode']==0,'Actual stable fault parent')
        api_path=Path(fault['actualParentVerification']['path']);need(stamp(api_path)==fault['actualParentVerification'],'Actual API parent record unchanged');api=helper.load(api_path);need(api['status']=='PASS' and api['actualGNUExecuted'] and api['actualCxxCompilerVersion'].startswith('13.') and len(api['commands'])==15,'Actual prior C/C++ GNU audit')
        for name,build in [('configure-api-debug',a.debugbuild),('configure-api-sanitized',a.sanbuild)]:
            argv=next(r['argv'] for r in api['commands'] if r['name']==name);need('-B' in argv and Path(argv[argv.index('-B')+1]).resolve()==build,'Exact previously fresh parent build '+name)
        normal_records=helper.load(a.parent.parent/'artifacts-after.json');need(all(stamp(r['path'])==r for r in normal_records),'Actual normal/fault artifacts still identical')
        parent_paths={Path(r['path']) for r in normal_records}|{a.parent,api_path}
        for prefix,build in [('debug',a.debugbuild),('sanitized',a.sanbuild)]:
            for name,count in [('production',46),('harness',2)]:
                rows=helper.load(api_path.parent/(prefix+'-'+name+'-compilation.json'));need(len(rows)==count and all(Path(r['object']['path']).is_relative_to(build) and stamp(r['object']['path'])==r['object'] for r in rows.values()),'Exact already-audited parent '+prefix+' '+name);parent_paths.update(Path(r['object']['path']) for r in rows.values())
            parent_paths.update({build/'CMakeCache.txt',build/'compile_commands.json',build/'pikapika_world_static_mesh_session_api_tests'})
            for lib in ['pikapika_world_static_mesh_session_api','pikapika_world_static_mesh_session_source_wire',owner.LIB,packet.LIB,tick.LIBRARY,'pikapika_world_static_mesh_flight_scheduler','pikapika_core']:parent_paths.update({build/('lib'+lib+'.a'),build/'CMakeFiles'/(lib+'.dir/link.txt')})
        def parent_artifacts():return [stamp(p) for p in sorted(parent_paths)]
        parent_before=parent_artifacts();write(a.output/'parent-artifacts-before.json',parent_before)
        def compilation(build,sanitized=False):
            rows={}
            for target,file in [(LIB,'core/src/world_static_mesh_session_packet_wire.cpp'),(TEST,'tests/world_static_mesh_session_packet_wire_tests.cpp')]:
                for name,row in packet.compile_rows(helper,build,target,{file}).items():tick.strict_command(row['argv'],sanitized=sanitized,werror=True);rows[name]=row
            need(len(rows)==2,'Exactly two actual packet-data TUs');link=shlex.split((build/'CMakeFiles'/(TEST+'.dir/link.txt')).read_text());archives={Path(v).name for v in link if v.endswith('.a')};need(archives=={'lib'+LIB+'.a'},'Pure packet executable links only packet library, no model/core archive');return rows
        normal_rows=compilation(a.normal)
        def normal_artifacts():return [stamp(p) for p in sorted({Path(r['path']) for r in normal_records}|{r['object'] for r in normal_rows.values()}|{a.normal/TEST,a.normal/('lib'+LIB+'.a'),a.normal/'CMakeFiles'/(TEST+'.dir/link.txt'),a.normal/'CMakeFiles'/(LIB+'.dir/link.txt')})]
        normal_before=normal_artifacts();write(a.output/'normal-artifacts-before.json',normal_before);result['actualGNUExecuted']=True
        for prefix,build in [('debug',a.debugbuild),('sanitized',a.sanbuild)]:commands.run(prefix+'-packet-build',['cmake','--build',build,'--target',TEST,'--parallel','2','--verbose'])
        result['reusedFreshParentDebugSanitizerBuilds']=True;debug_rows=compilation(a.debugbuild);san_rows=compilation(a.sanbuild,True)
        need(all('-g' in r['argv'] and '-DNDEBUG' not in r['argv'] for r in debug_rows.values()),'Genuine new Debug objects')
        for label,rows in [('normal',normal_rows),('debug',debug_rows),('sanitized',san_rows)]:write(a.output/(label+'-compilation.json'),{k:dict(argv=r['argv'],directory=str(r['directory']),object=stamp(r['object'])) for k,r in rows.items()})
        captures={};references={};directed={};env={'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
        for label,build in [('normal',a.normal),('debug',a.debugbuild),('sanitized',a.sanbuild)]:
            e=env if label=='sanitized' else None;directed[label]=commands.run(label+'-lifetime',[build/TEST,'--run'],env=e);need(b'caller edit, copy/move and source destruction PASS' in directed[label],'Actual owned lifetime assertions');raw=commands.run(label+'-packet24',[build/TEST,'--fixtures'],env=e);p=a.output/(label+'-packet-wire.json');p.write_bytes(raw);captures[label]=raw;r=json.loads(commands.run(label+'-independent-reference',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session-packet-wire.py',p],env=e));need(r['status']=='PASS' and r['rows']==24 and r['mappedFloatBitValues']==492 and r['negativeZeroOccurrences']==164,'Actual complete pinned packet reference');references[label]=r
        need(captures['normal']==captures['debug']==captures['sanitized'] and directed['normal']==directed['debug']==directed['sanitized'],'All actual whole raw fields/lifetime stdout exact without normalization')
        result.update(status='PASS',actualCompilerVersion=api['actualCxxCompilerVersion'],newProductionTUs=1,newHarnessTUs=1,modelCoreLinked=False,rowsPerBuild=24,mappedFloatBitValues=492,negativeZeroOccurrences=164,normalDebugSanitizedWholeRawExact=True,actualFourFpuModesObservedAndRetained=True,references=references,captures={k:stamp(a.output/(k+'-packet-wire.json')) for k in captures},scope='Actual finite GNU13 packet-data 1production+1harness normal/true Debug/O1 ASan-UBSan. All24/492bit/164negativezero/native vectors/raw exact. Pure packet library only, no model/core archive. Existing C API/model/fault parent artifacts immutable. No packet allocator-fault, all FPU/instruction certificate, model/pump/C ABI/JS/WASM/game acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=sources();write(a.output/'sources-after.json',after);result['sourceStable']=before==after
        if before!=after:result['status']='FAIL'
        if normal_before is not None:
            after=normal_artifacts();write(a.output/'normal-artifacts-after.json',after);result['normalArtifactsStable']=normal_before==after
            if normal_before!=after:result['status']='FAIL'
        if parent_before is not None:
            after=parent_artifacts();write(a.output/'parent-artifacts-after.json',after);result['parentArtifactsStable']=parent_before==after
            if parent_before!=after:result['status']='FAIL'
        result.update(commands=commands.items,recipe=stamp(Path(__file__)));write(a.output/'verification.json',result);print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    return int(result['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
