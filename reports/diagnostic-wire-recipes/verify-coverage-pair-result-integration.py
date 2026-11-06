"""Complete Native pair Result integration after actual builds and all control shards; preserve old data libraries and profiles."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-pair-result-native-002'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh final integration');OUT.mkdir(parents=True)
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-pair-result-native-002/verification.json';n=json.loads(native.read_bytes());need(n['status']=='FINITE_NATIVE_REPORT_COVERAGE_PAIR_RESULT_PASS','Actual complete Native acceptance first')
    web=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-pair-result-web-002/verification.json';w=json.loads(web.read_bytes());need(w['status']=='FINITE_COVERAGE_PAIR_RESULT_WEB_PASS','Actual web/schema acceptance')
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native.parent/name).read_bytes()):need(stamp(ROOT/row['path'])==row,'Native tested/protected bytes unchanged')
    sources=[ROOT/p for p in ['tests/report_coverage_pair_result_wire_reference_tests.py','scripts/verify-report-coverage-pair-result-wire.py','scripts/verify-diagnostic-wire.py','scripts/verify-report-coverage-snapshot-wire.py','scripts/verify-report-coverage-audit-partition-wire.py','scripts/verify-report-coverage-cell-work-wire.py']];before=[stamp(p) for p in sources]
    shard_dir=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-pair-result-shards-001'
    need((shard_dir/'scanner.py.txt').read_bytes()==sources[0].read_bytes(),'Exact exercised control source')
    early=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-pair-result-early-001/fixture.stdout.hex.txt'
    need(early.read_bytes()==(native.parent/'Release-fixture.stdout.hex.txt').read_bytes(),'All sharded controls exercised exact fresh Native fixture')
    shards=[]
    for i in range(8):
        raw=(shard_dir/(str(i)+'.stdout.json')).read_bytes()
        command=json.loads((shard_dir/(str(i)+'.command.json')).read_bytes())
        need(command['exitCode']==0 and len(raw)==command['stdoutBytes'] and hashlib.sha256(raw).hexdigest()==command['stdoutSha256'],'Actual shard output receipt')
        child=json.loads(raw);need(child['status']=='PASS_SHARD' and child['shard']==i and child['shards']==8 and child['baseline']==n['reference'],'Explicit distinct shard and full baseline')
        need(child['controlsDecoded']==len(range(i,child['controlsConsidered'],8)),'Every assigned control decoded')
        shards.append(child)
    summary=json.loads((shard_dir/'verification.json').read_bytes())
    need(summary['status']=='PASS' and summary['allEightShardsAccepted'] and sum(c['controlsDecoded'] for c in shards)==summary['controlsConsidered']==summary['controlsDecoded'],'No omitted or double-counted control')
    comparable=[{k:v for k,v in c.items() if k not in ['shard','controlsDecoded','mutations']} for c in shards]
    need(all(c==comparable[0] for c in comparable),'All source boundaries and totals identical')
    controls=summary
    args=['all8-bounded-shards-already-executed',str(shard_dir)]
    expected={'wellFormedSingleByteMutations': 16856, 'recordOrderCountRejections': 3, 'absentToNullRejections': 126, 'presentToAbsentOrNullRejections': 262, 'enumToU32Rejections': 168, 'fieldValueExchangeRejections': 2508, 'objectFieldOrderRejections': 303, 'arrayOrderCountRejections': 523, 'variantOrdinalByteMutations': 32, 'variantToPresentRejections': 8, 'variantWrapperRemovalRejections': 8, 'variantChildExchangeRejections': 24, 'messageLengthRejections': 33, 'identicalFieldExchanges': 53, 'identicalArrayOrders': 3, 'identicalVariantChildExchanges': 4, 'controlsConsidered': 20854, 'controlsDecoded': 20854}
    need(all(controls[k]==v for k,v in expected.items()) and controls['baseline']==n['reference'],'Exact independent variant/child/tag controls')
    links=[]
    for cfg in ['Release','Debug']:
        log=next((ROOT/'build/wfdcpr2/pikapika_report_coverage_pair_result_wire_tests.dir'/cfg).rglob('link.command.1.tlog'));raw=log.read_bytes();text=raw.decode('utf16').upper()
        inputs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text);actual=[s.strip('"').replace('\\','/').split('/')[-1] for s in inputs]
        windows=['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB']
        need(sorted(actual)==sorted(windows+['PIKAPIKA_DIAGNOSTIC_WIRE.LIB','PIKAPIKA_REPORT_VALUES_WIRE.LIB']),'Only2 data and Windows libraries')
        (OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(raw);links.append(dict(configuration=cfg,inputLibraries=actual))
    profiles=[]
    for p in sorted((ROOT/'build/wfdcpr2').glob('*.json')):
        prior=ROOT/'build/wfdv1'/p.name
        if prior.is_file():need(p.read_bytes()==prior.read_bytes(),'Old profile exact '+p.name);profiles.append(p.name)
    need(len(profiles)==20,'All20 original profiles');after=[stamp(p) for p in sources];need(before==after,'Reference sources stable')
    result=dict(status='FINITE_COVERAGE_PAIR_RESULT_INTEGRATION_PASS',nativeReceipt=stamp(native),webReceipt=stamp(web),referenceControls={k:v for k,v in controls.items() if k!='mutations'},
        referenceCommand=dict(argv=list(map(str,args)),exitCode=0),sourceBefore=before,sourceAfter=after,sourceStable=True,linkAudit=links,old20ProfilesRawExact=True,fullReportMapped=False,CABIPumpImplemented=False,actualGNUExecuted=False)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','old20ProfilesRawExact','sourceStable']}))
if __name__=='__main__':main()
