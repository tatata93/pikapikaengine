"""Fresh47 selected CTests once per configuration: exact assertion JSON except line endings, all raw fixtures and20 profiles; new target3 data TUs/no Interval."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent/'run-20261106-preparation-snapshot-inventory-native-001'
BUILD=ROOT/'build/wfdpsi2'
PARENT=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-pair-values-native-001'
EARLY=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-snapshot-inventory-early-001'
TARGET='pikapika_report_preparation_snapshot_inventory_wire_tests';NAME='report_preparation_snapshot_inventory_wire'
EXTRACTOR=ROOT/'reports/diagnostic-wire-recipes/verify-guard-pair-record-ctest-extraction.py'
PROOF=ROOT/'reports/diagnostic-wire-validation/run-20261106-pair-record-ctest-extraction-001'
def need(v,m):
 if not v:raise ValueError(m)
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 need(__debug__ and sys.platform=='win32' and not OUT.exists() and not BUILD.exists(),'Fresh Windows Native output')
 proof=json.loads((PROOF/'verification.json').read_bytes());need(proof['status']=='ALL45_TWO_CONFIGURATION_CTEST_EXTRACTION_EXPERIMENT_PASS_ONLY' and proof['source']=='20cc0218bc523effe929a3bbfc724f65f43077ca' and proof['capturedLogNegativeRefusals']==14 and proof['artifactsAndCompiledBinariesStable'],'Actual full45/two-config extraction proof first')
 need((PROOF/'recipe.py.txt').read_bytes()==EXTRACTOR.read_bytes(),'Exact exercised extractor source')
 spec=importlib.util.spec_from_file_location('actual_ctest_parser',EXTRACTOR);extractor=importlib.util.module_from_spec(spec);spec.loader.exec_module(extractor)
 parent=json.loads((PARENT/'verification.json').read_bytes());need(parent['status']=='FINITE_NATIVE_REPORT_PREPARATION_PAIR_VALUES_PASS' and parent['schema']==2 and parent['sourceStable'] and parent['protectedRawExact'],'Complete parent Native')
 audit_path=PARENT/'verification.json';audit=dict(configurations={cfg:dict(actualNames=parent['configurations'][cfg]['names']) for cfg in ['Release','Debug']})
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());commands=[]
 paths=[ROOT/p for p in ['CMakeLists.txt','core/include/pikapika/diagnostic_wire.hpp','core/src/diagnostic_wire.cpp','core/include/pikapika/report_values_wire.hpp','core/src/report_values_wire.cpp','tests/report_preparation_snapshot_inventory_wire_tests.cpp','cmake/ReportValuesSchema.cmake','core/report-values-schema-v1.json','reports/diagnostic-wire-recipes/verify-preparation-snapshot-inventory-native.py','tests/report_preparation_snapshot_inventory_wire_reference_tests.py','scripts/verify-report-preparation-snapshot-inventory-wire.py','scripts/verify-diagnostic-wire.py','scripts/verify-report-values-wire.py','scripts/verify-report-preparation-pair-values-wire.py']]+[EXTRACTOR,PROOF/'verification.json',PARENT/'verification.json',audit_path]
 protected=[ROOT/p for p in subprocess.check_output(['git','ls-files','core','engine','samples','assets','platform','tests'],cwd=ROOT,text=True).splitlines() if p not in {x.relative_to(ROOT).as_posix() for x in paths}]
 before=[stamp(p) for p in paths];old=[stamp(p) for p in protected];write(OUT/'source-before.json',before);write(OUT/'protected-before.json',old)
 baselines={};baseline_paths=set();parent_inventories={}
 for cfg in ['Release','Debug']:
  names=set(audit['configurations'][cfg]['actualNames']);need(len(names)==46,'All46 prior names')
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
  need(set(rows)==names,'Complete46 prior captures');baselines[cfg]=rows;baseline_paths.add(EARLY/(cfg+'-run.stdout.txt'))
 baseline_before=[stamp(p) for p in sorted(baseline_paths)];write(OUT/'baseline-before.json',baseline_before)
 def run(name,argv,binary=False,expected_failure=False):
  start=time.monotonic();p=subprocess.Popen(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE);timed_out=False
  try:stdout,stderr=p.communicate(timeout=240)
  except subprocess.TimeoutExpired:
   timed_out=True;cleanup=subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15);(OUT/(name+'.timeout-cleanup.txt')).write_bytes(cleanup.stdout+cleanup.stderr);stdout,stderr=p.communicate(timeout=15)
  (OUT/(name+('.stdout.hex.txt' if binary else '.stdout.txt'))).write_bytes((stdout.hex()+'\n').encode() if binary else stdout);(OUT/(name+'.stderr.txt')).write_bytes(stderr)
  row=dict(name=name,argv=list(map(str,argv)),exitCode=p.returncode,timedOut=timed_out,expectedFailure=expected_failure,seconds=time.monotonic()-start,stdoutBytes=len(stdout),stdoutSha256=hashlib.sha256(stdout).hexdigest(),stdoutReversibleHex=binary);commands.append(row);write(OUT/(name+'.command.json'),row)
  need(not timed_out and ((p.returncode!=0) if expected_failure else (p.returncode==0)),'Actual '+name)
  return stdout
 result=dict(schema=2,status='FAIL',scope=__doc__);configurations={};new_assertions=[];fixtures=[];references=[];assertion_results=[]
 try:
  run('configure',['cmake','-S',ROOT,'-B',BUILD,'-A','x64','-DBUILD_TESTING=ON'])
  for cfg,baseline in baselines.items():
   targets=[TARGET]+[baseline[n]['target'] for n in sorted(baseline)];need(len(targets)==len(set(targets))==47,'All47 targets')
   groups=[targets[:1]]+[targets[i:i+4] for i in range(1,len(targets),4)]
   for i,group in enumerate(groups):run(cfg+'-build-'+str(i),['cmake','--build',BUILD,'--config',cfg,'--target',*group,'--parallel','2'])
   inventory=json.loads(run(cfg+'-inventory',['ctest','--test-dir',BUILD,'-C',cfg,'--show-only=json-v1']));need(len(inventory['tests'])==(104 if cfg=='Release' else 102),'Actual registered count')
   expected={name:dict(binary=str(BUILD/cfg/(row['target']+'.exe')),stdout=row['run'].relative_to(ROOT).as_posix()) for name,row in baseline.items()};expected[NAME]=dict(binary=str(BUILD/cfg/(TARGET+'.exe')),stdout=(EARLY/(cfg+'-run.stdout.txt')).relative_to(ROOT).as_posix())
   need(set(expected).issubset({t['name'] for t in inventory['tests']}),'All47 registered')
   actual=[];old_groups=[c for c in parent['commands'] if c['name'].startswith(cfg+'-ctest-')];need(len(old_groups)==15,'All parent groups retained')
   args_list=[]
   for c in old_groups:
    argv=list(c['argv']);need(argv[0]=='ctest' and argv[1]=='--test-dir','Actual parent CTest argv');argv[2]=str(BUILD);need(argv[-1]=='-V','Parent detailed CTest retained');args_list.append(argv)
   args_list.append(['ctest','--test-dir',str(BUILD),'-C',cfg,'-R','^'+NAME+'$','--output-on-failure','-V'])
   for i,argv in enumerate(args_list):
    raw=run(cfg+'-ctest-'+str(i),argv);names=re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',raw,re.M);rows=extractor.parse(raw,{n.decode():expected[n.decode()] for n in names});actual.extend(rows)
    payloads={n.decode():p for n,p in re.findall(rb'^\s*(\d+): (\{[^\r\n]*\})\r?$',raw,re.M)}
    for row in rows:
     payload=payloads[str(row['ctestNumber'])];dest=OUT/(cfg+'-'+row['name']+'-ctest-json.txt');dest.write_bytes(payload+b'\n');assertion_results.append(dict(configuration=cfg,name=row['name'],actualCTestCommand=cfg+'-ctest-'+str(i),compiledBinary=expected[row['name']]['binary'],JSONText=stamp(dest),baseline=row['originalStdout'],rawDirectStdoutTransferClaim=False))
     if row['name']==NAME:new_assertions.append(json.loads(payload))
   need(len(actual)==47 and len({r['name'] for r in actual})==47 and {r['name'] for r in actual}==set(expected),'Every old46 and new1 executed exactly once')
   configurations[cfg]=dict(registered=len(inventory['tests']),actualPassed=47,names=sorted(r['name'] for r in actual),old46Retained=True)
   for name,row in baseline.items():
    raw=run(cfg+'-old-'+name+'-fixture',[BUILD/cfg/(row['target']+'.exe'),'--fixture'],True);need(raw==bytes.fromhex(row['fixture'].read_text()),'Whole original raw fixture '+name)
   fixture=run(cfg+'-fixture',[BUILD/cfg/(TARGET+'.exe'),'--fixture'],True);fixtures.append(fixture)
   references.append(json.loads(run(cfg+'-reference',[sys.executable,'-B','-X','utf8',ROOT/'scripts/verify-report-preparation-snapshot-inventory-wire.py',OUT/(cfg+'-fixture.stdout.hex.txt'),'--hex'])))
   for target in ['pikapika_diagnostic_wire','pikapika_report_values_wire',TARGET]:
    log=next((BUILD/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));text=log.read_bytes().decode('utf16')
    for flag in ['/W4','/WX','/fp:strict','/GL-',('/MDd' if cfg=='Debug' else '/MD')]:need(re.search(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',text,re.I),'Actual strict flag')
    need(bool(re.search(r'/D\s*(?:"NDEBUG"|NDEBUG)',text))==(cfg=='Release'),'True Debug split')
    if target==TARGET:need('REPORT_PREPARATION_SNAPSHOT_INVENTORY_WIRE_TESTS.CPP' in text.upper() and 'INTERVAL.CPP' not in text.upper(),'New harness1TU without Interval')
    (OUT/(cfg+'-'+target+'.tlog.txt')).write_bytes(log.read_bytes())
   link=next((BUILD/(TARGET+'.dir')/cfg).rglob('link.command.1.tlog'));text=link.read_bytes().decode('utf16').upper();libs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text);libs=[v.strip('"').replace('\\','/').split('/')[-1] for v in libs]
   need(sorted(libs)==sorted(['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB','PIKAPIKA_DIAGNOSTIC_WIRE.LIB','PIKAPIKA_REPORT_VALUES_WIRE.LIB']),'Only2 data and Windows libraries');(OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(link.read_bytes())
  need(len(new_assertions)==2 and new_assertions[0]==new_assertions[1] and fixtures[0]==fixtures[1] and references[0]==references[1],'All new assertions/raw/reference exact across configurations')
  profiles=[];(OUT/'old-profile-originals').mkdir()
  for p in sorted(BUILD.glob('*.json')):
   prior=ROOT/'build/wfdv1'/p.name
   if prior.is_file():need(p.read_bytes()==prior.read_bytes(),'Old profile exact');(OUT/'old-profile-originals'/p.name).write_bytes(prior.read_bytes());profiles.append(stamp(p))
  need(len(profiles)==20,'All20 profiles')
  refusal=run('optimized-reference',[sys.executable,'-O','-B',ROOT/'scripts/verify-report-preparation-snapshot-inventory-wire.py',OUT/'Release-fixture.stdout.hex.txt','--hex'],expected_failure=True);need(b'Optimized Python is refused' in (OUT/'optimized-reference.stderr.txt').read_bytes(),'Actual optimized refusal')
  result.update(status='FINITE_NATIVE_REPORT_PREPARATION_SNAPSHOT_INVENTORY_PASS',native=new_assertions[0],reference=references[0],registeredTests={c:v['registered'] for c,v in configurations.items()},selectedCTestPerConfiguration=47,configurations=configurations,assertionResults=assertion_results,allOldAndNewAssertionJSONTextExactExceptLineTerminators=True,oldDirectRunCommandsReexecuted=False,oldDirectRunRawStdoutEquivalenceClaim=False,all46OldRawFixturesExact=True,old20ProfilesRawExact=True,profiles=profiles,extractorFull45Proof=stamp(PROOF/'verification.json'),extractorSource=stamp(EXTRACTOR),newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=0,newHarnessIntervalTU=False,oldIntervalTUBuiltForOldRegressionHarnesses=True,oldCoreBuiltOrLinked=False,oldTestsRerun=True,oldPhysicsTestsRerun=False,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False,optimizedVerifierRefused=True)
 except BaseException as e:result['error']=type(e).__name__+': '+str(e)
 after=[stamp(p) for p in paths];protected_after=[stamp(p) for p in protected];baseline_after=[stamp(p) for p in sorted(baseline_paths)];write(OUT/'source-after.json',after);write(OUT/'protected-after.json',protected_after);write(OUT/'baseline-after.json',baseline_after)
 result.update(commands=commands,sourceStable=before==after,protectedFiles=len(old),protectedRawExact=old==protected_after,baselineRawStable=baseline_before==baseline_after)
 if before!=after or old!=protected_after or baseline_before!=baseline_after:result['status']='FAIL'
 write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','error','native','protectedFiles','selectedCTestPerConfiguration','oldDirectRunCommandsReexecuted'] if k in result}));return int(result['status']!='FINITE_NATIVE_REPORT_PREPARATION_SNAPSHOT_INVENTORY_PASS')
if __name__=='__main__':raise SystemExit(main())
