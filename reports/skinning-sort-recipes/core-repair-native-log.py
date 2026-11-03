import hashlib,json,subprocess
from pathlib import Path
p=Path('build/skinning-sort');records=json.loads((p/'native-commands.json').read_text());original=records[0]
# The fixture captured under label native overwrote the initial build/run raw
# stdout. Preserve that fixture capture under its unambiguous name first.
for ext in ['stdout','stderr']:(p/('native-fixtures.'+ext+'.bin')).write_bytes((p/('native.'+ext+'.bin')).read_bytes())
command=['cmd.exe','/d','/c',str(p/'native.cmd')];r=subprocess.run(command,capture_output=True)
for ext,b in [('stdout',r.stdout),('stderr',r.stderr)]:
 (p/('native-build-run.'+ext+'.bin')).write_bytes(b)
 # Restore the old ambiguous alias to the build/run capture; the canonical
 # names are native-build-run and native-fixtures from this point forward.
 (p/('native.'+ext+'.bin')).write_bytes(b)
obj={'reason':'Initial native label reused for fixture capture, overwriting build/run raw. Fixture bytes preserved separately; unchanged final source build/run re-executed and compared with original recorded hashes.','command':command,'exitCode':r.returncode,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace'),'stdoutSha256':hashlib.sha256(r.stdout).hexdigest(),'stderrSha256':hashlib.sha256(r.stderr).hexdigest(),'stdoutMatchesOriginalRecordedHash':hashlib.sha256(r.stdout).hexdigest()==original['stdoutSha256'],'stderrMatchesOriginalRecordedHash':hashlib.sha256(r.stderr).hexdigest()==original['stderrSha256']}
(p/'native-log-repair.json').write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8');print('Native repair exit',r.returncode,'original hashes match',obj['stdoutMatchesOriginalRecordedHash'],obj['stderrMatchesOriginalRecordedHash'])
if r.returncode:raise SystemExit(r.returncode)
