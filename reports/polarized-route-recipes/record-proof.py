import datetime,hashlib,json,pathlib,subprocess,sys
base=pathlib.Path('build/polarized-route-proof')
log=[]
def run(args,out=None):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(args,capture_output=True)
    if out:(base/out).write_bytes(p.stdout)
    log.append({'command':args,'startedUtc':start,'exitCode':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace')})
    (base/'proof-commands.json').write_text(json.dumps({'commands':log,'allSuccessful':all(x['exitCode']==0 for x in log)},indent=2),encoding='utf-8')
    if p.returncode:raise SystemExit(p.returncode)
run([str(base/'polarized-tests.exe')],'native-tests.txt')
run([str(base/'polarized-tests.exe'),'--fixtures'],'native-fixtures.json')
run([str(base/'polarized-tests.exe'),'--oracle'],'native-oracle.csv')
run(['node',str(base/'run-wasm.mjs')],'wasm-tests.txt')
run(['node',str(base/'run-wasm.mjs'),'--fixtures'],'wasm-fixtures.json')
run(['node',str(base/'run-wasm.mjs'),'--oracle'],'wasm-oracle.csv')
run([sys.executable,'scripts/verify-polarized-route.py',str(base/'native-fixtures.json'),str(base/'wasm-fixtures.json'),'--oracle',str(base/'native-oracle.csv'),'--wasm-oracle',str(base/'wasm-oracle.csv')],'fixture-comparison.json')
print(log[-1]['stdout'])
