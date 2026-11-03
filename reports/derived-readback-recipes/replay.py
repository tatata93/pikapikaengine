"""Capture fresh Native fixtures and independently check both transports."""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time

root = pathlib.Path(__file__).resolve().parents[2]
base = root / 'build/derived-readback-reference'
base.mkdir(exist_ok=True)
out = pathlib.Path(tempfile.mkdtemp(prefix='run-', dir=base))
commands = []


def run(name, args):
    start = time.time()
    result = subprocess.run([str(a) for a in args], cwd=root, capture_output=True, timeout=120)
    for kind, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
        (out / (name + '.' + kind + '.txt')).write_bytes(data)
    commands.append(dict(name=name, args=[str(a) for a in args], exitCode=result.returncode,
                         elapsedSeconds=time.time()-start))
    (out / 'commands.json').write_bytes((json.dumps(commands, indent=2) + '\n').encode())
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace')[-5000:])
        print(result.stderr.decode('utf-8', errors='replace')[-4000:])
        raise RuntimeError(name + ' failed')
    return result.stdout


native = out / 'native40.json'
source = out / 'source11.json'
native.write_bytes(run('native40', [root / 'build/native/Release/pikapika_derived_mesh_tests.exe', '--fixtures']))
source.write_bytes(run('source11', [root / 'build/native/Release/pikapika-derived-probe.exe', '--fixtures']))
run('sdk', ['node', 'scripts/verify-derived-mesh-wasm.mjs', native, out / 'sdk-report.json',
            out / 'sdk-outputs.json', out / 'wasm40.json', source])
records = {}
for mode in ['single', 'batch']:
    stdout = run(mode, ['node', 'scripts/verify-derived-profile.mjs', native, source, '--readback', mode])
    report = json.loads(stdout)
    assert report['readback'] == mode and report['profiledQueries'] == 48
    assert report['nativeNumericBitComparisons'] == 2318
    assert report['referenceControls']['rejectedControls'] == 36
    records[mode] = report
sdk = json.loads((out / 'sdk-report.json').read_text(encoding='utf-8'))
assert sdk['numericComparisons'] == 2841
files = []
for path in out.iterdir():
    if path.is_file():
        data = path.read_bytes()
        files.append(dict(path=str(path.relative_to(root)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
summary = dict(status='PASS', sdkNumericComparisons=2841, transports=records, files=files,
               runDirectory=str(out), commands=commands)
(out / 'verification.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
(base / 'latest.json').write_bytes((json.dumps(dict(runDirectory=str(out)), indent=2) + '\n').encode())
print(json.dumps(dict(status='PASS', sdkNumericComparisons=2841, numericComparisonsPerTransport=2318,
                      independentNegativeControlsPerTransport=36, runDirectory=str(out))))
