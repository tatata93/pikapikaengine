"""Accept exact-source Native/GNU/Pages/manifest/seven transfers/UI, separate from pending all19 CI."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-publication/run-20261106-advance-commit-ledgers-public-review-001'
def need(v,m):
 if not v:raise ValueError(m)
def read(p):return json.loads(p.read_bytes())
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine-run',required=True,type=int);p.add_argument('--pages-run',required=True,type=int);args=p.parse_args();need(__debug__ and re.fullmatch('[0-9a-f]{40}',args.source) and min(args.engine_run,args.pages_run)>0 and not OUT.exists(),'Fresh exact provenance')
 paths=dict(native=ROOT/'reports/diagnostic-wire-advance-commit-ledgers-verification.json',gnu=ROOT/'reports/diagnostic-wire-advance-commit-ledgers-gnu-verification.json',jobs=ROOT/'reports/world-static-mesh-flight-advance-public-checks/run-20261106-advance-commit-ledgers-public-ready-001/result.json',manifest=ROOT/'reports/pages-deployment/run-20261106-advance-commit-ledgers-public-001/receipt.json',samples=ROOT/'reports/pages-deployment/run-20261106-advance-commit-ledgers-public-samples-001/verification.json',archive=ROOT/'reports/pages-deployment/run-20261106-advance-commit-ledgers-archive-actual-001/actual-archive-verification.json',archiveProvenance=ROOT/'reports/pages-deployment/run-20261106-advance-commit-ledgers-archive-actual-001/provenance.json',ui=ROOT/'reports/diagnostic-wire-learning/run-20261106-advance-commit-ledgers-public-001/observation.json')
 n,g,j,m,s,a,u=[read(paths[k]) for k in ['native','gnu','jobs','manifest','samples','archive','ui']]
 need(n['status']=='FINITE_NATIVE_REPORT_ADVANCE_COMMIT_LEDGERS_PASS' and n['totalMappedRecordTypes']==101 and n['totalMappedFields']==600 and n['selectedCTestPerConfiguration']==67,'Complete Native101 first')
 need(g['status']=='FINITE_ACTUAL_GNU_REPORT_ADVANCE_COMMIT_LEDGERS_PASS' and g['source']==args.source and g['sourceFilesChecked']==28,'Actual exact-source GNU')
 need(j['feature']==args.source and j['runs']['engine']['id']==args.engine_run and j['runs']['pages']['id']==args.pages_run and len(j['runs']['engine']['jobs'])==19,'Exact run/head linkage')
 need(next(v for v in j['runs']['engine']['jobs'] if v['id']==g['job'])['conclusion']=='success' and j['runs']['pages']['conclusion']=='success','Actual new diagnostic and Pages jobs succeeded')
 need(m['status']=='PASS' and m['source']==args.source and s['source']==args.source and s['allSevenBytesExact'] and not s['allSelectedPayloadsTransferred'],'Actual manifest and seven transferred whole files')
 need(a['status']=='PASS' and a['selectedFiles']==m['selectedFiles'] and a['selectedBytes']==m['selectedBytes'] and a['manifest']['sha256']==m['manifestSha256'],'Actual archive and manifest agree')
 need(u['source']==args.source and u['publicReady'] and u['launchEnabled'] and u['diagramVisuallyInspected'] and not u['performanceBenchmark'],'Actual public READY and original diagram')
 native=(ROOT/n['nativeReceipt']['path']).parent;checked={};rows=0
 for name in ['source-before.json','protected-before.json']:
  for row in read(native/name):
   raw=subprocess.check_output(['git','show',args.source+':'+row['path']],cwd=ROOT);need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'Exact tested/protected feature blob '+row['path']);checked[row['path']]=row;rows+=1
 need(len(checked)==473,'Every unique Native tested/protected source file')
 all_ci=j['runs']['engine']['conclusion']=='success' and all(v['conclusion']=='success' for v in j['runs']['engine']['jobs'])
 result=dict(schema=1,status='FINITE_ADVANCE_COMMIT_LEDGERS_NATIVE_GNU_PUBLIC_READY_ALL19_CI_PASS' if all_ci else 'FINITE_ADVANCE_COMMIT_LEDGERS_NATIVE_GNU_PUBLIC_READY_ENGINE_PENDING',source=args.source,totalMappedRecordTypes=101,totalMappedFields=600,totalMappedVariants=2,**{k:stamp(path) for k,path in paths.items()},engineRun=args.engine_run,engineJobCount=19,allEngineJobsAccepted=all_ci,pagesRun=args.pages_run,pagesSuccess=True,publicReady=True,launchEnabled=True,nativeTestedAndProtectedUniqueGitBlobsChecked=len(checked),nativeTestedAndProtectedRowsChecked=rows,allDeclaredMetadataFixedGitExact=True,actualSevenHTTPWholeBytesExact=True,allHTTPPayloadsTransferred=False,archiveTransferred=False,newGetterConnectedToWASMOrGame=False,fullReportMapped=False,CABIPumpImplemented=False,launchURL='https://tatata93.github.io/pikapikaengine/?v='+args.source[:8],scope='Actual101 Native/GNU, Pages/archive/manifest/seven transfers/public UI accepted. All19 engine jobs remain separately tracked until actual final success. Every declared inventory hash matches fixed Git; all selected payloads were not transferred. No new numeric model, game feature or performance claim.')
 target=ROOT/'reports/diagnostic-wire-advance-commit-ledgers-public-verification.json';need(not target.exists(),'New receipt only');OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:result[k] for k in ['status','nativeTestedAndProtectedUniqueGitBlobsChecked','allEngineJobsAccepted','publicReady']}))
if __name__=='__main__':main()
