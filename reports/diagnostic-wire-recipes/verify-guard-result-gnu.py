"""Fresh GNU full GuardResult diagnostics; exactly2 data TUs,1 harness,1 test-only Interval TU; no numerical model library."""
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
    commands=[];sources=[ROOT/p for p in ['core/include/pikapika/report_values_wire.hpp', 'core/src/report_values_wire.cpp', 'tests/report_guard_result_wire_tests.cpp', 'scripts/verify-report-guard-result-wire.py', 'reports/diagnostic-wire-recipes/verify-guard-result-gnu.py', 'core/include/pikapika/diagnostic_wire.hpp', 'core/src/diagnostic_wire.cpp', 'scripts/verify-diagnostic-wire.py', 'tests/report_guard_result_wire_reference_tests.py', 'tests/report_values_schema_tests.py', 'cmake/ReportValuesSchema.cmake', 'core/report-values-schema-v1.json', 'scripts/verify-report-values-wire.py', 'scripts/verify-report-preparation-pair-values-wire.py','scripts/verify-report-preparation-snapshot-inventory-wire.py','scripts/verify-report-guard-failure-wire.py', 'scripts/verify-report-coverage-audit-partition-wire.py', 'scripts/verify-report-coverage-cell-work-wire.py', 'scripts/verify-report-coverage-pair-result-wire.py', 'scripts/verify-report-coverage-plane-audit-partition-wire.py', 'scripts/verify-report-coverage-plane-cell-work-wire.py', 'scripts/verify-report-coverage-plane-result-wire.py', 'scripts/verify-report-coverage-plane-source-snapshot-wire.py', 'scripts/verify-report-coverage-snapshot-wire.py', 'scripts/verify-report-coverage-sphere-audit-partition-wire.py', 'scripts/verify-report-coverage-sphere-cell-work-wire.py', 'scripts/verify-report-coverage-sphere-result-wire.py', 'scripts/verify-report-coverage-sphere-source-snapshot-wire.py', 'scripts/verify-report-flight-endpoint-wire.py', 'scripts/verify-report-flight-result-wire.py', 'scripts/verify-report-flight-source-tube-wire.py', 'scripts/verify-report-guard-child-variant-wire.py', 'scripts/verify-report-guard-identity-body-wire.py', 'scripts/verify-report-guard-mesh-call-wire.py', 'scripts/verify-report-guard-pair-record-wire.py', 'scripts/verify-report-guard-plane-box-call-wire.py', 'scripts/verify-report-guard-plane-calls-wire.py', 'scripts/verify-report-guard-plane-metric-call-wire.py', 'scripts/verify-report-guard-sphere-box-call-wire.py', 'scripts/verify-report-held-snapshot-work-wire.py', 'scripts/verify-report-ledgers-wire.py', 'scripts/verify-report-preparation-result-wire.py', 'scripts/verify-report-settings-wire.py', 'scripts/verify-report-work-wire.py', 'tests/diagnostic_wire_subtree_control_support.py', 'core/src/interval.cpp']]
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
        spec=importlib.util.spec_from_file_location('actual_source_oracle',ROOT/'scripts/verify-report-guard-result-wire.py')
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
        need(required=={ROOT/p for p in ['scripts/verify-diagnostic-wire.py', 'scripts/verify-report-coverage-audit-partition-wire.py', 'scripts/verify-report-coverage-cell-work-wire.py', 'scripts/verify-report-coverage-pair-result-wire.py', 'scripts/verify-report-coverage-plane-audit-partition-wire.py', 'scripts/verify-report-coverage-plane-cell-work-wire.py', 'scripts/verify-report-coverage-plane-result-wire.py', 'scripts/verify-report-coverage-plane-source-snapshot-wire.py', 'scripts/verify-report-coverage-snapshot-wire.py', 'scripts/verify-report-coverage-sphere-audit-partition-wire.py', 'scripts/verify-report-coverage-sphere-cell-work-wire.py', 'scripts/verify-report-coverage-sphere-result-wire.py', 'scripts/verify-report-coverage-sphere-source-snapshot-wire.py', 'scripts/verify-report-flight-endpoint-wire.py', 'scripts/verify-report-flight-result-wire.py', 'scripts/verify-report-flight-source-tube-wire.py', 'scripts/verify-report-guard-child-variant-wire.py', 'scripts/verify-report-guard-failure-wire.py', 'scripts/verify-report-guard-identity-body-wire.py', 'scripts/verify-report-guard-mesh-call-wire.py', 'scripts/verify-report-guard-pair-record-wire.py', 'scripts/verify-report-guard-plane-box-call-wire.py', 'scripts/verify-report-guard-plane-calls-wire.py', 'scripts/verify-report-guard-plane-metric-call-wire.py', 'scripts/verify-report-guard-result-wire.py', 'scripts/verify-report-guard-sphere-box-call-wire.py', 'scripts/verify-report-held-snapshot-work-wire.py', 'scripts/verify-report-ledgers-wire.py', 'scripts/verify-report-preparation-pair-values-wire.py', 'scripts/verify-report-preparation-result-wire.py', 'scripts/verify-report-preparation-snapshot-inventory-wire.py', 'scripts/verify-report-settings-wire.py', 'scripts/verify-report-values-wire.py', 'scripts/verify-report-work-wire.py']},'Exact actual34-oracle closure')
        need(required.issubset({p.resolve() for p in sources}),'Actual imported oracle modules must all be captured')
        result['oracleSourceClosure']=dict(status='PASS',required=sorted(p.relative_to(ROOT).as_posix() for p in required))
        version=run('compiler',['g++','-dumpfullversion']).decode().strip();need(version.startswith('13.'),'Actual GNU13 required')
        target=run('target',['g++','-dumpmachine']).decode().strip();need(target=='x86_64-linux-gnu','Actual target')
        schema=json.loads(run('schema-controls',[sys.executable,'-B',ROOT/'tests/report_values_schema_tests.py','--output',out/'schema-controls','--build',out/'schema-copies']));need(schema['accepted']==1 and schema['refused']==len(json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes())['headers'])+3 and schema['sourceStable'],'Actual CMake source gate controls')
        captures=[];checks=[];stop_results={}
        for name,options in [('Release',['-O2','-DNDEBUG']),('Debug',['-O0','-g']),('Sanitized',['-O1','-g','-DNDEBUG','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer'])]:
            binary=out/name
            run(name+'-build',['g++','-std=c++20','-Wall','-Wextra','-Wpedantic','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto',*options,'-Icore/include',sources[6],sources[1],sources[2],ROOT/'core/src/interval.cpp','-o',binary])
            checks.append(json.loads(run(name+'-run',[binary,'--run'],name=='Sanitized')))
            stops=[]
            for i in range(16):
                stop=json.loads(run(name+'-stop-'+str(i),[binary,'--stop-shard-'+str(i)],name=='Sanitized'))
                need(stop==dict(status='PASS',shard=i,shards=16,totalCallbackBoundaries=26175,testedCallbackBoundaries=1636 if i<15 else 1635,stopAndExceptionCases=3272 if i<15 else 3270,wholeFixtureBytes=219960,sourceRepeatedRawExact=True),'Every strict stop shard exact')
                stops.append(stop)
            need(sum(v['stopAndExceptionCases'] for v in stops)==52350,'All stop/exception cases executed')
            stop_results[name]=stops

            captures.append(run(name+'-fixture',[binary,'--fixture'],name=='Sanitized',True))
            check=json.loads(run(name+'-reference',[sys.executable,'-B',ROOT/'scripts/verify-report-guard-result-wire.py',out/(name+'-fixture.stdout.hex.txt'),'--hex']));need(check['status']=='PASS','Actual independent decoder')
        native_record=json.loads((ROOT/'reports/diagnostic-wire-guard-result-verification.json').read_bytes());need(native_record['status']=='FINITE_NATIVE_REPORT_GUARD_RESULT_PASS','Actual complete Native first')
        native_directory=(ROOT/native_record['nativeReceipt']['path']).resolve().parent;need(native_directory.is_relative_to(ROOT/'reports/diagnostic-wire-recipes'),'Bounded exact formal Native provenance')
        native=bytes.fromhex((native_directory/'Release-fixture.stdout.hex.txt').read_text())
        need(all(b==native for b in captures) and checks[0]==checks[1]==checks[2],'Whole raw and all GNU assertions across three configurations exact')
        need(checks[0]['common']==native_record['native']['common'],'Native/GNU common assertions exact; legitimate valueless outcomes remain platform-specific')
        shards=[]
        expected={'wellFormedSingleByteMutations': 138586, 'recordOrderCountRejections': 3, 'absentToNullRejections': 289, 'presentToAbsentOrNullRejections': 520, 'enumToU32Rejections': 394, 'fieldValueExchangeRejections': 29092, 'objectFieldOrderRejections': 1544, 'arrayOrderCountRejections': 548, 'variantOrdinalByteMutations': 32, 'variantToPresentRejections': 8, 'variantWrapperRemovalRejections': 8, 'variantChildExchangeRejections': 26, 'variantChildPairsConsidered': 28, 'disjointVariantChildPairs': 27, 'nestedVariantChildPairs': 1, 'nestedVariantChildReplacementRejections': 2, 'messageLengthRejections': 147, 'identicalFieldExchanges': 340, 'identicalArrayOrders': 6, 'identicalVariantChildExchanges': 1}
        inventory={'entries': 138586, 'canonicalBytes': 13260615, 'canonicalSha256': 'ffe82711749f5866bf7a6d7090a0cce221ff486eb9d0e73daa7d7f9c3b39c216'}
        for i in range(4):
            control=json.loads(run('reference-controls-'+str(i),[sys.executable,'-B',ROOT/'tests/report_guard_result_wire_reference_tests.py',out/'Release-fixture.stdout.hex.txt','--hex','--shard',str(i),'--shards','4']))
            need(control['status']=='PASS_SHARD' and control['shard']==i and control['shards']==4 and control['controlsConsidered']==171199 and control['controlsDecoded']==(42800 if i<3 else 42799) and control['baseline']==check,'Actual complete shard')
            need(all(control[k]==v for k,v in expected.items()),'Exact complete finite control inventory')
            need(control['mutationInventory']==inventory and control['comparisonMethod']['outsideScopeWholeBytesCompared'] and control['comparisonMethod']['originalAncestorDepthReproduced'] and not control['comparisonMethod']['mutationsDropped'] and control['comparisonMethod']['wholeDocumentDualComparisons']>0,'Exact full mutation inventory, original context and actual whole dual checks')
            shards.append({k:v for k,v in control.items() if k!='mutations'})
        need(sum(s['controlsDecoded'] for s in shards)==171199,'All four shards complete')
        controls=dict(status='PASS',shards=4,controlsConsidered=171199,controlsDecoded=171199,perShard=shards,**expected)
        result.update(status='FINITE_GNU_REPORT_GUARD_RESULT_PASS',compiler=version,target=target,native=checks[0],reference=check,schemaControls=schema,referenceControls={k:v for k,v in controls.items() if k!='mutations'},mutationInventory=inventory,stopShards=stop_results,all52350StopExceptionCasesPerConfiguration=True,wholeRawExact=True,allNewTranslationUnitsInstrumented=True,newProductionTUs=2,newHarnessTUs=1,oldCoreBuiltOrLinked=False,oldIntervalTUInstrumentedForHarness=True,newHarnessIntervalTU=True,testOnlyIntervalTUs=1,fullReportMapped=False,CABIPumpImplemented=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    after=stamps();result.update(commands=commands,sourceStable=before==after,sourceBefore=before,sourceAfter=after)
    if before!=after:result['status']='FAIL'
    write(out/'verification.json',result);print('PIKAPIKA_REPORT_GUARD_RESULT_WIRE='+json.dumps(result,allow_nan=False));return int(result['status']!='FINITE_GNU_REPORT_GUARD_RESULT_PASS')
if __name__=='__main__':raise SystemExit(main())
