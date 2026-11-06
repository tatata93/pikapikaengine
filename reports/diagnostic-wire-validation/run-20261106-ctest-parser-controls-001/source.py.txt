"""Prepared45-test verbose-output experiment; require committed, completed PairRecord acceptance first."""
from pathlib import Path
import hashlib,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-pair-record-native-001'
AUDIT=ROOT/'reports/diagnostic-wire-integration/run-20261106-guard-pair-record-selected-ctest-001/verification.json'
FORMAL=ROOT/'reports/diagnostic-wire-guard-pair-record-verification.json'
OUT=ROOT/'reports/diagnostic-wire-validation/run-20261106-pair-record-ctest-extraction-001'
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def parse(raw,expected):
 text=raw.decode('utf8');starts=re.findall(r'^\s*Start\s+(\d+):\s+(\S+)\s*$',text,re.M)
 passed=re.findall(r'^\s*\d+/\d+\s+Test\s+#(\d+):\s+(\S+)\s+\.+\s+Passed\s+',text,re.M)
 assert starts==passed and len(starts)==len(expected) and len({i for i,_ in starts})==len(starts) and {n for _,n in starts}==set(expected)
 assert re.findall(r'(\d+)% tests passed, (\d+) tests failed out of (\d+)',text)==[('100','0',str(len(expected)))]
 payloads=re.findall(rb'^\s*(\d+): (\{[^\r\n]*\})\r?$',raw,re.M)
 assert len(payloads)==len(starts) and {i.decode() for i,_ in payloads}=={i for i,_ in starts}
 records=[]
 for number,name in starts:
  payload=next(value for i,value in payloads if i.decode()==number);row=expected[name];prior=(ROOT/row['stdout']).read_bytes()
  assert payload==prior.rstrip(b'\r\n') and json.loads(payload)==json.loads(prior)
  commands=[line for line in text.splitlines() if line.startswith(number+': Test command: ')]
  assert commands==[number+': Test command: '+row['binary']+' "--run"']
  records.append(dict(name=name,ctestNumber=int(number),originalStdout=stamp(ROOT/row['stdout']),allJSONTextExceptLineTerminatorsExact=True))
 return records
