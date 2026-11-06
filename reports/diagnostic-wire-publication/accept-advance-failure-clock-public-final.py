"""Continue the accepted exact-source public proof with actual final18 CI states."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert __debug__
 prior=ROOT/'reports/diagnostic-wire-advance-failure-clock-public-verification.json'
 jobs=ROOT/'reports/world-static-mesh-flight-advance-public-checks/run-20261106-advance-failure-clock-final-001/result.json'
 target=ROOT/'reports/diagnostic-wire-advance-failure-clock-public-final-verification.json'
 assert not target.exists()
 p=json.loads(prior.read_bytes());j=json.loads(jobs.read_bytes())
 assert p['status']=='FINITE_ADVANCE_FAILURE_CLOCK_NATIVE_GNU_PUBLIC_READY_ENGINE_PENDING' and p['publicReady'] and not p['allEngineJobsAccepted'] and p['nativeTestedAndProtectedUniqueGitBlobsChecked']==467
 assert j['feature']==p['source']=='84b743dfdd248ce610798b75872bd3d6cf485137'
 for k in ['engine','pages']:
  r=j['runs'][k];assert r['id']==p[k+'Run'] and r['status']=='completed' and r['conclusion']=='success' and all(x['status']=='completed' and x['conclusion']=='success' for x in r['jobs'])
 assert len(j['runs']['engine']['jobs'])==18 and len(j['runs']['pages']['jobs'])==2
 for key in ['native','gnu','jobs','manifest','samples','archive','archiveProvenance','ui']:
  assert stamp(ROOT/p[key]['path'])==p[key]
 result=dict(schema=1,status='FINITE_ADVANCE_FAILURE_CLOCK_NATIVE_GNU_PUBLIC_READY_ALL18_CI_PASS',source=p['source'],prior=stamp(prior),finalJobs=stamp(jobs),allEngineJobsAccepted=True,engineJobCount=18,pagesSuccess=True,publicReady=True,launchEnabled=True,nativeTestedAndProtectedUniqueGitBlobsChecked=467,priorProofSourcesUnchanged=True,testsRerun=False,allHTTPPayloadsTransferred=False,newGetterConnectedToWASMOrGame=False,fullReportMapped=False,CABIPumpImplemented=False,launchURL=p['launchURL'])
 target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status=result['status'],testsRerun=False)))
if __name__=='__main__':main()
