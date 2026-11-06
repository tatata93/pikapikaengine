"""Accept the returned actual GNU rejection log against exact feature b90e0124."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='b90e0124b95305c05c3cf8cec390f564f8893802'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-rejection-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh actual acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/rejection-gnu-diagnostic.base64').read_bytes(),validate=False)
    log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_DIAGNOSTIC_REJECTION=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_DIAGNOSTIC_REJECTION={' in line]
    need(len(lines)==1,'Exactly one actual rejection record');actual=json.loads(lines[0]);write(OUT/'actual-rejection-verification.json',actual)
    need(actual['status']=='FINITE_GNU_DIAGNOSTIC_REJECTION_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU result')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'] and len(actual['sourceBefore'])==5,'All5 actual immutable sources')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
        need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob '+row['path'])
    commands=actual['commands'];need(len(commands)==14 and all(r['exitCode']==0 for r in commands),'All14 actual commands')
    for cfg in ['Release','Debug','Sanitized']:
        args=next(r for r in commands if r['name']==cfg+'-build')['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        need([Path(s).name for s in args if s.endswith('.cpp')]==['diagnostic_wire.cpp','diagnostic_wire_rejection_tests.cpp'],'Only1 primitive production and1 harness TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No model or getter library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All new source instrumented')
        fixture=next(r for r in commands if r['name']==cfg+'-fixture')
        need(fixture['stdoutBytes']==827 and fixture['stdoutSha256']=='61e08b17d1a6407d53ed83d42f2340ea8e2a2a3730d9fd202e66b14dffdbddba','Actual whole control document')
        if cfg=='Sanitized':
            for suffix in ['run','fixture']:need(next(r for r in commands if r['name']==cfg+'-'+suffix)['sanitizerRuntimeOptions'],'Actual sanitizer runtime')
    native=json.loads((ROOT/'reports/diagnostic-wire-rejection-verification.json').read_bytes())
    need(actual['native']==native['native'] and actual['reference']==native['reference'],'Exact Native assertions/reference')
    need(actual['wholeRawExact'] and actual['allNewTranslationUnitsInstrumented'] and not actual['oldCoreBuiltOrLinked'],'Finite scope')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_DIAGNOSTIC_REJECTION_PASS',source=SOURCE,engineRun=42152200205,job=127677842307,compiler=actual['compiler'],target=actual['target'],
        actualDebugAndAllNewSourceO1AsanUbsan=True,regularCommands=14,sourceFilesChecked=5,newProductionTUs=1,newHarnessTUs=1,
        wholeControlNativeGnuThreeConfigurationsRawExact=True,explicitRejectionBytes=0,explicitRejectionCallbacks=0,native=actual['native'],reference=actual['reference'],
        decodedLog=stamp(log),actualRecord=stamp(OUT/'actual-rejection-verification.json'),childRawAndObjectsTransferred=False,inputVariantMapped=False,fullReportMapped=False,CABIPumpImplemented=False,
        scope='Actual GNU explicit rejection step; control827 bytes differs from rejection0 bytes. Child raw/objects remain runner-local. No Input valueless reachability or getter, rollback, numeric model, WASM/game proof.')
    write(ROOT/'reports/diagnostic-wire-rejection-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog']}))
if __name__=='__main__':main()
