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
    (root / 'reports/sphere-triangle-sdk-public-runs.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{key: run[key] for key in ['id', 'name', 'status', 'conclusion', 'html_url']} for run in runs]))
elif mode == 'bytes':
    paths = ['core/include/pikapika/simulation_api.h', 'core/src/simulation_api.cpp', 'core/include/pikapika/sphere_triangle.hpp', 'core/src/sphere_triangle.cpp', 'tests/sphere-triangle-sdk.test.mjs', 'tests/derived-profile-cli.test.mjs', 'tests/simulation_api_tests.cpp', 'tools/sphere_triangle_sdk_probe.cpp', 'scripts/verify-sphere-triangle-sdk.mjs', 'scripts/build-simulation.mjs', 'CMakeLists.txt', 'docs/SPHERE_TRIANGLE_SDK.md', 'docs/SPHERE_TRIANGLE_SDK_PLAN.md', 'docs/SPHERE_TRIANGLE.md', 'docs/PLAN.md', 'docs/learn/index.html', 'docs/learn/diagrams/sphere-triangle.svg', 'docs/legal/REFERENCES.md', 'docs/legal/ASSETS.md', 'docs/legal/DEPENDENCIES.md', 'index.html', 'style.css', 'samples/app.mjs', 'samples/back-cover.mjs', 'engine/simulation.mjs', 'engine/renderer.mjs', 'assets/pikapika-simulation.wasm', 'assets/pikapika-simulation.mjs', 'assets/pikapika-simulation.build.json', 'assets/robot-back-cover.skin.json', 'assets/robot-back-cover.scene.json']
    files = []
    for path in paths:
        query = '?build=f7448823095f375b' if path.endswith(('.mjs', '.wasm', '.skin.json', '.scene.json', '.build.json')) else '?v=' + commit[:7]
        url = 'https://tatata93.github.io/pikapikaengine/' + path + query
        actual = request(url)
        expected = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=root)
        assert actual == expected, path + ' public bytes differ'
        files.append({'path': path, 'url': url, 'bytes': len(actual), 'sha256': sha256(actual).hexdigest()})
    result = {'schema': 1, 'status': 'PASS', 'commit': commit, 'checked': datetime.now(timezone.utc).isoformat(), 'files': files}
    (root / 'reports/sphere-triangle-sdk-public-bytes.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'files': len(files), 'bytes': sum(file['bytes'] for file in files)}))
else:
    raise ValueError('status or bytes required')
