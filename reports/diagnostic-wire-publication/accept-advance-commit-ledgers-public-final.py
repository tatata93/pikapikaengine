"""Continue an exact-source accepted public proof with actual final19 CI states."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]

def need(value,message):
 if not value:raise ValueError(message)

def stamp(path):
 raw=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main():
 need(__debug__,'Optimized Python refused')
 prior=ROOT/'reports/diagnostic-wire-advance-commit-ledgers-public-verification.json'
 jobs=ROOT/'reports/world-static-mesh-flight-advance-public-checks/run-20261106-advance-commit-ledgers-final-001/result.json'
 target=ROOT/'reports/diagnostic-wire-advance-commit-ledgers-public-final-verification.json'
 need(not target.exists(),'New receipt only')
 p=json.loads(prior.read_bytes());j=json.loads(jobs.read_bytes())
 need(p['status']=='FINITE_ADVANCE_COMMIT_LEDGERS_NATIVE_GNU_PUBLIC_READY_ENGINE_PENDING' and p['publicReady'] and not p['allEngineJobsAccepted'] and p['nativeTestedAndProtectedUniqueGitBlobsChecked']==473,'Accepted public/Native/GNU pending CI receipt first')
 need(re.fullmatch('[0-9a-f]{40}',p['source']) is not None and j['feature']==p['source'],'Exact full source')
 for key in ['engine','pages']:
  run=j['runs'][key]
  need(run['id']==p[key+'Run'] and run['status']=='completed' and run['conclusion']=='success' and all(row['status']=='completed' and row['conclusion']=='success' for row in run['jobs']),'Every actual job succeeded')
 need(len(j['runs']['engine']['jobs'])==19 and len(j['runs']['pages']['jobs'])==2,'All19 engine jobs and both Pages jobs')
 for key in ['native','gnu','jobs','manifest','samples','archive','archiveProvenance','ui']:
  need(stamp(ROOT/p[key]['path'])==p[key],'Original acceptance source unchanged')
 result=dict(schema=1,status='FINITE_ADVANCE_COMMIT_LEDGERS_NATIVE_GNU_PUBLIC_READY_ALL19_CI_PASS',source=p['source'],prior=stamp(prior),finalJobs=stamp(jobs),allEngineJobsAccepted=True,engineJobCount=19,pagesSuccess=True,publicReady=True,launchEnabled=True,nativeTestedAndProtectedUniqueGitBlobsChecked=473,priorProofSourcesUnchanged=True,testsRerun=False,allHTTPPayloadsTransferred=False,newGetterConnectedToWASMOrGame=False,fullReportMapped=False,CABIPumpImplemented=False,launchURL=p['launchURL'])
 target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(status=result['status'],testsRerun=False)))

if __name__=='__main__':main()
