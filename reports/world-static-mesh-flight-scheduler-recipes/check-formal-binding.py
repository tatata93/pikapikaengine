"""Exercise the new formal scheduler CMake helper without wiring main CMake.

Imports immutable wfa3 core/7 serializer objects. Debug uses /MD and iterator0
explicitly to match that Release import: scheduler Debug refusal, NOT Debug core.
"""
from __future__ import annotations
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RECIPE = Path(__file__).resolve()
MODULE = ROOT / 'cmake/PikapikaWorldFlightSchedulerBinding.cmake'
FULL_HELPER = RECIPE.with_name('check-full-fixtures.py')
FACT_HELPER = ROOT / 'reports/world-static-mesh-flight-advance-recipes/check-configured-prototype.py'
FULL_CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-scheduler.py'
FULL_CONTROLS = ROOT / 'tests/world_static_mesh_flight_scheduler_reference_tests.py'
CREDIT_CHECKER = ROOT / 'scripts/verify-world-static-mesh-flight-scheduler-credit.py'
PROTOTYPE = RECIPE.parent / 'run-20261105-prototype-002'
FULL_BASELINE = RECIPE.parent / 'run-20261105-full-fixtures-001/scheduler-full.json'
SCHEDULER = ROOT / 'core/src/world_static_mesh_flight_scheduler.cpp'
SCHEDULER_HEADER = ROOT / 'core/include/pikapika/world_static_mesh_flight_scheduler.hpp'
TEST = ROOT / 'tests/world_static_mesh_flight_scheduler_tests.cpp'
MAIN = ROOT / 'tests/world_static_mesh_flight_scheduler_fixtures.cpp'
SHARED = ROOT / 'tests/world_static_mesh_flight_advance_fixtures.cpp'
OPTIONS = ['/W4','/WX','/permissive-','/fp:strict','/GL-']

def need(ok, message):
    if not ok:
        raise ValueError(message)

