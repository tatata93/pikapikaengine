"""Accept the returned real job record; child captures remain runner-local."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/world-static-mesh-session-publication/run-20261105-wire-gnu-actual-001'
SHA='77a363b38fd1af72a6452af33537b21657668c3f'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(not OUT.exists(),'Fresh acceptance directory');OUT.mkdir()
    raw=base64.b64decode((ROOT/'build/wire-addon-actual-log.base64').read_bytes(),validate=False)
    log=OUT/'owner-job-decoded.log.txt';log.write_bytes(raw)
    records=[]
    for line in raw.decode('utf8').splitlines():
        i=line.find('{"schema":')
        if i>=0:
            try:records.append(json.loads(line[i:]))
            except json.JSONDecodeError:pass
    need(len(records)==2,'Exactly parent and addon actual final records');parent,r=records
    need(parent['status']=='PASS' and len(parent['commands'])==21 and parent['actualGNUExecuted'],'Actual parent success')
    for k in ['actualGNUExecuted','reusedFreshParentDebugSanitizerBuilds','sourceStable','normalArtifactsStable','parentArtifactsStable','compilerStable','normalDebugSanitizedWholeRawExact','actualIntegerOptimizedProcessRefused']:
        need(r[k] is True,'Actual addon flag '+k)
    need(r['status']=='PASS' and r['actualCompilerVersion']=='13.3.0' and r['actualCompilerTarget']=='x86_64-linux-gnu','Actual GNU13 result')
    need(r['libraryTranslationUnits']==45 and r['newWireHarnessTranslationUnits']==2 and len(r['commands'])==22,'Actual command/TU inventory')
    need(all(c['exitCode']==0 for c in r['commands']),'All regular commands successful')
    need(r['sourceRowsPerBuild']==27 and r['tokenRowsPerBuild']==77 and r['sourceMappedFloatBitValues']==604 and r['copiedSourceRejectionsPerComparison']==13,'Bounded mapped inventories')
    need(r['normalBuildReconfiguredOrBuilt'] is False,'Normal immutable')
    for mode in ['normal','debug','sanitized']:
        need(r['references'][mode]['source']['status']=='PASS' and r['references'][mode]['token']['status']=='PASS','Actual references '+mode)
    write(OUT/'actual-parent-verification.json',parent);write(OUT/'actual-addon-verification.json',r)
    paths=['.github/workflows/verify.yml','reports/world-static-mesh-session-recipes/verify-wire-addon-gnu.py','reports/world-static-mesh-session-recipes/check-source-wire-reference.py','core/include/pikapika/world_static_mesh_session_source_wire.hpp','core/src/world_static_mesh_session_source_wire.cpp','tests/world_static_mesh_session_source_wire_tests.cpp','core/include/pikapika/world_static_mesh_session_wire.hpp','tests/world_static_mesh_session_wire_tests.cpp','scripts/verify-world-static-mesh-session-source-wire.py','scripts/verify-world-static-mesh-session-wire.py']
    for p in paths:
        old=subprocess.run(['git','show',SHA+':'+p],cwd=ROOT,capture_output=True,check=True).stdout
        need(old==(ROOT/p).read_bytes(),'Current source exact actual CI source '+p)
    sources=[stamp(ROOT/p) for p in paths];write(OUT/'accepted-sources.json',sources)
    receipt=dict(schema=1,status='ACTUAL_FINITE_GNU_SOURCE_AND_INTEGER_WIRE_PASS',source=SHA,runId=42033568554,jobId=127265818652,jobUrl='https://github.com/tatata93/pikapikaengine/actions/runs/42033568554/job/127265818652',actualCompilerVersion=r['actualCompilerVersion'],actualCompilerTarget=r['actualCompilerTarget'],regularAddonCommands=22,actualParentCommands=21,libraryTranslationUnits=45,newWireHarnessTranslationUnits=2,sourceRowsPerBuild=27,tokenRowsPerBuild=77,mappedSourceFloatBitValues=604,copiedSourceRejectionsPerComparison=13,normalDebugSanitizedWholeRawExact=True,sourceStable=True,normalArtifactsStable=True,parentArtifactsStable=True,compilerStable=True,decodedActualJobLog=stamp(log),actualParentVerification=stamp(OUT/'actual-parent-verification.json'),actualAddonVerification=stamp(OUT/'actual-addon-verification.json'),sources=stamp(OUT/'accepted-sources.json'),rawChildCaptureFilesDownloaded=False,wholeWorkflowAtObservation='in_progress',scope='Complete returned decoded UTF8 job log and actual final JSON records saved. Child captures/objects remain runner-local, not downloaded originals. Finite GNU13 normal/genuine Debug/45 production +2 wire harness O1 ASan-UBSan. No normalization of wire values. Not new allocator-fault, arbitrary plane-boundary, mesh/full guard, C ABI/JS/WASM/model-step or whole engine completion.')
    write(OUT/'receipt.json',receipt);write(ROOT/'reports/world-static-mesh-session-wire-gnu-verification.json',receipt)
    write(ROOT/'reports/world-static-mesh-session-recipes/wire-gnu-acceptance-freeze.json',dict(schema=1,status=receipt['status'],sources=sources,acceptance=stamp(ROOT/'reports/world-static-mesh-session-wire-gnu-verification.json')))
    print(json.dumps(dict(status=receipt['status'],log=stamp(log),regularAddonCommands=22)))
if __name__=='__main__':main()
