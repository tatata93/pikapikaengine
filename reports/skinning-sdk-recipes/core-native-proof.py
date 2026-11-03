import json,subprocess
from pathlib import Path
p=Path('build/skinning-sdk');records=[]
for cmd in [['cmake','--build','build/native','--config','Release','--target','pikapika_simulation_api_tests'],['build/native/Release/pikapika_simulation_api_tests.exe']]:
 r=subprocess.run(cmd,capture_output=True);records.append({'command':cmd,'exitCode':r.returncode,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace')})
 (p/'native-commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8');print('exit',r.returncode,' '.join(cmd));print(r.stdout.decode('utf-8',errors='replace'));print(r.stderr.decode('utf-8',errors='replace'))
 if r.returncode:raise SystemExit(r.returncode)
