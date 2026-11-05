"""Independent actual27 source projections and copied-oracle rejection controls."""
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-source-wire-reference/run-20261105-pinned-001'
CHECKER=ROOT/'scripts/verify-world-static-mesh-session-source-wire.py'


def need(ok,message):
    if not ok:raise ValueError(message)


def main():
    need(not OUT.exists(),'Fresh reference evidence');OUT.mkdir(parents=True);sys.dont_write_bytecode=True
    (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());(OUT/'checker.py.txt').write_bytes(CHECKER.read_bytes())
    spec=importlib.util.spec_from_file_location('plain_source_reference',CHECKER);ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    base=HERE/'run-20261105-source-wire-producer-001';paths={Path(__file__).resolve(),CHECKER,base/'Release-source-wire.json',base/'Debug-source-wire.json',ROOT/'core/include/pikapika/world_static_mesh_session_source_wire.hpp',ROOT/'core/src/world_static_mesh_session_source_wire.cpp',ROOT/'tests/world_static_mesh_session_source_wire_tests.cpp'}
    stamps=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)};before=stamps();start=time.monotonic();result={'status':'FAIL','scope':__doc__}
    def write(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
    try:
        need(json.loads((base/'result.json').read_bytes())['status']=='FINITE_NATIVE_PLAIN_SOURCE_PRODUCER_PASS','Actual complete Native producer prerequisite')
        captures={cfg:json.loads((base/(cfg+'-source-wire.json')).read_bytes()) for cfg in ['Release','Debug']};references={cfg:ref.verify(d) for cfg,d in captures.items()};need((base/'Release-source-wire.json').read_bytes()==(base/'Debug-source-wire.json').read_bytes(),'Whole actual producer raw equality')
        data=captures['Release'];rejected=[]
        def reject(name,change):
            copied=deepcopy(data);change(copied)
            try:ref.verify(copied)
            except (ValueError,KeyError,TypeError,IndexError):rejected.append(name)
            else:raise ValueError('Copied source alteration accepted: '+name)
        def setpath(path,value):
            def change(d):
                for key in path[:-1]:d=d[key]
                d[path[-1]]=value
            return change
        good=next(i for i,r in enumerate(data['rows']) if r['source'] is not None and len(r['source']['bodies'])==2)
        wide=next(i for i,r in enumerate(data['rows']) if r['source'] is not None and r['source']['ticks']==2**64-1)
        maximum=next(i for i,r in enumerate(data['rows']) if r['source'] is not None and len(r['source']['planes'])==16)
        failed=next(i for i,r in enumerate(data['rows']) if r['status']==5)
        p=['rows',good,'source']
        reject('body-position-field',setpath(p+['bodies',0,'positionBits',0],0))
        reject('signed-zero-margin',setpath(p+['marginBits'],0))
        reject('bool-static-to-same-int',setpath(p+['bodies',0,'static'],0))
        reject('full64-body-id-truncated',setpath(['rows',wide,'source','bodies',0,'id'],2**32-1))
        reject('full64-ticks-as-float',setpath(['rows',wide,'source','ticks'],float(2**64-1)))
        reject('raw-body-order',lambda d:d['rows'][good]['source']['bodies'].reverse())
        reject('plane-order',lambda d:d['rows'][maximum]['source']['planes'].reverse())
        reject('partial-source-on-refusal',setpath(['rows',failed,'source'],{}))
        reject('wrong-error-index',setpath(['rows',failed,'index'],0))
        reject('status-same-valued-float',setpath(['rows',good,'status'],0.0))
        reject('unknown-source-field',lambda d:d['rows'][good]['source'].update(invented=1))
        reject('missing-case',lambda d:d['rows'].pop())
        def consistent_input_and_output_change(d):
            d['rows'][good]['words'][5]+=1;d['rows'][good]['source']['bodies'][0]['id']+=1
        reject('pinned-consistent-input-output-change',consistent_input_and_output_change)
        renamed=deepcopy(data)
        for i,row in enumerate(renamed['rows']):row['name']='renamed/'+str(i)
        renamed['rows'].reverse();need(ref.verify(renamed)['inputFingerprint']==references['Release']['inputFingerprint'],'Nonsemantic names/order remain independent')
        argv=[sys.executable,'-O',str(CHECKER),str(base/'Release-source-wire.json')];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30);(OUT/'optimized.stdout.txt').write_bytes(p.stdout);(OUT/'optimized.stderr.txt').write_bytes(p.stderr);write('optimized-command.json',{'argv':argv,'exitCode':p.returncode});need(p.returncode!=0 and b'normal Python' in p.stderr,'Actual -O process refuses')
        result.update(status='PASS',references=references,copiedNegativeControls=len(rejected),rejected=rejected,labelAndDocumentOrderIndependent=True,actualOptimizedPythonRefused=True,actualAllocatorFaultInjected=False,scope='Actual27 Release/Debug mapped v1 bit/field projections plus13 copied refusals and actual -O process. Real owner lifetime assertions are in the Native producer, not synthesized rows here. No general plane-rounding proof, allocator fault, mesh, C ABI/JS/WASM or model step acceptance.')
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    result.update(sourceStable=before==stamps(),seconds=time.monotonic()-start)
    if not result['sourceStable']:result['status']='FAIL'
    write('verification.json',result);print(json.dumps({k:result[k] for k in ['status','copiedNegativeControls','labelAndDocumentOrderIndependent','actualOptimizedPythonRefused','sourceStable','error'] if k in result}));return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
