"""Accept returned actual GNU packet record, preserving all prior phase records."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-publication/run-20261106-packet-gnu-actual-001'
SHA='b01610b15d326e36cd5b4146f7d0e1dcd1438297'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def main():
    need(not OUT.exists(),'Fresh acceptance');OUT.mkdir();log=OUT/'owner-job-decoded.log.txt';log.write_bytes(base64.b64decode((ROOT/'build/packet-actual-gnu-log.base64').read_bytes()));records=[]
    for l in log.read_text(encoding='utf8').splitlines():
        i=l.find('{"schema":')
        if i>=0:
            try:records.append(json.loads(l[i:]))
            except json.JSONDecodeError:pass
    need(len(records)==5 and [len(r['commands']) for r in records]==[21,22,15,1,11] and all(r['status']=='PASS' and all(c['exitCode']==0 for c in r['commands']) for r in records),'Actual five driver chain')
    r=records[-1]
    for k in ['actualGNUExecuted','reusedFreshParentDebugSanitizerBuilds','sourceStable','normalArtifactsStable','parentArtifactsStable','normalDebugSanitizedWholeRawExact','actualFourFpuModesObservedAndRetained']:need(r[k] is True,'Actual packet flag '+k)
    need(r['normalBuildReconfiguredOrBuilt'] is False and r['modelCoreLinked'] is False and r['actualCompilerVersion']=='13.3.0' and r['newProductionTUs']==r['newHarnessTUs']==1 and r['rowsPerBuild']==24 and r['mappedFloatBitValues']==492 and r['negativeZeroOccurrences']==164,'Actual GNU packet inventory')
    for mode in ['normal','debug','sanitized']:need(r['references'][mode]['status']=='PASS' and r['references'][mode]['inputFingerprint']=='e81c7b5dd04bee50d51f76f0c06d669d06b01edaa9955c2bb1c0bf243a570475','Actual pinned independent reference '+mode)
    for name,record in zip(['owner','wire','api','fault','packet'],records):write(OUT/('actual-'+name+'-verification.json'),record)
    files=['CMakeLists.txt','.github/workflows/verify.yml','core/include/pikapika/world_static_mesh_session_packet_wire.hpp','core/src/world_static_mesh_session_packet_wire.cpp','tests/world_static_mesh_session_packet_wire_tests.cpp','scripts/verify-world-static-mesh-session-packet-wire.py','reports/world-static-mesh-session-recipes/verify-packet-wire-gnu.py']
    for rel in files:need(subprocess.run(['git','show',SHA+':'+rel],cwd=ROOT,capture_output=True,check=True).stdout==(ROOT/rel).read_bytes(),'Current exact actual CI source '+rel)
    sources=[stamp(ROOT/p) for p in files];write(OUT/'accepted-sources.json',sources)
    receipt=dict(schema=1,status='ACTUAL_FINITE_GNU_OWNED_PACKET_WIRE_PASS',source=SHA,runId=42054806291,jobId=127340156639,jobUrl='https://github.com/tatata93/pikapikaengine/actions/runs/42054806291/job/127340156639',actualCompilerVersion='13.3.0',regularPacketCommands=11,earlierParentCommands=[21,22,15,1],newProductionTUs=1,newHarnessTUs=1,modelCoreLinked=False,rowsPerBuild=24,mappedFloatBitValues=492,negativeZeroOccurrences=164,actualFourFpuModesObservedAndRetained=True,normalDebugSanitizedWholeRawExact=True,normalArtifactsStable=True,parentArtifactsStable=True,sourceStable=True,decodedActualJobLog=stamp(log),actualReturnedVerification=stamp(OUT/'actual-packet-verification.json'),sources=stamp(OUT/'accepted-sources.json'),rawChildCaptureFilesDownloaded=False,wholeWorkflowAtObservation='in_progress',scope='Actual finite GNU13 pure packet-data normal/true Debug/O1 ASan-UBSan one production+one harness. All24/492bit/164negativezero/full64/mode/raw exact without normalization. Earlier API/model/fault artifacts immutable. Complete returned decoded UTF8 log/final records saved; child raw/object files runner-local. Four rounding-mode copy is not a full FPU/machine certificate. No packet allocator fault, C ABI pump/complete Report export/JS/WASM/game completion.')
    canonical=ROOT/'reports/world-static-mesh-session-packet-wire-gnu-verification.json';write(canonical,receipt);write(OUT/'receipt.json',receipt);write(HERE/'packet-wire-gnu-acceptance-freeze.json',dict(schema=1,status=receipt['status'],sources=sources,canonical=stamp(canonical)));print(json.dumps(dict(status=receipt['status'],log=stamp(log),regularPacketCommands=11)))
if __name__=='__main__':main()
