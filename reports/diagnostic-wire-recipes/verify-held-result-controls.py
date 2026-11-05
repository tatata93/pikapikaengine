"""Recheck identical full mutation output after caching only the independent expected tree."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-held-result-controls-002'

def need(v,m):
    if not v:raise ValueError(m)

def stamps():
    paths=['tests/report_held_result_wire_reference_tests.py','scripts/verify-report-held-result-wire.py','scripts/verify-diagnostic-wire.py']+['scripts/verify-report-'+name+'-wire.py' for name in ['held-source','held-snapshot-work','held-proofs','held-audits']]
    return [dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in paths]

def main():
    need(__debug__ and not OUT.exists(),'Fresh mutation receipt');OUT.mkdir(parents=True);before=stamps()
    argv=[sys.executable,'-B','-X','utf8','tests/report_held_result_wire_reference_tests.py','reports/diagnostic-wire-recipes/run-20261106-held-result-native-001/Release-fixture.stdout.hex.txt','--hex']
    start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=180);elapsed=time.monotonic()-start
    (OUT/'reference-controls.stdout.txt').write_bytes(p.stdout);(OUT/'reference-controls.stderr.txt').write_bytes(p.stderr)
    command=dict(argv=argv,exitCode=p.returncode,seconds=elapsed,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest())
    (OUT/'command.json').write_text(json.dumps(command,indent=2)+'\n',encoding='utf8',newline='\n')
    need(p.returncode==0,'Actual mutation process');prior=(ROOT/'reports/diagnostic-wire-integration/run-20261106-held-result-native-001/reference-controls.stdout.txt').read_bytes()
    need(p.stdout==prior and before==stamps(),'Every prior result and mutated path/byte offset unchanged; sources stable')
    result=dict(status='PASS',allPriorMutationOutputRawExact=True,priorActualSeconds=132.98400000017136,actualCommand=command,sourceBefore=before,sourceAfter=stamps(),scope='Independent expected tree cached once; every grammar-valid mutation fully decoded and typed-compared. Exact same whole stdout as first132.984s run; no production, oracle specification, Native fixture, Node or model changes.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status='PASS',seconds=elapsed,allPriorMutationOutputRawExact=True)))
if __name__=='__main__':main()
