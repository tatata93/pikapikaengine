import hashlib
import json
import pathlib

root = pathlib.Path(__file__).resolve().parents[2]
files = []


def copy(source, target):
    source, target = root / source, root / target
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == data, str(target)
    else:
        target.write_bytes(data)
    files.append(dict(original=str(source.relative_to(root)).replace('\\', '/'),
                      path=str(target.relative_to(root)).replace('\\', '/'),
                      bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))


def tree(source, target):
    for path in sorted((root / source).rglob('*')):
        if path.is_file():
            copy(path.relative_to(root), pathlib.Path(target) / path.relative_to(root / source))


for name in ['native-byyygytv', 'sdk-r3xabv6w', 'web-tl1fgom3', 'native-5deqh1ew',
             'sdk-m2tud_m8', 'web-l3_827_i', 'node-arvrtsaz', 'node-pj7nbhcr',
             'syntax-n9pjd6yo', 'profile-cly94mhw']:
    tree('build/derived-readback-checks/' + name, 'reports/derived-readback-checks/' + name)
copy('build/native/Testing/Temporary/LastTest.log', 'reports/derived-readback-checks/LastTest.log')
profile = json.loads((root / 'build/derived-readback-checks/profile-cly94mhw/stdout.txt').read_text())
p = pathlib.Path(profile['runDirectory'])
tree(p.relative_to(root), 'reports/derived-readback-profile/' + p.name)
ref = pathlib.Path(json.loads((root / 'build/derived-readback-reference/latest.json').read_text())['runDirectory'])
tree(ref.relative_to(root), 'reports/derived-readback-reference/' + ref.name)
for mode, record in json.loads((ref / 'verification.json').read_text())['transports'].items():
    tree(pathlib.Path(record['outputDirectory']).relative_to(root), 'reports/derived-readback-' + mode)
    tree(pathlib.Path(record['referenceControls']['runDirectory']).relative_to(root), 'reports/derived-readback-controls-' + mode)
result = dict(status='PASS', files=files, fileCount=len(files),
              totalBytes=sum(f['bytes'] for f in files), byteIdentical=True,
              performanceQueriesAddedByArchive=0)
(root / 'reports/derived-readback-archive.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({k: v for k, v in result.items() if k != 'files'}))
