"""Accept actual returned GNU C/C++ job JSON, not local policy substitutes."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-publication/run-20261105-native-api-gnu-actual-001'
SHA='57d8bd81fb27ad1c65863b54d51499933ad312c2'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def main():
    need(not OUT.exists(),'Fresh actual acceptance');OUT.mkdir();log=OUT/'owner-job-decoded.log.txt';log.write_bytes(base64.b64decode((ROOT/'build/native-api-actual-gnu-log.base64').read_bytes()))
    records=[]
    for line in log.read_text(encoding='utf8').splitlines():
        i=line.find('{"schema":')
        if i>=0:
            try:records.append(json.loads(line[i:]))
            except json.JSONDecodeError:pass
    need(len(records)==3 and [len(r['commands']) for r in records]==[21,22,15] and all(r['status']=='PASS' and all(c['exitCode']==0 for c in r['commands']) for r in records),'Actual completed parent/wire/API command chain')
    r=records[-1]
    for k in ['actualGNUExecuted','freshCAndCxxSanitizerConfigured','sourceStable','normalArtifactsStable','parentArtifactsStable','compilerStable','normalDebugSanitizedWholeRawExact','actualOptimizedPythonRefused']:need(r[k] is True,'Actual flag '+k)
    need(r['normalBuildReconfiguredOrBuilt'] is False and r['actualCCompilerVersion']==r['actualCxxCompilerVersion']=='13.3.0' and r['actualCCompilerTarget']=='x86_64-linux-gnu','Actual C/C++ compiler and normal immutability')
    need(r['libraryTranslationUnits']==46 and r['harnessTranslationUnits']==2 and r['actualCLanguageHarnessTranslationUnits']==1 and r['sourceRowsPerBuild']==9 and r['mappedFloatBitValues']==1254 and r['negativeZeroOccurrences']==142,'Actual API translation unit and full-field inventory')
    for mode in ['normal','debug','sanitized']:need(r['references'][mode]['status']=='PASS' and r['references'][mode]['rows']==9,'Actual independent reference '+mode)
    for name,value in zip(['parent','wire','api'],records):write(OUT/('actual-'+name+'-verification.json'),value)
    files=['CMakeLists.txt','.github/workflows/verify.yml','core/include/pikapika/world_static_mesh_session_api.h','core/src/world_static_mesh_session_api.cpp','tests/world_static_mesh_session_api_tests.cpp','tests/world_static_mesh_session_api_c_tests.c','scripts/verify-world-static-mesh-session-api.py','reports/world-static-mesh-session-recipes/verify-native-api-gnu.py','reports/world-static-mesh-session-recipes/verify-wire-addon-gnu.py','reports/world-static-mesh-session-recipes/verify-gnu.py']
    for rel in files:need(subprocess.run(['git','show',SHA+':'+rel],cwd=ROOT,capture_output=True,check=True).stdout==(ROOT/rel).read_bytes(),'Current source identical to actual CI '+rel)
    sources=[stamp(ROOT/p) for p in files];write(OUT/'accepted-sources.json',sources)
    receipt=dict(schema=1,status='ACTUAL_FINITE_GNU_NATIVE_C_API_PASS',source=SHA,runId=42039281181,jobId=127285493025,jobUrl='https://github.com/tatata93/pikapikaengine/actions/runs/42039281181/job/127285493025',actualCCompilerVersion='13.3.0',actualCxxCompilerVersion='13.3.0',actualCompilerTarget='x86_64-linux-gnu',regularAPICommands=15,actualParentCommands=[21,22],libraryTranslationUnits=46,harnessTranslationUnits=2,actualCHarnessTranslationUnits=1,actualNormalDebugAndCAndCxxSanitized=True,sourceRowsPerBuild=9,mappedFloatBitValues=1254,negativeZeroOccurrences=142,normalDebugSanitizedWholeRawExact=True,actualOptimizedPythonRefused=True,sourceStable=True,normalArtifactsStable=True,parentArtifactsStable=True,compilerStable=True,decodedActualJobLog=stamp(log),actualReturnedVerification=stamp(OUT/'actual-api-verification.json'),sources=stamp(OUT/'accepted-sources.json'),rawChildCaptureFilesDownloaded=False,wholeWorkflowAtObservation='in_progress',scope='Actual finite GNU13 C/C++ Native plain lifecycle API, all46 production plus actual C/C++ harness O1 ASan-UBSan and true Debug. Full9/all1254bit/142negativezero/integers/raw exact, no identity normalization. Returned decoded UTF8 full log/final records saved; child raw/object files remained runner-local. Not new fault-injection/reentry, all allocator, pump/mesh/full guard, JS/WASM/game or general physics completion.')
    canonical=ROOT/'reports/world-static-mesh-session-c-api-gnu-verification.json';write(canonical,receipt);write(OUT/'receipt.json',receipt);write(HERE/'native-api-gnu-acceptance-freeze.json',dict(schema=1,status=receipt['status'],sources=sources,canonical=stamp(canonical)))
    print(json.dumps(dict(status=receipt['status'],log=stamp(log),regularAPICommands=15)))
if __name__=='__main__':main()
