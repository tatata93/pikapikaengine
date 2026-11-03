import copy,hashlib,json,pathlib,re,subprocess,sys
base=pathlib.Path('build/motion-proof');checker='scripts/verify-motion.py';original=(base/'native-fixtures.json').read_text(encoding='utf-8-sig');source=json.loads(original,parse_int=lambda t:-0.0 if t=='-0' else int(t));log=[]
def run(name,data=None,raw=None,optimized=False,oracle=None,other_raw=None):
    path=base/'negative-fixtures.json';path.write_text(raw if raw is not None else json.dumps(data or source),encoding='utf-8');args=[sys.executable]+(['-O'] if optimized else [])+[checker,str(path)]
    if other_raw is not None:
        p=base/'negative-wasm-fixtures.json';p.write_text(other_raw,encoding='utf-8');args.append(str(p))
    if oracle is not None:
        p=base/'negative-oracle.csv';p.write_text(oracle,encoding='utf-8');args+=['--oracle',str(p)]
    p=subprocess.run(args,capture_output=True,text=True);log.append({'mutation':name,'command':args,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode==0:raise RuntimeError('Negative control passed: '+name)
def row(d,name):return next(r for r in d['fixtures'] if r['name']==name)
def pose(d,name):return row(d,name)['result']['pose']
run('python-O',optimized=True);run('truncated-json',raw=json.dumps(source)[:-19]);run('duplicate-json-key',raw=json.dumps(source).replace('"schema": 1','"schema": 1, "schema": 1',1))
for j in range(len(source['fixtures'])):
    d=copy.deepcopy(source);del d['fixtures'][j];run('missing-fixture-'+str(j),d)
    d=copy.deepcopy(source);d['fixtures'][j]['name']='wrong-identity';run('changed-name-'+str(j),d)
for name,mut in [
 ('nonfinite-matrix',lambda d:pose(d,'rest')['bones'][0]['worldMatrix'].__setitem__(0,float('nan'))),
 ('wrong-fk',lambda d:pose(d,'two-link')['bones'][0]['worldMatrix'].__setitem__(12,2)),
 ('discarded-shear',lambda d:pose(d,'shear')['bones'][0]['worldMatrix'].__setitem__(4,0)),
 ('transposed-translation',lambda d:pose(d,'rest')['bones'][0]['worldMatrix'].__setitem__(3,3)),
 ('wrong-linear-value',lambda d:pose(d,'linear-mid')['bones'][0]['local']['position'].__setitem__(0,3)),
 ('wrong-step-key',lambda d:pose(d,'step-boundary')['bones'][0]['local']['position'].__setitem__(0,0)),
 ('wrong-normalized-key-gauge',lambda d:pose(d,'antipodal-terminal')['bones'][0]['local']['rotation'].__setitem__(2,.4472135954999579)),
 ('subnormal-clock-clipped',lambda d:pose(d,'subnormal-duration').__setitem__('sampledTime',0)),
 ('wrong-loop-phase',lambda d:pose(d,'loop-duration').__setitem__('sampledTime',2)),
 ('wrong-requested-clock',lambda d:pose(d,'linear-mid').__setitem__('requestedTime',1.5)),
 ('changed-stable-id',lambda d:pose(d,'rest')['bones'][0].__setitem__('id',11)),
 ('wrong-bone-count',lambda d:pose(d,'two-link')['bones'].pop()),
 ('wrong-ready-tie-order',lambda d:pose(d,'branching-order').__setitem__('evaluationOrder',[10,20,40,30])),
 ('cycle-gained-pose',lambda d:row(d,'disconnected-cycle')['result'].__setitem__('pose',pose(d,'rest'))),
 ('wrong-status',lambda d:row(d,'world-overflow')['result'].__setitem__('status',1)),
 ('missing-key-field',lambda d:row(d,'linear-mid')['input']['tracks'][0]['keys'][0].pop('pose')),
 ('changed-source-parent',lambda d:row(d,'two-link')['input']['bones'][0].__setitem__('parentId',10)),
 ('changed-source-key',lambda d:row(d,'linear-mid')['input']['tracks'][0]['keys'][0]['pose']['position'].__setitem__(0,1)),
 ('bool-id',lambda d:row(d,'rest')['input']['bones'][0].__setitem__('id',True)),
 ('missing-matrix-value',lambda d:pose(d,'rest')['bones'][0]['localMatrix'].pop()),
]:
    d=copy.deepcopy(source);mut(d);run(name,d)
rows=(base/'native-oracle.csv').read_text(encoding='utf-8-sig').splitlines();run('oracle-truncated',oracle='\n'.join(rows[:-1]));run('oracle-header',oracle='wrong\n'+'\n'.join(rows[1:]))
for name,column,value in [('id',0,'3'),('time',1,'0x1p+0'),('nonfinite',2,'0x1p+1024'),('matrix',2,'0x1p+3'),('decimal',2,'1.0')]:
    bad=rows.copy();v=bad[1].split(',');v[column]=value;bad[1]=','.join(v);run('oracle-'+name,oracle='\n'.join(bad))
bad=rows.copy();bad[1]+=',0x0p+0';run('oracle-extra-value',oracle='\n'.join(bad))
pattern=r'(?<=[,:\[])-0(?=[,\]}])';signed_count=len(re.findall(pattern,original))
if signed_count==0:raise RuntimeError('Actual Native fixtures no longer exercise lexical -0')
positive_args=[sys.executable,checker,str(base/'native-fixtures.json'),str(base/'wasm-fixtures.json')]
positive=subprocess.run(positive_args,capture_output=True,text=True)
if positive.returncode:raise RuntimeError('Actual signed-zero positive pair failed: '+positive.stderr)
changed=re.sub(pattern,'0',original,count=1)
run('actual-native-wasm-one-signed-zero-bit-changed',raw=original,other_raw=changed)
report={'checkerSha256':hashlib.sha256(pathlib.Path(checker).read_bytes()).hexdigest(),'negativeControls':log,'count':len(log),'allRejected':all(x['exitCode']!=0 for x in log),'positiveControls':[{'control':'actual Native/WASM fixtures with lexical integer -0','nativeLexicalSignedZeroCount':signed_count,'command':positive_args,'exitCode':positive.returncode,'stdout':positive.stdout,'stderr':positive.stderr}]};(base/'checker-negative-controls.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'negativeControls':len(log),'allRejected':True,'checkerSha256':report['checkerSha256']}))
