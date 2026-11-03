from pathlib import Path
import csv,io,subprocess,json,hashlib
base=Path('build/polarized-route-proof');native=base/'sqrt-native-oracle.csv';wasm=base/'sqrt-wasm-oracle.csv';rows=list(csv.reader(io.StringIO(native.read_text(encoding='utf-8-sig'))));out=[]
def run(label,r,other=None):
 p=base/'sqrt-negative.csv';buf=io.StringIO(newline='');csv.writer(buf,lineterminator='\n').writerows(r);p.write_text(buf.getvalue(),encoding='utf8',newline='\n');cmd=['python','scripts/verify-interval-sqrt.py',str(p)]+([str(other)] if other else []);x=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert x.returncode!=0,label;out.append({'name':label,'command':cmd,'exitCode':x.returncode,'stdout':x.stdout,'stderr':x.stderr})
checks=[('ordered-wrong-lower',2,4,'4000000000000000'),('ordered-wrong-upper',2,5,'0000000000000000'),('changed-source',2,1,'0000000000000000'),('bad-ordinal',2,0,'0'),('infinite-root',2,5,'7ff0000000000000'),('nan-root',2,5,'7ff8000000000001'),('negative-root',2,4,'bff0000000000000'),('excess-work',2,6,'99999'),('invalid-flag',2,7,'2'),('negative-counter',2,6,'-1'),('malformed-hex',2,4,'hello'),('unresolved-point-width',3,4,'0000000000000000')]
for label,index,col,value in checks:
 r=[a[:] for a in rows];r[index][col]=value
 if label=='ordered-wrong-lower':r[index][5]='4008000000000000'
 if label=='ordered-wrong-upper':r[index][4]='0000000000000000'
 if label=='unresolved-point-width':r[index][5]='3ff0000000000000'
 run(label,r)
for label,change in [('missing-row',lambda r:r[:-1]),('extra-column',lambda r:[r[0]]+[a+['0'] for a in r[1:]]),('missing-value',lambda r:[r[0]]+[a[:-1] for a in r[1:]])]:run(label,change([a[:] for a in rows]))
r=[a[:] for a in rows];r[1][5]='8000000000000000';run('signed-zero-bit-parity',r,wasm)
cmd=['python','-O','scripts/verify-interval-sqrt.py',str(native)];x=subprocess.run(cmd,capture_output=True,text=True);assert x.returncode!=0;out.append({'name':'optimized-python','command':cmd,'exitCode':x.returncode,'stdout':x.stdout,'stderr':x.stderr})
positive=subprocess.run(['python','scripts/verify-interval-sqrt.py',str(native),str(wasm)],capture_output=True,text=True,timeout=30);assert positive.returncode==0;report={'checkerSHA256':hashlib.sha256(Path('scripts/verify-interval-sqrt.py').read_bytes()).hexdigest(),'positive':json.loads(positive.stdout),'negativeControls':len(out),'records':out};(base/'sqrt-negative-controls.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n');print('shared sqrt positive and',len(out),'negative controls PASS')
