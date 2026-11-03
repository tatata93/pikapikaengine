import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

root = pathlib.Path(__file__).resolve().parents[2]
revision = sys.argv[1]
assert len(revision) == 40 and all(c in '0123456789abcdef' for c in revision)
def blob(p):
    return subprocess.check_output(['git','show', revision+':'+p], cwd=root)
names = ['index.html', 'docs/learn/index.html', 'docs/learn/diagrams/derived-readback.svg',
         'docs/DERIVED_MESH_BROWSER_READBACK.md', 'tools/derived-gpu-lab.html',
         'tools/derived-gpu-lab.mjs', 'tools/derived-gpu-profile.mjs', 'tools/derived-gpu-cases.mjs',
         'tools/derived-profile.mjs', 'engine/simulation.mjs', 'engine/renderer.mjs',
         'engine/derived-render.mjs', 'engine/strict-json.mjs', 'assets/pikapika-simulation.build.json']
names += list(json.loads(blob('assets/pikapika-simulation.build.json'))['artifacts'])
rows = []
for name in names:
    url = 'https://tatata93.github.io/pikapikaengine/'+name+'?v='+revision[:7]
    with urllib.request.urlopen(url, timeout=45) as response:
        actual = response.read()
        assert actual == blob(name), name
        rows.append(dict(path=name, url=url, status=response.status, bytes=len(actual),
                         sha256=hashlib.sha256(actual).hexdigest(), etag=response.headers.get('ETag')))
record = dict(status='PASS', revision=revision,
              checkedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              reference='Exact commit blobs; not Windows newline conversion', files=rows)
(root/'reports/derived-browser-http.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS', files=len(rows), bytes=sum(r['bytes'] for r in rows))))
