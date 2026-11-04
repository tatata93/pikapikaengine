from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json

root = Path(__file__).resolve().parents[2]
prefix = 'sphere-triangle-mesh-trajectory'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha256(data).hexdigest()}

local = read(root / f'reports/{prefix}-local-verification.json')
public = read(root / f'reports/{prefix}-public-bytes.json')
runs = read(root / f'reports/{prefix}-public-runs.json')
assert local['status'] == public['status'] == 'PASS'
assert len(runs['runs']) == 2
assert all(run['head_sha'] == public['commit'] and run['status'] == 'completed' and run['conclusion'] == 'success' for run in runs['runs'])
jobs = []
for run in runs['runs']:
    rows = read(root / f'reports/{prefix}-run-{run["id"]}.json')['jobs']
    assert rows and all(job['status'] == 'completed' and job['conclusion'] == 'success' and all(step['status'] == 'completed' and step['conclusion'] == 'success' for step in job['steps']) for job in rows)
    jobs += rows
engine = next(job for job in jobs if job['name'] == 'portable-core')
log = read(root / f'reports/{prefix}-job-{engine["id"]}-excerpt.json')
text = '\n'.join(line['text'] for line in log['lines'])
for marker in ['100% tests passed, 0 tests failed out of 35', '# tests 544', '# pass 544', '# fail 0', '# skipped 0', 'PASS 69 groups; 62 complete-input finite trajectory fixtures', '"packetNumericComparisons": 27160', '"modelNumericComparisons": 20808', '"cellAudits": 606', '"certifiedLeaves": 297', 'GNU 13.3.0']:
    assert marker in text, marker

def warnings(source):
    return [line['text'].split('warning:', 1)[1] for line in source['lines'] if 'warning:' in line['text']]

old = read(root / 'reports/sphere-triangle-mesh-lab-job-126329430810-excerpt.json')
assert len(warnings(log)) == 36 and warnings(log) == warnings(old)
assert len(public['files']) == 42
browser = read(root / f'reports/{prefix}-public-browser-verification.json')
assert browser['status'] == 'PASS' and (browser['numericBits'], browser['negativeZeroBits']) == (170, 20)
target = root / f'reports/{prefix}-public-verification.json'
paths = set((root / 'reports').glob(prefix + '-*.json'))
paths.update((root / f'reports/{prefix}-recipes').glob('*'))
paths.update((root / f'reports/{prefix}-public-browser').glob('*'))
paths.discard(target)
report = {
    'schema': 1, 'status': 'PASS', 'commit': public['commit'], 'checked': datetime.now(timezone.utc).isoformat(),
    'ctest': 35, 'node': 544, 'nativeGroups': 69, 'finiteFixtures': 62,
    'rational': read(root / f'reports/{prefix}-reference-final/reference.json'),
    'negativeControls': 71, 'warningDiagnosticsUnchanged': True, 'existingWarnings': 36,
    'newWarningAudit': 'New guard cpp and test each compiled with -Wall -Wextra -Wpedantic -Werror and strict floating-point flags.',
    'sanitizer': 'GNU ASan/UBSan instruments guard, mesh, primitive, interval, core, portable and guard tests; 69 groups pass. Linux Release and sanitized finite fixture bytes compared by cmp; independent rational checker accepts sanitized output.',
    'windowsSanitizer': 'No new local Windows sanitizer success claimed.',
    'publicFiles': len(public['files']), 'publicBytes': sum(file['bytes'] for file in public['files']),
    'publicBrowser': browser, 'ciJobs': jobs,
    'existingArtifacts': {'webBuild': '457dd1cda43de02c', 'exports': 74, 'sourceHeaders': 57, 'wasmBytes': 638777, 'protectedFilesUnchanged': 98, 'licenseNoticesUnchanged': 7},
    'ciEvidenceScope': 'All jobs/steps and bounded selected original log lines including every warning, not full logs.',
    'evidence': {path.relative_to(root).as_posix(): digest(path) for path in sorted(paths) if path.is_file()},
    'scope': 'Native-only proof for a defined linear sphere path against static triangle mesh. No new shared SDK/UI/World/TOI/response or game-contact integration. Fault-injected allocation/internal unreturned-work and naturally unreachable parameter-resolution branch remain unexecuted.'
}
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: report[key] for key in ['status', 'commit', 'ctest', 'node', 'nativeGroups', 'publicFiles', 'publicBytes']}))
