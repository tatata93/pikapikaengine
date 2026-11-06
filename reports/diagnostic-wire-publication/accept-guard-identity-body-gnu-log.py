"""Accept returned decoded GNU log against exact source340a7a89, independent of later leaf additions."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='340a7a8927140f35dc3178ced616fca6305569fe'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-guard-identity-body-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-guard-identity-body-gnu-diagnostic.base64').read_bytes(),validate=False)
    log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_REPORT_GUARD_IDENTITY_BODY_WIRE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_REPORT_GUARD_IDENTITY_BODY_WIRE={' in line]
    need(len(lines)==1,'Exactly one actual final record');actual=json.loads(lines[0]);write(OUT/'actual-guard-identity-body-verification.json',actual)
    need(actual['status']=='FINITE_GNU_REPORT_GUARD_IDENTITY_BODY_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'],'Actual source stable')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==16 and all(r['exitCode']==0 for r in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(r for r in commands if r['name']==cfg+'-build');args=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        tus=[Path(s).name for s in args if s.endswith('.cpp')]
        need(tus==['diagnostic_wire.cpp','report_values_wire.cpp','report_guard_identity_body_wire_tests.cpp'],'Exactly2 production and1 harness; no Interval TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No numerical library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(r for r in commands if r['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==1934 and fixture['stdoutSha256']=='be582391b51973a6b677f2c4f08ff11fbd541cee6fa7a921428177ab0369ccf1','Actual whole raw fixture')
    native=json.loads((ROOT/'reports/diagnostic-wire-guard-identity-body-verification.json').read_bytes())
    need(actual['native']==native['native'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    need(len(actual['sourceBefore'])==27,'All27 source files without Interval TU or model dependencies')
    need(actual['schemaControls']['accepted']==1 and actual['schemaControls']['refused']==19,'Actual schema controls')
    required=dict(wellFormedSingleByteMutations=740,recordOrderCountRejections=3,absentToNullRejections=2,presentToAbsentOrNullRejections=10,enumToU32Rejections=21,fixedIdentityBytesIndividuallyMutated=455,fixedLengthRejections=14)
    need(all(actual['referenceControls'][k]==v for k,v in required.items()),'Actual guard identity/body mutations')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and not actual['oldIntervalTUInstrumentedForHarness'] and not actual['newHarnessIntervalTU'] and not actual['oldCoreBuiltOrLinked'],'Actual finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_GUARD_IDENTITY_BODY_PASS',source=SOURCE,engineRun=42140594960,job=127639649312,
        compiler=actual['compiler'],target=actual['target'],regularCommands=16,actualDebugAndAllNewSourceO1AsanUbsan=True,newHarnessIntervalTU=False,wholeNativeGnuThreeConfigurationsRawExact=True,
        native=actual['native'],reference=actual['reference'],sourceFilesChecked=len(actual['sourceBefore']),decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-guard-identity-body-verification.json'),
        childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,guardIdentityBodyGnuAccepted=True,
        scope='Completed source340a7a89 GNU guard identity/body step. Decoded log and full final JSON retained; child raw/objects/schema child logs runner-local. Later guard Failure/Call diagnostics and complete Report/pump/JS/WASM/game are outside this receipt.')
    write(ROOT/'reports/diagnostic-wire-guard-identity-body-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
