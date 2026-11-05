"""Combine263 successful actual transfers with one Git-only recipe transfer.

The264-request Pages probe remains FAIL: its recipe404 is preserved. The actual
manifest explicitly excludes that nested recipe; fetch its fixed GitHub source
instead. No failed HTTP response is promoted to a successful response.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
SHA = '0060ec8143bfcf7fc7f09d8968ae72510a151d18'
RECIPE = 'reports/world-static-mesh-flight-controlled-scheduler-recipes/check-full-fixtures.py'


def main():
    out = Path(__file__).resolve().parent / 'run-20261105-full-bytes-001'
    out.mkdir(exist_ok=False)
    (out / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    prior_path = ROOT / 'reports/world-static-mesh-flight-guard-public-checks/run-qfull-002/receipt.json'
    manifest_path = ROOT / 'reports/pages-deployment/run-20261105-controlled-scheduler-full-public-001/pages-manifest.json'
    prior = json.loads(prior_path.read_bytes())
    manifest = json.loads(manifest_path.read_bytes())
    assert prior['commit'] == manifest['head'] == SHA
    assert prior['status'] == 'FAIL' and prior['fileCount'] == 264 and prior['failedPaths'] == [RECIPE]
    assert [x for x in manifest['excluded'] if x['path'] == RECIPE][0]['reason'] == 'nested-report-evidence-not-runtime'
    assert not any(x['path'] == RECIPE for x in manifest['files'])
    rows = [x for x in prior['files'] if x['path'] != RECIPE]
    assert len(rows) == 263 and all(x['status'] == 'PASS' and x['httpStatus'] == 200 and x['expected'] == x['actual'] for x in rows)
    for row in rows:
        raw = (prior_path.parent / row['rawPath']).read_bytes()
        assert len(raw) == row['actual']['bytes'] and hashlib.sha256(raw).hexdigest() == row['actual']['sha256']
    expected = subprocess.check_output(['git', 'show', SHA + ':' + RECIPE], cwd=ROOT)
    url = 'https://raw.githubusercontent.com/tatata93/pikapikaengine/' + SHA + '/' + RECIPE
    request = urllib.request.Request(url, headers={'User-Agent': 'pikapikaengine-exact-source-check', 'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read(16777217)
        metadata = {'url': url, 'httpStatus': response.status, 'finalURL': response.geturl(), 'headers': list(response.headers.items())}
    (out / 'github-recipe.py.txt').write_bytes(raw)
    metadata.update(expected={'bytes': len(expected), 'sha256': hashlib.sha256(expected).hexdigest()},
                    actual={'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                    status='PASS' if metadata['httpStatus'] == 200 and raw == expected else 'FAIL')
    (out / 'github-source-transfer.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf8')
    assert metadata['status'] == 'PASS'
    result = {'schema': 1, 'status': 'PASS', 'commit': SHA, 'matchedTransfers': 264,
              'channels': {'pages': 262, 'githubSource': 2},
              'matchedBytes': sum(x['actual']['bytes'] for x in rows) + len(raw),
              'successfulPriorTransfers': 263, 'priorReceipt': str(prior_path.relative_to(ROOT)),
              'priorReceiptStatusUnchanged': 'FAIL', 'expectedExcludedRecipe404': RECIPE,
              'explicitGitHubRecipeTransfer': metadata,
              'scope': '263 preserved PASS transfers and1 distinct exact GitHub source transfer; original264-request Pages probe still FAIL. Source-byte distribution only; no numerical or GNU acceptance.'}
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['status', 'matchedTransfers', 'matchedBytes', 'channels']}))


if __name__ == '__main__':
    main()
