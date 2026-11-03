import hashlib,json,subprocess
from pathlib import Path
p=Path('build/skinning-sort')
old=json.loads(Path('assets/pikapika-simulation.build.json').read_text())
(p/'before-license-hashes.json').write_text(json.dumps({f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in old['licenses']},indent=2)+'\n',encoding='utf-8')
command=['node','scripts/build-simulation.mjs'];r=subprocess.run(command,capture_output=True)
(p/'sdk-build.stdout.txt').write_bytes(r.stdout);(p/'sdk-build.stderr.txt').write_bytes(r.stderr)
(p/'sdk-build-command.json').write_text(json.dumps({'command':command,'exitCode':r.returncode,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace')},indent=2)+'\n',encoding='utf-8')
print(r.stdout.decode('utf-8',errors='replace'));print(r.stderr.decode('utf-8',errors='replace'));raise SystemExit(r.returncode)
