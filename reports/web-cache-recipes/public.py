"""Read public Actions state, or compare versioned Pages bytes to an exact commit."""
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
    req = urllib.request.Request(url, headers={
        "User-Agent": "pikapikaengine-public-verification", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        assert len(data) <= 8 * 1024 * 1024
        return data


if mode == 'status':
    url = 'https://api.github.com/repos/tatata93/pikapikaengine/actions/runs?head_sha=' + commit + '&per_page=10'
    runs = json.loads(request(url))['workflow_runs']
    assert all(run['head_sha'] == commit for run in runs)
    result = {"checked": datetime.now(timezone.utc).isoformat(), "commit": commit, "runs": runs}
    (root / 'reports/web-cache-public-runs.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{key: run[key] for key in ['id', 'name', 'status', 'conclusion', 'html_url']} for run in runs]))
elif mode == 'bytes':
    audit = json.loads((root / 'reports/web-cache-scope-audit.json').read_text(encoding='utf-8'))
    build = audit['build']
    local = json.loads((root / 'reports/web-cache-local-verification.json').read_text(encoding='utf-8'))
    html = subprocess.check_output(['git', 'show', commit + ':index.html'], cwd=root).decode()
    imports = json.loads(re.search(r'id="engine-imports">(.*?)</script>', html).group(1))['imports']
    paths = {key.removeprefix('./') for key in imports}
    paths.update(local['assets'])
    paths.update(page['path'] for page in audit['generatedPages'])
    paths.update(['style.css', 'scripts/build-web.mjs'])
    files = []
    for path in sorted(paths):
        url = 'https://tatata93.github.io/pikapikaengine/' + path + '?build=' + build
        actual = request(url)
        expected = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=root)
        assert actual == expected, path + ' public bytes differ'
        files.append({"path": path, "url": url, "bytes": len(actual), "sha256": sha256(actual).hexdigest()})
    result = {"schema": 1, "status": "PASS", "checked": datetime.now(timezone.utc).isoformat(),
              "commit": commit, "build": build, "files": files}
    (root / 'reports/web-cache-public-bytes.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({"status": "PASS", "files": len(files), "bytes": sum(f['bytes'] for f in files)}))
else:
    raise ValueError('status or bytes required')
