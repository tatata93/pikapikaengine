"""Copied actual77 comparison controls and actual Windows GNU platform refusal.

Synthetic second IDs are labeled copy controls, never sanitizer observations.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import math
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'run-20261105-gnu-controls-001'


def need(ok,message):
    if not ok:raise ValueError(message)


def imported(name,path):
    sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    need(not OUT.exists(),'Fresh control evidence');OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    driver=imported('owner_gnu_controls',HERE/'verify-gnu.py');helper=imported('owner_gnu_exact_tree',ROOT/'reports/world-static-mesh-flight-guard-recipes/verify-gnu.py')
    fixture=HERE/'run-20261105-full-003/owner-full.json';data=helper.load(fixture);binding=next(r for _,r in driver.reports(data))['binding']
    ids={k:binding[v] for k,v in [('packet','buildId'),('controlled','controlledBuildId'),('clock','schedulerBuildId'),('advance','upstreamBuildId')]}
    copied_ids={k:sha256(('COPY-CONTROL-NOT-AN-OBSERVATION-'+v).encode()).hexdigest() for k,v in ids.items()};copied=deepcopy(data);driver.map_ids(copied,ids,copied_ids)
    watched={Path(__file__).resolve(),HERE/'verify-gnu.py',HERE/'GNU_PLAN.md',fixture};stamps=lambda:{str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(watched)};before=stamps();start=time.monotonic();result={'status':'FAIL','actualGNUExecuted':False,'scope':__doc__}
    def write(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
    try:
        comparison=driver.compare_full(helper,data,copied,ids,copied_ids);rejected=[]
        def reject(name,change):
            changed=deepcopy(copied);change(changed)
            try:driver.compare_full(helper,data,changed,ids,copied_ids)
            except (ValueError,KeyError,TypeError,IndexError):rejected.append(name)
            else:raise ValueError('Copied alteration accepted: '+name)
        def setpath(path,value):
            def change(d):
                for key in path[:-1]:d=d[key]
                d[path[-1]]=value
            return change
        current=next(i for i,r in enumerate(copied['fixtures']) if r['kind']=='pump' and r['result']['report'] is not None and r['result']['report']['attempts']>0)
        retained=next(i for i,r in enumerate(copied['fixtures']) if any(p['report'] is not None for p in r['retainedPumps']))
        retained_slot=next(i for i,p in enumerate(copied['fixtures'][retained]['retainedPumps']) if p['report'] is not None)
        base=['fixtures',current,'result','report'];past=['fixtures',retained,'retainedPumps',retained_slot,'report']
        for location,label in [(base,'current'),(past,'retained')]:
            for key in ['buildId','controlledBuildId','schedulerBuildId','upstreamBuildId']:reject(label+'-'+key,setpath(location+['binding',key],'0'*64))
        reject('current-controlled-id',setpath(base+['tickReports',0,'report','binding','buildId'],'0'*64))
        reject('current-advance-id',setpath(base+['tickReports',0,'report','child','binding','buildId'],'0'*64))
        reject('current-guard-id',setpath(base+['tickReports',0,'report','child','guard','binding','buildId'],'0'*64))
        reject('retained-controlled-id',setpath(past+['tickReports',0,'report','binding','buildId'],'0'*64))
        reject('unused-fixed-report-slot',setpath(base+['tickReports',7],False))
        reject('attempt-integer-to-same-float',setpath(base+['attempts'],float(copied['fixtures'][current]['result']['report']['attempts'])))
        made=next(i for i,r in enumerate(copied['fixtures']) if r['kind']=='create' and r['result']['status']=='ok')
        reject('owner-generation-integer-to-same-float',setpath(['fixtures',made,'result','token','generation'],float(copied['fixtures'][made]['result']['token']['generation'])))
        def negative_zero(value,path=()):
            if type(value) is float and value==0 and math.copysign(1,value)<0:return path
            if isinstance(value,dict):
                for k,v in value.items():
                    found=negative_zero(v,path+(k,))
                    if found is not None:return found
            if isinstance(value,list):
                for k,v in enumerate(value):
                    found=negative_zero(v,path+(k,))
                    if found is not None:return found
            return None
        nz=negative_zero(copied);need(nz is not None,'Actual observed negative zero control');reject('actual-negative-zero-to-positive-zero',setpath(nz,0.0))
        snapshot=next(i for i,r in enumerate(copied['fixtures']) if r['retainedSnapshots'])
        reject('past-owned-snapshot-position',setpath(['fixtures',snapshot,'retainedSnapshots',0,'world','bodies',0,'position',0],1.25))
        reject('whole-document-row-order',lambda d:d['fixtures'].reverse())
        reject('missing-operation',lambda d:d['fixtures'].pop())
        reject('invented-runtime-owner-id',lambda d:d['fixtures'][current]['result'].update(ownerBuildId=copied_ids['packet']))
        def binding_order(d):
            r=d['fixtures'][current]['result']['report'];r['binding']=dict(reversed(list(r['binding'].items())))
        reject('binding-object-key-order',binding_order)
        for name,changed in [('aliased-family',dict(copied_ids,clock=copied_ids['packet'])),('extra-family',dict(copied_ids,owner='1'*64)),('stale-family',dict(copied_ids,packet=ids['packet']))]:
            try:driver.compare_full(helper,data,copied,ids,changed)
            except ValueError:rejected.append(name)
            else:raise ValueError('Bad identity tuple accepted: '+name)
        if sys.platform=='win32':
            output=ROOT/'build/public-checks/owner-gnu-refusal001'
            argv=[sys.executable,'-B','-X','utf8',str(HERE/'verify-gnu.py'),'--normal',str(ROOT/'build/wfos1'),'--output',str(output),'--sanbuild',str(ROOT/'build/wfo-refusal-san1'),'--debugbuild',str(ROOT/'build/wfo-refusal-debug1')]
            p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120);(OUT/'windows-refusal.stdout.txt').write_bytes(p.stdout);(OUT/'windows-refusal.stderr.txt').write_bytes(p.stderr)
            refusal=json.loads((output/'verification.json').read_bytes());need(p.returncode!=0 and refusal['status']=='FAIL' and refusal['actualGNUExecuted'] is False and 'Actual Linux GNU13 required' in refusal['error'],'Actual Windows process explicitly refuses GNU')
            write('windows-refusal-verification.json',refusal);result['actualWindowsRefusal']={'argv':argv,'exitCode':p.returncode,'error':refusal['error']}
        result.update(status='PASS',copyComparison=comparison,copiedNegativeControls=len(rejected),rejected=rejected,actualFixture={'path':fixture.relative_to(ROOT).as_posix(),'sha256':sha256(fixture.read_bytes()).hexdigest()},syntheticSecondIdentityTupleIsObservation=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    result.update(seconds=time.monotonic()-start,sourceStable=before==stamps())
    if not result['sourceStable']:result['status']='FAIL'
    write('verification.json',result);print(json.dumps({k:result[k] for k in ['status','copiedNegativeControls','actualGNUExecuted','sourceStable','error'] if k in result}));return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
