"""Actual Windows packet GNU refusal, no compiler or parent build invocation."""
from pathlib import Path
import ast,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'run-20261105-packet-wire-gnu-driver-001'
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def need(v,m):
    if not v:raise ValueError(m)
def main():
    need(sys.platform=='win32' and not OUT.exists(),'Fresh Windows-only output');OUT.mkdir();driver=HERE/'verify-packet-wire-gnu.py';ast.parse(driver.read_text(encoding='utf8'));paths=[driver,Path(__file__).resolve(),ROOT/'.github/workflows/verify.yml',ROOT/'core/src/world_static_mesh_session_packet_wire.cpp'];before=[stamp(p) for p in paths]
    refusal=ROOT/'build/public-checks/packet-wire-gnu-refusal-001';need(not refusal.exists(),'Fresh actual refusal');argv=[sys.executable,'-B','-X','utf8',str(driver),'--output',str(refusal)];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60);(OUT/'refusal.stdout.txt').write_bytes(p.stdout);(OUT/'refusal.stderr.txt').write_bytes(p.stderr);(OUT/'refusal.command.json').write_text(json.dumps(dict(argv=argv,exitCode=p.returncode),indent=2)+'\n',encoding='utf8');r=json.loads((refusal/'verification.json').read_bytes());need(p.returncode==1 and r['status']=='FAIL' and 'Actual Linux GNU13 required' in r['error'] and r['commands']==[] and r['actualGNUExecuted'] is False and r['reusedFreshParentDebugSanitizerBuilds'] is False and r['sourceStable'],'Actual zero-command unsupported-platform refusal')
    for f in refusal.iterdir():
        if f.is_file():(OUT/f.name).write_bytes(f.read_bytes())
    jobs=(ROOT/'.github/workflows/verify.yml').read_text(encoding='utf8').split('\njobs:\n',1)[1];need(len(re.findall(r'^  [a-z][a-z-]+:$',jobs,re.M))==6 and jobs.count('timeout-minutes: 20')==5 and jobs.count('timeout-minutes: 25')==1 and jobs.count('if: github.event.repository.private == false')==6,'Same six public jobs/budgets')
    need(before==[stamp(p) for p in paths],'Driver/workflow/source stable');result=dict(status='PASS',actualWindowsRefusal=True,actualGNUExecuted=False,actualBuildCommands=0,sixPublicJobsAndBudgetsUnchanged=True,sources=before,scope=__doc__);(OUT/'local-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(status='PASS',actualGNUExecuted=False)))
if __name__=='__main__':main()
