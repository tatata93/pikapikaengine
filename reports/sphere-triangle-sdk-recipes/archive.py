"""Archive selected proof text; never publish build binaries or overwrite runs."""
from hashlib import sha256
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
source, target = root / 'build/sphere-triangle-sdk-core', root / 'reports/sphere-triangle-sdk-standalone'
target.mkdir(exist_ok=False)
names = ['provenance.json', 'commands-final.json', 'compile-final.stdout.txt', 'compile-final.stderr.txt',
         'native-tests-final.stdout.txt', 'native-tests-final.stderr.txt', 'probe-final.stdout.txt', 'probe-final.stderr.txt',
         'transport-audit.json', 'input.rows', 'build-native.cmd', 'run-proof.py']
files = {}
for name in names:
    data = (source / name).read_bytes()
    (target / name).write_bytes(data)
    files[name] = {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
(target / 'archive.json').write_text(json.dumps({'schema': 1, 'files': files,
    'note': 'Original selected text outputs. Referenced exe/obj/lib files remain local and are not distributed. Full CMake build is separately recorded by check.py.'}, indent=2) + '\n', encoding='utf8')
print(json.dumps({'archivedFiles': len(files)}))