def main():
 assert __debug__ and not OUT.exists()
 source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 for p in [FORMAL,PARENT/'verification.json',AUDIT]:
  assert subprocess.check_output(['git','show',source+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT)==p.read_bytes(),'Committed completed PairRecord first'
 formal=json.loads(FORMAL.read_bytes());native=json.loads((PARENT/'verification.json').read_bytes());audit=json.loads(AUDIT.read_bytes())
 assert formal['status']==native['status']=='FINITE_NATIVE_REPORT_GUARD_PAIR_RECORD_PASS' and native['sourceStable'] and native['protectedRawExact'] and formal['selectedCTestPerConfiguration']==45
 assert audit['status']=='ACTUAL_SELECTED_CTEST_OUTPUT_PASS' and not audit['testsRerun']
 OUT.mkdir(parents=True);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());commands=[];configurations={};binary_paths=set();artifacts=[FORMAL,PARENT/'verification.json',AUDIT];expected_all={}
 for cfg in ['Release','Debug']:
  names=set(audit['configurations'][cfg]['actualNames']);assert len(names)==45
  inv=PARENT/(cfg+'-inventory.stdout.txt');artifacts.append(inv);inventory=json.loads(inv.read_bytes());expected={}
  for test in inventory['tests']:
   if test['name'] not in names:continue
   argv=test['command'];assert len(argv)==2 and argv[1]=='--run';binary=Path(argv[0]).resolve();assert binary.parent==ROOT/'build/wfdgpr3'/cfg and binary.suffix=='.exe'
   matches=[c for c in native['commands'] if c['name'].startswith(cfg+'-') and c['name'].endswith('-run') and len(c['argv'])==2 and Path(c['argv'][0]).resolve()==binary and c['argv'][1]=='--run']
   assert len(matches)==1;path=PARENT/(matches[0]['name']+'.stdout.txt');raw=path.read_bytes();assert len(raw)==matches[0]['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==matches[0]['stdoutSha256']
   expected[test['name']]=dict(binary=str(binary),stdout=path.relative_to(ROOT).as_posix());binary_paths.add(binary);artifacts.append(path)
  assert set(expected)==names;expected_all[cfg]=expected
 before=[stamp(p) for p in sorted(binary_paths|set(artifacts))];result=dict(schema=1,status='FAIL',source=source,scope=__doc__)
 try:
  negatives=0
  for cfg,expected in expected_all.items():
   groups=[c for c in native['commands'] if c['name'].startswith(cfg+'-ctest-')];assert len(groups)==14;selected=[]
   for index,parent in enumerate(groups):
    argv=parent['argv']+['-V'];start=time.monotonic();p=subprocess.Popen(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE);timed_out=False
    try:stdout,stderr=p.communicate(timeout=240)
    except subprocess.TimeoutExpired:
     timed_out=True;cleanup=subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15);(OUT/(cfg+'-'+str(index)+'.timeout-cleanup.txt')).write_bytes(cleanup.stdout+cleanup.stderr);stdout,stderr=p.communicate(timeout=15)
    name=cfg+'-'+str(index);(OUT/(name+'.stdout.txt')).write_bytes(stdout);(OUT/(name+'.stderr.txt')).write_bytes(stderr)
    command=dict(name=name,argv=argv,exitCode=p.returncode,timedOut=timed_out,seconds=time.monotonic()-start,timeoutSeconds=240,stdoutBytes=len(stdout),stdoutSha256=hashlib.sha256(stdout).hexdigest());commands.append(command);(OUT/(name+'.command.json')).write_text(json.dumps(command,indent=2)+'\n',encoding='utf8');assert not timed_out and p.returncode==0
    names=re.findall(rb'^\s*Start\s+\d+:\s+(\S+)\s*$',stdout,re.M);group_expected={name.decode():expected[name.decode()] for name in names};records=parse(stdout,group_expected);selected.extend(records)
    if index==0:
     payload=re.search(rb'^\s*\d+: (\{[^\r\n]*\})\r?$',stdout,re.M);assert payload
     whole=payload[0];first=records[0];binary=group_expected[first['name']]['binary'].encode();passed=re.search(rb'^\s*\d+/\d+\s+Test\s+#\d+:\s+\S+\s+\.+\s+Passed[^\r\n]*',stdout,re.M);assert passed
     controls=[stdout.replace(whole,b'',1),stdout+b'\n'+whole,stdout.replace(whole,b'999999: '+payload[1],1),stdout.replace(b'"status":"PASS"',b'"status":"FAIL"',1),stdout.replace(binary,b'wrong-executable.exe',1),stdout[:passed.start()]+stdout[passed.end():],stdout.replace(b'100% tests passed',b'99% tests passed',1)]
     for changed in controls:
      assert changed!=stdout
      try:parse(changed,group_expected)
      except (AssertionError,ValueError,StopIteration):negatives+=1
      else:raise AssertionError('Corrupted captured CTest log accepted')
   assert len(selected)==45 and {r['name'] for r in selected}==set(expected);configurations[cfg]=dict(actualPassed=45,records=selected)
  assert negatives==14
  result.update(status='ALL45_TWO_CONFIGURATION_CTEST_EXTRACTION_EXPERIMENT_PASS_ONLY',configurations=configurations,capturedLogNegativeRefusals=negatives,allActualNamesCommandsAndJSONTextExact=True,currentNativeRecipesModified=False,directStdoutRawTransferEquivalenceClaim=False,allProtocolFixturesStillSeparate=True,futureMeasuredSpeedupClaim=False)
 except BaseException as e:result['error']=type(e).__name__+': '+str(e)
 after=[stamp(p) for p in sorted(binary_paths|set(artifacts))];result.update(commands=commands,before=before,after=after,artifactsAndCompiledBinariesStable=before==after)
 if before!=after:result['status']='FAIL'
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','error','source','capturedLogNegativeRefusals','currentNativeRecipesModified'] if k in result}));return int(result['status']!='ALL45_TWO_CONFIGURATION_CTEST_EXTRACTION_EXPERIMENT_PASS_ONLY')
if __name__=='__main__':raise SystemExit(main())
