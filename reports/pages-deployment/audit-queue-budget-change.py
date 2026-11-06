"""Review one deploy-action input inside the unchanged12-minute job bound; no source or permission expansion."""
from pathlib import Path
import hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
BASE='20cc0218bc523effe929a3bbfc724f65f43077ca'
OUT=ROOT/'reports/pages-deployment/run-20261106-queue-budget-review-001'
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert __debug__ and not OUT.exists();OUT.mkdir()
 (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
 path='.github/workflows/pages.yml';old=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT);new=(ROOT/path).read_bytes();added=b"        with:\n          timeout: '660000'\n"
 assert new.count(added)==1 and new.replace(added,b'')==old
 assert b'timeout-minutes: 12' in old and b'timeout-minutes: 8' in old and b'retention-days: 1' in old
 assert b'actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346' in old and b'verify-archive.py' in old
 (OUT/'old-pages.yml.txt').write_bytes(old);(OUT/'new-pages.yml.txt').write_bytes(new)
 active=[ROOT/p for p in ['CMakeLists.txt','core/include/pikapika/report_values_wire.hpp','core/src/report_values_wire.cpp','core/report-values-schema-v1.json','cmake/ReportValuesSchema.cmake','.github/workflows/verify.yml']];before=[stamp(p) for p in active]
 args=['npm.cmd','run','build'];start=time.monotonic();p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=120)
 (OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);command=dict(argv=args,exitCode=p.returncode,seconds=time.monotonic()-start,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest());(OUT/'web-build.command.json').write_text(json.dumps(command,indent=2)+'\n',encoding='utf8');assert p.returncode==0
 after=[stamp(p) for p in active];assert before==after
 r=dict(schema=1,status='ONE_ACTION_TIMEOUT_INPUT_CHANGED_JOB_LIMITS_RETAINED',base=BASE,actionTimeoutMilliseconds=dict(previousDefault=600000,configured=660000),deployJobMinutes=12,buildJobMinutes=8,officialInputSource='https://raw.githubusercontent.com/actions/deploy-pages/368f82528645a54fb793d4d04e342629a3f51346/action.yml',onlyOneActionInputAdded=True,allOtherWorkflowBytesExact=True,actionSHAUnchanged=True,publicRepoGuardRunnerPermissionsEnvironmentDomainRetentionAndArchiveAuditUnchanged=True,byteBudgetsExpanded=False,jobLimitsExpanded=False,actualFutureDeploymentSuccess=False,command=command,before=before,after=after,activeCoreAndEngineWorkflowUnmodified=True,scope='Narrow configuration review and required web build only. Action timer10 to11minutes inside existing12-minute job; no guarantee of service queue completion and no old failure reclassification.')
 (OUT/'verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:r[k] for k in ['status','actionTimeoutMilliseconds','deployJobMinutes','activeCoreAndEngineWorkflowUnmodified','actualFutureDeploymentSuccess']}))
if __name__=='__main__':main()
