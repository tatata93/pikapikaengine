"""Actual GNU integer/plain-source wire checks after the actual owner verifier.

Normal is never built/reconfigured. Add only new wire targets to the fresh
parent Debug/sanitizer builds; preserve all previously observed parent objects.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SOURCE='pikapika_world_static_mesh_session_source_wire'
SOURCE_TEST=SOURCE+'_tests'
TOKEN_TEST='pikapika_world_static_mesh_session_wire_tests'
SOURCE_CHECK=ROOT/'scripts/verify-world-static-mesh-session-source-wire.py'
TOKEN_CHECK=ROOT/'scripts/verify-world-static-mesh-session-wire.py'
CONTROLS=HERE/'check-source-wire-reference.py'


def need(ok,message):
    if not ok:raise ValueError(message)


def imported(name,path):
    sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def arguments(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for flag,value in [('normal','build/ci-world-owner'),('sanbuild','build/wfo-san'),('debugbuild','build/wfo-debug'),('output','build/public-checks/owner-wire-gnu'),('parent','build/public-checks/owner-gnu/verification.json')]:p.add_argument('--'+flag,type=Path,default=ROOT/value)
    p.add_argument('--parallel',type=int,default=2);p.add_argument('--command-timeout',type=int,default=600);a=p.parse_args(argv)
    paths=[]
    for key in ['normal','sanbuild','debugbuild','output','parent']:
        value=getattr(a,key).resolve();need(value.is_relative_to(ROOT/'build') and value!=ROOT/'build','Repository build children only');setattr(a,key,value)
        if key!='parent':paths.append(value)
    need(a.output.is_relative_to(ROOT/'build/public-checks') and a.output!=ROOT/'build/public-checks' and not a.output.exists(),'Fresh public-checks child')
    need(a.parent.is_relative_to(ROOT/'build/public-checks') and a.parent!=ROOT/'build/public-checks','Actual parent result within public-checks')
    need(len(set(paths))==4 and 1<=a.parallel<=4 and 30<=a.command_timeout<=1200,'Distinct bounded paths/settings')
    for i,x in enumerate(paths):
        for y in paths[i+1:]:need(not x.is_relative_to(y) and not y.is_relative_to(x),'No build/output overlap')
    need(not a.parent.is_relative_to(a.output),'Parent cannot be inside fresh output');return a


def main():
    a=arguments();os.environ['PYTHONDONTWRITEBYTECODE']='1';a.output.mkdir(parents=True)
    owner=imported('wire_addon_owner',HERE/'verify-gnu.py');packet=imported('wire_addon_packet',ROOT/'reports/world-static-mesh-flight-controlled-scheduler-recipes/verify-gnu.py')
    tick=imported('wire_addon_tick',ROOT/'reports/world-static-mesh-flight-controlled-tick-recipes/verify-gnu.py');clock=imported('wire_addon_clock',ROOT/'reports/world-static-mesh-flight-scheduler-recipes/verify-gnu.py')
    helper=imported('wire_addon_guard',tick.GUARD_RECIPE);advance=imported('wire_addon_advance',tick.ADVANCE_RECIPE);auditor=imported('wire_addon_auditor',tick.AUDITOR)
    stamp,write=owner.stamp,owner.write;commands=helper.Commands(a.output,a.command_timeout)
    (a.output/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());write(a.output/'invocation.json',{'argv':sys.argv,'cwd':str(Path.cwd()),'python':sys.version})
    def sources():
        paths={Path(r['path']) for r in tick.sources()};paths.update({Path(__file__).resolve(),HERE/'verify-gnu.py',CONTROLS,HERE/'GNU_PLAN.md',ROOT/'.github/workflows/verify.yml'})
        return [stamp(p) for p in sorted(paths)]
    before=sources();write(a.output/'sources-before.json',before);normal_before=compiler_before=parent_before=None
    result={'schema':1,'status':'FAIL','actualGNUExecuted':False,'normalBuildReconfiguredOrBuilt':False,'reusedFreshParentDebugSanitizerBuilds':False,'scope':__doc__}
    try:
        need(sys.platform.startswith('linux'),'Actual Linux GNU13 required; other platforms refusal-only')
        parent=helper.load(a.parent);need(parent['status']=='PASS' and parent['actualGNUExecuted'] is True and all(parent[k] is True for k in ['sourceStable','normalArtifactsStable','compilerStable']),'Actual completed stable parent GNU acceptance')
        need(len(parent['commands'])==21 and all(r['exitCode']==0 for r in parent['commands']),'Actual parent21 commands')
        parent_dir=a.parent.parent
        prior_normal=helper.load(parent_dir/'normal-artifacts-after.json');prior_san=helper.load(parent_dir/'sanitized-library-compilation.json')
        prior_san_harness=helper.load(parent_dir/'sanitized-harness-compilation.json')
        need(all(Path(r['path']).is_relative_to(a.normal) for r in prior_normal),'Exact actual parent normal build path')
        need(all(Path(r['object']['path']).is_relative_to(a.sanbuild) for r in prior_san.values()),'Exact actual parent sanitizer build path')
        need(len(prior_san_harness)==12 and all(Path(r['object']['path']).is_relative_to(a.sanbuild) for r in prior_san_harness.values()),'Actual parent twelve sanitizer harness objects')
        debug_build=next(r['argv'] for r in parent['commands'] if r['name']=='debug-build')
        need('--build' in debug_build and Path(debug_build[debug_build.index('--build')+1]).resolve()==a.debugbuild,'Exact actual parent Debug build path')
        parent_paths={Path(r['path']) for r in prior_normal}|{Path(r['object']['path']) for r in [*prior_san.values(),*prior_san_harness.values()]}|{a.parent}
        for record in prior_normal:need(stamp(record['path'])==record,'Normal parent artifact still identical before addon')
        for record in [*prior_san.values(),*prior_san_harness.values()]:need(stamp(record['object']['path'])==record['object'],'Sanitized parent object still identical before addon')
        debug_objects=[]
        for target in [owner.LIB,packet.LIB,tick.LIBRARY,clock.LIBRARY,'pikapika_core']:
            rows=helper.compilation(a.debugbuild,target);debug_objects.extend(r['object'] for r in rows.values())
            parent_paths.update({a.debugbuild/('lib'+target+'.a'),a.debugbuild/'CMakeFiles'/(target+'.dir/link.txt')})
        need(len(debug_objects)==44 and all(p.is_file() for p in debug_objects),'All actual previous44 Debug dependency objects')
        parent_paths.update(debug_objects);parent_paths.update({a.debugbuild/'CMakeCache.txt',a.debugbuild/'compile_commands.json'})
        for target,expected in [(owner.SUPPORT,packet.SERIALIZERS|{'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp'}),(owner.TEST,{'tests/world_static_mesh_session_tests.cpp'})]:
            parent_paths.update(r['object'] for r in packet.compile_rows(helper,a.debugbuild,target,expected).values())
        for build in [a.sanbuild,a.debugbuild]:
            for target in [owner.LIB,packet.LIB,tick.LIBRARY,clock.LIBRARY,'pikapika_core',owner.SUPPORT]:parent_paths.update({build/('lib'+target+'.a'),build/'CMakeFiles'/(target+'.dir/link.txt')})
            targets=[owner.TEST,owner.FULL] if build==a.sanbuild else [owner.TEST]
            for target in targets:parent_paths.update({build/target,build/(target+'.map'),build/'CMakeFiles'/(target+'.dir/link.txt')})
        def parent_artifacts():return [stamp(p) for p in sorted(parent_paths)]
        parent_before=parent_artifacts();write(a.output/'parent-artifacts-before.json',parent_before)
        def profile(build,cfg,sanitized=False):
            pp,libs,core,_,up=packet.profile(helper,tick,clock,advance,auditor,build,cfg);op,own=owner.owner_profile(helper,build,cfg,pp)
            new=helper.compilation(build,SOURCE);need(set(new)=={(ROOT/'core/src/world_static_mesh_session_source_wire.cpp').resolve()},'One actual separate source decoder TU')
            all_libs={**libs,**own,**new};need(len(all_libs)==45,'Actual core40+five independent library TUs')
            for source,row in all_libs.items():
                need(row['object'].is_file(),'Actual built library object')
                if source==ROOT/'core/src/world_static_mesh_session.cpp':owner.own_command(row['argv'],sanitized=sanitized)
                elif source not in core:tick.strict_command(row['argv'],sanitized=sanitized,werror=True)
            if sanitized:helper.check_sanitized_compilation(build,core)
            return op,all_libs,up
        normal_profile,normal_libs,up=profile(a.normal,'Release');compiler=Path(up['compiler']['path']);compiler_before=stamp(compiler)
        need(re.fullmatch(r'13(?:\.[0-9]+)*',parent['actualCompilerVersion']) and parent['actualCompilerTarget'].startswith('x86_64'),'Actual parent GNU13/x64')
        need(parent['normalProfile']==normal_profile,'Same actual normal owner configured provenance');result['actualGNUExecuted']=True
        def harnesses(build,sanitized=False):
            collected={}
            for target,source in [(SOURCE_TEST,'tests/world_static_mesh_session_source_wire_tests.cpp'),(TOKEN_TEST,'tests/world_static_mesh_session_wire_tests.cpp')]:
                for name,row in packet.compile_rows(helper,build,target,{source}).items():
                    if target==SOURCE_TEST:tick.strict_command(row['argv'],sanitized=sanitized,werror=True)
                    else:
                        argv=row['argv'];need({'-Wall','-Wextra','-Wpedantic','-Werror','-fno-lto'}<=set(argv) and not any(re.match(r'-flto(?:=|$)',v) for v in argv),'Actual integer-only diagnostics/no-LTO')
                        if sanitized:
                            need(set(helper.SANITIZERS)<=set(argv),'Actual integer TU instrumented');optimizations=[v for v in argv if re.fullmatch(r'-O(?:[0-3sgz]|fast)',v)];need(optimizations and all(v=='-O1' for v in optimizations) and '-DNDEBUG' in argv,'Actual integer O1 only')
                    collected[target+':'+name]=row
            need(len(collected)==2,'Exactly two actual wire harness TUs')
            link=shlex.split((build/'CMakeFiles'/(SOURCE_TEST+'.dir/link.txt')).read_text())
            for lib in [SOURCE,owner.LIB,packet.LIB,tick.LIBRARY,clock.LIBRARY,'pikapika_core']:need(any(Path(v).name=='lib'+lib+'.a' for v in link),'Actual source test links dependency '+lib)
            return collected
        normal_harness=harnesses(a.normal)
        def observed(rows):return {str(k):{'argv':v['argv'],'directory':str(v['directory']),'object':stamp(v['object'])} for k,v in rows.items()}
        def normal_artifacts():
            paths={a.normal/'CMakeCache.txt',a.normal/'compile_commands.json'}
            for target in [SOURCE,owner.LIB,packet.LIB,tick.LIBRARY,clock.LIBRARY,'pikapika_core']:paths.update({a.normal/('lib'+target+'.a'),a.normal/'CMakeFiles'/(target+'.dir/link.txt')})
            for target in [SOURCE_TEST,TOKEN_TEST]:paths.update({a.normal/target,a.normal/'CMakeFiles'/(target+'.dir/link.txt')})
            paths.update(r['object'] for r in [*normal_libs.values(),*normal_harness.values()]);return [stamp(p) for p in sorted(paths)]
        normal_before=normal_artifacts();write(a.output/'normal-artifacts-before.json',normal_before);write(a.output/'normal-library-compilation.json',observed(normal_libs));write(a.output/'normal-wire-compilation.json',observed(normal_harness))
        for prefix,build in [('debug',a.debugbuild),('sanitized',a.sanbuild)]:commands.run(prefix+'-build-new-wires',['cmake','--build',build,'--target',SOURCE_TEST,TOKEN_TEST,'--parallel',a.parallel,'--verbose'])
        result['reusedFreshParentDebugSanitizerBuilds']=True
        debug_profile,debug_libs,_=profile(a.debugbuild,'Debug');san_profile,san_libs,_=profile(a.sanbuild,'Release',True)
        debug_harness=harnesses(a.debugbuild);san_harness=harnesses(a.sanbuild,True)
        for row in [*debug_libs.values(),*debug_harness.values()]:need('-g' in row['argv'] and '-DNDEBUG' not in row['argv'],'All actual Debug objects genuine')
        write(a.output/'debug-library-compilation.json',observed(debug_libs));write(a.output/'sanitized-library-compilation.json',observed(san_libs));write(a.output/'sanitized-wire-compilation.json',observed(san_harness))
        env={'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1','PYTHONDONTWRITEBYTECODE':'1'}
        runs={}
        for prefix,build in [('normal',a.normal),('debug',a.debugbuild),('sanitized',a.sanbuild)]:
            e=env if prefix=='sanitized' else None
            directed=commands.run(prefix+'-source-lifetime',[build/SOURCE_TEST,'--run'],env=e);need(b'caller/decoded/actual owner/old read lifetime PASS' in directed,'Actual source lifetime assertions')
            token_directed=commands.run(prefix+'-integer-vectors',[build/TOKEN_TEST,'--run'],env=e);need(b'24 known integer vectors' in token_directed,'Actual known integer vectors')
            raw=commands.run(prefix+'-source27',[build/SOURCE_TEST,'--fixtures'],env=e);source=a.output/(prefix+'-source27.json');source.write_bytes(raw)
            raw_token=commands.run(prefix+'-token77',[build/TOKEN_TEST,'--fixtures'],env=e);token=a.output/(prefix+'-token77.json');token.write_bytes(raw_token)
            sr=json.loads(commands.run(prefix+'-source-reference',[sys.executable,'-B',SOURCE_CHECK,source],env=e));tr=json.loads(commands.run(prefix+'-token-reference',[sys.executable,'-B',TOKEN_CHECK,token],env=e))
            need(sr['status']=='PASS' and sr['rows']==27 and sr['mappedFloatBitValues']==604 and tr['status']=='PASS' and tr['rows']==77,'Actual independent mapped source and integer references')
            runs[prefix]={'rawSource':raw,'rawToken':raw_token,'source':source,'token':token,'sourceReference':sr,'tokenReference':tr,'sourceCapture':stamp(source),'tokenCapture':stamp(token),'directed':directed,'tokenDirected':token_directed}
        for prefix in ['debug','sanitized']:
            need(all(runs[prefix][key]==runs['normal'][key] for key in ['rawSource','rawToken','directed','tokenDirected']),'All actual raw wire values/stdout equal, no identity stripping')
            controls=json.loads(commands.run(prefix+'-source-controls',[sys.executable,'-B',CONTROLS,'--release',runs['normal']['source'],'--debug',runs[prefix]['source'],'--output',a.output/(prefix+'-source-controls')]))
            need(controls['status']=='PASS' and controls['copiedNegativeControls']==13 and controls['actualOptimizedPythonRefused'] is True,'Actual source13 controls and -O process')
        optimized_argv=[sys.executable,'-O',str(TOKEN_CHECK),str(runs['normal']['token'])]
        optimized=subprocess.run(optimized_argv,cwd=ROOT,capture_output=True,timeout=30)
        (a.output/'token-optimized.stdout.txt').write_bytes(optimized.stdout);(a.output/'token-optimized.stderr.txt').write_bytes(optimized.stderr)
        write(a.output/'token-optimized.command.json',{'argv':optimized_argv,'exitCode':optimized.returncode})
        need(optimized.returncode!=0 and b'normal Python' in optimized.stderr,'Actual integer checker -O refusal')
        result.update(status='PASS',actualCompilerVersion=parent['actualCompilerVersion'],actualCompilerTarget=parent['actualCompilerTarget'],parentVerification=stamp(a.parent),libraryTranslationUnits=45,newWireHarnessTranslationUnits=2,sourceRowsPerBuild=27,tokenRowsPerBuild=77,sourceMappedFloatBitValues=604,copiedSourceRejectionsPerComparison=13,actualIntegerOptimizedProcessRefused=True,normalDebugSanitizedWholeRawExact=True,normalProfile=normal_profile,debugProfile=debug_profile,sanitizedProfile=san_profile,captures={k:{'source':v['sourceCapture'],'token':v['tokenCapture']} for k,v in runs.items()},references={k:{'source':v['sourceReference'],'token':v['tokenReference']} for k,v in runs.items()},scope='Actual GNU13 normal/genuine Debug/all45 production+two wire harness TUs O1 ASan-UBSan. Whole27 source/77 integer captures exact in all three builds with no normalization. Existing parent44 objects/normal artifacts monitored. No new allocator faults, general plane-boundary proof, mesh/arbitrary guard, C ABI/JS/WASM/model step acceptance.')
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
        if compiler_before is not None:
            result['compilerStable']=compiler_before==stamp(compiler)
            if not result['compilerStable']:result['status']='FAIL'
        result.update(commands=commands.items,recipe=stamp(Path(__file__)));write(a.output/'verification.json',result);print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
