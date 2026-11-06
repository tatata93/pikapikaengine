"""Accept real GNU full GuardResult results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-guard-result-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-guard-result-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_GUARD_RESULT_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_GUARD_RESULT_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-guard-result-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_GUARD_RESULT_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==62,'All62 stable source files')
    required={'scripts/verify-report-guard-plane-metric-call-wire.py', 'scripts/verify-report-coverage-plane-source-snapshot-wire.py', 'scripts/verify-report-guard-plane-calls-wire.py', 'scripts/verify-report-guard-sphere-box-call-wire.py', 'scripts/verify-report-ledgers-wire.py', 'scripts/verify-report-coverage-snapshot-wire.py', 'scripts/verify-report-coverage-sphere-result-wire.py', 'scripts/verify-report-held-snapshot-work-wire.py', 'scripts/verify-report-guard-failure-wire.py', 'scripts/verify-diagnostic-wire.py', 'scripts/verify-report-coverage-plane-cell-work-wire.py', 'scripts/verify-report-guard-child-variant-wire.py', 'scripts/verify-report-coverage-sphere-audit-partition-wire.py', 'scripts/verify-report-guard-identity-body-wire.py', 'scripts/verify-report-values-wire.py', 'scripts/verify-report-coverage-plane-result-wire.py', 'scripts/verify-report-coverage-pair-result-wire.py', 'scripts/verify-report-guard-result-wire.py', 'scripts/verify-report-preparation-pair-values-wire.py', 'scripts/verify-report-guard-mesh-call-wire.py', 'scripts/verify-report-guard-plane-box-call-wire.py', 'scripts/verify-report-coverage-sphere-cell-work-wire.py', 'scripts/verify-report-flight-endpoint-wire.py', 'scripts/verify-report-coverage-cell-work-wire.py', 'scripts/verify-report-coverage-audit-partition-wire.py', 'scripts/verify-report-guard-pair-record-wire.py', 'scripts/verify-report-settings-wire.py', 'scripts/verify-report-work-wire.py', 'scripts/verify-report-coverage-plane-audit-partition-wire.py', 'scripts/verify-report-preparation-result-wire.py', 'scripts/verify-report-coverage-sphere-source-snapshot-wire.py', 'scripts/verify-report-preparation-snapshot-inventory-wire.py', 'scripts/verify-report-flight-source-tube-wire.py', 'scripts/verify-report-flight-result-wire.py'};need(a.get('oracleSourceClosure',{}).get('status')=='PASS' and set(a['oracleSourceClosure']['required'])==required and required.issubset({r['path'] for r in a['sourceBefore']}),'Actual complete34-oracle closure required')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==67 and all(c['exitCode']==0 for c in commands),'All67 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_guard_result_wire_tests.cpp','interval.cpp'],'Exactly2 production data,1 harness and1 test-only Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All4 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==219960 and fixture['stdoutSha256']=='9c900b65b091982e72f7e51b36ce64e22c0aeab12122f37d7f94de495d6e1382','Actual complete219960 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-guard-result-verification.json').read_bytes());need(a['native']['common']==native['native']['common'] and a['reference']==native['reference'],'All Native assertions and independent reference exact')
    reach=a['native']['reachability'];empty=reach['valuelessCases'];retained=reach['retainedCases']
    need(reach['attempts']==empty+retained==9 and reach['resultRejectionPhaseCases']==6*empty and reach['exactPartialPrefixCases']==4*empty and reach['existingStickyFailureCases']==5*empty and reach['valuelessReentryRefusals']==26175*empty and reach['independentPrefixBytes']==(573 if empty else 0) and reach['independentPrefixCallbacks']==(76 if empty else 0) and not reach['privateBytesModified'],'Actual legitimate platform-specific valueless/retained outcomes; no manufactured empty variant')
    for cfg in ['Release','Debug','Sanitized']:
        stops=a['stopShards'][cfg];need(len(stops)==16 and stops==native['stopShards']['Release'],'All16 actual stop assertions equal Native')
        for i in range(16):
            command=next(c for c in commands if c['name']==cfg+'-stop-'+str(i));need(command['argv'][-1]=='--stop-shard-'+str(i),'Actual stop shard command')
            if cfg=='Sanitized':need(command['sanitizerRuntimeOptions'],'Actual O1 Asan-Ubsan stop runtime options')
    need(a['all52350StopExceptionCasesPerConfiguration'],'All original52350 cases retained')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'wellFormedSingleByteMutations': 138586, 'recordOrderCountRejections': 3, 'absentToNullRejections': 289, 'presentToAbsentOrNullRejections': 520, 'enumToU32Rejections': 394, 'fieldValueExchangeRejections': 29092, 'objectFieldOrderRejections': 1544, 'arrayOrderCountRejections': 548, 'variantOrdinalByteMutations': 32, 'variantToPresentRejections': 8, 'variantWrapperRemovalRejections': 8, 'variantChildExchangeRejections': 26, 'variantChildPairsConsidered': 28, 'disjointVariantChildPairs': 27, 'nestedVariantChildPairs': 1, 'nestedVariantChildReplacementRejections': 2, 'messageLengthRejections': 147, 'identicalFieldExchanges': 340, 'identicalArrayOrders': 6, 'identicalVariantChildExchanges': 1}
    inventory={'entries': 138586, 'canonicalBytes': 13260615, 'canonicalSha256': 'ffe82711749f5866bf7a6d7090a0cce221ff486eb9d0e73daa7d7f9c3b39c216'}
    controls=a['referenceControls'];need(controls['status']=='PASS' and controls['shards']==4 and controls['controlsConsidered']==controls['controlsDecoded']==171199 and len(controls['perShard'])==4,'All four full control shards required')
    for i,shard in enumerate(controls['perShard']):
        need(shard['shard']==i and shard['status']=='PASS_SHARD' and shard['shards']==4 and shard['controlsConsidered']==171199 and shard['controlsDecoded']==(42800 if i<3 else 42799) and shard['baseline']==a['reference'] and all(shard[k]==v for k,v in expected.items()),'Every actual shard exact')
        need(shard['mutationInventory']==inventory and shard['comparisonMethod']['outsideScopeWholeBytesCompared'] and shard['comparisonMethod']['originalAncestorDepthReproduced'] and not shard['comparisonMethod']['mutationsDropped'] and shard['comparisonMethod']['wholeDocumentDualComparisons']>0,'All mutations retained; actual contextual/whole dual checks')
        command=next(c for c in commands if c['name']=='reference-controls-'+str(i));need(command['argv'][-5:]==['--hex','--shard',str(i),'--shards','4'] and any(Path(p).name=='report_guard_result_wire_reference_tests.py' for p in command['argv']),'Actual scanner shard command')
    need(a['mutationInventory']==inventory and all(controls[k]==v for k,v in expected.items()),'Complete171199 changes and347 identical exchanges separated')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and a['oldIntervalTUInstrumentedForHarness'] and a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==1 and not a['oldCoreBuiltOrLinked'],'Explicit4 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_GUARD_RESULT_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=67,actualDebugAndAllFourSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],reference=a['reference'],stopShards=a['stopShards'],all52350StopCasesPerConfiguration=True,mutationInventory=inventory,sourceFilesChecked=62,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-guard-result-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU full GuardResult step only. Exactly4 TUs, including one original test-only Interval TU; no numerical model library. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-guard-result-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
