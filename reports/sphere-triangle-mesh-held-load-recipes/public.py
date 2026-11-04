"""Read exact public run state and milestone bytes; no account mutation."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, re, subprocess, sys, urllib.request
root=Path(__file__).resolve().parents[2]
mode,commit=sys.argv[1:]
assert re.fullmatch('[0-9a-f]{40}',commit)
prefix='sphere-triangle-mesh-held-load'
def request(url):
    req=urllib.request.Request(url,headers={'User-Agent':'pikapikaengine-public-verification','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=30) as response:
        data=response.read(16*1024*1024+1)
        assert len(data)<=16*1024*1024
        return data
if mode=='status':
    runs=json.loads(request('https://api.github.com/repos/tatata93/pikapikaengine/actions/runs?head_sha='+commit+'&per_page=10'))['workflow_runs']
    assert all(r['head_sha']==commit for r in runs)
    result={'checked':datetime.now(timezone.utc).isoformat(),'commit':commit,'runs':runs}
    (root/f'reports/{prefix}-public-runs.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ['id','name','status','conclusion','html_url']} for r in runs]))
elif mode=='bytes':
    paths=['core/include/pikapika/sphere_triangle_mesh_held_load.hpp','core/src/sphere_triangle_mesh_held_load.cpp',
           'tests/sphere_triangle_mesh_held_load_tests.cpp','tests/sphere_triangle_mesh_held_load_fixtures.cpp','tests/sphere_triangle_mesh_held_load_test_support.hpp',
           'scripts/check-sphere-triangle-mesh-held-load.py','tests/sphere_triangle_mesh_held_load_reference_test.py',
           'CMakeLists.txt','docs/SPHERE_TRIANGLE_MESH_HELD_LOAD.md','docs/SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md',
           'docs/learn/diagrams/sphere-triangle-mesh-held-load.svg','docs/learn/index.html','docs/RESEARCH.md','docs/legal/REFERENCES.md','docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md',
           'assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json',
           'engine/simulation.mjs','engine/sphere-triangle-mesh-entry.mjs','tools/sphere-triangle-mesh-entry-lab.html','tools/sphere-triangle-mesh-entry-lab.mjs',
           'index.html','style.css','samples/app.mjs','samples/robot.mjs','samples/back-cover.mjs','assets/robot-back-cover.skin.json','assets/robot-back-cover.scene.json',
           'core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','scripts/build-simulation.mjs']
    html=subprocess.check_output(['git','show',commit+':index.html'],cwd=root).decode('utf-8')
    build=re.search(r'\?build=([a-f0-9]{16})',html).group(1)
    files=[]
    for path in paths:
        url='https://tatata93.github.io/pikapikaengine/'+path+'?v='+commit[:7]
        actual=request(url)
        expected=subprocess.check_output(['git','show',commit+':'+path],cwd=root)
        assert actual==expected,path+' public bytes differ'
        files.append({'path':path,'url':url,'bytes':len(actual),'sha256':sha256(actual).hexdigest()})
    result={'schema':1,'status':'PASS','commit':commit,'checked':datetime.now(timezone.utc).isoformat(),'build':build,'files':files}
    (root/f'reports/{prefix}-public-bytes.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','files':len(files),'bytes':sum(f['bytes'] for f in files),'build':build}))
else: raise ValueError('status or bytes required')
