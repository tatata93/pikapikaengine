"""Accept real GNU sphere Cell/Work results against explicit exact feature/job provenance."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-coverage-sphere-cell-work-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual GNU acceptance')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--engine-run',required=True,type=int);parser.add_argument('--job',required=True,type=int);args=parser.parse_args()
    need(re.fullmatch('[0-9a-f]{40}',args.source) and args.engine_run>0 and args.job>0,'Explicit exact provenance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-coverage-sphere-cell-work-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    text=raw.decode('utf8');need(args.source in text,'Exact source SHA visible in actual job log')
    lines=[s.split('PIKAPIKA_REPORT_COVERAGE_SPHERE_CELL_WORK_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_COVERAGE_SPHERE_CELL_WORK_WIRE={' in s];need(len(lines)==1,'One actual final record');a=json.loads(lines[0]);write(OUT/'actual-coverage-sphere-cell-work-verification.json',a)
    need(a['status']=='FINITE_GNU_REPORT_COVERAGE_SPHERE_CELL_WORK_PASS' and a['compiler']=='13.3.0' and a['target']=='x86_64-linux-gnu','Actual GNU host and pass')
    need(a['sourceStable'] and a['sourceBefore']==a['sourceAfter'] and len(a['sourceBefore'])==28,'All28 stable source files')
    for row in a['sourceBefore']:
        blob=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=a['commands'];need(len(commands)==16 and all(c['exitCode']==0 for c in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(c for c in commands if c['name']==cfg+'-build');argv=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in argv,'Actual strict flag')
        need([Path(p).name for p in argv if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_coverage_sphere_cell_work_wire_tests.cpp'],'Exactly2 production and1 harness; no Interval TU')
        need(not any(p.endswith(('.lib','.a','.so')) for p in argv),'No numerical model library')
        if cfg=='Debug':need('-O0' in argv and '-g' in argv and '-DNDEBUG' not in argv,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in argv,'All3 source TUs instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(c for c in commands if c['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual runtime sanitizer options')
        fixture=next(c for c in commands if c['name']==cfg+'-fixture');need(fixture['stdoutBytes']==2759 and fixture['stdoutSha256']=='dd2c8420c62bc46aa72a082929d2bcae41c5682d3e1654a5b2151652cce793f5','Actual complete2759 raw bytes')
    native=json.loads((ROOT/'reports/diagnostic-wire-coverage-sphere-cell-work-verification.json').read_bytes());need(a['native']==native['native'] and a['reference']==native['reference'],'All Native assertions and independent reference exact')
    need(a['schemaControls']['accepted']==1 and a['schemaControls']['refused']==20,'Actual17-header schema gate')
    expected={'wellFormedSingleByteMutations': 1880, 'typedPayloadByteMutations': 584, 'recordOrderCountRejections': 3, 'absentToNullRejections': 4, 'presentToAbsentOrNullRejections': 8, 'endpointSwapRejections': 8, 'timeBoundsCountRejections': 16, 'fieldValueExchangeRejections': 176, 'objectFieldOrderRejections': 16, 'identicalFieldExchanges': 16, 'totalDifferingControls': 2111}
    need(all(a['referenceControls'][k]==v for k,v in expected.items()) and a['referenceControls']['status']=='PASS','Actual2111 grammar-valid semantic changes and16 identical field exchanges separate')
    need(a['wholeRawExact'] and a['allNewTranslationUnitsInstrumented'] and not a['oldIntervalTUInstrumentedForHarness'] and not a['newHarnessIntervalTU'] and a['testOnlyIntervalTUs']==0 and not a['oldCoreBuiltOrLinked'],'Explicit3 TU finite scope')
    r=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_COVERAGE_SPHERE_CELL_WORK_PASS',source=args.source,engineRun=args.engine_run,job=args.job,compiler=a['compiler'],target=a['target'],regularCommands=16,actualDebugAndAllThreeSourceO1AsanUbsan=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=0,wholeNativeGnuThreeConfigurationsRawExact=True,native=a['native'],reference=a['reference'],sourceFilesChecked=28,decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-coverage-sphere-cell-work-verification.json'),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,scope='Actual GNU sphere Cell/Work step only. Exactly3 TUs; no Interval source required or linked. Decoded log and full final JSON retained; child raw/object/schema child logs runner-local. Whole plane Result/World Report/pump and JS/WASM/game connection remain separate.')
    write(ROOT/'reports/diagnostic-wire-coverage-sphere-cell-work-gnu-verification.json',r);print(json.dumps({k:r[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
