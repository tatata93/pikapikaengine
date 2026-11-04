"""Read exact public Actions state or compare this milestone's Pages resources."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess
import sys
import urllib.request

root = Path(__file__).resolve().parents[2]
mode, commit = sys.argv[1:]
assert re.fullmatch(r'[a-f0-9]{40}', commit)


def request(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'pikapikaengine-public-verification', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        assert len(data) <= 8 * 1024 * 1024
        return data


if mode == 'status':
    url = 'https://api.github.com/repos/tatata93/pikapikaengine/actions/runs?head_sha=' + commit + '&per_page=10'
    runs = json.loads(request(url))['workflow_runs']
    assert all(run['head_sha'] == commit for run in runs)
    result = {'checked': datetime.now(timezone.utc).isoformat(), 'commit': commit, 'runs': runs}
    (root / 'reports/sphere-triangle-mesh-entry-public-runs.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{key: run[key] for key in ['id', 'name', 'status', 'conclusion', 'html_url']} for run in runs]))
elif mode == 'bytes':
    paths = ["scripts/verify-sphere-triangle-mesh-trajectory-native-sdk.py","scripts/verify-sphere-triangle-mesh-trajectory-wasm-wire.mjs","tests/sphere_triangle_mesh_trajectory_sdk_tests.cpp","tools/sphere_triangle_mesh_trajectory_sdk_probe.cpp","scripts/build-simulation.mjs","docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_ABI.md","docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_SDK_PLAN.md","docs/learn/diagrams/sphere-triangle-mesh-trajectory-exchange.svg"] + ['core/include/pikapika/sphere_triangle_mesh_trajectory.hpp','core/src/sphere_triangle_mesh_trajectory.cpp','tests/sphere_triangle_mesh_trajectory_tests.cpp','scripts/verify-sphere-triangle-mesh-trajectory.py','tests/sphere_triangle_mesh_trajectory_reference_tests.py','CMakeLists.txt','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY.md','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-trajectory.svg','docs/learn/index.html','docs/learn/learn.css','docs/PLAN.md','docs/RESEARCH.md','docs/legal/REFERENCES.md','docs/legal/DEPENDENCIES.md','docs/legal/ASSETS.md','index.html','style.css','samples/app.mjs','samples/back-cover.mjs','samples/robot.mjs','engine/simulation.mjs','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json','assets/robot-back-cover.skin.json','assets/robot-back-cover.scene.json','tools/sphere-triangle-mesh-lab.html','tools/sphere-triangle-mesh-lab.mjs','core/include/pikapika/sphere_triangle.hpp','core/src/sphere_triangle.cpp','core/include/pikapika/sphere_triangle_mesh.hpp','core/src/sphere_triangle_mesh.cpp','core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','third_party/emscripten-6.0.13/EMSCRIPTEN-LICENSE.txt','third_party/emscripten-6.0.13/LIBCXX-LICENSE.txt','third_party/emscripten-6.0.13/LIBCXXABI-LICENSE.txt','third_party/emscripten-6.0.13/LIBUNWIND-LICENSE.txt','third_party/emscripten-6.0.13/COMPILER-RT-LICENSE.txt','third_party/emscripten-6.0.13/MUSL-COPYRIGHT.txt','third_party/emscripten-6.0.13/MUSL-MATH-NOTICES.txt']
    paths += ['engine/sphere-triangle-mesh-trajectory.mjs','tests/sphere_triangle_mesh_trajectory_sdk.test.mjs','scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_JS.md','docs/learn/diagrams/sphere-triangle-mesh-trajectory-owned.svg','reports/sphere-triangle-mesh-trajectory-js-browser/index.html']
    paths += ['tools/sphere-triangle-mesh-trajectory-lab.html','tools/sphere-triangle-mesh-trajectory-lab.mjs','tests/sphere-triangle-mesh-trajectory-lab.test.mjs','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_LAB.md','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_LAB_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-trajectory-lab.svg','scripts/build-web.mjs','tests/web-build.test.mjs']
    paths += ['core/include/pikapika/sphere_triangle_mesh_entry.hpp','core/src/sphere_triangle_mesh_entry.cpp','tests/sphere_triangle_mesh_entry_tests.cpp','tests/sphere_triangle_mesh_entry_fixture.hpp','scripts/verify-sphere-triangle-mesh-entry.py','tests/sphere_triangle_mesh_entry_reference_tests.py','docs/SPHERE_TRIANGLE_MESH_ENTRY.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-entry.svg']
    assert len(paths)==len(set(paths))
    build_html = subprocess.check_output(['git','show',commit+':tools/sphere-triangle-mesh-lab.html'],cwd=root).decode('utf-8')
    build = re.search(r'\?build=([0-9a-f]{16})', build_html).group(1)
    files = []
    for path in paths:
        query = '?build=' + build if path.endswith(('.mjs', '.wasm', '.skin.json', '.scene.json', '.build.json')) else '?v=' + commit[:7]
        url = 'https://tatata93.github.io/pikapikaengine/' + path + query
        actual = request(url)
        expected = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=root)
        assert actual == expected, path + ' public bytes differ'
        files.append({'path': path, 'url': url, 'bytes': len(actual), 'sha256': sha256(actual).hexdigest()})
    result = {'schema': 1, 'status': 'PASS', 'commit': commit, 'checked': datetime.now(timezone.utc).isoformat(), 'files': files}
    (root / 'reports/sphere-triangle-mesh-entry-public-bytes.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'files': len(files), 'bytes': sum(file['bytes'] for file in files)}))
else:
    raise ValueError('status or bytes required')
