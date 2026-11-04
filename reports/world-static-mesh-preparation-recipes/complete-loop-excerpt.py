"""Preserve literal loop terminators omitted by the first bounded log selector."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[2]
path = root / 'reports/world-static-mesh-preparation-job-126541504170-excerpt.json'
report = json.loads(path.read_text(encoding='utf-8'))
rows = [{"line":10637,"text":"2026-11-04T11:32:01.9021144Z \u001b[36;1mdone\u001b[0m"},{"line":10776,"text":"2026-11-04T11:32:41.3381215Z \u001b[36;1mdone\u001b[0m"},{"line":11103,"text":"2026-11-04T11:34:38.3575049Z \u001b[36;1mdone\u001b[0m"},{"line":11791,"text":"2026-11-04T11:36:40.5038689Z \u001b[36;1mdone\u001b[0m"}]
assert report['jobId'] == 126541504170 and report['commit'] == '6608bc3963a7eaca1ac8a9d40f3ae5d76f93d05e'
table = {row['line']: row for row in report['lines']}
for row in rows:
    assert re.sub(r'\x1b\[[0-9;]*m', '', row['text'].split(' ', 1)[1]).strip() == 'done'
    if row['line'] in table:
        assert row == table[row['line']]
    table[row['line']] = row
report['lines'] = [table[n] for n in sorted(table)]
report['selectionRepair'] = 'Literal done loop terminators restored from the same fetched job log after aggregate001 rejected their omission. No CI result or product changed.'
path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'addedLoopRows': len(rows), 'selectedLines': len(table)}))
