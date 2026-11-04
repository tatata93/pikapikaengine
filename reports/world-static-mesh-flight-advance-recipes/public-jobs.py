"""Read exact public run/job state including timestamps omitted by connector.

Usage: python public-jobs.py FULL_COMMIT ENGINE_RUN PAGES_RUN FRESH_OUTPUT
No dispatch, rerun, authentication or repository setting change.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
API = 'https://api.github.com/repos/tatata93/pikapikaengine/actions/runs/'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('feature')
    parser.add_argument('engine', type=int)
    parser.add_argument('pages', type=int)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.feature) or min(args.engine, args.pages) <= 0:
        raise ValueError('Exact commit and positive run IDs required')
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'reports/world-static-mesh-flight-advance-public-checks'):
        raise ValueError('Output outside advance public checks')
    out.mkdir(parents=True, exist_ok=False)
    result = {'status': 'FAIL', 'feature': args.feature, 'observedUTC': datetime.now(timezone.utc).isoformat(),
              'scope': 'Read-only public REST exact run/head linkage, all job status and actual timestamp span. In-progress is not success. No log/numerical/UI proof.', 'responses': [], 'runs': {}}
    try:
        for name, run_id in [('engine', args.engine), ('pages', args.pages)]:
            values = {}
            for kind, suffix in [('run', ''), ('jobs', '/jobs?per_page=100')]:
                url = API + str(run_id) + suffix
                request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'pikapikaengine-public-job-timing'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    raw = response.read(4 * 1024 * 1024 + 1)
                    if response.status != 200 or len(raw) > 4 * 1024 * 1024:
                        raise ValueError('HTTP status/body bound')
                    meta = {'url': url, 'httpStatus': response.status, 'headers': list(response.headers.items()),
                            'bytes': len(raw), 'sha256': sha256(raw).hexdigest(), 'path': name + '-' + kind + '.json'}
                (out / meta['path']).write_bytes(raw)
                result['responses'].append(meta)
                values[kind] = json.loads(raw)
            run, jobs = values['run'], values['jobs']
            if run['id'] != run_id or run['head_sha'] != args.feature or len(jobs['jobs']) != jobs['total_count']:
                raise ValueError('Run/head or unpaginated job inventory mismatch')
            rows = []
            for job in jobs['jobs']:
                if job['run_id'] != run_id or job['head_sha'] != args.feature:
                    raise ValueError('Job/head linkage mismatch')
                row = {k: job[k] for k in ['id', 'name', 'status', 'conclusion', 'started_at', 'completed_at']}
                if job['started_at'] and job['completed_at']:
                    row['actualTimestampSeconds'] = (datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00')) - datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))).total_seconds()
                    if row['actualTimestampSeconds'] < 0:
                        raise ValueError('Negative job elapsed time')
                rows.append(row)
            result['runs'][name] = {'id': run_id, 'status': run['status'], 'conclusion': run['conclusion'], 'jobs': rows}
        result['status'] = 'OBSERVED'
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['status', 'runs', 'error'] if k in result}))
    return 0 if result['status'] == 'OBSERVED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
