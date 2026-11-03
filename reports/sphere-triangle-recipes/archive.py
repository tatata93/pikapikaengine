"""Archive only named original proof outputs, without executable/object binaries."""
from hashlib import sha256
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
source = root / 'build/sphere-triangle-core'
destination = root / 'reports/sphere-triangle-standalone'
destination.mkdir(parents=True, exist_ok=True)
copied = []
for path in sorted(source.iterdir()):
    if not path.is_file() or path.suffix not in ['.txt', '.json', '.cmd']:
        continue
    target = destination / path.name
    data = path.read_bytes()
    if target.exists():
        assert target.read_bytes() == data, 'refuse to replace an archived proof'
    else:
        target.write_bytes(data)
    copied.append({'path': target.relative_to(root).as_posix(), 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
reference = root / 'build/sphere-triangle-reference-integrated'
if reference.exists():
    for path in sorted(reference.glob('*.json')):
        target = root / 'reports' / ('sphere-triangle-' + path.name)
        data = path.read_bytes()
        if target.exists():
            assert target.read_bytes() == data, 'refuse to replace reference evidence'
        else:
            target.write_bytes(data)
        copied.append({'path': target.relative_to(root).as_posix(), 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
last_test = root / 'build/native/Testing/Temporary/LastTest.log'
if last_test.exists():
    data = last_test.read_bytes()
    target = root / 'reports/sphere-triangle-native-all.txt'
    if target.exists():
        assert target.read_bytes() == data, 'refuse to replace CTest detail'
    else:
        target.write_bytes(data)
    copied.append({'path': target.relative_to(root).as_posix(), 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
provenance = json.loads((destination / 'provenance.json').read_text(encoding='utf-8'))
for item in provenance['sources']:
    assert sha256((root / item['path']).read_bytes()).hexdigest() == item['sha256']
commands = json.loads((destination / 'commands-final.json').read_text(encoding='utf-8'))
for command in commands:
    assert command['exitCode'] == 0
    for stream in ['stdout', 'stderr']:
        path = destination / (command['label'] + '.' + stream + ('.json' if command['label'] == 'fraction-final' and stream == 'stdout' else '.txt'))
        data = path.read_bytes()
        assert len(data) == command[stream + 'Bytes'] and sha256(data).hexdigest() == command[stream + 'SHA256']
report = {'schema': 1, 'status': 'PASS', 'files': copied}
(root / 'reports/sphere-triangle-archive.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'files': len(copied)}))
