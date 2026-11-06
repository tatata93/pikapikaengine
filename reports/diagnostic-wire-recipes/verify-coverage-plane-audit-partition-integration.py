"""Complete Native plane Audit/Partition integration, valid Interval sources and all independent controls."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-plane-audit-partition-native-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh final integration');OUT.mkdir(parents=True)
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-coverage-plane-audit-partition-native-001/verification.json';n=json.loads(native.read_bytes());need(n['status']=='FINITE_NATIVE_REPORT_COVERAGE_PLANE_AUDIT_PARTITION_PASS','Actual complete Native acceptance first')
    web=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-plane-audit-partition-web-001/verification.json';w=json.loads(web.read_bytes());need(w['status']=='FINITE_COVERAGE_PLANE_AUDIT_PARTITION_WEB_PASS','Actual web/schema acceptance')
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native.parent/name).read_bytes()):need(stamp(ROOT/row['path'])==row,'Native tested/protected bytes unchanged')
    sources=[ROOT/p for p in ['tests/report_coverage_plane_audit_partition_wire_reference_tests.py','scripts/verify-report-coverage-plane-audit-partition-wire.py','scripts/verify-diagnostic-wire.py']];before=[stamp(p) for p in sources]
    args=[sys.executable,'-B','-X','utf8','tests/report_coverage_plane_audit_partition_wire_reference_tests.py',native.parent/'Release-fixture.stdout.hex.txt','--hex'];p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,timeout=120)
    (OUT/'reference-controls.stdout.txt').write_bytes(p.stdout);(OUT/'reference-controls.stderr.txt').write_bytes(p.stderr);need(p.returncode==0,'Actual complete controls');controls=json.loads(p.stdout)
    expected={'wellFormedSingleByteMutations': 5560, 'recordOrderCountRejections': 3, 'absentToNullRejections': 44, 'presentToAbsentOrNullRejections': 80, 'enumToU32Rejections': 64, 'endpointSwapRejections': 82, 'identicalEndpointExchanges': 10, 'rootFieldSwapRejections': 361, 'cellFieldSwapRejections': 96, 'parentAuditIndexSwapRejections': 2, 'identicalRootFieldExchanges': 11, 'identicalOwnershipExchanges': 1, 'axisIntervalExchangeRejections': 30, 'evaluationFieldValueExchangeRejections': 60, 'fixedArrayCountRejections': 84, 'objectFieldOrderRejections': 588, 'totalDifferingControls': 7054}
    need(all(controls[k]==v for k,v in expected.items()) and controls['baseline']==n['reference'],'Exact independent variant/child/tag controls')
    links=[]
    for cfg in ['Release','Debug']:
        log=next((ROOT/'build/wfdcpap3/pikapika_report_coverage_plane_audit_partition_wire_tests.dir'/cfg).rglob('link.command.1.tlog'));raw=log.read_bytes();text=raw.decode('utf16').upper()
        inputs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text);actual=[s.strip('"').replace('\\','/').split('/')[-1] for s in inputs]
        windows=['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB']
        need(sorted(actual)==sorted(windows+['PIKAPIKA_DIAGNOSTIC_WIRE.LIB','PIKAPIKA_REPORT_VALUES_WIRE.LIB']),'Only2 data and Windows libraries')
        (OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(raw);links.append(dict(configuration=cfg,inputLibraries=actual))
    profiles=[]
    for p in sorted((ROOT/'build/wfdcpap3').glob('*.json')):
        prior=ROOT/'build/wfdv1'/p.name
        if prior.is_file():need(p.read_bytes()==prior.read_bytes(),'Old profile exact '+p.name);profiles.append(p.name)
    need(len(profiles)==20,'All20 original profiles');after=[stamp(p) for p in sources];need(before==after,'Reference sources stable')
    result=dict(status='FINITE_COVERAGE_PLANE_AUDIT_PARTITION_INTEGRATION_PASS',nativeReceipt=stamp(native),webReceipt=stamp(web),referenceControls={k:v for k,v in controls.items() if k!='mutations'},
        referenceCommand=dict(argv=list(map(str,args)),exitCode=0),sourceBefore=before,sourceAfter=after,sourceStable=True,linkAudit=links,old20ProfilesRawExact=True,fullReportMapped=False,CABIPumpImplemented=False,actualGNUExecuted=False)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','old20ProfilesRawExact','sourceStable']}))
if __name__=='__main__':main()
