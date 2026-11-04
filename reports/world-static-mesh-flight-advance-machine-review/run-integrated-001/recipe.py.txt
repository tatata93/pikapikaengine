"""Read-only integrated Release clock/commit exploration; not machine attestation.

Run only after the integration build owner declares the artifacts complete.
Never compiles, links, executes the target, or rewrites an earlier collection.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD = ROOT / 'build/wfa2'
SCOPE = ('Read-only integrated Release disassembly exploration with map/COFF/PE correspondence. '
         'Not a complete clock graph, exception/alias/store-dominance proof, compiler attestation, '
         'extension of the accepted leaf audit, or formal artifact acceptance.')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write('\n')


def excerpt(path, lines):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines)+'\n')


def correlate(out, obj_path, exe_path, map_path):
    obj, exe = obj_path.read_bytes(), exe_path.read_bytes()
    machine, count, _, _, _, optional, _ = struct.unpack_from('<HHLLLHH', obj)
    require(machine == 0x8664 and optional == 0, 'Expected standard x64 COFF object')
    require(len(obj) >= 20+40*count, 'Truncated COFF section table')
    pe = struct.unpack_from('<L', exe, 0x3c)[0]
    require(exe[pe:pe+4] == b'PE\0\0', 'Missing PE signature')
    pe_machine, pe_count, _, _, _, pe_optional, _ = struct.unpack_from('<HHLLLHH', exe, pe+4)
    require(pe_machine == 0x8664 and struct.unpack_from('<H', exe, pe+24)[0] == 0x20b,
            'Expected x64 PE32+')
    image_base = struct.unpack_from('<Q', exe, pe+24+24)[0]
    sections = []
    for n in range(pe_count):
        section = struct.unpack_from('<8sLLLLLLHHL', exe, pe+24+pe_optional+40*n)
        name, _, rva, size, raw, _, _, _, _, flags = section
        sections.append((name.rstrip(b'\0').decode('ascii'), rva, raw, size, flags))
    symbols = (out / 'object-symbols.stdout.txt').read_text(encoding='utf-8', errors='replace').splitlines()
    dis = (out / 'object-disassembly.stdout.txt').read_text(encoding='utf-8', errors='replace').splitlines()
    executable = (out / 'executable-disassembly.stdout.txt').read_text(encoding='utf-8', errors='replace').splitlines()
    map_lines = map_path.read_text(encoding='utf-8', errors='replace').splitlines()
    mapped_symbols = {}
    for i, line in enumerate(map_lines):
        match = re.match(r'^\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+(\S+)\s+([0-9A-Fa-f]{16})(?:\s|$)', line)
        if match:
            mapped_symbols.setdefault(match.group(1), []).append(
                {'line': i+1, 'text': line, 'virtualAddress': hex(int(match.group(2), 16))})
    findings = []
    for name in ['advance', 'clock_preflight', 'commit', 'prepare_commit', 'validate_commit', 'origin_preflight']:
        matches = [(i+1, line) for i, line in enumerate(symbols)
                   if '| ?'+name+'@' in line and 'notype ()' in line]
        entry = {'name': name, 'objectSymbolMatches': matches}
        findings.append(entry)
        if len(matches) != 1:
            entry['limitation'] = 'Function symbol absent or ambiguous; no inferred replacement.'
            continue
        symbol_line, symbol = matches[0]
        decorated = symbol.split('|', 1)[1].strip().split(' ', 1)[0]
        section = int(re.search(r'SECT([0-9A-F]+)', symbol).group(1), 16)
        require(1 <= section <= count, 'COFF section out of range')
        sec = struct.unpack_from('<8sLLLLLLHHL', obj, 20+40*(section-1))
        _, _, _, size, raw, reloc, _, reloc_count, _, _ = sec
        code = obj[raw:raw+size]
        require(len(code) == size and size > 0, 'Truncated/empty function section')
        masked, relocations = set(), []
        for i in range(reloc_count):
            address, symbol_index, kind = struct.unpack_from('<LLH', obj, reloc+10*i)
            require(kind in (2, 3, 4, 5, 6, 7, 8, 9), 'Unreviewed x64 relocation type')
            require(address+4 <= size, 'Relocation outside function section')
            masked.update(range(address, address+4))
            relocations.append({'offset': address, 'type': kind, 'symbolIndex': symbol_index})
        runs, start = [], 0
        for i in range(size+1):
            if i == size or i in masked:
                if i > start:
                    runs.append((start, i))
                start = i+1
        require(runs, 'No unrelocated bytes')
        a, b = max(runs, key=lambda ab: ab[1]-ab[0])
        positions, pos = [], exe.find(code[a:b])
        while pos >= 0:
            base = pos-a
            if base >= 0 and base+size <= len(exe) and all(exe[base+i] == code[i] for i in range(size) if i not in masked):
                positions.append(base)
            pos = exe.find(code[a:b], pos+1)
        locations = []
        for base in positions:
            for sec_name, rva, raw_start, raw_size, flags in sections:
                if raw_start <= base and base+size <= raw_start+raw_size and flags & 0x20000000:
                    va = image_base+rva+base-raw_start
                    locations.append({'fileOffset': base, 'virtualAddress': hex(va), 'section': sec_name})
                    lines = []
                    for i, line in enumerate(executable):
                        match = re.match(r'\s*([0-9A-F]{16}):', line)
                        if match and va <= int(match.group(1), 16) < va+size:
                            lines.append(str(i+1)+':'+line)
                    excerpt(out / (name+'-executable-'+hex(va)+'.txt'), lines)
        first = next((i for i, line in enumerate(dis) if line.startswith(decorated+' ')), None)
        if first is not None:
            last = next((i for i in range(first+1, len(dis))
                         if dis[i] and not dis[i].startswith(' ') and dis[i].endswith(':')), len(dis))
            excerpt(out / (name+'-object.txt'), [str(i+1)+':'+dis[i] for i in range(first, last)])
        map_records = mapped_symbols.get(decorated, [])
        map_addresses = {r['virtualAddress'] for r in map_records}
        entry.update({'decoratedSymbol': decorated, 'symbolLine': symbol_line,
                      'coffSection': section, 'bytes': size,
                      'objectSectionSha256': hashlib.sha256(code).hexdigest(),
                      'nonRelocatedBytesCompared': size-len(masked),
                      'relocationsNotSemanticallyResolved': relocations,
                      'executableMatches': locations, 'mapRecords': map_records,
                      'mapAndByteCorrespondence': len(locations) == 1 and len(map_records) == 1
                         and locations[0]['virtualAddress'] in map_addresses})
        if not locations or not map_records:
            entry['limitation'] = 'No complete section/map match; inline or eliminated code must be examined in its caller.'
    return {'schema': 1, 'status': 'EXPLORED', 'scope': SCOPE, 'imageBase': hex(image_base),
            'functions': findings, 'formalArtifactAuditComplete': False,
            'notProved': ['resolved relocation/callee closure', 'all FP control-state paths',
                          'exception/normal control-flow dominance', 'World/Progress alias closure',
                          'post-first-store no-fail semantics', 'complete clock graph',
                          'hardware/crash/CPU-transaction atomicity']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--build', type=Path, default=DEFAULT_BUILD)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.output.resolve()
    allowed = ROOT / 'reports/world-static-mesh-flight-advance-machine-review'
    require(out.is_relative_to(allowed) and out != allowed, 'Output must be a fresh machine-review child')
    require(build == DEFAULT_BUILD or build.is_relative_to(ROOT / 'build/world-flight-advance-integration'),
            'Unexpected integration build directory')
    obj = build / 'pikapika_core.dir/Release/world_static_mesh_flight_advance.obj'
    exe = build / 'Release/pikapika_world_static_mesh_flight_advance_tests.exe'
    map_path = build / 'Release/world-flight-advance.map'
    profile_path = build / 'world-flight-binding-Release.json'
    # Complete prerequisites before creating a run: a missing build is not a test attempt.
    for path in (obj, exe, map_path, profile_path):
        require(path.is_file(), 'Build-owner completion required; missing '+str(path))
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    require(profile['compiler']['id'] == 'MSVC' and profile['configuration'] == 'Release', 'Expected MSVC Release profile')
    dumpbin = Path(profile['compiler']['dumpbin'])
    require(dumpbin.is_file(), 'dumpbin unavailable')
    prototype_path = ROOT / 'reports/world-static-mesh-flight-advance-prototype-verification.json'
    prototype = json.loads(prototype_path.read_text(encoding='utf-8'))
    for item in prototype['files']:
        require(identity(ROOT / item['path']) == item, 'Frozen prototype evidence changed: '+item['path'])
    paths = {ROOT / item['path'] for item in prototype['files']}
    paths.update((obj, exe, map_path, profile_path, prototype_path, Path(__file__).resolve(),
                  ROOT / 'CMakeLists.txt', ROOT / 'reports/world-static-mesh-flight-guard-recipes/audit-binding.py'))
    paths.update(ROOT / source['path'] for source in profile['sources'])
    paths.update(p for p in build.rglob('*.tlog') if p.name in ('CL.command.1.tlog', 'link.command.1.tlog'))
    before = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(paths)}
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'before.json', before)
    (out / 'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    (out / 'profile.json').write_bytes(profile_path.read_bytes())
    commands, result = [], None
    started = time.perf_counter()
    try:
        for name, switches, artifact in (
            ('object-symbols', ['/symbols'], obj), ('object-disassembly', ['/disasm'], obj),
            ('object-relocations', ['/relocations'], obj), ('executable-headers', ['/headers'], exe),
            ('executable-disassembly', ['/disasm'], exe), ('executable-unwind', ['/unwindinfo'], exe)):
            argv = [str(dumpbin), '/nologo', *switches, str(artifact)]
            start = time.perf_counter()
            completed = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120, check=False)
            stdout, stderr = out / (name+'.stdout.txt'), out / (name+'.stderr.txt')
            stdout.write_bytes(completed.stdout)
            stderr.write_bytes(completed.stderr)
            record = {'name': name, 'argv': argv, 'cwd': str(ROOT), 'exit': completed.returncode,
                      'elapsedSeconds': time.perf_counter()-start, 'stdout': identity(stdout), 'stderr': identity(stderr)}
            write(out / (name+'.command.json'), record)
            commands.append(record)
            require(completed.returncode == 0, 'dumpbin failed: '+name)
        result = correlate(out, obj, exe, map_path)
        write(out / 'byte-map-correlation.json', result)
    finally:
        after = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(paths)}
        write(out / 'after.json', after)
        write(out / 'commands.json', commands)
        write(out / 'collection.json', {'schema': 1, 'status': 'COLLECTED' if result is not None and before == after else 'FAILED',
              'scope': SCOPE, 'originalSourcesAndArtifactsUnchanged': before == after,
              'inputFiles': len(before), 'frozenPrototypeFilesChecked': len(prototype['files']),
              'profile': identity(profile_path), 'profileBuildId': profile['buildId'],
              'requestedProfileSources': len(profile['sources']),
              'compilerProfileAndStrictCommandAcceptance': 'Separate core auditor evidence; not certified by this review.',
              'formalArtifactAuditComplete': False, 'elapsedSeconds': time.perf_counter()-started,
              'dumpbin': {'path': str(dumpbin), 'bytes': dumpbin.stat().st_size,
                          'sha256': hashlib.sha256(dumpbin.read_bytes()).hexdigest()}})
        require(before == after, 'Input source or artifact changed during collection')
    print(json.dumps({'status': 'COLLECTED', 'commands': len(commands), 'inputFiles': len(before),
                      'profileBuildId': profile['buildId'], 'formalArtifactAuditComplete': False,
                      'output': out.relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    main()
