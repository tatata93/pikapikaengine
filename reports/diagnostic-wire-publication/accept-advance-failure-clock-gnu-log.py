"""Accept actual GNU Failure/ClockAudit output against fixed feature Git blobs."""
from pathlib import Path
import argparse,base64,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-advance-failure-clock-gnu-actual-001'
def need(v,m):
 if not v:raise ValueError(m)
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine-run',required=True,type=int);p.add_argument('--job',required=True,type=int);a=p.parse_args()
 need(__debug__ and re.fullmatch('[0-9a-f]{40}',a.source) and min(a.engine_run,a.job)>0 and not OUT.exists(),'Fresh explicit provenance')
 raw=base64.b64decode((ROOT/'build/report-advance-failure-clock-gnu-diagnostic.base64').read_bytes());text=raw.decode('utf8');need(a.source in text,'Exact source in actual log')
 lines=[s.split('PIKAPIKA_REPORT_ADVANCE_FAILURE_CLOCK_WIRE=',1)[1] for s in text.splitlines() if 'PIKAPIKA_REPORT_ADVANCE_FAILURE_CLOCK_WIRE={' in s];need(len(lines)==1,'One actual final JSON');r=json.loads(lines[0])
 need(r['status']=='FINITE_GNU_REPORT_ADVANCE_FAILURE_CLOCK_PASS' and r['compiler']=='13.3.0' and r['target']=='x86_64-linux-gnu' and r['sourceStable'] and r['sourceBefore']==r['sourceAfter'],'Real GNU and stable success')
 required={'scripts/verify-diagnostic-wire.py','scripts/verify-report-advance-failure-clock-wire.py','scripts/verify-report-guard-failure-wire.py','scripts/verify-report-intervals-wire.py'}
 need(r['oracleSourceClosure']['status']=='PASS' and set(r['oracleSourceClosure']['required'])==required and len(r['sourceBefore'])==31 and required.issubset({s['path'] for s in r['sourceBefore']}),'Every actual oracle source')
 for s in r['sourceBefore']:
  b=subprocess.check_output(['git','show',a.source+':'+s['path']],cwd=ROOT);need(len(b)==s['bytes'] and hashlib.sha256(b).hexdigest()==s['sha256'],'Exact feature blob '+s['path'])
 commands=r['commands'];need(len(commands)==16 and len({c['name'] for c in commands})==16 and all(c['exitCode']==0 for c in commands),'All16 actual commands')
 native=json.loads((ROOT/'reports/diagnostic-wire-advance-failure-clock-verification.json').read_bytes());need(r['native']==native['native'] and r['reference']==native['reference'],'Every Native assertion and independent reference')
 for cfg in ['Release','Debug','Sanitized']:
  c=next(c for c in commands if c['name']==cfg+'-build');v=c['argv']
  need([Path(p).name for p in v if p.endswith('.cpp')]==['diagnostic_wire.cpp','report_values_wire.cpp','report_advance_failure_clock_wire_tests.cpp','interval.cpp'],'Exactly4 source TUs')
  need(not any(p.endswith(('.lib','.a','.so')) for p in v),'No numerical model library')
  for f in ['-std=c++20','-Werror','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-lto']:need(f in v,'Strict flags')
  if cfg=='Debug':need('-O0' in v and '-g' in v and '-DNDEBUG' not in v,'True Debug')
  if cfg=='Sanitized':
   for f in ['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-fno-omit-frame-pointer']:need(f in v,'All4 TUs instrumented')
  for suffix in ['run','fixture','reference']:need(sum(c['name']==cfg+'-'+suffix for c in commands)==1,'Every actual configuration command')
  c=next(c for c in commands if c['name']==cfg+'-fixture');need(c['stdoutBytes']==5183 and c['stdoutSha256']=='5012e5b95d0ab5b305e2bc58bf7d697c7d2dbf46f0ff00207c66753b834ec2ea','Whole fixture exact')
  if cfg=='Sanitized':need(all(c['sanitizerRuntimeOptions'] for c in commands if c['name'] in {cfg+'-run',cfg+'-fixture'}),'Actual sanitizer runtime options')
 controls=r['referenceControls'];need(controls['status']=='PASS' and controls['shards']==1 and controls['shard']==0 and controls['controlsDecoded']==controls['controlsConsidered']==3196 and controls['identicalFieldExchanges']==7 and controls['identicalArrayOrders']==controls['identicalVariantChildExchanges']==0,'All3196 changes;7 identical separated')
 local=json.loads((ROOT/'reports/diagnostic-wire-recipes/run-20261106-advance-failure-clock-controls-001/verification.json').read_bytes())
 for k,v in local.items():
  if k.endswith(('Mutations','Rejections','Exchanges','Orders','PairsConsidered','ChildPairs')):need(controls[k]==v,'Every finite control category exact '+k)
 need(r['schemaControls']['accepted']==1 and r['schemaControls']['refused']==20 and r['schemaControls']['mappedTypes']==99 and r['schemaControls']['mappedFields']==581,'Actual schema gate')
 need(r['wholeRawExact'] and r['allNewTranslationUnitsInstrumented'] and r['newHarnessIntervalTU'] and r['oldIntervalTUInstrumentedForHarness'] and r['testOnlyIntervalTUs']==1 and not r['oldCoreBuiltOrLinked'],'Finite compiled scope')
 OUT.mkdir(parents=True);log=OUT/'diagnostic-job-decoded.log.txt';log.write_bytes(raw);actual=OUT/'actual-advance-failure-clock-verification.json';actual.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
 result=dict(schema=1,status='FINITE_ACTUAL_GNU_REPORT_ADVANCE_FAILURE_CLOCK_PASS',source=a.source,engineRun=a.engine_run,job=a.job,sourceFilesChecked=31,regularCommands=16,actualDebugAndAllFourSourceO1AsanUbsan=True,wholeNativeGnuThreeConfigurationsRawExact=True,native=r['native'],reference=r['reference'],decodedLog=stamp(log),actualRecord=stamp(actual),childRawAndObjectsTransferred=False,fullReportMapped=False,CABIPumpImplemented=False)
 (ROOT/'reports/diagnostic-wire-advance-failure-clock-gnu-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status=result['status'],sourceFilesChecked=31)))
if __name__=='__main__':main()