def stamp(path):
    path=Path(path); raw=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def write(path, value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')

def exact(value):
    if type(value) is dict:
        return ['object', [[k,exact(v)] for k,v in value.items()]]
    if type(value) is list:
        return ['array',[exact(v) for v in value]]
    if type(value) is float:
        import struct
        return ['float64',struct.pack('>d',value).hex()]
    if type(value) is int:
        return ['integer',str(value)]
    if type(value) is bool:
        return ['bool',value]
    return [type(value).__name__,value]

def compare_full(left,right,left_id,right_id,seven_id):
    need(left_id!=right_id and left_id!=seven_id and right_id!=seven_id,'Distinct explicit scheduler identities, unchanged upstream')
    clones=[];counts=[]
    for data,identity in ((left,left_id),(right,right_id)):
        data=deepcopy(data);count=[0,0,0]
        for row in data['fixtures']:
            r=row['report'];need(r['binding']['buildId']==identity,'Actual family2 scheduler identity at exact path')
            r['binding']['buildId']='<scheduler-config-only>';count[0]+=1
            for tick in r['tickReports']:
                if tick is None:
                    continue
                a=tick['report'];need(a['binding']['buildId']==seven_id,'Actual family7 advance identity unchanged')
                a['binding']['buildId']='<advance-config-only>';count[1]+=1
                if a['guard'] is not None:
                    need(a['guard']['binding']['buildId']==seven_id,'Actual family7 owned guard identity unchanged')
                    a['guard']['binding']['buildId']='<advance-config-only>';count[2]+=1
        clones.append(exact(data));counts.append(count)
    need(counts==[[28,43,41],[28,43,41]],'Exact3 path-family cardinalities')
    need(clones[0]==clones[1],'Whole same-ABI full document differs beyond declared3 identity patterns; no layout/storage/type/bit normalization')
    raw=json.dumps(clones[0],separators=(',',':')).encode()
    return {'status':'PASS','identityFamilies':2,'pathPatterns':3,'leafCountsPerSide':counts,'normalizedTreeSha256':hashlib.sha256(raw).hexdigest(),
            'scope':'Same MSVC ABI full comparison only; original raw unchanged, no layout/sizeof/storage/numerical normalization.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',default='run-20261105-formal-binding-001')
    parser.add_argument('--build',default='build/wfsb1')
    args=parser.parse_args()
    need(sys.platform=='win32','MSVC Windows experiment only; GNU not simulated')
    need(re.fullmatch(r'run-[A-Za-z0-9_.-]{1,70}',args.name),'Fresh report component')
    build=(ROOT/args.build).resolve();out=RECIPE.parent/args.name
    need(build.parent==ROOT/'build' and re.fullmatch(r'wfsb[1-9][0-9]*',build.name),'Fresh short build/wfsbN only')
    need(not build.exists() and not out.exists(),'Never overwrite evidence or existing builds')
    build.mkdir();out.mkdir();(out/'recipe.py.txt').write_bytes(RECIPE.read_bytes())
    write(out/'invocation.json',{'argv':sys.argv,'cwd':str(Path.cwd())})
    sys.dont_write_bytecode=True
    old=runpy.run_path(str(FULL_HELPER),run_name='readonly_frozen_full_fixture_helpers')
    fact=runpy.run_path(str(FACT_HELPER),run_name='readonly_frozen_fact_helpers')
    paths=sorted(set(old['protected']()+[RECIPE,MODULE,FULL_HELPER,FULL_CHECKER,FULL_CONTROLS,CREDIT_CHECKER,FULL_BASELINE,
        PROTOTYPE/'scheduler-profile.json',PROTOTYPE/'observations.json']))
    identities=lambda:{p.relative_to(ROOT).as_posix():stamp(p) for p in paths}
    before=identities();write(out/'before.json',before);commands=[]
    def run(name,argv,timeout=600):
        row={'name':name,'argv':list(map(str,argv)),'cwd':str(ROOT),'before':identities()};start=time.monotonic()
        try:
            done=subprocess.run(row['argv'],cwd=ROOT,capture_output=True,timeout=timeout)
            code,stdout,stderr=done.returncode,done.stdout,done.stderr
        except subprocess.TimeoutExpired as error:
            code,stdout,stderr=None,error.stdout or b'',(error.stderr or b'')+str(error).encode()
        except BaseException as error:
            code,stdout,stderr=None,b'',str(error).encode()
        (out/(name+'.stdout.txt')).write_bytes(stdout);(out/(name+'.stderr.txt')).write_bytes(stderr)
        row.update(exitCode=code,seconds=time.monotonic()-start,after=identities())
        row.update(sourceStable=row['before']==row['after'],stdout=stamp(out/(name+'.stdout.txt')),stderr=stamp(out/(name+'.stderr.txt')))
        commands.append(row);write(out/(name+'.command.json'),row)
        print(json.dumps({k:row[k] for k in ['name','exitCode','seconds','sourceStable']}),flush=True)
        if code!=0:
            print(stdout.decode('utf-8',errors='replace'),flush=True);print(stderr.decode('utf-8',errors='replace'),file=sys.stderr,flush=True)
        need(code==0 and row['sourceStable'],'Command failed or protected bytes changed: '+name)
        return stdout
    result={'schema':1,'status':'FAIL','scope':'Isolated formal CMake helper/target experiment, immutable imported Release core. Debug /MD+iterator0 scheduler refusal only, not full Debug core. No main integration, GNU, sanitizer or machine proof.'}
    try:
        quote=fact['cmake_path'];cquote=fact['cmake_quote'];project=build/'project';project.mkdir()
        lines=['cmake_minimum_required(VERSION 3.24)','project(FormalSchedulerBindingExperiment LANGUAGES CXX)',
            'set(CMAKE_CXX_STANDARD 20)','set(CMAKE_CXX_STANDARD_REQUIRED ON)','set(CMAKE_CXX_EXTENSIONS OFF)',
            'set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)','set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL)',
            'string(APPEND CMAKE_CXX_FLAGS_DEBUG " /D_ITERATOR_DEBUG_LEVEL=0")',fact['FACTS'],
            'add_library(old_core STATIC IMPORTED)','set_target_properties(old_core PROPERTIES IMPORTED_LOCATION '+quote(old['LIB'])+')',
            'file(READ '+quote(ROOT/'build/wfa3/world-flight-binding-Release.json')+' old_json)',
            'string(JSON PP_WF_BUILD_ID GET "${old_json}" buildId)','string(JSON PP_WF_PROFILE GET "${old_json}" profile)',
            'set(saved_id "${PP_WF_BUILD_ID}")','set(saved_profile "${PP_WF_PROFILE}")',
            'include('+quote(MODULE)+')','pikapika_add_world_flight_scheduler(formal_scheduler old_core)',
            'if(NOT PP_WF_BUILD_ID STREQUAL saved_id OR NOT PP_WF_PROFILE STREQUAL saved_profile)',
            '  message(FATAL_ERROR "Formal helper mutated upstream configuration")','endif()',
            'unset(PP_WF_BUILD_ID)','unset(PP_WF_PROFILE)',
            'pikapika_add_world_flight_scheduler(default_scheduler old_core PROFILE_STEM scheduler-default-binding)']
        for target,sources,lib,library_only in [
            ('scheduler_tests',[TEST],'formal_scheduler',False),('scheduler_default_tests',[TEST],'default_scheduler',False),
            ('scheduler_fixtures',[MAIN,SHARED],'formal_scheduler',True),('legacy51_fixtures',[SHARED],'old_core',False)]:
            lines += ['add_executable('+target+' '+' '.join(quote(p) for p in sources)+')',
                'target_include_directories('+target+' PRIVATE '+quote(ROOT/'core/include')+' '+quote(ROOT/'tests')+')',
                'target_link_libraries('+target+' PRIVATE '+lib+(' '+' '.join(quote(p) for p in old['OBJECTS']) if target in {'scheduler_fixtures','legacy51_fixtures'} else '')+')',
                'target_compile_options('+target+' PRIVATE '+' '.join(OPTIONS)+')',
                'target_link_options('+target+' PRIVATE /LTCG:OFF "/MAP:$<TARGET_FILE_DIR:'+target+'>/'+target+'.map")',
                'set_property(TARGET '+target+' PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)']
            if library_only:
                lines.append('target_compile_definitions('+target+' PRIVATE PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1)')
        driver='\n'.join(lines)+'\n'
        (project/'CMakeLists.txt').write_text(driver,encoding='utf-8',newline='\n');(out/'CMakeLists.txt').write_text(driver,encoding='utf-8',newline='\n')
        run('01-configure',['cmake','-S',project,'-B',build/'configured','-A','x64'])
        profiles={}
        for stem in ['world-flight-scheduler-binding','scheduler-default-binding']:
            for configuration in ['Release','Debug']:
                path=build/'configured'/(stem+'-'+configuration+'.json');p=json.loads(path.read_text())
                material=p['identityMaterial'];canonical=json.dumps(material,ensure_ascii=False,separators=(',',':')).encode()
                need(hashlib.sha256(canonical).hexdigest()==p['buildId'],'Exact independent JSON identity formula')
                need(p['sourceSet']=='world-static-mesh-flight-scheduler-v1' and len(material['sources'])==2,'Exact source2 set')
                for row in material['sources']:
                    need(stamp(ROOT/row['path'])['sha256']==row['sha256'],'Actual configured source hash')
                expected=1 if stem=='world-flight-scheduler-binding' and configuration=='Release' else 0
                need(p['profile']==expected and p['runtimeBuildId']==(p['buildId'] if expected else ''),'Release/configured-only profile')
                profiles[stem+'-'+configuration]=p;(out/path.name).write_bytes(path.read_bytes())
        release=profiles['world-flight-scheduler-binding-Release'];identity=release['buildId']
        seven=json.loads((ROOT/'build/wfa3/world-flight-binding-Release.json').read_text())['buildId']
        previous=json.loads((PROTOTYPE/'scheduler-profile.json').read_text())['buildId']
        need(identity not in {seven,previous},'New formal configuration must not relabel old identity')
        run('02-release-build',['cmake','--build',build/'configured','--config','Release','--parallel','2'])
        raw=run('03-release-thirteen',[build/'configured/Release/scheduler_tests.exe','--run'])
        need(raw==(PROTOTYPE/'04-run.stdout.txt').read_bytes(),'Actual13/1382 Native stdout unchanged')
        raw=run('04-release-observations',[build/'configured/Release/scheduler_tests.exe','--observations'])
        (out/'observations.json').write_bytes(raw)
        need(raw==(PROTOTYPE/'observations.json').read_bytes(),'Complete selected numerical/bit observations unchanged without normalization')
        run('05-credit-reference',[sys.executable,'-B',CREDIT_CHECKER,out/'observations.json'],240)
        raw=run('06-full-fixtures',[build/'configured/Release/scheduler_fixtures.exe','--fixtures'])
        (out/'scheduler-full.json').write_bytes(raw)
        comparison=compare_full(json.loads(FULL_BASELINE.read_bytes()),json.loads(raw),previous,identity,seven)
        write(out/'full-comparison.json',comparison)
        full=json.loads(run('07-full-reference',[sys.executable,'-B',FULL_CHECKER,out/'scheduler-full.json'],240))
        controls=json.loads(run('08-full-controls',[sys.executable,'-B',FULL_CONTROLS,out/'scheduler-full.json','--output',out/'full-controls'],240))
        run('09-default-release-refusal',[build/'configured/Release/scheduler_default_tests.exe','--unsupported-profile'])
        raw=run('10-legacy51',[build/'configured/Release/legacy51_fixtures.exe','--fixtures']);(out/'legacy51.json').write_bytes(raw)
        need(len(raw)==2979456 and raw==old['BASE'].read_bytes(),'Macro-free legacy51 exact raw unchanged')
        run('11-legacy51-reference',[sys.executable,'-B',old['CHECKER'],out/'legacy51.json'],240)
        run('12-legacy51-controls',[sys.executable,'-B',old['CONTROLS'],out/'legacy51.json','--output',out/'legacy-controls'],240)
        run('13-debug-build',['cmake','--build',build/'configured','--config','Debug','--target','scheduler_tests','scheduler_default_tests','--parallel','2'])
        run('14-debug-configured-refusal',[build/'configured/Debug/scheduler_tests.exe','--unsupported-profile'])
        run('15-debug-default-refusal',[build/'configured/Debug/scheduler_default_tests.exe','--unsupported-profile'])
        provenance=[]
        for path in sorted((build/'configured').rglob('CL.command.1.tlog')):
            if not any(part in path.parts for part in ['formal_scheduler.dir','default_scheduler.dir','scheduler_tests.dir','scheduler_default_tests.dir','scheduler_fixtures.dir','legacy51_fixtures.dir']):
                continue
            rawlog=path.read_bytes();text=rawlog.decode('utf-16');lines=text.splitlines();entries=[]
            debug='Debug' in path.parts
            for i,line in enumerate(lines):
                if not line.startswith('^'):
                    continue
                source=Path(line[1:]).resolve();end=next((j for j in range(i+1,len(lines)) if lines[j].startswith('^')),len(lines));command=' '.join(lines[i+1:end])
                need(source in {SCHEDULER,TEST,MAIN,SHARED},'Only allowed new TUs actually compiled')
                for token in OPTIONS:
                    need(re.search(r'(?:^|\s)'+re.escape(token)+r'(?=\s|$)',command,re.I),'Actual strict/WX/nonLTO missing '+token)
                fp=re.findall(r'(?:^|\s)/fp:([^\s]+)',command,re.I)
                need(fp and all(v.casefold()=='strict' for v in fp),'Actual fp option override')
                need(not re.search(r'(?:^|\s)/(?:GL|WX-|MDd)(?=\s|$)',command,re.I),'Actual LTO/warnings/ABI weakening')
                if source==SCHEDULER:
                    is_formal='formal_scheduler.dir' in path.parts;stem='world-flight-scheduler-binding' if is_formal else 'scheduler-default-binding'
                    p=profiles[stem+('-Debug' if debug else '-Release')]
                    need(('PIKAPIKA_FLIGHT_SCHEDULER_PROFILE='+str(p['profile'])) in command and p['buildId'] in command,'Actual separate source2 macro/ID')
                if debug:
                    need('NDEBUG' not in command and '_ITERATOR_DEBUG_LEVEL=0' in command and re.search(r'(?:^|\s)/MD(?=\s|$)',command,re.I),'Debug rejection uses explicit Release-import ABI with NDEBUG absent')
                entries.append({'source':source.relative_to(ROOT).as_posix(),'command':command})
            dest=out/('compile-'+str(len(provenance))+'.tlog.txt');dest.write_bytes(rawlog);provenance.append({'original':stamp(path),'copy':stamp(dest),'DebugABICompatibility':debug,'entries':entries})
        need(len(provenance)==10,'Six Release and four Debug actual targets')
        result.update(status='FINITE_FORMAL_BINDING_HELPER_PASS',profiles=profiles,fullComparison=comparison,
            newFormalSchedulerBuildId=identity,previousPrototypeSchedulerBuildId=previous,unchangedSevenBuildId=seven,
            nativeGroups=13,selectedPumps=1382,fullReference=full,fullControls=controls,legacy51RawIdentical=True,
            actualCompileProvenance=provenance,actualNewGNUExecuted=False,mainCMakeWired=False,
            DebugScope='Debug scheduler TU/profile0 with /MD+iterator0 ABI matching imported Release core; NOT whole Debug core.')
    except BaseException as error:
        result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(out/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(paths),commands=commands)
        if not result['sourceStable']:
            result['status']='FAIL'
        write(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ['status','newFormalSchedulerBuildId','sourceStable','error'] if k in result}),flush=True)
    return 0 if result['status']=='FINITE_FORMAL_BINDING_HELPER_PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
