"""Independently check saved public state, excerpts and browser records."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((root / name).read_text(encoding='utf-8'))


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


commit = '474e88cc5a545356f731c160f93c69e913a607ba'
build = '75daf0141409872f'
runs = read('reports/web-cache-public-runs.json')
assert runs['commit'] == commit and len(runs['runs']) == 2
for run in runs['runs']:
    assert run['head_sha'] == commit and run['status'] == 'completed' and run['conclusion'] == 'success'
    jobs = read('reports/web-cache-run-' + str(run['id']) + '.json')['jobs']
    assert jobs
    for job in jobs:
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(step['status'] == 'completed' and step['conclusion'] == 'success' for step in job['steps'])
        excerpt = read('reports/web-cache-job-' + str(job['id']) + '-excerpt.json')
        assert excerpt['job'] == job['id'] and excerpt['fullLines'] > len(excerpt['lines'])
ci = read('reports/web-cache-job-126249604931-excerpt.json')
text = '\n'.join(line['text'] for line in ci['lines'])
for marker in ['100% tests passed, 0 tests failed out of 30', '# tests 496', '# pass 496', '# fail 0', '# skipped 0',
               '"numericComparisons": 2841', '"nativeNumericBitComparisons": 2318', '"totalComparedNumericValues": 54410',
               '27 skin binding IO groups passed', 'derived mesh: 54 groups passed', '5 known-result assertions passed']:
    assert marker in text, marker
assert sum('warning:' in line['text'] for line in ci['lines']) == 36
http = read('reports/web-cache-public-bytes.json')
assert http['status'] == 'PASS' and http['commit'] == commit and http['build'] == build
assert len(http['files']) == 76 and len({file['path'] for file in http['files']}) == 76
line_endings = []
for file in http['files']:
    committed = subprocess.check_output(['git', 'show', commit + ':' + file['path']], cwd=root)
    assert {"bytes": len(committed), "sha256": sha256(committed).hexdigest()} == {k: file[k] for k in ['bytes', 'sha256']}, file['path']
    working = (root / file['path']).read_bytes()
    if working != committed:
        assert not file['path'].endswith('.wasm')
        assert working.replace(b'\r\n', b'\n') == committed.replace(b'\r\n', b'\n'), file['path']
        line_endings.append(file['path'])
browser = read('reports/web-cache-public-browser.json')
ui = read('reports/web-cache-public-ui.json')
assert browser['state'] == 'ready' and browser['failure'] is None and not browser['errors']
assert browser['pending'] is None and browser['renderer']['residentMeshes'] == 3
assert browser['counts']['queries'] == browser['counts']['validated'] == 20
assert browser['startup']['diagnostics']['buildId'] == build
assert browser['startup']['assetURL'] == 'https://tatata93.github.io/pikapikaengine/assets/robot-back-cover.skin.json?build=' + build
assert browser['authorSource'] == (root / 'assets/robot-back-cover.skin.json').read_text(encoding='utf-8').strip()
assert all(record['state'] == 'completed' for record in browser['records'])
assert any(record['clipSeconds'] == 1 for record in browser['records'])
assert ui['url'] == 'https://tatata93.github.io/pikapikaengine/?v=474e88c' and ui['pauseVisible']
assert ui['entry'].endswith('?build=' + build)
for key, url in ui['imports']['imports'].items():
    assert url == key + '?build=' + build
files = [p for p in sorted((root / 'reports').glob('web-cache-*')) if p.is_file() and p.name != 'web-cache-public-verification.json']
recipes = [p for p in sorted((root / 'reports/web-cache-recipes').glob('*.py'))]
report = {"schema": 1, "status": "PASS", "generated": datetime.now(timezone.utc).isoformat(),
          "commit": commit, "build": build, "nodeTests": 496, "ctest": 30, "compilerWarningLines": 36,
          "publicFiles": 76, "publicBytes": sum(file['bytes'] for file in http['files']), "browserQueries": 20,
          "workingTreeLineEndingDifferences": line_endings,
          "scope": "Finite cache invalidation and launch check; CI excerpts are not full logs; no new physics or performance claim",
          "files": {p.relative_to(root).as_posix(): digest(p) for p in files + recipes}}
(root / 'reports/web-cache-public-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['status', 'nodeTests', 'ctest', 'publicFiles', 'browserQueries']}))
