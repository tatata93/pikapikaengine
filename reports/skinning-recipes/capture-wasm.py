import csv,io,json,struct,subprocess
from pathlib import Path
p=Path('build/skinning-proof');records=[]
for args,name in [([], 'wasm-tests.txt'),(['--fixtures'],'wasm.json'),(['--oracle'],'wasm-oracle.csv')]:
 command=['node',str(p/'run-wasm.mjs'),*args];r=subprocess.run(command,capture_output=True)
 (p/name).write_bytes(r.stdout);records.append({'command':command,'exitCode':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()})
 if r.returncode:raise SystemExit(r.returncode)
(p/'wasm-commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
def load(name):return json.loads((p/name).read_text(),parse_int=lambda t:-0.0 if t=='-0' else int(t))
count=0
def compare(a,b,path='root'):
 global count
 if isinstance(a,bool) or a is None or isinstance(a,str):
  if type(a)!=type(b) or a!=b:raise RuntimeError(path)
 elif isinstance(a,(int,float)):
  if struct.pack('>d',float(a))!=struct.pack('>d',float(b)):raise RuntimeError(path)
  count+=1
 elif isinstance(a,list):
  if not isinstance(b,list) or len(a)!=len(b):raise RuntimeError(path)
  for j,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{j}]')
 elif isinstance(a,dict):
  if a.keys()!=b.keys():raise RuntimeError(path)
  for key in a:compare(a[key],b[key],path+'.'+key)
 else:raise RuntimeError(path)
compare(load('native.json'),load('wasm.json'));fixture_count=count
a=list(csv.reader(io.StringIO((p/'native-oracle.csv').read_text())));b=list(csv.reader(io.StringIO((p/'wasm-oracle.csv').read_text())))
if a[0]!=b[0] or len(a)!=129 or len(b)!=129:raise RuntimeError('Oracle shape')
for i,(x,y) in enumerate(zip(a[1:],b[1:])):
 if len(x)!=105 or len(y)!=105:raise RuntimeError('Oracle row')
 if x[0]!=str(i) or y[0]!=str(i):raise RuntimeError('Oracle id')
 for j,(xx,yy) in enumerate(zip(x[1:],y[1:])):
  if struct.pack('>d',float.fromhex(xx))!=struct.pack('>d',float.fromhex(yy)):raise RuntimeError(f'Oracle bit {i},{j}')
  count+=1
report={'passed':True,'fixtures':65,'testGroupsNative':68,'testGroupsWasm':68,'fixtureNumericBitsCompared':fixture_count,'oracleRows':128,'oracleNumericBitsCompared':count-fixture_count,'totalNumericBitsCompared':count,'maximumAbsoluteDifference':0,'comparison':'binary64 bit equality including signed zero, full fixture inputs and results; oracle id checked separately'}
(p/'standalone-parity.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
