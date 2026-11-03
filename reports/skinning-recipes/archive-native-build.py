import json,subprocess
from pathlib import Path
p=Path('build/skinning-proof')
command=['cmd.exe','/d','/c',str(p/'build-native.cmd')]
r=subprocess.run(command,capture_output=True)
(p/'native-build.json').write_text(json.dumps({'command':command,'exitCode':r.returncode,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace'),'outputEncoding':'compiler OEM bytes preserved separately; decoded text replaces unknown bytes'},indent=2)+'\n',encoding='utf-8')
(p/'native-build-stdout.bin').write_bytes(r.stdout)
(p/'native-build-stderr.bin').write_bytes(r.stderr)
print('Native archived build exit',r.returncode)
raise SystemExit(r.returncode)
