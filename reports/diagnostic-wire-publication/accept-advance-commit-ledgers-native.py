"""Publish a finite Native acceptance only after real full parent exit and independent audits."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-commit-ledgers-native-001'
def need(v,m):
 if not v:raise ValueError(m)
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observed-parent-exit',required=True,type=int);args=parser.parse_args()
 target=ROOT/'reports/diagnostic-wire-advance-commit-ledgers-verification.json';need(__debug__ and args.observed_parent_exit==0 and not target.exists(),'Fresh receipt and actual observed parent exit0')
 n=json.loads((NATIVE/'verification.json').read_bytes());i=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-commit-ledgers-native-001/verification.json';f=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-commit-ledgers-final-001/verification.json';w=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-commit-ledgers-web-001/verification.json';c=ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-commit-ledgers-controls-002/verification.json'
 integration=json.loads(i.read_bytes());final=json.loads(f.read_bytes());web=json.loads(w.read_bytes());control=json.loads(c.read_bytes())
 need(n['status']=='FINITE_NATIVE_REPORT_ADVANCE_COMMIT_LEDGERS_PASS' and n['sourceStable'] and n['protectedRawExact'] and n['baselineRawStable'] and n['selectedCTestPerConfiguration']==67 and len(n['assertionResults'])==134,'Whole actual Native')
 need(integration['status']=='FINITE_ADVANCE_COMMIT_LEDGERS_INTEGRATION_PASS' and integration['all134ActualAssertionRecordsRechecked'] and not integration['testsRerun'] and final['status']=='PASS' and final['mappedRecordTypes']==101 and final['mappedFields']==600 and final['webBuildExitCode']==0,'Independent assertions and final source review')
 need(web['status']=='FINITE_ADVANCE_COMMIT_LEDGERS_WEB_PASS' and control['status']=='PASS' and control['sourceStable'] and control['controlsDecoded']==10547 and control['identicalFieldExchanges']==112,'Actual Web and all controls')
 result=dict(n,totalMappedRecordTypes=101,totalMappedFields=600,totalMappedVariants=2,nativeReceipt=stamp(NATIVE/'verification.json'),integrationReceipt=stamp(i),finalSourceReview=stamp(f),webReceipt=stamp(w),controlsReceipt=stamp(c),fullNativeParentObservedExitCode=0,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False,newGetterConnectedToWASMOrGame=False)
 target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status=result['status'],totalMappedRecordTypes=101,totalMappedFields=600,selectedCTestPerConfiguration=67)))
if __name__=='__main__':main()
