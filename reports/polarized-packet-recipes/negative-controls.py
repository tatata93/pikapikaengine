import copy,hashlib,json,pathlib,subprocess,sys
base=pathlib.Path('build/polarized-packet-proof');checker='scripts/verify-polarized-packet.py'
source=json.loads((base/'native-fixtures.json').read_text(encoding='utf-8-sig'));log=[]
def run(name,data=None,raw=None,optimized=False,oracle=None):
    path=base/'negative-fixtures.json';path.write_text(raw if raw is not None else json.dumps(data or source),encoding='utf-8')
    args=[sys.executable]+(['-O'] if optimized else [])+[checker,str(path)]
    if oracle is not None:
        op=base/'negative-oracle.csv';op.write_text(oracle,encoding='utf-8');args+=['--oracle',str(op)]
    p=subprocess.run(args,capture_output=True,text=True)
    log.append({'mutation':name,'command':args,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode==0:raise RuntimeError('Negative control passed: '+name)
run('python-O',optimized=True);run('truncated-json',raw=json.dumps(source)[:-17]);run('duplicate-json-key',raw=json.dumps(source).replace('"schema": 1','"schema": 1, "schema": 1',1))
for j in range(len(source['fixtures'])):
    d=copy.deepcopy(source);del d['fixtures'][j];run('missing-fixture-'+str(j),d)
    d=copy.deepcopy(source);d['fixtures'][j]['name']='wrong-identity';run('changed-name-'+str(j),d)
def row(d,name):return next(r for r in d['fixtures'] if r['name']==name)
def result(d,name):return row(d,name)['result']
for name,mut in [
 ('reversed-bound',lambda d:result(d,'normal-plate')['stats'].__setitem__('detected',[2,1])),
 ('nonfinite-bound',lambda d:result(d,'normal-plate')['stats'].__setitem__('detected',[0,float('nan')])),
 ('wrong-watts',lambda d:result(d,'normal-plate')['stats'].__setitem__('detected',[4,4])),
 ('source-as-weight',lambda d:result(d,'normal-plate')['stats'].__setitem__('totalSource',[1,1])),
 ('missing-stats',lambda d:result(d,'identity-bundle').__setitem__('stats',None)),
 ('unknown-as-zero',lambda d:result(d,'sensor-boundary').__setitem__('stats',{'totalSource':[1,1],'acceptedSource':[0,0],'detected':[0,0]})),
 ('wrong-accepted-count',lambda d:result(d,'normal-plate')['counts'].__setitem__(1,1)),
 ('lost-prefix',lambda d:result(d,'power-prefix-route-miss')['records'][0]['route'].__setitem__('completedPowerSteps',0)),
 ('omitted-packet',lambda d:result(d,'identity-bundle')['records'].pop()),
 ('wrong-ordinal',lambda d:result(d,'identity-bundle')['records'][0].__setitem__('ordinal',1)),
 ('original-watts-changed',lambda d:result(d,'identity-bundle')['records'][0].__setitem__('power',[3,0,0,0])),
 ('nonaccepted-sensor-power',lambda d:result(d,'all-route-miss')['records'][0].__setitem__('sensorPower',[0,0])),
 ('changed-source-input',lambda d:row(d,'normal-plate')['input']['packets'][0]['power'].__setitem__(0,3)),
 ('changed-sensor-input',lambda d:row(d,'normal-plate')['input']['sensor']['normal'].__setitem__(0,1)),
 ('subnormal-power-clipped',lambda d:result(d,'subnormal-power')['stats'].__setitem__('detected',[0,0])),
 ('extra-cosine',lambda d:result(d,'inclined-nonunit-sensor')['records'][0].__setitem__('sensorPower',[.8,.8])),
 ('extra-index-squared',lambda d:result(d,'normal-plate')['stats'].__setitem__('detected',[10.368,10.368])),
 ('ghost-routes-reset',lambda d:result(d,'noncoplanar-unpolarized')['stats'].__setitem__('detected',[1263376/466948881,1263376/466948881])),
 ('budget-stats',lambda d:result(d,'evaluation-budget').__setitem__('stats',{'totalSource':[2,2],'acceptedSource':[1,1],'detected':[1,1]})),
 ('missing-counter',lambda d:result(d,'normal-plate')['sqrt'].pop()),
 ('negative-counter',lambda d:result(d,'normal-plate')['sqrt'].__setitem__(0,-1)),
 ('bad-enum',lambda d:result(d,'normal-plate').__setitem__('status',9)),
 ('nonfinite-reference',lambda d:row(d,'normal-plate')['input']['packets'][0]['reference'].__setitem__(0,float('inf'))),
]:
    d=copy.deepcopy(source);mut(d);run(name,d)
rows=(base/'native-oracle.csv').read_text(encoding='utf-8-sig').splitlines()
run('oracle-truncated',oracle='\n'.join(rows[:-1]));run('oracle-header',oracle='wrong\n'+'\n'.join(rows[1:]))
for name,col,value in [('id',0,'7'),('kind',1,'7'),('source',2,'0x1.8p+0'),('nonfinite',6,'0x1p+1024'),('output',10,'0x1.8p+0'),('decimal',6,'1.0')]:
    bad=rows.copy();r=bad[1].split(',');r[col]=value;bad[1]=','.join(r);run('oracle-'+name,oracle='\n'.join(bad))
bad=rows.copy();bad[1]+=',0x0p+0';run('oracle-extra-column',oracle='\n'.join(bad))
report={'checkerSha256':hashlib.sha256(pathlib.Path(checker).read_bytes()).hexdigest(),'negativeControls':log,'count':len(log),'allRejected':all(x['exitCode']!=0 for x in log)}
(base/'checker-negative-controls.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'negativeControls':len(log),'allRejected':True,'checkerSha256':report['checkerSha256']}))
