"""Fresh65 actual CTests once per configuration (old48 and new contracts plus16 stop shards): exact assertion JSON except line endings, all raw fixtures and20 profiles; new target2 production data TUs,1 harness and1 test-only Interval TU."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent/'run-20261106-guard-result-native-003'
INITIAL=Path(__file__).parent/'run-20261106-guard-result-native-002'
BUILD=ROOT/'build/wfdgres3'
PARENT=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-result-native-001'
EARLY=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-result-early-002'
TARGET='pikapika_report_guard_result_wire_tests';NAME='report_guard_result_wire'
LEGACY_EXTRACTOR=ROOT/'reports/diagnostic-wire-recipes/verify-guard-pair-record-ctest-extraction.py'
EXTRACTOR=ROOT/'reports/diagnostic-wire-recipes/verify-guard-result-ctest-extraction.py'
ARGUMENT_PROOF=ROOT/'reports/diagnostic-wire-validation/run-20261106-guard-result-argument-extraction-001/verification.json'
PROOF=ROOT/'reports/diagnostic-wire-validation/run-20261106-pair-record-ctest-extraction-001'
def need(v,m):
 if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 need(__debug__ and sys.platform=='win32' and not OUT.exists() and BUILD.exists(),'Fresh continuation output; original build retained')
 proof=json.loads((PROOF/'verification.json').read_bytes());need(proof['status']=='ALL45_TWO_CONFIGURATION_CTEST_EXTRACTION_EXPERIMENT_PASS_ONLY' and proof['source']=='20cc0218bc523effe929a3bbfc724f65f43077ca' and proof['capturedLogNegativeRefusals']==14 and proof['artifactsAndCompiledBinariesStable'],'Actual full45/two-config extraction proof first')
 need((PROOF/'recipe.py.txt').read_bytes()==LEGACY_EXTRACTOR.read_bytes(),'Exact exercised extractor source')
 spec=importlib.util.spec_from_file_location('actual_ctest_parser',EXTRACTOR);extractor=importlib.util.module_from_spec(spec);spec.loader.exec_module(extractor)
 parent=json.loads((PARENT/'verification.json').read_bytes());need(parent['status']=='FINITE_NATIVE_REPORT_PREPARATION_RESULT_PASS' and parent['schema']==2 and parent['sourceStable'] and parent['protectedRawExact'],'Complete parent Native')
 audit_path=PARENT/'verification.json';audit=dict(configurations={cfg:dict(actualNames=parent['configurations'][cfg]['names']) for cfg in ['Release','Debug']})
 initial=json.loads((INITIAL/'verification.json').read_bytes());need(initial['status']=='FAIL' and initial['error']=='ValueError: New harness1TU without Interval' and initial['sourceStable'] and initial['protectedRawExact'] and initial['baselineRawStable'],'Preserved actual failed extraction with stable sources')
 for name in ['source-before.json','protected-before.json','baseline-before.json']:
  for row in json.loads((INITIAL/name).read_bytes()):need(stamp(ROOT/row['path'])==row,'Exact original captured bytes before continuation')
 argument_proof=json.loads(ARGUMENT_PROOF.read_bytes());need(argument_proof['status']=='ACTUAL50_CAPTURED_CTESTS_AND12_NEGATIVE_ARGUMENT_CASES_PASS' and argument_proof['sourceStable'] and argument_proof['testsRerun']==False,'Actual captured argument extension experiment')
 need((ARGUMENT_PROOF.parent/'parser.py.txt').read_bytes()==EXTRACTOR.read_bytes(),'Exact exercised extension')
 OUT.mkdir();copied=[]
 for source in INITIAL.iterdir():
  need(source.is_file(),'Only initial raw files')
  name=source.name
  if name in {'verification.json','recipe.py.txt','source-before.json','source-after.json','protected-before.json','protected-after.json','baseline-before.json','baseline-after.json'}:name=INITIAL.name+'-'+name
  destination=OUT/name;need(not destination.exists(),'Fresh copy');destination.write_bytes(source.read_bytes());copied.append(dict(original=stamp(source),copy=stamp(destination)))
 (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());commands=[];reused_commands=[];prior_commands={c['name']:c for c in initial['commands']}

 paths=[ROOT/p for p in ['CMakeLists.txt','core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp','core/include/pikapika/report_values_wire.hpp','core/src/report_values_wire.cpp','tests/report_guard_result_wire_tests.cpp','cmake/ReportValuesSchema.cmake','core/report-values-schema-v1.json','reports/diagnostic-wire-recipes/verify-guard-result-native-continuation-tu.py','tests/report_guard_result_wire_reference_tests.py','scripts/verify-report-guard-result-wire.py','scripts/verify-diagnostic-wire.py','scripts/verify-report-values-wire.py','scripts/verify-report-preparation-pair-values-wire.py','scripts/verify-report-preparation-snapshot-inventory-wire.py','scripts/verify-report-guard-failure-wire.py', 'scripts/verify-report-coverage-audit-partition-wire.py', 'scripts/verify-report-coverage-cell-work-wire.py', 'scripts/verify-report-coverage-pair-result-wire.py', 'scripts/verify-report-coverage-plane-audit-partition-wire.py', 'scripts/verify-report-coverage-plane-cell-work-wire.py', 'scripts/verify-report-coverage-plane-result-wire.py', 'scripts/verify-report-coverage-plane-source-snapshot-wire.py', 'scripts/verify-report-coverage-snapshot-wire.py', 'scripts/verify-report-coverage-sphere-audit-partition-wire.py', 'scripts/verify-report-coverage-sphere-cell-work-wire.py', 'scripts/verify-report-coverage-sphere-result-wire.py', 'scripts/verify-report-coverage-sphere-source-snapshot-wire.py', 'scripts/verify-report-flight-endpoint-wire.py', 'scripts/verify-report-flight-result-wire.py', 'scripts/verify-report-flight-source-tube-wire.py', 'scripts/verify-report-guard-child-variant-wire.py', 'scripts/verify-report-guard-identity-body-wire.py', 'scripts/verify-report-guard-mesh-call-wire.py', 'scripts/verify-report-guard-pair-record-wire.py', 'scripts/verify-report-guard-plane-box-call-wire.py', 'scripts/verify-report-guard-plane-calls-wire.py', 'scripts/verify-report-guard-plane-metric-call-wire.py', 'scripts/verify-report-guard-sphere-box-call-wire.py', 'scripts/verify-report-held-snapshot-work-wire.py', 'scripts/verify-report-ledgers-wire.py', 'scripts/verify-report-preparation-result-wire.py', 'scripts/verify-report-settings-wire.py', 'scripts/verify-report-work-wire.py', 'tests/diagnostic_wire_subtree_control_support.py', 'core/src/interval.cpp']]+[EXTRACTOR,LEGACY_EXTRACTOR,ARGUMENT_PROOF,INITIAL/'verification.json',PROOF/'verification.json',PARENT/'verification.json',audit_path]
 equivalence=ROOT/'reports/diagnostic-wire-validation/run-20261106-subtree-control-equivalence-001/verification.json';equivalence_record=json.loads(equivalence.read_bytes());need(equivalence_record['status']=='ALL17840_EXISTING_RESULT_CONTROLS_WHOLE_SCOPED_EQUIVALENCE_PASS' and equivalence_record['sourceStable'],'Actual whole/scoped equivalence proof retained');paths.append(equivalence)
 paths.append(ROOT/'reports/diagnostic-wire-recipes/verify-guard-result-native.py')
 paths.extend([ROOT/'reports/diagnostic-wire-recipes/verify-guard-result-native-continuation.py',ROOT/'reports/diagnostic-wire-recipes/guard-result-tu-audit.py',ROOT/'reports/diagnostic-wire-validation/run-20261106-guard-result-tu-audit-001/verification.json'])
 audit_module=ROOT/'reports/diagnostic-wire-recipes/guard-result-tu-audit.py';audit_proof=json.loads((ROOT/'reports/diagnostic-wire-validation/run-20261106-guard-result-tu-audit-001/verification.json').read_bytes());need(audit_proof['status']=='ACTUAL_RELEASE_FOUR_TUS_AND9_NEGATIVE_AUDITS_PASS','Actual four-TU audit experiment');need((ROOT/'reports/diagnostic-wire-validation/run-20261106-guard-result-tu-audit-001/audit.py.txt').read_bytes()==audit_module.read_bytes(),'Exact exercised audit source');audit_spec=importlib.util.spec_from_file_location('actual_four_tu_audit',audit_module);tu_audit=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(tu_audit)
 protected=[ROOT/p for p in subprocess.check_output(['git','ls-files','core','engine','samples','assets','platform','tests'],cwd=ROOT,text=True).splitlines() if p not in {x.relative_to(ROOT).as_posix() for x in paths}]
 before=[stamp(p) for p in paths];old=[stamp(p) for p in protected];write(OUT/'source-before.json',before);write(OUT/'protected-before.json',old)
 baselines={};baseline_paths=set();parent_inventories={}
 for cfg in ['Release','Debug']:
  names=set(audit['configurations'][cfg]['actualNames']);need(len(names)==48,'All48 prior names')
  inv_path=PARENT/(cfg+'-inventory.stdout.txt');baseline_paths.add(inv_path);inventory=json.loads(inv_path.read_bytes());parent_inventories[cfg]=inventory;rows={}
  for test in inventory['tests']:
   if test['name'] not in names:continue
   argv=test['command'];need(len(argv)==2 and argv[1]=='--run','Actual parent command');stem=Path(argv[0]).stem;need(re.fullmatch(r'pikapika_[a-z0-9_]+_tests',stem),'Bounded target name')
   row=dict(target=stem)
   captures=[r for r in parent['assertionResults'] if r['configuration']==cfg and r['name']==test['name']];need(len(captures)==1,'One parent canonical CTest JSON capture')
   capture=captures[0];canonical=ROOT/capture['JSONText']['path'];need(stamp(canonical)==capture['JSONText'] and not capture['rawDirectStdoutTransferClaim'],'Exact canonical JSON provenance')
   command=next(c for c in parent['commands'] if c['name']==capture['actualCTestCommand']);need(command['exitCode']==0 and not command['timedOut'] and command['argv'][0]=='ctest','Actual parent CTest passed')
   ctest_raw=PARENT/(command['name']+'.stdout.txt');raw=ctest_raw.read_bytes();need(len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'],'Exact original detailed CTest output');baseline_paths.add(ctest_raw)
   row['run']=canonical;baseline_paths.add(canonical)
   found=[c for c in parent['commands'] if c['name'].startswith(cfg+'-') and c['name'].endswith('-fixture') and len(c['argv'])==2 and Path(c['argv'][0]).resolve()==Path(argv[0]).resolve() and c['argv'][1]=='--fixture'];need(len(found)==1,'One actual prior raw fixture capture')
   command=found[0];path=PARENT/(command['name']+'.stdout.hex.txt');raw=bytes.fromhex(path.read_text());need(command['exitCode']==0 and len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'],'Exact parent raw fixture bytes')
   row['fixture']=path;baseline_paths.add(path)
   rows[test['name']]=row
  need(set(rows)==names,'Complete48 prior captures');baselines[cfg]=rows;baseline_paths.add(EARLY/(cfg+'-run.stdout.txt'))
 baseline_before=[stamp(p) for p in sorted(baseline_paths)];write(OUT/'baseline-before.json',baseline_before)
 def run(name,argv,binary=False,expected_failure=False):
  if name in prior_commands:
   original=prior_commands[name];need(original['argv']==list(map(str,argv)) and original['exitCode']==0 and not original['timedOut'] and original['expectedFailure']==expected_failure and original['stdoutReversibleHex']==binary,'Exact original executed command, flags and outcome')
   source=INITIAL/(name+('.stdout.hex.txt' if binary else '.stdout.txt'));raw=source.read_bytes();actual=bytes.fromhex(raw.decode()) if binary else raw
   need(len(actual)==original['stdoutBytes'] and hashlib.sha256(actual).hexdigest()==original['stdoutSha256'] and (OUT/source.name).read_bytes()==raw,'Exact transferred raw original command output')
   commands.append(dict(original,reusedActualCapturedCommand=True,originalCommandReceipt=stamp(INITIAL/(name+'.command.json'))));reused_commands.append(name);return actual
  start=time.monotonic();p=subprocess.Popen(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE);timed_out=False
  try:stdout,stderr=p.communicate(timeout=240)
  except subprocess.TimeoutExpired:
   timed_out=True;cleanup=subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15);(OUT/(name+'.timeout-cleanup.txt')).write_bytes(cleanup.stdout+cleanup.stderr);stdout,stderr=p.communicate(timeout=15)
  (OUT/(name+('.stdout.hex.txt' if binary else '.stdout.txt'))).write_bytes((stdout.hex()+'\n').encode() if binary else stdout);(OUT/(name+'.stderr.txt')).write_bytes(stderr)
  row=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,timedOut=timed_out,expectedFailure=expected_failure,seconds=time.monotonic()-start,stdoutBytes=len(stdout),stdoutSha256=hashlib.sha256(stdout).hexdigest(),stdoutReversibleHex=binary);commands.append(row);write(OUT/(name+'.command.json'),row)
  need(not timed_out and ((p.returncode!=0) if expected_failure else (p.returncode==0)),'Actual '+name)
  return stdout
 result=dict(schema=2,status='FAIL',scope=__doc__);configurations={};new_assertions=[];fixtures=[];references=[];assertion_results=[];new_stops={cfg:[] for cfg in ['Release','Debug']}
 try:
  run('configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON'])
  for cfg,baseline in baselines.items():
   targets=[TARGET]+[baseline[n]['target'] for n in sorted(baseline)];need(len(targets)==len(set(targets))==49,'All49 build targets')
   groups=[targets[:1]]+[targets[i:i+4] for i in range(1,len(targets),4)]
   for i,group in enumerate(groups):run(cfg+'-build-'+str(i),['cmake','--build',BUILD,'--config',cfg,'--target',*group,'--parallel','2'])
   inventory=json.loads(run(cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));need(len(inventory['tests'])==(122 if cfg=='Release' else 120),'Actual registered count')
   expected={name:dict(binary=str(BUILD/cfg/(row['target']+'.exe')),stdout=row['run'].relative_to(ROOT).as_posix()) for name,row in baseline.items()};expected[NAME]=dict(binary=str(BUILD/cfg/(TARGET+'.exe')),stdout=(EARLY/(cfg+'-run.stdout.txt')).relative_to(ROOT).as_posix())
   for stop in range(16):
    expected_path=OUT/(cfg+'-stop-'+str(stop)+'-independent-expected-spec.json.txt')
    specification=dict(status='PASS',shard=stop,shards=16,totalCallbackBoundaries=26175,testedCallbackBoundaries=1636 if stop<15 else 1635,stopAndExceptionCases=3272 if stop<15 else 3270,wholeFixtureBytes=219960,sourceRepeatedRawExact=True)
    expected_path.write_text(json.dumps(specification,separators=(',',':'))+'\n',encoding='utf8',newline='\n')
    expected[NAME+'_stop_'+str(stop)]=dict(binary=str(BUILD/cfg/(TARGET+'.exe')),stdout=expected_path.relative_to(ROOT).as_posix(),argument='--stop-shard-'+str(stop))
   need(set(expected).issubset({t['name'] for t in inventory['tests']}),'All65 registered')
   actual=[];old_groups=[c for c in parent['commands'] if c['name'].startswith(cfg+'-ctest-')];need(len(old_groups)==17,'All parent groups retained')
   args_list=[]
   for c in old_groups:
    argv=list(c['argv']);need(argv[0]=='ctest' and argv[1]=='--test-dir','Actual parent CTest argv');argv[2]=str(BUILD);need(argv[-1]=='-V','Parent detailed CTest retained');args_list.append(argv)
   args_list.append(['ctest','--test-dir',str(BUILD),'-C',cfg,'-R','^'+NAME+'$','--output-on-failure','-V'])
   for stop in range(16):args_list.append(['ctest','--test-dir',str(BUILD),'-C',cfg,'-R','^'+NAME+'_stop_'+str(stop)+'$','--output-on-failure','-V'])
   for i,argv in enumerate(args_list):
    raw=run(cfg+'-ctest-'+str(i),argv);names=re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',raw,re.M);rows=extractor.parse(raw,{n.decode():expected[n.decode()] for n in names});actual.extend(rows)
    payloads={n.decode():p for n,p in re.findall(rb'^\s*(\d+): (\{[^\r\n]*\})\r?$',raw,re.M)}
    for row in rows:
     payload=payloads[str(row['ctestNumber'])];dest=OUT/(cfg+'-'+row['name']+'-ctest-json.txt');dest.write_bytes(payload+b'\n');assertion_results.append(dict(configuration=cfg,name=row['name'],actualCTestCommand=cfg+'-ctest-'+str(i),compiledBinary=expected[row['name']]['binary'],JSONText=stamp(dest),baseline=row['originalStdout'],rawDirectStdoutTransferClaim=False,baselineKind=('independent-count-specification-not-execution' if row['name'].startswith(NAME+'_stop_') else 'actual-prior-passing-command')) )
     if row['name']==NAME:new_assertions.append(json.loads(payload))
     if row['name'].startswith(NAME+'_stop_'):new_stops[cfg].append(json.loads(payload))
   need(len(actual)==65 and len({r['name'] for r in actual})==65 and {r['name'] for r in actual}==set(expected),'Every old48, new contracts and all16 stop shards executed exactly once')
   configurations[cfg]=dict(registered=len(inventory['tests']),actualPassed=65,names=sorted(r['name'] for r in actual),old48Retained=True)
   for name,row in baseline.items():
    raw=run(cfg+'-old-'+name+'-fixture',[BUILD/cfg/(row['target']+'.exe'),'--fixture'],True);need(raw==bytes.fromhex(row['fixture'].read_text()),'Whole original raw fixture '+name)
   fixture=run(cfg+'-fixture',[BUILD/cfg/(TARGET+'.exe'),'--fixture'],True);fixtures.append(fixture)
   references.append(json.loads(run(cfg+'-reference',[sys.executable,'-B','-X','utf8',ROOT/'scripts/verify-report-guard-result-wire.py',OUT/(cfg+'-fixture.stdout.hex.txt'),'--hex'])))
   audit_rows=tu_audit.audit(BUILD,cfg);write(OUT/(cfg+'-actual-four-tu-audit.json'),dict(status='PASS',actualTUs=4,sourceCommands=audit_rows))
   for target in ['pikapika_diagnostic_wire','pikapika_report_values_wire',TARGET]:
    log=next((BUILD/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));(OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(log.read_bytes())
   link=next((BUILD/(TARGET+'.dir')/cfg).rglob('link.command.1.tlog'));text=link.read_bytes().decode('utf16').upper();libs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text);libs=[v.strip('"').replace('\\','/').split('/')[-1] for v in libs]
   need(sorted(libs)==sorted(['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB','PIKAPIKA_DIAGNOSTIC_WIRE.LIB','PIKAPIKA_REPORT_VALUES_WIRE.LIB']),'Only2 data and Windows libraries');(OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(link.read_bytes())
  for cfg,stops in new_stops.items():
   need(len(stops)==16 and {v['shard'] for v in stops}==set(range(16)) and all(v['status']=='PASS' and v['shards']==16 for v in stops),'All actual16 stop commands')
   need(sum(v['testedCallbackBoundaries'] for v in stops)==26175 and sum(v['stopAndExceptionCases'] for v in stops)==52350,'No boundary or stop/exception case dropped')
  need(new_stops['Release']==new_stops['Debug'],'All actual stop outputs exact across configurations')
  need(len(new_assertions)==2 and new_assertions[0]==new_assertions[1] and fixtures[0]==fixtures[1] and references[0]==references[1],'All new assertions/raw/reference exact across configurations')
  profiles=[];(OUT/'old-profile-originals').mkdir()
  for p in sorted(BUILD.glob('*.json')):
   prior=ROOT/'build/wfdv1'/p.name
   if prior.is_file():need(p.read_bytes()==prior.read_bytes(),'Old profile exact');(OUT/'old-profile-originals'/p.name).write_bytes(prior.read_bytes());profiles.append(stamp(p))
  need(len(profiles)==20,'All20 profiles')
  refusal=run('optimized-reference',[sys.executable,'-O','-B',ROOT/'scripts/verify-report-guard-result-wire.py',OUT/'Release-fixture.stdout.hex.txt','--hex'],expected_failure=True);need(b'Optimized Python refused' in (OUT/'optimized-reference.stderr.txt').read_bytes(),'Actual optimized refusal')
  result.update(status='FINITE_NATIVE_REPORT_GUARD_RESULT_PASS',native=new_assertions[0],stopShards=new_stops,all52350StopAndExceptionCasesPerConfiguration=True,rootContractsBaselineOnlyFromActualPassingEarlyCommands=True,failedEarlyParentAccepted=False,reference=references[0],registeredTests={c:v['registered'] for c,v in configurations.items()},selectedCTestPerConfiguration=65,configurations=configurations,assertionResults=assertion_results,allOldAndNewAssertionJSONTextExactExceptLineTerminators=True,oldDirectRunCommandsReexecuted=False,oldDirectRunRawStdoutEquivalenceClaim=False,all48OldRawFixturesExact=True,old20ProfilesRawExact=True,profiles=profiles,extractorFull45Proof=stamp(PROOF/'verification.json'),extractorSource=stamp(EXTRACTOR),argumentExtractionProof=stamp(ARGUMENT_PROOF),fourTranslationUnitAuditProof=stamp(ROOT/'reports/diagnostic-wire-validation/run-20261106-guard-result-tu-audit-001/verification.json'),allFourTranslationUnitsStrictFlagsIndividuallyAudited=True,initialFailedReceipt=stamp(INITIAL/'verification.json'),initialRawCopies=copied,reusedActualCommands=reused_commands,reusedCommandsReexecuted=False,originalBuildDirectoryReused=True,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,newHarnessIntervalTU=True,oldIntervalTUBuiltForOldRegressionHarnesses=True,oldCoreBuiltOrLinked=False,oldTestsRerun=True,oldPhysicsTestsRerun=False,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False,optimizedVerifierRefused=True)
 except BaseException as e:result['error']=type(e).__name__+': '+str(e)
 after=[stamp(p) for p in paths];protected_after=[stamp(p) for p in protected];baseline_after=[stamp(p) for p in sorted(baseline_paths)];write(OUT/'source-after.json',after);write(OUT/'protected-after.json',protected_after);write(OUT/'baseline-after.json',baseline_after)
 result.update(commands=commands,sourceStable=before==after,protectedFiles=len(old),protectedRawExact=old==protected_after,baselineRawStable=baseline_before==baseline_after)
 if before!=after or old!=protected_after or baseline_before!=baseline_after:result['status']='FAIL'
 write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','error','native','protectedFiles','selectedCTestPerConfiguration','oldDirectRunCommandsReexecuted'] if k in result}));return int(result['status']!='FINITE_NATIVE_REPORT_GUARD_RESULT_PASS')
if __name__=='__main__':raise SystemExit(main())
