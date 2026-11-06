"""Accept real GNU sphere Result results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-coverage-sphere-result-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-coverage-sphere-result-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_COVERAGE_SPHERE_RESULT_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_COVERAGE_SPHERE_RESULT_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-coverage-sphere-result-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_COVERAGE_SPHERE_RESULT_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==32,'All32 stable source files')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==31 and all(c['exitCode']==0 for c in commands),'All31 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_coverage_sphere_result_wire_tests.cpp','interval.cpp'],'Exactly2 production,1 harness,1 test-only original Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All4 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==57252 and fixture['stdoutSha256']=='96e49d871fbd6d0713112787c1d199310eba11086a60c087368fa51011fd9d2e','Actual complete57252 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-coverage-sphere-result-verification.json').read_bytes());need(a['native']==native['native'] and a['reference']==native['reference'],'All Native assertions and independent reference exact')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'controlsConsidered': 38958, 'wellFormedSingleByteMutations': 32288, 'recordOrderCountRejections': 3, 'absentToNullRejections': 125, 'presentToAbsentOrNullRejections': 238, 'enumToU32Rejections': 160, 'fieldValueExchangeRejections': 4951, 'objectFieldOrderRejections': 615, 'arrayOrderCountRejections': 515, 'variantOrdinalByteMutations': 0, 'variantToPresentRejections': 0, 'variantWrapperRemovalRejections': 0, 'variantChildExchangeRejections': 0, 'messageLengthRejections': 63, 'identicalFieldExchanges': 247, 'identicalArrayOrders': 3, 'identicalVariantChildExchanges': 0, 'controlsDecoded': 38958}
    need(all(a['referenceControls'][k]==v for k,v in expected.items()) and a['referenceControls']['status']=='PASS','Actual differing controls and unchanged exchanges separate')
    need(a['referenceControls']['allSixteenShardsAccepted'] and a['referenceControls']['shards']==16,'Actual16-shard aggregate')
    for index in range(16):
        argv=next(c for c in commands if c['name']=='reference-controls-'+str(index))['argv'];need(argv[-4:]==['--shard',str(index),'--shards','16'],'Exact distinct assigned shard command')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and a['oldIntervalTUInstrumentedForHarness'] and a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==1 and not a['oldCoreBuiltOrLinked'],'Explicit4 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_COVERAGE_SPHERE_RESULT_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=31,actualDebugAndAllFourSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],reference=a['reference'],sourceFilesChecked=32,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-coverage-sphere-result-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU sphere Result step only. All4 TUs include original Interval for test source construction. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-coverage-sphere-result-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
