"""Audit actual MSVC probe source/flags/link and preserve web delivery before the next milestone."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-input-valueless-final-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh final probe audit');OUT.mkdir(parents=True)
    native=ROOT/'reports/diagnostic-wire-publication/run-20261106-input-valueless-native-002/verification.json'
    n=json.loads(native.read_bytes());need(n['status']=='FINITE_NATIVE_INPUT_VALUELESS_PROBE_PASS' and n['sourceStable'] and n['actual']['valuelessCases']==4 and n['actual']['retainedCases']==0,'Actual Native four attempts')
    for p,digest in n['sourceBefore'].items():need(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest,'Native tested source unchanged')
    headers=['core/include/pikapika/accelerated_pair_coverage.hpp','core/include/pikapika/accelerated.hpp','core/include/pikapika/core.hpp','core/include/pikapika/interval.hpp']
    for p in headers:need((ROOT/p).read_bytes()==subprocess.check_output(['git','show','b90e0124:'+p],cwd=ROOT),'Complete local include closure agrees with committed parent')
    links=[]
    for cfg in ['Release','Debug']:
        tlog=next((ROOT/'build/wfdip2/binary/probe.dir'/cfg).rglob('CL.command.1.tlog'));raw=tlog.read_bytes();text=raw.decode('utf16')
        for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual '+flag)
        need(bool(re.search(r'/D\s*(?:"NDEBUG"|NDEBUG)',text))==(cfg=='Release'),'Actual Debug/Release NDEBUG split')
        need('COVERAGE_INPUT_VALUELESS_PROBE.CPP' in text.upper(),'Actual probe TU');(OUT/(cfg+'-CL.command.1.tlog.txt')).write_bytes(raw)
        tlog=next((ROOT/'build/wfdip2/binary/probe.dir'/cfg).rglob('link.command.1.tlog'));raw=tlog.read_bytes();text=raw.decode('utf16').upper()
        inputs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text);actual=[s.strip('"').replace('\\','/').split('/')[-1] for s in inputs]
        windows=['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB']
        need(sorted(actual)==sorted(windows),'Only Windows system libraries; no product library');(OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(raw);links.append(dict(configuration=cfg,inputLibraries=actual))
    p=subprocess.run(['git','diff','--exit-code','b90e0124','--','core','engine','samples','assets','platform','cmake','CMakeLists.txt'],cwd=ROOT,capture_output=True);need(p.returncode==0,'Tracked product and main build unchanged')
    ast.parse((ROOT/'reports/diagnostic-wire-publication/verify-input-valueless-gnu.py').read_text(encoding='utf8'))
    (OUT/'probe.cpp.tested.txt').write_bytes((ROOT/'tests/coverage_input_valueless_probe.cpp').read_bytes())
    p=subprocess.run(['npm.cmd','run','build'],cwd=ROOT,capture_output=True);(OUT/'web-build.stdout.txt').write_bytes(p.stdout);(OUT/'web-build.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Required milestone web build')
    result=dict(status='FINITE_NATIVE_INPUT_VALUELESS_PROBE_FINAL_PASS',nativeReceipt=stamp(native),actual=n['actual'],completeHeaderClosureExactGit=True,
        linkAudit=links,testedSourceSnapshot=stamp(OUT/'probe.cpp.tested.txt'),trackedProductAndMainBuildUnchanged=True,gnuRecipeSyntaxParsed=True,gnuExecuted=False,
        inputGetterImplemented=False,mappedRecordTypes=62,mappedFields=369,allPossibleOperationsTested=False,webBuildExitCode=0,
        scope='Four actual MSVC throwing conversion attempts in both configurations; no all-operation or GNU outcome claim. Old interval header is a declaration dependency, no interval.cpp or model library compiled/linked.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
