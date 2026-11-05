"""Accept actual GNU fault positions, without forcing Native STL counts."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-publication/run-20261105-native-api-fault-gnu-actual-001'
SHA='aa0e36764c77907b1b646f58d5d7f8e57e5829c5'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def main():
    need(not OUT.exists(),'Fresh acceptance');OUT.mkdir();log=OUT/'owner-job-decoded.log.txt';log.write_bytes(base64.b64decode((ROOT/'build/native-api-fault-actual-gnu-log.base64').read_bytes()));records=[]
    for l in log.read_text(encoding='utf8').splitlines():
        i=l.find('{"schema":')
        if i>=0:
            try:records.append(json.loads(l[i:]))
            except json.JSONDecodeError:pass
    need(len(records)==4 and [len(r['commands']) for r in records]==[21,22,15,1] and all(r['status']=='PASS' and all(c['exitCode']==0 for c in r['commands']) for r in records),'Actual four completed driver chain')
    r=records[-1];need(r['actualGNUFaultExecuted'] and r['sourceStable'] and r['normalArtifactsAndCompilerStable'] and r['actualSanitizedFaultExecutable'] is False and r['normalBuildReconfiguredOrBuilt'] is False,'Actual fault run and stable normal artifacts')
    need(r['actualCxxCompilerVersion']=='13.3.0' and r['contextFailurePositions']==1 and r['operationFailurePositions']==[9,3,3,2] and r['actualOperationFailures']==17 and r['actualAllocatorBusyReentryChecks']==20 and r['cachedGetterAllocations']==0 and r['stageCapturedBeforeAllocation'],'Actual GNU observed positions/guards')
    for name,value in zip(['owner','wire','api','fault'],records):write(OUT/('actual-'+name+'-verification.json'),value)
    paths=['CMakeLists.txt','.github/workflows/verify.yml','tests/world_static_mesh_session_api_allocation_tests.cpp','core/include/pikapika/world_static_mesh_session_api.h','core/src/world_static_mesh_session_api.cpp','reports/world-static-mesh-session-recipes/verify-native-api-allocation-gnu.py']
    for p in paths:need(subprocess.run(['git','show',SHA+':'+p],cwd=ROOT,capture_output=True,check=True).stdout==(ROOT/p).read_bytes(),'Current accepted source exact Git '+p)
    sources=[stamp(ROOT/p) for p in paths];write(OUT/'accepted-sources.json',sources)
    receipt=dict(schema=1,status='ACTUAL_FINITE_GNU_NORMAL_C_API_ALLOCATION_PASS',source=SHA,runId=42043319829,jobId=127299536652,jobUrl='https://github.com/tatata93/pikapikaengine/actions/runs/42043319829/job/127299536652',actualCxxCompilerVersion='13.3.0',actualFaultCommands=1,earlierParentCommands=[21,22,15],contextFailurePositions=1,operationFailurePositions={'stage':9,'create':3,'reset':3,'read':2},actualOperationFailures=17,actualTotalFailurePositions=18,actualAllocatorBusyReentryChecks=20,cachedGetterAllocations=0,normalReleaseOnly=True,actualSanitizedFaultExecutable=False,normalArtifactsAndCompilerStable=True,sourceStable=True,decodedActualJobLog=stamp(log),actualReturnedFaultVerification=stamp(OUT/'actual-fault-verification.json'),sources=stamp(OUT/'accepted-sources.json'),rawChildCaptureFilesDownloaded=False,NativeObservedTotalFailurePositions=23,NativeAndGNUCountsForcedEqual=False,wholeWorkflowAtObservation='in_progress',scope='Actual GNU13 normal-only global scalar/array new failures. All measured context/stage/create/reset/read positions and20 allocator-callback busy checks/whole cache/live owner/recovery verified. GNU stage9 vs Native14 is observed STL allocation difference, not normalized equality. Complete returned decoded log/final records saved; child raw/object files runner-local. Separate C+C++ ASan parent is not fault executable. No all allocator/OS OOM/aligned/CRT/thread/post-pump fault, packet decoder, pump/mesh/full guard/JS/WASM/game acceptance.')
    canonical=ROOT/'reports/world-static-mesh-session-c-api-allocation-gnu-verification.json';write(canonical,receipt);write(OUT/'receipt.json',receipt);write(HERE/'native-api-allocation-gnu-acceptance-freeze.json',dict(schema=1,status=receipt['status'],sources=sources,canonical=stamp(canonical)));print(json.dumps(dict(status=receipt['status'],actualGNUFailures=18,NativeFailures=23,log=stamp(log))))
if __name__=='__main__':main()
