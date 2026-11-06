"""Measure four legitimate Input emplace failures on real GNU; accept retained and valueless separately."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
def main():
    need(__debug__ and sys.platform=='linux','Actual Linux required')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve();need(out.is_relative_to(ROOT/'build') and not out.exists(),'Fresh bounded output');out.mkdir(parents=True)
    sources=['tests/coverage_input_valueless_probe.cpp','core/include/pikapika/accelerated_pair_coverage.hpp','core/include/pikapika/accelerated.hpp','core/include/pikapika/core.hpp','core/include/pikapika/interval.hpp',Path(__file__).relative_to(ROOT).as_posix()]
    def stamps():return [dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in sources]
    before=stamps();commands=[]
    def run(name,args,san=False):
        env=os.environ.copy()
        if san:env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,env=env,timeout=120)
        (out/(name+'.stdout.txt')).write_bytes(p.stdout);(out/(name+'.stderr.txt')).write_bytes(p.stderr)
        row=dict(name=name,argv=list(map(str,args)),exitCode=p.returncode,seconds=time.monotonic()-start,sanitizerRuntimeOptions=san,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest());commands.append(row);write(out/(name+'.command.json'),row)
        if p.returncode:print(p.stdout.decode(errors='replace')[-2000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(status='FAIL',scope=__doc__)
    try:
        compiler=run('compiler',['g++','-dumpfullversion']).decode().strip();target=run('target',['g++','-dumpmachine']).decode().strip();need(compiler.startswith('13.') and target=='x86_64-linux-gnu','Actual GNU13 x64')
        checks=[]
        for cfg,flags in [('Release',['-O2','-DNDEBUG']),('Debug',['-O0','-g']),('Sanitized',['-O1','-g','-DNDEBUG','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer'])]:
            binary=out/cfg
            run(cfg+'-build',['g++','-std=c++20','-Wall','-Wextra','-Wpedantic','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto',*flags,'-Icore/include',ROOT/sources[0],'-o',binary])
            checks.append(json.loads(run(cfg+'-run',[binary],cfg=='Sanitized')))
        need(checks[0]==checks[1]==checks[2] and checks[0]['status']=='PASS' and checks[0]['attempts']==4,'All actual GNU configurations agree')
        need(checks[0]['valuelessCases']+checks[0]['retainedCases']==4,'Report both outcomes separately')
        result.update(status='FINITE_GNU_INPUT_VALUELESS_PROBE_PASS',compiler=compiler,target=target,actual=checks[0],newTranslationUnits=1,allNewTranslationUnitsInstrumented=True,modelLibraryLinked=False,allPossibleOperationsTested=False,inputGetterImplemented=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    after=stamps();result.update(commands=commands,sourceBefore=before,sourceAfter=after,sourceStable=before==after)
    if before!=after:result['status']='FAIL'
    write(out/'verification.json',result);print('PIKAPIKA_INPUT_VALUELESS_PROBE='+json.dumps(result));return int(result['status']!='FINITE_GNU_INPUT_VALUELESS_PROBE_PASS')
if __name__=='__main__':raise SystemExit(main())
