"""Finish link/profile integration after actual Native build; preserve premature first observation."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-rejection-final-links-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    raw=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    need(__debug__ and not OUT.exists(),'Fresh final integration');OUT.mkdir(parents=True)
    native=ROOT/'reports/diagnostic-wire-recipes/run-20261106-rejection-native-001/verification.json'
    n=json.loads(native.read_bytes());need(n['status']=='FINITE_NATIVE_DIAGNOSTIC_REJECTION_PASS','Native finished successfully first')
    prior=ROOT/'reports/diagnostic-wire-integration/run-20261106-rejection-native-001/verification.json'
    previous=json.loads(prior.read_bytes());need(previous['status']=='FAIL' and previous['error']=='StopIteration: ','Preserve premature missing link observation')
    need([r['name'] for r in previous['commands']]==['schema-controls','npm-test','npm-check','npm-build'] and all(r['exitCode']==0 for r in previous['commands']),'All actual unaffected checks passed')
    for name in ['source-before.json','protected-before.json']:
        for row in json.loads((native.parent/name).read_bytes()):
            raw=(ROOT/row['path']).read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'Tested and protected source exact')
    schema=json.loads((prior.parent/'schema-controls.stdout.txt').read_bytes());need(schema['mappedTypes']==62 and schema['mappedFields']==369 and schema['accepted']==1 and schema['refused']==20,'Actual schema gate')
    links=[]
    for cfg in ['Release','Debug']:
        log=next((ROOT/'build/wfdrej1/pikapika_diagnostic_wire_rejection_tests.dir'/cfg).rglob('link.command.1.tlog'))
        raw=log.read_bytes();text=raw.decode('utf16').upper()
        inputs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text)
        actual=[s.strip('"').replace('\\','/').split('/')[-1] for s in inputs]
        windows=['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB']
        need(sorted(actual)==sorted(windows+['PIKAPIKA_DIAGNOSTIC_WIRE.LIB']),'Only primitive and Windows system libraries')
        (OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(raw);links.append(dict(configuration=cfg,inputLibraries=actual))
    profiles=[]
    for p in sorted((ROOT/'build/wfdrej1').glob('*.json')):
        prior_profile=ROOT/'build/wfdv1'/p.name
        if prior_profile.is_file():need(p.read_bytes()==prior_profile.read_bytes(),'Old profile exact '+p.name);profiles.append(p.name)
    need(len(profiles)==20,'All20 old profiles')
    result=dict(status='FINITE_DIAGNOSTIC_REJECTION_INTEGRATION_PASS',nativeReceipt=stamp(native),priorPartialReceipt=stamp(prior),
        priorSuccessfulChecksReused=True,prematureLinkObservationWasNotProductFailure=True,testedSourcesUnchanged=True,
        schemaControls=schema,linkAudit=links,old20ProfilesRawExact=True,fullReportMapped=False,CABIPumpImplemented=False,actualGNUExecuted=False)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
