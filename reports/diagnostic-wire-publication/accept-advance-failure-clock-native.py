"""Publish a finite Native acceptance only after real full parent exit and independent audits."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-failure-clock-native-001'
def need(v,m):
 if not v:raise ValueError(m)
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observed-parent-exit',required=True,type=int);args=parser.parse_args()
 target=ROOT/'reports/diagnostic-wire-advance-failure-clock-verification.json';need(__debug__ and args.observed_parent_exit==0 and not target.exists(),'Fresh receipt and actual observed parent exit0')
 n=json.loads((NATIVE/'verification.json').read_bytes());i=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-failure-clock-native-001/verification.json';f=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-failure-clock-final-001/verification.json';w=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-failure-clock-web-001/verification.json';c=ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-failure-clock-controls-001/verification.json'
 integration=json.loads(i.read_bytes());final=json.loads(f.read_bytes());web=json.loads(w.read_bytes());control=json.loads(c.read_bytes())
 need(n['status']=='FINITE_NATIVE_REPORT_ADVANCE_FAILURE_CLOCK_PASS' and n['sourceStable'] and n['protectedRawExact'] and n['baselineRawStable'] and n['selectedCTestPerConfiguration']==66 and len(n['assertionResults'])==132,'Whole actual Native')
 need(integration['status']=='FINITE_ADVANCE_FAILURE_CLOCK_INTEGRATION_PASS' and integration['all132ActualAssertionRecordsRechecked'] and not integration['testsRerun'] and final['status']=='PASS' and final['mappedRecordTypes']==99 and final['mappedFields']==581 and final['webBuildExitCode']==0,'Independent assertions and final source review')
 need(web['status']=='FINITE_ADVANCE_FAILURE_CLOCK_WEB_PASS' and control['status']=='PASS' and control['sourceStable'] and control['controlsDecoded']==3196 and control['identicalFieldExchanges']==7,'Actual Web and all controls')
 result=dict(n,totalMappedRecordTypes=99,totalMappedFields=581,totalMappedVariants=2,nativeReceipt=stamp(NATIVE/'verification.json'),integrationReceipt=stamp(i),finalSourceReview=stamp(f),webReceipt=stamp(w),controlsReceipt=stamp(c),fullNativeParentObservedExitCode=0,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False,newGetterConnectedToWASMOrGame=False)
 target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status=result['status'],totalMappedRecordTypes=99,totalMappedFields=581,selectedCTestPerConfiguration=66)))
if __name__=='__main__':main()
