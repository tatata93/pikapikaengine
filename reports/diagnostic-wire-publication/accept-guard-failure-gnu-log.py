"""Accept returned decoded GNU log against exact source69e88fc3, independent of later leaf additions."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='69e88fc326336db7cfa64cffdcd520d88e976880'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-guard-failure-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-guard-failure-gnu-diagnostic.base64').read_bytes(),validate=False)
    log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_REPORT_GUARD_FAILURE_WIRE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_REPORT_GUARD_FAILURE_WIRE={' in line]
    need(len(lines)==1,'Exactly one actual final record');actual=json.loads(lines[0]);write(OUT/'actual-guard-failure-verification.json',actual)
    need(actual['status']=='FINITE_GNU_REPORT_GUARD_FAILURE_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'],'Actual source stable')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==16 and all(r['exitCode']==0 for r in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(r for r in commands if r['name']==cfg+'-build');args=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        tus=[Path(s).name for s in args if s.endswith('.cpp')]
        need(tus==['diagnostic_wire.cpp','report_values_wire.cpp','report_guard_failure_wire_tests.cpp'],'Exactly2 production and1 harness; no Interval TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No numerical library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(r for r in commands if r['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==1415 and fixture['stdoutSha256']=='fb540b0c3084442c9870e83b834738509e1ca93798d9207cbc6f7872bc52bf7f','Actual whole raw fixture')
    native=json.loads((ROOT/'reports/diagnostic-wire-guard-failure-verification.json').read_bytes())
    need(actual['native']==native['native'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    need(len(actual['sourceBefore'])==27,'All27 source files without Interval TU or model dependencies')
    need(actual['schemaControls']['accepted']==1 and actual['schemaControls']['refused']==19,'Actual schema controls')
    required=dict(wellFormedSingleByteMutations=268,recordOrderCountRejections=3,absentToNullRejections=24,presentToAbsentOrNullRejections=48,enumToU32Rejections=12)
    need(all(actual['referenceControls'][k]==v for k,v in required.items()),'Actual source/guard failure locations mutations')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and not actual['oldIntervalTUInstrumentedForHarness'] and not actual['newHarnessIntervalTU'] and not actual['oldCoreBuiltOrLinked'],'Actual finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_GUARD_FAILURE_PASS',source=SOURCE,engineRun=42143593978,job=127649591837,
        compiler=actual['compiler'],target=actual['target'],regularCommands=16,actualDebugAndAllNewSourceO1AsanUbsan=True,newHarnessIntervalTU=False,wholeNativeGnuThreeConfigurationsRawExact=True,
        native=actual['native'],reference=actual['reference'],sourceFilesChecked=len(actual['sourceBefore']),decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-guard-failure-verification.json'),
        childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,guardFailureGnuAccepted=True,
        scope='Completed source69e88fc3 GNU source/guard failure locations step. Decoded log and full final JSON retained; child raw/objects/schema child logs runner-local. Later coverage/Call diagnostics and complete Report/pump/JS/WASM/game are outside this receipt.')
    write(ROOT/'reports/diagnostic-wire-guard-failure-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
