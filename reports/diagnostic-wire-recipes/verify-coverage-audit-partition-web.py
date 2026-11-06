"""Independent web regressions and seventeen-header admission for the separate Input variant boundary."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-coverage-audit-partition-web-001'
def need(v,m):
    if not v:raise ValueError(m)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
def main():
    need(__debug__ and not OUT.exists(),'Fresh web/schema checks');OUT.mkdir(parents=True);commands=[]
    def run(name,args):
        start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,timeout=240)
        (OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        row=dict(name=name,argv=list(map(str,args)),exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(row);write(OUT/(name+'.command.json'),row);need(p.returncode==0,'Actual '+name);return p.stdout
    result=dict(status='FAIL',scope=__doc__)
    try:
        m=json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes());need(len(m['mappedVariants'])==1 and m['mappedVariants'][0]['alternatives']==[dict(ordinal=0,cppType='accelerated_pair_coverage::SpherePair'),dict(ordinal=1,cppType='accelerated_pair_coverage::SpherePlane')],'Separate variant declaration')
        schema=json.loads(run('schema-controls',[sys.executable,'-B','-X','utf8','tests/report_values_schema_tests.py','--output','build/wfdcaps1-result','--build','build/wfdcaps1-copies']))
        need(schema['mappedTypes']==67 and schema['mappedFields']==389 and schema['accepted']==1 and schema['refused']==20,'Actual17-header source gate')
        destination=OUT/'schema-controls';destination.mkdir()
        for p in (ROOT/'build/wfdcaps1-result').iterdir():need(p.is_file(),'Only receipts');(destination/p.name).write_bytes(p.read_bytes())
        for command in ['test','check','build']:run('npm-'+command,['npm.cmd','run',command])
        result.update(status='FINITE_COVERAGE_AUDIT_PARTITION_WEB_PASS',schemaControls=schema,mappedRecordTypes=67,mappedFields=389,mappedVariants=1,actualGNUExecuted=False)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    result['commands']=commands;write(OUT/'verification.json',result);print(json.dumps({k:result[k] for k in ['status','error'] if k in result}));return int(result['status']!='FINITE_COVERAGE_AUDIT_PARTITION_WEB_PASS')
if __name__=='__main__':raise SystemExit(main())
