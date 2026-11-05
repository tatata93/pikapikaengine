"""Accept returned decoded GNU log against exact sourcead72, independent of later leaf additions."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='ad72d7e5a19c9cd281188b323b2b25076b01c055'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-intervals-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/report-intervals-gnu-portable.base64').read_bytes(),validate=False)
    log=OUT/'portable-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_REPORT_INTERVALS_WIRE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_REPORT_INTERVALS_WIRE={' in line]
    need(len(lines)==1,'Exactly one actual final record');actual=json.loads(lines[0]);write(OUT/'actual-intervals-verification.json',actual)
    need(actual['status']=='FINITE_GNU_REPORT_INTERVALS_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'],'Actual source stable')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==16 and all(r['exitCode']==0 for r in commands),'All16 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        build=next(r for r in commands if r['name']==cfg+'-build');args=build['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        tus=[Path(s).name for s in args if s.endswith('.cpp')]
        need(tus==['diagnostic_wire.cpp','report_values_wire.cpp','report_intervals_wire_tests.cpp','interval.cpp'],'Exactly2 production,1 harness and1 old Interval TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No numerical library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        for suffix in ['run','fixture','reference']:
            command=next(r for r in commands if r['name']==cfg+'-'+suffix)
            if cfg=='Sanitized' and suffix in ['run','fixture']:need(command['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==1037 and fixture['stdoutSha256']=='d064ab959e8187b4ec8e819ddeb18e5b8afb286d58acaa9247ed23e414264828','Actual whole raw fixture')
    native=json.loads((ROOT/'reports/diagnostic-wire-intervals-verification.json').read_bytes())
    need(actual['native']==native['native'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    need(actual['schemaControls']['accepted']==1 and actual['schemaControls']['refused']==19 and actual['referenceControls']['wellFormedSingleByteMutations']==81 and actual['referenceControls']['recordOrderCountRejections']==3,'Actual schema and mutation controls')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and actual['oldIntervalTUInstrumentedForHarness'] and not actual['oldCoreBuiltOrLinked'],'Actual finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_INTERVALS_PASS',source=SOURCE,engineRun=42084630642,job=127446315357,
        compiler=actual['compiler'],target=actual['target'],regularCommands=16,actualDebugAndAllNewSourceO1AsanUbsan=True,oldIntervalTUAlsoO1AsanUbsan=True,wholeNativeGnuThreeConfigurationsRawExact=True,
        native=actual['native'],reference=actual['reference'],sourceFilesChecked=len(actual['sourceBefore']),decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-intervals-verification.json'),
        childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False,newGeometryGnuAccepted=False,
        scope='Completed sourcead72 GNU intervals step. Decoded log and full final JSON retained; child raw/objects/schema child logs runner-local. New CandidateAudit/Geometry structures and complete Report/pump/JS/WASM/game are outside this receipt.')
    write(ROOT/'reports/diagnostic-wire-intervals-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
