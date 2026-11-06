"""Independently recheck all65 actual CTests, aliases, raw captures and scoped controls; never rerun Cpp."""
from pathlib import Path
import hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-result-native-004'
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-guard-result-native-002'
def need(v,m):
 if not v:raise ValueError(m)
def read(p):return json.loads(p.read_bytes())
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 need(__debug__ and not OUT.exists(),'Fresh independent integration')
 n=read(NATIVE/'verification.json');need(n['status']=='FINITE_NATIVE_REPORT_GUARD_RESULT_PASS' and n['sourceStable'] and n['protectedRawExact'] and n['baselineRawStable'],'Whole Native first')
 need(n['selectedCTestPerConfiguration']==65 and n['registeredTests']==dict(Release=122,Debug=120) and n['protectedFiles']==402,'Exact Native counts')
 for name in ['source-before.json','protected-before.json','baseline-before.json']:
  for row in read(NATIVE/name):need(stamp(ROOT/row['path'])==row,'Every tested/protected/baseline byte unchanged')
 for copied in n['initialRawCopies']:need(stamp(ROOT/copied['original']['path'])==copied['original'] and stamp(ROOT/copied['copy']['path'])==copied['copy'],'Original and transferred raw copies exact')
 for command in n['commands']:
  for alias in command.get('requestedInputAliases',[]):
   need(stamp(ROOT/alias['originalInput']['path'])==alias['originalInput'] and stamp(ROOT/alias['requestedIdenticalInput']['path'])==alias['requestedIdenticalInput'],'Exact original/current input alias')
   need((ROOT/alias['originalInput']['path']).read_bytes()==(ROOT/alias['requestedIdenticalInput']['path']).read_bytes() and command['actualOriginalArgvPreserved'],'No changed input or fabricated argv')
 web=ROOT/'reports/diagnostic-wire-integration/run-20261106-guard-result-web-metadata-correction-001/verification.json';w=read(web)
 need(w['status']=='FINITE_GUARD_RESULT_WEB_METADATA_CORRECTION_ACCEPTED' and w['mappedRecordTypes']==97 and w['mappedFields']==575 and w['schemaControls']['mappedTypes']==97 and w['schemaControls']['mappedFields']==575 and w['schemaControls']['accepted']==1 and w['schemaControls']['refused']==20 and w['actualNodePass']==693 and w['actualNodeSkipped']==0 and not w['testsRerun'] and not w['correctedProducerExecuted'],'Actual Web gates and explicit summary correction')
 controls=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-result-controls-001';c=read(controls/'verification.json');inventory=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-result-inventory-001';full=read(inventory/'stdout.json')
 need(c['status']=='ALL4_GUARD_RESULT_CONTROL_SHARDS_PASS' and c['sourceStable'] and c['controlsDecoded']==171199 and c['baseline']==n['reference'],'All four new control shards')
 canonical=json.dumps(full['mutations'],separators=(',',':')).encode();need(dict(entries=len(full['mutations']),canonicalBytes=len(canonical),canonicalSha256=hashlib.sha256(canonical).hexdigest())==c['mutationInventory'],'Every scalar/key inventory entry retained')
 for i,shard in enumerate(c['perShard']):
  command=read(controls/('shard-'+str(i)+'.command.json'));raw=(controls/('shard-'+str(i)+'.stdout.json')).read_bytes()
  need(command['exitCode']==0 and not command['timedOut'] and len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'] and json.loads(raw)==shard,'Actual complete control output')
  need(shard['status']=='PASS_SHARD' and shard['shard']==i and shard['shards']==4 and shard['controlsDecoded']==(42800 if i<3 else 42799) and shard['mutationInventory']==c['mutationInventory'],'Every shard and inventory exact')
  method=shard['comparisonMethod'];need(method['scopedComparisons']+method['wholeComparisons']==shard['controlsDecoded'] and method['wholeDocumentDualComparisons']>0 and method['outsideScopeWholeBytesCompared'] and method['originalAncestorDepthReproduced'] and not method['mutationsDropped'],'Exact stated comparison scope')
 for name,path in [('scanner.py.txt','tests/report_guard_result_wire_reference_tests.py'),('support.py.txt','tests/diagnostic_wire_subtree_control_support.py')]:need((controls/name).read_bytes()==(ROOT/path).read_bytes(),'Exact exercised control source')
 equivalence=ROOT/'reports/diagnostic-wire-validation/run-20261106-subtree-control-equivalence-001/verification.json';e=read(equivalence);need(e['status']=='ALL17840_EXISTING_RESULT_CONTROLS_WHOLE_SCOPED_EQUIVALENCE_PASS' and e['sourceStable'],'Complete old full/scoped experiment')
 module=ROOT/n['extractorSource']['path'];need(stamp(module)==n['extractorSource'],'Actual parser exact');spec=importlib.util.spec_from_file_location('integration_argument_parser',module);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
 parent=read(ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-result-native-001/verification.json');results=n['assertionResults'];need(len(results)==130,'Every actual result record')
 configurations={};raw_receipts=[]
 for cfg in ['Release','Debug']:
  inventory_now=read(NATIVE/(cfg+'-inventory.stdout.txt'));arguments={t['name']:t['command'][1] for t in inventory_now['tests'] if 'command' in t}
  expected={r['name']:dict(binary=r['compiledBinary'],stdout=r['baseline']['path'],argument=arguments[r['name']]) for r in results if r['configuration']==cfg}
  old=set(parent['configurations'][cfg]['names']);new={'report_guard_result_wire',*('report_guard_result_wire_stop_'+str(i) for i in range(16))};need(len(expected)==65 and set(expected)==old|new,'All48 old and all17 new tests')
  commands=[v for v in n['commands'] if v['name'].startswith(cfg+'-ctest-')];need(len(commands)==34,'All actual CTest groups');actual=[]
  for command in commands:
   p=NATIVE/(command['name']+'.stdout.txt');raw=p.read_bytes();need(command['exitCode']==0 and not command['timedOut'] and len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'],'Actual CTest output exact')
   names=[v.decode() for v in re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',raw,re.M)];actual+=parser.parse(raw,{name:expected[name] for name in names});raw_receipts.append(stamp(p))
  need(len(actual)==len({r['name'] for r in actual})==65 and {r['name'] for r in actual}==set(expected),'Each CTest executed exactly once across original/continuations')
  for row in [r for r in results if r['configuration']==cfg]:need(stamp(ROOT/row['JSONText']['path'])==row['JSONText'],'Every stored canonical JSON text exact')
  stops=n['stopShards'][cfg];need(len(stops)==16 and sum(v['testedCallbackBoundaries'] for v in stops)==26175 and sum(v['stopAndExceptionCases'] for v in stops)==52350,'Every callback boundary and stop/exception case retained')
  audit=read(NATIVE/(cfg+'-actual-four-tu-audit.json'));need(audit['status']=='PASS' and audit['actualTUs']==4 and len(audit['sourceCommands'])==4,'Every actual source TU audited')
  configurations[cfg]=dict(actualPassed=65,actualNames=sorted(r['name'] for r in actual),old48Retained=True,actualStopExceptionCases=52350)
 need(n['all48OldRawFixturesExact'] and n['old20ProfilesRawExact'] and n['testOnlyIntervalTUs']==1 and n['newHarnessIntervalTU'] and n['allFourTranslationUnitsStrictFlagsIndividuallyAudited'] and not n['oldCoreBuiltOrLinked'] and not n['reusedCommandsReexecuted'],'Exact retained and compiled scope')
 for row in n['profiles']:
  p=ROOT/row['path'];need(stamp(p)==row and p.read_bytes()==(NATIVE/'old-profile-originals'/p.name).read_bytes(),'All old profile bytes')
 need(len(n['profiles'])==20,'All20 profiles')
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());result=dict(status='FINITE_GUARD_RESULT_INTEGRATION_PASS',nativeReceipt=stamp(NATIVE/'verification.json'),webReceipt=stamp(web),controlReceipt=stamp(controls/'verification.json'),equivalenceReceipt=stamp(equivalence),configurations=configurations,actualCTestOutputReceipts=raw_receipts,all130ActualAssertionRecordsRechecked=True,all65NamesCommandsAndArgumentsPerConfigurationExact=True,allRawCopiedOriginalsAndAliasesExact=True,all48OldRawFixturesExact=True,old20ProfilesRawExact=True,testedSourcesAndBaselineStable=True,testsRerun=False,newProductionTUs=2,newHarnessTUs=1,testOnlyIntervalTUs=1,actualGNUExecuted=False,fullReportMapped=False,CABIPumpImplemented=False)
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:result[k] for k in ['status','all130ActualAssertionRecordsRechecked','testsRerun']}))
if __name__=='__main__':main()
