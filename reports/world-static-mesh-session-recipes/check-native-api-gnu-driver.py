"""Synthetic C-option policy controls and a real Windows platform refusal only."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'run-20261105-native-api-gnu-driver-004'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(sys.platform=='win32' and not OUT.exists(),'Fresh Windows-only driver controls');OUT.mkdir();driver=HERE/'verify-native-api-gnu.py';ast.parse(driver.read_text(encoding='utf8'));spec=importlib.util.spec_from_file_location('api_gnu_controls',driver);m=importlib.util.module_from_spec(spec);sys.dont_write_bytecode=True;spec.loader.exec_module(m)
    protected=[driver,Path(__file__).resolve(),ROOT/'.github/workflows/verify.yml',ROOT/'core/src/world_static_mesh_session_api.cpp',ROOT/'tests/world_static_mesh_session_api_c_tests.c'];before=[stamp(p) for p in protected];write(OUT/'before.json',before)
    base=['/SYNTHETIC-NOT-OBSERVED/gcc','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto','-fexcess-precision=standard','-mfpmath=sse','-msse2','-Wall','-Wextra','-Wpedantic','-Werror','-O1','-DNDEBUG','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer','-c','SYNTHETIC.c'];m.c_command(base,True);negative=[]
    cases=[('missing-c-sanitizer',[v for v in base if v!='-fsanitize=address,undefined']),('missing-ubsan-fatal',[v for v in base if v!='-fno-sanitize-recover=undefined']),('missing-werror',[v for v in base if v!='-Werror']),('missing-rounding',[v for v in base if v!='-frounding-math']),('conflicting-O3',base+['-O3']),('fastmath',base+['-ffast-math']),('x87',base+['-mfpmath=387']),('lto',base+['-flto=auto']),('contract',base+['-ffp-contract=fast']),('excess',base+['-fexcess-precision=fast']),('cxx-standard',base+['-std=c++20']),('force-cxx',base+['-x','c++'])]
    for name,argv in cases:
        try:m.c_command(argv,True)
        except ValueError:negative.append(name);continue
        raise ValueError('Synthetic policy accepted '+name)
    write(OUT/'synthetic-policy-controls.json',dict(scope='Copied compiler-option policy only; no actual GCC invocation or generated object',base=base,rejected=negative,cases=cases))
    refusal=ROOT/'build/public-checks/native-api-gnu-refusal-004';debug=ROOT/'build/wfo-api-refusal-debug-004';san=ROOT/'build/wfo-api-refusal-san-004';need(not any(p.exists() for p in [refusal,debug,san]),'Fresh refusal paths')
    argv=[sys.executable,'-B','-X','utf8',str(driver),'--output',str(refusal),'--debugbuild',str(debug),'--sanbuild',str(san)];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60);(OUT/'refusal.stdout.txt').write_bytes(p.stdout);(OUT/'refusal.stderr.txt').write_bytes(p.stderr);write(OUT/'refusal.command.json',dict(argv=argv,exitCode=p.returncode));r=json.loads((refusal/'verification.json').read_bytes());need(p.returncode==1 and r['status']=='FAIL' and 'Actual Linux GNU13 required' in r['error'] and r['commands']==[] and r['actualGNUExecuted'] is False and r['freshCAndCxxSanitizerConfigured'] is False and r['sourceStable'] and not debug.exists() and not san.exists(),'Actual refusal before build/parent access')
    for file in refusal.iterdir():
        if file.is_file():(OUT/file.name).write_bytes(file.read_bytes())
    text=(ROOT/'.github/workflows/verify.yml').read_text(encoding='utf8');jobs=text.split('\njobs:\n',1)[1];need(len(__import__('re').findall(r'^  [a-z][a-z-]+:$',jobs,__import__('re').M))==6,'Existing six jobs only');need(jobs.count('timeout-minutes: 20')==5 and jobs.count('timeout-minutes: 25')==1 and jobs.count('if: github.event.repository.private == false')==6,'Public guards and budgets unchanged')
    after=[stamp(p) for p in protected];need(before==after,'Driver/source/workflow stable');write(OUT/'after.json',after);write(OUT/'local-verification.json',dict(status='PASS',syntheticPolicyRejections=len(negative),actualWindowsRefusal=True,actualGNUExecuted=False,actualBuildCommands=0,oldBuildsTouched=False,existingSixJobsAndBudgetsUnchanged=True));print(json.dumps(dict(status='PASS',syntheticPolicyRejections=len(negative),actualGNUExecuted=False)))
if __name__=='__main__':main()
