"""Replay actual visible-browser DTOs through the existing independent Fraction oracle.
The frozen SDK suite is retained for the oracle's explicit adversarial coverage gates.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import sys
root=Path(__file__).resolve().parents[2]
phase=sys.argv[1]
assert phase in ('local','public')
spec=importlib.util.spec_from_file_location('mesh_reference',root/'scripts/verify-sphere-triangle-mesh.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
base=oracle.load(root/'reports/sphere-triangle-mesh-lab-checks/run-20261104-root/sdk/wasm-fixtures.json')
browser=oracle.load(root/f'reports/sphere-triangle-mesh-lab-{phase}-browser/replay.json')
assert len(base['fixtures'])==45 and len(browser['fixtures'])==21
baseline=oracle.verify(base)
combined={**base,'fixtures':base['fixtures']+browser['fixtures']}
output=root/f'reports/sphere-triangle-mesh-lab-{phase}-browser/combined-rational-fixtures.json'
output.write_text(json.dumps(combined,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
actual=oracle.verify(oracle.load(output))
def components(report):return report['primitiveReference']['referenceComponents']+report['aggregateReferenceComponents']
report={'schema':1,'status':'PASS','phase':phase,'generated':datetime.now(timezone.utc).isoformat(),'baselineFixtures':45,'actualBrowserPackets':21,'baselineComponents':components(baseline),'combinedComponents':components(actual),'browserAdditionalComponents':components(actual)-components(baseline),'combined':actual,'scope':'Independent rational inclusion of actual visible browser source/results; baseline suite retained for coverage gates, no physics fallback.'}
(root/f'reports/sphere-triangle-mesh-lab-{phase}-rational-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','phase','actualBrowserPackets','baselineComponents','combinedComponents','browserAdditionalComponents']}))
