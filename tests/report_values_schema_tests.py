"""Exercise the actual CMake source review gate in fresh isolated header copies."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/diagnostic-wire-recipes/run-20261106-values-schema-001'
BUILD=ROOT/'build/wfdvs1'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--build',type=Path);args=parser.parse_args()
    out=args.output.resolve() if args.output else OUT;build=args.build.resolve() if args.build else BUILD
    if args.output:need(out.is_relative_to(ROOT/'build'),'Optional output remains in build')
    if args.build:need(build.is_relative_to(ROOT/'build'),'Optional source copies remain in build')
    need(__debug__ and not out.exists() and not build.exists(),'Fresh bounded schema controls')
    out.mkdir(parents=True);build.mkdir(parents=True);manifest=json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes())
    paths=[r['path'] for r in manifest['headers']]+['core/report-values-schema-v1.json']
    before=[stamp(ROOT/p) for p in paths]+[stamp(ROOT/'cmake/ReportValuesSchema.cmake')]
    driver=build/'check.cmake';driver.write_text('include("'+(ROOT/'cmake/ReportValuesSchema.cmake').as_posix()+'")\npp_check_report_values_schema("${SOURCE}")\n',encoding='utf8',newline='\n')
    rows=[]
    cases=[('original',None,None)]+[('changed-'+str(i),path,'change') for i,path in enumerate(paths)]+[('missing-header',paths[0],'missing'),('missing-manifest',paths[-1],'missing')]
    for name,target,mode in cases:
        copy=build/name
        for path in paths:
            p=copy/path;p.parent.mkdir(parents=True,exist_ok=True)
            if mode=='missing' and path==target:continue
            data=(ROOT/path).read_bytes()
            if mode=='change' and path==target:
                if path.endswith('.json'):
                    modified=json.loads(data);modified['unreviewedField']=True;data=(json.dumps(modified)+'\n').encode()
                else:data+=b'\n// Intentional unreviewed source mutation for gate test.\n'
            p.write_bytes(data)
        argv=['cmake','-DSOURCE='+copy.as_posix(),'-P',str(driver)];start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
        (out/(name+'.stdout.txt')).write_bytes(p.stdout);(out/(name+'.stderr.txt')).write_bytes(p.stderr)
        accepted=p.returncode==0;need(accepted==(target is None),'Actual schema admission '+name)
        if target is not None:need(b'Report values schema' in p.stderr,'Actual expected source-gate refusal')
        row=dict(name=name,target=target,mutation=mode,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-start,accepted=accepted);rows.append(row)
        (out/(name+'.command.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf8',newline='\n')
    after=[stamp(ROOT/p) for p in paths]+[stamp(ROOT/'cmake/ReportValuesSchema.cmake')];need(before==after,'All actual product sources unchanged')
    result=dict(schema=1,status='PASS',mappedTypes=len(manifest['mappedTypes']),mappedFields=sum(len(r['fields']) for r in manifest['mappedTypes']),commands=rows,accepted=1,refused=len(cases)-1,sourceStable=True,before=before,after=after,scope='Source/schema review gate only; no field reflection, complete Report coverage or numerical model proof.')
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','mappedTypes','mappedFields','accepted','refused','sourceStable']}))
if __name__=='__main__':main()
