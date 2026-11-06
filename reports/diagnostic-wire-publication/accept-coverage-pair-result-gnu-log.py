"""Accept real GNU Audit/Partition results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-coverage-pair-result-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-coverage-pair-result-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_COVERAGE_PAIR_RESULT_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_COVERAGE_PAIR_RESULT_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-coverage-pair-result-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_COVERAGE_PAIR_RESULT_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==33,'All33 stable source files')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==16 and all(c['exitCode']==0 for c in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_coverage_pair_result_wire_tests.cpp','interval.cpp'],'Exactly2 production,1 harness,1 test-only original Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All4 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==30168 and fixture['stdoutSha256']=='f9d39fcdff3f3a3e0957894c7365573d9743a733fc6b8b8bbf7493e5a34c996a','Actual complete30168 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-coverage-pair-result-verification.json').read_bytes());need(a['native']['common']==native['native']['common'] and a['reference']==native['reference'],'All common Native assertions and independent reference exact')
    reach=a['native']['reachability']
    need(reach==dict(attempts=4,valuelessCases=0,retainedCases=4,resultRejectionPhaseCases=0,exactPartialPrefixCases=0,existingStickyFailureCases=0,valuelessReentryRefusals=0,privateBytesModified=False),'Actual GNU retained-alternative branch; no invented valueless execution')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'wellFormedSingleByteMutations': 16856, 'recordOrderCountRejections': 3, 'absentToNullRejections': 126, 'presentToAbsentOrNullRejections': 262, 'enumToU32Rejections': 168, 'fieldValueExchangeRejections': 2508, 'objectFieldOrderRejections': 303, 'arrayOrderCountRejections': 523, 'variantOrdinalByteMutations': 32, 'variantToPresentRejections': 8, 'variantWrapperRemovalRejections': 8, 'variantChildExchangeRejections': 24, 'messageLengthRejections': 33, 'identicalFieldExchanges': 53, 'identicalArrayOrders': 3, 'identicalVariantChildExchanges': 4, 'controlsConsidered': 20854, 'controlsDecoded': 20854}
    need(all(a['referenceControls'][k]==v for k,v in expected.items()) and a['referenceControls']['status']=='PASS','Actual20854 semantic changes;60 identical exchanges separate')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and a['oldIntervalTUInstrumentedForHarness'] and a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==1 and not a['oldCoreBuiltOrLinked'],'Explicit4 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_COVERAGE_PAIR_RESULT_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=16,actualDebugAndAllFourSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],nativeCommonMatchesMsvc=True,gnuRetained4MsvcValueless4Separate=True,reference=a['reference'],sourceFilesChecked=33,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-coverage-pair-result-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU complete pair Result step only. All4 TUs include original Interval for test source construction. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-coverage-pair-result-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
