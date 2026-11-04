"""Preserve all preliminary independent-reference attempts without rewriting them."""
from hashlib import sha256
from pathlib import Path
import json, shutil
root=Path(__file__).resolve().parents[2]
source=root/'build/held-load-reference'
target=root/'reports/sphere-triangle-mesh-held-load-reference-attempts'
assert not target.exists()
files=[]
for number in range(1,6):
    name=f'run-{number:03d}'
    shutil.copytree(source/name,target/name)
    for original in (source/name).rglob('*'):
        if not original.is_file(): continue
        copied=target/original.relative_to(source)
        data=original.read_bytes()
        assert copied.read_bytes()==data
        files.append({'original':original.relative_to(root).as_posix(),'archived':copied.relative_to(root).as_posix(),
                      'bytes':len(data),'sha256':sha256(data).hexdigest()})
(target/'archive-map.json').write_text(json.dumps({'schema':1,'scope':'Preliminary agent runs; final root acceptance is separate. All five attempts exited zero; self-only and partial-control stages are distinguished by their original commands.','files':files},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(files)}))
