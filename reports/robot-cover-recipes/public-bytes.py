import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

root=pathlib.Path(__file__).resolve().parents[2]
revision=sys.argv[1]
assert len(revision)==40 and all(c in '0123456789abcdef' for c in revision)
names=['index.html','style.css','samples/app.mjs','samples/back-cover.mjs','samples/robot.mjs',
       'engine/renderer.mjs','engine/simulation.mjs','engine/skin-binding.mjs','engine/derived-render.mjs',
       'engine/motion.mjs','engine/portable.mjs','engine/math.mjs','engine/time.mjs','engine/physics.mjs','engine/strict-json.mjs',
       'assets/robot-back-cover.skin.json','assets/robot-back-cover.scene.json','assets/pikapika-core.wasm',
       'assets/pikapika-simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.build.json',
       'docs/ROBOT_BACK_COVER.md','docs/learn/index.html','docs/learn/diagrams/robot-back-cover.svg']
rows=[]
for p in names:
    expected=subprocess.check_output(['git','show',revision+':'+p],cwd=root)
    url='https://tatata93.github.io/pikapikaengine/'+p+'?v='+revision[:7]
    with urllib.request.urlopen(url,timeout=45) as response:
        actual=response.read();assert actual==expected,p
        rows.append(dict(path=p,url=url,status=response.status,bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest(),etag=response.headers.get('ETag')))
record=dict(status='PASS',revision=revision,checkedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            reference='Exact commit blobs, no Windows newline conversion',files=rows)
(root/'reports/robot-cover-http.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(dict(status='PASS',files=len(rows),bytes=sum(r['bytes'] for r in rows))))
