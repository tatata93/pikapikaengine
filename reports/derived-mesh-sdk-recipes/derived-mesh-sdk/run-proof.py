import hashlib,json,platform,struct,subprocess,sys,tempfile,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROOF=ROOT/'build/derived-mesh-sdk'
RUN=Path(tempfile.mkdtemp(prefix='run-',dir=PROOF))
DEPENDENCY=PROOF/'dependency-core.lib'
VCVARS=r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
OWNED=['core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','tests/simulation_api_tests.cpp','tools/derived_mesh_probe.cpp']
def sha(data):return hashlib.sha256(data).hexdigest()
def file_info(path):
    p=Path(path);data=p.read_bytes();return {'bytes':len(data),'sha256':sha(data)}
def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
BEFORE={p:file_info(ROOT/p) for p in OWNED}
COMMANDS=[]
def run(label,args,expected=0):
    start=datetime.now(timezone.utc).isoformat();timer=time.perf_counter()
    p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    stdout=RUN/(label+'.stdout.bin');stderr=RUN/(label+'.stderr.bin');stdout.write_bytes(p.stdout);stderr.write_bytes(p.stderr)
    COMMANDS.append({'label':label,'argv':args,'cwd':str(ROOT),'startedUTC':start,'observedWallSeconds':time.perf_counter()-timer,'exitCode':p.returncode,'expectedExitCode':expected,'stdout':str(stdout.relative_to(ROOT)),'stderr':str(stderr.relative_to(ROOT)),'stdoutSHA256':sha(p.stdout),'stderrSHA256':sha(p.stderr)})
    write_json(RUN/'commands.json',COMMANDS)
    if p.returncode!=expected:raise RuntimeError(f'{label}: expected exit {expected}, got {p.returncode}')
    return p.stdout
def compile(label,sources,exe):
    folder=RUN/label;folder.mkdir();batch=RUN/(label+'.cmd')
    command='cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /permissive- /Icore/include '+' '.join(sources)+' "'+str(DEPENDENCY)+'" /Fe"'+str(exe)+'" /Fo"'+str(folder)+'/" /link /INCREMENTAL:NO'
    batch.write_text('@echo off\ncall "'+VCVARS+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+command+'\n',encoding='utf-8',newline='\r\n')
    run(label,['cmd.exe','/d','/c',str(batch)])
def load(raw):return json.loads(raw,parse_int=lambda s:-0.0 if s=='-0' else int(s))
def tree(value):
    if isinstance(value,bool) or value is None or isinstance(value,str):return value
    if isinstance(value,(int,float)):return struct.pack('>d',float(value)).hex()
    if isinstance(value,list):return [tree(x) for x in value]
    return {k:tree(v) for k,v in value.items()}

abi=RUN/'simulation-api-tests.exe';probe=RUN/'pikapika-derived-probe.exe'
compile('compile-abi',['core/src/simulation_api.cpp','tests/simulation_api_tests.cpp'],abi)
abi_stdout=run('run-abi',[str(abi)])
if not abi_stdout.rstrip().endswith(b'65 simulation C ABI test groups passed'):raise RuntimeError('Missing full ABI acceptance summary')
compile('compile-probe',['tools/derived_mesh_probe.cpp'],probe)
raw=run('probe-fixtures',[str(probe),'--fixtures']);(RUN/'probe-fixtures.json').write_bytes(raw)
fixtures=load(raw)['fixtures']
if len(fixtures)!=11 or not all(x['sourceSavedUnchanged'] for x in fixtures):raise RuntimeError('Probe fixture count/source preservation')
path=RUN/'input.skin';path.write_bytes(fixtures[0]['input']['portable'].encode('utf-8'));source_before=path.read_bytes()
for label,seconds,loop,reference in [('file-t1','1',False,fixtures[2]),('file-loop-t3','3',True,fixtures[4])]:
    args=[str(probe),'sample',str(path),seconds]+(['loop'] if loop else [])
    value=load(run(label,args))['fixtures'][0]
    for key in ['sourceSavedUnchanged','sourceError','deformation','derivedInput','derived']:
        if tree(value[key])!=tree(reference[key]):raise RuntimeError(f'File/probe parity mismatch: {label} {key}')
    if path.read_bytes()!=source_before:raise RuntimeError('Probe changed input file bytes')
run('reject-negative-time',[str(probe),'sample',str(path),'-1'],1)
run('reject-playback',[str(probe),'sample',str(path),'1','unknown'],1)
if path.read_bytes()!=source_before:raise RuntimeError('Invalid command changed input file bytes')
AFTER={p:file_info(ROOT/p) for p in OWNED}
if BEFORE!=AFTER:raise RuntimeError('Source changed during proof')
revision=run('revision',['git','rev-parse','HEAD']).decode('ascii').strip()
acceptance={'schema':1,'passed':True,'abiGroups':65,'newAbiGroups':6,'probeFixtures':11,'fileReplays':2,'invalidCliControls':2,'sourceUnchanged':True,'fixtureSHA256':sha(raw),'scope':'Native targeted fresh source compile linked to a copied current CMake core library. Main SDK and full clean CMake verification are independently owned by root. No GPU/world/raster guarantee.'}
write_json(RUN/'acceptance.json',acceptance)
provenance={'schema':1,'createdUTC':datetime.now(timezone.utc).isoformat(),'revisionBase':revision,'platform':platform.platform(),'python':sys.version,'sources':AFTER,'dependency':{'path':str(DEPENDENCY.relative_to(ROOT)),**file_info(DEPENDENCY),'note':'Stable current CMake library copy; source API definitions are freshly compiled explicitly and its archive API object is not required.'},'artifacts':{str(p.relative_to(ROOT)):file_info(p) for p in [abi,probe,RUN/'probe-fixtures.json',RUN/'commands.json',RUN/'acceptance.json',Path(__file__)]},'acceptance':acceptance}
write_json(RUN/'provenance.json',provenance);write_json(PROOF/'latest.json',{'schema':1,'runDirectory':str(RUN.relative_to(ROOT))})
print(json.dumps({'passed':True,'runDirectory':str(RUN.relative_to(ROOT)),'fixtureSHA256':sha(raw)}))
