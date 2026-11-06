"""Fresh selected main CMake Native plane Cell/Work diagnostics acceptance; preserve all old builds."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent/'run-20261106-coverage-plane-cell-work-native-001'
BUILD=ROOT/'build/wfdcpcw2'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    need(__debug__ and sys.platform=='win32' and not OUT.exists() and not BUILD.exists(),'Fresh Native build/receipt')
    OUT.mkdir(parents=True);commands=[]
    paths=[ROOT/p for p in ['CMakeLists.txt','core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp','core/include/pikapika/report_values_wire.hpp','core/src/report_values_wire.cpp','tests/report_coverage_plane_cell_work_wire_tests.cpp','scripts/verify-report-coverage-plane-cell-work-wire.py','cmake/ReportValuesSchema.cmake','core/report-values-schema-v1.json',Path(__file__).relative_to(ROOT).as_posix(),'scripts/verify-diagnostic-wire.py']]
    protected=[ROOT/p for p in subprocess.check_output(['git','ls-files','core','engine','samples','assets','platform','tests'],cwd=ROOT,text=True).splitlines() if p not in {x.relative_to(ROOT).as_posix() for x in paths}]
    before=[stamp(p) for p in paths];old=[stamp(p) for p in protected];write(OUT/'source-before.json',before);write(OUT/'protected-before.json',old)
    (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    def run(name,argv,binary=False):
        start=time.monotonic()
        p=subprocess.Popen(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        timed_out=False
        try:
            stdout,stderr=p.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            timed_out=True
            cleanup=subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15)
            (OUT/(name+'.timeout-cleanup.txt')).write_bytes(cleanup.stdout+cleanup.stderr)
            stdout,stderr=p.communicate(timeout=15)
        p.stdout=stdout;p.stderr=stderr
        (OUT/(name+('.stdout.hex.txt' if binary else '.stdout.txt'))).write_bytes((p.stdout.hex()+'\n').encode() if binary else p.stdout)
        (OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        item=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,seconds=time.monotonic()-start,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest(),stdoutReversibleHex=binary)
        commands.append(item);write(OUT/(name+'.command.json'),item)
        if p.returncode:print(p.stdout.decode(errors='replace')[-4000:]);print(p.stderr.decode(errors='replace')[-2000:])
        need(not timed_out and p.returncode==0,'Actual '+name);return p.stdout
    result=dict(schema=1,status='FAIL',scope=__doc__)
    try:
        run('configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON'])
        captures=[];tests=[];inventories={}
        for cfg in ['Release','Debug']:
            targets=['pikapika_report_coverage_plane_cell_work_wire_tests', 'pikapika_report_values_wire_tests', 'pikapika_report_settings_wire_tests', 'pikapika_report_ledgers_wire_tests', 'pikapika_report_work_wire_tests', 'pikapika_report_intervals_wire_tests', 'pikapika_report_geometry_wire_tests', 'pikapika_report_result_wire_tests', 'pikapika_report_mesh_values_wire_tests', 'pikapika_report_mesh_result_wire_tests', 'pikapika_report_held_source_wire_tests', 'pikapika_report_held_snapshot_work_wire_tests', 'pikapika_report_held_proofs_wire_tests', 'pikapika_report_held_audits_wire_tests', 'pikapika_report_held_result_wire_tests', 'pikapika_report_flight_source_tube_wire_tests', 'pikapika_report_flight_endpoint_wire_tests', 'pikapika_report_flight_result_wire_tests', 'pikapika_report_guard_identity_body_wire_tests', 'pikapika_report_guard_failure_wire_tests', 'pikapika_report_coverage_source_wire_tests', 'pikapika_report_coverage_pair_sources_wire_tests', 'pikapika_diagnostic_wire_tests', 'pikapika_diagnostic_wire_rejection_tests', 'pikapika_report_coverage_input_variant_wire_tests', 'pikapika_report_coverage_snapshot_wire_tests', 'pikapika_report_coverage_cell_work_wire_tests', 'pikapika_report_coverage_audit_partition_wire_tests', 'pikapika_report_coverage_pair_result_wire_tests', 'pikapika_report_coverage_plane_source_snapshot_wire_tests', 'pikapika_report_coverage_plane_evaluation_wire_tests']
            groups=[targets[:1]]+[targets[start:start+4] for start in range(1,len(targets),4)]
            for group,selected in enumerate(groups,1):
                run(cfg+'-build-'+str(group),['cmake','--build',BUILD,'--config',cfg,'--target',*selected,'--parallel','2'])
            test=json.loads(run(cfg+'-run',[BUILD/cfg/'pikapika_report_coverage_plane_cell_work_wire_tests.exe','--run']));need(test['status']=='PASS','Actual Native assertions');tests.append(test)
            run(cfg+'-ctest',['ctest','--test-dir',BUILD,'-C',cfg,'-R','^(diagnostic_wire|diagnostic_wire_rejection|report_(coverage_plane_cell_work|coverage_plane_evaluation|coverage_plane_source_snapshot|coverage_pair_result|coverage_audit_partition|coverage_cell_work|coverage_snapshot|coverage_input_variant|coverage_pair_sources|coverage_source|guard_failure|guard_identity_body|flight_result|flight_endpoint|flight_source_tube|held_result|held_audits|held_proofs|held_snapshot_work|held_source|mesh_result|mesh_values|result|geometry|intervals|work|ledgers|settings|values)_wire)$','--output-on-failure'])
            inventory=json.loads(run(cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));inventories[cfg]=len(inventory['tests'])
            old_run=run(cfg+'-old-values-run',[BUILD/cfg/'pikapika_report_values_wire_tests.exe','--run']);need(json.loads(old_run)==json.loads((ROOT/'reports/diagnostic-wire-recipes/run-20261106-values-native-001'/(cfg+'-run.stdout.txt')).read_bytes()),'Whole old12 assertion output unchanged')
            old_raw=run(cfg+'-old-values-fixture',[BUILD/cfg/'pikapika_report_values_wire_tests.exe','--fixture'],True);need(old_raw==bytes.fromhex((ROOT/'reports/diagnostic-wire-recipes/run-20261106-values-native-001'/(cfg+'-fixture.stdout.hex.txt')).read_text()),'Whole old3112 bytes unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-settings-'+mode,[BUILD/cfg/'pikapika_report_settings_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-settings-native-002'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old settings '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-ledgers-'+mode,[BUILD/cfg/'pikapika_report_ledgers_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-ledgers-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old ledgers '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-work-'+mode,[BUILD/cfg/'pikapika_report_work_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-work-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old Work '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-intervals-'+mode,[BUILD/cfg/'pikapika_report_intervals_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-intervals-native-002'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old intervals '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-geometry-'+mode,[BUILD/cfg/'pikapika_report_geometry_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-geometry-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old geometry '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-result-'+mode,[BUILD/cfg/'pikapika_report_result_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-result-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old Result '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-mesh-values-'+mode,[BUILD/cfg/'pikapika_report_mesh_values_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-mesh-values-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old mesh values '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-mesh-result-'+mode,[BUILD/cfg/'pikapika_report_mesh_result_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-mesh-result-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old mesh Result '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-held-source-'+mode,[BUILD/cfg/'pikapika_report_held_source_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-held-source-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old held source '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-held-snapshot-work-'+mode,[BUILD/cfg/'pikapika_report_held_snapshot_work_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-held-snapshot-work-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old held snapshot/work '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-held-proofs-'+mode,[BUILD/cfg/'pikapika_report_held_proofs_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-held-proofs-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old held proofs '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-held-audits-'+mode,[BUILD/cfg/'pikapika_report_held_audits_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-held-audits-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old held audits '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-held-result-'+mode,[BUILD/cfg/'pikapika_report_held_result_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-held-result-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old held Result '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-flight-source-tube-'+mode,[BUILD/cfg/'pikapika_report_flight_source_tube_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-flight-source-tube-native-002'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old free flight source/tube '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-flight-endpoint-'+mode,[BUILD/cfg/'pikapika_report_flight_endpoint_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-flight-endpoint-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old free flight endpoint '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-flight-result-'+mode,[BUILD/cfg/'pikapika_report_flight_result_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-flight-result-native-002'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old free flight Result '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-guard-identity-body-'+mode,[BUILD/cfg/'pikapika_report_guard_identity_body_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-identity-body-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old guard identity/body '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-guard-failure-'+mode,[BUILD/cfg/'pikapika_report_guard_failure_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-failure-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old source/guard failure locations '+mode+' unchanged')
            for mode in ['run','fixture']:
                original=run(cfg+'-old-coverage-source-'+mode,[BUILD/cfg/'pikapika_report_coverage_source_wire_tests.exe','--'+mode],mode=='fixture')
                old_path=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-source-native-001'/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                expected=bytes.fromhex(old_path.read_text()) if mode=='fixture' else old_path.read_bytes()
                need(original==expected,'Whole old sphere/plane coefficients '+mode+' unchanged')
            for label,target,receipt in [
                ('pair-sources','pikapika_report_coverage_pair_sources_wire_tests','run-20261106-coverage-pair-sources-native-001'),
                ('primitive','pikapika_diagnostic_wire_tests','run-20261106-native-002'),
                ('rejection','pikapika_diagnostic_wire_rejection_tests','run-20261106-rejection-native-001'),
                ('input-variant','pikapika_report_coverage_input_variant_wire_tests','run-20261106-coverage-input-variant-native-002'),
                ('snapshot','pikapika_report_coverage_snapshot_wire_tests','run-20261106-coverage-snapshot-native-001'),
                ('cell-work','pikapika_report_coverage_cell_work_wire_tests','run-20261106-coverage-cell-work-native-001'),
                ('audit-partition','pikapika_report_coverage_audit_partition_wire_tests','run-20261106-coverage-audit-partition-native-001'),
                ('pair-result','pikapika_report_coverage_pair_result_wire_tests','run-20261106-coverage-pair-result-native-002'),
                ('plane-source-snapshot','pikapika_report_coverage_plane_source_snapshot_wire_tests','run-20261106-coverage-plane-source-snapshot-native-001'),
                ('plane-evaluation','pikapika_report_coverage_plane_evaluation_wire_tests','run-20261106-coverage-plane-evaluation-native-001')]:
                for mode in ['run','fixture']:
                    original=run(cfg+'-old-'+label+'-'+mode,[BUILD/cfg/(target+'.exe'),'--'+mode],mode=='fixture')
                    prior=ROOT/'reports/diagnostic-wire-recipes'/receipt/(cfg+'-'+mode+('.stdout.hex.txt' if mode=='fixture' else '.stdout.txt'))
                    expected=bytes.fromhex(prior.read_text()) if mode=='fixture' else prior.read_bytes()
                    need(original==expected,'Whole old '+label+' '+mode+' exact')
            raw=run(cfg+'-fixture',[BUILD/cfg/'pikapika_report_coverage_plane_cell_work_wire_tests.exe','--fixture'],True);captures.append(raw)
            ref=json.loads(run(cfg+'-reference',[sys.executable,'-B','-X','utf8',ROOT/'scripts/verify-report-coverage-plane-cell-work-wire.py',OUT/(cfg+'-fixture.stdout.hex.txt'),'--hex']));need(ref['status']=='PASS','Independent complete typed reference')
            for target in ['pikapika_diagnostic_wire','pikapika_report_values_wire','pikapika_report_coverage_plane_cell_work_wire_tests']:
                log=next((BUILD/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16')
                if target=='pikapika_report_coverage_plane_cell_work_wire_tests':need('INTERVAL.CPP' not in text.upper() and 'REPORT_COVERAGE_PLANE_CELL_WORK_WIRE_TESTS.CPP' in text.upper(),'Actual data-only harness; no Interval TU')
                for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual '+flag)
                need(bool(re.search(r'/D\s*(?:"NDEBUG"|NDEBUG)',text))==(cfg=='Release'),'Actual NDEBUG split')
                (OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(log.read_bytes())
        need(captures[0]==captures[1] and tests[0]==tests[1],'Actual Release/Debug exact raw and assertions')
        # The verifier explicitly refuses optimization rather than losing assertions.
        opt=subprocess.run([sys.executable,'-O','-B',ROOT/'scripts/verify-report-coverage-plane-cell-work-wire.py',OUT/'Release-fixture.stdout.hex.txt','--hex'],cwd=ROOT,capture_output=True)
        (OUT/'optimized.stdout.txt').write_bytes(opt.stdout);(OUT/'optimized.stderr.txt').write_bytes(opt.stderr)
        need(opt.returncode!=0 and b'Optimized Python is refused' in opt.stderr,'Actual optimized refusal')
        write(OUT/'optimized.command.json',dict(argv=list(map(str,opt.args)),exitCode=opt.returncode))
        result.update(status='FINITE_NATIVE_REPORT_COVERAGE_PLANE_CELL_WORK_PASS',native=tests[0],reference=ref,registeredTests=inventories,onlyNewCTestExecuted=False,selectedCTestPerConfiguration=31,oldLeafRegressionExecuted=True,oldCoreBuiltOrLinked=False,oldIntervalTUBuiltForOldRegressionHarnesses=True,newHarnessIntervalTU=False,oldTestsRerun=True,oldPhysicsTestsRerun=False,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False,optimizedVerifierRefused=True)
    except BaseException as error:result['error']=type(error).__name__+': '+str(error)
    after=[stamp(p) for p in paths];old_after=[stamp(p) for p in protected];write(OUT/'source-after.json',after);write(OUT/'protected-after.json',old_after)
    result.update(commands=commands,sourceStable=before==after,protectedFiles=len(old),protectedRawExact=old==old_after)
    if before!=after or old!=old_after:result['status']='FAIL'
    write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','native','error','protectedFiles'] if k in result}));return int(result['status']!='FINITE_NATIVE_REPORT_COVERAGE_PLANE_CELL_WORK_PASS')
if __name__=='__main__':raise SystemExit(main())
