"""Recheck actual47 CTest identities/JSON, raw fixtures and immutable proof sources without running Cpp tests again."""
from pathlib import Path
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-preparation-snapshot-inventory-native-001'
NATIVE=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-snapshot-inventory-native-001'
def need(v,m):
 if not v:raise ValueError(m)
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_bytes())
def main():
 need(__debug__ and not OUT.exists(),'Fresh integration');n=read(NATIVE/'verification.json');need(n['status']=='FINITE_NATIVE_REPORT_PREPARATION_SNAPSHOT_INVENTORY_PASS' and n['sourceStable'] and n['protectedRawExact'] and n['baselineRawStable'],'Actual full Native first')
 need(n['selectedCTestPerConfiguration']==47 and n['registeredTests']==dict(Release=104,Debug=102) and n['protectedFiles']==399,'Actual finite Native counts')
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
 for file in ['source-before.json','protected-before.json','baseline-before.json']:
  for row in read(NATIVE/file):need(stamp(ROOT/row['path'])==row,'Exact tested/protected/baseline bytes')
 web=ROOT/'reports/diagnostic-wire-integration/run-20261106-preparation-snapshot-inventory-web-001/verification.json';w=read(web);need(w['status']=='FINITE_PREPARATION_SNAPSHOT_INVENTORY_WEB_PASS' and w['schemaControls']['mappedTypes']==95 and w['schemaControls']['mappedFields']==554 and w['schemaControls']['accepted']==1 and w['schemaControls']['refused']==20,'Actual Web/header controls')
 controls=ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-snapshot-inventory-controls-001';cmd=read(controls/'command.json');raw=(controls/'stdout.json').read_bytes();need(cmd['exitCode']==0 and len(raw)==cmd['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==cmd['stdoutSha256'],'Actual complete mutation output')
 c=json.loads(raw);need(c['status']=='PASS' and c['shards']==1 and c['controlsDecoded']==c['controlsConsidered']==5537 and c['baseline']==n['reference'],'Complete unsharded grammar-valid controls')
 need((controls/'scanner.py.txt').read_bytes()==(ROOT/'tests/report_preparation_snapshot_inventory_wire_reference_tests.py').read_bytes(),'Exercised scanner exact')
 module=ROOT/n['extractorSource']['path'];need(stamp(module)==n['extractorSource'],'Exact actual extractor');spec=importlib.util.spec_from_file_location('integration_parser',module);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
 parent=read(ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-pair-values-native-001/verification.json');results=n['assertionResults'];need(len(results)==94,'All94 actual result records')
 configurations={};receipts=[]
 for cfg in ['Release','Debug']:
  expected={r['name']:dict(binary=r['compiledBinary'],stdout=r['baseline']['path']) for r in results if r['configuration']==cfg};old=set(parent['configurations'][cfg]['names']);need(len(expected)==47 and set(expected)==old|{'report_preparation_snapshot_inventory_wire'},'All46 old plus exactly1 new')
  commands=[r for r in n['commands'] if r['name'].startswith(cfg+'-ctest-')];need(len(commands)==16,'All actual finite CTest groups');actual=[]
  for command in commands:
   p=NATIVE/(command['name']+'.stdout.txt');raw=p.read_bytes();need(command['exitCode']==0 and not command['timedOut'] and len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'],'Actual CTest output framing')
   import re
   names=re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',raw,re.M);rows=parser.parse(raw,{name.decode():expected[name.decode()] for name in names});actual.extend(r['name'] for r in rows);receipts.append(stamp(p))
  need(len(actual)==len(set(actual))==47 and set(actual)==set(expected),'Every selected test executed once')
  for row in [r for r in results if r['configuration']==cfg]:need(stamp(ROOT/row['JSONText']['path'])==row['JSONText'],'Exact stored normalized assertion text')
  configurations[cfg]=dict(actualPassed=47,actualNames=sorted(actual),allOld46Retained=True)
 need(n['all46OldRawFixturesExact'] and n['old20ProfilesRawExact'] and not n['oldDirectRunCommandsReexecuted'] and not n['oldDirectRunRawStdoutEquivalenceClaim'] and not n['newHarnessIntervalTU'] and n['testOnlyIntervalTUs']==0,'Exact retained scope')
 profiles=[]
 for row in n['profiles']:
  p=ROOT/row['path'];need(stamp(p)==row and p.read_bytes()==(NATIVE/'old-profile-originals'/p.name).read_bytes(),'All original profile bytes retained');profiles.append(row)
 need(len(profiles)==20,'All20 profiles')
 r=dict(status='FINITE_PREPARATION_SNAPSHOT_INVENTORY_INTEGRATION_PASS',nativeReceipt=stamp(NATIVE/'verification.json'),webReceipt=stamp(web),referenceControls={k:v for k,v in c.items() if k!='mutations'},configurations=configurations,actualCTestOutputReceipts=receipts,all47ActualNamesCommandsAndJSONTextRechecked=True,old46RawFixturesExact=True,old20ProfilesRawExact=True,testedSourcesAndBaselineStable=True,oldDirectRunRawStdoutEquivalenceClaim=False,testsRerun=False,newTargetTUs=3,fullReportMapped=False,CABIPumpImplemented=False,actualGNUExecuted=False)
 (OUT/'verification.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:r[k] for k in ['status','all47ActualNamesCommandsAndJSONTextRechecked','old20ProfilesRawExact','testsRerun']}))
if __name__=='__main__':main()
