"""Fresh actual Native plain-source producer and real owner lifetime assertions.

Producer only; independent full source-wire reference is a separate next gate.
"""
from pathlib import Path
import hashlib
import json
import re
import runpy
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'build/wfop1'
OUT=HERE/'run-20261105-source-wire-producer-001'
LIB='pikapika_world_static_mesh_session_source_wire'
TARGET=LIB+'_tests'


def need(ok,message):
    if not ok:raise ValueError(message)


def stamp(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')


def main():
    need(sys.platform=='win32' and not BUILD.exists() and not OUT.exists(),'Fresh actual MSVC source producer');BUILD.mkdir();OUT.mkdir();sys.dont_write_bytecode=True
    old=runpy.run_path(str(ROOT/'reports/world-static-mesh-flight-scheduler-recipes/check-full-fixtures.py'),run_name='readonly_old_paths')
    watched=set(old['protected']())|{Path(__file__).resolve(),ROOT/'tests/world_static_mesh_session_source_wire_tests.cpp'}
    for name in ['wfos1','wfot1','wfot2','wfow1']:
        watched.update(p for p in (ROOT/'build'/name).rglob('*') if p.is_file() and (p.suffix in {'.exe','.lib','.vcxproj'} or p.name.endswith('command.1.tlog') or p.name.startswith(('world-flight-','world-owned-'))))
    watched=sorted(watched);identities=lambda:{p.relative_to(ROOT).as_posix():stamp(p) for p in watched};before=identities();write(OUT/'before.json',before);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());commands=[]
    def run(name,argv,timeout=180):
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,timeout=timeout);(OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        row={'name':name,'argv':list(map(str,argv)),'exitCode':p.returncode,'seconds':time.monotonic()-start};commands.append(row);write(OUT/(name+'.command.json'),row);print(json.dumps({k:row[k] for k in ['name','exitCode','seconds']}),flush=True)
        if p.returncode:print(p.stdout.decode(errors='replace')[-12000:]);print(p.stderr.decode(errors='replace')[-12000:])
        need(p.returncode==0,'Actual command failed: '+name);return p.stdout
    result={'schema':1,'status':'FAIL','scope':__doc__,'independentSourceReferenceAccepted':False,'actualGNUExecuted':False}
    try:
        run('01-configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON']);inventories={}
        for cfg,count in [('Release',54),('Debug',53)]:
            listing=json.loads(run('02-'+cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));names={r['name'] for r in listing['tests']}
            prior=json.loads((HERE/'run-20261105-token-wire-001'/('02-'+cfg+'-inventory.stdout.txt')).read_bytes());need(len(names)==count and names=={r['name'] for r in prior['tests']}|{'world_static_mesh_session_source_wire'},'Exact old inventory plus one plain source test');inventories[cfg]=count
        for stem in ['world-flight-binding','world-flight-scheduler-binding','world-flight-controlled-tick-binding','world-flight-controlled-scheduler-binding','world-owned-session-configuration']:
            for cfg in ['Release','Debug','MinSizeRel','RelWithDebInfo']:
                n=stem+'-'+cfg+'.json';need((BUILD/n).read_bytes()==(ROOT/'build/wfow1'/n).read_bytes(),'Old20 configuration documents raw exact')
        captures=[];provenance=[]
        for cfg in ['Release','Debug']:
            run(cfg+'-build',['cmake','--build',BUILD,'--config',cfg,'--target',TARGET,'--parallel','2'],900)
            run(cfg+'-directed-ctest',['ctest','--test-dir',BUILD,'-C',cfg,'-R','^world_static_mesh_session_source_wire$','--output-on-failure'])
            raw=run(cfg+'-fixtures',[BUILD/cfg/(TARGET+'.exe'),'--fixtures']);p=OUT/(cfg+'-source-wire.json');p.write_bytes(raw);captures.append(raw);data=json.loads(raw)
            need(data['schema']==1 and data['kind']=='plain-session-source-wire-fixtures' and data['actualRows']==len(data['rows'])==27,'Actual27 finite producer envelope')
            for target in [LIB,TARGET]:
                logs=list((BUILD/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));need(len(logs)==1,'One actual compiler log per new target/config');rawlog=logs[0].read_bytes();text=rawlog.decode('utf16');need(len(re.findall(r'^\^',text,re.M))==1,'One actual TU per new target')
                for flag in ['/W4','/WX','/permissive-','/fp:strict','/GL-']:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual new-source strict flags')
                need(re.search(r'(?:^|\s)'+('/MDd' if cfg=='Debug' else '/MD')+r'(?=\s|$)',text),'Actual separate runtime config');copy=OUT/(str(len(provenance))+'-compile.tlog.txt');copy.write_bytes(rawlog);provenance.append(stamp(copy))
        need(captures[0]==captures[1],'All source producer raw bytes exact across actual Release/Debug')
        result.update(status='FINITE_NATIVE_PLAIN_SOURCE_PRODUCER_PASS',inventories=inventories,commandsRecorded=len(commands),actualNewDirectedCTestPerConfiguration=1,old53TestsRerun=False,old20ConfigurationDocumentsRawExact=True,sourceRowsPerBuild=27,actualCallerDecodedOwnerOldReadLifetimeAssertions=True,realReleaseDebugRawExact=True,actualCompileLogs=provenance,CABIOrJSOrWASMChanged=False)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    finally:
        after=identities();write(OUT/'after.json',after);result.update(sourceStable=before==after,protectedPaths=len(watched),commands=commands)
        if before!=after:result['status']='FAIL'
        write(OUT/'result.json',result)
    print(json.dumps({k:result[k] for k in ['status','sourceStable','error'] if k in result}),flush=True);return int(result['status']!='FINITE_NATIVE_PLAIN_SOURCE_PRODUCER_PASS')


if __name__=='__main__':raise SystemExit(main())
