"""Capture the accepted baseline before adding the independent Native helper."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-plane-box-coverage'
out = ROOT/f'reports/{PREFIX}-baseline.json'
assert not out.exists()
prior = json.loads((ROOT/'reports/accelerated-pair-coverage-baseline.json').read_text(encoding='utf8'))
def info(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
for p, expected in prior['protected'].items():
    assert info((ROOT/p).read_bytes()) == expected, p
previous = [
    'core/include/pikapika/accelerated_pair_coverage.hpp',
    'core/src/accelerated_pair_coverage.cpp',
    'tests/accelerated_pair_coverage_tests.cpp',
    'tests/accelerated_pair_coverage_fixtures.cpp',
    'tests/accelerated_pair_coverage_test_support.hpp',
    'scripts/verify-accelerated-pair-coverage.py',
    'tests/accelerated_pair_coverage_reference_tests.py',
]
base = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
assert base.startswith('26b96cf')
protected = dict(prior['protected'])
for p in previous:
    raw = (ROOT/p).read_bytes()
    assert raw == subprocess.check_output(['git','show',f'{base}:{p}'],cwd=ROOT), p
    protected[p] = info(raw)
assert len(protected) == 369
allowed = {}
for p in ['CMakeLists.txt','.github/workflows/verify.yml','.gitattributes']:
    raw = (ROOT/p).read_bytes()
    blob = subprocess.check_output(['git','show',f'{base}:{p}'],cwd=ROOT)
    assert raw.replace(b'\r\n',b'\n') == blob, p
    allowed[p] = {'raw':info(raw),'gitBlob':info(blob),'gitBlobUtf8':blob.decode()}
entries = {p:info((ROOT/p).read_bytes()) for p in prior['generatedEntries']}
assert len(entries)==26
record = {'schema':1,'baseCommit':base,'created':datetime.now(timezone.utc).isoformat(),
          'protected':protected,'generatedEntries':entries,'permittedOldSources':allowed,
          'sdkManifest':prior['sdkManifest'],
          'priorPublicReceipt':'reports/accelerated-pair-coverage-public-verification.json',
          'scope':'369 accepted raw sources, all 26 generated HTML entries, and SDK remain unchanged. The standalone lesson article is outside those 26 entries and receives one original figure/paragraph. New helper is Native-only and conditional on explicit B/margin.'}
out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
old = (ROOT/'reports/accelerated-pair-coverage-recipes/check.py').read_text(encoding='utf8')
old = old.replace('accelerated-pair-coverage','accelerated-plane-box-coverage').replace('accelerated_pair_coverage','accelerated_plane_box_coverage').replace("== 362", "== 369")
check = ROOT/f'reports/{PREFIX}-recipes/check.py'
assert not check.exists()
check.write_text(old,encoding='utf8')
print(json.dumps({'status':'PASS','protected':len(protected),'entries':len(entries),'base':base}))
