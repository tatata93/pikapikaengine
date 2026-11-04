"""Archive only textual independent build proof, with an exact source map."""
from pathlib import Path
from hashlib import sha256
import json

root = Path(__file__).resolve().parents[2]
source = root / 'build/sphere-triangle-mesh-core'
target = root / 'reports/sphere-triangle-mesh-core-proof'
target.mkdir(exist_ok=False)
files = []
for p in sorted(source.iterdir()):
    if not p.is_file() or p.suffix not in ('.bin', '.json', '.py', '.cmd'):
        continue
    data = p.read_bytes()
    data.decode('utf8')
    name = p.name.removesuffix('.bin') + ('.txt' if p.suffix == '.bin' else '')
    (target / name).write_bytes(data)
    files.append({'source': p.relative_to(root).as_posix(), 'archive': (target / name).relative_to(root).as_posix(),
                  'bytes': len(data), 'sha256': sha256(data).hexdigest()})
(target / 'archive-map.json').write_text(json.dumps({'files': files, 'note': 'Exact text bytes; historical commands retain original build paths. No executables/objects archived.'}, indent=2) + '\n', encoding='utf8')
print(json.dumps({'archivedTextFiles': len(files)}))
