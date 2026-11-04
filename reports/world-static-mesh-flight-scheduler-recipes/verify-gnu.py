"""GNU13 scheduler full-transcript driver; no normal rebuild or machine claim.

Normal four targets must already be built by main CMake. Fresh Debug and O1
ASan/UBSan use main CMake with all linked core/serializer dependencies. Windows
can exercise only CLI/refusal and pure comparison helpers, never actual GNU.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import re
import shlex
import sys
import importlib.util
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
ADVANCE_RECIPE = ROOT/'reports/world-static-mesh-flight-advance-recipes/verify-gnu.py'
GUARD_RECIPE = ROOT/'reports/world-static-mesh-flight-guard-recipes/verify-gnu.py'
AUDITOR = ROOT/'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'
PLAN = Path(__file__).with_name('GNU_PLAN.md')
MODULE = ROOT/'cmake/PikapikaWorldFlightSchedulerBinding.cmake'
CHECKER = ROOT/'scripts/verify-world-static-mesh-flight-scheduler.py'
CONTROLS = ROOT/'tests/world_static_mesh_flight_scheduler_reference_tests.py'
CREDIT = ROOT/'scripts/verify-world-static-mesh-flight-scheduler-credit.py'
LIBRARY = 'pikapika_world_static_mesh_flight_scheduler'
TEST = LIBRARY+'_tests'
FULL = LIBRARY+'_fixtures'
SCHEDULER_SOURCES = {'core/include/pikapika/world_static_mesh_flight_scheduler.hpp',
                     'core/src/world_static_mesh_flight_scheduler.cpp'}
PROFILE_STEM = 'world-flight-scheduler-binding-'
SCHEDULER_OPTIONS = ['-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto',
    '-Wall','-Wextra','-Wpedantic','-Werror','-fexcess-precision=standard','-mfpmath=sse','-msse2']
WARN = ('core/src/world_static_mesh_flight_scheduler.cpp',
        'tests/world_static_mesh_flight_scheduler_tests.cpp',
        'tests/world_static_mesh_flight_scheduler_fixtures.cpp',
        'tests/world_static_mesh_flight_advance_fixtures.cpp')


def need(value, message):
    if not value:
        raise ValueError(message)


def import_file(name, path):
    sys.dont_write_bytecode = True
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def stamp(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}


def write(path, value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')


def compile_at(commands, name, argv, directory):
    """Replay an argv vector directly; CMake -E chdir reserializes -D quotes."""
    argv=list(map(str,argv));directory=str(Path(directory).resolve())
    record={'name':name,'argv':argv,'cwd':directory,'environmentOverrides':{}}
    started=time.monotonic()
    try:
        done=subprocess.run(argv,cwd=directory,capture_output=True,timeout=commands.timeout)
        record['exitCode'],stdout,stderr=done.returncode,done.stdout,done.stderr
    except subprocess.TimeoutExpired as error:
        record.update(exitCode=None,exception='TimeoutExpired: '+str(error))
        stdout,stderr=error.stdout or b'',(error.stderr or b'')+str(error).encode()
    except BaseException as error:
        record.update(exitCode=None,exception=type(error).__name__+': '+str(error))
        stdout,stderr=b'',str(error).encode()
    record['elapsedSeconds']=time.monotonic()-started
    for key,raw in (('stdout',stdout),('stderr',stderr)):
        path=commands.output/(name+'.'+key+'.txt');path.write_bytes(raw);record[key]=stamp(path)
    commands.items.append(record);write(commands.output/(name+'.command.json'),record)
    if record['exitCode']!=0:
        print(json.dumps({'failedCommand':name,'exitCode':record['exitCode'],
              'stdout':stdout.decode('utf-8',errors='replace'),'stderr':stderr.decode('utf-8',errors='replace')},ensure_ascii=False),flush=True)
    need(record['exitCode']==0,'Command failed: '+name)
    return stdout


def sources():
    paths={Path(__file__).resolve(),PLAN,MODULE,ADVANCE_RECIPE,GUARD_RECIPE,AUDITOR,CHECKER,CONTROLS,CREDIT,ROOT/'CMakeLists.txt'}
    for folder,suffixes in (('core',{'.cpp','.h','.hpp'}),('tests',{'.cpp','.h','.hpp','.py'}),
                            ('scripts',{'.py'}),('cmake',{'.cmake'})):
        paths.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in suffixes)
    for relative in ('assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json',
        'build/native/Release/pikapika_core.lib','build/native/pikapika_core.dir/Release/core.obj',
        'build/native/Release/pikapika_world_static_mesh_flight_guard_tests.exe','build/native/Release/world-flight-guard.map',
        'build/native/world-flight-binding-Release.json'):
        if (ROOT/relative).is_file():paths.add(ROOT/relative)
    return [stamp(p) for p in sorted(paths)]


def targets(advance):
    out=deepcopy(advance.TARGET_SOURCES)
    out.pop(advance.GUARD)
    out[TEST]={'tests/world_static_mesh_flight_scheduler_tests.cpp'}
    out[FULL]=out[advance.FIXTURES]|{'tests/world_static_mesh_flight_scheduler_fixtures.cpp'}
    return out


def definitions(argv, name):
    prefix='-D'+name+'='
    return [v[len(prefix):].replace('\\','').strip('"') for v in argv if v.startswith(prefix)]


def strict_command(argv, *, sanitized=False, werror=False):
    required={'-std=c++20','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto',
              '-fexcess-precision=standard','-mfpmath=sse','-msse2'}
    need(required<=set(argv),'Actual strict binary64/no-LTO compiler flags')
    need(not any(v in {'-ffast-math','-Ofast','-funsafe-math-optimizations','-ffinite-math-only',
                      '-fassociative-math','-ffp-contract=fast','-mfpmath=387','-fexcess-precision=fast'} or
                 re.match(r'-flto(?:=|$)',v) for v in argv),'No conflicting unsafe compiler options')
    if werror:
        need({'-Wall','-Wextra','-Wpedantic','-Werror'}<=set(argv),'Actual new/shared TU diagnostic policy')
    if sanitized:
        need({'-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer'}<=set(argv),
             'Every actual dependency command instrumented')
        optimizations=[v for v in argv if re.fullmatch(r'-O(?:[0-3sgz]|fast)',v)]
        need(optimizations and all(v=='-O1' for v in optimizations) and '-DNDEBUG' in argv,'Actual O1/NDEBUG only')


def library_compilation(helper, build):
    """Keep old core40 separate from the independently linked scheduler TU."""
    core={source:item for source,item in helper.compilation(build).items()
          if item['object'].is_relative_to(build/'CMakeFiles/pikapika_core.dir')}
    need(len(core)==40 and (ROOT/'core/src/world_static_mesh_flight_scheduler.cpp').resolve() not in core,
         'Exact unchanged pikapika_core forty actual TU commands')
    scheduler={};source=(ROOT/'core/src/world_static_mesh_flight_scheduler.cpp').resolve()
    for entry in helper.load(build/'compile_commands.json'):
        directory=Path(entry['directory']);actual=Path(entry['file'])
        actual=(actual if actual.is_absolute() else directory/actual).resolve()
        if actual!=source:continue
        argv=entry.get('arguments') or shlex.split(entry['command'])
        need('-o' in argv and argv.index('-o')+1<len(argv),'Actual independent library object argument')
        obj=Path(argv[argv.index('-o')+1]);obj=(obj if obj.is_absolute() else directory/obj).resolve()
        if not obj.is_relative_to(build/'CMakeFiles'/(LIBRARY+'.dir')):continue
        need(not scheduler,'Unique scheduler independent-library compiler entry')
        scheduler[source]={'argv':argv,'directory':str(directory),'object':obj}
    need(len(scheduler)==1,'Exactly one actual scheduler library TU, not an unbuilt same-source target')
    return core,scheduler,{**core,**scheduler}


def checked_scheduler_profile(helper, build, configuration, upstream, compiled=None):
    data=helper.load(build/(PROFILE_STEM+configuration+'.json'));material=data.get('identityMaterial',{})
    need(type(data.get('schema')) is int and data['schema']==1 and data.get('sourceSet')=='world-static-mesh-flight-scheduler-v1',
         'Separate formal scheduler two-source identity')
    profile=1 if configuration=='Release' else 0
    need(type(data.get('profile')) is int and data['profile']==profile and data.get('configuration')==configuration,
         'Exact expected scheduler profile/configuration')
    need(data.get('artifactAuditComplete') is False,'Configuration identity is not artifact attestation')
    need(type(data.get('buildId')) is str and re.fullmatch('[0-9a-f]{64}',data['buildId']) and
         data.get('runtimeBuildId')==(data['buildId'] if profile else ''),'Configured-only scheduler runtime identity')
    need(sha256(json.dumps(material,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==data['buildId'],
         'Exact formal JSON identity formula; no prototype identity substitution')
    need(material.get('identitySchema')==1 and type(material['identitySchema']) is int and
         material.get('sourceSet')==data['sourceSet'] and material.get('configuration')==configuration,
         'Material version/source set/configuration')
    need(material.get('compilerId')=='GNU' and re.fullmatch(r'13(?:\.[0-9]+)*',material.get('compilerVersion','')),
         'Scheduler material GNU13 only')
    need(Path(material.get('compilerPath','')).resolve()==Path(upstream['compiler']['path']).resolve() and
         material['compilerVersion']==upstream['compiler']['version'],'Same actual upstream/scheduler compiler')
    need(material.get('system')=='Linux' and material.get('architecture')=='x86_64' and material.get('pointerBytes')=='8' and
         material.get('generator')=='Unix Makefiles' and material.get('IPO') is False,'Native x86-64/no-IPO scheduler configuration')
    need(material.get('upstreamAdvanceBuildId')==upstream['buildId'] and
         type(material.get('upstreamProfile')) is int and material['upstreamProfile']==1 and
         type(material.get('profile')) is int and material['profile']==profile,
         'Actual family7 source eligibility; Debug runtime profile remains separately zero')
    need(material.get('helperSha256')==stamp(MODULE)['sha256'] and material.get('compileOptions')==SCHEDULER_OPTIONS,
         'Actual helper/source2 strict material')
    rows=material.get('sources');need(type(rows) is list and len(rows)==2 and {r['path'] for r in rows}==SCHEDULER_SOURCES,'Exactly two scheduler source records')
    for row in rows:
        need(row['sha256']==stamp(ROOT/row['path'])['sha256'],'Current scheduler source hash')
        need(row['flags']==(SCHEDULER_OPTIONS if row['path'].endswith('.cpp') else []),'Exact source-specific options')
    need(data['buildId']!=upstream['buildId'],'Scheduler identity cannot relabel upstream seven sources')
    cache=helper.cache(build)
    need(material.get('globalFlags')==cache.get('CMAKE_CXX_FLAGS','') and
         material.get('configurationFlags')==cache.get('CMAKE_CXX_FLAGS_'+configuration.upper(),''),
         'Actual cache global/configuration flags bound into identity')
    if compiled is not None:
        item=compiled[(ROOT/'core/src/world_static_mesh_flight_scheduler.cpp').resolve()]
        strict_command(item['argv'],werror=True)
        need(definitions(item['argv'],'PIKAPIKA_FLIGHT_SCHEDULER_PROFILE')==[str(profile)] and
             definitions(item['argv'],'PIKAPIKA_FLIGHT_SCHEDULER_BUILD_ID')==[data['buildId']],
             'Actual scheduler library TU definition/identity')
    return data


def harness_compilation(helper, advance, build, *, sanitized):
    selected={};wanted=targets(advance)
    for entry in helper.load(build/'compile_commands.json'):
        source=Path(entry['file']);directory=Path(entry['directory'])
        if not source.is_absolute():source=directory/source
        source=source.resolve();argv=entry.get('arguments') or shlex.split(entry['command'])
        if '-o' not in argv:continue
        obj=Path(argv[argv.index('-o')+1]);obj=obj if obj.is_absolute() else directory/obj;obj=obj.resolve()
        for target,paths in wanted.items():
            if source not in {ROOT/p for p in paths} or not obj.is_relative_to(build/'CMakeFiles'/(target+'.dir')):continue
            key=target+':'+source.relative_to(ROOT).as_posix()
            need(key not in selected,'Duplicate linked harness command')
            strict_command(argv,sanitized=sanitized,werror=source.relative_to(ROOT).as_posix() in WARN)
            if target==FULL:
                need(definitions(argv,'PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY')==['1'],'Shared advance writer main removed only in scheduler full target')
            selected[key]={'argv':argv,'directory':str(directory),'object':stamp(obj)}
    need(len(selected)==sum(len(v) for v in wanted.values()),'All four-target harness/serializer actual commands')
    return selected


def normal_artifacts(build, advance, compilation, harnesses):
    paths={build/'CMakeCache.txt',build/'compile_commands.json',build/'world-flight-binding-Release.json',
           build/(PROFILE_STEM+'Release.json'),build/'libpikapika_core.a',build/('lib'+LIBRARY+'.a')}
    for target in targets(advance):
        paths|={build/target,build/'CMakeFiles'/(target+'.dir')/'link.txt'}
    paths|={build/'world-flight-advance.map',build/'world-flight-advance-fixtures.map',
            build/(TEST+'.map'),build/(FULL+'.map'),build/'CMakeFiles'/(LIBRARY+'.dir')/'link.txt'}
    paths.update(v['object'] for v in compilation.values())
    paths.update(Path(v['object']['path']) for v in harnesses.values())
    return [stamp(p) for p in sorted(paths)]


def scheduler_run(helper, commands, prefix, binary, full_binary, output, env=None):
    raw=commands.run(prefix+'-scheduler-thirteen',[binary,'--run'],env=env)
    need(re.search(rb'13 directed groups PASS; 1382 actual pump observations',raw) is not None,'Actual scheduler13/1382 groups')
    selected=commands.run(prefix+'-scheduler-selected',[binary,'--observations'],env=env)
    selected_path=output/(prefix+'-scheduler-selected.json');selected_path.write_bytes(selected)
    credit=json.loads(commands.run(prefix+'-selected-integer-credit-reference',[sys.executable,CREDIT,selected_path],env=env))
    need(credit.get('status')=='PASS' and credit.get('traces')==1382,'Actual complete selected credit reference, separate from full nested proof')
    full=commands.run(prefix+'-scheduler-full',[full_binary,'--fixtures'],env=env)
    path=output/(prefix+'-scheduler-full.json');path.write_bytes(full);data=helper.load(path)
    need(type(data.get('schema')) is int and data['schema']==1 and data.get('kind')=='world-static-mesh-flight-scheduler-fixtures' and
         type(data.get('fixtures')) is list and len(data['fixtures'])==28,'Actual full 28-frame serializer, not Native fill')
    reference=json.loads(commands.run(prefix+'-full-independent',[sys.executable,CHECKER,path],env=env))
    need(reference.get('status')=='PASS' and reference.get('fixtures')==28 and reference.get('advanceAttempts')==43 and
         reference.get('actualOwnedGuardsVerified')==41 and reference.get('committedTicks')==37,'Actual full nested independent reference')
    controls_path=output/(prefix+'-full-controls')
    controls=json.loads(commands.run(prefix+'-full-independent-controls',[sys.executable,CONTROLS,path,'--output',controls_path],env=env))
    need(controls.get('status')=='PASS' and controls.get('selfTestGroups')==16 and controls.get('negativeControls')==146 and
         controls.get('labelAndOrderIndependent') is True,'Full actual controls:16self/146negative/order-label independence')
    optimized=helper.load(controls_path/'negative-controls.json')['optimizedPythonRejected']
    need(optimized.get('status')=='PASS' and type(optimized.get('exitCode')) is int and optimized['exitCode']!=0,'Actual -O refusal')
    return {'stdout':raw,'selected':helper.load(selected_path),'path':path,'data':data,'reference':reference,'controls':controls}


def compare_full(helper, normal, sanitized, normal_ids, sanitized_ids):
    """Two explicit identity families, precisely three paths and 112 leaves."""
    for ids in (normal_ids,sanitized_ids):
        need(type(ids) is dict and set(ids)=={'scheduler','advance'} and all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in ids.values()),'Two explicit full identity families')
        need(ids['scheduler']!=ids['advance'],'Separate scheduler and upstream identities')
    need(all(normal_ids[k]!=sanitized_ids[k] for k in normal_ids),'Distinct actual normal/instrumented identities in both families')
    clones=[];counts=[]
    for original,ids in ((normal,normal_ids),(sanitized,sanitized_ids)):
        data=deepcopy(original);need(type(data.get('schema')) is int and data['schema']==1 and
            data.get('kind')=='world-static-mesh-flight-scheduler-fixtures' and type(data.get('fixtures')) is list and len(data['fixtures'])==28,'Whole full scheduler28')
        count=[0,0,0]
        for row in data['fixtures']:
            report=row['report'];need(report['binding']['buildId']==ids['scheduler'],'Actual family2 identity at scheduler report path')
            report['binding']['buildId']='<scheduler-configuration-only>';count[0]+=1
            for tick in report['tickReports']:
                if tick is None:continue
                advance=tick['report'];need(advance['binding']['buildId']==ids['advance'],'Actual family7 identity at actual advance report path')
                advance['binding']['buildId']='<advance-configuration-only>';count[1]+=1
                if advance['guard'] is not None:
                    need(advance['guard']['binding']['buildId']==ids['advance'],'Actual family7 identity at actual owned guard path')
                    advance['guard']['binding']['buildId']='<advance-configuration-only>';count[2]+=1
        need(count==[28,43,41],'Exactly112 identity leaves; no missing/extra slots normalized')
        clones.append(helper.exact_tree(data));counts.append(count)
    need(clones[0]==clones[1],'Full tree differs beyond exactly three authorized identity paths; no layout/type/bit exceptions')
    return {'status':'PASS','frames':28,'identityFamilies':2,'pathPatterns':3,'normalizedLeavesPerSide':counts,
            'paths':['fixtures[*].report.binding.buildId','fixtures[*].report.tickReports[*].report.binding.buildId iff tick exists',
                     'fixtures[*].report.tickReports[*].report.guard.binding.buildId iff guard exists'],
            'normalBuildIds':normal_ids,'sanitizedBuildIds':sanitized_ids,
            'comparison':'All key/array order, scalar types, bool/null/messages, layout/storage and binary64 signed-zero bits; nothing else normalized.',
            'treeSha256':sha256(json.dumps(clones[0],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}


def arguments(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal',type=Path,default=ROOT/'build/ci-scheduler')
    parser.add_argument('--output',type=Path,default=ROOT/'build/public-checks/scheduler-gnu')
    parser.add_argument('--sanbuild',type=Path,default=ROOT/'build/wfs-san')
    parser.add_argument('--debugbuild',type=Path,default=ROOT/'build/wfs-debug')
    parser.add_argument('--parallel',type=int,default=2)
    parser.add_argument('--command-timeout',type=int,default=600)
    args=parser.parse_args(argv)
    for key in ('normal','output','sanbuild','debugbuild'):
        path=getattr(args,key).resolve();need(path.is_relative_to(ROOT/'build') and path!=ROOT/'build','Repository build children only')
        setattr(args,key,path)
    need(args.output.is_relative_to(ROOT/'build/public-checks') and args.output!=ROOT/'build/public-checks','Fresh build/public-checks output child only')
    need(1<=args.parallel<=4 and 30<=args.command_timeout<=1200,'Bounded command settings')
    need(len({args.normal,args.output,args.sanbuild,args.debugbuild})==4,'Four distinct paths')
    for path in (args.output,args.sanbuild,args.debugbuild):
        need(not path.exists(),'Fresh output/Debug/sanitizer paths required')
    for path in (args.sanbuild,args.debugbuild):
        for peer in (args.normal,args.output,args.debugbuild if path==args.sanbuild else args.sanbuild):
            need(not path.is_relative_to(peer) and not peer.is_relative_to(path),'No build/output overlap')
    need(not args.normal.is_relative_to(args.output),'Output must not contain normal build')
    return args


def main():
    args=arguments();os.environ['PYTHONDONTWRITEBYTECODE']='1';args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    write(args.output/'invocation.json',{'argv':sys.argv,'cwd':str(Path.cwd()),'python':sys.version})
    before=sources();write(args.output/'sources-before.json',before)
    helper=import_file('scheduler_gnu_guard_utilities',GUARD_RECIPE)
    advance=import_file('scheduler_gnu_advance_utilities',ADVANCE_RECIPE)
    commands=helper.Commands(args.output,args.command_timeout)
    result={'schema':1,'status':'FAIL','kind':'gnu13-full-scheduler','actualGNUExecuted':False,
            'normalBuildReconfiguredOrBuilt':False,'clockCommitSchedulerFormalMachineProof':False,
            'scope':'Actual main-CMake GNU13 normal/Debug/all-dependency O1 ASan/UBSan finite evidence only. Runtime source identity and old leaf audit do not prove complete clock/commit/scheduler instructions, alias/exception atomicity, fault injection, SDK or game integration.'}
    normal_before=None;compiler_before=None
    try:
        need(sys.platform.startswith('linux'),'Actual Linux GNU13 execution required; Windows is refusal-only')
        auditor=import_file('scheduler_gnu_current_upstream_auditor',AUDITOR)
        advance.checked_normal_cache(helper,args.normal)
        normal=advance.checked_profile(helper,auditor,args.normal,'Release')
        normal_core,normal_scheduler_rows,compiled=library_compilation(helper,args.normal)
        normal_scheduler=checked_scheduler_profile(helper,args.normal,'Release',normal,compiled)
        compiler=Path(normal['compiler']['path']);compiler_before=stamp(compiler)
        version=commands.run('compiler-version',[compiler,'--version']);need(b'Free Software Foundation' in version,'Actual GNU compiler')
        result['actualGNUExecuted']=True
        actual_version=commands.run('compiler-full-version',[compiler,'-dumpfullversion','-dumpversion']).decode().strip()
        machine=commands.run('compiler-target',[compiler,'-dumpmachine']).decode().strip()
        need(re.fullmatch(r'13(?:\.[0-9]+)*',actual_version) and actual_version==normal['compiler']['version'] and machine.startswith('x86_64'),'Actual GNU13/x86-64 agrees with profile')
        harnesses=harness_compilation(helper,advance,args.normal,sanitized=False)
        normal_before=normal_artifacts(args.normal,advance,compiled,harnesses);write(args.output/'normal-artifacts-before.json',normal_before)
        write(args.output/'normal-core-compilation.json',{str(k):{'argv':v['argv'],'object':stamp(v['object'])} for k,v in compiled.items()})
        write(args.output/'normal-harness-compilation.json',harnesses)
        audit=json.loads(commands.run('normal-seven-source-leaf-and-command-audit',[sys.executable,AUDITOR,'--profile',args.normal/'world-flight-binding-Release.json',
            '--object',compiled[(ROOT/'core/src/core.cpp').resolve()]['object'],'--binary',args.normal/advance.ADVANCE,
            '--map',args.normal/'world-flight-advance.map','--build-directory',args.normal,'--output',args.output/'normal-binding']))
        need(audit.get('status')=='PASS' and audit['advanceScope']['clockInstructionsAudited'] is False and
             audit['advanceScope']['commitPathAudited'] is False and audit['advanceScope']['WorldAdvanceAccepted'] is False,'Keep old artifact-audit scope separate')
        warning_dir=args.output/'warning-objects';warning_dir.mkdir()
        for i,source in enumerate(WARN):
            if source.startswith('core/'):
                item=compiled[(ROOT/source).resolve()];argv=list(item['argv']);directory=item['directory']
            else:
                target=TEST if source.endswith('scheduler_tests.cpp') else FULL
                item=harnesses[target+':'+source];argv=list(item['argv']);directory=item['directory']
            strict_command(argv,werror=True);argv[argv.index('-o')+1]=str(warning_dir/(str(i)+'.o'))
            # Keep actual compile-database argv and working directory together;
            # no shell or CMake command-line reserialization of quoted defines.
            compile_at(commands,'new-werror-tu-'+str(i),argv,directory)
        runs={}
        runs['normal']=scheduler_run(helper,commands,'normal',args.normal/TEST,args.normal/FULL,args.output)
        normal_advance=advance.advance_run(helper,commands,'normal',args.normal/advance.ADVANCE,args.output)
        normal_transactions=advance.transaction_run(helper,commands,'normal',args.normal/advance.FIXTURES,args.output)
        need(normal_transactions['controls'].get('selfTestGroups')==14 and normal_transactions['controls'].get('negativeControls')==85,'Unchanged old51/14self/85negative regression')
        common=['-G','Unix Makefiles','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_CXX_COMPILER='+str(compiler),'-DBUILD_TESTING=ON']
        commands.run('debug-configure',['cmake','-S',ROOT,'-B',args.debugbuild,*common,'-DCMAKE_BUILD_TYPE=Debug'])
        commands.run('debug-build',['cmake','--build',args.debugbuild,'--target',TEST,advance.ADVANCE,'--parallel',args.parallel,'--verbose'])
        debug=advance.checked_profile(helper,auditor,args.debugbuild,'Debug')
        debug_core,debug_scheduler_rows,debug_compiled=library_compilation(helper,args.debugbuild)
        debug_scheduler=checked_scheduler_profile(helper,args.debugbuild,'Debug',debug,debug_compiled)
        need(b'Scheduler default profile refusal PASS' in commands.run('debug-scheduler-refusal',[args.debugbuild/TEST,'--unsupported-profile']),'Actual default scheduler refusal')
        need(b'default NEW TU refusal' in commands.run('debug-advance-refusal',[args.debugbuild/advance.ADVANCE,'--unsupported-profile']),'Actual Debug advance refusal')
        flags=' '.join(['-O1','-g',*helper.SANITIZERS])
        commands.run('sanitizer-configure',['cmake','-S',ROOT,'-B',args.sanbuild,*common,'-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_CXX_FLAGS='+flags,'-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG','-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'])
        commands.run('sanitizer-build-all-dependencies',['cmake','--build',args.sanbuild,'--target',*targets(advance),'--parallel',args.parallel,'--verbose'])
        san=advance.checked_profile(helper,auditor,args.sanbuild,'Release')
        san_core,san_scheduler_rows,san_compiled=library_compilation(helper,args.sanbuild)
        san_scheduler=checked_scheduler_profile(helper,args.sanbuild,'Release',san,san_compiled)
        write(args.output/'sanitized-core-compilation.json',helper.check_sanitized_compilation(args.sanbuild,normal_core))
        for item in san_scheduler_rows.values():strict_command(item['argv'],sanitized=True,werror=True)
        write(args.output/'sanitized-scheduler-compilation.json',[
            {'source':str(source),'argv':item['argv'],'object':stamp(item['object'])} for source,item in san_scheduler_rows.items()])
        san_harnesses=harness_compilation(helper,advance,args.sanbuild,sanitized=True)
        write(args.output/'sanitized-harness-compilation.json',san_harnesses)
        env={'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1','PYTHONDONTWRITEBYTECODE':'1'}
        runs['sanitized']=scheduler_run(helper,commands,'sanitized',args.sanbuild/TEST,args.sanbuild/FULL,args.output,env)
        san_advance=advance.advance_run(helper,commands,'sanitized',args.sanbuild/advance.ADVANCE,args.output,env)
        san_transactions=advance.transaction_run(helper,commands,'sanitized',args.sanbuild/advance.FIXTURES,args.output,env)
        need(san_transactions['controls'].get('selfTestGroups')==14 and san_transactions['controls'].get('negativeControls')==85,'Actual sanitized old51 controls')
        need(runs['normal']['stdout']==runs['sanitized']['stdout'] and normal_advance['stdout']==san_advance['stdout'],'Actual assertion stdout equality')
        need(helper.exact_tree(normal_advance['data'])==helper.exact_tree(san_advance['data']),'Whole old clock18 exact equality, no normalization')
        selected_tree=helper.exact_tree(runs['normal']['selected'])
        need(selected_tree==helper.exact_tree(runs['sanitized']['selected']),
             'Whole selected1382 tree equality, no identity fields or normalization')
        selected_comparison={'status':'PASS','observations':1382,'normalization':'NONE',
            'treeSha256':sha256(json.dumps(selected_tree,separators=(',',':')).encode()).hexdigest()}
        comparison=compare_full(helper,runs['normal']['data'],runs['sanitized']['data'],
            {'scheduler':normal_scheduler['buildId'],'advance':normal['buildId']},
            {'scheduler':san_scheduler['buildId'],'advance':san['buildId']})
        old_comparison=advance.compare_transactions(helper,normal_transactions['data'],san_transactions['data'],normal['buildId'],san['buildId'])
        write(args.output/'full-comparison.json',comparison);write(args.output/'old-transaction-comparison.json',old_comparison)
        result.update(status='PASS',actualCompilerVersion=actual_version,actualCompilerTarget=machine,
            normalAdvanceProfile=normal,normalSchedulerProfile=normal_scheduler,sanitizedAdvanceProfile=san,sanitizedSchedulerProfile=san_scheduler,
            debugAdvanceProfile=debug,debugSchedulerProfile=debug_scheduler,normalBindingAudit=stamp(args.output/'normal-binding/audit.json'),
            schedulerGroupsPerBuild=13,selectedObservationsPerBuild=1382,fullFramesPerBuild=28,
            fullComparison=comparison,selectedComparison=selected_comparison,
            references={k:v['reference'] for k,v in runs.items()},controls={k:v['controls'] for k,v in runs.items()},
            captures={k:stamp(v['path']) for k,v in runs.items()},oldClockCasesPerBuild=18,oldAdvanceGroupsPerBuild=9,
            oldTransactionComparison=old_comparison,warningTranslationUnits=len(WARN),
            libraryTranslationUnits=len(compiled),coreTranslationUnits=len(normal_core),schedulerTranslationUnits=len(normal_scheduler_rows),
            harnessCompileCommandsPerBuild=len(harnesses),distinctHarnessSources=len({k.split(':',1)[1] for k in harnesses}),
            instrumentationScope='Every actual core/scheduler library dependency and all four target-specific main/shared writer/test commands; O1 ASan/UBSan, no LTO. sizeof/pointer outputs remain observations; no machine-proof promotion.')
    except BaseException as error:
        result['error']=type(error).__name__+': '+str(error)
    finally:
        after=sources();write(args.output/'sources-after.json',after);result['sourceStable']=before==after
        if before!=after:result.update(status='FAIL',stabilityError='Source/SDK/old available artifact changed')
        if normal_before is not None:
            normal_after=normal_artifacts(args.normal,advance,compiled,harnesses);write(args.output/'normal-artifacts-after.json',normal_after)
            result['normalArtifactsStable']=normal_before==normal_after
            if normal_before!=normal_after:result.update(status='FAIL',normalArtifactError='Normal existing artifact/configuration changed')
        if compiler_before is not None:
            result['compilerStable']=compiler_before==stamp(compiler_before['path'])
            if not result['compilerStable']:result.update(status='FAIL',compilerError='Compiler changed')
        result.update(commands=commands.items,recipe=stamp(Path(__file__)));write(args.output/'verification.json',result)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
