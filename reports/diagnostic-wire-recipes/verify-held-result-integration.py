"""Finite Native complete held Result integration: independent mutations, source gate and web regressions."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-held-result-native-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
def main():
    need(__debug__ and not OUT.exists(),'Fresh output');OUT.mkdir(parents=True);commands=[]
    def run(name,args):
        start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,timeout=240)
        (OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        item=dict(name=name,argv=list(map(str,args)),exitCode=p.returncode,seconds=time.monotonic()-start,stdoutBytes=len(p.stdout),stdoutSha256=hashlib.sha256(p.stdout).hexdigest());commands.append(item);write(OUT/(name+'.command.json'),item)
        need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(status='FAIL',scope=__doc__)
    try:
        fixture=ROOT/'reports/diagnostic-wire-recipes/run-20261106-held-result-native-001/Release-fixture.stdout.hex.txt'
        controls=json.loads(run('reference-controls',[sys.executable,'-B','-X','utf8','tests/report_held_result_wire_reference_tests.py',fixture,'--hex']))
        need(controls['wellFormedSingleByteMutations']>254 and controls['recordOrderCountRejections']==3,'Actual mutation coverage')
        schema=json.loads(run('schema-controls',[sys.executable,'-B','-X','utf8','tests/report_values_schema_tests.py','--output','build/wfdhrs1-result','--build','build/wfdhrs1-copies']))
        need(schema['mappedTypes']==50 and schema['mappedFields']==312 and schema['accepted']==1 and schema['refused']==19,'Actual source gate coverage')
        source=ROOT/'build/wfdhrs1-result';destination=OUT/'schema-controls';destination.mkdir()
        for p in source.iterdir():
            need(p.is_file(),'Only schema receipts');(destination/p.name).write_bytes(p.read_bytes())
        for command in ['test','check','build']:run('npm-'+command,['npm.cmd','run',command])
        links=[]
        for cfg in ['Release','Debug']:
            link=next((ROOT/'build/wfdhr1/pikapika_report_held_result_wire_tests.dir'/cfg).rglob('link.command.1.tlog'))
            raw=link.read_bytes();text=raw.decode('utf16').upper()
            # /IMPLIB is an output path, not an input library.
            import re
            inputs=re.findall(r'(?<!\S)(?:"[^"]+\.LIB"|[^\s"]+\.LIB)(?=\s|$)',text)
            actual=[s.strip('"').replace('\\','/').split('/')[-1] for s in inputs]
            windows=['KERNEL32.LIB','USER32.LIB','GDI32.LIB','WINSPOOL.LIB','SHELL32.LIB','OLE32.LIB','OLEAUT32.LIB','UUID.LIB','COMDLG32.LIB','ADVAPI32.LIB']
            need(sorted(actual)==sorted(windows+['PIKAPIKA_DIAGNOSTIC_WIRE.LIB','PIKAPIKA_REPORT_VALUES_WIRE.LIB']),'Only data and actual Windows system libraries linked')
            (OUT/(cfg+'-link.command.1.tlog.txt')).write_bytes(raw);links.append(dict(configuration=cfg,inputLibraries=actual))
        profiles=[]
        old=ROOT/'build/wfdv1'
        for p in sorted((ROOT/'build/wfdhr1').glob('*.json')):
            relative=p.relative_to(ROOT/'build/wfdhr1');prior=old/relative
            if prior.is_file():need(p.read_bytes()==prior.read_bytes(),'Preserve old profile '+str(relative));profiles.append(str(relative))
        # The fixed source-enforcement profile set has twenty files.
        need(len(profiles)==20,'All20 original profiles')
        result.update(status='FINITE_HELD_RESULT_INTEGRATION_PASS',referenceControls={k:v for k,v in controls.items() if k!='mutations'},schemaControls=schema,linkAudit=links,old20ProfilesRawExact=True,fullReportMapped=False,CABIPumpImplemented=False,actualGNUExecuted=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    result['commands']=commands;write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','error'] if k in result}));return int(result['status']!='FINITE_HELD_RESULT_INTEGRATION_PASS')
if __name__=='__main__':raise SystemExit(main())
