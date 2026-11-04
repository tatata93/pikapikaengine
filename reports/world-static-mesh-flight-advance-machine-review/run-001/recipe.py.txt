"""Read existing configured prototype artifacts; never compile or execute them.

This collection is exploratory machine review, not an extension of the accepted
guard leaf audit and not a complete clock/commit machine proof.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
CONFIGURED = ROOT / 'reports/world-static-mesh-flight-advance-checks/run-20261105-configured-001'
BUILD = ROOT / 'build/world-flight-advance-prototype/run-20261105-configured-001/build'


def identity(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    allowed = ROOT / 'reports/world-static-mesh-flight-advance-machine-review'
    if not out.is_relative_to(allowed) or out == allowed:
        raise ValueError('A fresh child of the machine-review directory is required')
    out.mkdir(parents=True, exist_ok=False)
    observation = json.loads((CONFIGURED / 'observation.json').read_text(encoding='utf-8'))
    profile = json.loads((ROOT / 'reports/world-static-mesh-flight-guard-binding-development/run-010/profile.json').read_text(encoding='utf-8'))
    dumpbin = Path(profile['compiler']['dumpbin'])
    obj = BUILD / 'advance_prototype_core.dir/Release/world_static_mesh_flight_advance.obj'
    exe = BUILD / 'Release/advance_configured.exe'
    paths = {ROOT / p for p in observation['commands'][0]['before']}
    paths.update((obj, exe, BUILD / 'Release/advance_prototype_core.lib',
                  Path(__file__).resolve(), CONFIGURED / 'observation.json',
                  CONFIGURED / 'compile-provenance.json', CONFIGURED / 'link-command.tlog.txt'))
    before = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(paths)}
    write(out / 'before.json', before)
    (out / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    commands = []
    try:
        for name, switches, artifact in (
            ('object-symbols', ['/symbols'], obj),
            ('object-disassembly', ['/disasm'], obj),
            ('object-relocations', ['/relocations'], obj),
            ('executable-headers', ['/headers'], exe),
            ('executable-disassembly', ['/disasm'], exe),
        ):
            argv = [str(dumpbin), '/nologo', *switches, str(artifact)]
            start = time.perf_counter()
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120, check=False)
            stdout = out / (name + '.stdout.txt')
            stderr = out / (name + '.stderr.txt')
            stdout.write_bytes(result.stdout)
            stderr.write_bytes(result.stderr)
            command = {'name': name, 'argv': argv, 'cwd': str(ROOT),
                       'exit': result.returncode, 'elapsedSeconds': time.perf_counter()-start,
                       'stdout': identity(stdout), 'stderr': identity(stderr)}
            write(out / (name + '.command.json'), command)
            commands.append(command)
            if result.returncode:
                raise RuntimeError('dumpbin failed: ' + name)
    finally:
        after = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(paths)}
        write(out / 'after.json', after)
        write(out / 'commands.json', commands)
        stable = before == after
        write(out / 'collection.json', {
            'schema': 1, 'status': 'COLLECTED' if stable and len(commands) == 5 and all(c['exit'] == 0 for c in commands) else 'FAILED',
            'scope': 'Read-only configured-001 exploratory disassembly; no execution, formal artifact acceptance, whole clock graph proof or commit atomicity proof.',
            'originalSourcesAndArtifactsUnchanged': stable,
            'configuredBuildId': observation['buildId'],
            'dumpbin': {'path': str(dumpbin), 'bytes': dumpbin.stat().st_size,
                        'sha256': hashlib.sha256(dumpbin.read_bytes()).hexdigest()},
            'commands': commands, 'formalArtifactAuditComplete': False})
        if not stable:
            raise RuntimeError('An input source or artifact changed during collection')
    print(json.dumps({'status': 'COLLECTED', 'commands': len(commands),
                      'originalSourcesAndArtifactsUnchanged': stable,
                      'output': out.relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    main()
