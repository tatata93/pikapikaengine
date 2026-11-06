"""Early independent typed/mutation review from the actual new Release harness; full Native regressions accepted separately."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-input-variant-reference-001'
def need(v,m):
    if not v:raise ValueError(m)
def main():
    need(__debug__ and not OUT.exists(),'Fresh independent reference review');OUT.mkdir(parents=True);commands=[]
    def run(name,args,binary=False):
        p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,timeout=120)
        (OUT/(name+('.stdout.hex.txt' if binary else '.stdout.txt'))).write_bytes((p.stdout.hex()+'\n').encode() if binary else p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        commands.append(dict(name=name,argv=list(map(str,args)),exitCode=p.returncode,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest()));need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(status='FAIL',scope=__doc__)
    try:
        exe=ROOT/'build/wfdciv2/Release/pikapika_report_coverage_input_variant_wire_tests.exe'
        test=json.loads(run('run',[exe,'--run']));need(test['common']['status']=='PASS','Actual new harness assertions')
        raw=run('fixture',[exe,'--fixture'],True);need(len(raw)==1899,'Whole variant fixture bytes')
        reference=json.loads(run('reference',[sys.executable,'-B','-X','utf8','scripts/verify-report-coverage-input-variant-wire.py',OUT/'fixture.stdout.hex.txt','--hex']))
        controls=json.loads(run('reference-controls',[sys.executable,'-B','-X','utf8','tests/report_coverage_input_variant_wire_reference_tests.py',OUT/'fixture.stdout.hex.txt','--hex']))
        expected=dict(wellFormedSingleByteMutations=640,recordOrderCountRejections=3,namedInputOrderRejections=4,variantOrdinalByteMutations=16,variantToPresentRejections=4,variantWrapperRemovalRejections=4,variantChildSwapRejections=4)
        need(all(controls[k]==v for k,v in expected.items()),'Actual complete variant controls')
        result.update(status='FINITE_COVERAGE_INPUT_VARIANT_REFERENCE_PASS',native=test,reference=reference,referenceControls={k:v for k,v in controls.items() if k!='mutations'},allNativeRegressionsComplete=False,actualGNUExecuted=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    result['commands']=commands;(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','native','error'] if k in result}));return int(result['status']!='FINITE_COVERAGE_INPUT_VARIANT_REFERENCE_PASS')
if __name__=='__main__':raise SystemExit(main())
