"""Fresh GNU advance CommitWork/CommitStorage diagnostics; exactly2 data TUs and1 harness; no Interval TU; no numerical model library."""
from pathlib import Path
import importlib.util,types
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def main():
    need(__debug__ and sys.platform=='linux','Real Linux required; no commands before host gate')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    out=args.output.resolve();need(out.is_relative_to(ROOT/'build') and not out.exists(),'Fresh bounded build output');out.mkdir(parents=True)
    commands=[];sources=[ROOT/p for p in ['core/include/pikapika/report_values_wire.hpp', 'core/src/report_values_wire.cpp', 'tests/report_advance_commit_ledgers_wire_tests.cpp', 'scripts/verify-report-advance-commit-ledgers-wire.py', 'reports/diagnostic-wire-recipes/verify-advance-commit-ledgers-gnu.py', 'core/include/pikapika/diagnostic_wire.hpp', 'core/src/diagnostic_wire.cpp', 'tests/report_advance_commit_ledgers_wire_reference_tests.py', 'tests/report_values_schema_tests.py', 'cmake/ReportValuesSchema.cmake', 'core/report-values-schema-v1.json', 'scripts/verify-diagnostic-wire.py']]
    def stamps():return [dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources]
    for row in json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes())['headers']:
        header=ROOT/row['path']
        if header not in sources:sources.append(header)
    before=stamps();write(out/'before.json',before)
    def run(name,argv,san=False,binary=False):
        env=os.environ.copy()
        if san:env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,env=env,timeout=180)
        (out/(name+('.stdout.hex.txt' if binary else '.stdout.txt'))).write_bytes((p.stdout.hex()+'\n').encode() if binary else p.stdout);(out/(name+'.stderr.txt')).write_bytes(p.stderr)
        r=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start,sanitizerRuntimeOptions=san,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest());commands.append(r);write(out/(name+'.command.json'),r)
        if p.returncode:print(p.stdout.decode(errors='replace')[-4000:]);print(p.stderr.decode(errors='replace')[-4000:])
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        spec=importlib.util.spec_from_file_location('actual_source_oracle',ROOT/'scripts/verify-report-advance-commit-ledgers-wire.py')
        oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
        required=set();seen=set()
        def visit(module):
            if id(module) in seen:return
            seen.add(id(module));file=getattr(module,'__file__',None)
            if not file:return
            path=Path(file).resolve()
            if not path.is_relative_to(ROOT/'scripts'):return
            required.add(path)
            for value in vars(module).values():
                if isinstance(value,types.ModuleType):visit(value)
        visit(oracle)
        need(required=={ROOT/p for p in ['scripts/verify-diagnostic-wire.py', 'scripts/verify-report-advance-commit-ledgers-wire.py']},'Exact actual2-oracle closure')
        need(required.issubset({p.resolve() for p in sources}),'Actual imported oracle modules must all be captured')
        result['oracleSourceClosure']=dict(status='PASS',required=sorted(p.relative_to(ROOT).as_posix() for p in required))
        version=run('compiler',['g++','-dumpfullversion']).decode().strip();need(version.startswith('13.'),'Actual GNU13 required')
        target=run('target',['g++','-dumpmachine']).decode().strip();need(target=='x86_64-linux-gnu','Actual target')
        schema=json.loads(run('schema-controls',[sys.executable,'-B',ROOT/'tests/report_values_schema_tests.py','--output',out/'schema-controls','--build',out/'schema-copies']));need(schema['accepted']==1 and schema['refused']==len(json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes())['headers'])+3 and schema['sourceStable'],'Actual CMake source gate controls')
        captures=[];checks=[]
        for name,options in [('Release',['-O2','-DNDEBUG']),('Debug',['-O0','-g']),('Sanitized',['-O1','-g','-DNDEBUG','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer'])]:
            binary=out/name
            run(name+'-build',['g++','-std=c++20','-Wall','-Wextra','-Wpedantic','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto',*options,'-Icore/include',sources[6],sources[1],sources[2],'-o',binary])
            checks.append(json.loads(run(name+'-run',[binary,'--run'],name=='Sanitized')))
            captures.append(run(name+'-fixture',[binary,'--fixture'],name=='Sanitized',True))
            check=json.loads(run(name+'-reference',[sys.executable,'-B',ROOT/'scripts/verify-report-advance-commit-ledgers-wire.py',out/(name+'-fixture.stdout.hex.txt'),'--hex']));need(check['status']=='PASS','Actual independent decoder')
        native_receipt=json.loads((ROOT/'reports/diagnostic-wire-advance-commit-ledgers-verification.json').read_bytes());native_dir=(ROOT/native_receipt['nativeReceipt']['path']).parent
        native=bytes.fromhex((native_dir/'Release-fixture.stdout.hex.txt').read_text())
        need(all(b==native for b in captures) and checks[0]==checks[1]==checks[2],'Whole raw Native/GNU normal/Debug/SAN exact')
        control=json.loads(run('reference-controls',[sys.executable,'-B',ROOT/'tests/report_advance_commit_ledgers_wire_reference_tests.py',out/'Release-fixture.stdout.hex.txt','--hex']))
        expected={'wellFormedSingleByteMutations': 8848, 'recordOrderCountRejections': 3, 'absentToNullRejections': 0, 'presentToAbsentOrNullRejections': 0, 'enumToU32Rejections': 0, 'fieldValueExchangeRejections': 1664, 'objectFieldOrderRejections': 32, 'arrayOrderCountRejections': 0, 'variantOrdinalByteMutations': 0, 'variantToPresentRejections': 0, 'variantWrapperRemovalRejections': 0, 'variantChildExchangeRejections': 0, 'variantChildPairsConsidered': 0, 'disjointVariantChildPairs': 0, 'nestedVariantChildPairs': 0, 'nestedVariantChildReplacementRejections': 0, 'messageLengthRejections': 0, 'identicalFieldExchanges': 112, 'identicalArrayOrders': 0, 'identicalVariantChildExchanges': 0}
        need(control['status']=='PASS' and control['shards']==1 and control['shard']==0 and control['controlsConsidered']==control['controlsDecoded']==10547 and control['baseline']==check and all(control[k]==v for k,v in expected.items()),'All10547 differing full-document controls and112 identical exchanges separated')
        controls={k:v for k,v in control.items() if k!='mutations'}
        result.update(status='FINITE_GNU_REPORT_ADVANCE_COMMIT_LEDGERS_PASS',compiler=version,target=target,native=checks[0],reference=check,schemaControls=schema,referenceControls={k:v for k,v in controls.items() if k!='mutations'},wholeRawExact=True,allNewTranslationUnitsInstrumented=True,newProductionTUs=2,newHarnessTUs=1,oldCoreBuiltOrLinked=False,oldIntervalTUInstrumentedForHarness=False,newHarnessIntervalTU=False,testOnlyIntervalTUs=0,fullReportMapped=False,CABIPumpImplemented=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    after=stamps();result.update(commands=commands,sourceStable=before==after,sourceBefore=before,sourceAfter=after)
    if before!=after:result['status']='FAIL'
    write(out/'verification.json',result);print('PIKAPIKA_REPORT_ADVANCE_COMMIT_LEDGERS_WIRE='+json.dumps(result,allow_nan=False));return int(result['status']!='FINITE_GNU_REPORT_ADVANCE_COMMIT_LEDGERS_PASS')
if __name__=='__main__':raise SystemExit(main())
