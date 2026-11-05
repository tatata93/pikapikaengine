"""Fresh real CMake verification of Release-only allocation test registration.

Prior actual execution remains evidence for identical compiler/link projects;
this checks the sole test-registration correction without mutating old builds.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'run-20261105-configuration-gate-002'
BUILD=ROOT/'build/wfot2'
OLD=ROOT/'build/wfos1'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    raw=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def main():
    need(sys.platform=='win32' and not BUILD.exists() and not (OUT/'result.json').exists(),'Fresh actual MSVC configuration evidence')
    OUT.mkdir(exist_ok=True);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());before=stamp(ROOT/'CMakeLists.txt');commands=[]
    def write(name,d):(OUT/name).write_bytes((json.dumps(d,indent=2)+'\n').encode())
    def run(name,argv):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=180)
        (OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        row={'name':name,'argv':list(map(str,argv)),'exitCode':p.returncode,'seconds':time.monotonic()-start};commands.append(row);write(name+'.command.json',row)
        need(p.returncode==0,'Actual command failed: '+name);return p.stdout
    result={'schema':1,'status':'FAIL','scope':__doc__}
    try:
        prior=json.loads((HERE/'run-20261105-main-integration-001/result.json').read_bytes());need(prior['status']=='FINITE_MAIN_OWNED_SESSION_INTEGRATION_PASS','Actual prior Release52/Debug execution')
        old=(HERE/'run-20261105-main-integration-001/CMakeLists.txt.txt').read_text();current=(ROOT/'CMakeLists.txt').read_text()
        a='    add_test(NAME world_static_mesh_session_allocation COMMAND pikapika_world_static_mesh_session_allocation_tests)\n    set_tests_properties(world_static_mesh_session_allocation PROPERTIES CONFIGURATIONS Release)'
        b='    add_test(NAME world_static_mesh_session_allocation COMMAND pikapika_world_static_mesh_session_allocation_tests CONFIGURATIONS Release)'
        need(old.count(a)==1 and old.replace(a,b)==current,'Sole source difference is actual add_test CONFIGURATIONS correction')
        bad=json.loads(run('01-before-debug-inventory',['ctest','--test-dir',OLD,'-C','Debug','-R','^world_static_mesh_session_allocation$','--show-only=json-v1']))
        need([r['name'] for r in bad['tests']]==['world_static_mesh_session_allocation'],'Preserve actual erroneous Debug registration')
        run('02-configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON'])
        inventories={}
        for cfg,count in [('Release',52),('Debug',51),('MinSizeRel',51),('RelWithDebInfo',51)]:
            d=json.loads(run('03-'+cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));names=[r['name'] for r in d['tests']]
            need(len(names)==count and ('world_static_mesh_session_allocation' in names)==(cfg=='Release'),'Correct actual configuration test registration')
            need('world_static_mesh_session' in names,'Owner refusal remains registered');inventories[cfg]=names
        profiles=[]
        for stem in ['world-flight-binding','world-flight-scheduler-binding','world-flight-controlled-tick-binding','world-flight-controlled-scheduler-binding','world-owned-session-configuration']:
            for cfg in ['Debug','Release','MinSizeRel','RelWithDebInfo']:
                name=stem+'-'+cfg+'.json';need((BUILD/name).read_bytes()==(OLD/name).read_bytes(),'All existing and owner configured provenance raw exact');profiles.append(stamp(BUILD/name))
        projects=[]
        old_projects={p.name:p for p in OLD.glob('*.vcxproj')};new_projects={p.name:p for p in BUILD.glob('*.vcxproj')};need(old_projects.keys()==new_projects.keys(),'All generated compiler/link target projects retained')
        ns={'v':'http://schemas.microsoft.com/developer/msbuild/2003'}
        def graph(paths):
            own={}
            for name,path in paths.items():
                tree=ET.parse(path);nodes=tree.findall('./v:PropertyGroup/v:ProjectGuid',ns);need(len(nodes)==1,'One actual project GUID')
                guid=nodes[0].text;need(re.fullmatch(r'\{[0-9A-F-]{36}\}',guid) is not None,'Actual generated project GUID');own[name]=guid
            need(len(set(own.values()))==len(own),'Unique generated project graph identities')
            for name,path in paths.items():
                for node in ET.parse(path).findall('./v:ItemGroup/v:ProjectReference',ns):
                    target=Path(node.attrib['Include']).name;need(target in own and node.find('v:Project',ns).text==own[target],'Actual reference GUID matches its exact named target')
            return own
        old_graph,new_graph=graph(old_projects),graph(new_projects)
        def normalized(path,base,guids):
            text=path.read_text(encoding='utf-8-sig')
            for prefix in [str(base),base.as_posix(),str(base).upper(),base.as_posix().upper()]:text=text.replace(prefix,'<EXACT_BUILD_DIRECTORY>')
            # Only the validated owning ProjectGuid and ProjectReference/Project
            # elements; never arbitrary GUID/string/compile/link normalization.
            text=text.replace('<ProjectGuid>'+guids[path.name]+'</ProjectGuid>','<ProjectGuid>'+path.name+'</ProjectGuid>')
            for name,guid in guids.items():text=text.replace('<Project>'+guid+'</Project>','<Project>'+name+'</Project>')
            return text
        skipped=[]
        for name,p in new_projects.items():
            if not ET.parse(p).findall('.//v:ClCompile[@Include]',ns):skipped.append(name);continue
            need(normalized(p,BUILD,new_graph)==normalized(old_projects[name],OLD,old_graph),'Exact compile/link project except build prefix and validated graph IDs: '+name)
            projects.append({'name':name,'current':stamp(p),'prior':stamp(old_projects[name])})
        need(len(projects)==77,'All actual71 executable and6 static-library compile/link projects')
        # Copied changes must remain observable outside those two explicit
        # configuration-only path/graph fields. No copied project is executed.
        sample=next(p for p in new_projects.values() if p.name=='pikapika_world_static_mesh_session.vcxproj')
        normal=normalized(sample,BUILD,new_graph)
        need(normal.count('<TreatWarningAsError>true</TreatWarningAsError>')==4,'Actual four strict configurations')
        changed=normal.replace('<TreatWarningAsError>true</TreatWarningAsError>','<TreatWarningAsError>false</TreatWarningAsError>',1)
        need(changed!=normalized(old_projects[sample.name],OLD,old_graph),'Copied compiler option alteration remains different')
        result.update(status='PASS',soleChangeTestConfigurationRegistration=True,actualPriorDebugMisregistrationObserved=True,actualFreshInventories=inventories,oldAndOwner20ConfigurationDocumentsRawExact=True,configurationDocuments=profiles,compilerLinkProjectsExactExceptBuildPrefixAndValidatedGraphIDs=True,projectCount=len(projects),projects=projects,utilityProjectsOutsideCompileLinkComparison=skipped,copiedCompilerChangeRemainsObservable=True,newBuildExecuted=False,scope='Actual fresh CMake/CTest registration plus all77 C++ compiler/link project raw comparison after exact absolute build-directory and validated owning/reference graph GUID element replacement only. Utility projects excluded explicitly. Actual previous Release52/Debug6 executions remain separate evidence; no claimed execution of fresh build/wfot2.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    result.update(commands=commands,sourceStable=before==stamp(ROOT/'CMakeLists.txt'),source=before)
    if not result['sourceStable']:result['status']='FAIL'
    write('result.json',result);print(json.dumps({k:result[k] for k in ['status','projectCount','sourceStable','error'] if k in result}));return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
