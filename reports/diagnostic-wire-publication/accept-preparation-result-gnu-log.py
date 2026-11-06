"""Accept real GNU preparation Result results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-preparation-result-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-preparation-result-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_PREPARATION_RESULT_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_PREPARATION_RESULT_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-preparation-result-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_PREPARATION_RESULT_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==32,'All32 stable source files')
    required={'scripts/verify-report-values-wire.py', 'scripts/verify-report-preparation-pair-values-wire.py', 'scripts/verify-report-guard-failure-wire.py', 'scripts/verify-diagnostic-wire.py', 'scripts/verify-report-preparation-snapshot-inventory-wire.py', 'scripts/verify-report-preparation-result-wire.py'};need(a.get('oracleSourceClosure',{}).get('status')=='PASS' and set(a['oracleSourceClosure']['required'])==required and required.issubset({r['path'] for r in a['sourceBefore']}),'Actual complete6-oracle closure required')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==19 and all(c['exitCode']==0 for c in commands),'All19 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_preparation_result_wire_tests.cpp'],'Exactly2 production and1 harness; no Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All3 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==26194 and fixture['stdoutSha256']=='8af9c976bdd5f701d5ad90b3d1893e4334bc355c91ea65e71fbc2dc0890d937f','Actual complete26194 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-preparation-result-verification.json').read_bytes());need(a['native']==native['native'] and a['reference']==native['reference'],'All Native assertions and independent reference exact')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'wellFormedSingleByteMutations': 15037, 'recordOrderCountRejections': 3, 'absentToNullRejections': 74, 'presentToAbsentOrNullRejections': 64, 'enumToU32Rejections': 152, 'fieldValueExchangeRejections': 2104, 'objectFieldOrderRejections': 246, 'arrayOrderCountRejections': 108, 'variantOrdinalByteMutations': 0, 'variantToPresentRejections': 0, 'variantWrapperRemovalRejections': 0, 'variantChildExchangeRejections': 0, 'variantChildPairsConsidered': 0, 'disjointVariantChildPairs': 0, 'nestedVariantChildPairs': 0, 'nestedVariantChildReplacementRejections': 0, 'messageLengthRejections': 52, 'identicalFieldExchanges': 96, 'identicalArrayOrders': 4, 'identicalVariantChildExchanges': 0}
    controls=a['referenceControls'];need(controls['status']=='PASS' and controls['shards']==4 and controls['controlsConsidered']==controls['controlsDecoded']==17840 and len(controls['perShard'])==4,'All four controls required')
    for i,shard in enumerate(controls['perShard']):
        need(shard['shard']==i and shard['status']=='PASS_SHARD' and shard['shards']==4 and shard['controlsConsidered']==17840 and shard['controlsDecoded']==4460 and shard['baseline']==a['reference'] and all(shard[k]==v for k,v in expected.items()),'Every actual shard exact')
        command=next(c for c in commands if c['name']=='reference-controls-'+str(i));need(command['argv'][-5:]==['--hex','--shard',str(i),'--shards','4'] and any(Path(p).name=='report_preparation_result_wire_reference_tests.py' for p in command['argv']),'Actual scanner shard command')
    need(all(controls[k]==v for k,v in expected.items()),'Whole17840 differing controls and100 identical exchanges separated')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and not a['oldIntervalTUInstrumentedForHarness'] and not a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==0 and not a['oldCoreBuiltOrLinked'],'Explicit3 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_PREPARATION_RESULT_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=19,actualDebugAndAllThreeSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=0,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],reference=a['reference'],sourceFilesChecked=32,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-preparation-result-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU preparation Result step only. Exactly3 TUs, no Interval TU or numerical model library. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-preparation-result-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
