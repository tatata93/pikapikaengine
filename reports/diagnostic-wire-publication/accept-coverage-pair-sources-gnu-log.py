"""Accept returned decoded GNU log against exact source9af02108, independent of later leaf additions."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='9af0210804e59c97fff83191a1137cc862e9a138'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-coverage-pair-sources-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-coverage-pair-sources-gnu-diagnostic.base64').read_bytes(),validate=False)
    log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_REPORT_COVERAGE_PAIR_SOURCES_WIRE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_REPORT_COVERAGE_PAIR_SOURCES_WIRE={' in line]
    need(len(lines)==1,'Exactly one actual final record');actual=json.loads(lines[0]);write(OUT/'actual-coverage-pair-sources-verification.json',actual)
    need(actual['status']=='FINITE_GNU_REPORT_COVERAGE_PAIR_SOURCES_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'],'Actual source stable')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==16 and all(r['exitCode']==0 for r in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(r for r in commands if r['name']==cfg+'-build');args=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        tus=[Path(s).name for s in args if s.endswith('.cpp')]
        need(tus==['diagnostic_wire.cpp','report_values_wire.cpp','report_coverage_pair_sources_wire_tests.cpp'],'Exactly2 production and1 harness; no Interval TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No numerical library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(r for r in commands if r['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==1875 and fixture['stdoutSha256']=='7e6bc331db942fa99532e054da11bdd030bfa82390e259d9f10cdcb8fd64a50b','Actual whole raw fixture')
    native=json.loads((ROOT/'reports/diagnostic-wire-coverage-pair-sources-verification.json').read_bytes())
    need(actual['native']==native['native'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    need(len(actual['sourceBefore'])==28,'All28 source files with17 reviewed headers; without Interval TU or model dependencies')
    need(actual['schemaControls']['accepted']==1 and actual['schemaControls']['refused']==20,'Actual schema controls')
    required=dict(wellFormedSingleByteMutations=640,namedInputOrderRejections=4,recordOrderCountRejections=3,absentToNullRejections=0,presentToAbsentOrNullRejections=0,enumToU32Rejections=0)
    need(all(actual['referenceControls'][k]==v for k,v in required.items()),'Actual original sphere-pair/sphere-plane inputs mutations')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and not actual['oldIntervalTUInstrumentedForHarness'] and not actual['newHarnessIntervalTU'] and not actual['oldCoreBuiltOrLinked'],'Actual finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_COVERAGE_PAIR_SOURCES_PASS',source=SOURCE,engineRun=42150617572,job=1276187501185,
        compiler=actual['compiler'],target=actual['target'],regularCommands=16,actualDebugAndAllNewSourceO1AsanUbsan=True,newHarnessIntervalTU=False,wholeNativeGnuThreeConfigurationsRawExact=True,
        native=actual['native'],reference=actual['reference'],sourceFilesChecked=len(actual['sourceBefore']),decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-coverage-pair-sources-verification.json'),
        childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,coveragePairSourcesGnuAccepted=True,
        scope='Completed source9af02108 GNU original sphere-pair/sphere-plane inputs step. Decoded log and full final JSON retained; child raw/objects/schema child logs runner-local. Later variant/Call diagnostics and complete Report/pump/JS/WASM/game are outside this receipt.')
    write(ROOT/'reports/diagnostic-wire-coverage-pair-sources-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
