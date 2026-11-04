"""Explain source-edit overlap without relabelling the original capture stable."""
from pathlib import Path
from hashlib import sha256
import json
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-flight-sdk'
directory=root/f'reports/{prefix}-checks/run-20261104-before'
rows=json.loads((directory/'baseline-commands.json').read_text())
changed=[{ 'command':r['name'],'authoredStable':r['authoredStable'],'paths':[p for p in set(r['authoredBefore'])|set(r['authoredAfter']) if r['authoredBefore'].get(p)!=r['authoredAfter'].get(p)]} for r in rows]
assert changed[0]['paths']==['core/include/pikapika/simulation_api.h'] and changed[1]['paths']==[]
files=['build/native/Release/pikapika-free-flight-legacy-probe.exe','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json','tools/free_flight_legacy_probe.cpp','scripts/verify-free-flight-legacy.mjs']
hashes={p:{'bytes':len((root/p).read_bytes()),'sha256':sha256((root/p).read_bytes()).hexdigest()} for p in files}
result={'schema':1,'overlap':changed,'usedPrebuiltInputs':hashes,'scope':'The public API header was being extended during the first prebuilt legacy Native execution. No compilation occurred in that capture. The existing executable (which includes dynamics, not simulation_api.h) and old SDK artifacts were used. Original authoredStable:false is preserved; it is not called a frozen-source build. Complete saved Native output and SDK bit records are compared separately. All final build/exchange runs require a frozen source snapshot.'}
(directory/'baseline-scope.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Original source-edit overlap retained; prebuilt baseline scope recorded.')
