"""Accept real GNU guard PlaneCalls results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-guard-plane-calls-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-guard-plane-calls-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_GUARD_PLANE_CALLS_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_GUARD_PLANE_CALLS_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-guard-plane-calls-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_GUARD_PLANE_CALLS_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==41,'All41 stable source files')
    required={'scripts/verify-report-guard-plane-calls-wire.py', 'scripts/verify-report-guard-plane-metric-call-wire.py', 'scripts/verify-report-coverage-snapshot-wire.py', 'scripts/verify-report-guard-plane-box-call-wire.py', 'scripts/verify-diagnostic-wire.py', 'scripts/verify-report-coverage-plane-source-snapshot-wire.py', 'scripts/verify-report-ledgers-wire.py', 'scripts/verify-report-coverage-audit-partition-wire.py', 'scripts/verify-report-coverage-plane-result-wire.py', 'scripts/verify-report-coverage-plane-cell-work-wire.py', 'scripts/verify-report-coverage-plane-audit-partition-wire.py', 'scripts/verify-report-coverage-pair-result-wire.py', 'scripts/verify-report-coverage-cell-work-wire.py'};need(a.get('oracleSourceClosure',{}).get('status')=='PASS' and set(a['oracleSourceClosure']['required'])==required and required.issubset({r['path'] for r in a['sourceBefore']}),'Actual complete13-oracle closure required')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==31 and all(c['exitCode']==0 for c in commands),'All31 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_guard_plane_calls_wire_tests.cpp','interval.cpp'],'Exactly2 production,1 harness,1 test-only original Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All4 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==48803 and fixture['stdoutSha256']=='4d00bf11c4dad940991fb5b642ea9a0d33207f55f3eec81ae6ba7a219a77754d','Actual complete48803 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-guard-plane-calls-verification.json').read_bytes());need(a['native']==native['native'] and a['reference']==native['reference'],'All Native assertions and independent reference exact')
    reach=a['reachability'];need(reach['attempts']==4 and reach['valuelessCases']+reach['retainedCases']==4 and not reach['privateBytesModified'],'Actual public emplace branches retained separately')
    count=reach['valuelessCases'];need(reach['resultRejectionPhaseCases']==6*count and reach['exactPartialPrefixCases']==4*count and reach['existingStickyFailureCases']==5*count and reach['valuelessReentryRefusals']==a['native']['callbackBoundaries']*count,'All actual reachable rejection/prefix/sticky/reentry cases')
    need(native['reachability']['valuelessCases']==4 and native['reachability']['retainedCases']==0,'Previously measured Native branch kept separate')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'controlsConsidered': 35067, 'wellFormedSingleByteMutations': 29057, 'recordOrderCountRejections': 3, 'absentToNullRejections': 135, 'presentToAbsentOrNullRejections': 262, 'enumToU32Rejections': 184, 'fieldValueExchangeRejections': 4510, 'objectFieldOrderRejections': 441, 'arrayOrderCountRejections': 448, 'variantOrdinalByteMutations': 8, 'variantToPresentRejections': 2, 'variantWrapperRemovalRejections': 2, 'variantChildExchangeRejections': 1, 'messageLengthRejections': 14, 'identicalFieldExchanges': 69, 'identicalArrayOrders': 4, 'identicalVariantChildExchanges': 0, 'controlsDecoded': 35067}
    need(all(a['referenceControls'][k]==v for k,v in expected.items()) and a['referenceControls']['status']=='PASS','Actual differing controls and unchanged exchanges separate')
    need(a['referenceControls']['allSixteenShardsAccepted'] and a['referenceControls']['shards']==16,'Actual16-shard aggregate')
    for index in range(16):
        argv=next(c for c in commands if c['name']=='reference-controls-'+str(index))['argv'];need(argv[-4:]==['--shard',str(index),'--shards','16'],'Exact distinct assigned shard command')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and a['oldIntervalTUInstrumentedForHarness'] and a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==1 and not a['oldCoreBuiltOrLinked'],'Explicit4 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_GUARD_PLANE_CALLS_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=31,actualDebugAndAllFourSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],reachability=reach,nativeReachability=native['reachability'],reference=a['reference'],sourceFilesChecked=41,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-guard-plane-calls-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU guard PlaneCalls step only. All4 TUs include original Interval for test source construction. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-guard-plane-calls-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
