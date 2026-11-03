import datetime, hashlib, json, pathlib, subprocess, sys, time

root = pathlib.Path(__file__).resolve().parents[2]
out = root / 'build/skinning-sdk/regressions'
out.mkdir(exist_ok=True)
proof = {'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'commands': [], 'scope': 'Frozen prior finite corpora replayed through current SDK63; not a universal error bound.'}
wasm = (root / 'assets/pikapika-simulation.wasm').read_bytes()
proof.update(sharedWasmBytes=len(wasm), sharedWasmSHA256=hashlib.sha256(wasm).hexdigest())
commands = json.loads((root / 'reports/motion-regressions.json').read_text('utf-8'))['commands']
commands.append({'label': 'motion shared WASM bit replay', 'command': ['node', 'scripts/verify-motion-wasm.mjs',
    'reports/motion-native-fixtures.json', 'build/motion-proof/regression-motion-parity.json',
    'build/motion-proof/regression-motion-outputs.json', 'reports/motion-native-oracle.csv']})
for item in commands:
    args = [a.replace('build/motion-proof/', 'build/skinning-sdk/regressions/') for a in item['command']]
    if args[0].lower().endswith('python.exe'):
        args[0] = sys.executable
    started = time.monotonic()
    run = subprocess.run(args, cwd=root, capture_output=True, encoding='utf-8', timeout=180)
    if item['label'] == 'strict support final Native fixtures' and run.returncode == 0:
        (out / 'regression-support-native-fixtures.json').write_bytes(run.stdout.encode('utf-8'))
    proof['commands'].append(dict(label=item['label'], command=args, exitCode=run.returncode,
        stdout=run.stdout, stderr=run.stderr, elapsedSeconds=time.monotonic()-started))
    print(item['label'], run.returncode, flush=True)
    if run.returncode:
        print(run.stdout, run.stderr)
        break
proof.update(finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='PASS' if len(proof['commands']) == len(commands) and all(r['exitCode'] == 0 for r in proof['commands']) else 'FAIL')
(root / 'build/skinning-sdk/regressions.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', 'utf-8', newline='\n')
sys.exit(proof['status'] != 'PASS')
