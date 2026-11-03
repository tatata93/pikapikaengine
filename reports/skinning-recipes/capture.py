import json,subprocess,sys
from pathlib import Path
p=Path('build/skinning-proof')
records=[]
for command,name in [([str(p/'skinning-native.exe')],'native-tests.txt'),([str(p/'skinning-native.exe'),'--fixtures'],'native.json'),([str(p/'skinning-native.exe'),'--oracle'],'native-oracle.csv')]:
 r=subprocess.run(command,capture_output=True)
 (p/name).write_bytes(r.stdout)
 records.append({'command':command,'exitCode':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()})
 if r.returncode:raise SystemExit(r.returncode)
(p/'native-commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
print('Captured Native tests/65 fixtures/128 oracle rows')
