"""Accept actual GNU reachability outcomes separately from the MSVC result."""
from pathlib import Path
import base64,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCE='45410f0d460a0dd2e0f3da32a79abccb38e5fb08'
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-input-valueless-gnu-actual-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh GNU acceptance');OUT.mkdir(parents=True)
    raw=base64.b64decode((ROOT/'build/input-valueless-gnu-diagnostic.base64').read_bytes(),validate=False);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw)
    lines=[line.split('PIKAPIKA_INPUT_VALUELESS_PROBE=',1)[1] for line in raw.decode('utf8').splitlines() if 'PIKAPIKA_INPUT_VALUELESS_PROBE={' in line]
    need(len(lines)==1,'Exactly one actual probe record');actual=json.loads(lines[0]);record=OUT/'actual-input-valueless-verification.json';write(record,actual)
    need(actual['status']=='FINITE_GNU_INPUT_VALUELESS_PROBE_PASS' and actual['compiler']=='13.3.0' and actual['target']=='x86_64-linux-gnu','Actual GNU target')
    need(actual['sourceStable'] and actual['sourceBefore']==actual['sourceAfter'] and len(actual['sourceBefore'])==6,'All6 source files')
    for row in actual['sourceBefore']:
        blob=subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT);need(len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Exact feature blob')
    commands=actual['commands'];need(len(commands)==8 and all(r['exitCode']==0 for r in commands),'All8 actual commands')
    outputs=[]
    for cfg in ['Release','Debug','Sanitized']:
        args=next(r for r in commands if r['name']==cfg+'-build')['argv']
        for flag in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(flag in args,'Actual strict flag')
        need([Path(s).name for s in args if s.endswith('.cpp')]==['coverage_input_valueless_probe.cpp'],'Only1 harness TU')
        need(not any(s.endswith(('.a','.so','.lib')) for s in args),'No product/model library')
        if cfg=='Debug':need('-O0' in args and '-g' in args and '-DNDEBUG' not in args,'True Debug')
        if cfg=='Sanitized':
            for flag in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(flag in args,'All source instrumented')
        run=next(r for r in commands if r['name']==cfg+'-run');outputs.append((run['stdoutBytes'],run['stdoutSha256']))
        if cfg=='Sanitized':need(run['sanitizerRuntimeOptions'],'Actual runtime')
    need(outputs[0]==outputs[1]==outputs[2],'Whole GNU run output agrees across actual configurations')
    a=actual['actual'];need(a['attempts']==4 and a['valuelessCases']==0 and a['retainedCases']==4 and all(c['conversionExceptionCaught'] and not c['valuelessObserved'] and c['oldAlternativeRawBitsRetained'] for c in a['cases']),'Actual GNU retained outcomes, not fabricated valueless execution')
    native=json.loads((ROOT/'reports/diagnostic-wire-input-valueless-native-verification.json').read_bytes());need(native['actual']['valuelessCases']==4 and native['actual']['retainedCases']==0,'Actual distinct MSVC outcomes')
    result=dict(schema=1,status='FINITE_ACTUAL_GNU_INPUT_VALUELESS_PROBE_PASS',source=SOURCE,engineRun=42153389787,job=127681723772,compiler=actual['compiler'],target=actual['target'],regularCommands=8,sourceFilesChecked=6,
        actualDebugAndAllSourceO1AsanUbsan=True,newTranslationUnits=1,gnuActual=a,msvcActual=native['actual'],decodedLog=stamp(log),actualRecord=stamp(record),childRawAndObjectsTransferred=False,
        gnuValuelessBranchExecuted=False,allPossibleOperationsTested=False,inputGetterImplemented=False,
        scope='Actual four throwing-conversion attempts: GNU retained4/valueless0, MSVC retained0/valueless4. Different allowed outcomes accepted separately. No fake private bytes, Input getter, full Report/pump/WASM/game proof.')
    write(ROOT/'reports/diagnostic-wire-input-valueless-gnu-verification.json',result);print(json.dumps({k:result[k] for k in ['status','sourceFilesChecked','decodedLog','gnuValuelessBranchExecuted']}))
if __name__=='__main__':main()
