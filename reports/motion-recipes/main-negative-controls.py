import copy,hashlib,json,pathlib,subprocess
base=pathlib.Path('build/motion-proof');checker='scripts/verify-motion-wasm.mjs';source=json.loads((base/'native-fixtures.json').read_text(),parse_int=lambda t:-0.0 if t=='-0' else int(t));log=[]
positive_file=base/'main-positive-json-roundtrip.json';positive_file.write_text(json.dumps(source),encoding='utf-8')
positive_args=['node',checker,str(positive_file)];positive=subprocess.run(positive_args,capture_output=True,text=True)
if positive.returncode:raise RuntimeError('Main negative-control harness roundtrip baseline failed: '+positive.stderr)
def run(name,data=None,oracle=None):
    f=base/'negative-main-fixtures.json';f.write_text(json.dumps(data or source),encoding='utf-8');args=['node',checker,str(f),str(base/'negative-main-report.json'),str(base/'negative-main-outputs.json')]
    if oracle is not None:
        p=base/'negative-main-oracle.csv';p.write_text(oracle,encoding='utf-8');args.append(str(p))
    p=subprocess.run(args,capture_output=True,text=True);log.append({'mutation':name,'command':args,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode==0:raise RuntimeError('Main parity negative control passed: '+name)
def row(d,name):return next(r for r in d['fixtures'] if r['name']==name)
for name,mut in [
 ('missing-fixture',lambda d:d['fixtures'].pop()),
 ('wrong-name',lambda d:d['fixtures'][0].__setitem__('name','wrong')),
 ('wrong-core-matrix',lambda d:row(d,'shear')['result']['pose']['bones'][0]['worldMatrix'].__setitem__(0,7)),
 ('wrong-topology-order',lambda d:row(d,'branching-order')['result']['pose'].__setitem__('evaluationOrder',[10,20,40,30])),
 ('exchange-not-counted-as-rejection',lambda d:row(d,'invalid-mode')['result'].__setitem__('status',0)),
 ('wrong-failure-status',lambda d:row(d,'world-overflow')['result'].__setitem__('status',1)),
 ('wrong-pose-phase',lambda d:row(d,'loop-duration')['result']['pose'].__setitem__('sampledTime',2)),
]:
    d=copy.deepcopy(source);mut(d);run(name,d)
rows=(base/'native-oracle.csv').read_text().splitlines();run('oracle-truncated',oracle='\n'.join(rows[:-1]));run('oracle-header',oracle='wrong\n'+'\n'.join(rows[1:]))
for name,col,value in [('id',0,'3'),('time',1,'0x1p+0'),('matrix',2,'0x1p+3'),('nonfinite',2,'0x1p+1024'),('decimal',2,'1.0')]:
    bad=rows.copy();v=bad[1].split(',');v[col]=value;bad[1]=','.join(v);run('oracle-'+name,oracle='\n'.join(bad))
report={'checkerSha256':hashlib.sha256(pathlib.Path(checker).read_bytes()).hexdigest(),'count':len(log),'allRejected':True,'negativeControls':log,'positiveControls':[{'control':'JSON roundtrip preserves all actual binary64 including -0','command':positive_args,'exitCode':positive.returncode,'stdout':positive.stdout,'stderr':positive.stderr}]};(base/'main-checker-negative-controls.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'mainNegativeControls':len(log),'allRejected':True,'checkerSha256':report['checkerSha256']}))
