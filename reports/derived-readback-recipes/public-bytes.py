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
names = ['index.html', 'docs/learn/index.html', 'docs/learn/diagrams/derived-readback.svg',
         'docs/DERIVED_MESH_BATCH_READ.md', 'docs/SIMULATION_ABI.md',
         'tools/derived-gpu-lab.html', 'tools/derived-gpu-lab.mjs', 'tools/derived-gpu-profile.mjs',
         'tools/derived-gpu-cases.mjs', 'tools/derived-profile.mjs', 'engine/simulation.mjs',
         'engine/renderer.mjs', 'engine/derived-render.mjs', 'assets/pikapika-simulation.build.json']
m = json.loads(subprocess.check_output(['git', 'show', revision + ':assets/pikapika-simulation.build.json'], cwd=root))
names += list(m['artifacts'])
rows = []
for p in names:
    expected = subprocess.check_output(['git', 'show', revision + ':' + p], cwd=root)
    url = 'https://tatata93.github.io/pikapikaengine/' + p + '?v=' + revision[:7]
    with urllib.request.urlopen(url, timeout=45) as response:
        actual = response.read()
        assert actual == expected, p
        rows.append(dict(path=p, url=url, status=response.status, bytes=len(actual),
                         sha256=hashlib.sha256(actual).hexdigest(), contentType=response.headers.get('Content-Type'),
                         etag=response.headers.get('ETag')))
result = dict(status='PASS', revision=revision, checkedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              reference='Exact Git commit blob bytes', files=rows)
(root / 'reports/derived-readback-http.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(dict(status='PASS', files=len(rows), bytes=sum(r['bytes'] for r in rows))))
