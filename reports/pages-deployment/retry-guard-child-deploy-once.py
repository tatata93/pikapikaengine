"""One bounded retry of the observed failed Child Pages deploy, using existing CLI authorization."""
from pathlib import Path
import hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/pages-deployment/run-20261106-guard-child-variant-deploy-retry-001'
SOURCE='c66c84472974a2b21eff8e26d30a53a4714d0bde';RUN=42242406268;JOB=127976082832
def main():
 assert __debug__ and not OUT.exists();OUT.mkdir()
 (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());commands=[]
 def call(name,args):
  start=time.monotonic();p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=120)
  (OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
  row=dict(argv=args,exitCode=p.returncode,seconds=time.monotonic()-start,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest());commands.append(row)
  (OUT/(name+'.command.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf8')
  assert p.returncode==0,name;return p.stdout
 job=json.loads(call('before-job',['gh','api',f'repos/tatata93/pikapikaengine/actions/jobs/{JOB}']))
 run=json.loads(call('before-run',['gh','api',f'repos/tatata93/pikapikaengine/actions/runs/{RUN}']))
 assert job['id']==JOB and job['run_id']==RUN and job['name']=='deploy' and job['status']=='completed' and job['conclusion']=='failure'
 assert run['head_sha']==SOURCE and run['id']==RUN and run['conclusion']=='failure'
 call('retry-failed-deploy',['gh','api','--method','POST',f'repos/tatata93/pikapikaengine/actions/jobs/{JOB}/rerun'])
 r=dict(schema=1,status='ONE_FAILED_DEPLOY_RETRY_REQUEST_ACCEPTED',source=SOURCE,run=RUN,failedJob=JOB,commands=commands,workflowModified=False,timeoutsOrPermissionsExpanded=False,actualRetrySuccess=False,scope='Existing authenticated CLI; one failed deploy job only, no downstream jobs. Integration retry403 retained separately. Request acceptance is not deployment success.')
 (OUT/'receipt.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps({k:r[k] for k in ['status','source','run','failedJob','actualRetrySuccess']}))
if __name__=='__main__':main()
