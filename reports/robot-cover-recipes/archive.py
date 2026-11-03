import hashlib
import json
import pathlib

root=pathlib.Path(__file__).resolve().parents[2]
rows=[]
def copytree(source,target):
    for file in sorted(source.rglob('*')):
        if not file.is_file():continue
        data=file.read_bytes();destination=target/file.relative_to(source)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():assert destination.read_bytes()==data,destination
        else:destination.write_bytes(data)
        rows.append(dict(source=file.relative_to(root).as_posix(),path=destination.relative_to(root).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for directory in sorted((root/'build').glob('robot-cover-source-*')):
    copytree(directory,root/'reports/robot-cover-source'/directory.name)
for directory in sorted((root/'build/robot-cover-checks').glob('run-*')):
    copytree(directory,root/'reports/robot-cover-checks'/directory.name)
latest=json.loads((root/'build/robot-cover-checks/latest.json').read_bytes())
(root/'reports/robot-cover-checks/latest.json').write_bytes((json.dumps(latest,indent=2)+'\n').encode())
(root/'reports/robot-cover-archive.json').write_bytes((json.dumps(dict(status='PASS',scope='Exact original bytes; all retained source and check runs, including exploratory measurements',files=rows),indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(rows),bytes=sum(r['bytes'] for r in rows))))
