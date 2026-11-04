"""Bind actual finite GNU, Pages, distribution and READY observations to d302."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
COMMIT = 'd302f5b760307b8a3b023658d251bba3d023fc49'
BASE = 'reports/world-static-mesh-flight-guard-public-checks/'
GNU = BASE + 'run-20261105-gnu-collected-002/result.json'
BYTES = BASE + 'run-20261105-movhpd-public-bytes-001/receipt.json'
OBSERVATION = BASE + 'run-20261105-movhpd-public-ready-002/receipt.json'
PAGES = BASE + 'run-20261105-gnu-acceptance-001/pages-jobs.json'
REST = BASE + 'run-20261105-movhpd-final-status-001/runs.json'

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf8'))

def stamp(name):
    raw = (ROOT / name).read_bytes()
    return {'path': name, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

gnu, distribution, ui = read(GNU), read(BYTES), read(OBSERVATION)
need(gnu['status'] == 'PASS' and gnu['commit'] == COMMIT and gnu['inputsStable'] is True,
     'Actual final GNU collection must pass')
need(gnu['steps'] == 25 and gnu['ctest'] == 46 and gnu['node'] == 684 and
     gnu['finalHelper']['finiteFixtures'] == 51 and gnu['warnings']['sameMultiset'] is True,
     'Expected observed GNU scope')
need(len(gnu['earlyNormalAudit']['normalSourceProfile']['sources']) == 5 and
     'sourceSet' not in gnu['earlyNormalAudit']['normalSourceProfile'], 'Actual legacy five-source profile format')
need(distribution['status'] == 'PASS' and distribution['commit'] == COMMIT and
     distribution['fileCount'] == 201 and distribution['bytes'] == 4856375 and
     not distribution['failedPaths'], 'Actual exact-commit selected distribution')
pages = read(PAGES)['jobs']
need(len(pages) == 3 and all(j['run_id'] == 41882793153 and j['status'] == 'completed' and
     j['conclusion'] == 'success' for j in pages), 'Actual Pages3 success')
for run_id in (41883086801, 41882793153):
    runs = [r for r in read(REST)['workflow_runs'] if r['id'] == run_id]
    need(len(runs) == 1 and runs[0]['head_sha'] == COMMIT and
         runs[0]['status'] == 'completed' and runs[0]['conclusion'] == 'success', 'REST commit/run linkage')
need(ui['commit'] == COMMIT and ui['actualBrowserState'] == 'C++ WASM / WEBGPU READY' and
     ui['sortieTestedForThisCommit'] is False, 'Actual READY observation scope')
for key in ('readyScreenshot', 'readyAX'):
    need(stamp(ui[key]['path']) == ui[key], 'Saved browser evidence unchanged')
need('C++ WASM / WEBGPU READY' in (ROOT / ui['readyAX']['path']).read_text(encoding='utf8'),
     'Actual READY AX text')
result = {'schema': 1, 'status': 'PUBLIC_FINITE_ACCEPTED', 'acceptedCommit': COMMIT,
          'collected': datetime.now(timezone.utc).isoformat(),
          'engineRun': 41883086801, 'pagesRun': 41882793153,
          'GNU': stamp(GNU), 'distribution': stamp(BYTES), 'browserObservation': stamp(OBSERVATION),
          'pagesJobs': stamp(PAGES), 'publicREST': stamp(REST),
          'local': stamp('reports/world-static-mesh-flight-guard-local-verification.json'),
          'actualSources': gnu['earlyNormalAudit']['normalSourceProfile']['sources'],
          'requiredEngineStages': 25, 'ctest': 46, 'nodeTests': 684,
          'fixtureComparison': gnu['finalHelper']['comparison'],
          'sourceProfileFormat': 'Legacy five-source profile; no sourceSet field was emitted by this accepted feature.',
          'warnings': gnu['warnings'], 'readyScreenshot': ui['readyScreenshot'],
          'scope': 'Five-source Native read-only World guard at the accepted commit. Finite numerical behavior, three leaf machine graphs and actual caller/strict-command gate;39-source sanitizer development and selected distribution/READY are separate observations.',
          'excluded': ['Uncommitted seven-source Native advance and its new local lesson.',
                       'Entire caller/clock/commit symbolic machine proof, new browser numerical API and World response.',
                       'This-commit sortie, all repository HTTP paths, all inputs/platforms, natural allocation/nonreturn fault injection.']}
out = ROOT / 'reports/world-static-mesh-flight-guard-public-verification.json'
with out.open('x', encoding='utf8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': result['status'], 'acceptedCommit': COMMIT}))
