import copy,hashlib,json,pathlib,subprocess,sys
base=pathlib.Path('build/polarized-route-proof');checker='scripts/verify-polarized-route.py'
source=json.loads((base/'native-fixtures.json').read_text(encoding='utf-8-sig'))
log=[]
def run(name,data=None,raw=None,optimized=False,oracle=None):
    path=base/'negative-fixtures.json';path.write_text(raw if raw is not None else json.dumps(data or source),encoding='utf-8')
    args=[sys.executable]+(['-O'] if optimized else [])+[checker,str(path)]
    if oracle is not None:
        op=base/'negative-oracle.csv';op.write_text(oracle,encoding='utf-8');args+=['--oracle',str(op)]
    p=subprocess.run(args,capture_output=True,text=True)
    log.append({'mutation':name,'command':args,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode==0:raise RuntimeError('Negative control unexpectedly passed: '+name)
run('python-O',optimized=True)
run('truncated-json',raw=json.dumps(source)[:-13])
run('duplicate-json-key',raw=json.dumps(source).replace('"schema": 1','"schema": 1, "schema": 1',1))
for j in range(len(source['fixtures'])):
    d=copy.deepcopy(source);del d['fixtures'][j];run('missing-fixture-'+str(j),d)
    d=copy.deepcopy(source);d['fixtures'][j]['name']='changed-name';run('changed-identity-'+str(j),d)
for name,mut in [
    ('reversed-output-bound',lambda d:d['fixtures'][0]['result']['completion']['state'].__setitem__('power',[2,1])),
    ('nonfinite-output',lambda d:d['fixtures'][0]['result']['completion']['state'].__setitem__('power',[0,float('nan')])),
    ('wrong-physical-output',lambda d:d['fixtures'][0]['result']['completion']['state'].__setitem__('power',[0,.9])),
    ('missing-completion',lambda d:d['fixtures'][0]['result'].__setitem__('completion',None)),
    ('wrong-prefix-count',lambda d:d['fixtures'][1]['result'].__setitem__('completedPowerSteps',0)),
    ('wrong-classification',lambda d:d['fixtures'][16]['result'].__setitem__('status',0)),
    ('missing-field',lambda d:d['fixtures'][0]['input'].pop('reference')),
    ('invalid-input-type',lambda d:d['fixtures'][0]['input'].__setitem__('wavelength',True)),
    ('changed-surface-input',lambda d:d['fixtures'][1]['input']['steps'][0]['normal'].__setitem__(0,1)),
    ('changed-medium-input',lambda d:d['fixtures'][1]['input'].__setitem__('index',[2,2])),
    ('subnormal-inward-clamp',lambda d:d['fixtures'][-1]['result']['completion']['state']['upper'][0].__setitem__(1,[0,0])),
    ('wrong-world-phase',lambda d:d['fixtures'][15]['result']['completion']['state']['upper'][0].__setitem__(1,[0,0])),
]:
    d=copy.deepcopy(source);mut(d);run(name,d)
rows=(base/'native-oracle.csv').read_text(encoding='utf-8-sig').splitlines()
run('oracle-truncated',oracle='\n'.join(rows[:-1]))
run('oracle-header',oracle='changed\n'+'\n'.join(rows[1:]))
for name,column,value in [('id',0,'42'),('frame',5,'7'),('input',1,'0x1.8p+0'),('nonfinite',6,'0x1p+1024'),('output',6,'0x1.8p+0'),('decimal',6,'1.0')]:
    bad=rows.copy();r=bad[1].split(',');r[column]=value;bad[1]=','.join(r);run('oracle-'+name,oracle='\n'.join(bad))
bad=rows.copy();bad[1]+= ',0x0p+0';run('oracle-extra-column',oracle='\n'.join(bad))
result={'checkerSha256':hashlib.sha256(pathlib.Path(checker).read_bytes()).hexdigest(),'negativeControls':log,'allRejected':all(x['exitCode']!=0 for x in log),'count':len(log)}
(base/'checker-negative-controls.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'negativeControls':len(log),'allRejected':True,'checkerSha256':result['checkerSha256']}))
