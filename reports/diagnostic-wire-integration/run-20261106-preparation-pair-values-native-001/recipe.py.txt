"""Recheck actual46 CTest identities/JSON, raw fixtures and immutable proof sources without running Cpp tests again."""
from pathlib import Path
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-preparation-pair-values-native-001'
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-pair-values-native-001'
def need(v,m):
 if not v:raise ValueError(m)
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_bytes())
def main():
 need(__debug__ and not OUT.exists(),'Fresh integration');n=read(NATIVE/'verification.json');need(n['status']=='FINITE_NATIVE_REPORT_PREPARATION_PAIR_VALUES_PASS' and n['sourceStable'] and n['protectedRawExact'] and n['baselineRawStable'],'Actual full Native first')
 need(n['selectedCTestPerConfiguration']==46 and n['registeredTests']==dict(Release=103,Debug=101) and n['protectedFiles']==397,'Actual finite Native counts')
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
 for file in ['source-before.json','protected-before.json','baseline-before.json']:
  for row in read(NATIVE/file):need(stamp(ROOT/row['path'])==row,'Exact tested/protected/baseline bytes')
 web=ROOT/'reports/diagnostic-wire-integration/run-20261106-preparation-pair-values-web-001/verification.json';w=read(web);need(w['status']=='FINITE_PREPARATION_PAIR_VALUES_WEB_PASS' and w['schemaControls']['mappedTypes']==93 and w['schemaControls']['mappedFields']==541 and w['schemaControls']['accepted']==1 and w['schemaControls']['refused']==20,'Actual Web/header controls')
 controls=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-pair-values-controls-001';cmd=read(controls/'command.json');raw=(controls/'stdout.json').read_bytes();need(cmd['exitCode']==0 and len(raw)==cmd['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==cmd['stdoutSha256'],'Actual complete mutation output')
 c=json.loads(raw);need(c['status']=='PASS' and c['shards']==1 and c['controlsDecoded']==c['controlsConsidered']==1737 and c['baseline']==n['reference'],'Complete unsharded grammar-valid controls')
 need((controls/'scanner.py.txt').read_bytes()==(ROOT/'tests/report_preparation_pair_values_wire_reference_tests.py').read_bytes(),'Exercised scanner exact')
 module=ROOT/n['extractorSource']['path'];need(stamp(module)==n['extractorSource'],'Exact actual extractor');spec=importlib.util.spec_from_file_location('integration_parser',module);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
 parent=read(ROOT/'reports/diagnostic-wire-integration/run-20261106-guard-pair-record-selected-ctest-001/verification.json');results=n['assertionResults'];need(len(results)==92,'All92 actual result records')
 configurations={};receipts=[]
 for cfg in ['Release','Debug']:
  expected={r['name']:dict(binary=r['compiledBinary'],stdout=r['baseline']['path']) for r in results if r['configuration']==cfg};old=set(parent['configurations'][cfg]['actualNames']);need(len(expected)==46 and set(expected)==old|{'report_preparation_pair_values_wire'},'All45 old plus exactly1 new')
  commands=[r for r in n['commands'] if r['name'].startswith(cfg+'-ctest-')];need(len(commands)==15,'All actual finite CTest groups');actual=[]
  for command in commands:
   p=NATIVE/(command['name']+'.stdout.txt');raw=p.read_bytes();need(command['exitCode']==0 and not command['timedOut'] and len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'],'Actual CTest output framing')
   import re
   names=re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',raw,re.M);rows=parser.parse(raw,{name.decode():expected[name.decode()] for name in names});actual.extend(r['name'] for r in rows);receipts.append(stamp(p))
  need(len(actual)==len(set(actual))==46 and set(actual)==set(expected),'Every selected test executed once')
  for row in [r for r in results if r['configuration']==cfg]:need(stamp(ROOT/row['JSONText']['path'])==row['JSONText'],'Exact stored normalized assertion text')
  configurations[cfg]=dict(actualPassed=46,actualNames=sorted(actual),allOld45Retained=True)
 need(n['all45OldRawFixturesExact'] and n['old20ProfilesRawExact'] and not n['oldDirectRunCommandsReexecuted'] and not n['oldDirectRunRawStdoutEquivalenceClaim'] and not n['newHarnessIntervalTU'] and n['testOnlyIntervalTUs']==0,'Exact retained scope')
 profiles=[]
 for row in n['profiles']:
  p=ROOT/row['path'];need(stamp(p)==row and p.read_bytes()==(NATIVE/'old-profile-originals'/p.name).read_bytes(),'All original profile bytes retained');profiles.append(row)
 need(len(profiles)==20,'All20 profiles')
 r=dict(status='FINITE_PREPARATION_PAIR_VALUES_INTEGRATION_PASS',nativeReceipt=stamp(NATIVE/'verification.json'),webReceipt=stamp(web),referenceControls={k:v for k,v in c.items() if k!='mutations'},configurations=configurations,actualCTestOutputReceipts=receipts,all46ActualNamesCommandsAndJSONTextRechecked=True,old45RawFixturesExact=True,old20ProfilesRawExact=True,testedSourcesAndBaselineStable=True,oldDirectRunRawStdoutEquivalenceClaim=False,testsRerun=False,newTargetTUs=3,fullReportMapped=False,CABIPumpImplemented=False,actualGNUExecuted=False)
 (OUT/'verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:r[k] for k in ['status','all46ActualNamesCommandsAndJSONTextRechecked','old20ProfilesRawExact','testsRerun']}))
if __name__=='__main__':main()
