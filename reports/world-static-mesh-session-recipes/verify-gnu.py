"""Actual GNU13 owned sessions: normal, real Debug, all44-dependency ASan/UBSan.

Normal build is immutable. Windows performs refusal only. Configured ownership
provenance is not a numerical profile, artifact certificate or runtime unlock.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import os
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
LIB='pikapika_world_static_mesh_session'
SUPPORT='pikapika_session_fixture_support'
TEST,FULL,ALLOC=LIB+'_tests',LIB+'_fixtures',LIB+'_allocation_tests'
MODULE=ROOT/'cmake/PikapikaWorldStaticMeshSessionConfiguration.cmake'
OPTIONS=['-Wall','-Wextra','-Wpedantic','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']


def need(ok,message):
    if not ok:raise ValueError(message)


def imported(name,path):
    sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def stamp(p):
    p=Path(p).resolve();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha256(b).hexdigest()}


def write(p,data):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def reports(data):
    need(data.get('kind')=='world-static-mesh-session-fixtures' and len(data['fixtures'])==77,'Actual complete77 owner history')
    for row in data['fixtures']:
        if row['kind']=='pump' and row['result']['report'] is not None:yield 0,row['result']['report']
        for pump in row['retainedPumps']:
            if pump['report'] is not None:yield 1,pump['report']


def map_ids(data,ids,replace):
    counts=[[0]*8 for _ in range(2)]
    def leaf(binding,key,family,where,slot):
        need(binding[key]==ids[family],'Exact observed numerical binding leaf')
        binding[key]=replace[family];counts[where][slot]+=1
    for where,r in reports(data):
        for key,family,slot in [('buildId','packet',0),('controlledBuildId','controlled',1),('schedulerBuildId','clock',2),('upstreamBuildId','advance',3)]:leaf(r['binding'],key,family,where,slot)
        for tick in r['tickReports']:
            if tick is None:continue
            c=tick['report'];leaf(c['binding'],'buildId','controlled',where,4);leaf(c['binding'],'upstreamBuildId','advance',where,5)
            if c['child'] is not None:
                leaf(c['child']['binding'],'buildId','advance',where,6)
                if c['child']['guard'] is not None:leaf(c['child']['guard']['binding'],'buildId','advance',where,7)
    need(counts==[[10,10,10,10,18,18,18,18],[52,52,52,52,92,92,92,92]],'Exactly688 numerical ID leaves at16 result/retained path patterns')
    return counts


def compare_full(helper,normal,sanitized,normal_ids,sanitized_ids):
    keys={'packet','controlled','clock','advance'}
    for ids in [normal_ids,sanitized_ids]:need(type(ids) is dict and set(ids)==keys and len(set(ids.values()))==4 and all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in ids.values()),'Four distinct exact numerical identity families')
    need(all(normal_ids[k]!=sanitized_ids[k] for k in keys),'Actual distinct normal/instrumented numerical IDs')
    trees=[];counts=[]
    for source,ids in [(normal,normal_ids),(sanitized,sanitized_ids)]:
        data=deepcopy(source);counts.append(map_ids(data,ids,{k:'<'+k+'-configured-numerical-source-only>' for k in keys}));trees.append(helper.exact_tree(data))
    need(trees[0]==trees[1],'Whole typed/ordered/IEEE64 owner history differs outside16 exact numerical identity paths')
    return {'status':'PASS','rows':77,'identityFamilies':4,'pathPatterns':16,'normalizedLeavesPerSide':counts,'normalIds':normal_ids,'sanitizedIds':sanitized_ids,'treeSha256':sha256(json.dumps(trees[0],ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
            'scope':'All public reads, snapshots, actual current and retained reports, fixed unused slots, scalar types, IEEE64/signed-zero and array/key order exact. No invented owner runtime ID or blanket stripping.'}


def own_command(argv,*,sanitized=False):
    need(set(OPTIONS)<=set(argv),'Actual owner strict/no-LTO/fatal-warning options')
    need(not any(v in {'-ffast-math','-Ofast','-funsafe-math-optimizations','-ffinite-math-only','-fassociative-math','-ffp-contract=fast','-fno-rounding-math','-mfpmath=387'} or re.match(r'-flto(?:=|$)',v) for v in argv),'No conflicting owner compiler options')
    if sanitized:
        need({'-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer'}<=set(argv),'Actual owner TU instrumented')
        optimizations=[v for v in argv if re.fullmatch(r'-O(?:[0-3sgz]|fast)',v)];need(optimizations and all(v=='-O1' for v in optimizations) and '-DNDEBUG' in argv,'Actual owner O1/NDEBUG only')


def owner_profile(helper,build,configuration,parent):
    rows=helper.compilation(build,LIB);need(set(rows)=={(ROOT/'core/src/world_static_mesh_session.cpp').resolve()},'One actual separate owner source TU')
    d=helper.load(build/('world-owned-session-configuration-'+configuration+'.json'));m=d['identityMaterial']
    need(d['schema']==1 and type(d['schema']) is int and d['configuredSource'] is True and d['artifactAuditComplete'] is False,'Configured ownership provenance only')
    need(re.fullmatch('[0-9a-f]{64}',d['configurationId']) and sha256(json.dumps(m,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==d['configurationId'],'Independent owner configured identity formula')
    expected={'identitySchema':1,'sourceSet':'world-static-mesh-session-owner-v1','configuration':configuration,'compilerId':'GNU','compilerVersion':parent['identityMaterial']['compilerVersion'],'system':'Linux','architecture':'x86_64','pointerBytes':'8','generator':'Unix Makefiles','generatorPlatform':'','runtimeLibrary':'','helperSha256':stamp(MODULE)['sha256'],'numericalParentBuildId':parent['buildId'],'numericalParentProfile':int(configuration=='Release'),'compileOptions':OPTIONS,'IPO':False}
    for key,value in expected.items():need(m[key]==value and type(m[key]) is type(value),'Actual owner material '+key)
    need(Path(m['compilerPath']).resolve()==Path(parent['identityMaterial']['compilerPath']).resolve(),'Actual same compiler')
    cache=helper.cache(build);need(m['globalFlags']==cache.get('CMAKE_CXX_FLAGS','') and m['configurationFlags']==cache.get('CMAKE_CXX_FLAGS_'+configuration.upper(),''),'Actual owner cache flags bound')
    need(len(m['sources'])==2 and {r['path'] for r in m['sources']}=={'core/include/pikapika/world_static_mesh_session.hpp','core/src/world_static_mesh_session.cpp'},'Exactly own header/source2')
    for row in m['sources']:need(row['sha256']==stamp(ROOT/row['path'])['sha256'] and row['flags']==(OPTIONS if row['path'].endswith('.cpp') else []),'Actual owner source hash/options')
    own_command(next(iter(rows.values()))['argv']);return d,rows


def arguments(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for flag,value in [('normal','build/ci-world-owner'),('output','build/public-checks/owner-gnu'),('sanbuild','build/wfo-san'),('debugbuild','build/wfo-debug')]:p.add_argument('--'+flag,type=Path,default=ROOT/value)
    p.add_argument('--parallel',type=int,default=2);p.add_argument('--command-timeout',type=int,default=600);a=p.parse_args(argv);paths=[]
    for key in ['normal','output','sanbuild','debugbuild']:
        value=getattr(a,key).resolve();need(value.is_relative_to(ROOT/'build') and value!=ROOT/'build','Repository build children only');setattr(a,key,value);paths.append(value)
    need(a.output.is_relative_to(ROOT/'build/public-checks') and a.output!=ROOT/'build/public-checks','Fresh public-checks output child')
    need(len(set(paths))==4 and 1<=a.parallel<=4 and 30<=a.command_timeout<=1200,'Distinct bounded paths/settings')
    for i,x in enumerate(paths):
        for y in paths[i+1:]:need(not x.is_relative_to(y) and not y.is_relative_to(x),'No path overlap')
    for x in [a.output,a.sanbuild,a.debugbuild]:need(not x.exists(),'Never overwrite output or historical build')
    return a


def main():
    a=arguments();os.environ['PYTHONDONTWRITEBYTECODE']='1';a.output.mkdir(parents=True);write(a.output/'invocation.json',{'argv':sys.argv,'cwd':str(Path.cwd()),'python':sys.version});(a.output/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    q=imported('owner_gnu_packet',ROOT/'reports/world-static-mesh-flight-controlled-scheduler-recipes/verify-gnu.py')
    tick=imported('owner_gnu_tick',ROOT/'reports/world-static-mesh-flight-controlled-tick-recipes/verify-gnu.py');clock=imported('owner_gnu_clock',ROOT/'reports/world-static-mesh-flight-scheduler-recipes/verify-gnu.py')
    helper=imported('owner_gnu_guard',tick.GUARD_RECIPE);advance=imported('owner_gnu_advance',tick.ADVANCE_RECIPE);auditor=imported('owner_gnu_auditor',tick.AUDITOR)
    commands=helper.Commands(a.output,a.command_timeout)
    def sources():
        paths={Path(x['path']) for x in tick.sources()};paths.update({Path(__file__).resolve(),HERE/'GNU_PLAN.md',ROOT/'reports/world-static-mesh-flight-controlled-scheduler-recipes/verify-gnu.py',ROOT/'reports/world-static-mesh-flight-scheduler-recipes/verify-gnu.py'})
        return [stamp(p) for p in sorted(paths)]
    before=sources();write(a.output/'sources-before.json',before);normal_before=compiler_before=None
    result={'schema':1,'status':'FAIL','actualGNUExecuted':False,'normalBuildReconfiguredOrBuilt':False,'scope':__doc__,'SDKChanged':False,'machineClockCommitProofComplete':False}
    try:
        need(sys.platform.startswith('linux'),'Actual Linux GNU13 required; other platforms refusal-only')
        advance.checked_normal_cache(helper,a.normal)
        def profile(build,cfg):
            parent,libs,core,ids,upstream=q.profile(helper,tick,clock,advance,auditor,build,cfg);own,rows=owner_profile(helper,build,cfg,parent);all_libs={**libs,**rows};need(len(all_libs)==44,'Actual core40 plus four separate library TUs');return own,all_libs,core,ids,upstream
        normal_profile,libraries,core,normal_ids,upstream=profile(a.normal,'Release');compiler=Path(upstream['compiler']['path']);compiler_before=stamp(compiler)
        need(b'Free Software Foundation' in commands.run('compiler-version',[compiler,'--version']),'Actual GNU compiler')
        version=commands.run('compiler-full-version',[compiler,'-dumpfullversion','-dumpversion']).decode().strip();machine=commands.run('compiler-target',[compiler,'-dumpmachine']).decode().strip()
        need(version==upstream['compiler']['version'] and re.fullmatch(r'13(?:\.[0-9]+)*',version) and machine.startswith('x86_64'),'Actual GNU13/x64 agrees');result['actualGNUExecuted']=True
        wanted={SUPPORT:q.SERIALIZERS|{'tests/world_static_mesh_flight_controlled_scheduler_fixtures.cpp'},TEST:{'tests/world_static_mesh_session_tests.cpp'},FULL:{'tests/world_static_mesh_session_fixtures.cpp'}}
        def harnesses(build,*,sanitized=False,allocation=False):
            targets=dict(wanted)
            if allocation:targets[ALLOC]={'tests/world_static_mesh_session_allocation_tests.cpp'}
            collected={}
            for target,expected in targets.items():
                for source,row in q.compile_rows(helper,build,target,expected).items():
                    tick.strict_command(row['argv'],sanitized=sanitized,werror=(target!=SUPPORT or source in q.WARN))
                    if target==SUPPORT:
                        for macro in ['PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY','PIKAPIKA_CONTROLLED_SCHEDULER_FIXTURE_LIBRARY_ONLY']:need(tick.definitions(row['argv'],macro)==['1'],'Actual serializer library-only definitions')
                    collected[target+':'+source]=row
            need(len(collected)==(13 if allocation else 12),'Exact target-specific harness TU count');return collected
        normal_harness=harnesses(a.normal,allocation=True)
        def artifacts():
            paths={a.normal/'CMakeCache.txt',a.normal/'compile_commands.json'}
            for stem in ['world-flight-binding-','world-flight-controlled-tick-binding-','world-flight-scheduler-binding-','world-flight-controlled-scheduler-binding-','world-owned-session-configuration-']:paths.add(a.normal/(stem+'Release.json'))
            for target in [LIB,SUPPORT,'pikapika_core',q.LIB,tick.LIBRARY,clock.LIBRARY]:paths.update({a.normal/('lib'+target+'.a'),a.normal/'CMakeFiles'/(target+'.dir/link.txt')})
            for target in [TEST,FULL,ALLOC]:paths.update({a.normal/target,a.normal/(target+'.map'),a.normal/'CMakeFiles'/(target+'.dir/link.txt')})
            paths.update(r['object'] for r in [*libraries.values(),*normal_harness.values()]);return [stamp(p) for p in sorted(paths)]
        def observed(rows):return {str(k):{'argv':v['argv'],'directory':str(v['directory']),'object':stamp(v['object'])} for k,v in rows.items()}
        normal_before=artifacts();write(a.output/'normal-artifacts-before.json',normal_before);write(a.output/'normal-library-compilation.json',observed(libraries));write(a.output/'normal-harness-compilation.json',observed(normal_harness))
        warning=a.output/'warning-objects';warning.mkdir()
        for i,source in enumerate(['core/src/world_static_mesh_session.cpp','tests/world_static_mesh_session_tests.cpp','tests/world_static_mesh_session_fixtures.cpp','tests/world_static_mesh_session_allocation_tests.cpp']):
            if source.startswith('core/'):row=libraries[(ROOT/source).resolve()]
            else:
                target=ALLOC if source.endswith('_allocation_tests.cpp') else TEST if source.endswith('_tests.cpp') else FULL
                row=normal_harness[target+':'+source]
            argv=list(row['argv']);argv[argv.index('-o')+1]=str(warning/(str(i)+'.o'));tick.compile_at(commands,'werror-'+str(i),argv,row['directory'])
        def run(build,prefix,env=None):
            directed=commands.run(prefix+'-directed',[build/TEST,'--run'],env=env);need(b'13 lifecycle and 5 actual numerical groups PASS' in directed,'Actual18 owner assertions')
            raw=commands.run(prefix+'-full77',[build/FULL,'--fixtures'],env=env);path=a.output/(prefix+'-full.json');path.write_bytes(raw)
            ref=json.loads(commands.run(prefix+'-independent',[sys.executable,'-B',ROOT/'scripts/verify-world-static-mesh-session.py',path],env=env));need(ref['status']=='PASS' and ref['rows']==77 and ref['pump']['controlled']['child']['guard']['childCalls']==54,'Actual independent77/54 math children')
            controls=json.loads(commands.run(prefix+'-controls',[sys.executable,'-B',ROOT/'tests/world_static_mesh_session_reference_tests.py',path,'--output',a.output/(prefix+'-controls')],env=env));need(controls['status']=='PASS' and controls['copiedRejectionControls']==65 and controls['actualOptimizedPythonRefused'] is True,'Actual independent65 rejection controls / real -O refusal')
            return {'raw':raw,'data':helper.load(path),'directed':directed,'reference':ref,'controls':controls,'capture':stamp(path)}
        normal=run(a.normal,'normal')
        allocation=json.loads(commands.run('normal-actual-allocation',[a.normal/ALLOC]));need(allocation['status']=='PASS' and allocation['kind']=='actual-owned-session-allocation-injection','Actual GNU compiled allocation assertions, not a copied MSVC count')
        total=0
        for operation in ['create','reset','read']:
            count=allocation['baselineAllocationAttempts'][operation];need(type(count) is int and 1<=count<=32,'Actual measured finite allocation attempts');rows=[r for r in allocation['failures'] if r['operation']==operation];need([r['failAfter'] for r in rows]==list(range(count)),'Every actually observed global-new position tested')
            for row in rows:need(row['actualAttempts']==row['failAfter']+1 and all(row[k] is True for k in ['activeStateRetained','pastSnapshotRetained','nextOperationValid']),'Actual retained state/recovery')
            total+=count
        need(total==allocation['actualAllocationFailures']==len(allocation['failures']),'Actual complete failure count')
        need(allocation['actualBusyChecks']==5 and len(allocation['busyReentry'])==5 and {r['operation'] for r in allocation['busyReentry']}=={'create','reset','read','destroy','pump'},'Actual five reentry operations')
        for row in allocation['busyReentry']:need(row['actualCallbacks']==1 and row['outerReadAllocations']>0 and all(row[k] is True for k in ['busyRefused','noOutputOrModelCall','stateUnchanged']),'Actual GNU allocator reentry assertions')
        common=['-G','Unix Makefiles','-DCMAKE_CXX_COMPILER='+str(compiler),'-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DBUILD_TESTING=ON']
        commands.run('debug-configure',['cmake','-S',ROOT,'-B',a.debugbuild,*common,'-DCMAKE_BUILD_TYPE=Debug']);commands.run('debug-build',['cmake','--build',a.debugbuild,'--target',TEST,'--parallel',a.parallel,'--verbose'])
        debug_profile,debug_libs,_,_,_=profile(a.debugbuild,'Debug')
        for row in debug_libs.values():need('-g' in row['argv'] and '-DNDEBUG' not in row['argv'],'Real Debug owner and all actual dependencies')
        need(b'actual default model refusal PASS' in commands.run('debug-refusal',[a.debugbuild/TEST,'--unsupported-profile']),'Actual Debug numerical refusal preserves owned data')
        flags=' '.join(['-O1','-g',*helper.SANITIZERS]);commands.run('sanitizer-configure',['cmake','-S',ROOT,'-B',a.sanbuild,*common,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_FLAGS='+flags,'-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG','-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'])
        commands.run('sanitizer-build-all-dependencies',['cmake','--build',a.sanbuild,'--target',TEST,FULL,'--parallel',a.parallel,'--verbose'])
        san_profile,san_libs,_,san_ids,_=profile(a.sanbuild,'Release');write(a.output/'sanitized-core-compilation.json',helper.check_sanitized_compilation(a.sanbuild,core))
        for source,row in san_libs.items():
            if source==ROOT/'core/src/world_static_mesh_session.cpp':own_command(row['argv'],sanitized=True)
            elif source not in core:tick.strict_command(row['argv'],sanitized=True,werror=True)
        write(a.output/'sanitized-library-compilation.json',observed(san_libs));write(a.output/'sanitized-harness-compilation.json',observed(harnesses(a.sanbuild,sanitized=True)))
        env={'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1','PYTHONDONTWRITEBYTECODE':'1'};san=run(a.sanbuild,'sanitized',env)
        need(normal['directed']==san['directed'],'Actual normal/sanitized directed stdout exact');comparison=compare_full(helper,normal['data'],san['data'],normal_ids,san_ids)
        replaced=san['raw']
        for family in sorted(san_ids):replaced=replaced.replace(san_ids[family].encode(),normal_ids[family].encode())
        need(replaced==normal['raw'],'Actual GNU ABI raw exact outside16 already validated numerical-ID paths');comparison['allOtherRawBytesExact']=True;write(a.output/'full-comparison.json',comparison)
        result.update(status='PASS',actualCompilerVersion=version,actualCompilerTarget=machine,normalProfile=normal_profile,debugProfile=debug_profile,sanitizedProfile=san_profile,fullComparison=comparison,references={k:v['reference'] for k,v in [('normal',normal),('sanitized',san)]},controls={k:v['controls'] for k,v in [('normal',normal),('sanitized',san)]},captures={k:v['capture'] for k,v in [('normal',normal),('sanitized',san)]},actualNormalAllocation=allocation,libraryTranslationUnits=44,harnessSanitizedTranslationUnits=12,harnessNormalTranslationUnits=13,warningTranslationUnits=4,fullRowsPerBuild=77,copiedRejectionsPerBuild=65,actualAllocatorFaultTestSanitized=False,scope='Finite actual GNU13 normal/real Debug/all44 production plus12 support/driver TU O1 ASan-UBSan. Normal-only measured global-new failure/reentry executable; producer scope text is historical, actual compiler/platform is audited here. No OS OOM, all allocator paths, new instruction/clock/commit, whole heap/deadline, SDK or game acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=sources();write(a.output/'sources-after.json',after);result['sourceStable']=before==after
        if before!=after:result['status']='FAIL'
        if normal_before is not None:
            after=artifacts();write(a.output/'normal-artifacts-after.json',after);result['normalArtifactsStable']=normal_before==after
            if normal_before!=after:result['status']='FAIL'
        if compiler_before is not None:
            result['compilerStable']=compiler_before==stamp(compiler_before['path'])
            if not result['compilerStable']:result['status']='FAIL'
        result.update(commands=commands.items,recipe=stamp(Path(__file__)));write(a.output/'verification.json',result);print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
