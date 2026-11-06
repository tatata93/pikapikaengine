"""Accept real GNU Audit/Partition results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-coverage-sphere-evaluation-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-coverage-sphere-evaluation-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_COVERAGE_SPHERE_EVALUATION_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_COVERAGE_SPHERE_EVALUATION_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-coverage-sphere-evaluation-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_COVERAGE_SPHERE_EVALUATION_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==29,'All29 stable source files')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==16 and all(c['exitCode']==0 for c in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_coverage_sphere_evaluation_wire_tests.cpp','interval.cpp'],'Exactly2 production,1 harness,1 test-only original Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All4 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==7943 and fixture['stdoutSha256']=='27c788911afda064a0533dc13e365f4608bb06f91c8072f8f49cb284c054694d','Actual complete7943 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-coverage-sphere-evaluation-verification.json').read_bytes());need(a['native']==native['native'] and a['reference']==native['reference'],'All Native assertions and independent reference exact')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'wellFormedSingleByteMutations': 4328, 'typedPayloadByteMutations': 1960, 'recordOrderCountRejections': 3, 'fieldValueExchangeRejections': 412, 'objectFieldOrderRejections': 136, 'fixedAxisArrayOrderCountRejections': 120, 'identicalFieldExchanges': 20, 'identicalAxisExchanges': 0, 'totalDifferingControls': 4999}
    need(all(a['referenceControls'][k]==v for k,v in expected.items()) and a['referenceControls']['status']=='PASS','Actual4999 differing semantic changes and20 unchanged field exchanges separate')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and a['oldIntervalTUInstrumentedForHarness'] and a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==1 and not a['oldCoreBuiltOrLinked'],'Explicit4 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_COVERAGE_SPHERE_EVALUATION_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=16,actualDebugAndAllFourSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],reference=a['reference'],sourceFilesChecked=29,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-coverage-sphere-evaluation-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU sphere Evaluation step only. All4 TUs include original Interval for test source construction. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole plane Result/World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-coverage-sphere-evaluation-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
