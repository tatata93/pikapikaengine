"""Accept returned decoded GNU log against exact source215d799d, independent of later leaf additions."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='215d799d8f63899bb08ee6fa4deb7f3ae9f368cb'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-coverage-snapshot-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-coverage-snapshot-gnu-diagnostic.base64').read_bytes(),validate=False)
    log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_REPORT_COVERAGE_SNAPSHOT_WIRE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_REPORT_COVERAGE_SNAPSHOT_WIRE={' in line]
    need(len(lines)==1,'Exactly one actual final record');actual=json.loads(lines[0]);write(OUT/'actual-coverage-snapshot-verification.json',actual)
    need(actual['status']=='FINITE_GNU_REPORT_COVERAGE_SNAPSHOT_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'],'Actual source stable')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==16 and all(r['exitCode']==0 for r in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(r for r in commands if r['name']==cfg+'-build');args=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        tus=[Path(s).name for s in args if s.endswith('.cpp')]
        need(tus==['diagnostic_wire.cpp','report_values_wire.cpp','report_coverage_snapshot_wire_tests.cpp'],'Exactly2 production and1 harness; no Interval TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No numerical library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(r for r in commands if r['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==10367 and fixture['stdoutSha256']=='3548919dce2d19454f634d6c555dbe43d19884fecd9a12981b2489a5a4a8a2b0','Actual whole raw fixture')
    native=json.loads((ROOT/'reports/diagnostic-wire-coverage-snapshot-verification.json').read_bytes())
    need(actual['native']['common']==native['native']['common'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    reach=actual['native']['reachability'];common=actual['native']['common']
    need(reach['attempts']==4 and reach['valuelessCases']+reach['retainedCases']==4 and not reach['privateBytesModified'],'Actual per-target reachability')
    need(reach['snapshotRejectionPhaseCases']==6*reach['valuelessCases'] and reach['exactPartialPrefixCases']==4*reach['valuelessCases'] and reach['existingStickyFailureCases']==5*reach['valuelessCases'] and reach['valuelessReentryRefusals']==common['callbackBoundaries']*reach['valuelessCases'],'Only actually reached empty branches count')
    need(len(actual['sourceBefore'])==28,'All28 source files with17 reviewed headers; without Interval TU or model dependencies')
    need(actual['schemaControls']['accepted']==1 and actual['schemaControls']['refused']==20,'Actual schema controls')
    required=dict(wellFormedSingleByteMutations=5120,namedInputOrderRejections=16,variantOrdinalByteMutations=64,variantToPresentRejections=16,variantWrapperRemovalRejections=16,variantChildSwapRejections=16,snapshotFieldSwapRejections=48,horizonToleranceSwapRejections=16,settingsCountSwapRejections=16,recordOrderCountRejections=3,absentToNullRejections=0,presentToAbsentOrNullRejections=0,enumToU32Rejections=0)
    need(all(actual['referenceControls'][k]==v for k,v in required.items()),'Actual Snapshot boundary mutations')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and not actual['oldIntervalTUInstrumentedForHarness'] and not actual['newHarnessIntervalTU'] and not actual['oldCoreBuiltOrLinked'],'Actual finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_COVERAGE_SNAPSHOT_PASS',source=SOURCE,engineRun=42158750423,job=127699077012,
        compiler=actual['compiler'],target=actual['target'],regularCommands=16,actualDebugAndAllNewSourceO1AsanUbsan=True,newHarnessIntervalTU=False,wholeNativeGnuThreeConfigurationsRawExact=True,
        native=actual['native'],reference=actual['reference'],sourceFilesChecked=len(actual['sourceBefore']),decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-coverage-snapshot-verification.json'),
        childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,coverageSnapshotGnuAccepted=True,inputVariantMapped=True,
        scope='Completed source215d799d GNU Snapshot boundary step. Decoded log and full final JSON retained; child raw/objects/schema child logs runner-local. Later Cell/Work/Call diagnostics and complete Report/pump/JS/WASM/game are outside this receipt.')
    write(ROOT/'reports/diagnostic-wire-coverage-snapshot-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
