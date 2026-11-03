from pathlib import Path
import json,subprocess
base=Path('build/optical-spot-proof');records=[]
for target,command in [
 ('native-tests.txt',[str(base/'spot-tests.exe')]),
 ('native-fixtures.json',[str(base/'spot-tests.exe'),'--fixtures']),
 ('native-oracle.csv',[str(base/'spot-tests.exe'),'--oracle']),
 ('wasm-tests.txt',['node',str(base/'run-wasm.mjs')]),
 ('wasm-fixtures.json',['node',str(base/'run-wasm.mjs'),'--fixtures']),
 ('wasm-oracle.csv',['node',str(base/'run-wasm.mjs'),'--oracle']),
 ('fixture-comparison.json',['python','scripts/verify-optical-spot.py',str(base/'native-fixtures.json'),str(base/'wasm-fixtures.json')]),
 ('oracle-comparison.json',['python','scripts/verify-optical-spot.py',str(base/'native-oracle.csv'),str(base/'wasm-oracle.csv')])]:
    proc=subprocess.run(command,capture_output=True,text=True,timeout=60)
    (base/target).write_text(proc.stdout,encoding='utf-8')
    records.append(dict(command=command,exitCode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr,target=target))
    print(json.dumps(dict(target=target,exitCode=proc.returncode,stdout=proc.stdout if 'comparison' in target else '[retained raw]')),flush=True)
    if proc.returncode:break
(base/'proof-commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
if any(r['exitCode'] for r in records):raise SystemExit(1)
