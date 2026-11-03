"""Check finite cache-fix scope, bytes and actual browser Source URL."""
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess

root = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=root)


def digest(path):
    data = (root / path).read_bytes()
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def authored(text):
    text = re.sub(r'<script type="importmap" id="engine-imports">[\s\S]*?</script>\s*', '', text)
    return re.sub(r'\?build=[0-9a-f]{16}', '', text)


local = json.loads((root / "reports/web-cache-local-verification.json").read_text(encoding='utf-8'))
assert local["status"] == "PASS" and local["assetsUnchanged"]
for path, expected in {**local["assets"], **local["sources"]}.items():
    assert digest(path) == expected, path
build = re.search(r'Web build ([0-9a-f]{16}): 45 versioned modules',
                  (root / 'reports/web-cache-build.txt').read_text(encoding='utf-8')).group(1)
browser = json.loads((root / "reports/web-cache-local-browser.json").read_text(encoding='utf-8'))
ui = json.loads((root / "reports/web-cache-local-ui.json").read_text(encoding='utf-8'))
assert browser["state"] == "ready" and not browser["failure"] and not browser["errors"]
assert browser["pending"] is None and browser["counts"]["queries"] == browser["counts"]["validated"]
assert browser["startup"]["diagnostics"]["buildId"] == build
assert browser["startup"]["assetURL"] == 'http://localhost:8080/assets/robot-back-cover.skin.json?build=' + build
assert browser["authorSource"] == (root / 'assets/robot-back-cover.skin.json').read_text(encoding='utf-8').strip()
assert browser["renderer"]["residentMeshes"] == 3
assert any(r["clipSeconds"] == 1 and r["state"] == 'completed' for r in browser["records"])
assert ui["pauseVisible"] and ui["entry"].endswith('?build=' + build)
for key, url in ui["imports"]["imports"].items():
    assert url == key + '?build=' + build
assert subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'core', 'engine', 'samples', 'assets', 'platform'], cwd=root).returncode == 0
pages = []
for path in git('diff', '--name-only', 'HEAD').decode().splitlines():
    if not path.endswith('.html'):
        continue
    old = git('show', 'HEAD:' + path).decode()
    new = (root / path).read_text(encoding='utf-8')
    assert authored(old) == authored(new), path + ' non-generated change'
    pages.append({"path": path, "generatedOnly": True, **digest(path)})
assert len(pages) == 21
evidence = ['reports/web-cache-before.txt', 'reports/web-cache-focused.txt',
            'reports/web-cache-local-browser.json', 'reports/web-cache-local-ui.json',
            'reports/web-cache-local.png']
for command in local['commands']:
    assert digest(command['log']) == {k: command[k] for k in ['bytes', 'sha256']}
    evidence.append(command['log'])
report = {"schema": 1, "status": "PASS", "parent": git('rev-parse', 'HEAD').decode().strip(),
          "build": build, "generatedPages": pages, "runtimeAndOriginalAssetsUnchanged": True,
          "browserQueries": browser['counts']['queries'], "evidence": {p: digest(p) for p in evidence}}
(root / 'reports/web-cache-scope-audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({"status": "PASS", "generatedPages": len(pages), "build": build}))
