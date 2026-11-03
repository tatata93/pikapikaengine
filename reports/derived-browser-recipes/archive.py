import hashlib
import json
import pathlib
import shutil

root = pathlib.Path(__file__).resolve().parents[2]
rows = []
def copy(source, target):
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == data, str(target) + ' would overwrite different evidence'
    else:
        target.write_bytes(data)
    rows.append(dict(source=source.relative_to(root).as_posix(), path=target.relative_to(root).as_posix(),
                     bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
def tree(source, target):
    for file in sorted(source.rglob('*')):
        if file.is_file():
            copy(file, target / file.relative_to(source))

for family in ['derived-browser-checks', 'derived-browser-raw-checks']:
    source = root/'build'/family
    if source.exists():
        tree(source, root/'reports'/family)
selected = set()
source = root/'build/derived-browser-raw-checks'
for command_file in source.glob('run-*/commands.json'):
    for entry in json.loads(command_file.read_bytes()):
        if 'verificationRun' in entry:
            selected.add(pathlib.Path(entry['verificationRun']))
for run in (root/'build/derived-gpu-verification').glob('run-*'):
    command_file = run/'command.json'
    if command_file.exists() and 'derived-browser-' in command_file.read_text(encoding='utf-8'):
        selected.add(run)
for run in sorted(selected):
    tree(run, root/'reports/derived-browser-verifiers'/run.name)
record = dict(status='PASS', scope='Original build output bytes, including failed validator attempts; no newline conversion',
              files=rows)
(root/'reports/derived-browser-archive.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS', files=len(rows), bytes=sum(r['bytes'] for r in rows))))
