"""Read-only exact TU inventory and genuine Debug link audit after main acceptance."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'build/wfos1'
OUT=Path(__file__).resolve().parent/'run-20261105-main-commands-001'
OWNER='pikapika_world_static_mesh_session'
SUPPORT='pikapika_session_fixture_support'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def main():
    need(sys.platform=='win32','Actual MSVC tlogs only');OUT.mkdir(exist_ok=False);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    result={'schema':1,'status':'FAIL','scope':__doc__}
    try:
        main_result=json.loads((OUT.parent/'run-20261105-main-integration-001/result.json').read_bytes())
        need(main_result['status']=='FINITE_MAIN_OWNED_SESSION_INTEGRATION_PASS','Actual completed prerequisite')
        serializers={'world_static_mesh_flight_controlled_scheduler_fixtures','world_static_mesh_flight_controlled_tick_fixtures','world_static_mesh_flight_advance_fixtures','world_static_mesh_flight_guard_fixtures','world_static_mesh_flight_preparation_fixtures','sphere_triangle_mesh_free_flight_guard_fixtures','sphere_triangle_mesh_held_load_fixtures','accelerated_pair_coverage_fixtures','accelerated_plane_box_coverage_fixtures','accelerated_sphere_box_coverage_fixtures'}
        counts=[]
        for entry in main_result['compileProvenance']:
            raw=(ROOT/entry['copy']['path']).read_bytes();need(hashlib.sha256(raw).hexdigest()==entry['copy']['sha256'],'Stored compiler command bytes')
            rows=re.findall(r'^\^([^\r\n]+)\r?\n([^\r\n]+)',raw.decode('utf16'),re.M);target=entry['target'];cfg=entry['configuration']
            if target==OWNER:wanted={'core/src/world_static_mesh_session.cpp'}
            elif target==SUPPORT:wanted={'tests/'+name+'.cpp' for name in serializers}
            else:wanted={'tests/'+target.removeprefix('pikapika_')+'.cpp'}
            actual=[Path(p).resolve().relative_to(ROOT).as_posix().lower() for p,_ in rows]
            need(len(actual)==len(set(actual)) and set(actual)==wanted,'Exact target/config TU inventory')
            for _,command in rows:
                runtime='/MDd' if cfg=='Debug' else '/MD'
                need(re.search(r'(?:^|\s)'+runtime+r'(?=\s|$)',command),'Exact runtime flag')
                if target==SUPPORT:
                    need('PIKAPIKA_ADVANCE_FIXTURE_LIBRARY_ONLY=1' in command and 'PIKAPIKA_CONTROLLED_SCHEDULER_FIXTURE_LIBRARY_ONLY=1' in command,'Support target suppresses both actual mains')
            counts.append({'target':target,'configuration':cfg,'actualSources':actual,'entries':len(rows)})
        need(len(counts)==8 and sum(x['entries'] for x in counts)==26,'Exactly8 compiler logs and26 new target TU entries')
        parents=['pikapika_core','pikapika_world_static_mesh_flight_controlled_tick','pikapika_world_static_mesh_flight_scheduler','pikapika_world_static_mesh_flight_controlled_scheduler']
        debug=[]
        for target in parents:
            p=next((BUILD/(target+'.dir/Debug')).rglob('CL.command.1.tlog'));raw=p.read_bytes();rows=re.findall(r'^\^([^\r\n]+)\r?\n([^\r\n]+)',raw.decode('utf16'),re.M)
            names={Path(p).name.lower() for p,_ in rows};expected=40 if target=='pikapika_core' else 1
            need(len(rows)==len(names)==expected,'Exact Debug numerical parent TU count')
            if target=='pikapika_core':
                prior=next((ROOT/'build/wfcqm2/pikapika_core.dir/Debug').rglob('CL.command.1.tlog')).read_bytes().decode('utf16')
                need(names=={Path(p).name.lower() for p in re.findall(r'^\^([^\r\n]+)',prior,re.M)},'Same actual old core40 inventory')
            for _,command in rows:need(re.search(r'(?:^|\s)/MDd(?=\s|$)',command) and 'NDEBUG' not in command and '_ITERATOR_DEBUG_LEVEL=0' not in command,'Every actual parent TU genuine Debug')
            debug.append({'target':target,'actualTUs':len(rows),'library':stamp(BUILD/'Debug'/(target+'.lib'))})
        link=next((BUILD/(OWNER+'_tests.dir/Debug')).rglob('link.command.1.tlog'));raw=link.read_bytes();text=raw.decode('utf16').upper()
        for name in [SUPPORT,OWNER,*parents]:need('DEBUG\\'+name.upper()+'.LIB' in text,'Actual Debug owner link dependency '+name)
        need('RELEASE\\' not in text and 'RELEASE/' not in text and '/LTCG:OFF' in text,'No Release link or LTO workaround')
        (OUT/'actual-owner-debug-link.tlog.txt').write_bytes(raw)
        result.update(status='PASS',newCompileLogs=8,newTargetTUEntries=26,newTargetInventories=counts,debugNumericalTUs=43,debugDependencyInventories=debug,actualDebugOwnerSixLibraries=True,noReleaseImport=True,productionOwnerOrOldKernelChanged=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    (OUT/'verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:result[k] for k in ['status','newTargetTUEntries','debugNumericalTUs','error'] if k in result}));return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
