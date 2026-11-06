"""Independently inspect132 actual CTest assertions and all raw fixtures; no C++ rerun."""
from pathlib import Path
import hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-failure-clock-native-001'
PARENT=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-result-native-004'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-failure-clock-native-001'
def need(v,m):
 if not v:raise ValueError(m)
def read(p):return json.loads(p.read_bytes())
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 need(__debug__ and not OUT.exists(),'Fresh integration')
 n=read(NATIVE/'verification.json');need(n['status']=='FINITE_NATIVE_REPORT_ADVANCE_FAILURE_CLOCK_PASS' and n['sourceStable'] and n['protectedRawExact'] and n['baselineRawStable'],'Whole Native first')
 need(n['selectedCTestPerConfiguration']==66 and n['registeredTests']==dict(Release=123,Debug=121) and len(n['assertionResults'])==132,'Exact tested counts')
 for name in ['source-before.json','protected-before.json','baseline-before.json']:
  for row in read(NATIVE/name):need(stamp(ROOT/row['path'])==row,'Every tested/protected/baseline byte exact')
 covered={row['path'] for name in ['source-before.json','protected-before.json'] for row in read(NATIVE/name)}
 need(len(covered)==467 and len(read(NATIVE/'source-before.json'))==81 and len(read(NATIVE/'protected-before.json'))==386,'Exact unique tested and protected inventory')
 previous_protected=read(PARENT/'protected-before.json');need(len(previous_protected)==402 and all(row['path'] in covered and stamp(ROOT/row['path'])==row for row in previous_protected),'All402 prior protected files still covered; headers may move into explicit source inventory')
 module=ROOT/n['extractorSource']['path'];need(stamp(module)==n['extractorSource'],'Exact exercised parser');spec=importlib.util.spec_from_file_location('independent_afc_parser',module);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
 spec=importlib.util.spec_from_file_location('independent_afc_tu_audit',ROOT/'reports/diagnostic-wire-recipes/guard-result-tu-audit.py');tu=importlib.util.module_from_spec(spec);spec.loader.exec_module(tu)
 spec=importlib.util.spec_from_file_location('independent_afc_oracle',ROOT/'scripts/verify-report-advance-failure-clock-wire.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 configurations={};ctest_receipts=[];fixture_receipts=[];parent=read(PARENT/'verification.json')
 for cfg in ['Release','Debug']:
  rows=[r for r in n['assertionResults'] if r['configuration']==cfg];inventory=read(NATIVE/(cfg+'-inventory.stdout.txt'));argv={r['name']:r['command'] for r in inventory['tests'] if 'command' in r}
  need(len(rows)==len({r['name'] for r in rows})==66 and {r['name'] for r in rows}==set(parent['configurations'][cfg]['names'])|{'report_advance_failure_clock_wire'},'All65 old plus1 new')
  expected={r['name']:dict(binary=r['compiledBinary'],stdout=r['baseline']['path'],argument=argv[r['name']][1]) for r in rows};actual=[]
  commands=[c for c in n['commands'] if c['name'].startswith(cfg+'-ctest-')];need(len(commands)==35,'34 old groups plus1 new')
  for c in commands:
   p=NATIVE/(c['name']+'.stdout.txt');b=p.read_bytes();need(c['exitCode']==0 and not c['timedOut'] and len(b)==c['stdoutBytes'] and hashlib.sha256(b).hexdigest()==c['stdoutSha256'],'Actual full CTest log')
   names=[s.decode() for s in re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',b,re.M)];actual+=parser.parse(b,{s:expected[s] for s in names});ctest_receipts.append(stamp(p))
  need(len(actual)==len({r['name'] for r in actual})==66 and {r['name'] for r in actual}==set(expected),'Every selected CTest exactly once')
  for r in rows:need(stamp(ROOT/r['JSONText']['path'])==r['JSONText'] and not r['rawDirectStdoutTransferClaim'],'Every actual canonical JSON text')
  old_commands=[c for c in n['commands'] if c['name'].startswith(cfg+'-old-') and c['name'].endswith('-fixture')];need(len(old_commands)==49 and len({c['argv'][0] for c in old_commands})==49,'All49 unique old fixture commands')
  for c in old_commands:
   need(c['exitCode']==0 and not c['timedOut'] and c['argv'][1]=='--fixture','Actual fixture command')
   captured=NATIVE/(c['name']+'.stdout.hex.txt');b=bytes.fromhex(captured.read_text());need(len(b)==c['stdoutBytes'] and hashlib.sha256(b).hexdigest()==c['stdoutSha256'],'Whole raw capture exact')
   old_target=Path(c['argv'][0]).name
   candidates=[p for p in parent['commands'] if p['name'].startswith(cfg+'-') and p['name'].endswith('-fixture') and len(p['argv'])==2 and Path(p['argv'][0]).name==old_target and p['argv'][1]=='--fixture'];need(len(candidates)==1,'One original raw baseline')
   need(b==bytes.fromhex((PARENT/(candidates[0]['name']+'.stdout.hex.txt')).read_text()),'Every old whole raw fixture exact');fixture_receipts.append(stamp(captured))
  c=next(c for c in n['commands'] if c['name']==cfg+'-fixture');raw=bytes.fromhex((NATIVE/(cfg+'-fixture.stdout.hex.txt')).read_text());need(c['stdoutBytes']==len(raw)==5183 and c['stdoutSha256']==hashlib.sha256(raw).hexdigest()=='5012e5b95d0ab5b305e2bc58bf7d697c7d2dbf46f0ff00207c66753b834ec2ea','New whole raw fixture')
  need(oracle.verify(raw)==n['reference'],'Independent typed decoding from actual raw new capture')
  audit=read(NATIVE/(cfg+'-four-tu-audit.json'));actual_tus=[]
  for target,sources in {'pikapika_diagnostic_wire':['core/src/diagnostic_wire.cpp'],'pikapika_report_values_wire':['core/src/report_values_wire.cpp'],'pikapika_report_advance_failure_clock_wire_tests':['tests/report_advance_failure_clock_wire_tests.cpp','core/src/interval.cpp']}.items():
   actual_tus+=tu.inspect((NATIVE/(cfg+'-'+target+'.tlog.txt')).read_bytes().decode('utf16'),{(ROOT/p).as_posix().upper() for p in sources},cfg)
  need(audit==actual_tus and len(audit)==len({r['source'] for r in audit})==4,'Every strict per-source command independently reparsed')
  configurations[cfg]=dict(actualPassed=66,old65Retained=True,uniqueOldFixtures=49,all16OldStopShardsRetained=True,actualNames=sorted(expected))
 web=ROOT/'reports/diagnostic-wire-integration/run-20261106-advance-failure-clock-web-001/verification.json';w=read(web);need(w['status']=='FINITE_ADVANCE_FAILURE_CLOCK_WEB_PASS' and w['schemaControls']['mappedTypes']==99 and w['schemaControls']['mappedFields']==581 and w['schemaControls']['accepted']==1 and w['schemaControls']['refused']==20,'Actual Web gates')
 for c in w['commands']:need(c['exitCode']==0 and not c['timedOut'],'Every Web command success')
 controls=ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-failure-clock-controls-001';c=read(controls/'verification.json');cmd=read(controls/'command.json');b=(controls/'stdout.json').read_bytes();complete=json.loads(b)
 need(c['status']=='PASS' and c['sourceStable'] and c['controlsDecoded']==c['controlsConsidered']==3196 and c['identicalFieldExchanges']==7 and c['baseline']==n['reference'],'Complete full-document controls')
 need(cmd['exitCode']==0 and not cmd['timedOut'] and cmd['timeoutSeconds']==180 and len(b)==cmd['stdoutBytes'] and hashlib.sha256(b).hexdigest()==cmd['stdoutSha256'],'Actual full control stdout')
 need({k:v for k,v in complete.items() if k!='mutations'}=={k:v for k,v in c.items() if k not in {'sourceBefore','sourceAfter','sourceStable','wholeNativeAccepted','actualGNUExecuted'}},'Actual summary matches full original')
 need((controls/'scanner.py.txt').read_bytes()==(ROOT/'tests/report_advance_failure_clock_wire_reference_tests.py').read_bytes(),'Actual scanner source')
 need(n['all49OldRawFixturesExact'] and n['old20ProfilesRawExact'] and len(n['profiles'])==20 and n['newHarnessIntervalTU'] and n['testOnlyIntervalTUs']==1 and not n['oldCoreBuiltOrLinked'],'Finite retained scope')
 for row in n['profiles']:
  p=ROOT/row['path'];need(stamp(p)==row and p.read_bytes()==(NATIVE/'old-profile-originals'/p.name).read_bytes(),'Old profile exact')
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());result=dict(status='FINITE_ADVANCE_FAILURE_CLOCK_INTEGRATION_PASS',nativeReceipt=stamp(NATIVE/'verification.json'),webReceipt=stamp(web),controlsReceipt=stamp(controls/'verification.json'),configurations=configurations,actualCTestOutputReceipts=ctest_receipts,wholeOldFixtureReceipts=fixture_receipts,all132ActualAssertionRecordsRechecked=True,all66NamesCommandsAndArgumentsPerConfigurationExact=True,all49OldRawFixturesExact=True,old20ProfilesRawExact=True,testedSourcesAndBaselineStable=True,testsRerun=False,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False)
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status=result['status'],all132ActualAssertionRecordsRechecked=True,testsRerun=False)))
if __name__=='__main__':main()
