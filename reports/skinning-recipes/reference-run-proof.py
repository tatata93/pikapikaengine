"""Local proof driver; no compiler/library dependency or source mutation."""
from pathlib import Path
import copy
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCRIPT = ROOT/'scripts/verify-skinning.py'
RAW = ROOT/'build/skinning-proof'
spec = importlib.util.spec_from_file_location('verify_skinning',SCRIPT)
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

def run(args):
    return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,text=True,
                          encoding='utf-8',capture_output=True,timeout=30)

command = [SCRIPT,RAW/'native.json',RAW/'wasm.json','--oracle',RAW/'native-oracle.csv',
           '--wasm-oracle',RAW/'wasm-oracle.csv']
good = run(command)
(HERE/'acceptance.json').write_text(good.stdout,encoding='utf-8')
(HERE/'acceptance.stderr.txt').write_text(good.stderr,encoding='utf-8')
v.check(good.returncode == 0,'acceptance failed: '+good.stderr)
original = v.parse_json(v.read_text(RAW/'native.json'))
cases = []

def bad_json(name, mutate=None, raw=None, expected=''):
    data = copy.deepcopy(original)
    if mutate: mutate(data)
    path = HERE/(name+'.json')
    path.write_text(raw if raw is not None else json.dumps(data,allow_nan=True),encoding='utf-8')
    p = run([SCRIPT,path])
    v.check(p.returncode != 0 and expected in p.stderr,name+': rejection missing/wrong: '+p.stderr)
    cases.append({'case':name,'exitCode':p.returncode,'stderr':p.stderr.strip()})

def find(d,name):
    return next(r for r in d['fixtures'] if r['name'] == name)

bad_json('duplicate-key',raw='{"schema":1,"schema":1,"fixtures":[]}',expected='duplicate JSON key')
bad_json('nonfinite-constant',lambda d:d['fixtures'][0]['input']['rest'][0]['matrix'].__setitem__(0,float('nan')),
         expected='nonfinite JSON constant')
text=json.dumps(original).replace('"matrix": [1,','"matrix": [1e999,',1)
v.check('1e999' in text,'overflow mutation did not apply')
bad_json('decimal-overflow',raw=text,expected='finite binary64')
bad_json('signed-zero-input',lambda d:d['fixtures'][0]['input']['rest'][0]['matrix'].__setitem__(1,-0.0),
         expected='binary64 inputs changed')
bad_json('modified-input',lambda d:find(d,'deform-identity')['input']['vertices'][0]['position'].__setitem__(0,1.25),
         expected='binary64 inputs changed')
bad_json('missing-key',lambda d:d['fixtures'][0]['result'].pop('diagnostics'),expected='object schema')
bad_json('extra-key',lambda d:d['fixtures'][0]['result'].__setitem__('unexpected',1),expected='object schema')
bad_json('row-missing',lambda d:d['fixtures'].pop(),expected='identity/count/order')
bad_json('row-order',lambda d:d['fixtures'].reverse(),expected='identity/count/order')
bad_json('boolean-status',lambda d:d['fixtures'][0]['result'].__setitem__('status',False),expected='integer shape/domain')
bad_json('wrong-failure-status',lambda d:find(d,'bind-singular')['result'].__setitem__('status',4),expected='independent status witness')
bad_json('failed-partial-position',lambda d:find(d,'deform-all-zero')['result'].__setitem__('positions',[[0,0,0]]),
         expected='atomic deform output')
bad_json('poison-inverse',lambda d:d['fixtures'][0]['result']['joints'][0]['inverseBind'].__setitem__(0,1.125),
         expected='point error exceeds')
bad_json('wrong-weight-normalization',lambda d:find(d,'deform-two-weighted')['result']['positions'][0].__setitem__(0,16),
         expected='point error exceeds')
bad_json('old-cancellation-loss',lambda d:find(d,'deform-cancellation-limit')['result']['positions'][0].__setitem__(0,.5),
         expected='point error exceeds')
bad_json('wrong-output-id',lambda d:d['fixtures'][0]['result']['joints'][0].__setitem__('id',19),expected='rest order/ID/bits')
bad_json('duplicate-diagnostic',lambda d:find(d,'deform-two-weighted')['result']['diagnostics'][1].__setitem__('id',7),
         expected='diagnostic prefix/order/IDs')
bad_json('bad-residual',lambda d:find(d,'deform-identity')['result']['weightResiduals'].__setitem__(0,.1),
         expected='normalization residual')

oracle = list(csv.reader(io.StringIO(v.read_text(RAW/'native-oracle.csv'))))
def bad_csv(name,mutate,expected):
    data=copy.deepcopy(oracle);mutate(data);path=HERE/(name+'.csv')
    with path.open('w',newline='',encoding='utf-8') as f: csv.writer(f).writerows(data)
    p=run([SCRIPT,RAW/'native.json','--oracle',path])
    v.check(p.returncode != 0 and expected in p.stderr,name+': rejection missing/wrong: '+p.stderr)
    cases.append({'case':name,'exitCode':p.returncode,'stderr':p.stderr.strip()})

bad_csv('oracle-missing-row',lambda d:d.pop(),'header/128-row count')
bad_csv('oracle-duplicate-id',lambda d:d[2].__setitem__(0,'0'),'width/identity/order')
bad_csv('oracle-extra-column',lambda d:d[1].append('0x0p+0'),'width/identity/order')
bad_csv('oracle-decimal-token',lambda d:d[1].__setitem__(1,'2.0'),'hexadecimal binary64')
bad_csv('oracle-input-zero-sign',lambda d:d[1].__setitem__(2,'-0x0p+0'),'binary64 inputs changed')
bad_csv('oracle-poison-inverse',lambda d:d[1].__setitem__(70,'0x1.8p-1'),'point error exceeds')
bad_csv('oracle-poison-position',lambda d:d[1].__setitem__(102,'0x1p+20'),'point error exceeds')
p=run(['-O',SCRIPT,'--self-test'])
v.check(p.returncode != 0 and 'optimized mode' in p.stderr,'Python -O did not fail closed')
cases.append({'case':'python-optimized','exitCode':p.returncode,'stderr':p.stderr.strip()})
(HERE/'negative-cases.json').write_text(json.dumps({'rejected':len(cases),'cases':cases},indent=2),encoding='utf-8')

tracked=['scripts/verify-skinning.py','core/include/pikapika/skinning.hpp','core/src/skinning.cpp','tests/skinning_tests.cpp']
raw=['native.json','wasm.json','native-oracle.csv','wasm-oracle.csv','native-tests.txt','wasm-tests.txt']
paths=[ROOT/p for p in tracked]+[RAW/p for p in raw]
manifest=[]
for p in paths:
    data=p.read_bytes();manifest.append({'path':str(p.relative_to(ROOT)).replace('\\','/'),
                                       'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(HERE/'provenance.json').write_text(json.dumps({'files':manifest,'negativeCases':len(cases),
    'command':['python',*[str(p.relative_to(ROOT)) if isinstance(p,Path) else p for p in command]],
    'interpretation':'exact real values of binary64 inputs; ordinary point tolerance, no general rigorous enclosure',
    'externalCodeOrDependencies':False},indent=2),encoding='utf-8')
print('PASS acceptance, 65 fixtures, 128 oracle rows, '+str(len(cases))+' rejection cases')
