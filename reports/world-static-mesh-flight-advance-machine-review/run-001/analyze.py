"""Exploratory COFF section/PE byte correlation, not a graph proof."""
from pathlib import Path
import hashlib
import json
import re
import struct

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'build/world-flight-advance-prototype/run-20261105-configured-001/build'
obj = (BASE / 'advance_prototype_core.dir/Release/world_static_mesh_flight_advance.obj').read_bytes()
exe = (BASE / 'Release/advance_configured.exe').read_bytes()
machine, count, _, _, _, optional, _ = struct.unpack_from('<HHLLLHH', obj)
if machine != 0x8664 or optional != 0:
    raise ValueError('Expected standard x64 COFF object')
pe = struct.unpack_from('<L', exe, 0x3c)[0]
if exe[pe:pe+4] != b'PE\0\0':
    raise ValueError('Missing PE signature')
_, pe_count, _, _, _, pe_optional, _ = struct.unpack_from('<HHLLLHH', exe, pe+4)
image_base = struct.unpack_from('<Q', exe, pe+24+24)[0]
pe_sections = []
for n in range(pe_count):
    off = pe+24+pe_optional+40*n
    name, virtual_size, rva, size, raw, _, _, _, _, flags = struct.unpack_from('<8sLLLLLLHHL', exe, off)
    pe_sections.append((name.rstrip(b'\0').decode('ascii'), rva, raw, size, flags))
symbols = (OUT / 'object-symbols.stdout.txt').read_text(encoding='utf-8', errors='replace').splitlines()
dis = (OUT / 'object-disassembly.stdout.txt').read_text(encoding='utf-8', errors='replace').splitlines()
exe_dis = (OUT / 'executable-disassembly.stdout.txt').read_text(encoding='utf-8', errors='replace').splitlines()
findings = []
for name in ['advance', 'clock_preflight', 'commit', 'prepare_commit', 'validate_commit', 'origin_preflight']:
    matches = [(i+1, line) for i, line in enumerate(symbols) if '| ?'+name+'@' in line and 'notype ()' in line]
    if len(matches) != 1:
        raise ValueError('Expected one function section for '+name)
    symbol_line, symbol = matches[0]
    section = int(re.search(r'SECT([0-9A-F]+)', symbol).group(1), 16)
    off = 20+40*(section-1)
    _, _, _, size, raw, reloc, _, reloc_count, _, _ = struct.unpack_from('<8sLLLLLLHHL', obj, off)
    code = obj[raw:raw+size]
    masked = set()
    relocation_types = []
    for i in range(reloc_count):
        address, symbol_index, kind = struct.unpack_from('<LLH', obj, reloc+10*i)
        if kind not in (2, 3, 4, 5, 6, 7, 8, 9):
            raise ValueError('Unreviewed x64 relocation type '+str(kind))
        masked.update(range(address, address+4))
        relocation_types.append({'offset': address, 'type': kind, 'symbolIndex': symbol_index})
    # Select the longest unchanged run as a search seed, then verify ALL other
    # unchanged bytes. Relocation targets are intentionally NOT certified here.
    runs = []
    start = 0
    for i in range(size+1):
        if i == size or i in masked:
            if i > start:
                runs.append((start, i))
            start = i+1
    a, b = max(runs, key=lambda ab: ab[1]-ab[0])
    seed = code[a:b]
    locations = []
    pos = exe.find(seed)
    while pos >= 0:
        base = pos-a
        if base >= 0 and base+size <= len(exe) and all(exe[base+i] == code[i] for i in range(size) if i not in masked):
            locations.append(base)
        pos = exe.find(seed, pos+1)
    mapped = []
    for base in locations:
        for sec_name, rva, raw_start, raw_size, flags in pe_sections:
            if raw_start <= base and base+size <= raw_start+raw_size and flags & 0x20000000:
                va = image_base+rva+base-raw_start
                mapped.append({'fileOffset': base, 'virtualAddress': hex(va), 'section': sec_name})
                excerpt = []
                for line in exe_dis:
                    m = re.match(r'\s*([0-9A-F]{16}):', line)
                    if m and va <= int(m.group(1), 16) < va+size:
                        excerpt.append(line)
                (OUT / (name+'-executable-excerpt.txt')).write_text('\n'.join(excerpt)+'\n', encoding='utf-8')
    first = next(i for i, line in enumerate(dis) if line.startswith('?'+name+'@'))
    last = next((i for i in range(first+1, len(dis)) if dis[i] and not dis[i].startswith(' ') and dis[i].endswith(':')), len(dis))
    (OUT / (name+'-object-excerpt.txt')).write_text('\n'.join(str(i+1)+':'+dis[i] for i in range(first, last))+'\n', encoding='utf-8')
    findings.append({'name': name, 'symbolLine': symbol_line, 'symbol': symbol,
                     'coffSection': section, 'bytes': size,
                     'nonRelocatedBytesCompared': size-len(masked),
                     'relocationsNotSemanticallyResolved': relocation_types,
                     'executableMatches': mapped,
                     'objectSectionSha256': hashlib.sha256(code).hexdigest(),
                     'scope': 'All non-relocation section bytes match; relocation target/control-flow semantics require a separate audit.'})
result = {'schema': 1, 'status': 'EXPLORED', 'functions': findings,
          'formalArtifactAuditComplete': False,
          'notProved': ['relocation target closure', 'branch/exception dominance',
                        'all external write aliases', 'Interval/CRT call graph',
                        'rounding-control behavior throughout the call',
                        'all clock inputs or machine faults', 'transactional CPU atomicity']}
with (OUT / 'byte-correlation.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'EXPLORED', 'matches': {f['name']: f['executableMatches'] for f in findings}}))
