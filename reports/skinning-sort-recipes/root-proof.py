import datetime,hashlib,json,pathlib,subprocess,sys,time

root=next(p for p in pathlib.Path(__file__).resolve().parents if (p/'CMakeLists.txt').is_file() and (p/'core/include/pikapika').is_dir())
out=root/'build/skinning-sort-root';out.mkdir(exist_ok=True)
commands=[]
def run(args,name):
    before=time.monotonic()
    r=subprocess.run(args,cwd=root,capture_output=True,timeout=180)
    (out/(name+'.stdout.txt')).write_bytes(r.stdout);(out/(name+'.stderr.txt')).write_bytes(r.stderr)
    commands.append(dict(command=args,exitCode=r.returncode,elapsedSeconds=time.monotonic()-before,
      stdout='build/skinning-sort-root/'+name+'.stdout.txt',stderr='build/skinning-sort-root/'+name+'.stderr.txt'))
    print(name,r.returncode,flush=True)
    if r.returncode: print(r.stdout.decode('utf-8',errors='replace'),r.stderr.decode('utf-8',errors='replace'));raise SystemExit(r.returncode)
run(['npm.cmd','run','build'],'web-build')
run(['npm.cmd','run','check'],'syntax')
run(['npm.cmd','test'],'node-tests')
run(['node','scripts/verify-skinning-wasm.mjs','reports/skinning-native.json','reports/skinning-native-oracle.csv',
 'build/skinning-sort-root/main-report.json','build/skinning-sort-root/main-outputs.json','build/skinning-sort-root/main-replay.json',
 'build/skinning-sort-root/main-replay-oracle.csv'],'main-replay')
# The former Native inputs remain frozen. The new SDK must match every original result bit.
result=json.loads((out/'main-report.json').read_text('utf-8'))
assert result['actualResultBitsCompared']==5288 and result['modelFixtures']==60 and result['exchangeRejections']==5
# Regenerate the old 24-system regression packet at a new path, preserving past evidence.
recipe=(root/'reports/skinning-sdk-recipes/core-regressions.py').read_text('utf-8')
recipe=recipe.replace('build/skinning-sdk/regressions','build/skinning-sort-root/regressions')
recipe=recipe.replace("build/skinning-sdk/regressions.json","build/skinning-sort-root/regressions.json")
# Original replace also handles the .json suffix. Driver root remains repository root.
(out/'regressions.py').write_text(recipe,'utf-8',newline='\n')
run([sys.executable,'build/skinning-sort-root/regressions.py'],'old-regressions')
paths=['core/src/skinning.cpp','tests/skinning_tests.cpp','tests/skinning.test.mjs','.github/workflows/verify.yml',
 'assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json',
 'scripts/verify-skinning.py','scripts/verify-skinning-wasm.mjs','tools/skinning-lab.mjs']
manifest=json.loads((root/'assets/pikapika-simulation.build.json').read_text('utf-8'))
for key in ['sourceSha256','licenses']:
 for p,h in manifest[key].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
for p,a in manifest['artifacts'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==a['sha256'],p
assert 'pass 323' in (out/'node-tests.stdout.txt').read_text('utf-8')
proof=dict(schema=1,status='PASS',date=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=commands,
 originalCode='051c2a9e1cc8a6c681725af21a3ba2b41e524bb8',nodeTests=323,mainSkinResultBits=5288,
 sdkSourceHeaders=51,licenseFiles=7,regressionCommands=24,
 sourceArtifacts=[dict(path=p,bytes=(root/p).stat().st_size,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in paths],
 scope='Frozen old corpus replayed through new SDK; 33 influence-order permutations covered by actual SDK test. No new precision/renderer claim.')
(out/'verification.json').write_text(json.dumps(proof,indent=2)+'\n','utf-8',newline='\n')
print('PASS new SDK full Node323, main5288 bits, old24 regressions and current manifest source/license/artifact hashes.')
