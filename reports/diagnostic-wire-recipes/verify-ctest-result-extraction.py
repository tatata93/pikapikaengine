"""Finite three-test experiment only; does not replace any active Native acceptance."""
from pathlib import Path
import hashlib,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-validation/run-20261106-ctest-extraction-001'
PRIOR=ROOT/'reports/diagnostic-wire-recipes/run-20261106-guard-child-variant-native-001'
BUILD=ROOT/'build/wfdgch2'
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert __debug__ and not OUT.exists();OUT.mkdir(parents=True)
 (OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());parent=json.loads((PRIOR/'verification.json').read_bytes());assert parent['status']=='FINITE_NATIVE_REPORT_GUARD_CHILD_VARIANT_PASS'
 expected={'diagnostic_wire':('pikapika_diagnostic_wire_tests','Release-old-primitive-run.stdout.txt'),'diagnostic_wire_rejection':('pikapika_diagnostic_wire_rejection_tests','Release-old-rejection-run.stdout.txt'),'report_values_wire':('pikapika_report_values_wire_tests','Release-old-values-run.stdout.txt')}
 binaries=[BUILD/'Release'/(target+'.exe') for target,_ in expected.values()];before=[stamp(p) for p in binaries]
 args=['ctest','--test-dir',str(BUILD),'-C','Release','-R','^(diagnostic_wire|diagnostic_wire_rejection|report_values_wire)$','-V','--output-on-failure']
 start=time.monotonic();p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60)
 (OUT/'ctest.stdout.txt').write_bytes(p.stdout);(OUT/'ctest.stderr.txt').write_bytes(p.stderr)
 command=dict(argv=args,exitCode=p.returncode,seconds=time.monotonic()-start,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest());(OUT/'ctest.command.json').write_text(json.dumps(command,indent=2)+'\n',encoding='utf8');assert p.returncode==0
 text=p.stdout.decode('utf8');started=re.findall(r'^\s*Start\s+(\d+):\s+(\S+)\s*$',text,re.M)
 passed=re.findall(r'^\s*\d+/\d+\s+Test\s+#(\d+):\s+(\S+)\s+\.+\s+Passed\s+',text,re.M)
 assert started==passed and len(started)==3 and {n for _,n in started}==set(expected)
 assert re.findall(r'(\d+)% tests passed, (\d+) tests failed out of (\d+)',text)==[('100','0','3')]
 payloads=re.findall(rb'^\s*(\d+): (\{[^\r\n]*\})\r?$',p.stdout,re.M);assert len(payloads)==3 and len({v[0] for v in payloads})==3
 records=[]
 for number,name in started:
  payload=next(raw for i,raw in payloads if i.decode()==number);target,old=expected[name];old_path=PRIOR/old;raw=old_path.read_bytes()
  assert json.loads(payload)==json.loads(raw) and payload==raw.rstrip(b'\r\n')
  lines=[line for line in text.splitlines() if line.startswith(number+': Test command: ')]
  assert len(lines)==1 and target+'.exe' in lines[0] and '--run' in lines[0]
  records.append(dict(name=name,ctestNumber=int(number),originalRun=stamp(old_path),parsedAssertionObjectExact=True,JSONTextExactIgnoringLineTerminators=True,rawDirectStdoutTransferClaim=False))
 after=[stamp(p) for p in binaries];assert before==after
 costs={k:sum(v['seconds'] for v in parent['commands'] if pred(v['name'])) for k,pred in [('ctest',lambda s:'-ctest-' in s),('separateOldRun',lambda s:'-old-' in s and s.endswith('-run'))]}
 result=dict(schema=1,status='THREE_TEST_CTEST_EXTRACTION_EXPERIMENT_PASS_ONLY',records=records,command=command,selectedTests=3,allActualStartsAndPassesAccounted=True,retainedCompiledBinariesStable=True,before=before,after=after,previousNativeMeasuredSeconds=costs,currentActivePairRecordAcceptanceModified=False,all45TestExtractorAccepted=False,oldDirectStdoutRawExactClaim=False,scope='One actual verbose CTest invocation of3 old diagnostics in a distinct completed build. JSON text excluding line terminators and all assertion objects match retained direct-run records. Current PairRecord Native suite unchanged. No all-suite adoption, raw direct-stdout transfer equivalence, or measured future speedup claim.')
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','selectedTests','currentActivePairRecordAcceptanceModified','all45TestExtractorAccepted','previousNativeMeasuredSeconds']}))
if __name__=='__main__':main()
