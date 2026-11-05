"""Accept returned decoded GNU log against exact source95a76c5f, independent of later leaf additions."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='95a76c5f9ea4c1eb89da77db805e90186a449a64'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-held-result-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-held-result-gnu-portable.base64').read_bytes(),validate=False)
    log=OUT/'portable-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_REPORT_HELD_RESULT_WIRE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_REPORT_HELD_RESULT_WIRE={' in line]
    need(len(lines)==1,'Exactly one actual final record');actual=json.loads(lines[0]);write(OUT/'actual-held-result-verification.json',actual)
    need(actual['status']=='FINITE_GNU_REPORT_HELD_RESULT_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'],'Actual source stable')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==16 and all(r['exitCode']==0 for r in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(r for r in commands if r['name']==cfg+'-build');args=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        tus=[Path(s).name for s in args if s.endswith('.cpp')]
        need(tus==['diagnostic_wire.cpp','report_values_wire.cpp','report_held_result_wire_tests.cpp','interval.cpp'],'Exactly2 production,1 harness and old Interval TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No numerical library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(r for r in commands if r['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==33080 and fixture['stdoutSha256']=='6247e947524823304c2fa0c7338c823a4d612902b9fd280be613416fedf16d41','Actual whole raw fixture')
    native=json.loads((ROOT/'reports/diagnostic-wire-held-result-verification.json').read_bytes())
    need(actual['native']==native['native'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    need(len(actual['sourceBefore'])==32,'All32 source files including4 independent oracle dependencies')
    need(actual['schemaControls']['accepted']==1 and actual['schemaControls']['refused']==19,'Actual schema controls')
    required=dict(wellFormedSingleByteMutations=8569,recordOrderCountRejections=3,outerPresencePairCombinations=312,allArrayOrderCountRejections=180,absentToNullRejections=212,presentToAbsentOrNullRejections=112,enumToU32Rejections=58,messageBytesIndividuallyMutated=1808)
    need(all(actual['referenceControls'][k]==v for k,v in required.items()),'Actual full held Result mutations')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and actual['oldIntervalTUInstrumentedForHarness'] and actual['newHarnessIntervalTU'] and not actual['oldCoreBuiltOrLinked'],'Actual finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_HELD_RESULT_PASS',source=SOURCE,engineRun=42126073035,job=127590509114,
        compiler=actual['compiler'],target=actual['target'],regularCommands=16,actualDebugAndAllNewSourceO1AsanUbsan=True,newHarnessIntervalTU=True,wholeNativeGnuThreeConfigurationsRawExact=True,
        native=actual['native'],reference=actual['reference'],sourceFilesChecked=len(actual['sourceBefore']),decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-held-result-verification.json'),
        childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,heldResultGnuAccepted=True,
        scope='Completed source95a76c5f GNU complete held Result step. Decoded log and full final JSON retained; child raw/objects/schema child logs runner-local. Later free flight diagnostics and complete Report/pump/JS/WASM/game are outside this receipt.')
    write(ROOT/'reports/diagnostic-wire-held-result-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
