"""Compare saved actual transaction inputs/owned guards to the earlier same-build corpus.

This never executes a binary or substitutes a new query. It does not validate
the new World commit/clock mathematically; that is a separate independent gate.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-legacy-integration-001/new-world-guard.json'
NEW = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-capture-001/transactions.json'
HELPER = ROOT / 'reports/world-static-mesh-flight-guard-recipes/verify-gnu.py'
OUT = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-provenance-001'

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def stamp(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf8', newline='\n')

OUT.mkdir(parents=True, exist_ok=False)
(OUT / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
watched = (OLD, NEW, HELPER, Path(__file__).resolve())
before = [stamp(p) for p in watched]
write('before.json', before)
result = {'schema': 1, 'status': 'FAIL', 'scope': 'Saved actual same-build input/owned-guard JSON provenance. Exact key/array order, scalar types and binary64 signed zero; no normalization, no re-query, no new binary run or independent transaction/clock proof.'}
try:
    spec = importlib.util.spec_from_file_location('transaction_provenance_helpers', HELPER)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    old, new = helper.load(OLD), helper.load(NEW)
    need(old['kind'] == 'world-static-mesh-flight-guard-fixtures' and
         new['kind'] == 'world-static-mesh-flight-advance-transaction-fixtures', 'Actual packet kinds')
    need(len(old['fixtures']) == len(new['fixtures']) == 51, 'Actual paired51 corpus')
    need(helper.exact_tree(old['layoutSizes']) == helper.exact_tree(new['layoutSizes']), 'Observed same-build layout metadata')
    rows = []
    for index, (prior, current) in enumerate(zip(old['fixtures'], new['fixtures'])):
        need(prior['name'] == current['name'], 'Same original case order/name at ' + str(index))
        need(helper.exact_tree(prior['input']) == helper.exact_tree(current['input']), 'Original input differs at ' + str(index))
        guard = current['report']['guard']
        row = {'ordinal': index, 'name': current['name'], 'inputExact': True, 'actualGuardPresent': guard is not None}
        if guard is not None:
            need(helper.exact_tree(prior['result']) == helper.exact_tree(guard), 'Actual owned guard differs at ' + str(index))
            row['ownedGuardExact'] = True
        else:
            row.update(ownedGuardExact=None, advanceReason=current['report']['reason'],
                       advanceStage=current['report']['failure']['stage'])
            need(current['report']['failure']['stage'] == 'clock' and
                 current['report']['work']['guardQueriesAttempted'] == 0 and
                 current['report']['work']['guardQueriesReturned'] == 0,
                 'Absent guard must be the actual pre-guard clock refusal')
        rows.append(row)
    result.update(status='PASS', inputPairs=51, actualOwnedGuardsCompared=sum(row['actualGuardPresent'] for row in rows),
                  actualPreGuardClockRefusals=sum(not row['actualGuardPresent'] for row in rows),
                  comparison='No normalization. All serialized guard fields match; the old format omits the non-normative outer guard message, which new transactions preserve separately.', rows=rows)
except Exception as error:
    result.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
finally:
    after = [stamp(p) for p in watched]; write('after.json', after)
    result['inputsAndRecipeUnchanged'] = before == after
    if before != after:
        result.update(status='FAIL', error='Input/helper/recipe changed')
    write('result.json', result)
print(json.dumps({k: result[k] for k in ('status', 'inputPairs', 'actualOwnedGuardsCompared', 'actualPreGuardClockRefusals', 'inputsAndRecipeUnchanged', 'error') if k in result}))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
