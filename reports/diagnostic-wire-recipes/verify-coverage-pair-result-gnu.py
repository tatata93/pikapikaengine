"""Fresh GNU complete pair Result diagnostics; exactly2 data TUs,1 harness and1 test-only original Interval TU; no physics-model libraries."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def main():
    need(__debug__ and sys.platform=='linux','Real Linux required; no commands before host gate')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    out=args.output.resolve();need(out.is_relative_to(ROOT/'build') and not out.exists(),'Fresh bounded build output');out.mkdir(parents=True)
    commands=[];sources=[ROOT/p for p in ['core/include/pikapika/report_values_wire.hpp','core/src/report_values_wire.cpp','tests/report_coverage_pair_result_wire_tests.cpp','scripts/verify-report-coverage-pair-result-wire.py',Path(__file__).relative_to(ROOT).as_posix(),'core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp','scripts/verify-diagnostic-wire.py','tests/report_coverage_pair_result_wire_reference_tests.py','tests/report_values_schema_tests.py','cmake/ReportValuesSchema.cmake','core/report-values-schema-v1.json','core/src/interval.cpp','tests/report_coverage_pair_result_wire_sources.hpp','scripts/verify-report-coverage-snapshot-wire.py','scripts/verify-report-coverage-audit-partition-wire.py','scripts/verify-report-coverage-cell-work-wire.py']]
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
        version=run('compiler',['g++','-dumpfullversion']).decode().strip();need(version.startswith('13.'),'Actual GNU13 required')
        target=run('target',['g++','-dumpmachine']).decode().strip();need(target=='x86_64-linux-gnu','Actual target')
        schema=json.loads(run('schema-controls',[sys.executable,'-B',ROOT/'tests/report_values_schema_tests.py','--output',out/'schema-controls','--build',out/'schema-copies']));need(schema['accepted']==1 and schema['refused']==len(json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes())['headers'])+3 and schema['sourceStable'],'Actual CMake source gate controls')
        captures=[];checks=[]
        for name,options in [('Release',['-O2','-DNDEBUG']),('Debug',['-O0','-g']),('Sanitized',['-O1','-g','-DNDEBUG','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer'])]:
            binary=out/name
            run(name+'-build',['g++','-std=c++20','-Wall','-Wextra','-Wpedantic','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto',*options,'-Icore/include',sources[6],sources[1],sources[2],ROOT/'core/src/interval.cpp','-o',binary])
            checks.append(json.loads(run(name+'-run',[binary,'--run'],name=='Sanitized')))
            captures.append(run(name+'-fixture',[binary,'--fixture'],name=='Sanitized',True))
            check=json.loads(run(name+'-reference',[sys.executable,'-B',ROOT/'scripts/verify-report-coverage-pair-result-wire.py',out/(name+'-fixture.stdout.hex.txt'),'--hex']));need(check['status']=='PASS','Actual independent decoder')
        native=bytes.fromhex((ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-pair-result-native-002/Release-fixture.stdout.hex.txt').read_text())
        need(all(b==native for b in captures) and checks[0]==checks[1]==checks[2],'Whole raw Native/GNU normal/Debug/SAN exact; target-specific reachability is kept separate')
        controls=json.loads(run('reference-controls',[sys.executable,'-B',ROOT/'tests/report_coverage_pair_result_wire_reference_tests.py',out/'Release-fixture.stdout.hex.txt','--hex']));need(all(controls[k]==v for k,v in {'wellFormedSingleByteMutations': 16856, 'recordOrderCountRejections': 3, 'absentToNullRejections': 126, 'presentToAbsentOrNullRejections': 262, 'enumToU32Rejections': 168, 'fieldValueExchangeRejections': 2508, 'objectFieldOrderRejections': 303, 'arrayOrderCountRejections': 523, 'variantOrdinalByteMutations': 32, 'variantToPresentRejections': 8, 'variantWrapperRemovalRejections': 8, 'variantChildExchangeRejections': 24, 'messageLengthRejections': 33, 'identicalFieldExchanges': 53, 'identicalArrayOrders': 3, 'identicalVariantChildExchanges': 4, 'controlsConsidered': 20854, 'controlsDecoded': 20854}.items()),'Actual independent Audit/Partition mutations')
        result.update(status='FINITE_GNU_REPORT_COVERAGE_PAIR_RESULT_PASS',compiler=version,target=target,native=checks[0],reference=check,schemaControls=schema,referenceControls={k:v for k,v in controls.items() if k!='mutations'},wholeRawExact=True,allNewTranslationUnitsInstrumented=True,newProductionTUs=2,newHarnessTUs=1,oldCoreBuiltOrLinked=False,oldIntervalTUInstrumentedForHarness=True,newHarnessIntervalTU=True,testOnlyIntervalTUs=1,fullReportMapped=False,CABIPumpImplemented=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    after=stamps();result.update(commands=commands,sourceStable=before==after,sourceBefore=before,sourceAfter=after)
    if before!=after:result['status']='FAIL'
    write(out/'verification.json',result);print('PIKAPIKA_REPORT_COVERAGE_PAIR_RESULT_WIRE='+json.dumps(result,allow_nan=False));return int(result['status']!='FINITE_GNU_REPORT_COVERAGE_PAIR_RESULT_PASS')
if __name__=='__main__':raise SystemExit(main())
